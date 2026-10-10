"""Statistical release evidence for Greenfield matrix outcomes."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
import hashlib
import json
from math import sqrt
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    combined_prompt_evidence_source,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    supported_greenfield_model_profile_ids,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    SUPPORTED_COMPLEXITY_BANDS,
    SUPPORTED_PUBLIC_INPUT_FORMATS,
    greenfield_complexity_band,
    greenfield_operating_envelope_receipt,
    require_supported_greenfield_operating_envelope,
)

from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_matrix_transaction_evidence import _TERMINAL_CONFIRMATION_FIELDS, _TERMINAL_CONFIRMATION_VERSION
from greenfield_matrix_release_artifacts import (
    repo_artifact_path, retained_evidence_manifest_issues, sha256_file,
)
from greenfield_model_profile_proof import authored_model_result_binding_issues, model_profile_release_proof
from greenfield_preconfirm_matrix_cases import case_evidence
from odylith.runtime.domain_intelligence.greenfield_create_transaction import load_compiled_product_create_transaction_file
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_pending_transaction_store import require_pending_transaction_released
from odylith.runtime.domain_intelligence.greenfield_prewrite_commit_result import require_greenfield_commit_result_preview
from odylith.runtime.domain_intelligence.greenfield_proposals_cli import _edit_preservation
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import verify_greenfield_source_duty_ledger_receipt
from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import whole_journey_observation_issues


STATISTICS_VERSION = "odylith.greenfield.matrix.statistics.v4"
STATISTICAL_CONFIDENCE_VERSION = "odylith.greenfield.statistical-confidence.v1"
_Z_95 = 1.959963984540054
_MINIMUM_RELEASE_SLICE_SAMPLES = 4
_CONFIDENCE_THRESHOLD_KEYS = frozenset(
    {
        "atomic_semantic_fidelity",
        "relation_fidelity",
        "clarification_identity",
        "unnecessary_question_rate_ceiling",
        "overall_case_success",
        "worst_slice_success",
    }
)
RELEASE_SLICE_DIMENSIONS = (
    "complexity_band",
    "evidence_format",
    "model_profile",
)
_DISCOVERY_TAG_SLICE_DIMENSIONS = frozenset(
    {"complexity", "model_profile", "host_profile"}
)
_HOST_NATIVE_OBSERVATION_FIELDS = {
    "origin",
    "host_candidate",
    "runtime_semantic_model_call_count",
}
_HOST_CANDIDATE_FIELDS = {
    "version",
    "contract_version",
    "canonical_version",
    "source_sha256",
    "raw_candidate_sha256",
    "canonical_candidate_sha256",
    "source_duty_ledger_sha256",
    "source_duty_verifier_task_sha256",
    "source_duty_decision_set_sha256",
    "source_duty_binding_sha256",
}


def outcome_statistics(
    *,
    cases: Sequence[Any],
    results: Sequence[GreenfieldMatrixResult],
    release: bool = False,
    required_slices: Mapping[str, Sequence[str]] | None = None,
    retained_evidence_manifest: Path | None = None,
) -> dict[str, Any]:
    """Report point estimates, intervals, and evidence-bound release slices.

    Discovery retains the historic descriptive tag slices.  Release reports
    instead classify the support-critical axes from each sealed transaction;
    case tags cannot manufacture coverage.
    """

    case_ids = [_case_id(case) for case in cases]
    result_ids = [_result_case_id(result) for result in results]
    duplicate_case_ids = _duplicates(case_ids)
    duplicate_result_ids = _duplicates(result_ids)
    results_by_id = {case_id: result for case_id, result in zip(result_ids, results, strict=False) if case_id}
    rows: list[dict[str, Any]] = []
    slice_members: dict[tuple[str, str], list[bool]] = defaultdict(list)
    missing_case_ids: list[str] = []
    evidence_issues: list[str] = []
    for case in cases:
        case_id = _case_id(case)
        result = results_by_id.get(case_id)
        if result is None:
            missing_case_ids.append(case_id)
            continue
        passed = result.status == "passed" and result.quality.passed
        slices = _case_slices(case)
        if release:
            safe_clarification = _safe_unsealed_clarification(case=case, result=result)
            sealed_slices, sealed_issues = release_slice_evidence(
                case=case,
                result=result,
                annotated_complexity=(
                    expected_case_source_complexity(case)
                    if safe_clarification
                    else None
                ),
                allow_unsealed_clarification=safe_clarification,
                retained_evidence_manifest=retained_evidence_manifest,
            )
            evidence_issues.extend(
                f"case `{case_id}` {issue}"
                for issue in sealed_issues
            )
            if getattr(case, "lifecycle_correction", "") and sealed_issues:
                passed = False
            slices = (
                *(
                    row
                    for row in slices
                    if row[0] not in _DISCOVERY_TAG_SLICE_DIMENSIONS
                ),
                *sealed_slices.items(),
            )
        rows.append({"case_id": case_id, "passed": passed})
        for dimension, value in slices:
            slice_members[(dimension, value)].append(passed)

    passed_count = sum(1 for row in rows if row["passed"])
    sample_count = len(rows)
    slices = [
        _slice_row(dimension=dimension, value=value, outcomes=outcomes)
        for (dimension, value), outcomes in sorted(slice_members.items())
    ]
    completed_slices = [row for row in slices if int(row["sample_count"]) > 0]
    worst = min(
        completed_slices,
        key=lambda row: (
            float(row["point_estimate"]),
            float(row["confidence_interval_95"]["lower"]),
            str(row["dimension"]),
            str(row["value"]),
        ),
        default=None,
    )
    least_confident = min(
        completed_slices,
        key=lambda row: (
            float(row["confidence_interval_95"]["lower"]),
            float(row["point_estimate"]),
            str(row["dimension"]),
            str(row["value"]),
        ),
        default=None,
    )
    lower, upper = wilson_interval(passed_count, sample_count)
    supplied_release_contract = (
        required_slices if required_slices is not None else release_slice_contract()
    )
    release_contract = _normalized_slice_contract(supplied_release_contract) if release else {}
    release_contract_issues = (
        _release_slice_contract_issues(
            supplied=supplied_release_contract,
            normalized=release_contract,
        )
        if release
        else []
    )
    release_minimum_samples = release_slice_minimum_sample_contract() if release else {}
    coverage_issues = (
        release_slice_coverage_issues(
            slices=slices,
            required=release_contract,
            minimum_samples=release_minimum_samples,
        )
        if release
        else []
    )
    failing_release_slices = [
        row
        for row in slices
        if row["dimension"] in release_contract and int(row["failed_count"]) > 0
    ]
    complete = not (
        missing_case_ids
        or duplicate_case_ids
        or duplicate_result_ids
        or evidence_issues
        or release_contract_issues
        or coverage_issues
    )
    confidence_contract = release_statistical_confidence_contract() if release else {}
    acceptance_checks = (
        [
            threshold_check(
                "overall_case_success",
                observed=_rate(passed_count, sample_count) if sample_count else None,
                expected=1.0,
                direction="floor",
            ),
            threshold_check(
                "worst_slice_success",
                observed=worst.get("point_estimate") if worst else None,
                expected=1.0,
                direction="floor",
            ),
        ]
        if release
        else []
    )
    confidence_checks = (
        [
            threshold_check(
                "overall_case_success",
                observed=lower if sample_count else None,
                expected=confidence_contract.get("overall_case_success"),
                direction="floor",
            ),
            threshold_check(
                "worst_slice_success",
                observed=(
                    _mapping(least_confident.get("confidence_interval_95")).get("lower")
                    if least_confident
                    else None
                ),
                expected=confidence_contract.get("worst_slice_success"),
                direction="floor",
            ),
        ]
        if release
        else []
    )
    acceptance_passed = all(row["status"] == "passed" for row in acceptance_checks)
    confidence_passed = all(row["status"] == "passed" for row in confidence_checks)
    passed = (
        complete
        and not failing_release_slices
        and acceptance_passed
        and confidence_passed
    )
    return {
        "version": STATISTICS_VERSION,
        "status": (
            "passed" if release and passed
            else "failed" if release
            else "complete" if complete
            else "incomplete"
        ),
        "passed": passed if release else complete,
        "selected_case_count": len(cases),
        "sample_count": sample_count,
        "passed_count": passed_count,
        "failed_count": sample_count - passed_count,
        "point_estimate": _rate(passed_count, sample_count),
        "confidence_interval_95": _interval_payload(lower, upper),
        "missing_case_ids": missing_case_ids,
        "duplicate_case_ids": duplicate_case_ids,
        "duplicate_result_ids": duplicate_result_ids,
        "release_required_slices": release_contract,
        "release_minimum_samples": release_minimum_samples,
        "release_contract_issues": release_contract_issues,
        "release_evidence_issues": list(dict.fromkeys(evidence_issues)),
        "release_coverage_issues": coverage_issues,
        "failing_release_slices": failing_release_slices,
        "worst_slice": worst or {},
        "least_confident_slice": least_confident or {},
        "acceptance_passed": acceptance_passed if release else None,
        "acceptance_checks": acceptance_checks,
        "confidence_passed": confidence_passed if release else None,
        "confidence_contract": confidence_contract,
        "confidence_checks": confidence_checks,
        "slices": slices,
    }


def release_slice_contract() -> dict[str, tuple[str, ...]]:
    """Return every published release slice that needs observed coverage."""

    return {
        "complexity_band": tuple(SUPPORTED_COMPLEXITY_BANDS),
        "evidence_format": tuple(SUPPORTED_PUBLIC_INPUT_FORMATS),
        "model_profile": supported_greenfield_model_profile_ids(),
    }


def release_slice_minimum_sample_contract() -> dict[str, dict[str, int]]:
    """Return the frozen evidence count required for every release slice.

    Four is the smallest perfect binomial sample whose 95% Wilson lower bound
    exceeds one half; smaller slices cannot support even a majority claim.
    """

    return {
        dimension: {
            value: _MINIMUM_RELEASE_SLICE_SAMPLES
            for value in values
        }
        for dimension, values in release_slice_contract().items()
    }


def release_slice_minimum_sample_contract_issues(value: Any) -> list[str]:
    """Reject absent, narrowed, or operator-softened release sample minima."""

    if not isinstance(value, Mapping):
        return ["release slice minimum samples must match the published contract"]
    normalized: dict[str, dict[str, int]] = {}
    for dimension, required_values in release_slice_contract().items():
        rows = value.get(dimension)
        if not isinstance(rows, Mapping):
            normalized[dimension] = {}
            continue
        normalized[dimension] = {
            str(slice_value): int(sample_count)
            for slice_value, sample_count in rows.items()
            if (
                str(slice_value).strip()
                and isinstance(sample_count, int)
                and not isinstance(sample_count, bool)
                and sample_count > 0
            )
        }
        if set(rows) != set(required_values):
            continue
    if (
        set(value) != set(RELEASE_SLICE_DIMENSIONS)
        or normalized != release_slice_minimum_sample_contract()
    ):
        return ["release slice minimum samples must match the published contract"]
    return []


def release_statistical_confidence_contract() -> dict[str, Any]:
    """Return confidence gates that are achievable at frozen release minima.

    A perfect four-observation sample has a 95% Wilson lower bound of
    0.510109, while a zero-failure sample has an upper bound of 0.489891.
    The uniform 0.5 confidence gate is therefore the strongest simple
    threshold supported by the published minimum. Product acceptance remains
    separately fixed at exact 1.0 success and 0.0 unnecessary questions.
    """

    return {
        "version": STATISTICAL_CONFIDENCE_VERSION,
        "method": "wilson",
        "confidence_level": 0.95,
        "atomic_semantic_fidelity": 0.5,
        "relation_fidelity": 0.5,
        "clarification_identity": 0.5,
        "unnecessary_question_rate_ceiling": 0.5,
        "overall_case_success": 0.5,
        "worst_slice_success": 0.5,
    }


def release_statistical_confidence_contract_issues(
    value: Any,
    *,
    minimum_samples: Mapping[str, Mapping[str, int]] | None = None,
) -> list[str]:
    """Validate confidence schema and feasibility at declared sample minima."""

    expected_keys = {
        "version",
        "method",
        "confidence_level",
        *_CONFIDENCE_THRESHOLD_KEYS,
    }
    if not isinstance(value, Mapping) or set(value) != expected_keys:
        return ["statistical confidence must use only the v1 confidence fields"]
    issues: list[str] = []
    if value.get("version") != STATISTICAL_CONFIDENCE_VERSION:
        issues.append(
            f"statistical confidence must declare {STATISTICAL_CONFIDENCE_VERSION}"
        )
    if value.get("method") != "wilson" or value.get("confidence_level") != 0.95:
        issues.append("statistical confidence must use the 95% Wilson interval")
    for name in sorted(_CONFIDENCE_THRESHOLD_KEYS):
        threshold = value.get(name)
        if (
            not isinstance(threshold, (int, float))
            or isinstance(threshold, bool)
            or not 0.0 <= float(threshold) <= 1.0
        ):
            issues.append(
                f"statistical confidence `{name}` must be a number from 0 through 1"
            )
    if issues:
        return issues
    sample_contract = (
        minimum_samples
        if minimum_samples is not None
        else release_slice_minimum_sample_contract()
    )
    minimum = release_statistical_confidence_sample_minimum(sample_contract)
    if minimum <= 0:
        return ["statistical confidence has no positive declared sample minimum"]
    perfect_lower, _perfect_upper = wilson_interval(minimum, minimum)
    _zero_lower, zero_upper = wilson_interval(0, minimum)
    for name in sorted(_CONFIDENCE_THRESHOLD_KEYS - {"unnecessary_question_rate_ceiling"}):
        if float(value[name]) > perfect_lower:
            issues.append(
                f"statistical confidence `{name}` cannot reach {float(value[name]):.6f} "
                f"at the declared minimum of {minimum}; perfect evidence reaches {perfect_lower:.6f}"
            )
    ceiling = float(value["unnecessary_question_rate_ceiling"])
    if ceiling < zero_upper:
        issues.append(
            "statistical confidence `unnecessary_question_rate_ceiling` cannot reach "
            f"{ceiling:.6f} at the declared minimum of {minimum}; "
            f"zero failures reach {zero_upper:.6f}"
        )
    return issues


def release_statistical_confidence_sample_minimum(
    minimum_samples: Mapping[str, Mapping[str, int]] | None = None,
) -> int:
    """Return the smallest positive denominator promised by release preflight."""

    sample_contract = (
        minimum_samples
        if minimum_samples is not None
        else release_slice_minimum_sample_contract()
    )
    declared_minima = [
        int(sample_count)
        for rows in sample_contract.values()
        if isinstance(rows, Mapping)
        for sample_count in rows.values()
        if isinstance(sample_count, int)
        and not isinstance(sample_count, bool)
        and sample_count > 0
    ]
    return min(declared_minima, default=0)


def expected_case_evidence_format(case: Any) -> str:
    """Return the public format actually sent through Greenfield authoring."""

    return case.model_evidence.source_format


def expected_case_source_complexity(case: Any) -> dict[str, int]:
    """Return source dimensions independently knowable from frozen case bytes."""

    prepared = case.model_evidence
    return {
        "evidence_bytes": len(prepared.evidence_source.encode("utf-8")),
        "documents": prepared.source_document_count,
    }


def release_slice_evidence(
    *,
    case: Any,
    result: GreenfieldMatrixResult,
    annotated_complexity: Mapping[str, Any] | None = None,
    source_predicate_complexity: Mapping[str, Any] | None = None,
    allow_unsealed_clarification: bool = False,
    retained_evidence_manifest: Path | None = None,
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Return support slices from sealed evidence, never from mutable case tags."""

    issues: list[str] = []
    evidence = _mapping(result.evidence)
    receipt = _mapping(evidence.get("preconfirm_dry_run"))
    snapshot = _mapping(receipt.get("semantic_snapshot"))
    envelope = _mapping(snapshot.get("operating_envelope"))
    expected_format = expected_case_evidence_format(case)
    annotated = dict(annotated_complexity) if isinstance(annotated_complexity, Mapping) else {}
    source_dimensions = expected_case_source_complexity(case)
    for dimension, expected in source_dimensions.items():
        if annotated and annotated.get(dimension) != expected:
            issues.append(f"annotated complexity `{dimension}` does not match frozen source evidence")

    sealed_profile = ""
    if envelope:
        try:
            require_supported_greenfield_operating_envelope(envelope)
        except ValueError:
            issues.append("has an invalid sealed operating-envelope receipt")
        complexity = _mapping(envelope.get("complexity"))
        dimensions = _mapping(complexity.get("dimensions"))
        if source_predicate_complexity is not None:
            observed = _mapping(_mapping(envelope.get("evidence_contract")).get("observed"))
            try:
                expected_envelope = greenfield_operating_envelope_receipt(
                    facts=_mapping(snapshot.get("facts")), source_format=expected_format,
                    source_size_bytes=source_dimensions["evidence_bytes"],
                    source_document_count=source_dimensions["documents"],
                    source_language=str(observed.get("language") or ""),
                    model_authoring=_mapping(_mapping(envelope.get("model_contract")).get("observed")),
                )
                if envelope != expected_envelope:
                    issues.append("sealed representation census or operating-envelope custody changed")
            except (ValueError, TypeError, KeyError):
                issues.append("cannot verify sealed representation operating envelope")
        elif annotated and dimensions != annotated:
            issues.append("annotated complexity does not match the sealed operating-envelope dimensions")
        complexity_band = str(complexity.get("band") or "").strip()
        evidence_format = str(envelope.get("evidence_format") or "").strip()
        observed_model = _mapping(_mapping(envelope.get("model_contract")).get("observed"))
        _sealed_observation_issues = _host_authority_observation_issues(observed_model)
        issues.extend(_sealed_observation_issues)
    elif allow_unsealed_clarification and annotated:
        complexity_band = greenfield_complexity_band(annotated)
        evidence_format = expected_format
    else:
        complexity_band = ""
        evidence_format = ""
        issues.append("lacks a sealed operating-envelope receipt")

    if evidence_format != expected_format:
        issues.append("sealed evidence format does not match the frozen case input")
    if getattr(case, "lifecycle_correction", ""):
        edit_issues = _receipt_bound_edit_issues(
            case=case, result=result, manifest=retained_evidence_manifest,
        )
        issues.extend(edit_issues)
        if edit_issues:
            # An invalid lifecycle row remains a failed sample, never EDIT coverage.
            evidence_format = ""
    if source_predicate_complexity is not None:
        if dict(source_predicate_complexity) != annotated:
            issues.append("source-predicate census does not match frozen source annotation")
        complexity_band = greenfield_complexity_band(source_predicate_complexity)
    model_evidence = _mapping(evidence.get("model_profile"))
    observed_profile = str(model_evidence.get("profile_id") or "").strip()
    if not observed_profile:
        issues.append("lacks an observed model profile")
    elif observed_profile not in supported_greenfield_model_profile_ids():
        issues.append("claims an unknown model profile")
    if model_evidence.get("status") != "passed" or model_evidence.get("issues") != []:
        issues.append("has unproven model-profile result evidence")
    if envelope:
        sealed_profile = observed_profile
    elif (
        observed_profile
        and allow_unsealed_clarification
        and _safe_unsealed_clarification(case=case, result=result)
    ):
        sealed_profile = observed_profile

    slices = {
        "complexity_band": complexity_band,
        "evidence_format": evidence_format,
        "model_profile": sealed_profile or observed_profile,
    }
    for dimension, value in slices.items():
        if not value:
            issues.append(f"lacks release slice `{dimension}`")
    return slices, tuple(dict.fromkeys(issues))


