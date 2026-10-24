import json
import os
import tempfile
import unittest
from unittest import mock

from helpers import ScriptedProvider, reply, tool_call

from argus import context, session
from argus.harness import Harness
from argus.security import Policy


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        with open(os.path.join(self.root, "note.txt"), "w", encoding="utf-8") as stream:
            stream.write("read me\n")

    def tearDown(self):
        self.tmp.cleanup()

    def raw_rows(self, path):
        with open(path, encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]

    def test_default_policy_is_safe(self):
        harness = Harness(
            self.root, provider=ScriptedProvider(), persist=False
        )
        self.assertEqual(harness.policy.mode, "safe")
        self.assertEqual(harness.provider_name, "fake")

    def test_persists_history_without_duplicate_tool_rows(self):
        provider = ScriptedProvider([
            reply("", [tool_call("read_file", {"path": "note.txt"}, "c1")]),
            reply("read it"),
        ])
        harness = Harness(
            self.root, provider=provider, policy=Policy("yolo")
        )
        self.assertEqual(harness.run("read the note"), "read it")
        rows = self.raw_rows(harness.session_path)
        self.assertEqual(
            [row["role"] for row in rows],
            ["user", "assistant", "tool", "assistant"],
        )
        self.assertEqual([row for row in rows if row["role"] == "tool"], [
            {
                "role": "tool",
                "name": "read_file",
                "call_id": "c1",
                "text": "1\tread me",
            }
        ])
        self.assertEqual(harness.usage, {"input": 2, "output": 2, "total": 4})

    def test_persistence_can_be_disabled(self):
        provider = ScriptedProvider([reply("ok")])
        harness = Harness(self.root, provider=provider, persist=False)
        harness.run("no files please")
        self.assertIsNone(harness.session_path)
        self.assertEqual(session.list_sessions(self.root), [])

    def test_resume_loads_the_latest_session(self):
        first = Harness(
            self.root, provider=ScriptedProvider([reply("first answer")]),
        )
        first.run("first task")
        second = Harness(
            self.root, provider=ScriptedProvider(), persist=False
        )
        self.assertTrue(second.resume())
        self.assertEqual(second.messages[0]["text"], "first task")
        self.assertEqual(second.messages[-1]["text"], "first answer")

    def test_resume_without_sessions_returns_false(self):
        fresh = os.path.join(self.root, "fresh")
        os.makedirs(fresh)
        harness = Harness(fresh, provider=ScriptedProvider(), persist=False)
        self.assertFalse(harness.resume())

    def test_compaction_is_persisted_and_reloadable(self):
        provider = ScriptedProvider([
            reply("", [tool_call("read_file", {"path": "note.txt"}, "c1")]),
            reply("compressed facts"),
            reply("finished"),
        ])
        harness = Harness(
            self.root, provider=provider, policy=Policy("yolo"),
            budget_tokens=1,
        )
        with mock.patch.object(context, "KEEP_RECENT", 1):
            self.assertEqual(harness.run("long task"), "finished")
        rows = self.raw_rows(harness.session_path)
        summaries = [row for row in rows if (row.get("meta") or {}).get("compaction")]
        self.assertEqual(len(summaries), 1)
        self.assertIn(context.SUMMARY_MARKER, summaries[0]["text"])
        self.assertIn("compressed facts", summaries[0]["text"])
        loaded = session.load(harness.session_path)
        self.assertTrue((loaded[0].get("meta") or {}).get("compaction"))
        self.assertEqual(loaded[-1]["text"], "finished")
        resumed = Harness(self.root, provider=ScriptedProvider(), persist=False)
        self.assertTrue(resumed.resume(harness.session_path))
        self.assertTrue((resumed.messages[0].get("meta") or {}).get("compaction"))
        self.assertEqual(harness.usage, {"input": 2, "output": 2, "total": 4})

    def test_remember_tool_writes_and_dedupes(self):
        harness = Harness(
            self.root, provider=ScriptedProvider(), persist=False
        )
        self.assertEqual(harness.tools["remember"].run("Use UTC."), "Remembered in ARGUS.md")
        self.assertEqual(
            harness.tools["remember"].run("Use   UTC."),
            "Already remembered in ARGUS.md",
        )
        with open(os.path.join(self.root, "ARGUS.md"), encoding="utf-8") as stream:
            self.assertEqual(stream.read(), "- Use UTC.\n")

    def test_use_skill_tool_is_offered_only_when_skills_exist(self):
        plain = Harness(self.root, provider=ScriptedProvider(), persist=False)
        self.assertNotIn("use_skill", plain.tools)
        skill_dir = os.path.join(self.root, "skills", "demo")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as stream:
            stream.write("---\ndescription: Demo skill\n---\nDo the demo.\n")
        harness = Harness(self.root, provider=ScriptedProvider(), persist=False)
        self.assertIn("use_skill", harness.tools)
        self.assertIn("Demo skill", harness.system)
        self.assertIn("Do the demo.", harness.tools["use_skill"].run("demo"))

    def test_subagent_runs_with_a_fresh_context(self):
        provider = ScriptedProvider([
            reply("", [tool_call("spawn_agent", {"task": "child work"}, "c1")]),
            reply("child report"),
            reply("parent final"),
        ])
        harness = Harness(
            self.root, provider=provider, policy=Policy("yolo"), persist=False
        )
        self.assertEqual(harness.run("parent task"), "parent final")
        self.assertEqual(harness.messages[-2]["text"], "child report")
        child_requests = [
            request for request in provider.requests
            if any(row.get("text") == "child work" for row in request["messages"])
        ]
        self.assertEqual(len(child_requests), 1)


if __name__ == "__main__":
    unittest.main()
