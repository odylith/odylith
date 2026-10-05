"""Detached public semantic and measured-timing qualification from saved evidence.

Digests authenticate retained review acts. They do not establish authorship or
natural-language entailment. The operator must pin genuinely independent review
records; synthetic test records are never actual public qualification evidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import math
from pathlib import Path
from typing import Any

from greenfield_evaluation_contract import (
    PUBLIC_SOURCE_PREDICATE_MODE, PUBLIC_SOURCE_SPLIT, published_structural_floors,
    validate_source_predicate_predeclaration, _frozen_floor_issues,
)
from greenfield_matrix_case_file import load_case_file
from greenfield_matrix_release_artifacts import is_sha256, sha256_file
from greenfield_matrix_statistics import release_slice_contract
from greenfield_matrix_types import GreenfieldArtifactCounts, GreenfieldMatrixResult, GreenfieldQualityVerdict
from greenfield_onboarding_quality_scorecard import build_onboarding_quality_scorecard
from greenfield_relation_fidelity import canonical_evidence_sha256
from greenfield_semantic_release_score import evaluate_semantic_release
from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import (
    PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS, WHOLE_JOURNEY_ELAPSED_SCOPE,
    whole_journey_observation_issues,
)


PUBLIC_QUALIFICATION_VERSION = "odylith.greenfield.detached-public-qualification.v1"
PUBLIC_MEASURED_BOUND_VERSION = "odylith.greenfield.measured-public-whole-journey-bound.v1"
PUBLIC_MEASURED_BOUND_SCOPE = "measured_retained_public_evidence_only"


def read_public_evidence_reference(ref: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    """Read one exact pinned public review artifact, refusing stale bytes."""
    if not isinstance(ref, Mapping) or set(ref) != {"path", "sha256"} or not is_sha256(ref["sha256"]):
        raise ValueError(f"{label} requires an exact saved path and SHA-256")
    path = Path(ref["path"]).expanduser().resolve()
    if sha256_file(path) != ref["sha256"]:
        raise ValueError(f"{label} bytes changed")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return dict(value)


def typed_saved_matrix_results(rows: Any) -> tuple[GreenfieldMatrixResult, ...]:
    """Rehydrate the existing models without editing serialized evidence."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("saved public matrix/control results must be a nonempty array")
    results = tuple(GreenfieldMatrixResult(**{**row,
        "counts": GreenfieldArtifactCounts(**row["counts"]),
        "quality": GreenfieldQualityVerdict(**row["quality"])}) for row in rows)
    if canonical_evidence_sha256([row.to_dict() for row in results]) != canonical_evidence_sha256(rows):
        raise ValueError("saved public matrix type roundtrip changed original fields or values")
    return results


