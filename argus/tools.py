"""Day 2: teach filesystem tools, path confinement, and bounded subprocesses."""

from dataclasses import dataclass
import fnmatch
import inspect
import os
import re
import subprocess


@dataclass
class Tool:
    """Describe a callable tool and the schema exposed to the provider."""

    name: str
    spec: dict
    run: callable


def tool(description, **params):
    """Decorate a function with a string-parameter tool schema."""
    def decorator(fn):
        required = []
        properties = {}
        signature = inspect.signature(fn)
        for name, text in params.items():
            properties[name] = {
                "type": "string",
                "description": text,
            }
            if signature.parameters[name].default is inspect.Parameter.empty:
                required.append(name)
        fn.__tool__ = Tool(
            fn.__name__,
            {
                "schema": {
                    "name": fn.__name__,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                }
            },
            fn,
        )
        return fn.__tool__
    return decorator


def core_tools(workdir):
    """Return confined read, write, edit, shell, listing, and grep tools."""
    root = os.path.realpath(workdir)
    ignored = {".git", "node_modules", "__pycache__", ".venv"}

    def resolve(path):
        candidate = os.path.realpath(os.path.join(root, path))
        if os.path.commonpath((root, candidate)) != root:
            raise PermissionError(f"{path!r} escapes the working directory")
        return candidate

    def read_file(path):
        """Read a confined text file with one-based line numbers."""
        filename = resolve(path)
        with open(filename, encoding="utf-8") as stream:
            lines = stream.readlines()
        output = [f"{index}\t{line.rstrip(chr(10))}" for index, line in enumerate(lines, 1)]
        if len(lines) > 4000:
            output = output[:4000]
            output.append(f"... truncated; file has {len(lines)} lines")
        return "\n".join(output)

    def write_file(path, content):
        """Write confined text, creating its parent directories."""
        filename = resolve(path)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as stream:
            stream.write(content)
        return f"Wrote {len(content)} chars to {path}"

    def edit_file(path, old, new):
        """Replace one and only one exact confined snippet."""
        filename = resolve(path)
        with open(filename, encoding="utf-8") as stream:
            content = stream.read()
        matches = content.count(old)
        if matches == 0:
            return "ERROR: snippet not found - read the file and copy it exactly"
        if matches > 1:
            return f"ERROR: snippet appears {matches} times - include more context to make it unique"
        with open(filename, "w", encoding="utf-8") as stream:
            stream.write(content.replace(old, new, 1))
        return f"Edited {path}"

    def bash(command, timeout="120"):
        """Run a bounded shell command inside the working directory."""
        try:
            limit = float(timeout)
            result = subprocess.run(
                command,
                shell=True,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=limit,
            )
        except subprocess.TimeoutExpired:
            return f"ERROR: timed out after {timeout}s"
        output = result.stdout + result.stderr
        if len(output) > 12000:
            output = output[:6000] + "\n... output truncated ...\n" + output[-6000:]
        return output or f"(exit {result.returncode}, no output)"

    def walk_files():
        for current, directories, filenames in os.walk(root):
            directories[:] = sorted(name for name in directories if name not in ignored)
            for filename in sorted(filenames):
                absolute = os.path.join(current, filename)
                yield os.path.relpath(absolute, root).replace(os.sep, "/")

    def list_files(pattern="**/*"):
        """List confined files matching a relative path or basename pattern."""
        matches = [
            path for path in walk_files()
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern)
        ]
        if len(matches) > 500:
            return "\n".join(matches[:500] + [f"and {len(matches) - 500} more"])
        return "\n".join(matches)

    def grep(regex, pattern="*"):
        """Search confined matching files line by line."""
        expression = re.compile(regex)
        hits = []
        for path in walk_files():
            if not (fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern)):
                continue
            try:
                with open(resolve(path), encoding="utf-8") as stream:
                    for number, line in enumerate(stream, 1):
                        if expression.search(line):
                            hits.append(f"{path}:{number}: {line.rstrip()[:200]}")
                            if len(hits) == 200:
                                return "\n".join(hits)
            except UnicodeDecodeError:
                continue
        return "\n".join(hits)

    def make(name, description, function, properties, required):
        return Tool(name, {"schema": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required}}}, function)

    return [
        make("read_file", "Read a file", read_file, {"path": {"type": "string"}}, ["path"]),
        make("write_file", "Write a file", write_file,
             {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
        make("edit_file", "Edit a file", edit_file,
             {key: {"type": "string"} for key in ("path", "old", "new")}, ["path", "old", "new"]),
        make("bash", "Run a shell command", bash,
             {"command": {"type": "string"}, "timeout": {"type": "string"}}, ["command"]),
        make("list_files", "List files", list_files, {"pattern": {"type": "string"}}, []),
        make("grep", "Search files", grep,
             {"regex": {"type": "string"}, "pattern": {"type": "string"}}, ["regex"]),
    ]
