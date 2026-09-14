"""Day 3: teach durable project memory, platform context, and concise agent rules."""

import os
import platform

MEMORY_FILE = "ARGUS.md"

BASE_SYSTEM_PROMPT = """You are Argus, a small sharp coding agent working inside one directory with the tools provided.
Act, don't narrate; inspect before assuming; prefer edit_file for small changes.
Verify after building by running or re-reading; never repeat a failing call unchanged.
When complete, reply with a short summary and stop calling tools."""


def build_system_prompt(workdir, extra=""):
    """Build the system prompt with workspace identity, memory, and optional guidance."""
    real_workdir = os.path.realpath(workdir)
    sections = [
        BASE_SYSTEM_PROMPT,
        f"Platform: {platform.platform()}\nWorking directory: {real_workdir}",
    ]
    memory_path = os.path.join(real_workdir, MEMORY_FILE)
    if os.path.isfile(memory_path):
        with open(memory_path, encoding="utf-8") as memory_file:
            sections.append(f"Project memory ({MEMORY_FILE}):\n{memory_file.read()}")
    if extra:
        sections.append(extra)
    return "\n\n".join(sections)


def remember(workdir, note):
    """Append a durable project fact to the workspace memory file."""
    path = os.path.join(os.path.realpath(workdir), MEMORY_FILE)
    with open(path, "a", encoding="utf-8") as memory_file:
        memory_file.write(f"- {note}\n")
    return f"Remembered in {MEMORY_FILE}"