def validate_measured_public_bound(
    *, results: Sequence[Any], source_evidence: Mapping[str, Any] | None,
    bound_evidence: Mapping[str, Any] | None,
) -> tuple[float | None, dict[str, Any], tuple[str, ...]]:
    """Authenticate a finite independent decision over every saved public row.

    This proves only the reviewed public measurements. Consumer timing custody
    is not inferred from host observations or reviewer metadata.
    """
    try:
        if not isinstance(source_evidence, Mapping) or source_evidence.get("mode") != PUBLIC_SOURCE_PREDICATE_MODE:
            raise ValueError("measured timing qualification requires public source evidence")
        if not isinstance(bound_evidence, Mapping) or set(bound_evidence) != {"measurements", "decision", "review_record"}:
            raise ValueError("measured timing qualification requires all three saved evidence refs")
        artifacts = {name: read_public_evidence_reference(ref, label="public timing " + name)
            for name, ref in bound_evidence.items()}
        base = read_public_evidence_reference(source_evidence["output"], label="public timing output")
        source_cases = load_case_file(Path(source_evidence["source_cases"]["path"]))
        read_public_evidence_reference(source_evidence["source_cases"], label="public timing source cases")
        _, source_issues = validate_source_predicate_predeclaration(cases=source_cases,
            path=Path(source_evidence["predeclaration"]["path"]), expected_sha256=source_evidence["predeclaration"]["sha256"])
        if source_issues:
            raise ValueError("public timing source predeclaration: " + "; ".join(source_issues))
        read_public_evidence_reference(source_evidence["retained_manifest"], label="public timing retained manifest")
        primary = base["results"]
        controls = base["lower_capability_control_proof"]["results"]
        if not isinstance(primary, list) or not isinstance(controls, list) or not controls:
            raise ValueError("public timing evidence lacks fixed primary/control rows")
        control_count = base["lower_capability_control_proof"].get("case_count")
        if type(control_count) is not int or control_count != len(controls):
            raise ValueError("public timing evidence lacks every declared control observation")
        public_ids = [case.case_id for case in source_cases]
        actual_ids = [row["evidence"]["case"]["id"] for row in primary]
        all_rows = [*primary, *controls]
        ids = [row["evidence"]["case"]["id"] for row in all_rows]
        if len(ids) != len(set(ids)) or set(actual_ids) != set(public_ids) or len(actual_ids) != len(public_ids):
            raise ValueError("public timing measurement does not cover the fixed complete case/control set")
        if canonical_evidence_sha256([result.to_dict() for result in results]) != canonical_evidence_sha256(all_rows):
            raise ValueError("profile rows differ from every saved primary/control observation")
        identities = {name: source_evidence[ref]["sha256"] for name, ref in (
            ("source_predeclaration_sha256", "predeclaration"), ("source_cases_sha256", "source_cases"),
            ("output_sha256", "output"), ("retained_manifest_sha256", "retained_manifest"))}
        expected = []
        for row in all_rows:
            stage = row["evidence"]["model_profile"]["stage_observation"]
            if not isinstance(stage, Mapping):
                raise ValueError("public timing stage observation must be an object")
            observation_issues = whole_journey_observation_issues(stage)
            if observation_issues:
                raise ValueError("public timing observation: " + "; ".join(observation_issues))
            expected.append({"case_id": row["evidence"]["case"]["id"],
                "result_sha256": canonical_evidence_sha256(row),
                "stage_sha256": canonical_evidence_sha256(stage),
                "elapsed_seconds": stage["whole_journey_seconds"]})
        measurements, decision, record = (artifacts[name] for name in ("measurements", "decision", "review_record"))
        if measurements != {"version": PUBLIC_MEASURED_BOUND_VERSION + ".measurements.v1",
            "public_split": PUBLIC_SOURCE_SPLIT, **identities,
            "elapsed_scope": WHOLE_JOURNEY_ELAPSED_SCOPE, "cases": expected}:
            raise ValueError("public timing measurements differ from complete immutable observations")
        fields = {"version", "status", "qualification_scope", "consumer_timing_custody", *identities,
            "measurements_sha256", "finite_bound_seconds", "elapsed_scope", "reviewer", "rationale"}
        if set(decision) != fields or decision.get("version") != PUBLIC_MEASURED_BOUND_VERSION + ".decision.v1":
            raise ValueError("public timing decision has invalid fields/version")
        if any(decision.get(key) != value for key, value in identities.items()):
            raise ValueError("public timing decision has changed source/output/manifest identity")
        bound = decision.get("finite_bound_seconds")
        if (type(bound) not in (float, int) or not math.isfinite(bound)
                or not 0 < bound <= PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS
                or any(entry["elapsed_seconds"] >= bound for entry in expected)):
            raise ValueError("public timing decision lacks a finite bound covering every observation")
        if (decision.get("status") != "approved" or decision.get("qualification_scope") != PUBLIC_MEASURED_BOUND_SCOPE
                or decision.get("consumer_timing_custody") != "unproved"
                or decision.get("elapsed_scope") != WHOLE_JOURNEY_ELAPSED_SCOPE
                or decision.get("measurements_sha256") != bound_evidence["measurements"]["sha256"]
                or not isinstance(decision.get("rationale"), str) or not decision["rationale"].strip()):
            raise ValueError("public timing decision is unapproved, relabeled, or not measurement-bound")
        from greenfield_onboarding_review import validate_independent_reviewer
        issues: list[str] = []
        awaiting: list[str] = []
        forbidden = {ref["sha256"] for ref in (*source_evidence.values(), *bound_evidence.values()) if isinstance(ref, Mapping)}
        validate_independent_reviewer(decision["reviewer"], forbidden_context_ids=forbidden, issues=issues, awaiting=awaiting)
        if issues or awaiting:
            raise ValueError("public timing independent review: " + "; ".join((*issues, *awaiting)))
        reviewer = decision["reviewer"]
        if record != {"version": PUBLIC_MEASURED_BOUND_VERSION + ".review-record.v1", **identities,
            "measurements_sha256": bound_evidence["measurements"]["sha256"],
            "decision_sha256": bound_evidence["decision"]["sha256"],
            "reviewer_sha256": canonical_evidence_sha256(reviewer), "review_context_id": reviewer["review_context_id"],
            "measurement_cases_sha256": canonical_evidence_sha256(expected), "verdict": "approved"}:
            raise ValueError("public timing retained review record lacks exact independent decision scope")
        return float(bound), {"version": PUBLIC_MEASURED_BOUND_VERSION, "status": "passed",
            "qualification_scope": PUBLIC_MEASURED_BOUND_SCOPE, "consumer_timing_custody": "unproved",
            "finite_bound_seconds": float(bound), "observation_count": len(expected),
            "evidence_refs": dict(bound_evidence), "source_identities": identities}, ()
    except (OSError, RuntimeError, ValueError, TypeError, KeyError, OverflowError) as exc:
        issue = f"public measured whole-journey evidence is incomplete: {exc}"
        return None, {"version": PUBLIC_MEASURED_BOUND_VERSION, "status": "failed", "issues": [issue]}, (issue,)