def _safe_unsealed_clarification(*, case: Any, result: GreenfieldMatrixResult) -> bool:
    if getattr(case, "lifecycle_correction", ""):
        return False
    expected_case = case_evidence(case)
    observed_case = _mapping(_mapping(result.evidence).get("case"))
    if expected_case.get("expectation") != "clarification_required":
        return False
    if result.status != "passed" or not result.quality.passed:
        return False
    for key in (
        "id",
        "expectation",
        "prompt_sha256",
        "confirmed_intent_sha256",
        "expected_clarification",
    ):
        if observed_case.get(key) != expected_case.get(key):
            return False
    source = combined_prompt_evidence_source(
        prompt=case.initial_prompt,
        edit_evidence="",
    )
    expected_source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    profile_evidence = _mapping(_mapping(result.evidence).get("model_profile"))
    if profile_evidence.get("expected_source_sha256") != expected_source_sha256:
        return False
    proof = model_profile_release_proof((result,), require_complete=False)
    return (
        proof.get("status") == "passed"
        and proof.get("version")
        and profile_evidence.get("semantic_authority") == "active_host_single_authority"
    )


def _retained_edit_root(*, case: Any, result: GreenfieldMatrixResult, manifest: Path | None) -> Path:
    if manifest is None:
        raise ValueError("EDIT lacks a finalized retained evidence manifest")
    problems = retained_evidence_manifest_issues(manifest)
    if problems:
        raise ValueError("EDIT retained evidence failed custody: " + "; ".join(problems))
    root = Path(manifest).resolve().parent
    package = json.loads(Path(manifest).read_text(encoding="utf-8"))
    references = [row for row in package["case_manifests"] if row["case_id"] == _case_id(case)]
    if len(references) != 1:
        raise ValueError("EDIT retained evidence does not identify its exact case")
    case_manifest = repo_artifact_path(root, references[0]["path"])
    if case_manifest is None:
        raise ValueError("EDIT retained case manifest is unsafe")
    case_root = case_manifest.parent
    retained_result = json.loads((case_root / "case-result.v1.json").read_text(encoding="utf-8"))
    if retained_result != json.loads(json.dumps(result.to_dict())):
        raise ValueError("EDIT result differs from its authenticated retained case result")
    return case_root


