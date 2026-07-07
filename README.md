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

## Próximos pasos

- Manifiesto de procedencia (modelo/versión/hash por salida) para cadena de custodia.
- Interfaz gráfica para usuarios no técnicos.
