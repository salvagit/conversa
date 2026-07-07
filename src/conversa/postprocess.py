"""Post-processing of transcripts with the Anthropic API: clean, summarize, narrate.

Long transcripts are chunked on speaker-turn boundaries and processed
sequentially. Prompts live in ``prompts/*.txt`` and can be edited without
touching code.
"""
from __future__ import annotations

import random
import time
from functools import lru_cache
from pathlib import Path

import anthropic

from .config import Config
from .secrets import ensure_anthropic_key

_PROMPTS_DIR = Path(__file__).parent / "prompts"


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()


class ChunkFailure(Exception):
    """Raised when a chunk keeps failing; carries the partial-progress path."""

    def __init__(self, partial_path: Path, detail: str):
        self.partial_path = partial_path
        self.detail = detail
        super().__init__(detail)


class InsufficientCreditsError(Exception):
    """Raised when the Anthropic account is out of API credits.

    Systemic, account-level failure: callers should abort the whole run
    instead of retrying the remaining files.
    """


def _raise_if_credit_error(exc: Exception) -> None:
    text = str(exc).lower()
    if "credit balance" in text or "billing" in text:
        raise InsufficientCreditsError(
            "Anthropic API credit balance exhausted. Add credits at "
            "console.anthropic.com → Billing and retry."
        ) from exc


def client() -> anthropic.Anthropic:
    ensure_anthropic_key()
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ERROR: ANTHROPIC_API_KEY not found in the environment or .env")
    return anthropic.Anthropic()


def _text_of(message) -> str:
    return "".join(b.text for b in message.content if b.type == "text").strip()


def _with_retry(fn, label: str, cfg: Config):
    last_exc: Exception | None = None
    for attempt in range(cfg.max_retries):
        try:
            return fn()
        except (anthropic.RateLimitError, anthropic.APIConnectionError,
                anthropic.InternalServerError) as exc:
            last_exc = exc
        except anthropic.APIStatusError as exc:
            status = getattr(exc, "status_code", None)
            if status and status >= 500:
                last_exc = exc
            else:
                _raise_if_credit_error(exc)  # abort the whole run, don't retry
                raise  # other 4xx: not retryable
        if attempt == cfg.max_retries - 1:
            break
        delay = min(cfg.base_delay * (2 ** attempt), 60.0) + random.uniform(0, 1)
        print(f"      retry {attempt + 1}/{cfg.max_retries} of {label} in {delay:.1f}s "
              f"({type(last_exc).__name__})…", flush=True)
        time.sleep(delay)
    if last_exc is None:  # unreachable, but explicit (asserts vanish under -O)
        raise RuntimeError("retry loop exhausted without exception or result")
    raise last_exc


def _turn_blocks(text: str) -> list[str]:
    return [b.strip() for b in text.split("\n\n") if b.strip()]


def _group_blocks(blocks: list[str], budget: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for block in blocks:
        if current and size + len(block) > budget:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(block)
        size += len(block) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def clean_file(md_path: Path, cfg: Config,
               anthropic_client: anthropic.Anthropic | None = None) -> Path:
    """Clean a transcript .md into <base>.limpia.md. Never touches the original."""
    c = anthropic_client or client()
    out_path = md_path.with_name(f"{md_path.stem}.limpia.md")
    system = load_prompt("clean")

    blocks = _turn_blocks(md_path.read_text(encoding="utf-8"))
    chunks = _group_blocks(blocks, cfg.chunk_chars)
    cleaned: list[str] = []

    for i, chunk in enumerate(chunks, 1):
        print(f"    cleaning chunk {i}/{len(chunks)}…", flush=True)
        try:
            message = _with_retry(
                lambda: c.messages.create(
                    model=cfg.clean_model, max_tokens=cfg.clean_max_tokens,
                    system=system, messages=[{"role": "user", "content": chunk}]),
                label=f"chunk {i}", cfg=cfg)
        except Exception as exc:  # noqa: BLE001 - save partial progress then report
            partial = md_path.with_name(f"{md_path.stem}.limpia.parcial.md")
            partial.write_text("\n\n".join(cleaned) + "\n", encoding="utf-8")
            if isinstance(exc, InsufficientCreditsError):
                raise
            raise ChunkFailure(
                partial, f"chunk {i}/{len(chunks)} of {md_path.name} failed: {exc}"
            ) from exc
        cleaned.append(_text_of(message))

    out_path.write_text("\n\n".join(cleaned).strip() + "\n", encoding="utf-8")
    return out_path


def summarize_file(limpia_path: Path, cfg: Config,
                   anthropic_client: anthropic.Anthropic | None = None) -> Path:
    """Summarize a cleaned transcript into <base>.resumen.md."""
    c = anthropic_client or client()
    base = (limpia_path.name[: -len(".limpia.md")]
            if limpia_path.name.endswith(".limpia.md") else limpia_path.stem)
    out_path = limpia_path.with_name(f"{base}.resumen.md")
    system = load_prompt("summary")
    transcript = limpia_path.read_text(encoding="utf-8")

    def _run():
        with c.messages.stream(
            model=cfg.summary_model, max_tokens=cfg.summary_max_tokens,
            system=system, messages=[{"role": "user", "content": transcript}]) as stream:
            return stream.get_final_message()

    message = _with_retry(_run, label="summary", cfg=cfg)
    out_path.write_text(_text_of(message) + "\n", encoding="utf-8")
    return out_path


def narrate_file(limpia_path: Path, context: str, cfg: Config, narrator: str,
                 brief: bool = False,
                 anthropic_client: anthropic.Anthropic | None = None) -> str:
    """First-person narrative of a named cleaned transcript, for use as evidence.

    ``context`` is a header hint (date + participants). ``narrator`` is the
    first-person subject. Returns the narrative Markdown (caller writes it)."""
    c = anthropic_client or client()
    system = load_prompt("narrate_brief" if brief else "narrate").format(narrator=narrator)
    transcript = limpia_path.read_text(encoding="utf-8")
    user = f"Context: {context}\n\nTranscript:\n\n{transcript}"

    def _run():
        with c.messages.stream(
            model=cfg.narrate_model, max_tokens=cfg.narrate_max_tokens,
            system=system, messages=[{"role": "user", "content": user}]) as stream:
            return stream.get_final_message()

    message = _with_retry(_run, label="narrative", cfg=cfg)
    return _text_of(message).strip()
