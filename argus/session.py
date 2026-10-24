"""Durable JSONL sessions, torn-tail tolerance, compaction restore, and repair."""

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
    stamp = int(time.time())
    base = f"{stamp}-{_slugify(label)}"
    path = os.path.join(directory, f"{base}.jsonl")
    counter = 1
    while os.path.exists(path):
        path = os.path.join(directory, f"{base}-{counter}.jsonl")
        counter += 1
    open(path, "a", encoding="utf-8").close()
    return path


def append(path, message):
    """Append one JSON message to a session file."""
    with open(path, "a", encoding="utf-8") as session_file:
        session_file.write(json.dumps(message, ensure_ascii=False) + "\n")


def _drop_adjacent_duplicate_tools(messages):
    """Remove duplicate tool rows produced by the pre-0.2 persistence bug."""
    cleaned = []
    for message in messages:
        if (
            message.get("role") == "tool"
            and cleaned
            and cleaned[-1].get("role") == "tool"
            and cleaned[-1].get("name") == message.get("name")
            and cleaned[-1].get("text") == message.get("text")
            and cleaned[-1].get("call_id", "") == message.get("call_id", "")
        ):
            continue
        cleaned.append(message)
    return cleaned


def load(path):
    """Load a session, restore the last compaction, and repair interrupted calls."""
    messages = []
    with open(path, encoding="utf-8") as session_file:
        for line in session_file:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                break
    messages = _drop_adjacent_duplicate_tools(messages)
    start = 0
    for index, message in enumerate(messages):
        if (message.get("meta") or {}).get("compaction"):
            start = index
    messages = messages[start:]
    while messages and messages[0].get("role") == "tool":
        messages.pop(0)
    assistant_index = next(
        (
            index
            for index in range(len(messages) - 1, -1, -1)
            if messages[index].get("role") == "assistant"
        ),
        None,
    )
    if assistant_index is None:
        return messages
    assistant = messages[assistant_index]
    tool_messages = [
        message
        for message in messages[assistant_index + 1:]
        if message.get("role") == "tool"
    ]
    calls = assistant.get("tool_calls") or []
    answered = {
        message.get("call_id") for message in tool_messages if message.get("call_id")
    }
    if answered:
        missing = [call for call in calls if call.get("id") not in answered]
    else:
        missing = calls[len(tool_messages):]
    for call in missing:
        messages.append(
            {
                "role": "tool",
                "name": call.get("name", ""),
                "call_id": call.get("id", ""),
                "text": "Interrupted before this ran (process restarted).",
            }
        )
    return messages


def list_sessions(workdir):
    """Return saved sessions newest-first with a short task preview."""
    directory = _session_directory(workdir)
    if not os.path.isdir(directory):
        return []
    sessions = []
    for name in os.listdir(directory):
        if not name.endswith(".jsonl"):
            continue
        path = os.path.join(directory, name)
        try:
            stat = os.stat(path)
            preview = ""
            with open(path, encoding="utf-8") as session_file:
                for line in session_file:
                    try:
                        message = json.loads(line)
                    except json.JSONDecodeError:
                        break
                    if message.get("role") == "user":
                        preview = (message.get("text") or "").replace("\n", " ")[:100]
                        break
        except OSError:
            continue
        sessions.append(
            {
                "path": path,
                "name": name,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "preview": preview,
            }
        )
    return sorted(sessions, key=lambda item: item["mtime"], reverse=True)


def latest(workdir):
    """Return the newest session path, or None when no sessions exist."""
    sessions = list_sessions(workdir)
    return sessions[0]["path"] if sessions else None
