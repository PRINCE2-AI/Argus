"""The agent turn loop with explicit tool-error containment."""

from .providers import Provider, ensure_call_ids, get_provider


def run(
    system,
    messages,
    tools,
    *,
    provider=None,
    model=None,
    max_turns=10,
    on_event=None,
    before_tool=None,
    before_turn=None,
):
    """Run model/tool turns and return the final assistant text."""
    if isinstance(provider, str):
        provider = get_provider(provider, model=model)
    elif provider is None:
        provider = get_provider(model=model)
    elif not isinstance(provider, Provider):
        raise TypeError("provider must be a Provider instance, a name, or None")
    on_event = on_event or (lambda kind, payload: None)
    before_tool = before_tool or (lambda call: None)
    ensure_call_ids(messages)
    tool_specs = [tool.spec["schema"] for tool in tools.values()]

    turns = max(1, int(max_turns))
    for _ in range(turns):
        if before_turn:
            replacement = before_turn(messages)
            if replacement is not None:
                messages[:] = replacement
        reply = provider.complete(system, messages, tool_specs)
        on_event("usage", reply.get("usage", {}))
        assistant = {
            "role": "assistant",
            "text": reply.get("text", ""),
            "tool_calls": reply.get("tool_calls", []),
            "finish_reason": reply.get("finish_reason", "stop"),
        }
        messages.append(assistant)
        on_event("assistant", assistant)
        if not assistant["tool_calls"]:
            return assistant["text"]

        for call in assistant["tool_calls"]:
            on_event("tool_start", call)
            reason = before_tool(call)
            if reason:
                result = f"BLOCKED: {reason}"
            else:
                tool = tools.get(call.get("name", ""))
                if tool is None:
                    result = f"ERROR: unknown tool {call.get('name', '')}"
                else:
                    args = call.get("args") or {}
                    if not isinstance(args, dict):
                        args = {}
                    try:
                        result = str(tool.run(**args))
                    except Exception as error:
                        result = f"ERROR: {type(error).__name__}: {error}"
            messages.append(
                {
                    "role": "tool",
                    "name": call.get("name", ""),
                    "call_id": call.get("id", ""),
                    "text": result,
                }
            )
            on_event("tool_end", {"call": call, "result": result})

    on_event("turn_limit", {"turns": turns})
    messages.append({"role": "user", "text": "Turn limit reached; wrap up now."})
    if before_turn:
        replacement = before_turn(messages)
        if replacement is not None:
            messages[:] = replacement
    reply = provider.complete(system, messages, [])
    on_event("usage", reply.get("usage", {}))
    assistant = {
        "role": "assistant",
        "text": reply.get("text", ""),
        "tool_calls": [],
        "finish_reason": reply.get("finish_reason", "stop"),
    }
    messages.append(assistant)
    on_event("assistant", assistant)
    return assistant["text"]
