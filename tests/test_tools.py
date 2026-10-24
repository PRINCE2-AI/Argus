import os
import tempfile
import unittest
from unittest import mock

from argus.tools import core_tools, redact, tool


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.tools = {item.name: item for item in core_tools(self.root)}

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, relative, content, binary=False):
        path = os.path.join(self.root, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        mode = "wb" if binary else "w"
        kwargs = {} if binary else {"encoding": "utf-8"}
        with open(path, mode, **kwargs) as stream:
            stream.write(content)
        return path

    def test_read_file_has_line_numbers(self):
        self.write("app.py", "a\nb\n")
        output = self.tools["read_file"].run("app.py")
        self.assertIn("1\ta", output)
        self.assertIn("2\tb", output)

    def test_read_file_escape_is_blocked(self):
        outside = os.path.join(os.path.dirname(self.root), "outside.txt")
        with self.assertRaises(PermissionError):
            self.tools["read_file"].run(outside)
        with self.assertRaises(PermissionError):
            self.tools["read_file"].run("../outside.txt")

    def test_protected_paths_are_blocked(self):
        self.write(".env", "SECRET=1\n")
        os.makedirs(os.path.join(self.root, ".git"), exist_ok=True)
        self.write(".git/config", "[core]\n")
        for path in (".env", ".git/config", ".argus/sessions/x.jsonl"):
            with self.assertRaises(PermissionError):
                self.tools["read_file"].run(path)
        with self.assertRaises(PermissionError):
            self.tools["write_file"].run(".env", "x")

    def test_list_files_includes_root_and_nested(self):
        self.write("root.txt", "hi")
        self.write("sub/nested.txt", "hi")
        self.write(".env", "SECRET=1\n")
        output = self.tools["list_files"].run()
        self.assertIn("root.txt", output)
        self.assertIn("sub/nested.txt", output)
        self.assertNotIn(".env", output)

    def test_list_files_pattern(self):
        self.write("root.py", "x")
        self.write("sub/nested.py", "x")
        self.write("sub/notes.md", "x")
        output = self.tools["list_files"].run("*.py")
        self.assertIn("root.py", output)
        self.assertIn("sub/nested.py", output)
        self.assertNotIn("notes.md", output)

    def test_edit_file_requires_unique_snippet(self):
        self.write("app.py", "value = 1\n")
        self.assertEqual(self.tools["edit_file"].run("app.py", "value = 1", "value = 2"), "Edited app.py")
        self.write("dup.py", "x\nx\n")
        self.assertIn("appears 2 times", self.tools["edit_file"].run("dup.py", "x", "y"))
        self.assertIn("not found", self.tools["edit_file"].run("dup.py", "z", "y"))

    def test_binary_read_is_rejected(self):
        self.write("data.bin", b"abc\x00def", binary=True)
        self.assertIn("binary file", self.tools["read_file"].run("data.bin"))

    def test_read_file_redacts_secret_patterns(self):
        fake_key = "sk-" + ("a" * 24)
        self.write("notes.txt", f"key={fake_key}\n")
        output = self.tools["read_file"].run("notes.txt")
        self.assertNotIn(fake_key, output)
        self.assertIn("REDACTED", output)

    def test_bash_redacts_output(self):
        fake_key = "AIza" + ("b" * 35)
        self.write("leak.txt", fake_key)
        command = "type leak.txt" if os.name == "nt" else "cat leak.txt"
        output = self.tools["bash"].run(command)
        self.assertNotIn(fake_key, output)
        self.assertIn("REDACTED", output)

    def test_redact_masks_environment_values(self):
        with mock.patch.dict(os.environ, {"ARGUS_API_KEY": "unit-test-secret-value"}, clear=False):
            self.assertEqual(redact("x unit-test-secret-value y"), "x [REDACTED] y")

    def test_grep_skips_protected_files(self):
        self.write(".env", "NEEDLE\n")
        self.write("app.py", "NEEDLE\n")
        output = self.tools["grep"].run("NEEDLE")
        self.assertIn("app.py:1", output)
        self.assertNotIn(".env", output)

    def test_typed_tool_schema(self):
        @tool("Add numbers", a={"type": "integer"}, b={"type": "integer"})
        def add(a, b):
            return a + b

        properties = add.spec["schema"]["parameters"]["properties"]
        self.assertEqual(properties["a"]["type"], "integer")
        self.assertEqual(add.run(2, 3), 5)

    def test_tool_decorator_rejects_unknown_parameter(self):
        with self.assertRaises(TypeError):
            @tool("Bad", missing="x")
            def no_match(value):
                return value


if __name__ == "__main__":
    unittest.main()
