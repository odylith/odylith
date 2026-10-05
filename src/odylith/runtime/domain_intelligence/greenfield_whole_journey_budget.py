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
WHOLE_JOURNEY_ELAPSED_SCOPE = "through_guardian_completion_record_and_final_clock_check_before_receipt_delivery"


@dataclass
class JourneyObservationFinalizer:
    """Reconcile final publication with one whole/proposal elapsed-time law."""

    observation: dict[str, Any]
    started: float
    clock: Callable[[], float]
    parent_clock: Callable[[], float]
    settled_parent_time: float = 0.0
    body_whole: float | None = None
    body_proposal: float | None = None

    def record_body(self, whole: float, proposal: float) -> None:
        self.body_whole, self.body_proposal = whole, proposal

    def settled(self) -> float:
        from odylith.runtime.domain_intelligence.greenfield_process import JourneyCancelled
        self.settled_parent_time = self.parent_clock()
        elapsed = self.clock() - self.started
        prior = self.body_whole if self.body_whole is not None else float(self.observation["whole_journey_seconds"])
        body_proposal = self.body_proposal if self.body_proposal is not None else float(self.observation["proposal_phase_elapsed_seconds"])
        proposal = body_proposal + elapsed - prior
        self._update(elapsed, proposal)
        if elapsed >= PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS:
            raise JourneyCancelled("Greenfield guarded settlement exceeded its deadline")
        remaining = float(self.observation["operational_timeout_seconds"]) - proposal
        if remaining <= 0:
            raise JourneyCancelled("Greenfield proposal exceeded its operational timeout at settlement")
        return remaining

    def published(self, finished: float) -> None:
        delta = finished - self.settled_parent_time
        self._update(float(self.observation["whole_journey_seconds"]) + delta,
                     float(self.observation["proposal_phase_elapsed_seconds"]) + delta)

    def _update(self, whole: float, proposal: float) -> None:
        self.observation.update(whole_journey_seconds=round(whole, 3),
            proposal_phase_elapsed_seconds=round(proposal, 3), elapsed_seconds=round(proposal, 3))


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
    from odylith.runtime.domain_intelligence.greenfield_process import (
        JOURNEY_CANCELLATION_GRACE_SECONDS, JOURNEY_SUPERVISION_VERSION,
    )
    supervision = stage.get("whole_journey_supervision")
    if (stage.get("whole_journey_route") != "odylith-greenfield-prepare.v1"
            or not isinstance(supervision, Mapping)
            or set(supervision) != {"version", "guardian_pid", "cancellation_grace_seconds"}
            or supervision.get("version") != JOURNEY_SUPERVISION_VERSION
            or type(supervision.get("guardian_pid")) is not int
            or supervision.get("guardian_pid", 0) <= 0
            or supervision.get("cancellation_grace_seconds") != JOURNEY_CANCELLATION_GRACE_SECONDS):
        issues.append("whole journey has no product-owned parent supervision evidence")
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
