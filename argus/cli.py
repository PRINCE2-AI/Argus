"""Day 5: teach Argus a usable command-line front door and approval flow."""

import argparse
import json

from .harness import Harness
from .security import Policy


def _clip(value, limit=160):
    """Render a compact one-line representation of an event value."""
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def event_printer(kind, payload):
    """Print assistant, tool-call, and tool-result events."""
    if kind == "assistant" and payload.get("text"):
        print(payload["text"])
    elif kind == "tool_start":
        print(f"[tool] {payload.get('name', '')} {_clip(payload.get('args', {}))}")
    elif kind == "tool_end":
        result = payload.get("result", "").splitlines() or [""]
        print(f"\033[2m{result[0]}\033[0m")


def approver(call, reason):
    """Ask for interactive approval of a safe-mode tool call."""
    print(f"{call.get('name', '')} {_clip(call.get('args', {}))}: {reason}")
    try:
        answer = input("approve ...? [y/N] ")
    except EOFError:
        return False
    return answer.strip().lower() in {"y", "yes"}


def _parser():
    """Build the Argus command-line parser."""
    parser = argparse.ArgumentParser(description="Argus agent harness")
    parser.add_argument("-p", "--prompt", help="run one headless task")
    parser.add_argument("-d", "--workdir", default=".", help="workspace directory")
    parser.add_argument("-m", "--model", help="Gemini model name")
    parser.add_argument("--mode", choices=("safe", "yolo", "read-only"))
    parser.add_argument("--resume", action="store_true", help="resume the newest session")
    parser.add_argument("--max-turns", type=int, default=120)
    return parser


def main(argv=None):
    """Run Argus in headless or interactive mode."""
    args = _parser().parse_args(argv)
    mode = args.mode or ("yolo" if args.prompt else "safe")
    policy = Policy(mode, approver if mode == "safe" else None)
    harness = Harness(
        args.workdir, model=args.model, policy=policy,
        on_event=event_printer, max_turns=args.max_turns,
    )
    if args.resume and not harness.resume():
        print("No saved Argus session found to resume.")
    if args.prompt:
        harness.run(args.prompt)
        return 0
    print(f"Argus | model={harness.model} | mode={mode} | jail={harness.workdir}")
    while True:
        try:
            task = input("argus> ")
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\nSession log is safe; use --resume to continue it.")
            continue
        if not task.strip():
            continue
        try:
            harness.run(task)
        except KeyboardInterrupt:
            print("\nSession log is safe; use --resume to continue it.")
        except Exception as error:
            print(f"ERROR: {type(error).__name__}: {error}")
