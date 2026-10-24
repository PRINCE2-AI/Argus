"""Transcript budgeting, factual compaction, and safe turn history."""

from .providers import get_provider

CHARS_PER_TOKEN = 4
KEEP_RECENT = 6
SUMMARY_MARKER = "[Conversation so far, compacted]"
SUMMARY_SYSTEM = (
    "You compress agent transcripts. Preserve: the original task, every file "
    "created or edited and its purpose, key decisions, unresolved errors, and "
    "what remains to be done. Be dense and factual."
)


def estimate_tokens(messages):
    """Estimate token usage from the string representation of messages."""
    return sum(len(str(message)) for message in messages) / CHARS_PER_TOKEN


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


def compact(provider, messages, budget_tokens):
    """Replace older turns with a dense summary when the budget is exceeded."""
    if isinstance(provider, str) or provider is None:
        provider = get_provider(model=provider)
    if (
        estimate_tokens(messages) <= budget_tokens
        or len(messages) <= KEEP_RECENT + 1
    ):
        return messages
    old = messages[:-KEEP_RECENT]
    recent = list(messages[-KEEP_RECENT:])
    summary_reply = provider.complete(
        SUMMARY_SYSTEM,
        [{"role": "user", "text": _transcript(old)}],
        [],
    )
    summary = (summary_reply.get("text") or "").strip()
    if not summary:
        return messages
    while recent and recent[0].get("role") == "tool":
        recent.pop(0)
    summary_message = {
        "role": "user",
        "text": f"{SUMMARY_MARKER}\n{summary}",
        "meta": {"compaction": True, "replaced": len(old)},
    }
    return [summary_message] + recent
