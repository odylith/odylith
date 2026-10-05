"""Score individual Greenfield cases against native custody or audited source predicates.

Semantic entailment in the public source mode is a retained independent judgment;
structural hashes authenticate evidence and never supply that judgment.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
from typing import Any

from greenfield_relation_fidelity import RELATION_FAMILIES, annotation_relation_evidence, snapshot_relation_evidence
from greenfield_relation_fidelity import canonical_evidence_sha256, observed_semantic_universe
from greenfield_matrix_case_file import load_case_file
from greenfield_matrix_release_artifacts import is_sha256, sha256_file, retained_evidence_manifest_issues, repo_artifact_path
from greenfield_onboarding_review import validate_independent_reviewer

NORMALIZED_SEMANTIC_DIGEST_VERSION = "odylith.greenfield.normalized-semantics.v1"
_SCORED_ROLE = "scored"
_REFERENCE_ROLE = "reference_only"
PUBLIC_SOURCE_MODE = "odylith.greenfield.public-source-predicate-evaluation.v1"
_ARTIFACT_REFS = {"predeclaration", "source_cases", "observed_bindings", "independent_audit", "output", "retained_manifest", "review_record"}

def score_native_commit(
    *,
    case: Any,
    case_id: str,
    annotation: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    actual_rows: tuple[Mapping[str, Any], ...] | None,
    metric_counts: Mapping[str, list[int]],
    failed_dimensions: list[str],
    p0: list[dict[str, str]],
    p1: list[dict[str, str]],
) -> tuple[dict[str, Any], list[str], str]:
    expected_relations = annotation_relation_evidence(
        case=case,
        value=annotation.get("relation_fidelity"),
        atom_rows=annotation.get("atoms"),
    )
    actual_relations = snapshot_relation_evidence(case=case, snapshot=snapshot)
    relation_counts = empty_relation_counts()
    relation_issues = [
        *(f"relation annotation {issue}" for issue in expected_relations.issues),
        *(f"relation custody {issue}" for issue in actual_relations.issues),
    ]
    if expected_relations.issues:
        p1.append(semantic_finding(case_id, "relation_annotation_invalid"))
    if actual_relations.issues:
        p1.append(semantic_finding(case_id, "relation_custody_invalid"))
    for family in RELATION_FAMILIES:
        expected_family = Counter(expected_relations.keys.get(family, ()))
        actual_family = Counter(actual_relations.keys.get(family, ()))
        matched = (
            sum((expected_family & actual_family).values())
            if not relation_issues
            else 0
        )
        sample_count = max(
            sum((expected_family | actual_family).values()),
            int(expected_relations.minimum_samples.get(family, 0)),
            int(actual_relations.minimum_samples.get(family, 0)),
        )
        relation_counts["matched"] += matched
        relation_counts["sample_count"] += sample_count
        relation_counts["families"][family] = {
            "matched": matched,
            "sample_count": sample_count,
        }
        if expected_family != actual_family:
            p1.append(semantic_finding(case_id, f"{family}_mismatch"))
    metric_counts["relation_fidelity"][0] += int(relation_counts["matched"])
    metric_counts["relation_fidelity"][1] += int(relation_counts["sample_count"])
    if relation_issues or relation_counts["matched"] != relation_counts["sample_count"]:
        failed_dimensions.append("relation_fidelity")

    if actual_rows is None:
        failed_dimensions.append("atomic_custody_invalid")
        p0.append(semantic_finding(case_id, "atomic_custody_invalid"))
        return relation_counts, relation_issues, ""
    expected_rows = _annotation_atoms(annotation, role=_SCORED_ROLE)
    reference_rows = _annotation_atoms(annotation, role=_REFERENCE_ROLE)
    expected = Counter(_expected_atom_key(row) for row in expected_rows)
    reference = {_expected_atom_key(row) for row in reference_rows}
    actual = Counter(
        key
        for row in actual_rows
        if (key := _actual_atom_key(row)) not in reference
    )
    union_count = sum((expected | actual).values())
    matched_count = sum((expected & actual).values())
    metric_counts["atomic_semantic_fidelity"][0] += matched_count
    metric_counts["atomic_semantic_fidelity"][1] += union_count
    if expected != actual:
        failed_dimensions.append("atomic_semantic_fidelity")
        if expected - actual:
            p0.append(semantic_finding(case_id, "expected_atomic_fact_missing"))
        if actual - expected:
            p0.append(semantic_finding(case_id, "unexpected_atomic_fact"))
    digest = ""
    if (
        expected == actual
        and not relation_issues
        and relation_counts["matched"] == relation_counts["sample_count"]
    ):
        digest = _normalized_semantic_digest(annotation)
        if not digest:
            failed_dimensions.append("normalized_semantic_identity")
            p1.append(semantic_finding(case_id, "normalized_semantic_identity_invalid"))
    return relation_counts, relation_issues, digest



def _normalized_semantic_digest(annotation: Mapping[str, Any]) -> str:
    """Bind canonical atom IDs to the exact relation graph without source wording."""

    path_ids: dict[tuple[str, str, int], str] = {}
    role_ids: dict[tuple[int, str], str] = {}
    seen_ids: set[str] = set()
    scored_atoms: list[tuple[str, str, str, str, str, str]] = []
    try:
        for atom in mapping_rows(annotation.get("atoms")):
            atom_id = str(atom.get("id") or "").strip()
            source_hash = str(mapping_value(atom.get("source")).get("quote_sha256") or "")
            if not atom_id or atom_id in seen_ids or len(source_hash) != 64:
                return ""
            seen_ids.add(atom_id)
            if atom.get("evaluation_role") == _SCORED_ROLE:
                scored_atoms.append((
                    atom_id, str(atom.get("category") or ""), _SCORED_ROLE,
                    str(atom.get("materiality") or ""), str(atom.get("expected_custody") or ""),
                    str(atom.get("expected_polarity") or ""),
                ))
            for link in mapping_rows(atom.get("projection_links")):
                order = int(link["relation_order"])
                path = str(link["path"])
                role = str(link["relation_role"])
                if order < 0 or not path or not _index_identity(path_ids, (path, source_hash, order), atom_id):
                    return ""
                if order and role and not _index_identity(role_ids, (order, role), atom_id):
                    return ""
        relation = mapping_value(annotation.get("relation_fidelity"))
        events: list[tuple[Any, ...]] = []
        for row in mapping_rows(relation.get("first_path_events")):
            order = int(row["order"])
            actor_id = _path_identity(path_ids, row, "actor_fact", order)
            owner_id = _path_identity(path_ids, row, "product_owner", order) if row.get("product_owner_path") else ""
            action_id = role_ids.get((order, "action_verb_quote"), "")
            target_id = role_ids.get((order, "target_quote"), "")
            visible_id = role_ids.get((order, "visible_result_quote"), "")
            if (
                order <= 0
                or actor_id != role_ids.get((order, "actor_fact_quote"), "")
                or not action_id
                or bool(row.get("target_sha256")) != bool(target_id)
                or bool(row.get("visible_result_sha256")) != bool(visible_id)
                or bool(row.get("product_owner_path")) != bool(owner_id)
            ):
                return ""
            events.append((
                order, str(row.get("actor_kind") or ""), actor_id, owner_id,
                action_id, target_id, visible_id,
            ))
        contexts = [
            (
                str(row["context_kind"]), _path_identity(
                    path_ids, row, "fact", int(row["first_path_event_order"])
                ), int(row["first_path_event_order"]),
            )
            for row in mapping_rows(relation.get("context_relations"))
        ]
        components = [
            (
                _path_identity(path_ids, row, "responsibility", int(row["first_path_event_order"])),
                _path_identity(path_ids, row, "product_owner", int(row["first_path_event_order"])),
                int(row["first_path_event_order"]), str(row["responsibility_source"]),
            )
            for row in mapping_rows(relation.get("component_responsibility_relations"))
        ]
    except (KeyError, TypeError, ValueError):
        return ""
    if not scored_atoms or not events:
        return ""
    if any(not row[1] for row in contexts) or any(not row[0] or not row[1] for row in components):
        return ""
    payload = {
        "version": NORMALIZED_SEMANTIC_DIGEST_VERSION,
        "expected_outcome": "commit",
        "atoms": sorted(scored_atoms),
        "relations": {"first_path_events": sorted(events), "context_relations": sorted(contexts),
                      "component_responsibility_relations": sorted(components)},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()



def _index_identity(index: dict[Any, str], key: Any, atom_id: str) -> bool:
    existing = index.setdefault(key, atom_id)
    return existing == atom_id



def _path_identity(index: Mapping[tuple[str, str, int], str], row: Mapping[str, Any], prefix: str, order: int) -> str:
    key = (str(row.get(f"{prefix}_path") or ""), str(row.get(f"{prefix}_sha256") or ""), order)
    return str(index.get(key) or index.get((key[0], key[1], 0)) or "")



def _annotation_atoms(
    annotation: Mapping[str, Any],
    *,
    role: str,
) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        row
        for row in mapping_rows(annotation.get("atoms"))
        if row.get("evaluation_role") == role
    )



def _expected_atom_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    source = mapping_value(row.get("source"))
    return (
        str(row.get("category") or ""),
        str(row.get("expected_polarity") or ""),
        str(row.get("expected_custody") or ""),
        int(source.get("start_byte", -1)),
        int(source.get("end_byte", -1)),
        str(source.get("quote_sha256") or ""),
        _links_key(row.get("projection_links")),
    )



def _actual_atom_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    categories = string_rows(row.get("categories"))
    refs = mapping_rows(row.get("source_span_refs"))
    ref = refs[0] if len(refs) == 1 else {}
    return (
        categories[0] if len(categories) == 1 else "",
        str(row.get("polarity") or ""),
        str(row.get("custody_state") or ""),
        int(ref.get("source_start_byte", -1)),
        int(ref.get("source_end_byte", -1)),
        str(ref.get("text_sha256") or ""),
        _links_key(row.get("projection_links")),
    )



def _links_key(value: Any) -> str:
    rows = list(value) if is_sequence(value) else []
    return json.dumps(rows, sort_keys=True, separators=(",", ":"))



def empty_relation_counts() -> dict[str, Any]:
    return {
        "matched": 0,
        "sample_count": 0,
        "families": {
            family: {"matched": 0, "sample_count": 0}
            for family in RELATION_FAMILIES
        },
    }



def mapping_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not is_sequence(value):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))



def mapping_value(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}



def semantic_finding(case_id: str, category: str) -> dict[str, str]:
    return {"case_id": case_id, "category": category}



def is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))



def string_rows(value: Any) -> tuple[str, ...]:
    if not is_sequence(value):
        return ()
    return tuple(str(item) for item in value)


def load_source_predicate_evidence(
    *, configuration: Mapping[str, Any], cases: Sequence[Any], results: Sequence[Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]], tuple[str, ...]]:
    """Authenticate separately retained source expectations, mapping, and audit.

    Pinned digests must come from retained release evidence.  Eligibility and
    hashes authenticate that review evidence; they do not perform entailment.
    """
    from greenfield_evaluation_contract import validate_source_predicate_predeclaration
    issues: list[str] = []
    if set(configuration) != {"mode", *_ARTIFACT_REFS} or configuration.get("mode") != PUBLIC_SOURCE_MODE:
        return {}, {}, ("source-predicate evaluation requires its explicit public mode and exact evidence refs",)
    payloads: dict[str, Mapping[str, Any]] = {}
    paths: dict[str, Path] = {}
    digests: dict[str, str] = {}
    try:
        for name in _ARTIFACT_REFS:
            ref = configuration[name]
            if not isinstance(ref, Mapping) or set(ref) != {"path", "sha256"} or not is_sha256(ref["sha256"]):
                raise ValueError(f"invalid retained {name} reference")
            path = Path(ref["path"]).resolve()
            if sha256_file(path) != ref["sha256"]:
                raise ValueError(f"retained {name} file hash changed")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError(f"retained {name} must be an object")
            payloads[name], paths[name], digests[name] = payload, path, ref["sha256"]
        source_cases = load_case_file(paths["source_cases"])
        annotations, source_issues = validate_source_predicate_predeclaration(
            cases=source_cases, path=paths["predeclaration"], expected_sha256=digests["predeclaration"])
        issues.extend(source_issues)
        if digests["source_cases"] not in payloads["predeclaration"].get("sources", {}).values():
            issues.append("source case file is not a frozen predeclaration source")
        output_rows = payloads["output"].get("results")
        if not isinstance(output_rows, list):
            raise ValueError("source-predicate output lacks exact matrix result rows")
        output_by_id = {row["evidence"]["case"]["id"]: row for row in output_rows}
        if len(output_by_id) != len(output_rows):
            issues.append("source-predicate output repeats case IDs")
        ids = tuple(output_by_id)
        issues.extend(retained_evidence_manifest_issues(paths["retained_manifest"], expected_case_ids=ids))
        selected_results = {str(mapping_value(mapping_value(result.evidence).get("case")).get("id") or ""): result for result in results}
        for case in cases:
            case_id = str(case.case_id)
            original = next((row for row in source_cases if row.case_id == case_id), None)
            if original is None or (case.prompt, case.confirmed_intent_markdown) != (original.prompt, original.confirmed_intent_markdown):
                issues.append(f"case `{case_id}` differs from frozen source input")
            result = selected_results.get(case_id)
            if result is None or output_by_id.get(case_id) != result.to_dict():
                issues.append(f"case `{case_id}` result differs from immutable actual output")
        binding, audit, record = (payloads[name] for name in ("observed_bindings", "independent_audit", "review_record"))
        if set(binding) != {"version", "public_split", "source_predeclaration_sha256", "output_sha256", "binder_identity", "cases"} or binding.get("version") != PUBLIC_SOURCE_MODE + ".bindings.v1" or binding.get("public_split") != "disclosed-public-live-subset":
            issues.append("observed source binding has invalid fields, version, or public split")
        if set(audit) != {"version", "source_predeclaration_sha256", "observed_bindings_sha256", "output_sha256", "retained_manifest_sha256", "review_record_sha256", "reviewer", "cases"} or audit.get("version") != PUBLIC_SOURCE_MODE + ".audit.v1":
            issues.append("independent semantic audit has invalid fields or version")
        for value, names in ((binding, ("predeclaration", "output")), (audit, ("predeclaration", "observed_bindings", "output", "retained_manifest", "review_record"))):
            for name in names:
                key = "source_predeclaration_sha256" if name == "predeclaration" else name + "_sha256"
                if value.get(key) != digests[name]:
                    issues.append(f"semantic evidence has changed {name} identity")
        awaiting: list[str] = []
        reviewer = audit.get("reviewer")
        validate_independent_reviewer(reviewer, forbidden_context_ids=set(digests.values()), issues=issues, awaiting=awaiting)
        issues.extend(awaiting)
        if not binding.get("binder_identity") or binding.get("binder_identity") == mapping_value(reviewer).get("identity"):
            issues.append("semantic binder and reviewer must have separate identities")
        expected_record = {"version": PUBLIC_SOURCE_MODE + ".review-record.v1",
            "source_predeclaration_sha256": digests["predeclaration"], "observed_bindings_sha256": digests["observed_bindings"],
            "output_sha256": digests["output"], "retained_manifest_sha256": digests["retained_manifest"],
            "reviewer_sha256": canonical_evidence_sha256(reviewer),
            "review_context_id": mapping_value(reviewer).get("review_context_id"),
            "reviewed_cases_sha256": canonical_evidence_sha256(audit.get("cases"))}
        if record != expected_record:
            issues.append("retained independent review record does not bind the complete exact semantic evidence/verdicts")
        bindings_by_id = {row["case_id"]: row for row in binding["cases"]}
        audits_by_id = {row["case_id"]: row for row in audit["cases"]}
        if len(bindings_by_id) != len(binding["cases"]) or len(audits_by_id) != len(audit["cases"]) or set(bindings_by_id) != set(ids) or set(audits_by_id) != set(ids):
            issues.append("semantic bindings/audits must cover every output case exactly once")
        retained = {row["case_id"]: row for row in payloads["retained_manifest"]["case_manifests"]}
        source_by_id = {case.case_id: case for case in source_cases}
        for case_id in ids:
            case = source_by_id[case_id]
            receipt = output_by_id[case_id]["evidence"].get("preconfirm_dry_run", {})
            snapshot = receipt.get("semantic_snapshot", {})
            if snapshot and receipt.get("semantic_snapshot_sha256") != canonical_evidence_sha256(snapshot):
                issues.append(f"case `{case_id}` snapshot receipt hash changed")
            if snapshot:
                transaction = mapping_value(mapping_value(retained[case_id].get("semantic_bindings")).get("transaction"))
                if transaction.get("transaction_hash") != receipt.get("transaction_hash"):
                    issues.append(f"case `{case_id}` transaction differs from retained immutable custody")
            case_path = repo_artifact_path(paths["retained_manifest"].parent, retained[case_id]["path"])
            case_manifest = json.loads(case_path.read_text(encoding="utf-8"))
            result_refs = [row for row in case_manifest["artifacts"] if row["path"] == "case-result.v1.json"]
            if len(result_refs) != 1:
                issues.append(f"case `{case_id}` lacks its retained immutable result")
            else:
                retained_result = repo_artifact_path(case_path.parent, result_refs[0]["path"])
                if json.loads(retained_result.read_text(encoding="utf-8")) != output_by_id[case_id]:
                    issues.append(f"case `{case_id}` output is not its exact retained case result")
            issues.extend(validate_source_predicate_binding_case(case=case, annotation=annotations[case_id],
                binding=bindings_by_id[case_id], audit=audits_by_id[case_id], receipt=receipt, snapshot=snapshot,
                clarification=output_by_id[case_id]["evidence"].get("clarification", {})))
        return annotations, bindings_by_id, tuple(issues)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        return {}, {}, tuple((*issues, f"source-predicate evidence is incomplete: {exc}"))


def source_predicate_units(annotation: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Keep original parent predicates, separately named IDs, and full obligations."""
    units = {"atom:" + row["id"]: {"kind": "atom", "source_sha256": canonical_evidence_sha256(row),
             "evaluation_role": row["evaluation_role"]} for row in annotation["atoms"]}
    for index, obligation in enumerate(annotation["obligations"], 1):
        units[f"obligation:{index}"] = {"kind": "obligation", "source_sha256": canonical_evidence_sha256(obligation), "evaluation_role": "scored"}
    fields = {"first_path_events": "first_path_relations", "context_relations": "context_relations", "component_responsibility_relations": "component_responsibilities"}
    for family, field in fields.items():
        for index, row in enumerate(annotation[field], 1):
            units[f"{family}:{index}"] = {"kind": family, "source_sha256": canonical_evidence_sha256(row), "evaluation_role": "scored"}
    return units


