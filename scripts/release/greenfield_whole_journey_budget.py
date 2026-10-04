"""Own the provisional diagnostic deadline and retained-proof contract."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    GREENFIELD_COMPLETION_RESERVE_SECONDS,
)


# Fixed shared cap, independent of the sum of individual maximum phase budgets.
# Public measurement has not qualified this as a release-wide operating bound.
PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS = 660.0
WHOLE_JOURNEY_ELAPSED_SCOPE = "through_observer_return_before_final_snapshot_serialization"


@dataclass(frozen=True)
class WholeJourneyDeadline:
    """Own one monotonic deadline that no phase may extend or replenish."""

    started: float
    clock: Callable[[], float]

    @property
    def cap_seconds(self) -> float:
        return PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS

    def remaining(self) -> float:
        remaining = self.cap_seconds - (self.clock() - self.started)
        if remaining <= 0:
            raise TimeoutError("host-native whole journey diagnostic deadline expired")
        return remaining

    def request_timeout(self, phase_remaining: float, *, reserve_seconds: float = 0.0) -> float:
        if not _finite_seconds(reserve_seconds):
            raise ValueError("whole journey completion reserve must be finite and nonnegative")
        available = self.remaining() - reserve_seconds
        if available <= 0:
            raise TimeoutError("host-native whole journey has no candidate completion reserve")
        return min(phase_remaining, available)

    def expired(self) -> bool:
        return self.clock() - self.started >= self.cap_seconds


def whole_journey_observation_issues(stage: Mapping[str, Any]) -> list[str]:
    """Reject a purported successful flow whose fixed-deadline proof is absent."""

    issues: list[str] = []
    if stage.get("whole_journey_diagnostic_cap_seconds") != PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS:
        issues.append("whole journey diagnostic cap does not match the fixed budget")
    if stage.get("candidate_completion_reserve_seconds") != GREENFIELD_COMPLETION_RESERVE_SECONDS:
        issues.append("candidate completion reserve does not match the fixed budget")
    if stage.get("whole_journey_bound_status") != "diagnostic_unqualified":
        issues.append("whole journey bound must remain diagnostic_unqualified")
    if stage.get("whole_journey_deadline_status") != "within":
        issues.append("whole journey deadline was not within its diagnostic cap")
    if stage.get("whole_journey_elapsed_scope") != WHOLE_JOURNEY_ELAPSED_SCOPE:
        issues.append("whole journey elapsed scope does not match its final snapshot boundary")
    elapsed = stage.get("whole_journey_seconds")
    if not _finite_seconds(elapsed) or elapsed >= PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS:
        issues.append("whole journey elapsed time must be finite and below its diagnostic cap")
    proposal_elapsed = stage.get("proposal_phase_elapsed_seconds")
    legacy_elapsed = stage.get("elapsed_seconds")
    if (not _finite_seconds(proposal_elapsed) or not _finite_seconds(legacy_elapsed)
            or proposal_elapsed != legacy_elapsed):
        issues.append("proposal phase elapsed time must be finite and match legacy elapsed_seconds")
    return issues


def _finite_seconds(value: object) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)
