"""Day 4: teach durable Argus sessions, torn-tail tolerance, and crash repair."""

import json
import os
import re
import time

SESSION_DIR = ".argus/sessions"


def _session_directory(workdir):
    """Return the real session directory for a workspace."""
    return os.path.join(os.path.realpath(workdir), SESSION_DIR)


def _slugify(label):
    """Convert a session label to a short filesystem-safe slug."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", label).strip("-").lower()
    return slug[:40] or "session"


def new_session(workdir, label="session"):
    """Create and return a timestamped JSONL session path."""
    directory = _session_directory(workdir)
    os.makedirs(directory, exist_ok=True)
    filename = f"{int(time.time())}-{_slugify(label)}.jsonl"
    path = os.path.join(directory, filename)
    open(path, "a", encoding="utf-8").close()
    return path


def append(path, message):
    """Append one JSON message to a session file."""
    with open(path, "a", encoding="utf-8") as session_file:
        session_file.write(json.dumps(message, ensure_ascii=False) + "\n")


def load(path):
    """Load a session, stopping at a torn tail and repairing interrupted calls."""
    messages = []
    with open(path, encoding="utf-8") as session_file:
        for line in session_file:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                break
    assistant_index = next(
        (index for index in range(len(messages) - 1, -1, -1)
         if messages[index].get("role") == "assistant"),
        None,
    )
    if assistant_index is None:
        return messages
    assistant = messages[assistant_index]
    tool_messages = sum(
        1 for message in messages[assistant_index + 1:] if message.get("role") == "tool"
    )
    calls = assistant.get("tool_calls", [])
    for call in calls[tool_messages:]:
        messages.append({
            "role": "tool",
            "name": call.get("name", ""),
            "text": "Interrupted before this ran (process restarted).",
        })
    return messages


def latest(workdir):
    """Return the newest session path, or None when no sessions exist."""
    directory = _session_directory(workdir)
    if not os.path.isdir(directory):
        return None
    paths = [
        os.path.join(directory, name)
        for name in os.listdir(directory)
        if name.endswith(".jsonl")
    ]
    return max(paths, key=os.path.getmtime) if paths else None
