"""OpenAI-compatible provider, including OpenRouter, Groq, and Ollama."""

import json

from .base import (
    USER_AGENT,
    Provider,
    ProviderError,
    ensure_call_ids,
    usage_dict,
)


class OpenAICompatibleProvider(Provider):
    """Call any OpenAI-compatible chat completions endpoint."""

    name = "openai"
    default_model = "gpt-4o-mini"
    default_base_url = "https://api.openai.com/v1"
    model_envs = ("OPENAI_MODEL", "ARGUS_MODEL")
    base_url_envs = ("OPENAI_BASE_URL", "ARGUS_BASE_URL")
    api_key_envs = ("OPENAI_API_KEY", "ARGUS_API_KEY")

    def complete(self, system, messages, tools):
        key = self.require_api_key()
        ensure_call_ids(messages)
        body = {
            "model": self.model,
            "messages": self.to_wire(system, messages),
        }
        if not self._is_reasoning_model():
            body["temperature"] = self.temperature
        if self.max_tokens:
            if self._is_reasoning_model():
                body["max_completion_tokens"] = self.max_tokens
            else:
                body["max_tokens"] = self.max_tokens
        if tools:
            body["tools"] = [
                {"type": "function", "function": tool} for tool in tools
            ]
        headers = {
            "Authorization": f"Bearer {key}",
            "User-Agent": USER_AGENT,
        }
        headers.update(self.extra_headers)
        response = self.transport(
            f"{self.base_url}/chat/completions",
            body,
            headers,
            timeout=self.timeout,
        )
        return self.parse(response)

    def _is_reasoning_model(self):
        model = self.model.lower()
        return model.startswith(("o1", "o3", "o4", "o5", "gpt-5"))

    @staticmethod
    def to_wire(system, messages):
        """Translate neutral messages into OpenAI chat messages."""
        wire = [{"role": "system", "content": system}]
        for message in messages:
            role = message.get("role")
            if role == "user":
                if message.get("text"):
                    wire.append({"role": "user", "content": message["text"]})
            elif role == "assistant":
                item = {
                    "role": "assistant",
                    "content": message.get("text") or None,
                }
                calls = []
                for call in message.get("tool_calls") or []:
                    calls.append(
                        {
                            "id": call.get("id"),
                            "type": "function",
                            "function": {
                                "name": call.get("name", ""),
                                "arguments": json.dumps(
                                    call.get("args", {}), ensure_ascii=False
                                ),
                            },
                        }
                    )
                if calls:
                    item["tool_calls"] = calls
                if item["content"] is None and not calls:
                    item["content"] = ""
                wire.append(item)
            elif role == "tool":
                wire.append(
                    {
                        "role": "tool",
                        "tool_call_id": message.get("call_id")
                        or message.get("name", ""),
                        "content": message.get("text", ""),
                    }
                )
        return wire

    @staticmethod
    def parse(response):
        """Normalize an OpenAI-compatible response."""
        if response.get("error"):
            error = response["error"]
            message = error.get("message") if isinstance(error, dict) else error
            raise ProviderError(f"Provider error: {message}")
        choices = response.get("choices") or []
        if not choices:
            raise ProviderError("Provider returned no choices")
        choice = choices[0]
        message = choice.get("message") or {}
        text = message.get("content")
        if isinstance(text, list):
            text = "".join(
                part.get("text", "")
                for part in text
                if isinstance(part, dict) and part.get("type") in {"text", "output_text"}
            )
        text = text or ""
        calls = []
        for item in message.get("tool_calls") or []:
            function = item.get("function") or {}
            raw_args = function.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            calls.append(
                {
                    "id": item.get("id") or "",
                    "name": function.get("name", ""),
                    "args": args,
                }
            )
        usage = response.get("usage") or {}
        return {
            "text": text,
            "tool_calls": calls,
            "usage": usage_dict(
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
                {"total": usage.get("total_tokens", 0)},
            ),
            "finish_reason": (choice.get("finish_reason") or "stop").lower(),
        }


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter's multi-model gateway."""

    name = "openrouter"
    default_model = "openai/gpt-4o-mini"
    default_base_url = "https://openrouter.ai/api/v1"
    model_envs = ("OPENROUTER_MODEL", "ARGUS_MODEL")
    base_url_envs = ("OPENROUTER_BASE_URL", "ARGUS_BASE_URL")
    api_key_envs = ("OPENROUTER_API_KEY", "ARGUS_API_KEY")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra_headers = {
            "HTTP-Referer": "https://github.com/PRINCE2-AI/Argus",
            "X-Title": "Argus",
        }


class GroqProvider(OpenAICompatibleProvider):
    """Groq's OpenAI-compatible endpoint."""

    name = "groq"
    default_model = "llama-3.3-70b-versatile"
    default_base_url = "https://api.groq.com/openai/v1"
    model_envs = ("GROQ_MODEL", "ARGUS_MODEL")
    base_url_envs = ("GROQ_BASE_URL", "ARGUS_BASE_URL")
    api_key_envs = ("GROQ_API_KEY", "ARGUS_API_KEY")


class OllamaProvider(OpenAICompatibleProvider):
    """Local Ollama models through its OpenAI-compatible endpoint."""

    name = "ollama"
    default_model = "llama3.2"
    default_base_url = "http://localhost:11434/v1"
    model_envs = ("OLLAMA_MODEL", "ARGUS_MODEL")
    base_url_envs = ("OLLAMA_BASE_URL", "ARGUS_BASE_URL")
    # Deliberately excludes ARGUS_API_KEY: never send a cloud key to localhost.
    api_key_envs = ("OLLAMA_API_KEY",)
    api_key_required = False

    def require_api_key(self):
        """Ollama usually runs without authentication."""
        return self.api_key or "ollama"
