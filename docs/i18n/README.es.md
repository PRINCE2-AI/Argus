# Argus

**Un pequeño e inspeccionable arnés de agentes en Python para trabajo real dentro de un solo directorio.**

[English](../../README.md) · **Español** · [हिन्दी](README.hi.md) · [Français](README.fr.md)

Argus conecta un modelo de lenguaje con un conjunto acotado de herramientas de
espacio de trabajo, mantiene cada acción dentro de un límite de rutas, guarda
sesiones duraderas y convierte las decisiones de seguridad en código legible.
Soporta seis proveedores de modelos, cuatro idiomas de interfaz y no tiene
dependencias de ejecución.

## Por qué Argus

- **Superficie pequeña.** Cada límite —proveedor, bucle, herramientas, política,
  sesiones, compactación— se puede leer en una sola sesión.
- **Seguridad explícita.** Lista de comandos denegados, cárcel de rutas, flujo de
  aprobación, redacción de secretos y revisión semántica opcional que falla de
  forma segura.
- **Sesiones resistentes.** Recupera escrituras incompletas, repara llamadas de
  herramientas interrumpidas y restaura resúmenes de compactación.
- **Independiente del proveedor.** Gemini, Anthropic, OpenAI, OpenRouter, Groq y
  Ollama local comparten un formato de mensajes neutral.
- **Cero dependencias en tiempo de ejecución.** Solo la biblioteca estándar de
  Python 3.10+.

## Inicio rápido

Requisitos: Python 3.10 o superior y una clave de API, o un modelo local de
Ollama.

```bash
git clone https://github.com/PRINCE2-AI/Argus.git
cd Argus
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env             # Windows: copy .env.example .env
```

Añade una clave a `.env`:

```dotenv
GEMINI_API_KEY=tu-clave
```

Ejecuta una tarea:

```bash
argus                                                  # interactivo
argus --prompt "Crea hello.py, ejecútalo e informa del resultado" --yes
argus --prompt "Resume este repositorio" --mode read-only
argus --resume                                         # sesión más reciente
argus --list-sessions
argus --lang es
```

## Proveedores

| Proveedor | `--provider` | Clave de API |
| --- | --- | --- |
| Google Gemini | `gemini` | `GEMINI_API_KEY` o `ARGUS_API_KEY` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` o `ARGUS_API_KEY` |
| OpenAI | `openai` | `OPENAI_API_KEY` o `ARGUS_API_KEY` |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` o `ARGUS_API_KEY` |
| Groq | `groq` | `GROQ_API_KEY` o `ARGUS_API_KEY` |
| Ollama local | `ollama` | ninguna |

Usa `--model` o `ARGUS_MODEL` para cambiar el modelo. Ollama ignora
deliberadamente `ARGUS_API_KEY` para no enviar credenciales de la nube a
localhost.

## API de Python

```python
from argus import Harness, Policy

harness = Harness(
    workdir=".",
    provider="gemini",
    model="gemini-3.1-flash-lite",
    policy=Policy("safe"),
)
print(harness.run("Crea un archivo de estado y verifícalo."))
```

También puedes añadir herramientas con `@tool` y pasarlas en `extra_tools`.

## Modelo de seguridad

| Modo | Comportamiento |
| --- | --- |
| `read-only` | Solo herramientas de lectura. |
| `safe` (predeterminado) | Las herramientas que modifican piden aprobación interactiva. |
| `yolo` | Ejecución automática, pero la lista de denegación sigue aplicándose. |

Las rutas se resuelven dentro del espacio de trabajo; `.env`, `.git` y `.argus`
están protegidos. Los comandos destructivos, la escalada de privilegios, los
shells inversos y las operaciones Git forzadas se bloquean. En modo headless,
`safe` deniega mutaciones salvo que uses `--yes`.

**Argus no es un sandbox del sistema operativo.** Para tareas no confiables, usa
un contenedor o una máquina virtual.

## Documentación

- [Arquitectura](../ARCHITECTURE.md)
- [Notas de portafolio](../PORTFOLIO.md)
- [Contribuir](../../CONTRIBUTING.md)
- [Seguridad](../../SECURITY.md)
- [Registro de cambios](../../CHANGELOG.md)

## Licencia

MIT. Consulta [LICENSE](../../LICENSE).
