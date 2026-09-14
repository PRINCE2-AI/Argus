"""Day 3: teach discoverable workspace skills and explicit skill loading."""

import os

SKILLS_DIR = "skills"


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


def catalog(workdir):
    """Return skill names mapped to descriptions and absolute file paths."""
    root = os.path.join(os.path.realpath(workdir), SKILLS_DIR)
    result = {}
    if not os.path.isdir(root):
        return result
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name, "SKILL.md")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as skill_file:
                text = skill_file.read()
            result[name] = {
                "description": _description(text),
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
    path = os.path.join(os.path.realpath(workdir), SKILLS_DIR, name, "SKILL.md")
    if not os.path.isfile(path):
        return f"Error: no skill named {name}"
    with open(path, encoding="utf-8") as skill_file:
        return skill_file.read()
