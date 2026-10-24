import os
import tempfile
import unittest
from unittest import mock

from argus import memory, skills


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_remember_normalizes_and_dedupes(self):
        self.assertEqual(memory.remember(self.root, "  Use   UTC.  "), "Remembered in ARGUS.md")
        self.assertEqual(memory.remember(self.root, "Use UTC."), "Already remembered in ARGUS.md")
        self.assertEqual(memory.read_memory(self.root), "- Use UTC.\n")
        self.assertEqual(memory.remember(self.root, "   "), "Nothing to remember")

    def test_remember_appends_after_missing_newline(self):
        path = os.path.join(self.root, memory.MEMORY_FILE)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write("# Notes")
        memory.remember(self.root, "second")
        self.assertEqual(memory.read_memory(self.root), "# Notes\n- second\n")

    def test_missing_memory_is_empty(self):
        self.assertEqual(memory.read_memory(self.root), "")

    def test_system_prompt_includes_context_and_memory(self):
        memory.remember(self.root, "The project uses Python.")
        prompt = memory.build_system_prompt(self.root, "Extra guidance.")
        self.assertIn(memory.BASE_SYSTEM_PROMPT, prompt)
        self.assertIn(os.path.realpath(self.root), prompt)
        self.assertIn(memory.MEMORY_NOTE, prompt)
        self.assertIn("<project_memory>", prompt)
        self.assertIn("The project uses Python.", prompt)
        self.assertTrue(prompt.endswith("Extra guidance."))

    def test_system_prompt_without_memory_has_no_memory_block(self):
        prompt = memory.build_system_prompt(self.root)
        self.assertNotIn("<project_memory>", prompt)
        self.assertIn(memory.MEMORY_NOTE, prompt)

    def test_long_memory_is_truncated(self):
        with open(os.path.join(self.root, memory.MEMORY_FILE), "w", encoding="utf-8") as stream:
            stream.write("x" * 500)
        with mock.patch.object(memory, "MAX_MEMORY_CHARS", 100):
            prompt = memory.build_system_prompt(self.root)
        self.assertIn("x" * 100, prompt)
        self.assertNotIn("x" * 101, prompt)
        self.assertIn("memory truncated", prompt)


class SkillsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.skills_root = os.path.join(self.root, "skills")

    def tearDown(self):
        self.tmp.cleanup()

    def write_skill(self, name, text):
        directory = os.path.join(self.skills_root, name)
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "SKILL.md"), "w", encoding="utf-8") as stream:
            stream.write(text)

    def test_missing_skills_directory_has_empty_catalog(self):
        self.assertEqual(skills.catalog(self.root), {})
        self.assertEqual(skills.catalog_prompt(self.root), "")

    def test_catalog_and_prompt_read_front_matter(self):
        self.write_skill(
            "demo",
            "---\ndescription: Demo skill\n---\nBody text.\n",
        )
        os.makedirs(os.path.join(self.skills_root, "empty"))
        catalog = skills.catalog(self.root)
        self.assertEqual(list(catalog), ["demo"])
        self.assertEqual(catalog["demo"]["description"], "Demo skill")
        prompt = skills.catalog_prompt(self.root)
        self.assertIn("demo: Demo skill", prompt)
        self.assertEqual(skills.read_skill(self.root, "demo"), "---\ndescription: Demo skill\n---\nBody text.\n")

    def test_missing_skill_returns_an_error(self):
        self.write_skill("demo", "Body")
        self.assertEqual(skills.read_skill(self.root, "nope"), "Error: no skill named nope")

    def test_traversal_names_are_rejected(self):
        self.write_skill("demo", "Body")
        for name in ("../demo", "..", "a/b", "", "C:\\secret", "demo/../other"):
            with self.subTest(name=name):
                self.assertEqual(
                    skills.read_skill(self.root, name),
                    f"Error: no skill named {name}",
                )

    def test_long_skill_is_truncated(self):
        self.write_skill("demo", "y" * 300)
        with mock.patch.object(skills, "MAX_SKILL_CHARS", 100):
            text = skills.read_skill(self.root, "demo")
        self.assertIn("skill truncated", text)
        self.assertEqual(len(text), 100 + len("\n... skill truncated ..."))


if __name__ == "__main__":
    unittest.main()
