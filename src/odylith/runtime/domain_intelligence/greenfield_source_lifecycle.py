"""Project validated source duties into one cited, passive state lifecycle.

The ledger owns the source meaning. The binding supplies only references to
accepted fields and design owners; this module neither chooses an actor nor
rewrites a transition effect.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_model_source_citations import (
    canonical_citation_from_host_selection,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
    GreenfieldSourceDutyBindingError,
    validate_greenfield_source_duty_binding,
    validate_greenfield_source_duty_design_binding,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    GreenfieldSourceDutyLedgerError,
    resolve_greenfield_transition_state_fields,
    verify_greenfield_source_duty_ledger_receipt,
)


SOURCE_LIFECYCLE_VERSION = "odylith.greenfield.source-lifecycle.v2"

_DESIGN_DUTY_FIELDS = {
    "conditional_guards": ("trigger", "protected_action", "rule"),
    "boundaries": ("kind", "rule"),
    "proof_duties": ("dossier_or_artifact", "must_show"),
}


class GreenfieldSourceLifecycleError(ValueError):
    """Source custody or a declared state-field relationship is invalid."""


def _source_refs(evidence: bytes, refs: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [canonical_citation_from_host_selection(evidence, ref) for ref in refs]


def _sha256(value: Mapping[str, Any]) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _design_duties(
    *, ledger: Mapping[str, Any], binding: Mapping[str, Any],
    evidence: bytes, role: str,
) -> list[dict[str, Any]]:
    """Carry ledger-authored meaning through typed, source-ordered design ownership."""

    return [
        {
            "duty_id": duty["id"],
            **{field: duty[field] for field in _DESIGN_DUTY_FIELDS[role]},
            "component_key": owner["component_key"],
            "workstream_key": owner["workstream_key"],
            "source_refs": _source_refs(evidence, duty["source_refs"]),
        }
        for duty, owner in zip(ledger[role], binding[role])
    ]


def verified_source_design_duties(
    source_duty: Mapping[str, Any], *, role: str,
    components: Sequence[Mapping[str, Any]],
    workstreams: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Read canonical duties only when their source, binding, and owner agree."""

    if role not in _DESIGN_DUTY_FIELDS:
        raise GreenfieldSourceLifecycleError("unknown source duty role")
    receipt = source_duty.get("ledger_receipt")
    binding = source_duty.get("binding")
    lifecycle = source_duty.get("lifecycle")
    if not all(isinstance(row, Mapping) for row in (receipt, binding, lifecycle)):
        raise GreenfieldSourceLifecycleError("source duty custody is incomplete")
    ledger = receipt.get("ledger")
    if not isinstance(ledger, Mapping):
        raise GreenfieldSourceLifecycleError("source duty ledger is missing")
    if (
        receipt.get("ledger_sha256") != _sha256(ledger)
        or binding.get("ledger_sha256") != receipt["ledger_sha256"]
        or binding.get("source_sha256") != receipt.get("source_sha256")
        or lifecycle.get("ledger_sha256") != receipt["ledger_sha256"]
        or lifecycle.get("source_sha256") != receipt.get("source_sha256")
        or lifecycle.get("binding_sha256") != _sha256(binding)
        or lifecycle.get("lifecycle_sha256") != _sha256({
            key: value for key, value in lifecycle.items() if key != "lifecycle_sha256"
        })
    ):
        raise GreenfieldSourceLifecycleError("source duty projection custody is stale")
    duties, owners, projected = ledger.get(role), binding.get(role), lifecycle.get(role)
    if not all(isinstance(rows, list) for rows in (duties, owners, projected)):
        raise GreenfieldSourceLifecycleError(f"{role} projection is missing")
    if len(duties) != len(owners) or len(duties) != len(projected):
        raise GreenfieldSourceLifecycleError(f"{role} projection has incomplete coverage")
    component_keys = {row["key"] for row in components}
    workstream_by_key = {row["key"]: row for row in workstreams}
    for duty, owner, row in zip(duties, owners, projected):
        if not all(isinstance(value, Mapping) for value in (duty, owner, row)):
            raise GreenfieldSourceLifecycleError(f"{role} projection is malformed")
        expected = {
            "duty_id": duty["id"],
            **{field: duty[field] for field in _DESIGN_DUTY_FIELDS[role]},
            "component_key": owner["component_key"],
            "workstream_key": owner["workstream_key"],
        }
        if set(row) != {*expected, "source_refs"} or any(
            row.get(key) != value for key, value in expected.items()
        ):
            raise GreenfieldSourceLifecycleError(f"{role} projection differs from accepted duty")
        refs = row.get("source_refs")
        if (
            not isinstance(refs, list)
            or len(refs) != len(duty["source_refs"])
            or any(
                not isinstance(ref, Mapping)
                or ref.get("quote") != raw["quote"]
                or type(ref.get("occurrence")) is not int
                or ref["occurrence"] < 1
                for ref, raw in zip(refs, duty["source_refs"])
            )
        ):
            raise GreenfieldSourceLifecycleError(f"{role} citation projection differs from source")
        component_key = row["component_key"]
        workstream_key = row["workstream_key"]
        if (
            component_key not in component_keys
            or workstream_key not in workstream_by_key
            or component_key not in workstream_by_key[workstream_key]["component_keys"]
        ):
            raise GreenfieldSourceLifecycleError(f"{role} design owner is missing")
    return [dict(row) for row in projected]


