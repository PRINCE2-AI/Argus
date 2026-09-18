"""Day 4: teach bounded delegation to fresh Argus sub-agents."""

from .tools import Tool, tool


def subagent_tool(make_harness, depth=0, max_depth=2):
    """Build a tool that delegates one self-contained task to a child harness."""
    @tool(
        "Delegate a self-contained task to a fresh sub-agent with its own clean "
        "context. The child cannot see this conversation and returns its final report.",
        task="The self-contained task for the fresh sub-agent",
    )
    def spawn_agent(task):
        """Run a delegated task unless the configured depth limit is reached."""
        if depth >= max_depth:
            return "ERROR: sub-agent depth limit reached; do this task yourself"
        child = make_harness(depth + 1)
        return child.run(task)

    return spawn_agent
