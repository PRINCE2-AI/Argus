import unittest
from unittest import mock

from helpers import ScriptedProvider, reply

from argus import context


def conversation(length, ending="assistant"):
    roles = ["user", "assistant", "tool"]
    messages = [
        {"role": roles[index % len(roles)], "text": "word " * 20}
        for index in range(length)
    ]
    if ending == "assistant":
        messages[-1] = {"role": "assistant", "text": "latest", "tool_calls": []}
    return messages


class ContextTests(unittest.TestCase):
    def test_estimate_tokens_uses_four_chars_per_token(self):
        self.assertEqual(context.estimate_tokens([{"role": "user", "text": "abcd"}]), len(str({"role": "user", "text": "abcd"})) / 4)
        self.assertEqual(context.estimate_tokens([]), 0)

    def test_no_compaction_under_budget(self):
        messages = conversation(20)
        provider = ScriptedProvider([reply("unused")])
        result = context.compact(provider, messages, 10_000_000)
        self.assertIs(result, messages)
        self.assertEqual(provider.requests, [])

    def test_no_compaction_when_history_is_short(self):
        messages = conversation(context.KEEP_RECENT + 1)
        provider = ScriptedProvider([reply("unused")])
        result = context.compact(provider, messages, 1)
        self.assertIs(result, messages)
        self.assertEqual(provider.requests, [])

    def test_compaction_keeps_recent_turns_and_marks_summary(self):
        messages = conversation(12)
        provider = ScriptedProvider([reply("dense summary")])
        with mock.patch.object(context, "KEEP_RECENT", 3):
            result = context.compact(provider, messages, 1)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]["role"], "user")
        self.assertTrue(result[0]["text"].startswith(context.SUMMARY_MARKER))
        self.assertIn("dense summary", result[0]["text"])
        self.assertEqual(result[0]["meta"], {"compaction": True, "replaced": 9})
        self.assertEqual(result[1:], messages[-3:])
        self.assertEqual(provider.requests[0]["system"], context.SUMMARY_SYSTEM)
        self.assertIn("assistant", provider.requests[0]["messages"][0]["text"])

    def test_compaction_drops_leading_tool_rows_from_recent_window(self):
        messages = [
            {"role": "user", "text": "start"},
            {"role": "assistant", "text": "", "tool_calls": [
                {"id": "c1", "name": "bash", "args": {}}
            ]},
            {"role": "tool", "name": "bash", "call_id": "c1", "text": "out"},
            {"role": "assistant", "text": "latest", "tool_calls": []},
        ]
        provider = ScriptedProvider([reply("summary")])
        with mock.patch.object(context, "KEEP_RECENT", 2):
            result = context.compact(provider, messages, 1)
        self.assertEqual(result[0]["meta"]["compaction"], True)
        self.assertEqual(result[1]["role"], "assistant")
        self.assertEqual(result[1]["text"], "latest")

    def test_empty_summary_keeps_original_history(self):
        messages = conversation(12)
        provider = ScriptedProvider([reply("")])
        with mock.patch.object(context, "KEEP_RECENT", 3):
            result = context.compact(provider, messages, 1)
        self.assertIs(result, messages)


if __name__ == "__main__":
    unittest.main()