def _retained_edit_phase(*, root: Path, label: str, phase: Mapping[str, Any], source: str) -> Any:
    digest = phase.get("transaction_hash")
    source_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if not _is_sha256(digest) or phase.get("source_sha256") != source_digest:
        raise ValueError(f"EDIT {label} seal/source identity changed")
    artifacts = _mapping(phase.get("artifacts"))
    transaction_token = phase.get("transaction_file")
    receipt_token = phase.get("completion_receipt_path")
    if not artifacts or transaction_token not in artifacts or receipt_token not in artifacts:
        raise ValueError(f"EDIT {label} lacks its original seal and delivered receipt references")
    pending_tail = f"/.odylith/runtime/greenfield/pending/{digest}/product-create-transaction.v1.json"
    if not isinstance(transaction_token, str) or not transaction_token.endswith(pending_tail):
        raise ValueError(f"EDIT {label} original pending identity is not canonical")
    consumer_identity = transaction_token[:-len(pending_tail)]
    bound_paths = set()
    completion_paths = []
    for original, row in artifacts.items():
        row = _mapping(row)
        if not isinstance(original, str) or not Path(original).is_absolute():
            raise ValueError(f"EDIT {label} original artifact identity is invalid")
        kind = row.get("kind")
        filename = "completion-receipt.json" if kind == "completion_receipt" else Path(original).name
        relative = f"semantic/lifecycle-{label}/{filename}"
        retained = repo_artifact_path(root, str(row.get("retained_path") or ""))
        if (kind not in {"pending", "completion_receipt"} or row.get("retained_path") != relative
                or retained is None or relative in bound_paths or not retained.is_file()
                or not _is_sha256(row.get("sha256")) or sha256_file(retained) != row["sha256"]
                or type(row.get("mode")) is not int or not 0 <= row["mode"] <= 0o777
                or row.get("retained_mode") != 0o600 or retained.stat().st_mode & 0o777 != 0o600):
            raise ValueError(f"EDIT {label} retained artifact bytes, mode or membership changed")
        bound_paths.add(relative)
        if kind == "completion_receipt":
            completion_paths.append((original, retained))
        elif Path(original).parent != Path(transaction_token).parent:
            raise ValueError(f"EDIT {label} original pending artifacts belong to different consumers")
    directory = root / f"semantic/lifecycle-{label}"
    if ({path.relative_to(root).as_posix() for path in directory.iterdir()} != bound_paths
            or len(completion_paths) != 1 or completion_paths[0][0] != receipt_token):
        raise ValueError(f"EDIT {label} retained pending membership or delivered receipt changed")
    transaction_path = repo_artifact_path(root, artifacts[transaction_token]["retained_path"])
    if transaction_path is None or transaction_path.name != "product-create-transaction.v1.json":
        raise ValueError(f"EDIT {label} retained transaction path is invalid")
    if not (transaction_path.parent / ".bounded-journey.v1.json").is_file():
        raise ValueError(f"EDIT {label} lacks bounded preparation custody")
    require_pending_transaction_released(
        transaction_path, repo_root=root, transaction_hash=digest,
        completion_receipt=completion_paths[0][1],
    )
    delivered = json.loads(completion_paths[0][1].read_bytes())
    canonical_receipt = f"{consumer_identity}/.odylith/runtime/greenfield/completion-receipts/{digest}/{delivered['journey_id']}.json"
    if receipt_token != canonical_receipt:
        raise ValueError(f"EDIT {label} original delivered receipt belongs to a foreign consumer")
    transaction = load_compiled_product_create_transaction_file(transaction_path)
    if transaction.transaction_hash != digest or transaction.proposal["intent"]["prompt"] != source:
        raise ValueError(f"EDIT {label} compiler seal does not preserve its exact source")
    observation = _mapping(phase.get("observation"))
    if whole_journey_observation_issues(observation) or observation.get("source_sha256") != source_digest:
        raise ValueError(f"EDIT {label} lacks its exact bounded model observation")
    candidate_path = root / ("diagnostics-initial/candidate.stdout" if label == "initial" else "semantic/host-candidate.raw.v1.json")
    ledger_path = root / ("diagnostics-initial/source-ledger-check.stdout" if label == "initial" else "semantic/host-source-ledger-check.raw.v1.json")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))["receipt"]
    binding_issues = authored_model_result_binding_issues(
        stage_observation=observation, raw_candidate=candidate, source_duty_receipt=ledger,
        create_payload={"commit_manifest": transaction.quality_manifest}, expected_source=source,
    )
    if binding_issues:
        raise ValueError(f"EDIT {label} model/source binding failed: " + "; ".join(binding_issues))
    if label == "initial":
        model = _mapping(phase.get("model_profile"))
        if (phase.get("model_binding_issues") != [] or model.get("status") != "passed"
                or model.get("issues") != [] or model.get("expected_source_sha256") != source_digest
                or model.get("stage_observation") != observation):
            raise ValueError("EDIT initial model proof does not match its bounded source")
    elif phase.get("source_duty_receipt") != ledger:
        raise ValueError("EDIT edited source-duty receipt differs from the actual retained checker receipt")
    return transaction


