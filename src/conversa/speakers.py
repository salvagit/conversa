"""Replace generic ``Speaker A/B/C`` labels with real names.

Works on the Markdown transcript/summary (``**Speaker A:**``) and the SRT
(``[Speaker A]``). Reads from a source dir and writes renamed copies to a
destination dir, leaving the originals untouched.
"""
from __future__ import annotations

import re
from pathlib import Path

# Suffixes we know how to rewrite (all share the "Speaker X" token form).
KNOWN_SUFFIXES = (".md", ".srt", ".limpia.md", ".resumen.md")


def parse_mapping(spec: str) -> dict[str, str]:
    """Parse ``"A=Salvador,B=Damián"`` into ``{"A": "Salvador", "B": "Damián"}``."""
    mapping: dict[str, str] = {}
    for pair in spec.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ValueError(f"mapeo inválido: {pair!r} (esperaba 'A=Nombre')")
        letter, name = pair.split("=", 1)
        mapping[letter.strip().upper()] = name.strip()
    return mapping


def apply_to_text(text: str, mapping: dict[str, str]) -> str:
    for letter, name in mapping.items():
        # \b after the letter so "Speaker A" never eats "Speaker AB", etc.
        text = re.sub(rf"Speaker {re.escape(letter)}\b", name, text)
    return text


def rename_base(base: str, mapping: dict[str, str],
                src_dir: Path, dst_dir: Path) -> list[Path]:
    """Rewrite every known artifact of ``base`` from src_dir into dst_dir."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for suffix in KNOWN_SUFFIXES:
        src = src_dir / f"{base}{suffix}"
        if not src.exists():
            continue
        out = dst_dir / f"{base}{suffix}"
        out.write_text(apply_to_text(src.read_text(encoding="utf-8"), mapping),
                       encoding="utf-8")
        written.append(out)
    return written
