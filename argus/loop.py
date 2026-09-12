"""Day 1: teach the agent turn loop and explicit tool-error containment."""

from .provider import DEFAULT_MODEL, complete


def run(
    system,
    messages,
    tools,
    *,
    model=DEFAULT_MODEL,
    max_turns=10,
    on_event=None,
    before_tool=None,
    before_turn=None,
):
    """Run model/tool turns and return the final assistant text."""
    on_event = on_event or (lambda kind, payload: None)
    before_tool = before_tool or (lambda call: None)
    tool_specs = [tool.spec for tool in tools.values()]

    for _ in range(max_turns):
        if before_turn:
            replacement = before_turn(messages)
            if replacement is not None:
                messages[:] = replacement
        reply = complete(model, system, messages, tool_specs)
        assistant = {
            "role": "assistant",
            "text": reply["text"],
            "tool_calls": reply["tool_calls"],
        }
        messages.append(assistant)
        on_event("assistant", assistant)
        if not reply["tool_calls"]:
            return reply["text"]

        for call in reply["tool_calls"]:
            on_event("tool_start", call)
            reason = before_tool(call)
            if reason:
                result = f"BLOCKED: {reason}"
            else:
                tool = tools.get(call["name"])
                if tool is None:
                    result = f"ERROR: unknown tool {call['name']}"
                else:
                    try:
                        result = str(tool.run(**call.get("args", {})))
                    except Exception as error:
                        result = f"ERROR: {type(error).__name__}: {error}"
            on_event("tool_end", {"call": call, "result": result})
            messages.append({"role": "tool", "name": call["name"], "text": result})

    messages.append({"role": "user", "text": "Turn limit reached; wrap up now."})
    if before_turn:
        replacement = before_turn(messages)
        if replacement is not None:
            messages[:] = replacement
    reply = complete(model, system, messages, [])
    assistant = {
        "role": "assistant",
        "text": reply["text"],
        "tool_calls": reply["tool_calls"],
    }
    messages.append(assistant)
    on_event("assistant", assistant)
    return reply["text"]
