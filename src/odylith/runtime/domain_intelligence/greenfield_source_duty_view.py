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
SOURCE_DUTY_COMPACT_VERSION = "odylith.greenfield.source-duty-compact.v12"
PARTICIPANT_FIELDS = ("human_actors", "internal_systems", "external_systems")
PARTICIPANT_JUDGMENTS = ("entity_name", "participant_type", "nonperformance", "identity_nonduplication")


def source_participant_claims(ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Separate compiler-owned roster addresses from authored duty identities."""
    return {f"/{field}/{index}": {"typed_role": field, "source_ref": deepcopy(ref)}
            for field in PARTICIPANT_FIELDS
            for index, ref in enumerate(ledger["nonperforming_participants"][field])}


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
    bank: list[dict[str, Any]] = []
    ids: dict[tuple, str] = {}

    def intern(citation: Mapping[str, Any]) -> str:
        pair = (citation["quote"], citation["context"], *((citation["mention_ordinal"],) if "mention_ordinal" in citation else ()))
        if pair not in ids:
            citation_id = f"c{len(bank)}"
            ids[pair] = citation_id
            bank.append({"id": citation_id, "q": pair[0], "c": pair[1],
                         **({"mention_ordinal": citation["mention_ordinal"]} if "mention_ordinal" in citation else {})})
        return ids[pair]

    view = deepcopy(dict(ledger))
    view["evidence_controls"] = [
        {"ref": intern(control), "handling": control["handling"]}
        for control in ledger["evidence_controls"]
    ]
    if ledger["version"] in {"odylith.greenfield.source-duty-ledger.v7", "odylith.greenfield.source-duty-ledger.v8", "odylith.greenfield.source-duty-ledger.v9", "odylith.greenfield.source-duty-ledger.v10", "odylith.greenfield.source-duty-ledger.v11", "odylith.greenfield.source-duty-ledger.v12", "odylith.greenfield.source-duty-ledger.v13", "odylith.greenfield.source-duty-ledger.v14"} and ledger["product_identity"] is not None:
        view["product_identity"]["source_ref"] = intern(ledger["product_identity"]["source_ref"])
    if ledger["version"] == "odylith.greenfield.source-duty-ledger.v14" and ledger["customer"] is not None:
        view["customer"] = intern(ledger["customer"])
    for section, _ in DUTY_SECTIONS:
        for row in view[section]:
            row["source_refs"] = [intern(ref) for ref in row["source_refs"]]
            if section in ACTION_SECTIONS:
                row["event_ref"] = intern(row["event_ref"])
                row["actor_ref"] = intern(row["actor_ref"])
                row["role_refs"] = [intern(ref) for ref in row["role_refs"]]
    if ledger["version"] in {"odylith.greenfield.source-duty-ledger.v10", "odylith.greenfield.source-duty-ledger.v11", "odylith.greenfield.source-duty-ledger.v12", "odylith.greenfield.source-duty-ledger.v13", "odylith.greenfield.source-duty-ledger.v14"}:
        view["nonperforming_participants"] = {
            field: [intern(ref) for ref in ledger["nonperforming_participants"][field]]
            for field in PARTICIPANT_FIELDS}
    if ledger["version"] in {"odylith.greenfield.source-duty-ledger.v12", "odylith.greenfield.source-duty-ledger.v13", "odylith.greenfield.source-duty-ledger.v14"}:
        for row in view["source_precedence"]:
            row["constraint_ref"] = intern(row["constraint_ref"])
        if view["terminal"] is not None:
            view["terminal"]["proof_boundary"] = intern(view["terminal"]["proof_boundary"])
            if view["terminal"]["result_fact"]["field"] != "first_path":
                view["terminal"]["result_fact"]["source_ref"] = intern(view["terminal"]["result_fact"]["source_ref"])
    view["version"] = ("odylith.greenfield.source-duty-compact.v3"
                       if ledger["version"] == "odylith.greenfield.source-duty-ledger.v5"
                       else "odylith.greenfield.source-duty-compact.v4"
                       if ledger["version"] == "odylith.greenfield.source-duty-ledger.v6"
                       else "odylith.greenfield.source-duty-compact.v5"
                       if ledger["version"] == "odylith.greenfield.source-duty-ledger.v7"
                       else "odylith.greenfield.source-duty-compact.v6"
                       if ledger["version"] == "odylith.greenfield.source-duty-ledger.v8"
                       else "odylith.greenfield.source-duty-compact.v7"
                       if ledger["version"] == "odylith.greenfield.source-duty-ledger.v9"
                       else "odylith.greenfield.source-duty-compact.v8"
                       if ledger["version"] == "odylith.greenfield.source-duty-ledger.v10"
                       else "odylith.greenfield.source-duty-compact.v9"
                       if ledger["version"] == "odylith.greenfield.source-duty-ledger.v11"
                       else "odylith.greenfield.source-duty-compact.v10"
                       if ledger["version"] == "odylith.greenfield.source-duty-ledger.v12"
                       else "odylith.greenfield.source-duty-compact.v11"
                       if ledger["version"] == "odylith.greenfield.source-duty-ledger.v13"
                       else SOURCE_DUTY_COMPACT_VERSION)
    if ledger["version"] in {"odylith.greenfield.source-duty-ledger.v9", "odylith.greenfield.source-duty-ledger.v10", "odylith.greenfield.source-duty-ledger.v11", "odylith.greenfield.source-duty-ledger.v12", "odylith.greenfield.source-duty-ledger.v13", "odylith.greenfield.source-duty-ledger.v14"}:
        version = view.pop("version")
        if view["status"] == "clarification_required":
            if view.get("customer") is not None or view["product_identity"] is not None or view["evidence_controls"] or any(view[section] for section, _ in DUTY_SECTIONS) or any(view.get("nonperforming_participants", {}).values()):
                raise ValueError("clarification must carry no inventory")
            return {"version": version, "result": {key: view[key] for key in ("status", "question")}}
        return {"version": version, "result": {"citations": bank, **view}}
    return {"citations": bank, **view}