def _receipt_bound_edit_issues(*, case: Any, result: GreenfieldMatrixResult, manifest: Path | None) -> tuple[str, ...]:
    try:
        root = _retained_edit_root(case=case, result=result, manifest=manifest)
        evidence = _mapping(result.evidence)
        lifecycle = _mapping(evidence.get("lifecycle_edit"))
        if "failure" in lifecycle or lifecycle.get("custody_issues"):
            raise ValueError("EDIT retains lifecycle failure or custody issues and cannot earn credit")
        if (lifecycle.get("version") != "odylith.greenfield.matrix.receipt-bound-edit.v1"
                or lifecycle.get("status") != "edited_seal_confirmed"):
            raise ValueError("EDIT lacks a confirmed receipt-bound lifecycle journey")
        for field, source in (("initial_request_sha256", case.initial_prompt), ("correction_sha256", case.lifecycle_correction)):
            if lifecycle.get(field) != hashlib.sha256(source.encode("utf-8")).hexdigest():
                raise ValueError("EDIT request/correction does not match its frozen case")
        if (evidence.get("case") != case_evidence(case) or result.status != "passed"
                or not result.quality.passed or result.create_returncode != 0
                or not result.browser_surface_proof_attempted or result.browser_surface_issues
                or evidence.get("browser_surface_proof") != {"required": True, "attempted": True, "issues": []}):
            raise ValueError("EDIT lacks exact case, committed quality and successful browser proof")
        for path, source in (("lifecycle.initial-request", case.initial_prompt), ("lifecycle.correction", case.lifecycle_correction)):
            if (root / "commands" / path).read_bytes() != source.encode("utf-8"):
                raise ValueError("EDIT retained request/correction bytes changed")
        initial = _mapping(lifecycle.get("initial"))
        edited = _mapping(lifecycle.get("edited"))
        initial_source = prepare_model_authoring_evidence(prompt=case.initial_prompt).evidence_source
        prepared = case.model_evidence
        previous = _retained_edit_phase(root=root, label="initial", phase=initial, source=initial_source)
        current = _retained_edit_phase(root=root, label="edited", phase=edited, source=prepared.evidence_source)
        if Path(initial["transaction_file"]).parents[5] != Path(edited["transaction_file"]).parents[5]:
            raise ValueError("EDIT seals do not belong to the same original consumer")
        if current.transaction_hash == previous.transaction_hash:
            raise ValueError("equal or no-op seals cannot count as committed EDIT samples")
        before = {token: {key: row[key] for key in ("sha256", "mode")} for token, row in initial["artifacts"].items()}
        if lifecycle.get("initial_artifacts_after_confirm") != before:
            raise ValueError("EDIT lacks exact final preservation readback of every initial artifact")
        context = _edit_preservation(previous, correction=prepared.edit_evidence,
            evidence_text=prepared.evidence_source)
        duty = current.proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]
        verified = verify_greenfield_source_duty_ledger_receipt(
            duty, evidence_text=prepared.evidence_source, edit_preservation=context, allow_legacy_edit=False,
        )
        if (verified != edited.get("source_duty_receipt")
                or any(row["verdict"] != "preserved" or row["correction_authorization"] != "not_required"
                    for row in verified["decision_set"]["edit_preservation"].values())):
            raise ValueError("EDIT did not preserve every prior duty without correction authorization")
        dry_run = _mapping(evidence.get("preconfirm_dry_run"))
        snapshot = _mapping(dry_run.get("semantic_snapshot"))
        envelope = _mapping(snapshot.get("operating_envelope"))
        observed = _mapping(_mapping(envelope.get("evidence_contract")).get("observed"))
        if (dry_run.get("status") != "compiled" or dry_run.get("transaction_hash") != current.transaction_hash
                or envelope != current.intent_authority["operating_envelope"]
                or envelope.get("evidence_format") != prepared.source_format
                or _mapping(_mapping(envelope.get("complexity")).get("dimensions")).get("documents") != 2
                or _mapping(_mapping(envelope.get("complexity")).get("dimensions")).get("evidence_bytes") != len(prepared.evidence_source.encode("utf-8"))
                or observed.get("documents") != 2):
            raise ValueError("EDIT sealed envelope is not its exact two-document edited source")
        model = _mapping(evidence.get("model_profile"))
        if (model.get("expected_source_sha256") != edited.get("source_sha256")
                or model.get("stage_observation") != edited.get("observation")
                or model.get("profile_id") != _mapping(initial.get("model_profile")).get("profile_id")
                or model_profile_release_proof((result,), require_complete=False).get("status") != "passed"):
            raise ValueError("EDIT model proof does not describe its edited seal")
        initial_model_row = replace(result, evidence={**evidence, "model_profile": initial["model_profile"]})
        if model_profile_release_proof((initial_model_row,), require_complete=False).get("status") != "passed":
            raise ValueError("EDIT initial preparation lacks full model-profile proof")
        confirmation = _mapping(evidence.get("confirmation_contract"))
        journal_bytes = (root / "commands/terminal-journal.v1.json").read_bytes()
        journal = json.loads(journal_bytes)
        journal_hash = hashlib.sha256(journal_bytes).hexdigest()
        committed = require_greenfield_commit_result_preview(journal.get("commit_result"))
        if (committed.get("validation_gate", {}).get("status") != "passed"
                or any(committed.get(key) != value for key, value in current.prewrite_package.commit_result_preview.items())
                or journal.get("repository_write_set_hash") != dry_run.get("repository_write_set_hash")):
            raise ValueError("EDIT journal commit result differs from its sealed result preview")
        if (confirmation.get("status") != "passed" or confirmation.get("scope") != "explicit_terminal_decision"
                or confirmation.get("commit_payload_source") != "closed_journal"
                or any(confirmation.get(key) != [] for key in ("decision_rail_issues", "terminal_handoff_issues", "terminal_proof_issues"))
                or confirmation.get("terminal_journal") != journal or confirmation.get("terminal_journal_sha256") != journal_hash
                or _mapping(confirmation.get("terminal_pre_retry_snapshot")).get("journal_sha256") != journal_hash
                or journal.get("state") != "closed" or journal.get("lifecycle_state") != "CLOSED"
                or journal.get("transaction_hash") != current.transaction_hash
                or not journal.get("commit_result")
                or json.loads((root / "semantic/create-payload.v1.json").read_text()) != journal["commit_result"]
                or [(row.get("attempt"), row.get("returncode")) for row in confirmation.get("terminal_commands", ())]
                   != [("confirm", 0), ("same_hash_retry", 0)]):
            raise ValueError("EDIT lacks its committed CLOSED journal and unchanged same-hash retry")
        for label in ("decide", "retry-decide"):
            response = json.loads((root / f"commands/{label}.stdout").read_bytes())
            if (set(response) != _TERMINAL_CONFIRMATION_FIELDS or response.get("version") != _TERMINAL_CONFIRMATION_VERSION
                    or response.get("status") != "CLOSED" or response.get("command") != "CONFIRM"
                    or response.get("transaction_hash") != current.transaction_hash
                    or not str(response.get("visible_markdown") or "").strip()
                    or not str(response.get("developer_context") or "").strip()):
                raise ValueError("EDIT retained CONFIRM/retry response does not bind its CLOSED seal")
        return ()
    except (OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return (str(exc),)


def wilson_interval(successes: int, sample_count: int) -> tuple[float, float]:
    """Return a bounded 95% Wilson score interval for a binomial rate."""

    if sample_count <= 0:
        return 0.0, 1.0
    successes = max(0, min(int(successes), int(sample_count)))
    n = float(sample_count)
    estimate = successes / n
    z2 = _Z_95 * _Z_95
    denominator = 1.0 + z2 / n
    center = (estimate + z2 / (2.0 * n)) / denominator
    margin = (_Z_95 / denominator) * sqrt((estimate * (1.0 - estimate) / n) + (z2 / (4.0 * n * n)))
    return round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6)


