"""Tests for speaker renaming (no heavy deps: pure text + path validation)."""
from pathlib import Path

import pytest

from conversa import speakers


def test_parse_mapping_basic():
    assert speakers.parse_mapping("A=Ana,B=Beto") == {
        "A": "Ana", "B": "Beto"}


def test_parse_mapping_trims_and_uppercases():
    assert speakers.parse_mapping(" a = Ana , b= Beto ") == {"A": "Ana", "B": "Beto"}


def test_parse_mapping_rejects_bad_pair():
    with pytest.raises(ValueError):
        speakers.parse_mapping("A")


def test_apply_to_text_md_and_srt():
    text = "**Speaker A:** hola\n\n[Speaker B] chau"
    out = speakers.apply_to_text(text, {"A": "Ana", "B": "Beto"})
    assert out == "**Ana:** hola\n\n[Beto] chau"


def test_apply_to_text_word_boundary():
    # "Speaker A" must not be eaten when followed by another letter.
    assert speakers.apply_to_text("Speaker AB", {"A": "Ana"}) == "Speaker AB"


@pytest.mark.parametrize("bad", ["../evil", "a/b", "/etc/passwd", "..", "", "."])
def test_validate_base_rejects_traversal(bad):
    with pytest.raises(ValueError):
        speakers.validate_base(bad)


def test_validate_base_accepts_plain_stem():
    assert speakers.validate_base("2024-07-12-team-meeting") == "2024-07-12-team-meeting"


def test_rename_base_rejects_traversal(tmp_path: Path):
    (tmp_path / "x.md").write_text("**Speaker A:** hola\n", encoding="utf-8")
    with pytest.raises(ValueError):
        speakers.rename_base("../escape", {"A": "Ana"}, tmp_path, tmp_path / "out")


def test_rename_base_writes_renamed_copy(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "call.md").write_text("**Speaker A:** hola\n", encoding="utf-8")
    (src / "call.srt").write_text("1\n00:00 --> 00:01\n[Speaker A] hola\n", encoding="utf-8")
    dst = tmp_path / "dst"
    written = speakers.rename_base("call", {"A": "Ana"}, src, dst)
    assert {p.name for p in written} == {"call.md", "call.srt"}
    assert "**Ana:** hola" in (dst / "call.md").read_text(encoding="utf-8")
    # original untouched
    assert "**Speaker A:** hola" in (src / "call.md").read_text(encoding="utf-8")
