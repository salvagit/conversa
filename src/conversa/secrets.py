"""Read API tokens from the environment or a local .env file (no dependency)."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _from_env_file(*names: str) -> str | None:
    env_file = Path(".env")
    if not env_file.exists():
        return None
    wanted = tuple(f"{n}=" for n in names)
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith(wanted):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def load_hf_token() -> str:
    for key in ("HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        if os.environ.get(key):
            return os.environ[key]
    token = _from_env_file("HF_TOKEN", "HUGGINGFACE_TOKEN")
    if token:
        return token
    sys.exit(
        "ERROR: no Hugging Face token found.\n"
        "Set HF_TOKEN in the environment or in a .env file, and accept the terms\n"
        "for pyannote/speaker-diarization-community-1 on huggingface.co."
    )


def ensure_anthropic_key() -> None:
    """Populate ANTHROPIC_API_KEY from .env if not already in the environment."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    key = _from_env_file("ANTHROPIC_API_KEY")
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