def threshold_check(
    name: str,
    *,
    observed: Any,
    expected: Any,
    direction: str,
) -> dict[str, Any]:
    """Return one fail-closed numeric floor or ceiling decision."""

    if not isinstance(expected, (int, float)) or isinstance(expected, bool):
        return {
            "name": name,
            "status": "unproven",
            "observed": observed,
            "expected": expected,
            "issue": f"{name} has no frozen threshold",
        }
    if not isinstance(observed, (int, float)) or isinstance(observed, bool):
        return {
            "name": name,
            "status": "unproven",
            "observed": observed,
            "expected": expected,
            "issue": f"{name} is unproven (0 of 0 is not a pass)",
        }
    passed = observed >= expected if direction == "floor" else observed <= expected
    symbol = ">=" if direction == "floor" else "<="
    return {
        "name": name,
        "status": "passed" if passed else "failed",
        "observed": observed,
        "expected": expected,
        "issue": "" if passed else f"{name} {observed:.6f} does not satisfy {symbol} {expected:.6f}",
    }


def _slice_row(*, dimension: str, value: str, outcomes: Sequence[bool]) -> dict[str, Any]:
    passed = sum(1 for outcome in outcomes if outcome)
    total = len(outcomes)
    lower, upper = wilson_interval(passed, total)
    return {
        "dimension": dimension,
        "value": value,
        "sample_count": total,
        "passed_count": passed,
        "failed_count": total - passed,
        "point_estimate": _rate(passed, total),
        "confidence_interval_95": _interval_payload(lower, upper),
    }


