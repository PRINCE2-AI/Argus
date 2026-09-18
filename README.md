# Argus

> A small, inspectable Python agent harness for real work inside one directory.

Argus is built from Python's standard library only. It connects a language
model to a small set of practical tools, keeps the model inside a workspace
boundary, records durable sessions, and makes safety decisions explicit.

The project is being built incrementally as a day-by-day reference
implementation. The goal is not to hide the agent behind a framework; it is to
make every important boundary easy to read, test, and extend.

## What Argus can do

- Call Gemini with a neutral message format and tool calls.
- Read, write, edit, list, search, and run commands in a confined workspace.
- Block dangerous shell commands through an explicit policy.
- Compact long conversations before a model turn.
- Keep project facts in `ARGUS.md`.
- Discover optional skills from `skills/<name>/SKILL.md`.
- Persist conversations as JSONL under `.argus/sessions`.
- Repair interrupted tool calls after a process restart.
- Delegate self-contained work to bounded child agents.

## Quick start

### 1. Clone and enter the repository

```powershell
git clone https://github.com/PRINCE2-AI/Argus.git
cd Argus
```

### 2. Configure a local API key

Create `.env` in the repository root:

```text
ARGUS_API_KEY=your-gemini-api-key
```

You can create a Gemini key in [Google AI Studio](https://aistudio.google.com/app/apikey).
The `.env` file is ignored by Git. Never paste an API key into source code,
commits, issues, or chat.

Argus also accepts `GEMINI_API_KEY` from the environment.

### 3. Select a model

The default model is defined by the provider. To select another available
Gemini model, set `ARGUS_MODEL`:

```powershell
$env:ARGUS_MODEL = "gemini-3.1-flash-lite"
```

### 4. Run Argus

The current module entry point is a Day 5 CLI stub:

```powershell
python -m argus
```

Run the first demo:

```powershell
python -m demos.day1_dice
```

## Python API

```python
from argus import Harness

harness = Harness(
    workdir=".",
    model="gemini-3.1-flash-lite",
)

answer = harness.run(
    "Create a short project status file and verify it."
)
print(answer)
```

`Harness` composes the provider, agent loop, tools, policy, context engine,
memory, skills, sessions, and sub-agents. A session can be resumed after a
restart:

```python
harness = Harness(workdir=".")
if harness.resume():
    print(harness.run("Continue the interrupted task."))
```

## Workspace memory

Argus stores durable project notes in `ARGUS.md`:

```python
from argus import Harness

harness = Harness(workdir=".")
harness.tools["remember"].run(
    note="The release codename is Silver Comet."
)
```

The memory is included in the next system prompt, so a fresh conversation can
use the fact without replaying the old conversation.

## Skills

Create a skill at `skills/brand-voice/SKILL.md`:

```markdown
---
description: Write concise, friendly copy
---

Use short sentences and a warm, practical tone.
```

Argus discovers the skill and exposes it through the `use_skill` tool when the
harness starts.

## Safety model

Every tool call passes through a `Policy`:

```python
from argus import Harness, Policy

harness = Harness(
    workdir=".",
    policy=Policy("safe"),
)
```

Available modes:

| Mode | Behavior |
| --- | --- |
| `read-only` | Allows only `read_file`, `list_files`, and `grep`. |
| `safe` | Requests approval for mutating tools. |
| `yolo` | Allows tools except commands matching deny patterns. |

All filesystem paths are resolved inside the configured workspace. Dangerous
patterns such as destructive `rm`, `sudo`, filesystem formatting, forced Git
pushes, and writes to block devices are denied.

## Repository layout

```text
argus/
  __init__.py       Public API
  __main__.py       Module entry point
  cli.py            CLI stub
  context.py        Conversation budgeting and compaction
  harness.py        Main composition layer
  loop.py           Model/tool turn loop
  memory.py         ARGUS.md project memory
  provider.py       Gemini HTTP client
  security.py       Tool policy and deny rules
  session.py        Durable JSONL sessions and repair
  skills.py         Skill discovery and loading
  subagent.py       Bounded child-agent delegation
  tools.py          Workspace tools and path jail
demos/
  day1_dice.py      First tool-calling demo
```

## Development

Argus targets Python 3.10+ and has no third-party runtime dependencies.
Before opening a pull request:

```powershell
python -m py_compile argus/*.py demos/*.py
git status
```

Keep secrets, `.env`, `.argus/`, `__pycache__/`, and generated workspace files
out of commits.

## Build progress

- [x] Day 1 — Provider boundary, agent loop, and dice tool
- [x] Day 2 — Workspace tools and safety policy
- [x] Day 3 — Context compaction, memory, and skills
- [x] Day 4 — Sessions, crash repair, sub-agents, and harness
- [ ] Day 5 — Full command-line interface

## License

This project is currently under active development. Add the repository's
chosen license here before publishing a release.
