from __future__ import annotations

from typing import Sequence

from odylith.runtime.execution_engine.contract import ContradictionRecord
from odylith.runtime.execution_engine.contract import ExecutionContract


def detect_contradictions(
    contract: ExecutionContract,
    *,
    intended_action: str,
    user_instructions: Sequence[str] = (),
    docs: Sequence[str] = (),
    live_state: Sequence[str] = (),
) -> tuple[ContradictionRecord, ...]:
    action = str(intended_action or "").strip().lower()
    records: list[ContradictionRecord] = []

    if "authoritative" in contract.authoritative_lane.lower() and "fixture" in action:
        records.append(
            ContradictionRecord(
                source="contract",
                claim=f"authoritative lane `{contract.authoritative_lane}`",
                conflicting_evidence=f"intended action `{intended_action}` targets a local fixture path",
                severity="high",
                blocks_execution=True,
            )
        )

    for instruction in user_instructions:
        normalized = str(instruction or "").strip().lower()
        if "do not use" in normalized:
            forbidden = normalized.split("do not use", 1)[1].strip().strip("`'\"")
            if forbidden and forbidden in action:
                records.append(
                    ContradictionRecord(
                        source="user_instruction",
                        claim=instruction,
                        conflicting_evidence=f"intended action `{intended_action}` still uses `{forbidden}`",
                        severity="high",
                        blocks_execution=True,
                    )
                )
        if "only use" in normalized:
            required = normalized.split("only use", 1)[1].strip().strip("`'\"")
            if required and required not in action:
                records.append(
                    ContradictionRecord(
                        source="user_instruction",
                        claim=instruction,
                        conflicting_evidence=f"intended action `{intended_action}` does not stay within `{required}`",
                        severity="medium",
                        blocks_execution="fixture" in action,
                    )
                )

    for document in docs:
        normalized = str(document or "").strip().lower()
        if normalized.startswith("forbidden:"):
            forbidden = normalized.split(":", 1)[1].strip()
            if forbidden and forbidden in action:
                records.append(
                    ContradictionRecord(
                        source="doc",
                        claim=document,
                        conflicting_evidence=f"intended action `{intended_action}` uses forbidden token `{forbidden}`",
                        severity="medium",
                        blocks_execution=True,
                    )
                )

    for status in live_state:
        normalized = str(status or "").strip().lower()
        if "blocked on token refresh" in normalized and action.startswith("deploy"):
            records.append(
                ContradictionRecord(
                    source="live_state",
                    claim=status,
                    conflicting_evidence=f"intended action `{intended_action}` would continue deployment while auth is blocked",
                    severity="high",
                    blocks_execution=True,
                )
            )

    return tuple(records)
