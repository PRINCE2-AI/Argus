"""Shared provider contract, HTTP transport, and message helpers."""

import json
import time
import urllib.error
import urllib.request
import uuid

from .. import config

USER_AGENT = "argus-harness/0.2.0"


class ProviderError(RuntimeError):
    """Report a provider failure with an optional HTTP status."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class Provider:
    """Base class for model providers using a neutral message format."""

    name = "provider"
    default_model = ""
    default_base_url = ""
    model_envs = ("ARGUS_MODEL",)
    base_url_envs = ("ARGUS_BASE_URL",)
    api_key_envs = ()
    api_key_required = True

    def __init__(self, model=None, api_key=None, base_url=None, timeout=600,
                 temperature=0.4, max_tokens=None, transport=None):
        config.load_env_file()
        self.model = model or config.first_env(*self.model_envs) or self.default_model
        self.api_key = api_key or config.first_env(*self.api_key_envs)
        self.base_url = (
            base_url
            or config.first_env(*self.base_url_envs)
            or self.default_base_url
        ).rstrip("/")
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.transport = transport or http_post_json
        self.extra_headers = {}

    def require_api_key(self):
        """Return the key or raise a provider error with setup guidance."""
        if self.api_key_required and not self.api_key:
            raise ProviderError(
                f"Set {self.api_key_envs[0]} (or ARGUS_API_KEY) for {self.name}."
            )
        return self.api_key

    def complete(self, system, messages, tools):
        """Return normalized text, tool calls, usage, and finish reason."""
        raise NotImplementedError


def http_post_json(url, payload, headers, timeout=600, retries=5):
    """POST JSON with bounded retries and normalized provider errors."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    request_headers.update(headers)
    for attempt in range(retries):
        request = urllib.request.Request(
            url, data=data, headers=request_headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as error:
                    raise ProviderError(
                        f"{url} returned invalid JSON: {error}"
                    ) from error
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            retryable = error.code in {408, 409, 429, 500, 502, 503, 504}
            if retryable and attempt < retries - 1:
                time.sleep(_retry_delay(error, attempt))
                continue
            raise ProviderError(
                f"HTTP {error.code} from {url}: {detail}", status=error.code
            ) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            if attempt < retries - 1:
                time.sleep(min(2 ** attempt * 2, 60))
                continue
            raise ProviderError(f"Request to {url} failed: {error}") from error
    raise ProviderError(f"Request to {url} failed after retries")


def _retry_delay(error, attempt):
    """Honor Retry-After when a provider supplies it."""
    try:
        value = error.headers.get("Retry-After") if error.headers else None
        if value:
            return min(float(value), 60.0)
    except (TypeError, ValueError):
        pass
    return min(2 ** attempt * 2, 60)


def ensure_call_ids(messages):
    """Give every assistant tool call an id and pair tool results with it."""
    pending = []
    for message in messages:
        role = message.get("role")
        if role == "assistant":
            pending = []
            for call in message.get("tool_calls") or []:
                if not call.get("id"):
                    call["id"] = f"call_{uuid.uuid4().hex[:12]}"
                pending.append(call["id"])
        elif role == "tool":
            if not message.get("call_id"):
                if pending:
                    message["call_id"] = pending.pop(0)
                elif message.get("name"):
                    message["call_id"] = f"call_{message['name']}"
            elif pending and pending[0] == message["call_id"]:
                pending.pop(0)


def usage_dict(input_tokens=0, output_tokens=0, extra=None):
    """Normalize token usage across providers."""
    usage = {"input": int(input_tokens or 0), "output": int(output_tokens or 0)}
    if extra:
        for key, value in extra.items():
            if value:
                usage[key] = int(value)
    usage["total"] = usage.get("total") or usage["input"] + usage["output"]
    return usage
