import json
import os
import tempfile
import unittest

from argus import session


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def write_lines(self, path, rows, tail=""):
        with open(path, "a", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row) + "\n")
            stream.write(tail)

    def test_new_session_is_unique_and_slugged(self):
        first = session.new_session(self.root, "Hello, World!")
        second = session.new_session(self.root, "Hello, World!")
        self.assertNotEqual(first, second)
        self.assertNotEqual(os.path.basename(first), os.path.basename(second))
        self.assertIn("hello-world", os.path.basename(first))
        self.assertTrue(os.path.isfile(first))
        self.assertTrue(os.path.isfile(second))

    def test_append_and_load_roundtrip(self):
        path = session.new_session(self.root, "roundtrip")
        rows = [
            {"role": "user", "text": "do it"},
            {"role": "assistant", "text": "", "tool_calls": [
                {"id": "c1", "name": "bash", "args": {"command": "ls"}}
            ]},
            {"role": "tool", "name": "bash", "call_id": "c1", "text": "ok"},
        ]
        for row in rows:
            session.append(path, row)
        self.assertEqual(session.load(path), rows)

    def test_torn_tail_is_ignored(self):
        path = session.new_session(self.root, "torn")
        self.write_lines(
            path,
            [{"role": "user", "text": "kept"}],
            tail='{"role": "assistant", "text": "trunc',
        )
        loaded = session.load(path)
        self.assertEqual([row["text"] for row in loaded], ["kept"])

    def test_adjacent_duplicate_tool_rows_are_dropped(self):
        path = session.new_session(self.root, "dupes")
        tool = {"role": "tool", "name": "bash", "call_id": "c1", "text": "same"}
        self.write_lines(
            path,
            [
                {"role": "user", "text": "go"},
                tool,
                dict(tool),
                {"role": "tool", "name": "bash", "call_id": "c2", "text": "other"},
            ],
        )
        loaded = session.load(path)
        self.assertEqual([row.get("call_id") for row in loaded[1:]], ["c1", "c2"])

    def test_load_starts_at_last_compaction(self):
        path = session.new_session(self.root, "compact")
        rows = [
            {"role": "user", "text": "old"},
            {
                "role": "user",
                "text": "summary",
                "meta": {"compaction": True, "replaced": 1},
            },
            {"role": "assistant", "text": "recent", "tool_calls": []},
        ]
        self.write_lines(path, rows)
        self.assertEqual(session.load(path), rows[1:])

    def test_leading_tool_rows_are_dropped(self):
        path = session.new_session(self.root, "leading")
        self.write_lines(
            path,
            [
                {"role": "tool", "name": "x", "text": "orphan"},
                {"role": "assistant", "text": "answer", "tool_calls": []},
            ],
        )
        self.assertEqual(session.load(path), [
            {"role": "assistant", "text": "answer", "tool_calls": []}
        ])

    def test_interrupted_tool_call_is_repaired(self):
        path = session.new_session(self.root, "repair")
        self.write_lines(
            path,
            [
                {"role": "user", "text": "go"},
                {
                    "role": "assistant",
                    "text": "",
                    "tool_calls": [
                        {"id": "a", "name": "read_file", "args": {"path": "x"}},
                        {"id": "b", "name": "bash", "args": {"command": "ls"}},
                    ],
                },
                {"role": "tool", "name": "read_file", "call_id": "a", "text": "x"},
            ],
        )
        loaded = session.load(path)
        self.assertEqual(len(loaded), 4)
        repaired = loaded[-1]
        self.assertEqual(repaired["call_id"], "b")
        self.assertIn("Interrupted", repaired["text"])

    def test_repair_without_call_ids_uses_position(self):
        path = session.new_session(self.root, "repair-positional")
        self.write_lines(
            path,
            [
                {
                    "role": "assistant",
                    "text": "",
                    "tool_calls": [
                        {"name": "one", "args": {}},
                        {"name": "two", "args": {}},
                    ],
                },
                {"role": "tool", "name": "one", "text": "ran"},
            ],
        )
        loaded = session.load(path)
        self.assertEqual(len(loaded), 3)
        self.assertEqual(loaded[-1]["name"], "two")

    def test_list_sessions_is_newest_first_with_preview(self):
        first = session.new_session(self.root, "first")
        second = session.new_session(self.root, "second")
        session.append(first, {"role": "user", "text": "old " + "x" * 200})
        session.append(second, {"role": "user", "text": "new task"})
        os.utime(first, (1000, 1000))
        os.utime(second, (2000, 2000))
        sessions = session.list_sessions(self.root)
        self.assertEqual([item["name"] for item in sessions], [
            os.path.basename(second),
            os.path.basename(first),
        ])
        self.assertEqual(sessions[0]["preview"], "new task")
        self.assertLessEqual(len(sessions[1]["preview"]), 100)
        self.assertEqual(session.latest(self.root), second)

    def test_empty_workspace_has_no_sessions(self):
        self.assertEqual(session.list_sessions(self.root), [])
        self.assertIsNone(session.latest(self.root))
        path = session.new_session(self.root, "empty")
        self.assertEqual(session.load(path), [])


if __name__ == "__main__":
    unittest.main()
