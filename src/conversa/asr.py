"""Transcription + speaker diarization with WhisperX.

Produces, per audio ``<base>``, in the configured output dir:
    <base>.md   -> speaker-labelled transcript (**Speaker A:** ...)
    <base>.srt  -> subtitles with timestamps

Requires ffmpeg on PATH and a Hugging Face token with access to the
diarization model.
"""
from __future__ import annotations

import os
import re
import warnings
from pathlib import Path

from .config import Config

# pyannote 4.x prints a noisy torchcodec warning at import time; WhisperX decodes
# audio itself via ffmpeg and hands pyannote an in-memory waveform, so silence it.
warnings.filterwarnings("ignore")
os.environ.setdefault("PYTHONWARNINGS", "ignore")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Cap subtitle cue length so SRT stays readable.
SRT_MAX_CUE_SECONDS = 7.0
SRT_MAX_CUE_WORDS = 14

_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?…»)\]])")
_SPACE_AFTER_OPEN = re.compile(r"([¿¡«(\[])\s+")


def format_timestamp(seconds: float) -> str:
    """Seconds -> SRT timestamp (HH:MM:SS,mmm)."""
    if seconds is None or seconds < 0:
        seconds = 0.0
    ms = round(seconds * 1000.0)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def detokenize(words: list[str]) -> str:
    """Join aligned word tokens into clean text (fix punctuation spacing)."""
    text = " ".join(w.strip() for w in words if w.strip())
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = _SPACE_AFTER_OPEN.sub(r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def iter_words(segments: list[dict]):
    """Flatten word-level tokens, inheriting the segment speaker as fallback."""
    for seg in segments:
        seg_spk = seg.get("speaker")
        for w in seg.get("words", []):
            token = (w.get("word") or "").strip()
            if not token:
                continue
            yield {
                "word": token,
                "start": w.get("start"),
                "end": w.get("end"),
                "speaker": w.get("speaker", seg_spk),
            }


def build_turns(segments: list[dict]) -> list[dict]:
    """Regroup words into speaker turns (a new turn whenever the speaker changes)."""
    turns: list[dict] = []
    last_spk = None
    for w in iter_words(segments):
        spk = w["speaker"] if w["speaker"] is not None else last_spk
        if not turns or turns[-1]["speaker"] != spk:
            turns.append({"speaker": spk, "words": []})
        turns[-1]["words"].append(w)
        last_spk = spk
    for t in turns:
        starts = [w["start"] for w in t["words"] if w["start"] is not None]
        ends = [w["end"] for w in t["words"] if w["end"] is not None]
        t["start"] = min(starts) if starts else 0.0
        t["end"] = max(ends) if ends else t["start"]
        t["text"] = detokenize([w["word"] for w in t["words"]])
    return turns


def speaker_label_map(turns: list[dict]) -> dict[str, str]:
    """Map pyannote labels (SPEAKER_00, ...) to Speaker A/B/C by first appearance."""
    mapping: dict[str, str] = {}
    for t in turns:
        spk = t["speaker"]
        if spk and spk not in mapping:
            mapping[spk] = f"Speaker {chr(ord('A') + len(mapping))}"
    return mapping


def write_markdown(turns: list[dict], out_path: Path, labels: dict[str, str]) -> None:
    lines: list[str] = []
    for t in turns:
        if not t["text"]:
            continue
        label = labels.get(t["speaker"], "Speaker ?")
        lines.append(f"**{label}:** {t['text']}")
        lines.append("")
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _chunk_words(words: list[dict]):
    cue: list[dict] = []
    for w in words:
        if cue:
            span = (w.get("end") or w.get("start") or 0.0) - (cue[0].get("start") or 0.0)
            if len(cue) >= SRT_MAX_CUE_WORDS or span > SRT_MAX_CUE_SECONDS:
                yield cue
                cue = []
        cue.append(w)
    if cue:
        yield cue


def write_srt(turns: list[dict], out_path: Path, labels: dict[str, str]) -> None:
    blocks: list[str] = []
    idx = 1
    for t in turns:
        label = labels.get(t["speaker"]) if t["speaker"] else None
        prefix = f"[{label}] " if label else ""
        for cue in _chunk_words(t["words"]):
            text = detokenize([w["word"] for w in cue])
            if not text:
                continue
            start = format_timestamp(cue[0].get("start", 0.0))
            end = format_timestamp(cue[-1].get("end", cue[-1].get("start", 0.0)))
            blocks.append(f"{idx}\n{start} --> {end}\n{prefix}{text}\n")
            idx += 1
    out_path.write_text("\n".join(blocks), encoding="utf-8")


def _is_memory_error(exc: Exception) -> bool:
    if isinstance(exc, MemoryError):
        return True
    msg = str(exc).lower()
    return any(s in msg for s in ("out of memory", "cannot allocate", "can't allocate",
                                  "bad_alloc", "not enough memory"))


class Transcriber:
    """Loads WhisperX models once and transcribes audio files, with automatic
    downgrade to a smaller Whisper model if transcription runs out of memory.

    ``config.language`` is passed straight to Whisper: it forces the expected
    language rather than letting Whisper auto-detect it (unreliable on noisy
    call audio), so it must match the audio."""

    def __init__(self, hf_token: str, config: Config, model_name: str | None = None):
        import whisperx
        from whisperx.diarize import DiarizationPipeline

        self._whisperx = whisperx
        self.cfg = config
        self.model_name = model_name or config.model

        print(f"Loading Whisper model '{self.model_name}' "
              f"({config.compute_type}, {config.threads} threads)…", flush=True)
        self.whisper_model = self._load_whisper(self.model_name)
        print(f"Loading alignment model for '{config.language}'…", flush=True)
        self.align_model, self.align_metadata = whisperx.load_align_model(
            config.language, config.device)
        print("Loading diarization model…", flush=True)
        self.diarize_model = DiarizationPipeline(token=hf_token, device=config.device)

    def _load_whisper(self, model_name: str):
        c = self.cfg
        return self._whisperx.load_model(
            model_name, c.device, compute_type=c.compute_type,
            language=c.language, threads=c.threads)

    def _downgrade(self) -> bool:
        """Switch to the next smaller model. Returns False if none is left."""
        chain = self.cfg.fallback_models
        try:
            idx = chain.index(self.model_name)
        except ValueError:
            idx = 0
        if idx + 1 >= len(chain):
            return False
        new_model = chain[idx + 1]
        print(f"  ⚠️  insufficient memory with '{self.model_name}'; "
              f"falling back to '{new_model}' and retrying…", flush=True)
        import gc
        del self.whisper_model
        gc.collect()
        self.model_name = new_model
        self.whisper_model = self._load_whisper(new_model)
        return True

    def transcribe(self, audio_path: Path) -> Path:
        whisperx = self._whisperx
        c = self.cfg

        print("  · loading audio…", flush=True)
        audio = whisperx.load_audio(str(audio_path))

        print("  · transcribing…", flush=True)
        while True:
            try:
                result = self.whisper_model.transcribe(
                    audio, batch_size=c.batch_size, language=c.language)
                break
            except Exception as exc:  # noqa: BLE001 - only retry on memory errors
                if _is_memory_error(exc) and self._downgrade():
                    continue
                raise

        print("  · aligning words…", flush=True)
        result = whisperx.align(
            result["segments"], self.align_model, self.align_metadata,
            audio, c.device, return_char_alignments=False)

        print(f"  · diarizing (speakers {c.min_speakers}-{c.max_speakers})…", flush=True)
        diarize_df = self.diarize_model(
            audio, min_speakers=c.min_speakers, max_speakers=c.max_speakers)
        result = whisperx.assign_word_speakers(diarize_df, result)

        turns = build_turns(result["segments"])
        labels = speaker_label_map(turns)

        base = audio_path.stem
        md_path = c.output_dir / f"{base}.md"
        srt_path = c.output_dir / f"{base}.srt"
        write_markdown(turns, md_path, labels)
        write_srt(turns, srt_path, labels)
        n_spk = len(labels)
        print(f"  ✓ {md_path}  ({n_spk} speaker{'s' if n_spk != 1 else ''})", flush=True)
        return md_path
