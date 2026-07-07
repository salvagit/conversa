"""Tests for multi-language support: name lookup, headings, prompt rendering."""
import re

from conversa import postprocess
from conversa.config import Config, language_display_name


def test_language_display_name_known():
    assert language_display_name("es") == "Spanish"
    assert language_display_name("en") == "English"
    assert language_display_name("PT") == "Portuguese"  # case-insensitive


def test_language_display_name_falls_back_to_raw_code():
    assert language_display_name("xx") == "xx"


def test_config_language_name_property():
    assert Config(language="es").language_name == "Spanish"
    assert Config(language="xx").language_name == "xx"


def test_summary_headings_spanish_are_pinned():
    assert postprocess.summary_headings("es") == (
        "Participantes", "Temas tratados", "Decisiones tomadas",
        "Pendientes / próximos pasos", "Citas textuales relevantes")


def test_summary_headings_unknown_language_falls_back_to_english():
    assert postprocess.summary_headings("xx") == postprocess.summary_headings("en")


def _no_placeholders_left(rendered: str) -> bool:
    return not re.search(r"\{[a-z_]+\}", rendered)


def test_clean_prompt_renders_for_any_language():
    for lang in ("es", "en", "xx"):
        rendered = postprocess.load_prompt("clean").format(
            language=language_display_name(lang))
        assert _no_placeholders_left(rendered)
        assert lang != "es" or "Spanish" in rendered


def test_summary_prompt_renders_with_headings():
    cfg = Config(language="es")
    h1, h2, h3, h4, h5 = postprocess.summary_headings(cfg.language)
    rendered = postprocess.load_prompt("summary").format(
        language=cfg.language_name, h1=h1, h2=h2, h3=h3, h4=h4, h5=h5)
    assert _no_placeholders_left(rendered)
    assert "## Participantes" in rendered


def test_narrate_prompts_render_for_any_language():
    for name in ("narrate", "narrate_brief"):
        rendered = postprocess.load_prompt(name).format(
            narrator="Ana", language="English")
        assert _no_placeholders_left(rendered)
        assert "Ana" in rendered