def _saved_scorecard(base: Mapping[str, Any], rows: Sequence[Any], profile: Mapping[str, Any]) -> dict[str, Any]:
    return build_onboarding_quality_scorecard(results=rows, browser_proof=base["browser_surface_proof"],
        platform_leakage_proof=base["platform_domain_leakage_proof"], metamorphic_output=base["metamorphic_output"],
        model_profile_proof=profile, unavailable_provider_proof=base["unavailable_provider_proof"],
        commit_recovery_proof=base["commit_recovery_proof"])


def qualify_saved_public_evidence(
    *, base: Mapping[str, Any], base_result_path: Path, retained_manifest_path: Path,
    source_evidence: Mapping[str, Any], bound_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Recompute owned reports and explain the original diagnostic failure."""
    from greenfield_model_profile_proof import model_profile_release_proof, unavailable_provider_proof_issues
    from greenfield_model_profiles import UNAVAILABLE_PROVIDER_PROFILE
    issues: list[str] = []
    report: dict[str, Any] = {"version": PUBLIC_QUALIFICATION_VERSION, "status": "failed",
        "qualification_scope": PUBLIC_MEASURED_BOUND_SCOPE, "consumer_timing_custody": "unproved"}
    try:
        for key, path in (("output", base_result_path), ("retained_manifest", retained_manifest_path)):
            ref = source_evidence[key]
            if Path(ref["path"]).expanduser().resolve() != path.resolve() or ref["sha256"] != sha256_file(path):
                raise ValueError(f"public source {key} ref differs from the immutable finalizer input")
        primary = typed_saved_matrix_results(base["results"])
        controls = typed_saved_matrix_results(base["lower_capability_control_proof"]["results"])
        rows = (*primary, *controls)
        original_profile = model_profile_release_proof(rows, require_complete=True)
        if base["model_profile_proof"] != original_profile:
            raise ValueError("saved model-profile diagnostics differ from the comprehensive canonical proof")
        if original_profile["issues"] != ["release proof lacks a public-data-backed finite whole-journey bound"]:
            raise ValueError("saved model-profile proof contains a residual or unexplained failure")
        if base["semantic_release"] != {"status": "not_requested", "passed": True}:
            raise ValueError("public base must retain its original unrequested semantic report")
        unavailable = base["unavailable_provider_proof"]
        if (not isinstance(unavailable, Mapping)
                or unavailable.get("version") != "odylith.greenfield.post-receipt-provider-isolation-proof.v2"
                or unavailable.get("status") != "passed"
                or unavailable.get("profile_id") != UNAVAILABLE_PROVIDER_PROFILE
                or unavailable.get("semantic_authority") != "active_host_single_authority"
                or unavailable.get("runtime_provider_mode") != "disabled"
                or type(unavailable.get("post_receipt_provider_invocations")) is not int
                or unavailable["post_receipt_provider_invocations"] != 0
                or not isinstance(unavailable.get("no_write"), Mapping)):
            raise ValueError("saved unavailable-provider control lacks its exact v2 disabled-provider evidence")
        no_write = unavailable["no_write"]
        unavailable_issues = unavailable_provider_proof_issues(returncode=unavailable["returncode"],
            proposal_seconds=unavailable["proposal_seconds"], detail=unavailable["failure_detail"],
            before_record_count=no_write["before_record_count"], after_record_count=no_write["after_record_count"],
            write_audit_active=no_write["write_audit_active"], write_audit_error=no_write["write_audit_error"],
            write_attempts=no_write["write_attempts"], subprocess_attempts=no_write["subprocess_attempts"],
            changed_records=no_write["changed_records"], staged_transaction_present=no_write["staged_transaction_present"])
        if unavailable_issues:
            raise ValueError("saved unavailable-provider control did not pass: " + "; ".join(unavailable_issues))
        old_scorecard = _saved_scorecard(base, rows, original_profile)
        if base["onboarding_quality_scorecard"] != old_scorecard or base.get("status") != "failed":
            raise ValueError("saved base failure/scorecard differs from its canonical diagnostic evidence")
        failed_dimensions = [key for key, value in old_scorecard["dimensions"].items() if value["status"] == "failed"]
        if failed_dimensions != ["preconfirm_tribunal_accuracy"]:
            raise ValueError("saved scorecard contains an unrelated failed dimension")
        floors = published_structural_floors()
        floor_issues = _frozen_floor_issues(floors)
        if floor_issues:
            raise ValueError("public floors differ from the published contract: " + "; ".join(floor_issues))
        cases = load_case_file(Path(source_evidence["source_cases"]["path"]))
        semantic = evaluate_semantic_release(cases=cases, annotations={}, results=primary,
            floors=floors, release_required_slices=release_slice_contract(), source_predicate_evidence=source_evidence)
        profile = model_profile_release_proof(rows, require_complete=True,
            whole_journey_bound_evidence=bound_evidence, public_source_evidence=source_evidence)
        readiness = _saved_scorecard(base, rows, profile)
        if semantic.get("status") != "passed" or semantic.get("passed") is not True:
            issues.append("detached public semantic evidence did not meet the published floors/audit contract")
        if profile.get("status") != "passed":
            issues.append("detached public model-profile/timing evidence did not pass")
        if readiness.get("status") != "awaiting-independent-review":
            issues.append("detached public scorecard did not reach independent review")
        report.update(semantic_release=semantic, model_profile_proof=profile,
            published_floors=floors, published_floors_sha256=canonical_evidence_sha256(floors),
            original_failure_authenticated=True, review_readiness_scorecard=readiness,
            source_evidence_refs=dict(source_evidence), whole_journey_bound_evidence_refs=bound_evidence)
        report["unavailable_provider_control_sha256"] = canonical_evidence_sha256(unavailable)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        issues.append(f"public detached qualification is incomplete: {exc}")
    report.update(status="passed" if not issues else "failed", issues=issues)
    return report
