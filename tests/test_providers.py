import io
import json
import unittest
import urllib.error
from unittest import mock

from argus.providers import (
    AnthropicProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    OpenRouterProvider,
    ProviderError,
    available_providers,
    ensure_call_ids,
    get_provider,
    infer_provider,
    usage_dict,
)
from argus.providers.base import http_post_json


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def capture_transport(response):
    calls = []

    def transport(url, payload, headers, timeout=None):
        calls.append(
            {"url": url, "payload": payload, "headers": headers, "timeout": timeout}
        )
        return response

    return transport, calls


class RegistryTests(unittest.TestCase):
    def test_available_providers(self):
        self.assertEqual(
            available_providers(),
            ["anthropic", "gemini", "groq", "ollama", "openai", "openrouter"],
        )

    def test_infer_provider_from_settings_and_model_names(self):
        def no_env(name, default=None):
            return default

        with mock.patch("argus.providers.config.env", side_effect=no_env):
            self.assertEqual(infer_provider(), "gemini")
            self.assertEqual(infer_provider(model="claude-sonnet-4-5"), "anthropic")
            self.assertEqual(infer_provider(model="gpt-4o-mini"), "openai")
            self.assertEqual(infer_provider(model="o3-mini"), "openai")
            self.assertEqual(infer_provider(model="openai/gpt-4o"), "openrouter")
            self.assertEqual(infer_provider(model="gemini-2.5-pro"), "gemini")
            self.assertEqual(
                infer_provider(model="local", base_url="http://localhost"), "openai"
            )

        def configured(name, default=None):
            return {"ARGUS_PROVIDER": "google"}.get(name, default)

        with mock.patch("argus.providers.config.env", side_effect=configured):
            self.assertEqual(infer_provider(model="gpt-4o"), "gemini")

    def test_get_provider_by_name_and_alias(self):
        provider = get_provider("google", model="gemini-2.5-pro", api_key="k")
        self.assertIsInstance(provider, GeminiProvider)
        self.assertEqual(provider.name, "gemini")

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(ProviderError):
            get_provider("does-not-exist")

    def test_ollama_needs_no_api_key(self):
        provider = get_provider("ollama", base_url="http://localhost:11434/v1")
        self.assertIsInstance(provider, OllamaProvider)
        self.assertNotIn("ARGUS_API_KEY", OllamaProvider.api_key_envs)
        provider.api_key = None
        self.assertEqual(provider.require_api_key(), "ollama")


