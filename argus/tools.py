"""Filesystem tools, path confinement, secret redaction, and bounded shells."""

import fnmatch
import inspect
import os
import re
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import config

PROTECTED_NAMES = {".env", ".git", ".argus"}
PROTECTED_PREFIXES = (".env.",)
IGNORED_DIRS = {
    ".git",
    ".argus",
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".ruff_cache",
    ".mypy_cache",
}
MAX_READ_LINES = 4000
MAX_GREP_BYTES = 1_000_000
MAX_OUTPUT = 12000

_SECRET_NAME = re.compile(
    r"(?:API_KEY|APIKEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|ACCESS_KEY)", re.I
)
_SECRET_PATTERNS = [
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"), "[REDACTED_GEMINI_KEY]"),
    (re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_\-]{16,}\b"), "[REDACTED_OPENAI_KEY]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"), "[REDACTED_SLACK_TOKEN]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    (
        re.compile(
            r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"
        ),
        "[REDACTED_JWT]",
    ),
    (
        re.compile(
            r"(?i)\b(?:api[_-]?key|token|secret|password)\s*=\s*[^\s\"']+"
        ),
        lambda match: match.group(0).split("=")[0] + "=[REDACTED]",
    ),
]


@dataclass
class Tool:
    """Describe a callable tool and the schema exposed to the provider."""

    name: str
    spec: dict
    run: Callable[..., Any]


def tool(description, **params):
    """Decorate a function with a tool schema; string values mean string params."""
    def decorator(fn):
        required = []
        properties = {}
        signature = inspect.signature(fn)
        for name, spec in params.items():
            if isinstance(spec, str):
                properties[name] = {"type": "string", "description": spec}
            elif isinstance(spec, dict):
                properties[name] = dict(spec)
            else:
                raise TypeError(f"tool parameter {name!r} must be a str or dict")
            parameter = signature.parameters.get(name)
            if parameter is None:
                raise TypeError(f"tool {fn.__name__!r} has no parameter {name!r}")
            if parameter.default is inspect.Parameter.empty:
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


