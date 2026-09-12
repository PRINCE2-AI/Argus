"""Day 1: teach provider boundaries, wire formats, and resilient HTTP rules."""

import json
import time
import urllib.error
import urllib.request

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-3.1-pro-preview"


def api_key():
    """Return the configured Gemini API key or explain how to configure one."""
    import os

    key = os.environ.get("ODYSSEUS_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "Set ODYSSEUS_API_KEY (or GEMINI_API_KEY) before calling Gemini."
        )
    return key


def _to_wire(messages):
    """Translate neutral messages into Gemini contents."""
    contents = []
    for message in messages:
        role = message["role"]
        if role == "user":
            contents.append({"role": "user", "parts": [{"text": message["text"]}]})
        elif role == "assistant":
            parts = []
            if message.get("text"):
                parts.append({"text": message["text"]})
            for call in message.get("tool_calls", []):
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
            contents.append({"role": "model", "parts": parts})
        elif role == "tool":
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": message["name"],
                                "response": {"result": message["text"]},
                            }
                        }
                    ],
                }
            )
    return contents


def complete(model, system, messages, tools):
    """Call Gemini and return normalized text, tool calls, and token usage."""
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": _to_wire(messages),
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 65536},
    }
    if tools:
        body["tools"] = [{"functionDeclarations": [tool["schema"] for tool in tools]}]
    response = _post(
        f"{API_ROOT}/{model}:generateContent?key={api_key()}",
        body,
    )
    text_parts = []
    tool_calls = []
    for candidate in response.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if part.get("thought"):
                continue
            if "text" in part:
                text_parts.append(part["text"])
            if "functionCall" in part:
                function_call = part["functionCall"]
                tool_calls.append(
                    {
                        "name": function_call["name"],
                        "args": function_call.get("args", {}),
                        "signature": part.get("thoughtSignature"),
                    }
                )
    usage = response.get("usageMetadata", {})
    return {
        "text": "".join(text_parts),
        "tool_calls": tool_calls,
        "usage": {
            "input": usage.get("promptTokenCount", 0),
            "output": usage.get("candidatesTokenCount", 0),
        },
    }


def _post(url, body, retries=5):
    """POST JSON with bounded retries for transient provider failures."""
    payload = json.dumps(body).encode("utf-8")
    for attempt in range(retries):
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503):
                detail = error.read().decode("utf-8", errors="replace")[:400]
                raise RuntimeError(f"HTTP {error.code}: {detail}") from error
            if attempt == retries - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
        time.sleep(2**attempt * 2)
    raise RuntimeError("HTTP request failed after retries")
