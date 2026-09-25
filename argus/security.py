"""Day 2: teach tool policy, deny patterns, and explicit approval boundaries."""

import re

READ_TOOLS = {"read_file", "list_files", "grep"}
DENY_PATTERNS = [
    r"\brm\s+(?:-[^\s]*f[^\s]*\s+)?(?:-r[^\s]*\s+)?(?:/|~|\$HOME)(?:\s|$)",
    r"\bsudo\b",
    r"\b(?:mkfs(?:\.[^\s]+)?|dd\s+if=)",
    r"\bcurl\b[^|\n]*\|\s*(?:sh|bash)\b",
    r"\bgit\s+push\b[^|\n]*\s--force(?:\s|$)",
    r">\s*/dev/sd[a-z]\b",
]


class Policy:
    """Decide whether a tool call is allowed under a named safety mode."""

    def __init__(self, mode="safe", approver=None, decision_model=None):
        if mode not in {"read-only", "safe", "yolo"}:
            raise ValueError("mode must be 'read-only', 'safe', or 'yolo'")
        self.mode = mode
        self.approver = approver or (lambda call, reason: False)
        self.decision_model = decision_model

    def check(self, call):
        """Return None to allow a call, otherwise return its blocking reason."""
        name = call.get("name", "")
        if name == "bash":
            command = call.get("args", {}).get("command", "")
            if any(re.search(pattern, command) for pattern in DENY_PATTERNS):
                return "command matches a safety deny pattern"
            if self.decision_model:
                try:
                    from .jev import command_risk

                    decision = command_risk(self.decision_model, command)
                    risk = decision["choice"]
                    if decision["confidence"] < 0.6:
                        return "Jev confidence is too low; command requires review"
                    if risk == "dangerous":
                        return "Jev classified this command as dangerous"
                    if risk == "review" and self.mode != "yolo":
                        return "Jev classified this command as requiring review"
                except Exception as error:
                    if self.mode != "read-only":
                        return f"Jev safety check unavailable: {error}"
        if name in READ_TOOLS or self.mode == "yolo":
            return None
        if self.mode == "read-only":
            return "read-only policy blocks this tool"
        reason = "safe policy requires approval"
        if self.approver(call, reason):
            return None
        return reason
