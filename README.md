# conversa

Local console tool to transcribe spoken conversations with speaker separation
(WhisperX + diarization) and post-process them with the Anthropic API: filler-word
cleanup, structured summarization, and first-person narrative. Designed for use
with evidentiary value (interviews, evidence): the audio never leaves your
machine; only the text is, optionally, sent to the language model.

> ⚠️ Transcripts are **automatic** and may contain errors. The primary evidence
> is always the recording.

## Requirements

- Python 3.11+
- `ffmpeg` on `PATH` (`brew install ffmpeg`)
- A Hugging Face token with access to
  `pyannote/speaker-diarization-community-1` (accept the terms)
- An Anthropic API key (console.anthropic.com — pay-as-you-go, **different from
  a Claude Pro/Max subscription**)

## Installation

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
conversa init          # creates conversa.toml and .env.example
```

Fill in `.env` with `HF_TOKEN` and `ANTHROPIC_API_KEY`.

## Usage

```bash
conversa run audios/                 # full pipeline (transcribe→clean→summarize)
conversa transcribe audios/my.m4a    # WhisperX only
conversa clean audios/               # cleanup only
conversa summarize audios/           # summary only
conversa rename my-audio --map "A=Ana,B=Beto" --to names/
conversa narrate names/my-audio.limpia.md --narrator Ana --brief \
    --context "September 3, 2024. Participants: Ana and Beto."
```

Outputs (in `output_dir`, `transcripciones/` by default): `<base>.md`,
`<base>.srt`, `<base>.limpia.md`, `<base>.resumen.md`.

## Configuration

`conversa.toml` (optional) lets you override models, language, speaker range,
audio extensions, output folder and tokens. Prompts live in
`src/conversa/prompts/*.txt` and can be edited without touching code.

## Security and privacy

Evidentiary, sensitive material. Keep the data flow in mind:

- **The audio never leaves your machine.** Transcription (WhisperX +
  diarization) runs 100% locally.
- **The text IS sent to the Anthropic API** in the `clean`, `summarize` and
  `narrate` stages. If you need **nothing** to leave the machine, use only
  `conversa transcribe` (raw transcription, no LLM). Review Anthropic's API
  data-retention policy for your case.
- **Secrets:** `HF_TOKEN` and `ANTHROPIC_API_KEY` go in environment variables or
  in `.env` (excluded by `.gitignore`). Prefer environment variables and run the
  tool in trusted directories (a foreign `.env` could inject a different API
  key).
- **Always review the outputs.** Transcription is automatic (ASR errors) and the
  LLM can be influenced by the audio content itself (prompt injection). For
  evidence, the primary proof is the recording; rely on the `.srt` with
  timestamps to cross-check figures and key phrases.

## Next steps

- Provenance manifest (model/version/hash per output) for chain of custody.
- `--local-only` flag / explicit consent before sending text to the LLM.
- Graphical interface for non-technical users.
