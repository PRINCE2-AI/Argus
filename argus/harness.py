"""Compose providers, tools, policy, memory, skills, sessions, and delegation."""

import os

from . import context, loop, memory, session, skills
from .providers import Provider, get_provider
from .security import Policy
from .subagent import subagent_tool
from .tools import core_tools, tool


class Harness:
    """Compose Argus tools, policy, memory, skills, sessions, and the loop."""

    def __init__(self, workdir=".", model=None, policy=None, extra_tools=None,
                 system_extra="", on_event=None, budget_tokens=600_000,
                 max_turns=120, session_path=None, enable_subagents=True,
                 persist=True, _depth=0, decision_model=None, provider=None,
                 api_key=None, base_url=None):
        self.workdir = os.path.realpath(workdir)
        os.makedirs(self.workdir, exist_ok=True)
        if isinstance(provider, Provider):
            self.provider = provider
        else:
            self.provider = get_provider(
                provider, model=model, api_key=api_key, base_url=base_url
            )
        self.model = self.provider.model
        self.provider_name = self.provider.name
        if policy is None:
            policy = Policy("safe", decision_model=decision_model)
        elif decision_model is not None:
            policy.decision_model = decision_model
        self.policy = policy
        self.on_event = on_event
        self.budget_tokens = budget_tokens
        self.max_turns = max_turns
        self.session_path = session_path
        self.persist = persist
        self.usage = {"input": 0, "output": 0, "total": 0}
        self.tools = {item.name: item for item in core_tools(self.workdir)}

        @tool("Remember a durable fact in project memory", note="The fact to remember")
        def remember(note):
            """Store a fact in the workspace's Argus memory file."""
            return memory.remember(self.workdir, note)

        self.tools[remember.name] = remember
        if skills.catalog(self.workdir):
            @tool("Load a workspace skill", name="The skill name to load")
            def use_skill(name):
                """Return the full text of a named workspace skill."""
                return skills.read_skill(self.workdir, name)

            self.tools[use_skill.name] = use_skill
        if enable_subagents:
            def make_child(depth):
                return Harness(
                    self.workdir,
                    provider=self.provider,
                    policy=self.policy,
                    system_extra=system_extra,
                    on_event=self.on_event,
                    budget_tokens=self.budget_tokens,
                    max_turns=self.max_turns,
                    enable_subagents=True,
                    persist=False,
                    _depth=depth,
                )

            child_tool = subagent_tool(make_child, _depth, 2)
            self.tools[child_tool.name] = child_tool
        if extra_tools:
            self.tools.update(
                {item.name: item for item in extra_tools}
                if isinstance(extra_tools, (list, tuple)) else extra_tools
            )
        prompt_extra = skills.catalog_prompt(self.workdir)
        if system_extra:
            prompt_extra = "\n\n".join(
                part for part in (prompt_extra, system_extra) if part
            )
        self.system = memory.build_system_prompt(self.workdir, prompt_extra)
        self.messages = []

    def resume(self, path=None):
        """Load a saved session into this harness."""
        chosen = path or self.session_path or session.latest(self.workdir)
        if not chosen or not os.path.isfile(chosen):
            return False
        loaded = session.load(chosen)
        if not loaded:
            return False
        self.messages = loaded
        self.session_path = chosen
        return True

    def run(self, task):
        """Run a task through the composed Argus agent and return its answer."""
        if self.persist and not self.session_path:
            self.session_path = session.new_session(self.workdir, task[:32])
        user_message = {"role": "user", "text": task}
        self.messages.append(user_message)
        if self.persist:
            session.append(self.session_path, user_message)
        recorded_index = len(self.messages)

        def record():
            nonlocal recorded_index
            if not self.persist:
                return
            recorded_index = min(recorded_index, len(self.messages))
            while recorded_index < len(self.messages):
                session.append(self.session_path, self.messages[recorded_index])
                recorded_index += 1

        def before_turn(messages):
            nonlocal recorded_index
            compacted = context.compact(
                self.provider, messages, self.budget_tokens
            )
            if compacted is not messages:
                messages[:] = compacted
                if self.persist:
                    session.append(self.session_path, messages[0])
                recorded_index = len(messages)
            record()
            return messages

        def event(kind, payload):
            if kind in {"assistant", "tool_end"}:
                record()
            elif kind == "usage":
                usage = payload or {}
                self.usage["input"] += int(usage.get("input", 0) or 0)
                self.usage["output"] += int(usage.get("output", 0) or 0)
                self.usage["total"] += int(usage.get("total", 0) or 0)
            if self.on_event:
                self.on_event(kind, payload)

        return loop.run(
            self.system,
            self.messages,
            self.tools,
            provider=self.provider,
            max_turns=self.max_turns,
            on_event=event,
            before_tool=self.policy.check,
            before_turn=before_turn,
        )