def _case_slices(case: Any) -> tuple[tuple[str, str], ...]:
    values: list[tuple[str, str]] = []
    input_style = str(getattr(case, "input_style", "") or "unspecified").strip()
    values.append(("input_style", input_style))
    expectation = str(getattr(case, "expectation", "") or "transaction_committed").strip()
    values.append(("expectation", expectation))
    provenance = getattr(case, "provenance", None)
    source_family = str(getattr(provenance, "source_family", "") or "unspecified").strip()
    values.append(("source_family", source_family))
    for stressor in getattr(case, "stressors", ()) or ():
        token = str(stressor or "").strip()
        if token:
            values.append(("stressor", token))
    for tag in getattr(case, "tags", ()) or ():
        token = str(tag or "").strip()
        if token.startswith("complexity:"):
            values.append(("complexity", token.partition(":")[2] or "unspecified"))
        elif token.startswith("model-profile:"):
            values.append(("model_profile", token.partition(":")[2] or "unspecified"))
        elif token.startswith("host-profile:"):
            values.append(("host_profile", token.partition(":")[2] or "unspecified"))
    return tuple(dict.fromkeys(values))


def _normalized_slice_contract(
    value: Mapping[str, Sequence[str]],
) -> dict[str, tuple[str, ...]]:
    contract: dict[str, tuple[str, ...]] = {}
    for dimension in RELEASE_SLICE_DIMENSIONS:
        rows = value.get(dimension)
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
            contract[dimension] = ()
            continue
        contract[dimension] = tuple(
            dict.fromkeys(str(item or "").strip() for item in rows if str(item or "").strip())
        )
    return contract


