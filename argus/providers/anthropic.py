"""Anthropic Messages API provider."""

from .base import (
    USER_AGENT,
    Provider,
    ProviderError,
    ensure_call_ids,
    usage_dict,
)


class AnthropicProvider(Provider):
    """Call the Anthropic Messages API."""

    name = "anthropic"
    default_model = "claude-sonnet-4-5"
    default_base_url = "https://api.anthropic.com/v1"
    model_envs = ("ANTHROPIC_MODEL", "ARGUS_MODEL")
    base_url_envs = ("ANTHROPIC_BASE_URL", "ARGUS_BASE_URL")
    api_key_envs = ("ANTHROPIC_API_KEY", "ARGUS_API_KEY")
    api_version = "2023-06-01"

    def complete(self, system, messages, tools):
        key = self.require_api_key()
        ensure_call_ids(messages)
        body = {
            "model": self.model,
            "system": system,
            "messages": self.to_wire(messages),
            "max_tokens": self.max_tokens or 16384,
            "temperature": self.temperature,
        }
        if tools:
            body["tools"] = [
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                }
                for tool in tools
            ]
        response = self.transport(
            f"{self.base_url}/messages",
            body,
            {
                "x-api-key": key,
                "anthropic-version": self.api_version,
                "User-Agent": USER_AGENT,
            },
            timeout=self.timeout,
        )
        return self.parse(response)

    @staticmethod
    def to_wire(messages):
        """Translate neutral messages into Anthropic content blocks."""
        wire = []
        last_role = None
        for message in messages:
            role = message.get("role")
            if role == "user":
                if message.get("text"):
                    wire.append(
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": message["text"]}],
                        }
                    )
                last_role = "user"
            elif role == "assistant":
                content = []
                if message.get("text"):
                    content.append({"type": "text", "text": message["text"]})
                for call in message.get("tool_calls") or []:
                    content.append(
                        {
                            "type": "tool_use",
                            "id": call.get("id", ""),
                            "name": call.get("name", ""),
                            "input": call.get("args", {}),
                        }
                    )
                if not content:
                    content = [{"type": "text", "text": "(no output)"}]
                wire.append({"role": "assistant", "content": content})
                last_role = "assistant"
            elif role == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": message.get("call_id")
                    or message.get("name", ""),
                    "content": message.get("text", ""),
                }
                if last_role == "tool" and wire and wire[-1]["role"] == "user":
                    wire[-1]["content"].append(block)
                else:
                    wire.append({"role": "user", "content": [block]})
                last_role = "tool"
        return wire

    @staticmethod
    def parse(response):
        """Normalize an Anthropic response."""
        if response.get("type") == "error":
            error = response.get("error") or {}
            raise ProviderError(
                f"Anthropic error: {error.get('message', 'unknown error')}"
            )
        text_parts = []
        tool_calls = []
        for block in response.get("content") or []:
            block_type = block.get("type")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            elif block_type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "args": block.get("input") or {},
                    }
                )
        usage = response.get("usage") or {}
        return {
            "text": "".join(text_parts),
            "tool_calls": tool_calls,
            "usage": usage_dict(
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
                {"cached": usage.get("cache_read_input_tokens", 0)},
            ),
            "finish_reason": (response.get("stop_reason") or "end_turn").lower(),
        }