def project_greenfield_source_lifecycle(
    *,
    ledger_receipt: Mapping[str, Any],
    binding: Mapping[str, Any],
    candidate_result: Mapping[str, Any],
    evidence_text: str,
) -> dict[str, Any]:
    """Return a detached canonical lifecycle after revalidating every input.

    Each effect is preserved in source order. The ledger must name the same
    governed object and field at both ends of a bound relationship. This is
    an exact identity check on source-authored labels, not a semantic guess.
    """

    try:
        receipt = verify_greenfield_source_duty_ledger_receipt(
            ledger_receipt, evidence_text=evidence_text
        )
        accepted_binding = validate_greenfield_source_duty_binding(
            binding,
            ledger_receipt=receipt,
            candidate_result=candidate_result,
            evidence_text=evidence_text,
        )
    except (GreenfieldSourceDutyLedgerError, GreenfieldSourceDutyBindingError) as exc:
        raise GreenfieldSourceLifecycleError("source lifecycle custody is invalid") from exc

    return _project_verified_source_lifecycle(
        receipt=receipt, binding=accepted_binding, evidence_text=evidence_text,
    )


def _project_verified_source_lifecycle(
    *, receipt: Mapping[str, Any], binding: Mapping[str, Any], evidence_text: str,
) -> dict[str, Any]:
    """Project already verified records for both admission and exact readback."""
    ledger = receipt["ledger"]
    evidence = evidence_text.encode("utf-8")
    fields = ledger["state_fields"]
    resolved_fields = resolve_greenfield_transition_state_fields(ledger)
    state_fields = [
        {
            "duty_id": row["id"],
            "state_object": row["state_object"],
            "field": row["field"],
            "meaning": row["meaning"],
            "source_refs": _source_refs(evidence, row["source_refs"]),
        }
        for row in fields
    ]

    off_path_transitions: list[dict[str, Any]] = []
    for duty, owner in zip(
        ledger["off_path_transitions"], binding["off_path_transitions"]
    ):
        effects: list[dict[str, Any]] = []
        for source_effect, field in zip(duty["effects"], resolved_fields[duty["id"]], strict=True):
            effects.append(
                {
                    "state_field_id": field["id"],
                    "field": source_effect["field"],
                    "change": source_effect["change"],
                    "observable_check": source_effect["observable_check"],
                }
            )
        off_path_transitions.append(
            {
                "duty_id": duty["id"],
                "trigger": duty["trigger"],
                "governed_object": duty["governed_object"],
                "effects": effects,
                "component_key": owner["component_key"],
                "workstream_key": owner["workstream_key"],
                "source_refs": _source_refs(evidence, duty["source_refs"]),
            }
        )

    lifecycle = {
        "version": SOURCE_LIFECYCLE_VERSION,
        "source_sha256": receipt["source_sha256"],
        "ledger_sha256": receipt["ledger_sha256"],
        "binding_sha256": _sha256(binding),
        "state_fields": state_fields,
        "off_path_transitions": off_path_transitions,
        **{
            role: _design_duties(
                ledger=ledger, binding=binding, evidence=evidence, role=role,
            )
            for role in _DESIGN_DUTY_FIELDS
        },
    }
    lifecycle["lifecycle_sha256"] = _sha256(lifecycle)
    return lifecycle


def require_verified_greenfield_source_lifecycle(
    source_duty: Mapping[str, Any], *, evidence_text: str,
    provisional_design: Mapping[str, Any],
) -> None:
    """Require the complete passive projection of accepted source duties.

    Rehashing exported records cannot authorize new state meaning, effects,
    citations or owners. Raw candidate citations remain admission-owned and
    are neither reconstructed nor inferred during this readback.
    """
    if not isinstance(source_duty, Mapping) or set(source_duty) != {
        "ledger_receipt", "binding", "lifecycle"
    }:
        raise GreenfieldSourceLifecycleError("source duty custody is incomplete")
    receipt, binding, lifecycle = (
        source_duty["ledger_receipt"], source_duty["binding"], source_duty["lifecycle"]
    )
    if not all(isinstance(row, Mapping) for row in (receipt, binding, lifecycle)):
        raise GreenfieldSourceLifecycleError("source duty custody is incomplete")
    try:
        receipt = verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=evidence_text)
        if (
            binding.get("source_sha256") != receipt["source_sha256"]
            or binding.get("ledger_sha256") != receipt["ledger_sha256"]
        ):
            raise GreenfieldSourceLifecycleError("source duty projection custody is stale")
        validate_greenfield_source_duty_design_binding(
            binding, ledger=receipt["ledger"], provisional_design=provisional_design,
        )
        expected = _project_verified_source_lifecycle(
            receipt=receipt, binding=binding, evidence_text=evidence_text,
        )
    except (GreenfieldSourceDutyLedgerError, GreenfieldSourceDutyBindingError) as exc:
        raise GreenfieldSourceLifecycleError("source lifecycle custody is invalid") from exc
    if dict(lifecycle) != expected or _sha256(lifecycle) != _sha256(expected):
        raise GreenfieldSourceLifecycleError("source lifecycle differs from its accepted duty projection")


__all__ = [
    "GreenfieldSourceLifecycleError",
    "SOURCE_LIFECYCLE_VERSION",
    "project_greenfield_source_lifecycle",
    "require_verified_greenfield_source_lifecycle",
    "verified_source_design_duties",
]
