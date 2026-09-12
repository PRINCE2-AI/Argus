"""Day 1: teach tool calling with a small dice tool and visible transcripts."""

import random

from argus.loop import run


class RollDice:
    """Roll a requested number of six-sided dice."""

    spec = {
        "schema": {
            "name": "roll_dice",
            "description": "Roll count six-sided dice",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "string", "description": "How many dice"}
                },
                "required": ["count"],
            },
        }
    }

    def run(self, **kwargs):
        """Return the individual rolls and their total."""
        count = int(kwargs["count"])
        rolls = [random.randint(1, 6) for _ in range(count)]
        return f"rolls={rolls}, total={sum(rolls)}"


def on_event(kind, payload):
    """Print each loop event as a compact transcript line."""
    if kind == "assistant":
        print(f"assistant: {payload['text'] or payload['tool_calls']}")
    elif kind == "tool_start":
        print(f"tool call: {payload['name']}({payload.get('args', {})})")
    else:
        print(f"tool result: {payload['result']}")


def before_tool(_call):
    """Allow every demo tool call."""
    return None


if __name__ == "__main__":
    task = "Roll 3 dice and tell me whether the total beats 10"
    print(f"user: {task}")
    run(
        "You are a concise dice assistant.",
        [{"role": "user", "text": task}],
        {"roll_dice": RollDice()},
        on_event=on_event,
        before_tool=before_tool,
    )
