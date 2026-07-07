"""Configuration for conversa, with sane defaults and optional TOML overrides.

Everything works out of the box with the dataclass defaults. Drop a
``conversa.toml`` next to where you run the tool (or pass ``--config``) to
override any of these without touching code.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - tomllib is stdlib on 3.11+
    tomllib = None  # type: ignore[assignment]

DEFAULT_CONFIG_NAME = "conversa.toml"


@dataclass
class Config:
    # --- ASR (WhisperX) ---
    model: str = "large-v3-turbo"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "es"
    min_speakers: int = 2
    max_speakers: int = 3
    batch_size: int = 16
    threads: int = 8
    fallback_models: list[str] = field(
        default_factory=lambda: ["large-v3-turbo", "medium", "small"])
    diarize_model: str = "pyannote/speaker-diarization-community-1"

    # --- I/O ---
    audio_exts: list[str] = field(
        default_factory=lambda: [".m4a", ".mp3", ".wav", ".mp4", ".ogg", ".flac"])
    output_dir: Path = Path("transcripciones")

    # --- LLM (Anthropic) ---
    clean_model: str = "claude-haiku-4-5"
    summary_model: str = "claude-sonnet-5"
    narrate_model: str = "claude-sonnet-5"
    chunk_chars: int = 8000
    clean_max_tokens: int = 8000
    summary_max_tokens: int = 8000
    narrate_max_tokens: int = 8000
    max_retries: int = 5
    base_delay: float = 2.0

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        """Load config, merging a TOML file (explicit path or ./conversa.toml)."""
        cfg = cls()
        toml_path = path or Path(DEFAULT_CONFIG_NAME)
        if tomllib is None or not toml_path.exists():
            return cfg
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        # Accept both flat keys and [asr]/[io]/[llm] sections.
        flat: dict = {}
        for value in data.values():
            if isinstance(value, dict):
                flat.update(value)
        flat.update({k: v for k, v in data.items() if not isinstance(v, dict)})
        known = {f.name for f in fields(cls)}
        for key, value in flat.items():
            if key in known:
                setattr(cfg, key, Path(value) if key == "output_dir" else value)
        return cfg
