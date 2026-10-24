import unittest

from helpers import ScriptedProvider, reply, tool_call

from argus import loop
from argus.tools import tool


@tool("Echo the provided text", text="text to echo")
def echo(text):
    return "echo:" + text


@tool("Always fails")
def boom():
    raise ValueError("bad state")


class LoopTests(unittest.TestCase):
    def setUp(self):
        self.tools = {
            "echo": echo,
            "boom": boom,
        }

    def test_returns_final_text_and_executes_tool(self):
        provider = ScriptedProvider([
            reply("", [tool_call("echo", {"text": "hi"}, "c1")]),
            reply("final answer"),
        ])
        messages = [{"role": "user", "text": "go"}]
        events = []
        answer = loop.run(
            "system", messages, self.tools, provider=provider,
            on_event=lambda kind, payload: events.append((kind, payload)),
        )
        self.assertEqual(answer, "final answer")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[2]["role"], "tool")
        self.assertEqual(messages[2]["call_id"], "c1")
        self.assertEqual(messages[2]["text"], "echo:hi")
        self.assertEqual(messages[3]["text"], "final answer")
        self.assertEqual(provider.requests[0]["tools"][0]["name"], "echo")
        kinds = [kind for kind, _ in events]
        self.assertEqual(kinds, ["usage", "assistant", "tool_start", "tool_end", "usage", "assistant"])

    def test_unknown_tool_is_reported_to_model(self):
        provider = ScriptedProvider([
            reply("", [tool_call("missing", {}, "c1")]),
            reply("done"),
        ])
        messages = [{"role": "user", "text": "go"}]
        loop.run("system", messages, self.tools, provider=provider)
        self.assertTrue(messages[2]["text"].startswith("ERROR: unknown tool"))

    def test_tool_exception_is_contained(self):
        provider = ScriptedProvider([
            reply("", [tool_call("boom", {}, "c1")]),
            reply("done"),
        ])
        messages = [{"role": "user", "text": "go"}]
        loop.run("system", messages, self.tools, provider=provider)
        self.assertIn("ERROR: ValueError: bad state", messages[2]["text"])

    def test_non_dict_arguments_are_discarded(self):
        provider = ScriptedProvider([
            reply("", [{"id": "c1", "name": "echo", "args": "not-a-dict"}]),
            reply("done"),
        ])
        messages = [{"role": "user", "text": "go"}]
        loop.run("system", messages, self.tools, provider=provider)
        self.assertTrue(messages[2]["text"].startswith("ERROR: TypeError"))

    def test_before_tool_can_block_a_call(self):
        provider = ScriptedProvider([
            reply("", [tool_call("echo", {"text": "hi"}, "c1")]),
            reply("done"),
        ])
        messages = [{"role": "user", "text": "go"}]
        loop.run(
            "system", messages, self.tools, provider=provider,
            before_tool=lambda call: "policy says no",
        )
        self.assertEqual(messages[2]["text"], "BLOCKED: policy says no")

    def test_before_turn_can_replace_history(self):
        provider = ScriptedProvider([reply("answer")])
        messages = [{"role": "user", "text": "original"}]
        loop.run(
            "system", messages, self.tools, provider=provider,
            before_turn=lambda current: [{"role": "user", "text": "replaced"}],
        )
        self.assertEqual(provider.requests[0]["messages"], [{"role": "user", "text": "replaced"}])

    def test_turn_limit_requests_a_final_wrap_up(self):
        provider = ScriptedProvider([
            reply("", [tool_call("echo", {"text": "1"}, "c1")]),
            reply("", [tool_call("echo", {"text": "2"}, "c2")]),
        ])
        messages = [{"role": "user", "text": "go"}]
        events = []
        answer = loop.run(
            "system", messages, self.tools, provider=provider,
            max_turns=2,
            on_event=lambda kind, payload: events.append(kind),
        )
        self.assertEqual(answer, "done")
        self.assertIn("turn_limit", events)
        self.assertEqual(messages[-2]["text"], "Turn limit reached; wrap up now.")
        self.assertEqual(provider.requests[-1]["tools"], [])
        self.assertEqual(len(provider.requests), 3)

    def test_invalid_provider_type_is_rejected(self):
        with self.assertRaises(TypeError):
            loop.run("system", [], self.tools, provider=object())

    def test_empty_tool_set_is_allowed(self):
        provider = ScriptedProvider([reply("plain answer")])
        messages = [{"role": "user", "text": "go"}]
        answer = loop.run("system", messages, {}, provider=provider)
        self.assertEqual(answer, "plain answer")
        self.assertEqual(provider.requests[0]["tools"], [])


if __name__ == "__main__":
    unittest.main()
