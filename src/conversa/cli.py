"""conversa — transcribe, clean, summarize and narrate spoken conversations."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, pipeline, postprocess, speakers
from .config import Config

_CONFIG_TEMPLATE = """\
# conversa config — override any default here. All keys are optional.
[general]
# ISO 639-1 code. Drives both the Whisper ASR model and the language the LLM
# stages (clean/summarize/narrate) write their output in. Any language Whisper
# supports works; see src/conversa/config.py:LANGUAGE_NAMES for the ones with
# a friendly display name (others still work, just less polished prompts).
language = "es"

[asr]
model = "large-v3-turbo"
min_speakers = 2
max_speakers = 3
threads = 8

[io]
output_dir = "transcripciones"
audio_exts = [".m4a", ".mp3", ".wav"]

[llm]
clean_model = "claude-haiku-4-5"
summary_model = "claude-sonnet-5"
narrate_model = "claude-sonnet-5"
"""

_ENV_TEMPLATE = """\
# Hugging Face token with access to pyannote/speaker-diarization-community-1
HF_TOKEN=hf_xxx
# Anthropic API key (create at console.anthropic.com; pay-as-you-go credits)
ANTHROPIC_API_KEY=sk-ant-xxx
"""


def _load_cfg(args) -> Config:
    cfg = Config.load(Path(args.config) if args.config else None)
    if getattr(args, "output_dir", None):
        cfg.output_dir = Path(args.output_dir)
    return cfg


def _cmd_run(args) -> int:
    cfg = _load_cfg(args)
    stages = {"transcribe": args.stage in (None, "transcribe"),
              "clean": args.stage in (None, "clean"),
              "summary": args.stage in (None, "summarize")}
    return pipeline.run(Path(args.path), cfg, force=args.force,
                        do_transcribe=stages["transcribe"],
                        do_clean=stages["clean"], do_summary=stages["summary"])


def _cmd_rename(args) -> int:
    cfg = _load_cfg(args)
    try:
        mapping = speakers.parse_mapping(args.map)
        src = Path(args.src) if args.src else cfg.output_dir
        dst = Path(args.to)
        written = speakers.rename_base(args.base, mapping, src, dst)
    except ValueError as exc:
        sys.exit(f"ERROR: {exc}")
    if not written:
        sys.exit(f"ERROR: found no artifacts for '{args.base}' in {src}")
    for p in written:
        print(f"  ✓ {p}")
    return 0


def _cmd_narrate(args) -> int:
    cfg = _load_cfg(args)
    limpia = Path(args.path)
    if not limpia.exists():
        sys.exit(f"ERROR: {limpia} does not exist")
    base = (limpia.name[: -len(".limpia.md")]
            if limpia.name.endswith(".limpia.md") else limpia.stem)
    out = limpia.with_name(f"{base}.relato.md")
    try:
        text = postprocess.narrate_file(
            limpia, args.context or "", cfg, narrator=args.narrator, brief=args.brief)
    except postprocess.InsufficientCreditsError as exc:
        print(f"✗ {exc}", flush=True)
        return 2
    out.write_text(text + "\n", encoding="utf-8")
    print(f"  ✓ {out}")
    return 0


def _cmd_init(args) -> int:
    for name, content in (("conversa.toml", _CONFIG_TEMPLATE),
                          (".env.example", _ENV_TEMPLATE)):
        p = Path(name)
        if p.exists():
            print(f"– {name} already exists, skipping")
        else:
            p.write_text(content, encoding="utf-8")
            print(f"  ✓ {name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="conversa", description=__doc__)
    parser.add_argument("--version", action="version", version=f"conversa {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, path_help="Audio file, folder, .md or .limpia.md"):
        p.add_argument("path", help=path_help)
        p.add_argument("--force", action="store_true", help="Redo even if output already exists")
        p.add_argument("--config", help="Path to a conversa.toml")
        p.add_argument("--output-dir", help="Output folder (override)")

    p_run = sub.add_parser("run", help="Full pipeline (transcribe→clean→summarize)")
    common(p_run)
    p_run.set_defaults(func=_cmd_run, stage=None)

    for name, stage, help_ in (("transcribe", "transcribe", "Transcribe only (WhisperX)"),
                               ("clean", "clean", "Clean filler words only"),
                               ("summarize", "summarize", "Summarize only")):
        p = sub.add_parser(name, help=help_)
        common(p)
        p.set_defaults(func=_cmd_run, stage=stage)

    p_nar = sub.add_parser("narrate", help="First-person narrative from a named .limpia.md file")
    p_nar.add_argument("path", help="A .limpia.md file with speaker names")
    p_nar.add_argument("--narrator", required=True, help="Narrator's name (first person)")
    p_nar.add_argument("--context", help="Context for the heading (date, participants)")
    p_nar.add_argument("--brief", action="store_true", help="Condensed version")
    p_nar.add_argument("--config")
    p_nar.add_argument("--output-dir")
    p_nar.set_defaults(func=_cmd_narrate)

    p_ren = sub.add_parser("rename", help="Replace Speaker A/B/C with real names")
    p_ren.add_argument("base", help="Audio base name (no extension)")
    p_ren.add_argument("--map", required=True, help='Mapping "A=Ana,B=Beto"')
    p_ren.add_argument("--src", help="Source folder (default: output_dir)")
    p_ren.add_argument("--to", required=True, help="Destination folder")
    p_ren.add_argument("--config")
    p_ren.add_argument("--output-dir")
    p_ren.set_defaults(func=_cmd_rename)

    p_init = sub.add_parser("init", help="Create conversa.toml and .env.example in the current directory")
    p_init.set_defaults(func=_cmd_init)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    target = getattr(args, "path", None)
    if target is not None and not Path(target).exists():
        sys.exit(f"ERROR: {target} does not exist")
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
