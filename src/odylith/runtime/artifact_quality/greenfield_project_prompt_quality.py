"""Structural quality checks for Greenfield implementation prompts."""

from __future__ import annotations

from collections.abc import Mapping

from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedArtifact
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_handoff_contract import (
    PROJECT_HANDOFF_STEP_SEQUENCE,
    project_handoff_step_contract_issues,
)


_PROJECT_PROMPT_REQUIRED_FIELDS = ("label", "when", "prompt", "result", "stop")


def project_implementation_prompt_issues(artifact: RenderedArtifact) -> list[str]:
    """Validate presentation presence and its typed action contract.

    Product meaning and implementation obligations are never inferred from the
    visible prompt. General copy-quality checks own grammar and legibility;
    this gate owns only sequence identity and structural completeness.
    """

    if artifact.surface != "Project implementation prompt":
        return []
    raw_fields = dict(artifact.fields)
    fields = {
        key: normalize_string(value)
        for key, value in raw_fields.items()
    }
    issues: list[str] = []
    missing = [key for key in _PROJECT_PROMPT_REQUIRED_FIELDS if not fields.get(key)]
    if missing:
        issues.append(f"{artifact.identity} is missing prompt fields: {', '.join(missing)}")
    position = _position(fields.get("position", ""))
    if position < 1 or position > len(PROJECT_HANDOFF_STEP_SEQUENCE):
        issues.append(f"{artifact.identity} has an invalid typed handoff sequence position")
        return issues
    expected_step_id = PROJECT_HANDOFF_STEP_SEQUENCE[position - 1]
    explicit_step_id = normalize_string(fields.get("step_id"))
    if explicit_step_id != expected_step_id:
        issues.append(f"{artifact.identity} has a step identity that does not match its sequence position")
    issues.extend(
        f"{artifact.identity} {issue}"
        for issue in project_handoff_step_contract_issues(
            artifact.contract
            or (
                raw_fields.get("contract")
                if isinstance(raw_fields.get("contract"), Mapping)
                else {}
            ),
            expected_step_id=expected_step_id,
        )
    )
    return issues


def _position(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


__all__ = ["project_implementation_prompt_issues"]
