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
    _frozen_floor_issues,
)
from greenfield_matrix_case_file import load_case_file
from greenfield_matrix_release_artifacts import is_sha256, sha256_file
from greenfield_matrix_statistics import release_slice_contract
from greenfield_matrix_types import GreenfieldArtifactCounts, GreenfieldMatrixResult, GreenfieldQualityVerdict
from greenfield_onboarding_quality_scorecard import build_onboarding_quality_scorecard
from greenfield_relation_fidelity import canonical_evidence_sha256
from greenfield_semantic_case_score import (
    validate_source_predicate_predeclaration, PUBLIC_EDIT_SOURCE_MODE, PUBLIC_EDIT_SOURCE_SPLIT, PUBLIC_COMPOSITION_MODE,
)
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
        if not isinstance(source_evidence, Mapping) or source_evidence.get("mode") not in (PUBLIC_SOURCE_PREDICATE_MODE, PUBLIC_EDIT_SOURCE_MODE):
            raise ValueError("measured timing qualification requires public source evidence")
        if not isinstance(bound_evidence, Mapping) or set(bound_evidence) != {"measurements", "decision", "review_record"}:
            raise ValueError("measured timing qualification requires all three saved evidence refs")
        artifacts = {name: read_public_evidence_reference(ref, label="public timing " + name)
            for name, ref in bound_evidence.items()}
        base = read_public_evidence_reference(source_evidence["output"], label="public timing output")
        source_cases = load_case_file(Path(source_evidence["source_cases"]["path"]))
        read_public_evidence_reference(source_evidence["source_cases"], label="public timing source cases")
        source_declaration = read_public_evidence_reference(source_evidence["predeclaration"], label="public timing predeclaration")
        if source_declaration.get("version", PUBLIC_SOURCE_PREDICATE_MODE) != source_evidence["mode"]:
            raise ValueError("public timing source mode and predeclaration versions differ")
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
            "public_split": PUBLIC_EDIT_SOURCE_SPLIT if source_evidence["mode"] == PUBLIC_EDIT_SOURCE_MODE else PUBLIC_SOURCE_SPLIT, **identities,
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


def _saved_public_diagnostics(base: Mapping[str, Any]) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    """Authenticate original diagnostic reports before deriving any release qualification."""
    from greenfield_model_profile_proof import model_profile_release_proof, unavailable_provider_proof_issues
    from greenfield_model_profiles import UNAVAILABLE_PROVIDER_PROFILE
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
    return primary, controls


