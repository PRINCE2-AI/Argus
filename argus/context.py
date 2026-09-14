"""Day 3: teach transcript budgeting, factual compaction, and safe turn history."""

from . import provider

CHARS_PER_TOKEN = 4
KEEP_RECENT = 6


def estimate_tokens(messages):
    """Estimate token usage from the string representation of messages."""
    return sum(len(str(message)) for message in messages) // CHARS_PER_TOKEN


def _transcript(messages):
    lines = []
    for message in messages:
        role = message.get("role", "unknown")
        name = message.get("name")
        label = f"{role} ({name})" if name else role
        text = message.get("text", "")
        calls = message.get("tool_calls", [])
        if calls:
            called = ", ".join(call.get("name", "unknown") for call in calls)
            text = f"{text} [tool calls: {called}]".strip()
        lines.append(f"{label}: {text[:2000]}")
    return "\n".join(lines)


def compact(model, messages, budget_tokens):
    """Compact older transcript messages when the requested budget is exceeded."""
    if estimate_tokens(messages) <= budget_tokens or len(messages) <= KEEP_RECENT + 1:
        return messages
    old = messages[:-KEEP_RECENT]
    recent = messages[-KEEP_RECENT:]
    summary_reply = provider.complete(
        model,
        "You compress agent transcripts. Preserve: the original task, every file "
        "created or edited and its purpose, key decisions, unresolved errors, and "
        "what remains to be done. Be dense and factual.",
        [{"role": "user", "text": _transcript(old)}],
        [],
    )
    while recent and recent[0].get("role") == "tool":
        recent.pop(0)
    summary = summary_reply["text"]
    return [{"role": "user", "text": "[Conversation so far, compacted]\n" + summary}] + recent
