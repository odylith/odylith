"""One lossless citation-bank view and derived reference order for source duties."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

ACTION_SECTIONS = frozenset(
    ("first_path_actions", "supporting_human_actions", "system_duties")
)
DUTY_SECTIONS = (
    ("first_path_actions", "first_path_action"),
    ("supporting_human_actions", "supporting_human_action"),
    ("system_duties", "system_duty"),
    ("state_fields", "state_field"),
    ("off_path_transitions", "off_path_transition"),
    ("conditional_guards", "conditional_guard"),
    ("boundaries", "boundary"),
    ("proof_duties", "proof_duty"),
)
MAX_DERIVED_REFS = 5
MAX_COMPACT_CITATIONS = 256
SOURCE_DUTY_COMPACT_VERSION = "odylith.greenfield.source-duty-compact.v3"


def duty_references(section: str, row: Mapping[str, Any]) -> tuple[list, list]:
    """Compiler-defined indexes: event/actor first, then authored extra context."""

    def unique(refs: list) -> list:
        found: list = []
        for ref in refs:
            if ref not in found:
                found.append(ref)
        return found

    if section in ACTION_SECTIONS:
        return (
            unique([row["event_ref"], *row["source_refs"]]),
            unique([row["actor_ref"], *row["role_refs"]]),
        )
    refs = unique(list(row["source_refs"]))
    return (refs, list(refs))


def compact_source_duty_view(ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Intern exact citations once; preserve every material field and row order."""
    bank: list[dict[str, str]] = []
    ids: dict[tuple[str, str], str] = {}

    def intern(citation: Mapping[str, str]) -> str:
        pair = (citation["quote"], citation["context"])
        if pair not in ids:
            citation_id = f"c{len(bank)}"
            ids[pair] = citation_id
            bank.append({"id": citation_id, "q": pair[0], "c": pair[1]})
        return ids[pair]

    view = deepcopy(dict(ledger))
    view["evidence_controls"] = [
        {"ref": intern(control), "handling": control["handling"]}
        for control in ledger["evidence_controls"]
    ]
    for section, _ in DUTY_SECTIONS:
        for row in view[section]:
            row["source_refs"] = [intern(ref) for ref in row["source_refs"]]
            if section in ACTION_SECTIONS:
                row["event_ref"] = intern(row["event_ref"])
                row["actor_ref"] = intern(row["actor_ref"])
                row["role_refs"] = [intern(ref) for ref in row["role_refs"]]
    view["version"] = SOURCE_DUTY_COMPACT_VERSION
    return {"citations": bank, **view}
