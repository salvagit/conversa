"""End-to-end orchestration: transcribe -> clean -> summarize.

Stages are resumable: each skips work whose output already exists (unless
``force``). A low-balance API error aborts the whole run (nothing else will
succeed until credits are topped up).
"""
from __future__ import annotations

import sys
from pathlib import Path

from . import postprocess
from .config import Config
from .secrets import load_hf_token


def resolve_bases(path: Path, cfg: Config) -> list[str]:
    """Return the audio base names for a file or folder argument."""
    if path.is_dir():
        files = sorted(f for ext in cfg.audio_exts for f in path.glob(f"*{ext}"))
        if not files:
            sys.exit(f"ERROR: no audio files ({', '.join(cfg.audio_exts)}) in {path}")
        return [f.stem for f in files]
    if path.suffix in cfg.audio_exts:
        return [path.stem]
    name = path.name
    for suffix in (".limpia.md", ".md"):
        if name.endswith(suffix):
            return [name[: -len(suffix)]]
    sys.exit(f"ERROR: unrecognized {path} (expected audio, .md or .limpia.md)")


def run(path: Path, cfg: Config, *, force: bool = False,
        do_transcribe: bool = True, do_clean: bool = True,
        do_summary: bool = True) -> int:
    """Run the requested stages. Returns a process exit code (0/1/2)."""
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    bases = resolve_bases(path, cfg)
    incomplete: list[str] = []

    if do_transcribe:
        audio_dir = path if path.is_dir() else path.parent
        pending = [b for b in bases
                   if force or not (cfg.output_dir / f"{b}.md").exists()]
        if pending:
            from .asr import Transcriber
            transcriber = Transcriber(load_hf_token(), cfg)
            exts = cfg.audio_exts
            for i, base in enumerate(pending, 1):
                audio = next((audio_dir / f"{base}{e}" for e in exts
                              if (audio_dir / f"{base}{e}").exists()), None)
                print(f"\n[transcribe {i}/{len(pending)}] {base}", flush=True)
                if audio is None:
                    print(f"  ✗ can't find the audio for {base}", flush=True)
                    incomplete.append(base)
                    continue
                try:
                    transcriber.transcribe(audio)
                except Exception as exc:  # noqa: BLE001
                    print(f"  ✗ transcription FAILED: {exc}", flush=True)
                    incomplete.append(base)
        else:
            print("Transcription: nothing pending.", flush=True)

    client = postprocess.client() if (do_clean or do_summary) else None
    try:
        if do_clean:
            _stage_clean(bases, cfg, client, force, incomplete)
        if do_summary:
            _stage_summary(bases, cfg, client, force, incomplete)
    except postprocess.InsufficientCreditsError as exc:
        print(f"\n✗ {exc}\n  Aborting: no point continuing without credits.", flush=True)
        return 2

    if incomplete:
        print("\n⚠️  Left incomplete: " + ", ".join(sorted(set(incomplete))), flush=True)
        return 1
    print("\n✓ Done.", flush=True)
    return 0


def _stage_clean(bases, cfg, client, force, incomplete):
    for base in bases:
        md = cfg.output_dir / f"{base}.md"
        out = cfg.output_dir / f"{base}.limpia.md"
        if not md.exists():
            print(f"– clean: missing {md.name}, skipping", flush=True)
            continue
        if out.exists() and not force:
            print(f"– clean: {out.name} already exists, skipping", flush=True)
            continue
        print(f"\n[clean] {md.name}", flush=True)
        try:
            print(f"  ✓ {postprocess.clean_file(md, cfg, client)}", flush=True)
        except postprocess.InsufficientCreditsError:
            raise
        except postprocess.ChunkFailure as exc:
            print(f"  ✗ {exc.detail}\n    partial saved at {exc.partial_path}", flush=True)
            incomplete.append(base)
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ cleanup FAILED: {exc}", flush=True)
            incomplete.append(base)


def _stage_summary(bases, cfg, client, force, incomplete):
    for base in bases:
        limpia = cfg.output_dir / f"{base}.limpia.md"
        out = cfg.output_dir / f"{base}.resumen.md"
        if not limpia.exists():
            print(f"– summarize: missing {limpia.name}, skipping", flush=True)
            continue
        if out.exists() and not force:
            print(f"– summarize: {out.name} already exists, skipping", flush=True)
            continue
        print(f"\n[summarize] {limpia.name}", flush=True)
        try:
            print(f"  ✓ {postprocess.summarize_file(limpia, cfg, client)}", flush=True)
        except postprocess.InsufficientCreditsError:
            raise
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ summary FAILED: {exc}", flush=True)
            incomplete.append(base)