def qualify_saved_public_evidence(
    *, base: Mapping[str, Any], base_result_path: Path, retained_manifest_path: Path,
    source_evidence: Mapping[str, Any], bound_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Recompute owned reports and explain the original diagnostic failure."""
    from greenfield_model_profile_proof import model_profile_release_proof
    issues: list[str] = []
    report: dict[str, Any] = {"version": PUBLIC_QUALIFICATION_VERSION, "status": "failed",
        "qualification_scope": PUBLIC_MEASURED_BOUND_SCOPE, "consumer_timing_custody": "unproved"}
    try:
        for key, path in (("output", base_result_path), ("retained_manifest", retained_manifest_path)):
            ref = source_evidence[key]
            if Path(ref["path"]).expanduser().resolve() != path.resolve() or ref["sha256"] != sha256_file(path):
                raise ValueError(f"public source {key} ref differs from the immutable finalizer input")
        primary, controls = _saved_public_diagnostics(base)
        rows = (*primary, *controls)
        floors = published_structural_floors()
        floor_issues = _frozen_floor_issues(floors)
        if floor_issues:
            raise ValueError("public floors differ from the published contract: " + "; ".join(floor_issues))
        cases = load_case_file(Path(source_evidence["source_cases"]["path"]))
        semantic = evaluate_semantic_release(cases=cases, annotations={}, results=primary,
            floors=floors, release_required_slices=release_slice_contract(), source_predicate_evidence=source_evidence,
            retained_evidence_manifest=retained_manifest_path)
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
        report["unavailable_provider_control_sha256"] = canonical_evidence_sha256(base["unavailable_provider_proof"])
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        issues.append(f"public detached qualification is incomplete: {exc}")
    report.update(status="passed" if not issues else "failed", issues=issues)
    return report


_RELEASE_CUSTODY_REFS = frozenset(("checkpoint", "source_export", "source_archive", "build",
    "distribution_custody", "release_manifest", "build_provenance", "activation", "profile"))
_FAMILY_FIELDS = frozenset(("family_id", "role", "case_count", "ordered_case_ids_sha256",
    "source_cases", "predeclaration", "input_identities"))
_OBSERVATION_FIELDS = frozenset(("commit", "tree", "archive_sha256", "wheel_sha256",
    "release_manifest_sha256", "distribution_custody_sha256", "activation_sha256",
    "source_export_root", "distribution_root", "runtime_executable", "runtime_executable_sha256",
    "trusted_executable", "trusted_executable_sha256", "profile_id", "model", "reasoning_effort",
    "argv_shape_sha256", "actual_import_pins"))
_EXECUTION_REFS = frozenset(("execution_request", "execution_result", "execution_log"))
_GENUINE_VERSION = "odylith.v43.genuine-edit-control-declaration.v3"


def _composition_file(ref: Mapping[str, Any], *, label: str) -> Path:
    # These refs also include binary archives/executables, unlike JSON-only review records.
    from greenfield_matrix_release_artifacts import _safe_file_without_symlinks
    if not isinstance(ref, Mapping) or set(ref) != {"path", "sha256"} or not is_sha256(ref["sha256"]):
        raise ValueError(f"{label} requires exact path/hash custody")
    path = _safe_file_without_symlinks(Path(ref["path"]).expanduser(), label=label)
    if sha256_file(path) != ref["sha256"]:
        raise ValueError(f"{label} bytes changed")
    return path


def _composition_release_custody(refs: Mapping[str, Any]) -> dict[str, Any]:
    """Reconcile existing frozen/build/custody/activation witnesses with observed file bytes."""
    if not isinstance(refs, Mapping) or set(refs) != _RELEASE_CUSTODY_REFS:
        raise ValueError("composition lacks its closed current release custody")
    paths = {name: _composition_file(ref, label=name) for name, ref in refs.items()}
    data = {name: read_public_evidence_reference(ref, label=name)
        for name, ref in refs.items() if name != "source_archive"}
    checkpoint, export, build, custody, manifest, provenance, activation, profile = (
        data[name] for name in ("checkpoint", "source_export", "build", "distribution_custody",
            "release_manifest", "build_provenance", "activation", "profile"))
    head, tree = export["head"], export["tree"]
    if (not isinstance(head, str) or len(head) != 40 or not isinstance(tree, str) or len(tree) != 40
            or checkpoint.get("status") != "passed" or checkpoint.get("head") != head
            or checkpoint.get("tree") != tree or checkpoint.get("current_source_pins_unchanged") is not True
            or export.get("status") != "source_export_prepared" or export.get("source_status_porcelain") != ""
            or export.get("archive_sha256") != refs["source_archive"]["sha256"]):
        raise ValueError("composition checkpoint/tree/archive/export identity differs")
    if (build.get("status") != "passed" or build.get("head") != head
            or build.get("source_head_after") != head or build.get("source_status_after") != ""
            or [row.get("phase") for row in build.get("phases", ())] != ["wheel", "assets", "smoke"]
            or any(row.get("returncode") != 0 for row in build["phases"])):
        raise ValueError("composition lacks its exact passed package build")
    for row in build["phases"]:
        _composition_file({"path": row["log"], "sha256": row["log_sha256"]}, label="build log")
    if (custody.get("status") != "passed" or custody.get("head") != head
            or custody.get("provenance_commit_verified") is not True
            or any(custody.get(key) != [] for key in ("frozen_archive_source_mismatches",
                "wheel_source_mismatches", "wheel_unexpected_owners"))
            or not custody.get("source_pins") or not custody.get("artifact_hashes")):
        raise ValueError("composition package/source custody did not pass")
    distribution = paths["release_manifest"].parent
    if paths["build_provenance"].parent != distribution:
        raise ValueError("composition manifest and provenance belong to different distributions")
    for name, digest in custody["artifact_hashes"].items():
        if Path(name).name != name:
            raise ValueError("composition distribution artifact path is unsafe")
        _composition_file({"path": str(distribution / name), "sha256": digest}, label="distribution artifact")
    if custody.get("artifact_count") != len(custody["artifact_hashes"]):
        raise ValueError("composition distribution artifact census changed")
    for name, count, rows in (("checksums", "checksum_count", custody.get("checksums")),
            ("manifest assets", "manifest_asset_count", custody.get("manifest_asset_checks"))):
        if not isinstance(rows, list) or not rows or custody.get(count) != len(rows) or any(row.get("matches") is not True for row in rows):
            raise ValueError(f"composition {name} custody is incomplete")
    if (any(custody["artifact_hashes"].get(name) != row["sha256"] for name, row in manifest["assets"].items())
            or provenance["source_tree"].get("head") != head or provenance["source_tree"].get("dirty") is not False
            or provenance["workflow"].get("sha") != head
            or activation.get("status") != "activated_after_package_pass"
            or activation.get("implementation_revision") != head or profile.get("implementation_revision") != head
            or activation.get("source_export") != export["source_export"]
            or Path(activation["distribution"]).resolve() != distribution.resolve()
            or Path(activation["package_result"]).resolve() != paths["build"].resolve()
            or activation.get("profile") != profile):
        raise ValueError("composition build/manifest/activation/profile custody differs")
    if not activation.get("file_pins"):
        raise ValueError("composition activation has no frozen file pins")
    for name, digest in activation["file_pins"].items():
        _composition_file({"path": name, "sha256": digest}, label="activation pin")
    source = Path(export["source_export"]).resolve()
    for name, digest in custody["source_pins"].items():
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("composition source owner path is unsafe")
        _composition_file({"path": str(source / "src" / name), "sha256": digest}, label="frozen source owner")
    wheel = provenance["artifacts"]["wheel"]
    if custody["artifact_hashes"].get(wheel["name"]) != wheel["sha256"]:
        raise ValueError("composition wheel identity differs")
    _composition_file({"path": profile["trusted_executable"], "sha256": profile["executable_sha256"]}, label="trusted native executable")
    return {"commit": head, "tree": tree, "archive_sha256": refs["source_archive"]["sha256"],
        "wheel_sha256": wheel["sha256"], "release_manifest_sha256": refs["release_manifest"]["sha256"],
        "distribution_custody_sha256": refs["distribution_custody"]["sha256"],
        "activation_sha256": refs["activation"]["sha256"], "source_export_root": str(source),
        "distribution_root": str(distribution.resolve()), "trusted_executable": profile["trusted_executable"],
        "trusted_executable_sha256": profile["executable_sha256"], "profile_id": profile["profile_id"],
        "model": profile["model"], "reasoning_effort": profile["reasoning_effort"],
        "argv_shape_sha256": profile["argv_shape_sha256"]}


def _composition_input_identities(cases: Sequence[Any]) -> list[dict[str, Any]]:
    from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
    import hashlib
    def text_hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
    return [{"case_id": case.case_id, "baseline_request_sha256": text_hash(case.prompt),
        "confirmed_intent_sha256": text_hash(case.confirmed_intent_markdown),
        "initial_prompt_sha256": text_hash(case.initial_prompt),
        "h0_source_sha256": text_hash(prepare_model_authoring_evidence(prompt=case.initial_prompt).evidence_source),
        "correction_sha256": text_hash(case.lifecycle_correction),
        "h1_source_sha256": text_hash(case.model_evidence.evidence_source) if case.lifecycle_correction else None}
        for case in cases]


def _composition_membership(declaration: Mapping[str, Any]) -> dict[str, tuple[Any, ...]]:
    from greenfield_semantic_case_score import PUBLIC_SOURCE_MODE
    families, ids = {}, set()
    for name, count, role in (("primary", 40, "scored_primary"), ("high", 4, "scored_high_edit"),
            ("genuine_edit", 4, "exclusion_and_separate_gate_only")):
        record = declaration[name]
        extra = {"annotation_manifest"} if name == "genuine_edit" else set()
        if (not isinstance(record, Mapping) or set(record) != _FAMILY_FIELDS | extra
                or record.get("role") != role or record.get("case_count") != count
                or not isinstance(record.get("family_id"), str) or not record["family_id"]):
            raise ValueError(f"composition {name} family contract changed")
        _composition_file(record["source_cases"], label=name + " source cases")
        _composition_file(record["predeclaration"], label=name + " predeclaration")
        cases = load_case_file(Path(record["source_cases"]["path"]))
        case_ids = [case.case_id for case in cases]
        identities = _composition_input_identities(cases)
        if (len(cases) != count or ids & set(case_ids) or len(set(case_ids)) != count
                or record["ordered_case_ids_sha256"] != canonical_evidence_sha256(case_ids)
                or record["input_identities"] != identities):
            raise ValueError(f"composition {name} input membership/identity changed")
        ids.update(case_ids)
        families[name] = cases
        if name != "genuine_edit":
            annotations, issues = validate_source_predicate_predeclaration(cases=cases,
                path=Path(record["predeclaration"]["path"]), expected_sha256=record["predeclaration"]["sha256"])
            mode = read_public_evidence_reference(record["predeclaration"], label=name).get("version", PUBLIC_SOURCE_MODE)
            if issues or mode != (PUBLIC_SOURCE_MODE if name == "primary" else PUBLIC_EDIT_SOURCE_MODE):
                raise ValueError(f"composition {name} source predicates invalid: " + "; ".join(issues))
            if name == "high" and any(not case.lifecycle_correction or case.input_style != "edited_confirmation"
                    or annotations[case.case_id]["complexity_band"] != "high" for case in cases):
                raise ValueError("composition high family lacks four authentic high EDIT inputs")
            if name == "high":
                domains = {case.provenance.source_family for case in cases}
                primary_domains = {case.provenance.source_family for case in families["primary"] if case.provenance.source_family}
                if len(domains) != 4 or not domains <= primary_domains:
                    raise ValueError("composition High4 requires four distinct existing Primary40 domains")
            if name == "primary" and any(case.lifecycle_correction for case in cases):
                raise ValueError("composition primary source format changed")
        else:
            _composition_genuine_sources(record=record, cases=cases)
    if len({declaration[name]["family_id"] for name in families}) != 3:
        raise ValueError("composition family identities repeat")
    _composition_source_exclusions(declaration)
    return families


def _composition_genuine_sources(*, record: Mapping[str, Any], cases: Sequence[Any]) -> None:
    source = read_public_evidence_reference(record["predeclaration"], label="genuine predeclaration")
    if (source.get("version") != _GENUINE_VERSION or source["case_file"]["sha256"] != record["source_cases"]["sha256"]
            or [row["case_id"] for row in source["cases"]] != [case.case_id for case in cases]):
        raise ValueError("genuine exclusion-only source declaration differs")
    _composition_file({key: source["case_file"][key] for key in ("path", "sha256")}, label="genuine original case file")
    _composition_file(record["annotation_manifest"], label="genuine annotations")
    annotation = read_public_evidence_reference(record["annotation_manifest"], label="genuine annotations")
    if (annotation.get("version") != "odylith.genuine-edit-source-annotation-manifest.v1"
            or [row["case_id"] for row in annotation["cases"]] != [case.case_id for case in cases]):
        raise ValueError("genuine exclusion-only annotations differ")
    root = Path(record["annotation_manifest"]["path"]).resolve().parent
    from greenfield_matrix_release_artifacts import repo_artifact_path
    for row in annotation["cases"]:
        path = repo_artifact_path(root, row["annotation_path"])
        _composition_file({"path": str(path), "sha256": row["annotation_sha256"]}, label="genuine annotation")
    for case, row in zip(cases, source["cases"], strict=True):
        from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
        expected = {"initial-request.txt": case.prompt, "confirmed-intent.txt": case.confirmed_intent_markdown,
            "initial-prompt.txt": case.initial_prompt, "correction.txt": case.lifecycle_correction,
            "initial-source-frame.txt": prepare_model_authoring_evidence(prompt=case.initial_prompt).evidence_source,
            "edited-source-frame.txt": case.model_evidence.evidence_source}
        if set(row["files"]) != set(expected):
            raise ValueError("genuine source file membership changed")
        for name, value in expected.items():
            ref = {key: row["files"][name][key] for key in ("path", "sha256")}
            if _composition_file(ref, label="genuine source").read_bytes() != value.encode("utf-8"):
                raise ValueError("genuine source bytes differ from their native case")


def _composition_source_exclusions(declaration: Mapping[str, Any]) -> None:
    primary = {row["case_id"]: row for row in declaration["primary"]["input_identities"]}
    genuine = {row["case_id"]: row for row in declaration["genuine_edit"]["input_identities"]}
    source = read_public_evidence_reference(declaration["genuine_edit"]["predeclaration"], label="genuine predeclaration")
    originals = ("release-accessibility-005-source", "release-accessibility-007-source",
        "release-agriculture-021-description", "release-agriculture-037-source")
    if [(row["original_case_id"], row["case_id"]) for row in source["cases"]] != [
            (case_id, f"genuine-lifecycle-edit-v3-{index:02}") for index, case_id in enumerate(originals, 1)]:
        raise ValueError("composition changed the exact four authorized baseline/H0 pairs")
    pairs = []
    for row in source["cases"]:
        left, right = primary[row["original_case_id"]], genuine[row["case_id"]]
        if (any(left[key] != right[key] for key in ("baseline_request_sha256", "h0_source_sha256"))
                or not right["h1_source_sha256"] or right["h1_source_sha256"] == left["h0_source_sha256"]):
            raise ValueError("authorized genuine baseline/H0 pair does not match")
        pairs.append({"primary_case_id": left["case_id"], "genuine_case_id": right["case_id"],
            "baseline_request_sha256": left["baseline_request_sha256"], "h0_source_sha256": left["h0_source_sha256"]})
    if len({row["primary_case_id"] for row in pairs}) != 4 or declaration["permitted_baseline_overlap"] != pairs:
        raise ValueError("composition permitted baseline overlap differs from original four pairs")
    allowed = {(row["primary_case_id"], row["genuine_case_id"]) for row in pairs}
    families = {name: declaration[name]["input_identities"] for name in ("primary", "genuine_edit", "high")}
    observations = [(name, row) for name, rows in families.items() for row in rows]
    for index, (family, row) in enumerate(observations):
        for other_family, other in observations[:index]:
            pair = (other["case_id"], row["case_id"])
            if (other_family, family) == ("primary", "genuine_edit") and pair in allowed:
                continue
            frame_overlap = {row["h0_source_sha256"], row["h1_source_sha256"]} & {other["h0_source_sha256"], other["h1_source_sha256"]} - {None}
            same_request = row["baseline_request_sha256"] == other["baseline_request_sha256"]
            if row["h1_source_sha256"] and (row["h0_source_sha256"], row["correction_sha256"], row["h1_source_sha256"]) == (other["h0_source_sha256"], other["correction_sha256"], other["h1_source_sha256"]):
                raise ValueError("composition repeats a complete EDIT journey")
            if (family == "high" or other_family == "high") and (same_request or frame_overlap):
                raise ValueError("composition High4 reuses an existing source/journey")
            if family != other_family and (same_request or frame_overlap):
                raise ValueError("composition contains an undeclared primary/genuine overlap")


def _composition_execution(
    *, ref: Mapping[str, Any], declaration_ref: Mapping[str, Any], declaration: Mapping[str, Any],
    family: Mapping[str, Any], output_ref: Mapping[str, Any], manifest_ref: Mapping[str, Any],
    dispatch_ref: Mapping[str, Any], rows: Sequence[Any], common: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Associate actual request/result observations with original retained case custody."""
    from greenfield_matrix_release_artifacts import retained_evidence_manifest_issues, repo_artifact_path
    from greenfield_matrix_statistics import release_slice_evidence
    from dataclasses import replace
    for item in (ref, output_ref, manifest_ref, dispatch_ref):
        _composition_file(item, label="composition execution evidence")
    binding = read_public_evidence_reference(ref, label="execution binding")
    version = PUBLIC_COMPOSITION_MODE
    fields = {"version", "declaration_sha256", "family_id", "runner_sha256", "observed_before", "observed_after",
        "case_phases", *_EXECUTION_REFS, *(name + "_sha256" for name in _RELEASE_CUSTODY_REFS),
        "dispatch_attestation_sha256", "source_cases_sha256", "predeclaration_sha256", "output_sha256", "retained_manifest_sha256"}
    identities = {"declaration_sha256": declaration_ref["sha256"], "family_id": family["family_id"],
        **{name + "_sha256": value["sha256"] for name, value in declaration["release_custody"].items()},
        "dispatch_attestation_sha256": dispatch_ref["sha256"], "predeclaration_sha256": family["predeclaration"]["sha256"],
        "output_sha256": output_ref["sha256"], "retained_manifest_sha256": manifest_ref["sha256"]}
    if set(binding) != fields or binding.get("version") != version + ".execution-binding.v1" or any(binding.get(key) != value for key, value in identities.items()):
        raise ValueError("composition execution lacks exact declaration/package/family bindings")
    for name in _EXECUTION_REFS:
        _composition_file(binding[name], label=name)
    request = read_public_evidence_reference(binding["execution_request"], label="actual execution request")
    result = read_public_evidence_reference(binding["execution_result"], label="actual execution result")
    _composition_file(binding["execution_log"], label="actual execution log")
    request_fields = {"version", "family_id", "declaration_sha256", "release_custody_sha256", "source_cases_sha256",
        "predeclaration_sha256", "runner_sha256", "argv", "cwd", "observed_before"}
    result_fields = {"version", "family_id", "declaration_sha256", "request_sha256", "exit_code", "output_sha256",
        "retained_manifest_sha256", "log_sha256", "observed_after", "case_phases_sha256"}
    if (set(request) != request_fields or request.get("version") != version + ".execution-request.v1"
            or set(result) != result_fields or result.get("version") != version + ".execution-result.v1"
            or any(request.get(key) != binding[key] for key in ("family_id", "declaration_sha256", "source_cases_sha256", "predeclaration_sha256", "runner_sha256", "observed_before"))
            or request.get("release_custody_sha256") != canonical_evidence_sha256(declaration["release_custody"])
            or any(result.get(key) != binding[key] for key in ("family_id", "declaration_sha256", "output_sha256", "retained_manifest_sha256", "observed_after"))
            or result.get("request_sha256") != binding["execution_request"]["sha256"] or result.get("exit_code") != 0
            or result.get("log_sha256") != binding["execution_log"]["sha256"]
            or result.get("case_phases_sha256") != canonical_evidence_sha256(binding["case_phases"])):
        raise ValueError("composition request/result is not its actual execution association")
    if Path(request["cwd"]).resolve() != Path(common["source_export_root"]):
        raise ValueError("composition driver did not execute from the frozen export")
    before, after = binding["observed_before"], binding["observed_after"]
    if (not isinstance(before, Mapping) or set(before) != _OBSERVATION_FIELDS or before != after
            or any(before.get(key) != value for key, value in common.items())):
        raise ValueError("composition executed package/profile changed or differs between families")
    _composition_file({"path": before["runtime_executable"], "sha256": before["runtime_executable_sha256"]}, label="actual driver executable")
    imports = before["actual_import_pins"]
    required = {"odylith.runtime.domain_intelligence.greenfield_model_profile_contract",
        "odylith.runtime.domain_intelligence.greenfield_host_transport", "greenfield_preconfirm_matrix"}
    if not isinstance(imports, Mapping) or not required <= set(imports):
        raise ValueError("composition lacks actual driver import observations")
    for imported in imports.values():
        if not _composition_file(imported, label="actual imported owner").resolve().is_relative_to(Path(common["source_export_root"])):
            raise ValueError("composition imported owner is outside its frozen export")
    profile = read_public_evidence_reference(declaration["release_custody"]["profile"], label="profile")
    for module, name in (("greenfield_model_profile_contract", "profile"), ("greenfield_host_transport", "transport")):
        observed = imports["odylith.runtime.domain_intelligence." + module]
        if (observed["path"] != profile["actual_import_paths"][name]
                or observed["sha256"] != profile[name + "_owner_sha256"]):
            raise ValueError("composition actual imports differ from the activated profile owners")
    dispatch = read_public_evidence_reference(dispatch_ref, label="family dispatch attestation")
    association = dispatch.get("composition", {})
    if (set(association) != {"declaration_sha256", "family_id", "runner", "argv_sha256", "source_cases", "predeclaration_sha256"}
            or dispatch.get("status") not in {"CLEAR_READ_ONLY_CASE01_DISPATCH", "CLEAR_READ_ONLY_FAMILY_DISPATCH"}
            or dispatch["activation"]["sha256"] != identities["activation_sha256"]
            or any(dispatch["identity"].get(key) != common[target] for key, target in (("head", "commit"), ("tree", "tree"), ("archive_sha256", "archive_sha256")))
            or association["declaration_sha256"] != declaration_ref["sha256"]
            or association["family_id"] != family["family_id"]
            or association["predeclaration_sha256"] != family["predeclaration"]["sha256"]
            or association["source_cases"]["sha256"] != binding["source_cases_sha256"]
            or association["runner"]["sha256"] != binding["runner_sha256"]
            or not isinstance(request["argv"], list) or not request["argv"]
            or association["argv_sha256"] != canonical_evidence_sha256(request["argv"])):
        raise ValueError("composition dispatch is not bound to this family/runner/argv/subset")
    _composition_file(association["runner"], label="actual runner")
    _composition_file(association["source_cases"], label="actual invoked source cases")
    issues = retained_evidence_manifest_issues(Path(manifest_ref["path"]), expected_case_ids=[row.evidence["case"]["id"] for row in rows])
    if issues:
        raise ValueError("composition retained custody: " + "; ".join(issues))
    manifest = read_public_evidence_reference(manifest_ref, label="actual retained manifest")
    retained = {row["case_id"]: row for row in manifest["case_manifests"]}
    actual_sources = {row.evidence["case"]["source_file"] for row in rows}
    if len(actual_sources) != 1:
        raise ValueError("composition batch must retain one exact invoked case file")
    source_path = Path(next(iter(actual_sources)))
    if source_path.resolve() != Path(association["source_cases"]["path"]).resolve():
        raise ValueError("composition actual source differs from its dispatch")
    if sha256_file(source_path) != binding["source_cases_sha256"]:
        raise ValueError("composition execution source file changed")
    activation = read_public_evidence_reference(declaration["release_custody"]["activation"], label="activation")
    if (activation["file_pins"].get(str(source_path)) != binding["source_cases_sha256"]
            or activation["file_pins"].get(association["runner"]["path"]) != binding["runner_sha256"]):
        raise ValueError("composition invoked subset was not frozen before execution")
    cases = load_case_file(source_path)
    parent_cases = load_case_file(Path(family["source_cases"]["path"]))
    parent_ids = {case.case_id: case for case in parent_cases}
    if (any(replace(case, source_file=parent_ids[case.case_id].source_file) != parent_ids[case.case_id] for case in cases)
            or [case.case_id for case in cases] != [row.evidence["case"]["id"] for row in rows]):
        raise ValueError("composition actual batch differs from the declared parent family")
    phases = []
    source_declaration = read_public_evidence_reference(family["predeclaration"], label="family source census")
    census = {entry["case_id"]: entry.get("complexity_dimensions") for entry in source_declaration["cases"]}
    for case, row in zip(cases, rows, strict=True):
        stages = [row.evidence["lifecycle_edit"][phase]["observation"] for phase in ("initial", "edited")] if case.lifecycle_correction else [row.evidence["model_profile"]["stage_observation"]]
        for stage in stages:
            if stage.get("model_profile_id") != common["profile_id"]:
                raise ValueError("composition native phase uses a different activated profile")
            for name in ("authority_gate_request", "source_ledger_request", "source_duty_verifier_request", "host_request"):
                if name in stage and any(stage[name].get(key) != common[target] for key, target in (
                        ("executable_sha256", "trusted_executable_sha256"), ("model", "model"),
                        ("reasoning_effort", "reasoning_effort"), ("argv_shape_sha256", "argv_shape_sha256"))):
                    raise ValueError("composition native call differs from the activated executable/model/argv")
        _, problems = release_slice_evidence(case=case, result=row, retained_evidence_manifest=Path(manifest_ref["path"]),
            annotated_complexity=census[case.case_id], source_predicate_complexity=census[case.case_id],
            allow_unsealed_clarification=case.expectation == "clarification_required")
        if problems:
            raise ValueError("composition native case custody: " + "; ".join(problems))
        case_ref = retained[case.case_id]
        case_path = repo_artifact_path(Path(manifest_ref["path"]).resolve().parent, case_ref["path"])
        package = json.loads(case_path.read_text())
        if json.loads((case_path.parent / "case-result.v1.json").read_text()) != row.to_dict():
            raise ValueError("composition case result differs from retained bytes")
        phases.extend(_composition_case_phases(case=case, row=row, case_path=case_path,
            package=package, request_sha256=binding["execution_request"]["sha256"]))
    if binding["case_phases"] != phases:
        raise ValueError("composition phase/receipt/invocation association differs from retained evidence")
    return phases


def _composition_case_phases(*, case: Any, row: Any, case_path: Path, package: Mapping[str, Any], request_sha256: str) -> list[dict[str, Any]]:
    from greenfield_matrix_release_artifacts import repo_artifact_path
    from odylith.runtime.domain_intelligence.greenfield_pending_transaction_store import require_pending_transaction_released
    from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
    import hashlib
    evidence, phases = row.evidence, []
    labels = ("initial", "edited") if case.lifecycle_correction else ("initial",)
    for label in labels:
        phase = evidence["lifecycle_edit"][label] if case.lifecycle_correction else {}
        stage = phase["observation"] if phase else evidence["model_profile"]["stage_observation"]
        outcome = "clarify" if not phase and case.expectation == "clarification_required" else "commit"
        source = case.model_evidence.evidence_source if label == "edited" else prepare_model_authoring_evidence(prompt=case.initial_prompt).evidence_source
        artifacts = phase["artifacts"] if phase else package["artifacts"]
        tx = phase.get("transaction_hash") if phase else evidence.get("preconfirm_dry_run", {}).get("transaction_hash")
        if phase:
            receipt_path = repo_artifact_path(case_path.parent, phase["artifacts"][phase["completion_receipt_path"]]["retained_path"])
            tx_path = repo_artifact_path(case_path.parent, phase["artifacts"][phase["transaction_file"]]["retained_path"])
        else:
            receipt_path = case_path.parent / "semantic/native-completion-receipt.v1.json"
            tx_path = case_path.parent / "semantic/product-create-transaction.v1.json"
        receipt_sha, invocation = None, None
        if outcome == "commit":
            if not (tx_path.parent / ".bounded-journey.v1.json").is_file():
                raise ValueError("composition commit lacks actual bounded delivery custody")
            require_pending_transaction_released(tx_path, repo_root=case_path.parent, transaction_hash=tx, completion_receipt=receipt_path)
            receipt_sha = sha256_file(receipt_path)
            invocation = json.loads(receipt_path.read_text())["journey_id"]
        else:
            command = case_path.parent / "commands/propose.stdout"
            command_sha = sha256_file(command)
            if stage.get("proposal_stdout_sha256") != command_sha or evidence.get("preconfirm_dry_run"):
                raise ValueError("composition clarification command/no-write association changed")
            invocation = canonical_evidence_sha256({"execution_request_sha256": request_sha256, "case_id": case.case_id,
                "phase": label, "stage_sha256": canonical_evidence_sha256(stage),
                "command_stdout_sha256": command_sha, "result_sha256": canonical_evidence_sha256(row.to_dict())})
        phases.append({"case_id": case.case_id, "phase": label, "outcome": outcome,
            "result_sha256": canonical_evidence_sha256(row.to_dict()), "retained_case_manifest_sha256": sha256_file(case_path),
            "phase_artifact_manifest_sha256": canonical_evidence_sha256(artifacts), "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "transaction_hash": tx if outcome == "commit" else None, "completion_receipt_sha256": receipt_sha,
            "native_invocation_id": invocation})
    return phases


def qualify_composed_public_evidence(*, evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Score exactly Public40+High4; genuine EDIT4 is an authenticated separate gate."""
    from greenfield_model_profile_proof import model_profile_release_proof
    version = PUBLIC_COMPOSITION_MODE
    report = {"version": version, "status": "failed", "passed": False, "issues": [],
        "family_counts": {"primary": 40, "high": 4, "genuine_edit": 4}, "scored_denominator": 44,
        "genuine_scored_contribution": 0, "consumer_timing_custody": "unproved"}
    try:
        if set(evidence) != {"version", "declaration", "primary", "high", "genuine_edit"} or evidence["version"] != version:
            raise ValueError("composition requires its exact closed final evidence")
        _composition_file(evidence["declaration"], label="composition declaration")
        declaration = read_public_evidence_reference(evidence["declaration"], label="composition declaration")
        if set(declaration) != {"version", "authority_ref", "published_floors_sha256", "required_slices_sha256",
                "release_custody", "primary", "high", "genuine_edit", "permitted_baseline_overlap"} or declaration["version"] != version:
            raise ValueError("composition declaration has invalid fields/version")
        _composition_file(declaration["authority_ref"], label="composition prospective authority")
        floors = published_structural_floors()
        if (_frozen_floor_issues(floors) or declaration["published_floors_sha256"] != canonical_evidence_sha256(floors)
                or declaration["required_slices_sha256"] != canonical_evidence_sha256(release_slice_contract())):
            raise ValueError("composition changed published floors or required slices")
        families = _composition_membership(declaration)
        common = _composition_release_custody(declaration["release_custody"])
        sources, scored, phases, outputs, manifests, profiles = {"mode": version}, [], [], [], [], {}
        for name in ("primary", "high", "genuine_edit"):
            final, family = evidence[name], declaration[name]
            if name != "genuine_edit":
                if set(final) != {"source_evidence", "timing_evidence", "dispatch_attestation", "execution_binding"}:
                    raise ValueError("composition scored family has invalid final fields")
                source = final["source_evidence"]
                for name_ref in ("source_cases", "predeclaration", "output", "retained_manifest", "observed_bindings", "independent_audit", "review_record"):
                    _composition_file(source[name_ref], label="composition scored " + name_ref)
                if any(source[key] != family[key] for key in ("source_cases", "predeclaration")):
                    raise ValueError("composition scoring references a different source family")
                sources[name] = source
                base = read_public_evidence_reference(source["output"], label=name + " output")
                primary, controls = _saved_public_diagnostics(base)
                profile = model_profile_release_proof((*primary, *controls), require_complete=True,
                    whole_journey_bound_evidence=final["timing_evidence"], public_source_evidence=source)
                if profile.get("status") != "passed":
                    raise ValueError(name + " lacks exact native profile and independent finite timing proof")
                profiles[name] = profile
                scored.extend(primary)
                batches = [(source["output"], source["retained_manifest"], final["dispatch_attestation"], final["execution_binding"], primary)]
            else:
                batches = _composition_genuine_batches(final=final, family=family,
                    declaration_ref=evidence["declaration"], declaration=declaration)
            ids = []
            for output_ref, manifest_ref, dispatch_ref, execution_ref, rows in batches:
                outputs.append(output_ref["sha256"])
                manifests.append(manifest_ref["sha256"])
                ids.extend(row.evidence["case"]["id"] for row in rows)
                phases.extend((name, phase) for phase in _composition_execution(ref=execution_ref,
                    declaration_ref=evidence["declaration"], declaration=declaration, family=family,
                    output_ref=output_ref, manifest_ref=manifest_ref, dispatch_ref=dispatch_ref, rows=rows, common=common))
            if ids != [case.case_id for case in families[name]]:
                raise ValueError("composition final outputs changed ordered family membership/denominator")
        _composition_output_exclusions(phases=phases, declaration=declaration, outputs=outputs, manifests=manifests)
        semantic = evaluate_semantic_release(cases=(*families["primary"], *families["high"]), annotations={}, results=scored,
            floors=floors, release_required_slices=release_slice_contract(), source_predicate_evidence=sources)
        report.update(semantic_release=semantic, model_profile_proofs=profiles, evidence_refs=dict(evidence),
            published_floors_sha256=canonical_evidence_sha256(floors), same_release_observations=common)
        if semantic.get("status") != "passed" or semantic.get("sample_count") != 44:
            raise ValueError("composed semantic evidence did not meet every unchanged floor/confidence/coverage gate")
        report.update(status="passed", passed=True)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
        report["issues"].append(f"composed public qualification is incomplete: {exc}")
    return report


def _composition_genuine_batches(*, final: Mapping[str, Any], family: Mapping[str, Any], declaration_ref: Mapping[str, Any], declaration: Mapping[str, Any]) -> list[tuple[Any, ...]]:
    version = PUBLIC_COMPOSITION_MODE
    if set(final) != {"gate_report", "independent_review_record", "output", "retained_manifest", "dispatch_attestation", "execution_binding"}:
        raise ValueError("genuine separate gate final fields are incomplete")
    for value in final.values():
        _composition_file(value, label="genuine final evidence")
    wrappers = {key: read_public_evidence_reference(final[key], label="genuine " + key) for key in ("output", "retained_manifest", "execution_binding", "dispatch_attestation")}
    for name, suffix in (("output", "batch-outputs"), ("retained_manifest", "batch-manifests"), ("dispatch_attestation", "batch-dispatches")):
        if wrappers[name].keys() != {"version", "family_id", "batches"} or wrappers[name]["version"] != version + "." + suffix + ".v1" or wrappers[name]["family_id"] != family["family_id"] or len(wrappers[name]["batches"]) != 2:
            raise ValueError("genuine batch references require exact original1+3 evidence")
    envelope = wrappers["execution_binding"]
    if envelope != {"version": version + ".execution-binding-batches.v1", "declaration_sha256": declaration_ref["sha256"],
            "family_id": family["family_id"], "output_sha256": final["output"]["sha256"], "retained_manifest_sha256": final["retained_manifest"]["sha256"], "batches": envelope.get("batches")} or len(envelope["batches"]) != 2:
        raise ValueError("genuine execution batch envelope differs")
    batches = []
    for index in range(2):
        refs = [wrappers[name]["batches"][index] for name in ("output", "retained_manifest", "dispatch_attestation", "execution_binding")]
        output = read_public_evidence_reference(refs[0], label="genuine original batch output")
        rows = typed_saved_matrix_results(output["results"])
        if len(rows) != (1 if index == 0 else 3) or any(row.status != "passed" or not row.quality.passed for row in rows):
            raise ValueError("genuine original batch denominator/order changed")
        batches.append((*refs, rows))
    gate = read_public_evidence_reference(final["gate_report"], label="genuine independent gate")
    identities = {"declaration_sha256": declaration_ref["sha256"], "release_custody_sha256": canonical_evidence_sha256(declaration["release_custody"]),
        **{name + "_sha256": family[name]["sha256"] for name in ("source_cases", "predeclaration", "annotation_manifest")},
        **{name + "_sha256": final[name]["sha256"] for name in ("output", "retained_manifest")}}
    ids = [row["case_id"] for row in family["input_identities"]]
    if gate != {"version": version + ".genuine-gate.v1", "status": "passed", "qualified_case_ids": ids,
            **identities, "independent_review_record_sha256": final["independent_review_record"]["sha256"]}:
        raise ValueError("genuine gate lacks all four current independent verdicts/bindings")
    review = read_public_evidence_reference(final["independent_review_record"], label="genuine independent review")
    if set(review) != {"version", *identities, "reviewer", "cases"} or review["version"] != version + ".genuine-review-record.v1" or any(review[key] != value for key, value in identities.items()):
        raise ValueError("genuine review is not bound to its current sources/package/outputs")
    from greenfield_onboarding_review import validate_independent_reviewer
    issues, awaiting = [], []
    validate_independent_reviewer(review["reviewer"], forbidden_context_ids=set(identities.values()), issues=issues, awaiting=awaiting)
    actual_rows = [row for batch in batches for row in batch[-1]]
    if issues or awaiting or len(review["cases"]) != 4 or any(set(verdict) != {"case_id", "verdict", "result_sha256", "rationale"}
            or verdict["case_id"] != row.evidence["case"]["id"] or verdict["verdict"] != "passed"
            or verdict["result_sha256"] != canonical_evidence_sha256(row.to_dict())
            or not isinstance(verdict["rationale"], str) or not verdict["rationale"].strip()
            for verdict, row in zip(review["cases"], actual_rows, strict=True)):
        raise ValueError("genuine separate semantic gate lacks complete independent actual-result review")
    return batches


def _composition_output_exclusions(*, phases: Sequence[Any], declaration: Mapping[str, Any], outputs: Sequence[str], manifests: Sequence[str]) -> None:
    if len(set(outputs)) != len(outputs) or len(set(manifests)) != len(manifests):
        raise ValueError("composition reuses an actual output or retained manifest")
    allowed = {(row["primary_case_id"], row["genuine_case_id"]) for row in declaration["permitted_baseline_overlap"]}
    for index, (family, phase) in enumerate(phases):
        for other_family, other in phases[:index]:
            same_case = family == other_family and phase["case_id"] == other["case_id"]
            if not same_case and any(phase[key] == other[key] for key in ("result_sha256", "retained_case_manifest_sha256")):
                raise ValueError("composition reuses an actual result/case package")
            if phase["native_invocation_id"] == other["native_invocation_id"] or (phase["completion_receipt_sha256"] is not None and phase["completion_receipt_sha256"] == other["completion_receipt_sha256"]):
                raise ValueError("composition reuses a native invocation or delivered receipt")
            permitted_h0 = (other_family, family) == ("primary", "genuine_edit") and (other["case_id"], phase["case_id"]) in allowed and other["phase"] == phase["phase"] == "initial"
            if phase["transaction_hash"] is not None and phase["transaction_hash"] == other["transaction_hash"] and not permitted_h0:
                raise ValueError("composition reuses a transaction outside independently prepared permitted H0 pairs")
