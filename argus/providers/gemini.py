"""Google Gemini provider."""

import uuid

from .base import USER_AGENT, Provider, ProviderError, usage_dict


class GeminiProvider(Provider):
    """Call the Gemini generateContent API."""

    name = "gemini"
    default_model = "gemini-3.1-pro-preview"
    default_base_url = "https://generativelanguage.googleapis.com/v1beta"
    model_envs = ("GEMINI_MODEL", "ARGUS_MODEL")
    base_url_envs = ("GEMINI_BASE_URL", "ARGUS_BASE_URL")
    api_key_envs = ("GEMINI_API_KEY", "ARGUS_API_KEY")

    def complete(self, system, messages, tools):
        key = self.require_api_key()
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": self.to_wire(messages),
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens or 65536,
            },
        }
        if tools:
            body["tools"] = [{"functionDeclarations": tools}]
        response = self.transport(
            f"{self.base_url}/models/{self.model}:generateContent",
            body,
            {"x-goog-api-key": key, "User-Agent": USER_AGENT},
            timeout=self.timeout,
        )
        return self.parse(response)

    @staticmethod
    def to_wire(messages):
        """Translate neutral messages into Gemini contents."""
        contents = []
        for message in messages:
            role = message.get("role")
            if role == "user":
                if message.get("text"):
                    contents.append(
                        {"role": "user", "parts": [{"text": message["text"]}]}
                    )
            elif role == "assistant":
                parts = []
                if message.get("text"):
                    parts.append({"text": message["text"]})
                for call in message.get("tool_calls") or []:
                    part = {
                        "functionCall": {
                            "name": call["name"],
                            "args": call.get("args", {}),
                        }
                    }
                    # Gemini 3 requires the model's thought signature to round-trip.
                    if call.get("signature") is not None:
                        part["thoughtSignature"] = call["signature"]
                    parts.append(part)
                if parts:
                    contents.append({"role": "model", "parts": parts})
            elif role == "tool":
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": message["name"],
                                    "response": {"result": message.get("text", "")},
                                }
                            }
                        ],
                    }
                )
        return contents

    @staticmethod
    def parse(response):
        """Normalize a Gemini response and surface safety blocks."""
        feedback = response.get("promptFeedback") or {}
        if feedback.get("blockReason"):
            reason = feedback.get("blockReasonMessage") or feedback["blockReason"]
            raise ProviderError(f"Gemini blocked the prompt: {reason}")
        candidates = response.get("candidates") or []
        if not candidates:
            raise ProviderError("Gemini returned no candidates")
        candidate = candidates[0]
        finish = (candidate.get("finishReason") or "STOP").upper()
        parts = (candidate.get("content") or {}).get("parts") or []
        text_parts = []
        tool_calls = []
        for part in parts:
            if part.get("thought"):
                continue
            if "text" in part:
                text_parts.append(part["text"])
            if "functionCall" in part:
                call = part["functionCall"]
                tool_calls.append(
                    {
                        "id": call.get("id")
                        or f"call_{uuid.uuid4().hex[:12]}",
                        "name": call.get("name", ""),
                        "args": call.get("args") or {},
                        "signature": part.get("thoughtSignature"),
                    }
                )
        if finish in {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"}:
            raise ProviderError(f"Gemini stopped the response: {finish}")
        usage = response.get("usageMetadata") or {}
        return {
            "text": "".join(text_parts),
            "tool_calls": tool_calls,
            "usage": usage_dict(
                usage.get("promptTokenCount", 0),
                usage.get("candidatesTokenCount", 0),
                {
                    "cached": usage.get("cachedContentTokenCount", 0),
                    "thought": usage.get("thoughtsTokenCount", 0),
                    "total": usage.get("totalTokenCount", 0),
                },
            ),
            "finish_reason": finish.lower() or "stop",
        }