class OpenAITests(unittest.TestCase):
    def test_request_body_and_tool_translation(self):
        transport, calls = capture_transport(
            {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
        )
        provider = OpenAICompatibleProvider(
            model="gpt-4o-mini", api_key="secret",
            base_url="https://api.test/v1", transport=transport,
        )
        messages = [
            {"role": "user", "text": "hi"},
            {
                "role": "assistant",
                "text": "calling",
                "tool_calls": [{"id": "c1", "name": "echo", "args": {"text": "x"}}],
            },
            {"role": "tool", "name": "echo", "call_id": "c1", "text": "done"},
        ]
        provider.complete("system", messages, [{"name": "echo"}])
        request = calls[0]
        self.assertEqual(request["url"], "https://api.test/v1/chat/completions")
        self.assertEqual(request["headers"]["Authorization"], "Bearer secret")
        body = request["payload"]
        self.assertEqual(body["temperature"], 0.4)
        self.assertEqual(body["messages"][0], {"role": "system", "content": "system"})
        self.assertEqual(body["messages"][1], {"role": "user", "content": "hi"})
        assistant = body["messages"][2]
        self.assertEqual(assistant["tool_calls"][0]["function"]["name"], "echo")
        self.assertEqual(
            json.loads(assistant["tool_calls"][0]["function"]["arguments"]),
            {"text": "x"},
        )
        self.assertEqual(body["messages"][3]["tool_call_id"], "c1")
        self.assertEqual(body["tools"], [{"type": "function", "function": {"name": "echo"}}])

    def test_reasoning_models_use_completion_tokens(self):
        transport, calls = capture_transport(
            {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
        )
        provider = OpenAICompatibleProvider(
            model="o3-mini", api_key="secret",
            base_url="https://api.test/v1", max_tokens=256, transport=transport,
        )
        provider.complete("system", [], [])
        body = calls[0]["payload"]
        self.assertEqual(body["max_completion_tokens"], 256)
        self.assertNotIn("max_tokens", body)
        self.assertNotIn("temperature", body)

    def test_openrouter_sets_attribution_headers(self):
        transport, calls = capture_transport({"choices": []})
        provider = OpenRouterProvider(
            model="openai/gpt-4o-mini", api_key="secret",
            base_url="https://api.test/v1", transport=transport,
        )
        with self.assertRaises(ProviderError):
            provider.complete("system", [], [])
        self.assertEqual(calls[0]["headers"]["X-Title"], "Argus")
        self.assertIn("HTTP-Referer", calls[0]["headers"])

    def test_parse_text_blocks_and_malformed_arguments(self):
        parsed = OpenAICompatibleProvider.parse(
            {
                "choices": [{
                    "message": {
                        "content": [
                            {"type": "text", "text": "hello "},
                            {"type": "output_text", "text": "world"},
                            {"type": "reasoning", "text": "hidden"},
                        ],
                        "tool_calls": [
                            {
                                "id": "c1",
                                "function": {"name": "echo", "arguments": "not json"},
                            },
                            {
                                "function": {"name": "other", "arguments": None},
                            },
                        ],
                    },
                    "finish_reason": "TOOL_CALLS",
                }],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 4,
                    "total_tokens": 10,
                },
            }
        )
        self.assertEqual(parsed["text"], "hello world")
        self.assertEqual(parsed["tool_calls"][0]["args"], {})
        self.assertEqual(parsed["tool_calls"][1]["args"], {})
        self.assertEqual(parsed["tool_calls"][0]["name"], "echo")
        self.assertEqual(parsed["finish_reason"], "tool_calls")
        self.assertEqual(parsed["usage"], {"input": 3, "output": 4, "total": 10})

    def test_parse_provider_error(self):
        with self.assertRaises(ProviderError):
            OpenAICompatibleProvider.parse({"error": {"message": "quota"}})
        with self.assertRaises(ProviderError):
            OpenAICompatibleProvider.parse({"choices": []})


class AnthropicTests(unittest.TestCase):
    def test_consecutive_tool_results_are_merged(self):
        wire = AnthropicProvider.to_wire([
            {
                "role": "assistant",
                "text": "working",
                "tool_calls": [
                    {"id": "t1", "name": "one", "args": {"a": 1}},
                    {"id": "t2", "name": "two", "args": {}},
                ],
            },
            {"role": "tool", "name": "one", "call_id": "t1", "text": "first"},
            {"role": "tool", "name": "two", "call_id": "t2", "text": "second"},
        ])
        self.assertEqual(len(wire), 2)
        self.assertEqual(wire[0]["role"], "assistant")
        self.assertEqual(
            [block["type"] for block in wire[0]["content"]],
            ["text", "tool_use", "tool_use"],
        )
        self.assertEqual(wire[1]["role"], "user")
        self.assertEqual(
            [block["tool_use_id"] for block in wire[1]["content"]],
            ["t1", "t2"],
        )

    def test_empty_assistant_message_gets_placeholder(self):
        wire = AnthropicProvider.to_wire([
            {"role": "assistant", "text": "", "tool_calls": []}
        ])
        self.assertEqual(wire[0]["content"], [{"type": "text", "text": "(no output)"}])

    def test_complete_builds_tools_and_headers(self):
        transport, calls = capture_transport(
            {
                "content": [
                    {"type": "text", "text": "hello"},
                    {"type": "tool_use", "id": "t1", "name": "echo", "input": {"x": 1}},
                ],
                "stop_reason": "tool_use",
                "usage": {"input_tokens": 5, "output_tokens": 6},
            }
        )
        provider = AnthropicProvider(
            model="claude-test", api_key="secret",
            base_url="https://api.test/v1", transport=transport,
        )
        parsed = provider.complete(
            "system",
            [{"role": "user", "text": "hi"}],
            [{"name": "echo", "description": "Echo", "parameters": {"type": "object"}}],
        )
        request = calls[0]
        self.assertEqual(request["url"], "https://api.test/v1/messages")
        self.assertEqual(request["headers"]["x-api-key"], "secret")
        self.assertEqual(request["headers"]["anthropic-version"], "2023-06-01")
        self.assertEqual(request["payload"]["system"], "system")
        self.assertEqual(request["payload"]["max_tokens"], 16384)
        self.assertEqual(request["payload"]["tools"][0]["input_schema"], {"type": "object"})
        self.assertEqual(parsed["text"], "hello")
        self.assertEqual(parsed["tool_calls"], [{"id": "t1", "name": "echo", "args": {"x": 1}}])
        self.assertEqual(parsed["finish_reason"], "tool_use")
        self.assertEqual(parsed["usage"], {"input": 5, "output": 6, "total": 11})

    def test_parse_error_response(self):
        with self.assertRaises(ProviderError):
            AnthropicProvider.parse(
                {"type": "error", "error": {"message": "overloaded"}}
            )


class GeminiTests(unittest.TestCase):
    def test_to_wire_round_trips_thought_signature(self):
        wire = GeminiProvider.to_wire([
            {"role": "user", "text": "hi"},
            {
                "role": "assistant",
                "text": "calling",
                "tool_calls": [{
                    "id": "c1", "name": "echo", "args": {"text": "x"},
                    "signature": "sig-123",
                }],
            },
            {"role": "tool", "name": "echo", "call_id": "c1", "text": "done"},
        ])
        self.assertEqual(wire[0], {"role": "user", "parts": [{"text": "hi"}]})
        self.assertEqual(wire[1]["role"], "model")
        self.assertEqual(wire[1]["parts"][0], {"text": "calling"})
        self.assertEqual(
            wire[1]["parts"][1]["functionCall"],
            {"name": "echo", "args": {"text": "x"}},
        )
        self.assertEqual(wire[1]["parts"][1]["thoughtSignature"], "sig-123")
        self.assertEqual(
            wire[2]["parts"][0]["functionResponse"],
            {"name": "echo", "response": {"result": "done"}},
        )

    def test_parse_ignores_thought_parts_and_keeps_signature(self):
        parsed = GeminiProvider.parse({
            "candidates": [{
                "finishReason": "STOP",
                "content": {"parts": [
                    {"text": "hidden", "thought": True},
                    {"text": "hello"},
                    {
                        "functionCall": {"name": "echo", "args": {"x": 1}},
                        "thoughtSignature": "sig",
                    },
                ]},
            }],
            "usageMetadata": {
                "promptTokenCount": 3,
                "candidatesTokenCount": 4,
                "totalTokenCount": 7,
                "cachedContentTokenCount": 1,
                "thoughtsTokenCount": 2,
            },
        })
        self.assertEqual(parsed["text"], "hello")
        self.assertTrue(parsed["tool_calls"][0]["id"].startswith("call_"))
        self.assertEqual(parsed["tool_calls"][0]["signature"], "sig")
        self.assertEqual(parsed["finish_reason"], "stop")
        self.assertEqual(
            parsed["usage"],
            {"input": 3, "output": 4, "cached": 1, "thought": 2, "total": 7},
        )

    def test_safety_blocks_raise_provider_errors(self):
        for response in (
            {"promptFeedback": {"blockReason": "SAFETY"}},
            {"candidates": [{"finishReason": "SAFETY", "content": {}}]},
            {"candidates": []},
        ):
            with self.subTest(response=response):
                with self.assertRaises(ProviderError):
                    GeminiProvider.parse(response)

    def test_complete_uses_api_key_header_and_function_declarations(self):
        transport, calls = capture_transport({
            "candidates": [{
                "finishReason": "STOP",
                "content": {"parts": [{"text": "ok"}]},
            }],
        })
        provider = GeminiProvider(
            model="gemini-test", api_key="secret",
            base_url="https://api.test/v1beta", transport=transport,
        )
        parsed = provider.complete(
            "system", [{"role": "user", "text": "hi"}], [{"name": "echo"}]
        )
        request = calls[0]
        self.assertEqual(
            request["url"],
            "https://api.test/v1beta/models/gemini-test:generateContent",
        )
        self.assertEqual(request["headers"]["x-goog-api-key"], "secret")
        self.assertEqual(
            request["payload"]["tools"], [{"functionDeclarations": [{"name": "echo"}]}]
        )
        self.assertEqual(parsed["text"], "ok")


class TransportAndHelperTests(unittest.TestCase):
    def test_missing_key_is_reported(self):
        provider = GeminiProvider(model="gemini-test", api_key="secret")
        self.assertEqual(provider.require_api_key(), "secret")
        provider.api_key = None
        with self.assertRaises(ProviderError):
            provider.require_api_key()

    def test_http_post_json_retries_server_errors(self):
        error = urllib.error.HTTPError(
            "https://api.test", 500, "boom", {}, io.BytesIO(b"boom")
        )
        response = FakeResponse(json.dumps({"ok": True}).encode("utf-8"))
        with mock.patch(
            "argus.providers.base.urllib.request.urlopen",
            side_effect=[error, response],
        ) as urlopen, mock.patch("argus.providers.base.time.sleep") as sleep:
            result = http_post_json("https://api.test", {"a": 1}, {})
        self.assertEqual(result, {"ok": True})
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once()

    def test_http_post_json_does_not_retry_client_errors(self):
        error = urllib.error.HTTPError(
            "https://api.test", 400, "bad", {}, io.BytesIO(b"bad request")
        )
        with mock.patch(
            "argus.providers.base.urllib.request.urlopen", side_effect=error
        ) as urlopen, mock.patch("argus.providers.base.time.sleep") as sleep:
            with self.assertRaises(ProviderError) as caught:
                http_post_json("https://api.test", {}, {})
        self.assertEqual(caught.exception.status, 400)
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    def test_http_post_json_rejects_invalid_json(self):
        response = FakeResponse(b"not json")
        with mock.patch(
            "argus.providers.base.urllib.request.urlopen", return_value=response
        ):
            with self.assertRaises(ProviderError):
                http_post_json("https://api.test", {}, {})

    def test_ensure_call_ids_pairs_results(self):
        messages = [
            {
                "role": "assistant",
                "tool_calls": [{"name": "a", "args": {}}, {"name": "b", "args": {}}],
            },
            {"role": "tool", "name": "a", "text": "x"},
            {"role": "tool", "name": "b", "text": "y"},
        ]
        ensure_call_ids(messages)
        ids = [call["id"] for call in messages[0]["tool_calls"]]
        self.assertEqual([row["call_id"] for row in messages[1:]], ids)
        ensure_call_ids(messages)
        self.assertEqual([call["id"] for call in messages[0]["tool_calls"]], ids)

    def test_usage_dict_normalization(self):
        self.assertEqual(usage_dict(3, 4), {"input": 3, "output": 4, "total": 7})
        self.assertEqual(
            usage_dict(1, 2, {"total": 10, "cached": 0}),
            {"input": 1, "output": 2, "total": 10},
        )


if __name__ == "__main__":
    unittest.main()
