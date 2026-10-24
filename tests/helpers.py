"""Shared deterministic test doubles."""

import copy

from argus.providers import Provider


class ScriptedProvider(Provider):
    """Return scripted normalized replies and record every request."""

    name = "fake"
    default_model = "fake-model"

    def __init__(self, replies=None):
        super().__init__(model="fake-model", api_key="test-key")
        self.replies = list(replies or [])
        self.requests = []

    def complete(self, system, messages, tools):
        self.requests.append(
            {
                "system": system,
                "messages": copy.deepcopy(messages),
                "tools": copy.deepcopy(tools),
            }
        )
        if self.replies:
            return self.replies.pop(0)
        return {
            "text": "done",
            "tool_calls": [],
            "usage": {"input": 1, "output": 1, "total": 2},
            "finish_reason": "stop",
        }


def reply(text="", tool_calls=None, usage=None, finish_reason="stop"):
    """Build a normalized provider reply."""
    return {
        "text": text,
        "tool_calls": list(tool_calls or []),
        "usage": usage or {"input": 1, "output": 1, "total": 2},
        "finish_reason": finish_reason,
    }


def tool_call(name, args=None, call_id="call_test"):
    """Build a normalized tool call."""
    return {"id": call_id, "name": name, "args": args or {}}
