"""Environment loading shared by providers, tools, and the CLI."""

import os


def load_env_file(path=None):
    """Load KEY=VALUE pairs without overwriting the current environment."""
    candidates = [path] if path else [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
        ),
    ]
    for candidate in candidates:
        if not candidate or not os.path.isfile(candidate):
            continue
        with open(candidate, encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                name = name.strip()
                value = value.strip().strip("\"'")
                if name and name not in os.environ:
                    os.environ[name] = value
        return candidate
    return None


def env(name, default=None):
    """Read an environment variable after loading the nearest .env file."""
    load_env_file()
    return os.environ.get(name, default)


def first_env(*names, default=None):
    """Return the first configured environment variable from a group."""
    load_env_file()
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default