def redact(text):
    """Mask provider keys and common secret formats in tool output."""
    if not isinstance(text, str):
        return text
    values = set()
    for name, value in os.environ.items():
        if _SECRET_NAME.search(name) and len(value) >= 8:
            values.add(value)
    for value in sorted(values, key=len, reverse=True):
        text = text.replace(value, "[REDACTED]")
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def core_tools(workdir):
    """Return confined read, write, edit, shell, listing, and grep tools."""
    root = os.path.realpath(workdir)

    def resolve(path):
        candidate = os.path.realpath(os.path.join(root, path))
        try:
            if os.path.commonpath((root, candidate)) != root:
                raise PermissionError(f"{path!r} escapes the working directory")
        except ValueError as error:
            raise PermissionError(
                f"{path!r} escapes the working directory"
            ) from error
        relative = os.path.relpath(candidate, root)
        parts = relative.split(os.sep)
        if any(part in PROTECTED_NAMES for part in parts) or any(
            part.startswith(PROTECTED_PREFIXES) for part in parts
        ):
            raise PermissionError(f"{path!r} is a protected path")
        return candidate

    def read_file(path):
        """Read a confined text file with one-based line numbers."""
        filename = resolve(path)
        output = []
        total = 0
        with open(filename, encoding="utf-8", errors="replace") as stream:
            for index, line in enumerate(stream, 1):
                total = index
                if index > MAX_READ_LINES:
                    break
                if "\x00" in line:
                    return "ERROR: binary file; use bash for binary inspection"
                output.append(f"{index}\t{line.rstrip(chr(10))}")
        if total > MAX_READ_LINES:
            output.append(
                f"... truncated at {MAX_READ_LINES} lines; file has at least {total}"
            )
        return redact("\n".join(output))

    def write_file(path, content):
        """Write confined text atomically, creating parent directories."""
        filename = resolve(path)
        directory = os.path.dirname(filename)
        os.makedirs(directory, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=directory, prefix=".argus-")
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
                stream.write(content)
            os.replace(temporary, filename)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
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
            return (
                f"ERROR: snippet appears {matches} times - include more context "
                "to make it unique"
            )
        directory = os.path.dirname(filename)
        handle, temporary = tempfile.mkstemp(dir=directory, prefix=".argus-")
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
                stream.write(content.replace(old, new, 1))
            os.replace(temporary, filename)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
        return f"Edited {path}"

    def bash(command, timeout="120"):
        """Run a bounded shell command inside the working directory."""
        try:
            limit = min(max(float(timeout), 1.0), 3600.0)
        except (TypeError, ValueError):
            return "ERROR: timeout must be a number of seconds"
        config.load_env_file()
        environment = {
            name: value
            for name, value in os.environ.items()
            if not _SECRET_NAME.search(name)
        }
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=limit,
                env=environment,
            )
        except subprocess.TimeoutExpired:
            return f"ERROR: timed out after {timeout}s"
        output = result.stdout + result.stderr
        output = redact(output)
        if len(output) > MAX_OUTPUT:
            half = MAX_OUTPUT // 2
            output = (
                output[:half]
                + "\n... output truncated ...\n"
                + output[-half:]
            )
        return output or f"(exit {result.returncode}, no output)"

    def walk_files():
        for current, directories, filenames in os.walk(root):
            directories[:] = sorted(
                name
                for name in directories
                if name not in IGNORED_DIRS and name not in PROTECTED_NAMES
            )
            for filename in sorted(filenames):
                if filename in PROTECTED_NAMES or filename.startswith(
                    PROTECTED_PREFIXES
                ):
                    continue
                absolute = os.path.join(current, filename)
                if os.path.islink(absolute):
                    continue
                yield os.path.relpath(absolute, root).replace(os.sep, "/")

    def matches(path, pattern):
        if pattern in {"**", "**/*"}:
            return True
        return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(
            os.path.basename(path), pattern
        )

    def list_files(pattern="**"):
        """List confined files matching a relative path or basename pattern."""
        files = [path for path in walk_files() if matches(path, pattern)]
        if len(files) > 500:
            return "\n".join(files[:500] + [f"and {len(files) - 500} more"])
        return "\n".join(files)

    def grep(regex, pattern="**"):
        """Search confined matching files line by line."""
        expression = re.compile(regex)
        hits = []
        for path in walk_files():
            if not matches(path, pattern):
                continue
            filename = resolve(path)
            try:
                if os.path.getsize(filename) > MAX_GREP_BYTES:
                    continue
                with open(filename, encoding="utf-8") as stream:
                    for number, line in enumerate(stream, 1):
                        if expression.search(line):
                            hits.append(
                                f"{path}:{number}: {line.rstrip()[:200]}"
                            )
                            if len(hits) == 200:
                                return redact("\n".join(hits))
            except (UnicodeDecodeError, OSError):
                continue
        return redact("\n".join(hits))

    def make(name, description, function, properties, required):
        return Tool(
            name,
            {
                "schema": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                }
            },
            function,
        )

    return [
        make(
            "read_file",
            "Read a file with line numbers",
            read_file,
            {"path": {"type": "string"}},
            ["path"],
        ),
        make(
            "write_file",
            "Write a file atomically",
            write_file,
            {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            ["path", "content"],
        ),
        make(
            "edit_file",
            "Replace one unique snippet in a file",
            edit_file,
            {
                key: {"type": "string"}
                for key in ("path", "old", "new")
            },
            ["path", "old", "new"],
        ),
        make(
            "bash",
            "Run a shell command in the workspace",
            bash,
            {
                "command": {"type": "string"},
                "timeout": {"type": "string", "description": "Seconds (default 120)"},
            },
            ["command"],
        ),
        make(
            "list_files",
            "List files (defaults to every file in the workspace)",
            list_files,
            {"pattern": {"type": "string"}},
            [],
        ),
        make(
            "grep",
            "Search files with a regular expression",
            grep,
            {
                "regex": {"type": "string"},
                "pattern": {"type": "string"},
            },
            ["regex"],
        ),
    ]
