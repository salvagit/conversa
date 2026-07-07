# Plan — Visibilidad: LICENSE, topics de GitHub, publicación en PyPI

_Fecha: 2026-07-07_

## Contexto

`conversa` es público en `github.com/salvagit/conversa` pero invisible: sin
licencia, sin topics, y solo instalable clonando el repo. "SEO" tradicional
no aplica a una herramienta de consola — la visibilidad acá se juega en
señales que entiende GitHub (licencia, topics, CI) y en estar donde la gente
instala paquetes (PyPI). Se prioriza esto sobre otras acciones (badges, demo,
awesome-lists, redes) que se evalúan después.

## Hallazgo bloqueante: nombre en PyPI

El nombre **`conversa` ya está tomado** en PyPI (paquete no relacionado, de
conversión de unidades). Verificado libres: `conversa-cli`,
`conversa-transcribe`, `conversa-evidence`.

Esto **no afecta al usuario final**: `[project.scripts]` define el comando
`conversa` de forma independiente del nombre de distribución (`[project]
name`). Cambiar el nombre de distribución para PyPI no cambia que el comando
siga siendo `conversa` una vez instalado.

## Decisiones (ya tomadas por el usuario, 2026-07-07)

1. **Nombre de distribución en PyPI: `conversa-transcribe`.** El comando que
   escribe el usuario final sigue siendo `conversa` (no cambia).
2. **Cuenta de PyPI: no existe todavía, hay que crearla.** Bloquea solo el
   paso 3.4 (configurar Trusted Publisher); el resto del código se prepara
   igual sin necesitar la cuenta.
3. **Método de publicación: Trusted Publisher** (OIDC de GitHub Actions →
   PyPI), sin tokens ni secrets. Evita repetir el problema de la API key de
   Anthropic compartida en texto plano.

## Fase 1 — LICENSE (sin dependencias, se puede hacer ya)

- Agregar `LICENSE` en la raíz del repo: texto MIT estándar, copyright
  "Salvador", año 2026 (coincide con `pyproject.toml: license = {text="MIT"}`).
- Verificar que GitHub detecta la licencia (aparece en la barra lateral del repo).

## Fase 2 — Topics de GitHub (sin dependencias, se puede hacer ya)

- `gh repo edit salvagit/conversa --add-topic <topic>` para cada uno:
  `cli`, `transcription`, `speech-to-text`, `whisper`, `whisperx`,
  `speaker-diarization`, `anthropic`, `claude`, `legal-tech`, `evidence`,
  `python`.
- Verificar con `gh repo view --json repositoryTopics`.

## Fase 3 — Publicación en PyPI (requiere decisiones del usuario arriba)

3.1. **Metadata de `pyproject.toml`** para descubribilidad en PyPI:
   - Cambiar `[project] name` al nombre de distribución elegido (el
     `[project.scripts] conversa = ...` NO cambia).
   - Agregar `keywords` (transcription, whisper, diarization, evidence, cli,
     spanish, anthropic, claude).
   - Agregar `classifiers` (Development Status, Intended Audience, License ::
     OSI Approved :: MIT, Programming Language :: Python :: 3.11/3.12,
     Topic :: Multimedia :: Sound/Audio :: Speech, Environment :: Console).
   - Agregar `[project.urls]` (Repository, Issues) apuntando a
     `github.com/salvagit/conversa`.

3.2. **CI mínimo** (`.github/workflows/test.yml`): correr `pytest` en cada
   push/PR. Barato (ya hay 22 tests livianos, sin whisperx) y da una señal de
   confianza real (badge verde) para cualquiera que llegue al repo.

3.3. **Workflow de publicación** (`.github/workflows/publish.yml`): build con
   `python -m build`, publish vía `pypa/gh-action-pypi-publish` usando Trusted
   Publisher (sin secrets), disparado por tags `v*.*.*`.

3.4. **Configurar Trusted Publisher en pypi.org** (acción manual del usuario:
   crear cuenta si no existe, ir a "Publishing" → agregar repo
   `salvagit/conversa`, workflow `publish.yml`, environment opcional).

3.5. **Primer release**: tag `v0.1.0` → dispara el workflow → publica en PyPI.
   Verificar `pip install <nombre-elegido>` funciona en un venv limpio y expone
   el comando `conversa`.

3.6. Actualizar `README.md`: instrucciones de instalación pasan a
   `pip install <nombre-elegido>` como opción principal, con "desde código
   fuente" como alternativa para desarrollo.

## Estado (2026-07-07)

- ✅ Fase 1 (LICENSE), Fase 2 (topics), Fase 3.1-3.3 (metadata, CI, workflow de
  publicación) hechas, commiteadas (`8adc173`) y pusheadas. CI corrido y
  **verde en GitHub** (no solo local).
- 🐛 Encontrado y arreglado en el camino: `python -m build` fallaba
  (`force-include` de prompts duplicaba archivos). No lo detectaba
  `pip install -e .` porque usa un code path distinto. Verificado con un
  build real + instalación del wheel en venv limpio: `conversa --version`
  y los prompts cargan bien.
- ⏳ Pendiente, bloqueado por acción del usuario: 3.4 (cuenta de PyPI +
  Trusted Publisher) y 3.5/3.6 (primer release + actualizar README).

## Verificación

- `LICENSE` presente y detectado por GitHub.
- Topics visibles en `gh repo view --json repositoryTopics`.
- CI verde en un push de prueba.
- `pip install <nombre-elegido>` en un venv limpio (o Docker) instala y
  `conversa --version` funciona.
- README refleja el nuevo método de instalación.

## Fuera de alcance (para después)

Badges en el README, GIF de demo, listas "awesome-*", publicación en foros/redes
(Show HN, Reddit, etc.) — se retoman una vez esto esté andando.
