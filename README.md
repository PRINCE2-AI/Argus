# Argus

Argus is a small, standard-library-only Python agent harness built incrementally
over several days. It supports Gemini tool calling, confined filesystem tools,
safety policies, context compaction, durable memory, skills, sessions, and
sub-agents.

## Requirements

- Python 3.10+
- No third-party Python packages
- A Gemini API key for live Gemini requests

## Setup

Create a local `.env` file in the repository root:

```text
ARGUS_API_KEY=your-gemini-api-key
```

The `.env` file is ignored by Git and must never be committed. Argus also
accepts the `GEMINI_API_KEY` environment variable.

## Run

Run the current CLI stub:

```powershell
python -m argus
```

Run the Day 1 dice demo:

```powershell
python -m demos.day1_dice
```

For free-tier Gemini access, a Flash model can be selected in code or through
the `ARGUS_MODEL` environment variable:

```powershell
$env:ARGUS_MODEL = "gemini-3.1-flash-lite"
```

## Use the harness

```python
from argus import Harness

harness = Harness(
    workdir=".",
    model="gemini-3.1-flash-lite",
)
answer = harness.run("Create a short project status file and verify it.")
print(answer)
```

The harness provides:

- `read_file`, `write_file`, `edit_file`, `bash`, `list_files`, and `grep`
- Working-directory path confinement
- Safe, read-only, and yolo policies
- `ARGUS.md` project memory
- Skill discovery from `skills/<name>/SKILL.md`
- JSONL sessions under `.argus/sessions`
- Session resume and interrupted-tool repair
- Context compaction through the `before_turn` loop hook
- Bounded `spawn_agent` delegation

## Project layout

```text
argus/
  context.py
  harness.py
  loop.py
  memory.py
  provider.py
  security.py
  session.py
  skills.py
  subagent.py
  tools.py
demos/
  day1_dice.py
```

## Safety notes

Argus tools are confined to the configured working directory. Destructive shell
patterns such as `rm -rf`, `sudo`, filesystem formatting, forced Git pushes,
and writes to `/dev/sd*` are blocked by the safety policy.

Do not commit `.env`, API keys, session data, or other secrets.