def _release_slice_contract_issues(
    *,
    supplied: Mapping[str, Sequence[str]],
    normalized: Mapping[str, Sequence[str]],
) -> list[str]:
    if set(supplied) != set(RELEASE_SLICE_DIMENSIONS):
        return ["release slice contract must declare only every published slice dimension"]
    if dict(normalized) != release_slice_contract():
        return ["release slice contract does not match the published operating envelope"]
    return []


def release_slice_coverage_issues(
    *,
    slices: Sequence[Mapping[str, Any]],
    required: Mapping[str, Sequence[str]],
    minimum_samples: Mapping[str, Mapping[str, int]] | None = None,
) -> list[str]:
    issues: list[str] = []
    observed: dict[str, set[str]] = defaultdict(set)
    sample_counts: dict[tuple[str, str], int] = {}
    for row in slices:
        dimension = str(row.get("dimension") or "")
        value = str(row.get("value") or "")
        if dimension in required and value:
            observed[dimension].add(value)
            sample_counts[(dimension, value)] = int(row.get("sample_count", 0) or 0)
    for dimension, required_values in required.items():
        required_set = set(required_values)
        dimension_minimums = _mapping(_mapping(minimum_samples).get(dimension))
        missing = sorted(required_set - observed[dimension])
        unknown = sorted(observed[dimension] - required_set)
        if missing:
            issues.append(f"release evidence lacks {dimension} coverage: " + ", ".join(missing))
        if unknown:
            issues.append(f"release evidence has unknown {dimension} slices: " + ", ".join(unknown))
        for value in sorted(required_set & observed[dimension]):
            minimum = int(dimension_minimums.get(value, 0) or 0)
            observed_count = sample_counts.get((dimension, value), 0)
            if minimum > 0 and observed_count < minimum:
                issues.append(
                    f"release evidence has {observed_count} sample(s) for {dimension} `{value}`; "
                    f"requires at least {minimum}"
                )
    return issues


