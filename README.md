# conversa

Herramienta local de consola para transcribir conversaciones habladas con
separación de hablantes (WhisperX + diarización) y post-procesarlas con la API de
Anthropic: limpieza de muletillas, resumen estructurado y relato en primera
persona. Pensada para uso con valor probatorio (entrevistas, evidencia): el audio
nunca sale de tu máquina; solo el texto va, opcionalmente, al modelo de lenguaje.

> ⚠️ Las transcripciones son **automáticas** y pueden contener errores. La prueba
> primaria es siempre la grabación.

## Requisitos

- Python 3.11+
- `ffmpeg` en el `PATH` (`brew install ffmpeg`)
- Token de Hugging Face con acceso a
  `pyannote/speaker-diarization-community-1` (aceptar los términos)
- API key de Anthropic (console.anthropic.com — prepago por uso, **distinto de
  una suscripción Claude Pro/Max**)

## Instalación

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
conversa init          # crea conversa.toml y .env.example
```

Completá `.env` con `HF_TOKEN` y `ANTHROPIC_API_KEY`.

## Uso

```bash
conversa run audios/                 # pipeline completo (transcribir→limpiar→resumir)
conversa transcribe audios/mi.m4a    # solo WhisperX
conversa clean audios/               # solo limpieza
conversa summarize audios/           # solo resumen
conversa rename mi-audio --map "A=Ana,B=Beto" --to nombres/
conversa narrate nombres/mi-audio.limpia.md --narrator Ana --brief \
    --context "3 de septiembre de 2024. Participantes: Ana y Beto."
```

Salidas (en `output_dir`, por defecto `transcripciones/`): `<base>.md`,
`<base>.srt`, `<base>.limpia.md`, `<base>.resumen.md`.

## Configuración

`conversa.toml` (opcional) permite override de modelos, idioma, rango de
hablantes, extensiones de audio, carpeta de salida y tokens. Los prompts viven en
`src/conversa/prompts/*.txt` y se pueden editar sin tocar código.

## Seguridad y privacidad

Material de uso probatorio y sensible. Tené en cuenta el flujo de datos:

- **El audio nunca sale de tu máquina.** La transcripción (WhisperX + diarización)
  corre 100% local.
- **El texto sí se envía a la API de Anthropic** en las etapas `clean`, `summarize`
  y `narrate`. Si necesitás que **nada** salga de la máquina, usá solo
  `conversa transcribe` (transcripción cruda, sin LLM). Revisá la política de
  retención de datos de la API de Anthropic para tu caso.
- **Secretos:** `HF_TOKEN` y `ANTHROPIC_API_KEY` van en variables de entorno o en
  `.env` (excluido por `.gitignore`). Preferí variables de entorno y ejecutá la
  herramienta en directorios de confianza (un `.env` ajeno podría inyectar otra
  API key).
- **Revisá siempre las salidas.** La transcripción es automática (errores de ASR) y
  el LLM puede ser influido por el propio contenido del audio (prompt injection).
  Para evidencia, la prueba primaria es la grabación; apoyate en el `.srt` con
  timestamps para cotejar cifras y frases clave.

## Próximos pasos

- Manifiesto de procedencia (modelo/versión/hash por salida) para cadena de custodia.
- Flag `--local-only` / consentimiento explícito antes de enviar texto al LLM.
- Interfaz gráfica para usuarios no técnicos.
