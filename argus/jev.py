"""Optional Jev decision client for fast, typed Argus routing and safety checks."""

import json
import os
import urllib.error
import urllib.request

DEFAULT_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"


class JevError(RuntimeError):
    """Report an unavailable, invalid, or rejected Jev decision."""


class Jev:
    """Call Jev's structured decision endpoint without third-party packages."""

    def __init__(self, api_key=None, model=None, endpoint=None, timeout=30):
        self.api_key = api_key or os.environ.get("JEV_API_KEY")
        self.model = model or os.environ.get("JEV_MODEL", DEFAULT_MODEL)
        self.endpoint = endpoint or os.environ.get("JEV_ENDPOINT", DEFAULT_ENDPOINT)
        self.timeout = timeout
        if not self.api_key:
            raise JevError("Set JEV_API_KEY before using Jev.")

    def decide(self, state, questions):
        """Return validated structured decisions from Jev."""
        body = {"model": self.model, "state": state, "questions": questions}
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:400]
            raise JevError(f"Jev HTTP {error.code}: {detail}") from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise JevError(f"Jev request failed: {error}") from error
        return _validate_decisions(result)


def _validate_decisions(result):
    """Normalize Jev answers and reject malformed confidence values."""
    answers = result.get("answers", result.get("decisions", result))
    if not isinstance(answers, dict):
        raise JevError("Jev response did not contain a decision object.")
    normalized = {}
    for name, answer in answers.items():
        if isinstance(answer, dict):
            value = answer.get("choice", answer.get("value", answer.get("answer")))
            confidence = answer.get("confidence", answer.get("probability", 0.0))
        else:
            value, confidence = answer, 0.0
        try:
            confidence = float(confidence)
        except (TypeError, ValueError) as error:
            raise JevError(f"Invalid confidence for decision {name!r}.") from error
        if not 0.0 <= confidence <= 1.0:
            raise JevError(f"Confidence for decision {name!r} is outside 0..1.")
        normalized[name] = {"choice": value, "confidence": confidence}
    return normalized


def command_risk(decision_model, command):
    """Classify a shell command as safe, review, or dangerous."""
    decisions = decision_model.decide(
        command,
        {
            "risk": {
                "type": "choice",
                "instructions": "Classify the shell command's operational risk.",
                "criteria": {
                    "safe": "Read-only or reversible command.",
                    "review": "Mutating command requiring human review.",
                    "dangerous": "Destructive, credential, or system-level command.",
                },
            }
        },
    )
    return decisions["risk"]
