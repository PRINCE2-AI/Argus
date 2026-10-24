"""Tool policy, deny patterns, and explicit approval boundaries."""

import re

READ_TOOLS = {"read_file", "list_files", "grep", "use_skill"}

DENY_PATTERNS = [
    # Destructive removal of roots, home directories, and parent directories.
    r"\brm\s+(?:-[^\s]+\s+)*(?:/|~|\$HOME|\.\.)(?:\s|/|$)",
    r"\brm\b[^\n]*(?:\.\./|/\.\.)",
    r"\brm\b[^\n]*(?:\.git|\.argus)(?:\s|$|[;&|])",
    # Leaving the workspace or touching protected files from a shell.
    r"\b(?:cd|pushd)\s+(?:\.\.(?=[/;\s]|$)|/|~|\$HOME)",
    r"\b(?:cat|less|more|head|tail|grep|base64|xxd|od|strings)\b[^\n]*\.env(?:\s|$|[;&|])",
    r"\b(?:cp|mv|scp|rsync|tar|zip)\s+(?:-[^\s]+\s+)*\.env(?:\s|$|[;&|])",
    r"\bfind\b[^\n]*-delete\b",
    # Privilege escalation and system-level operations.
    r"\b(?:sudo|doas)\b",
    r"\b(?:shutdown|reboot|halt|poweroff|mkfs(?:\.[^\s]+)?)\b",
    r"\bdd\s+if=",
    r"\bch(?:mod|own)\s+(?:-[^\s]+\s+)*[^\s]+\s+(?:/|~|\$HOME)(?:\s|$)",
    # Writes to system or home paths.
    r">>?\s*(?:/(?:etc|dev|proc|sys|boot)\b|~|\$HOME)",
    # Downloads piped directly into an interpreter.
    r"\b(?:curl|wget)\b[^|\n]*\|\s*(?:sh|bash|zsh|python[0-9.]*|perl|ruby|node)\b",
    # Reverse shells and cloud metadata access.
    r"\b(?:bash|sh)\s+-i\b[^\n]*/dev/tcp",
    r"\bnc(?:at)?\b[^\n]*-e\s",
    r"169\.254\.169\.254",
    # Force-pushing or discarding uncommitted work.
    r"\bgit\s+push\b[^\n]*(?:--force(?:-with-lease)?|\s-f(?:\s|$))",
    r"\bgit\s+clean\s+[^\n]*-[a-z]*f",
    r"\bgit\s+reset\s+--hard\b",
    # Fork bomb.
    r":\s*\(\s*\)\s*\{[^\n]*:\s*\|\s*:",
]


class Policy:
    """Decide whether a tool call is allowed under a named safety mode."""

    def __init__(self, mode="safe", approver=None, decision_model=None):
        self.mode = None
        self.set_mode(mode)
        self.approver = approver or (lambda call, reason: False)
        self.decision_model = decision_model

    def set_mode(self, mode):
        """Change the policy mode after validating it."""
        if mode not in {"read-only", "safe", "yolo"}:
            raise ValueError("mode must be 'read-only', 'safe', or 'yolo'")
        self.mode = mode

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
                    risk = decision.get("choice")
                    if risk not in {"safe", "review", "dangerous"}:
                        return "Jev returned an unknown risk; command requires review"
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
