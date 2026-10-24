"""Argus command-line front door, approval flow, and fleet runner."""

import argparse
import json
import os
import sys
import time

from . import __version__, session
from .fleet import run_fleet
from .harness import Harness
from .i18n import LANGUAGES, resolve_lang, t
from .providers import ProviderError, available_providers, get_provider
from .security import Policy

YES_WORDS = {"y", "yes", "s", "si", "sí", "o", "oui", "ha", "haan", "हाँ", "हां"}


def _configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


def _clip(value, limit=160):
    """Render a compact one-line representation of an event value."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."


class Ui:
    """Render localized events and approval prompts."""

    def __init__(self, lang=None):
        self.lang = resolve_lang(lang)
        self.color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

    def t(self, key, **values):
        return t(key, self.lang, **values)

    def set_lang(self, code):
        if code in LANGUAGES:
            self.lang = resolve_lang(code)
            return True
        return False

    def _dim(self, text):
        return f"\033[2m{text}\033[0m" if self.color else text

    def _red(self, text):
        return f"\033[31m{text}\033[0m" if self.color else text

    def event(self, kind, payload):
        if kind == "assistant" and payload.get("text"):
            print(payload["text"])
        elif kind == "tool_start":
            print(
                self.t(
                    "tool_call",
                    name=payload.get("name", ""),
                    args=_clip(payload.get("args", {})),
                )
            )
        elif kind == "tool_end":
            lines = (payload.get("result") or "").splitlines() or [""]
            first = lines[0][:240]
            if first.startswith(("ERROR", "BLOCKED")):
                print(self._red(first))
            else:
                print(self._dim(first))
        elif kind == "turn_limit":
            print(self._red(self.t("turn_limit")))

    def approver(self, call, reason):
        print(
            self.t(
                "approval",
                name=call.get("name", ""),
                args=_clip(call.get("args", {})),
            )
        )
        print(self._dim(f"  {reason}"))
        try:
            answer = input()
        except EOFError:
            return False
        return answer.strip().lower() in YES_WORDS


def _parser(ui):
    parser = argparse.ArgumentParser(description=ui.t("cli_description"))
    parser.add_argument("-p", "--prompt", help=ui.t("help_prompt"))
    parser.add_argument("-d", "--workdir", default=".", help=ui.t("help_workdir"))
    parser.add_argument("-m", "--model", help=ui.t("help_model"))
    parser.add_argument(
        "--provider",
        choices=available_providers(),
        help=ui.t("help_provider"),
    )
    parser.add_argument("--base-url", help="override the provider API base URL")
    parser.add_argument(
        "--mode",
        choices=("safe", "yolo", "read-only"),
        help=ui.t("help_mode"),
    )
    parser.add_argument("--yes", action="store_true", help=ui.t("help_yes"))
    parser.add_argument(
        "--max-turns", type=int, default=120, help=ui.t("help_max_turns")
    )
    parser.add_argument(
        "--budget-tokens",
        type=int,
        default=600_000,
        help=ui.t("help_budget"),
    )
    parser.add_argument("--lang", choices=sorted(LANGUAGES), help=ui.t("help_lang"))
    parser.add_argument(
        "--version", action="version", version=f"argus {__version__}"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--resume", action="store_true", help=ui.t("help_resume"))
    group.add_argument("--session", metavar="PATH", help=ui.t("help_session"))
    parser.add_argument(
        "--list-sessions", action="store_true", help=ui.t("help_list_sessions")
    )
    parser.add_argument("--fleet", metavar="FILE", help=ui.t("help_fleet"))
    parser.add_argument(
        "--workers", type=int, default=4, help=ui.t("help_workers")
    )
    return parser


def _policy(args, ui):
    mode = args.mode or "safe"
    if args.yes and mode == "safe":
        policy = Policy(mode)
        policy.approver = lambda call, reason: True
        return policy
    approver = ui.approver if mode == "safe" and sys.stdin.isatty() else None
    return Policy(mode, approver=approver)


def _warn_headless(args, ui, policy):
    if policy.mode == "safe" and not args.yes and not sys.stdin.isatty():
        print(ui.t("headless_warning"))


def _print_sessions(args, ui):
    sessions = session.list_sessions(args.workdir)
    if not sessions:
        print(ui.t("no_sessions"))
        return 0
    print(ui.t("list_sessions_header", workdir=os.path.realpath(args.workdir)))
    for item in sessions:
        stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(item["mtime"]))
        print(f"{stamp}  {item['size']:>8}  {item['path']}")
        if item["preview"]:
            print(f"          {item['preview']}")
    return 0


def _make_harness(args, ui, policy, provider):
    return Harness(
        args.workdir,
        provider=provider,
        policy=policy,
        on_event=ui.event,
        max_turns=args.max_turns,
        budget_tokens=args.budget_tokens,
    )


def _resume_if_requested(harness, args, ui):
    if args.session:
        if not harness.resume(args.session):
            print(ui.t("no_session"))
    elif args.resume:
        if not harness.resume():
            print(ui.t("no_session"))
        else:
            print(ui.t("session_loaded", path=harness.session_path))


def _run_prompt(args, ui):
    policy = _policy(args, ui)
    _warn_headless(args, ui, policy)
    try:
        provider = get_provider(
            args.provider, model=args.model, base_url=args.base_url
        )
        harness = _make_harness(args, ui, policy, provider)
        _resume_if_requested(harness, args, ui)
        harness.run(args.prompt)
        return 0
    except ProviderError as error:
        print(ui.t("error", error=error))
        return 1
    except Exception as error:
        print(ui.t("error", error=f"{type(error).__name__}: {error}"))
        return 1


def _run_fleet(args, ui):
    try:
        with open(args.fleet, encoding="utf-8") as fleet_file:
            jobs = json.load(fleet_file)
    except (OSError, json.JSONDecodeError) as error:
        print(ui.t("error", error=error))
        return 1
    if isinstance(jobs, dict):
        jobs = jobs.get("jobs", [])
    if not isinstance(jobs, list) or not jobs:
        print(ui.t("error", error="fleet file must contain a non-empty job list"))
        return 1
    for job in jobs:
        if not isinstance(job, dict) or not {"name", "workdir", "task"} <= set(job):
            print(ui.t("error", error="each job needs name, workdir, and task"))
            return 1
    policy = _policy(args, ui)
    _warn_headless(args, ui, policy)
    provider = get_provider(args.provider, model=args.model, base_url=args.base_url)
    print(ui.t("fleet_start", count=len(jobs), workers=args.workers))

    def make_harness(workdir):
        return Harness(
            workdir,
            provider=provider,
            policy=policy,
            on_event=ui.event,
            max_turns=args.max_turns,
            budget_tokens=args.budget_tokens,
        )

    results = run_fleet(jobs, make_harness, max_workers=max(1, args.workers))
    failed = False
    for index, result in enumerate(results, 1):
        status = ui.t("status_ok" if result["ok"] else "status_failed")
        print(
            ui.t(
                "fleet_line",
                index=index,
                count=len(results),
                name=result["name"],
                status=status,
                seconds=result.get("seconds", 0.0),
            )
        )
        print(result["report"])
        failed = failed or not result["ok"]
    print(ui.t("fleet_done"))
    return 1 if failed else 0


def _command(task, harness, ui):
    parts = task.split()
    command = parts[0].lower()
    if command in {"/exit", "/quit"}:
        return "exit"
    if command == "/help":
        print(ui.t("help_body"))
    elif command == "/mode" and len(parts) == 2:
        try:
            harness.policy.set_mode(parts[1])
            print(ui.t("mode_set", mode=harness.policy.mode))
        except ValueError as error:
            print(ui.t("error", error=error))
    elif command == "/session":
        print(ui.t("session_path", path=harness.session_path or "(not started)"))
    elif command == "/tokens":
        print(
            ui.t(
                "tokens",
                input=harness.usage.get("input", 0),
                output=harness.usage.get("output", 0),
            )
        )
    elif command == "/lang" and len(parts) == 2 and ui.set_lang(parts[1]):
        print(ui.t("lang_set", language=LANGUAGES[ui.lang]))
    else:
        print(ui.t("unknown_command", command=command))
    return None


def _interactive(args, ui):
    policy = _policy(args, ui)
    try:
        provider = get_provider(
            args.provider, model=args.model, base_url=args.base_url
        )
        harness = _make_harness(args, ui, policy, provider)
    except ProviderError as error:
        print(ui.t("error", error=error))
        return 1
    _resume_if_requested(harness, args, ui)
    print(
        ui.t(
            "banner",
            version=__version__,
            provider=harness.provider_name,
            model=harness.model,
            mode=policy.mode,
            workdir=harness.workdir,
        )
    )
    while True:
        try:
            task = input(ui.t("prompt"))
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            continue
        task = task.strip()
        if not task:
            continue
        if task.startswith("/"):
            if _command(task, harness, ui) == "exit":
                return 0
            continue
        try:
            harness.run(task)
        except KeyboardInterrupt:
            print()
            print(ui.t("interrupted"))
        except ProviderError as error:
            print(ui.t("error", error=error))
        except Exception as error:
            print(ui.t("error", error=f"{type(error).__name__}: {error}"))


def main(argv=None):
    """Run Argus in headless, interactive, fleet, or session-listing mode."""
    _configure_stdio()
    ui = Ui()
    args = _parser(ui).parse_args(argv)
    if args.lang:
        ui.set_lang(args.lang)
    if args.list_sessions:
        return _print_sessions(args, ui)
    if args.fleet:
        if args.prompt:
            _parser(ui).error("--fleet cannot be combined with --prompt")
        return _run_fleet(args, ui)
    if args.prompt:
        return _run_prompt(args, ui)
    return _interactive(args, ui)
