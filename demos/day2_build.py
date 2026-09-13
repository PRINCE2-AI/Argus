"""Day 2: teach a policy-controlled build agent in a confined scratch tree."""

import tempfile

from argus.loop import run
from argus.security import Policy
from argus.tools import core_tools


def on_event(kind, payload):
    """Print the build transcript and tool outcomes."""
    if kind == "assistant":
        print(f"assistant: {payload['text'] or payload['tool_calls']}")
    elif kind == "tool_start":
        print(f"tool start: {payload['name']} {payload.get('args', {})}")
    else:
        print(f"tool end: {payload['result']}")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="argus-day2-") as workdir:
        tools = {item.name: item for item in core_tools(workdir)}
        policy = Policy("yolo")
        run(
            "You are a careful coding assistant. Use tools to complete the task.",
            [{"role": "user", "text": "Create fib.py with an iterative fib(n), a __main__ printing fib(30), run it and confirm the output is 832040"}],
            tools,
            model="gemini-3.1-flash-lite",
            on_event=on_event,
            before_tool=policy.check,
        )