def validate_source_predicate_binding_case(
    *, case: Any, annotation: Mapping[str, Any], binding: Mapping[str, Any],
    audit: Mapping[str, Any], receipt: Mapping[str, Any], snapshot: Mapping[str, Any],
    clarification: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    """Check complete many-to-many mappings and audited semantic dispositions."""
    issues: list[str] = []
    if set(binding) != {"case_id", "operator_evidence_sha256", "snapshot_sha256", "transaction_hash", "forward", "reverse"}:
        issues.append("source binding case fields are invalid")
    if set(audit) != {"case_id", "snapshot_sha256", "transaction_hash", "entries"}:
        issues.append("semantic audit case fields are invalid")
    for value in (binding, audit):
        if value.get("case_id") != case.case_id or value.get("snapshot_sha256") != (canonical_evidence_sha256(snapshot) if snapshot else "") or value.get("transaction_hash") != receipt.get("transaction_hash", ""):
            issues.append("semantic mapping/audit has stale case, snapshot or transaction identity")
    if binding.get("operator_evidence_sha256") != annotation["operator_evidence_sha256"]:
        issues.append("semantic binding operator evidence identity changed")
    units = source_predicate_units(annotation)
    universe = observed_semantic_universe(case=case, snapshot=snapshot) if snapshot else {}
    if clarification:
        universe["/clarification"] = {"id": "/clarification", "kind": "clarification",
            "destination_sha256": canonical_evidence_sha256(clarification),
            "source_witness_sha256": "", "normalized_role_sha256": {}, "custody_state": "ambiguity"}
    reviewed = {(row["direction"], row["id"]): row for row in audit["entries"]}
    if len(reviewed) != len(audit["entries"]):
        issues.append("independent semantic audit repeats an entry")
    seen_review: set[tuple[str, str]] = set()
    for direction, expected in (("forward", units), ("reverse", universe)):
        rows = binding.get(direction)
        if not isinstance(rows, list):
            issues.append(f"semantic binding {direction} must be an array")
            continue
        seen: set[str] = set()
        for row in rows:
            identity = row["id"]
            if identity in seen or identity not in expected:
                issues.append(f"semantic {direction} contains duplicate or unknown identity `{identity}`")
                continue
            seen.add(identity)
            audit_key = (direction, identity)
            seen_review.add(audit_key)
            verdict = reviewed.get(audit_key)
            if verdict is None or set(verdict) != {"direction", "id", "entry_sha256", "verdict", "rationale"} or verdict.get("entry_sha256") != canonical_evidence_sha256(row) or verdict.get("verdict") != "confirmed" or not isinstance(verdict.get("rationale"), str) or not verdict["rationale"].strip():
                issues.append(f"semantic {direction} `{identity}` lacks an exact independently reviewed verdict")
            if not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
                issues.append(f"semantic {direction} `{identity}` lacks its semantic explanation")
            if direction == "forward":
                if set(row) != {"id", "unit", "disposition", "observed", "semantic_identity", "rationale"} or row.get("unit") != expected[identity]:
                    issues.append(f"source predicate `{identity}` was changed")
                if not isinstance(row.get("semantic_identity"), str) or not row["semantic_identity"].strip():
                    issues.append(f"source predicate `{identity}` lacks its independently audited semantic identity")
                disposition = row.get("disposition")
                if disposition not in {"full", "partial", "missing", "contradicted", "invented_support", "reference_only"} or (disposition == "reference_only") != (expected[identity]["evaluation_role"] == "reference_only"):
                    issues.append(f"source predicate `{identity}` has invalid applicability/disposition")
                observed = row.get("observed")
                if not isinstance(observed, list) or len(observed) != len(set(observed)) or any(value not in universe for value in observed):
                    issues.append(f"source predicate `{identity}` has invalid observed destinations")
                    continue
                if disposition == "full" and snapshot and not observed:
                    issues.append(f"source predicate `{identity}` has no observed support")
                if identity.startswith("atom:") and disposition == "full" and observed:
                    atom = next(atom for atom in annotation["atoms"] if "atom:" + atom["id"] == identity)
                    if atom.get("expected_custody") == "accepted_fact" and all(universe[key]["custody_state"] in {"assumption", "ambiguity"} for key in observed):
                        issues.append(f"source predicate `{identity}` advisory custody cannot discharge an accepted fact")
                if expected[identity]["kind"] == "first_path_events" and disposition == "full":
                    main = [value for value in observed if universe[value]["kind"] == "main_event"]
                    selected = [key for key, value in universe.items() if value["kind"] == "main_event"]
                    index = int(identity.rsplit(":", 1)[1]) - 1
                    if len(main) != 1 or index >= len(selected) or main[0] != selected[index]:
                        issues.append(f"source relation `{identity}` has wrong main/support selection or order")
            else:
                if set(row) != {"id", "evidence", "disposition", "source_ids", "duplicate_of", "rationale"} or row.get("evidence") != expected[identity]:
                    issues.append(f"observed claim `{identity}` has changed destination/witness/role hashes")
                source_ids = row.get("source_ids")
                if not isinstance(source_ids, list) or len(source_ids) != len(set(source_ids)) or any(value not in units for value in source_ids):
                    issues.append(f"observed claim `{identity}` has invalid source predicate IDs")
                    continue
                disposition = row.get("disposition")
                if disposition not in {"source_supported", "bounded_interpretation", "assumption", "duplicate", "reference_only", "unsupported", "contradicted"}:
                    issues.append(f"observed claim `{identity}` has invalid reverse disposition")
                if disposition in {"source_supported", "bounded_interpretation", "assumption", "reference_only"} and not source_ids:
                    issues.append(f"observed claim `{identity}` lacks independent source support")
                if disposition == "reference_only" and any(units[key]["evaluation_role"] != "reference_only" for key in source_ids):
                    issues.append(f"observed claim `{identity}` invented a reference exemption")
                if disposition == "duplicate" and (row.get("duplicate_of") not in universe or row.get("duplicate_of") == identity):
                    issues.append(f"observed claim `{identity}` has no distinct supported duplicate parent")
        if seen != set(expected):
            issues.append(f"semantic {direction} enumeration is incomplete")
    if seen_review != set(reviewed):
        issues.append("independent semantic audit has missing or extra dispositions")
    reverse_by_id = {row["id"]: row for row in binding.get("reverse", ())}
    for row in reverse_by_id.values():
        issues.extend(_reverse_custody_issues(row, universe.get(row["id"], {}),
            universe.get(row.get("duplicate_of"), {})))
        if row.get("disposition") == "duplicate" and mapping_value(reverse_by_id.get(row.get("duplicate_of"))).get("disposition") not in {"source_supported", "bounded_interpretation", "assumption"}:
            issues.append("duplicate observed representation lacks a supported non-duplicate parent")
    return tuple(issues)


def _reverse_custody_issues(
    row: Mapping[str, Any], evidence: Mapping[str, Any], parent: Mapping[str, Any],
) -> tuple[str, ...]:
    """Audit labels cannot change canonical observed custody in either direction."""
    issues: list[str] = []
    disposition, custody = row.get("disposition"), evidence.get("custody_state")
    if custody == "assumption" and disposition not in {"assumption", "duplicate", "unsupported", "contradicted"}:
        issues.append(f"observed claim `{row['id']}` reclassified an advisory assumption as accepted support")
    if disposition == "assumption" and custody != "assumption":
        issues.append(f"observed claim `{row['id']}` reclassified non-assumption custody as an advisory assumption")
    if disposition == "duplicate" and parent and custody != parent.get("custody_state"):
        issues.append(f"observed claim `{row['id']}` duplicate changes actual custody")
    return tuple(issues)


def score_source_predicates(
    *, case_id: str, annotation: Mapping[str, Any], binding: Mapping[str, Any],
    metric_counts: Mapping[str, list[int]], failed_dimensions: list[str],
    p0: list[dict[str, str]], p1: list[dict[str, str]],
    count_atomic: bool = True,
) -> tuple[dict[str, Any], list[str], str]:
    """Score authenticated bindings once; reverse custody failures earn no credit."""
    rows = {row["id"]: row for row in binding["forward"]}
    scored = ["atom:" + atom["id"] for atom in annotation["atoms"] if atom["evaluation_role"] == "scored"]
    if count_atomic:
        metric_counts["atomic_semantic_fidelity"][0] += sum(rows[key]["disposition"] == "full" for key in scored)
        metric_counts["atomic_semantic_fidelity"][1] += len(scored)
    counts = empty_relation_counts()
    units = source_predicate_units(annotation)
    for family in RELATION_FAMILIES:
        keys = [key for key, unit in units.items() if unit["kind"] == family]
        matched = sum(rows[key]["disposition"] == "full" for key in keys)
        counts["families"][family] = {"matched": matched, "sample_count": len(keys)}
        counts["matched"] += matched
        counts["sample_count"] += len(keys)
    metric_counts["relation_fidelity"][0] += counts["matched"]
    metric_counts["relation_fidelity"][1] += counts["sample_count"]
    missing = [key for key, unit in units.items() if unit["evaluation_role"] == "scored" and rows[key]["disposition"] != "full"]
    reverse_by_id = {row["id"]: row for row in binding["reverse"]}
    reverse_failures = [row["id"] for row in binding["reverse"]
        if row["disposition"] in {"unsupported", "contradicted"} or _reverse_custody_issues(
            row, row["evidence"], mapping_value(reverse_by_id.get(row.get("duplicate_of"))).get("evidence", {}))]
    if missing:
        failed_dimensions.append("source_predicate_coverage")
        p0.append(semantic_finding(case_id, "source_predicate_or_compound_obligation_missing"))
    if reverse_failures:
        failed_dimensions.append("reverse_semantic_support")
        p0.append(semantic_finding(case_id, "unsupported_observed_semantic_claim"))
    digest = ""
    if not missing and not reverse_failures:
        digest = canonical_evidence_sha256({"version": PUBLIC_SOURCE_MODE + ".normalized-semantics.v1",
            "units": sorted((key, value["kind"], rows[key]["semantic_identity"])
                for key, value in units.items() if value["evaluation_role"] == "scored"),
            "expected_outcome": annotation["expected_outcome"]})
    return counts, [], digest
