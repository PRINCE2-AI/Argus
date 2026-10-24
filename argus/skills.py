"""Discoverable workspace skills with explicit, confined loading."""

import os
import re

SKILLS_DIR = "skills"
MAX_SKILL_CHARS = 64_000
_VALID_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _description(text):
    """Read a front-matter description line, if one exists."""
    in_front_matter = False
    for line in text.splitlines():
        if line.strip() == "---":
            in_front_matter = not in_front_matter
            continue
        if in_front_matter and line.startswith("description:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return ""


def _skill_root(workdir):
    return os.path.realpath(os.path.join(os.path.realpath(workdir), SKILLS_DIR))


def _skill_path(workdir, name):
    if not isinstance(name, str) or not _VALID_NAME.match(name.strip()):
        return None
    root = _skill_root(workdir)
    path = os.path.realpath(os.path.join(root, name.strip(), "SKILL.md"))
    try:
        if os.path.commonpath((root, path)) != root:
            return None
    except ValueError:
        return None
    return path


def catalog(workdir):
    """Return skill names mapped to descriptions and absolute file paths."""
    root = _skill_root(workdir)
    result = {}
    if not os.path.isdir(root):
        return result
    for name in sorted(os.listdir(root)):
        path = _skill_path(workdir, name)
        if not path or not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as skill_file:
            text = skill_file.read()
        result[name] = {
            "description": _description(text)[:200],
            "path": path,
        }
    return result


def catalog_prompt(workdir):
    """Render the available skill catalog for a system prompt."""
    skills = catalog(workdir)
    if not skills:
        return ""
    lines = ["Skills available (load one with the use_skill tool when relevant):"]
    lines.extend(f"- {name}: {item['description']}" for name, item in skills.items())
    return "\n".join(lines)


def read_skill(workdir, name):
    """Read a named skill document or return a clear missing-skill error."""
    path = _skill_path(workdir, name)
    if not path or not os.path.isfile(path):
        return f"Error: no skill named {name}"
    with open(path, encoding="utf-8") as skill_file:
        text = skill_file.read()
    if len(text) > MAX_SKILL_CHARS:
        text = text[:MAX_SKILL_CHARS] + "\n... skill truncated ..."
    return text