def _result_case_id(result: GreenfieldMatrixResult) -> str:
    evidence = result.evidence if isinstance(result.evidence, Mapping) else {}
    case = evidence.get("case") if isinstance(evidence.get("case"), Mapping) else {}
    return str(case.get("id") or "").strip()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _host_authority_observation_issues(
    observed: Mapping[str, Any],
) -> tuple[str, ...]:
    issues: list[str] = []
    if set(observed) != _HOST_NATIVE_OBSERVATION_FIELDS:
        return ("host-native model observation has an invalid closed schema",)
    if observed.get("origin") != "host_native":
        issues.append("model observation does not identify host authority")
    if observed.get("runtime_semantic_model_call_count") != 0:
        issues.append("model observation reports a runtime semantic call")
    candidate = _mapping(observed.get("host_candidate"))
    if set(candidate) != _HOST_CANDIDATE_FIELDS:
        issues.append("host_candidate lacks the exact sealed receipt")
    for field in (
        "source_sha256",
        "raw_candidate_sha256",
        "canonical_candidate_sha256",
        "source_duty_ledger_sha256",
        "source_duty_verifier_task_sha256",
        "source_duty_decision_set_sha256",
        "source_duty_binding_sha256",
    ):
        if not _is_sha256(candidate.get(field)):
            issues.append(f"host_candidate {field} is invalid")
    return tuple(dict.fromkeys(issues))


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and not set(value) - set("0123456789abcdef")
    )


def _case_id(case: Any) -> str:
    return str(getattr(case, "case_id", "") or getattr(case, "slug", "")).strip()


def _rate(successes: int, sample_count: int) -> float:
    return round(successes / sample_count, 6) if sample_count else 0.0


def _duplicates(values: Sequence[str]) -> list[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _interval_payload(lower: float, upper: float) -> dict[str, Any]:
    return {
        "method": "wilson",
        "lower": lower,
        "upper": upper,
        "inference_scope": "descriptive fixed-corpus score interval; not a population user-utility claim",
    }


__all__ = [
    "RELEASE_SLICE_DIMENSIONS",
    "STATISTICS_VERSION",
    "STATISTICAL_CONFIDENCE_VERSION",
    "expected_case_evidence_format",
    "expected_case_source_complexity",
    "outcome_statistics",
    "release_slice_contract",
    "release_slice_coverage_issues",
    "release_slice_evidence",
    "release_slice_minimum_sample_contract",
    "release_slice_minimum_sample_contract_issues",
    "release_statistical_confidence_contract",
    "release_statistical_confidence_contract_issues",
    "release_statistical_confidence_sample_minimum",
    "threshold_check",
    "wilson_interval",
]
