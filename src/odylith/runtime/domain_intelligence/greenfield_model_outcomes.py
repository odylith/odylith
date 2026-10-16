"""Trusted model runtime outcomes, separate from candidate semantic rejection."""

from typing import Literal


class GreenfieldModelAuthoringError(RuntimeError):
    """A model-produced Product Intent could not be safely accepted."""


class GreenfieldModelRuntimeError(GreenfieldModelAuthoringError):
    """Expose fixed consumer copy without provider diagnostics or evidence text."""

    def __init__(self, reason: Literal["timeout", "unavailable"]) -> None:
        code, message = {
            "timeout": (
                "MODEL_TIMEOUT_NO_WRITE",
                "Greenfield exceeded its model time window; no records were created. Try again.",
            ),
            "unavailable": (
                "MODEL_UNAVAILABLE_NO_WRITE",
                "Greenfield model authoring is unavailable; no records were created. "
                "Check the configured provider and try again.",
            ),
        }[reason]
        self.outcome = {"kind": "environment", "code": code}
        super().__init__(message)
