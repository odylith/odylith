"""Versioned plan contract for multi-step agent execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AgentPlanStep:
    step_id: str
    summary: str
    owner: str
    stop_condition: str

    def to_payload(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class AgentPlanV1:
    plan_id: str
    route_id: str
    steps: list[AgentPlanStep]
    delegation_recommendation: str

    def to_payload(self) -> dict[str, object]:
        return {
            "schema": "agent_plan.v1",
            "plan_id": self.plan_id,
            "route_id": self.route_id,
            "steps": [step.to_payload() for step in self.steps],
            "delegation_recommendation": self.delegation_recommendation,
        }
