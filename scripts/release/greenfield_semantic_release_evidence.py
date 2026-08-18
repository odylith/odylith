"""Fail-closed evidence validation for Greenfield semantic release scoring."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from greenfield_semantic_development_evidence import AUTHOR_SEGMENT_VERSION
from greenfield_semantic_development_evidence import DEVELOPMENT_EVIDENCE_PLAN_VERSION
from greenfield_semantic_development_evidence import MECHANISM_EVIDENCE_VERSION
from greenfield_semantic_development_evidence import MECHANISM_ID
from greenfield_semantic_development_evidence import canonical_sha256
from greenfield_semantic_development_evidence import development_mechanism_contract_sha256
from greenfield_semantic_development_evidence import materiality_critic_input_for_case
from greenfield_semantic_development_evidence import require_development_evidence_plan
from greenfield_semantic_development_evidence import require_run_evidence
from greenfield_semantic_development_evidence import semantic_graph_author_input_for_case
from greenfield_semantic_deterministic_law_contract import require_deterministic_law_report
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_intent_packet,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    SEMANTIC_REASONING_CAPABILITY_PROFILE,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    semantic_materiality_assessment_sha256,
)


EVALUATION_CONTRACT_VERSION = "odylith.greenfield.semantic-release-evaluation-contract.v2"
CANDIDATE_BUNDLE_VERSION = "odylith.greenfield.semantic-release-candidates.v3"
REPORT_VERSION = "odylith.greenfield.semantic-release-report.v2"

FLOOR_NAMES = (
    "maximum_p0_findings",
    "maximum_p1_findings",
    "minimum_fact_precision",
    "minimum_accepted_fact_custody",
    "minimum_constraint_recall",
    "minimum_explicit_system_recall",
    "minimum_material_question_recall",
    "maximum_unnecessary_question_rate",
    "minimum_first_path_comprehension",
    "minimum_package_utility",
    "minimum_equivalent_source_convergence",
    "minimum_overall_success",
    "minimum_worst_slice_success",
    "maximum_deterministic_law_failures",
)
RESOURCE_CEILING_NAMES = (
    "maximum_case_total_wall_ms",
    "maximum_case_total_tokens",
    "maximum_case_model_calls",
    "maximum_case_restarts",
    "maximum_cohort_total_wall_ms",
    "maximum_cohort_total_tokens",
    "maximum_cohort_model_calls",
    "maximum_cohort_restarts",
)
FROZEN_FLOORS = {
    "maximum_p0_findings": 0.0,
    "maximum_p1_findings": 0.0,
    "minimum_fact_precision": 1.0,
    "minimum_accepted_fact_custody": 1.0,
    "minimum_constraint_recall": 1.0,
    "minimum_explicit_system_recall": 1.0,
    "minimum_material_question_recall": 0.95,
    "maximum_unnecessary_question_rate": 0.05,
    "minimum_first_path_comprehension": 0.9,
    "minimum_package_utility": 0.9,
    "minimum_equivalent_source_convergence": 1.0,
    "minimum_overall_success": 0.95,
    "minimum_worst_slice_success": 0.8,
    "maximum_deterministic_law_failures": 0.0,
}
FROZEN_RESOURCE_CEILINGS = {
    "maximum_case_total_wall_ms": 600_000,
    "maximum_case_total_tokens": 100_000,
    "maximum_case_model_calls": 2,
    "maximum_case_restarts": 0,
    "maximum_cohort_total_wall_ms": 14_400_000,
    "maximum_cohort_total_tokens": 2_400_000,
    "maximum_cohort_model_calls": 48,
    "maximum_cohort_restarts": 0,
}
REQUIRED_AUXILIARY_REPORTS = (
    "host_parity",
    "lower_capability_safety",
)
FROZEN_AUXILIARY_REPORT_VERSIONS = {
    "host_parity": "odylith.greenfield.host-parity-report.v1",
    "lower_capability_safety": (
        "odylith.greenfield.lower-capability-safety-evaluation.v1"
    ),
}
_ALLOWED_HOST_SETS = (
    ("codex",),
    ("codex", "claude"),
)


def require_evaluation_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the frozen v2 semantic and resource release contract."""

    row = _mapping(value, "evaluation contract")
    _exact_keys(
        row,
        {
            "version",
            "mechanism_id",
            "floors",
            "resource_ceilings",
            "required_model_profiles",
            "required_host_profiles",
            "required_auxiliary_reports",
            "minimum_independent_reviews",
        },
        "evaluation contract",
    )
    if row.get("version") != EVALUATION_CONTRACT_VERSION:
        raise ValueError("semantic release evaluation contract uses an unsupported version")
    if row.get("mechanism_id") != MECHANISM_ID:
        raise ValueError("semantic release evaluation contract uses an unsupported mechanism")
    floors = _mapping(row.get("floors"), "evaluation contract floors")
    _exact_keys(floors, set(FLOOR_NAMES), "evaluation contract floors")
    normalized_floors = {
        name: _number(floors.get(name), f"floors.{name}") for name in FLOOR_NAMES
    }
    if normalized_floors != FROZEN_FLOORS:
        raise ValueError("semantic release evaluation contract changes a frozen release floor")
    ceilings = _mapping(row.get("resource_ceilings"), "resource ceilings")
    _exact_keys(ceilings, set(RESOURCE_CEILING_NAMES), "resource ceilings")
    normalized_ceilings = {
        name: _nonnegative_integer(ceilings.get(name), f"resource_ceilings.{name}")
        for name in RESOURCE_CEILING_NAMES
    }
    if normalized_ceilings != FROZEN_RESOURCE_CEILINGS:
        raise ValueError("semantic release evaluation contract changes a frozen resource ceiling")
    if (
        normalized_ceilings["maximum_case_total_wall_ms"] == 0
        or normalized_ceilings["maximum_case_total_tokens"] == 0
        or normalized_ceilings["maximum_cohort_total_wall_ms"] == 0
        or normalized_ceilings["maximum_cohort_total_tokens"] == 0
    ):
        raise ValueError("wall and token resource ceilings must be positive")
    profiles = _strings(row.get("required_model_profiles"), "required_model_profiles")
    if profiles != [SEMANTIC_REASONING_CAPABILITY_PROFILE]:
        raise ValueError("semantic authority requires only the frontier reasoning profile")
    hosts = _strings(row.get("required_host_profiles"), "required_host_profiles")
    if tuple(hosts) not in _ALLOWED_HOST_SETS:
        raise ValueError("semantic release host profiles must be Codex or Codex plus Claude")
    auxiliary = _mapping(row.get("required_auxiliary_reports"), "required auxiliary reports")
    _exact_keys(auxiliary, set(REQUIRED_AUXILIARY_REPORTS), "required auxiliary reports")
    auxiliary_versions = {
        name: _text(auxiliary.get(name), f"required auxiliary report {name}")
        for name in REQUIRED_AUXILIARY_REPORTS
    }
    if auxiliary_versions != FROZEN_AUXILIARY_REPORT_VERSIONS:
        raise ValueError("semantic release evaluation contract changes an auxiliary gate")
    minimum_reviews = row.get("minimum_independent_reviews")
    if minimum_reviews != 2 or isinstance(minimum_reviews, bool):
        raise ValueError("evaluation requires exactly two independent reviewers")
    return {
        "version": EVALUATION_CONTRACT_VERSION,
        "mechanism_id": MECHANISM_ID,
        "floors": normalized_floors,
        "resource_ceilings": normalized_ceilings,
        "required_model_profiles": profiles,
        "required_host_profiles": hosts,
        "required_auxiliary_reports": auxiliary_versions,
        "minimum_independent_reviews": minimum_reviews,
    }


def require_auxiliary_reports(
    value: Mapping[str, Mapping[str, Any]],
    *,
    contract: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    """Require passed auxiliary safety/parity reports and bind their full payloads."""

    reports = _mapping(value, "auxiliary reports")
    required = _mapping(contract.get("required_auxiliary_reports"), "required auxiliary reports")
    _exact_keys(reports, set(required), "auxiliary reports")
    bindings: dict[str, dict[str, str]] = {}
    for name in REQUIRED_AUXILIARY_REPORTS:
        report = _mapping(reports.get(name), f"auxiliary report {name}")
        if report.get("version") != required[name]:
            raise ValueError(f"auxiliary report {name} uses an unsupported version")
        if report.get("status") != "passed" or (
            "passed" in report and report.get("passed") is not True
        ):
            raise ValueError(f"auxiliary report {name} did not pass")
        bindings[name] = {
            "version": str(report["version"]),
            "status": "passed",
            "sha256": canonical_sha256(report),
        }
    return bindings


def require_candidate_bundle(
    value: Mapping[str, Any],
    *,
    corpus: Mapping[str, Any],
    corpus_sha256: str,
    case_index: Mapping[str, Mapping[str, Any]],
    contract: Mapping[str, Any],
    evidence_plan: Mapping[str, Any],
    deterministic_law_report: Mapping[str, Any],
) -> tuple[
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
    str,
    dict[str, Mapping[str, int]],
    dict[str, Any],
]:
    """Validate candidate truth against runner-owned assignments and execution receipts."""

    frozen_corpus_sha = _sha256(corpus_sha256, "frozen corpus sha256")
    bundle = _mapping(value, "candidate bundle")
    _exact_keys(
        bundle,
        {
            "version",
            "corpus_sha256",
            "implementation_revision",
            "authoring_contract_sha256",
            "development_evidence_plan_sha256",
            "deterministic_law_report_sha256",
            "cohort_nonce",
            "cases",
        },
        "candidate bundle",
    )
    if bundle.get("version") != CANDIDATE_BUNDLE_VERSION:
        raise ValueError("candidate bundle uses an unsupported version")
    if bundle.get("corpus_sha256") != frozen_corpus_sha:
        raise ValueError("candidate bundle does not match the frozen corpus")
    revision = _sha256(bundle.get("implementation_revision"), "implementation revision", length=40)
    authoring_sha = semantic_intent_authoring_contract_sha256()
    if bundle.get("authoring_contract_sha256") != authoring_sha:
        raise ValueError("candidate bundle uses a stale authoring contract")
    try:
        plan = require_development_evidence_plan(
            evidence_plan,
            corpus=corpus,
            corpus_sha256=frozen_corpus_sha,
        )
        law_report = require_deterministic_law_report(
            deterministic_law_report,
            implementation_revision=revision,
            candidate_bundle_version=CANDIDATE_BUNDLE_VERSION,
            development_evidence_plan_version=DEVELOPMENT_EVIDENCE_PLAN_VERSION,
            development_author_segment_version=AUTHOR_SEGMENT_VERSION,
            mechanism_evidence_version=MECHANISM_EVIDENCE_VERSION,
        )
    except RuntimeError as error:
        raise ValueError(str(error)) from error
    plan_sha = canonical_sha256(plan)
    law_sha = canonical_sha256(law_report)
    if bundle.get("development_evidence_plan_sha256") != plan_sha:
        raise ValueError("candidate bundle does not bind the development evidence plan")
    if bundle.get("deterministic_law_report_sha256") != law_sha:
        raise ValueError("candidate bundle does not bind the deterministic law report")
    if bundle.get("cohort_nonce") != plan["cohort_nonce"]:
        raise ValueError("candidate bundle does not bind the runner-owned cohort")
    if plan["required_host_profiles"] != list(contract["required_host_profiles"]):
        raise ValueError("evidence plan host assignments differ from the evaluation contract")
    if plan["capability_profile"] != SEMANTIC_REASONING_CAPABILITY_PROFILE:
        raise ValueError("evidence plan uses a non-authority capability profile")
    rows = _mapped_rows(bundle.get("cases"), "candidate cases")
    raw_candidates = _unique_index(rows, "case_id", "candidate cases")
    if set(raw_candidates) != set(case_index):
        raise ValueError("candidate bundle must cover every frozen case exactly once")
    assignments = _unique_index(plan["cases"], "case_id", "evidence plan assignments")
    candidates: dict[str, Mapping[str, Any]] = {}
    meta: dict[str, Mapping[str, Any]] = {}
    resources: dict[str, Mapping[str, int]] = {}
    observed_run_nonces: set[str] = set()
    observed_run_ids: set[str] = set()
    for case_id in sorted(raw_candidates):
        candidate, candidate_meta, telemetry = _require_candidate_case(
            raw_candidates[case_id],
            case_id=case_id,
            prompt=str(case_index[case_id]["prompt"]),
            corpus=corpus,
            plan=plan,
            plan_sha256=plan_sha,
            assignment=assignments[case_id],
            law_report_sha256=law_sha,
            run_nonces=observed_run_nonces,
            run_ids=observed_run_ids,
        )
        candidates[case_id] = candidate
        meta[case_id] = candidate_meta
        resources[case_id] = telemetry
    if {row["host_profile"] for row in meta.values()} != set(
        contract["required_host_profiles"]
    ):
        raise ValueError("candidate bundle does not prove every required release host")
    if {row["model_profile"] for row in meta.values()} != set(
        contract["required_model_profiles"]
    ):
        raise ValueError("candidate bundle does not prove every required authority profile")
    return (
        candidates,
        meta,
        canonical_sha256(bundle),
        resources,
        {
            "development_evidence_plan_sha256": plan_sha,
            "deterministic_law_report_sha256": law_sha,
            "mechanism_contract_sha256": development_mechanism_contract_sha256(),
            "cohort_assignment_sha256": str(plan["cohort_assignment_sha256"]),
            "cases": {
                case_id: {
                    name: meta[case_id][name]
                    for name in (
                        "assignment_sha256",
                        "mechanism_evidence_sha256",
                        "critic_run_assignment_sha256",
                        "critic_run_sha256",
                        "critic_input_sha256",
                        "critic_output_sha256",
                        "author_run_assignment_sha256",
                        "author_run_sha256",
                        "author_input_sha256",
                        "author_output_sha256",
                    )
                }
                for case_id in sorted(meta)
            },
        },
    )


def _require_candidate_case(
    value: Mapping[str, Any],
    *,
    case_id: str,
    prompt: str,
    corpus: Mapping[str, Any],
    plan: Mapping[str, Any],
    plan_sha256: str,
    assignment: Mapping[str, Any],
    law_report_sha256: str,
    run_nonces: set[str],
    run_ids: set[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    raw = _mapping(value, f"candidate {case_id}")
    _exact_keys(
        raw,
        {
            "case_id",
            "prompt_sha256",
            "outcome",
            "semantic_artifact",
            "mechanism_evidence",
            "review_package",
            "transaction_proof",
        },
        f"candidate {case_id}",
    )
    prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if raw.get("prompt_sha256") != prompt_sha:
        raise ValueError(f"candidate {case_id} does not match its source prompt")
    artifact = _mapping(raw.get("semantic_artifact"), f"candidate {case_id} semantic artifact")
    try:
        verified = require_semantic_intent_packet(artifact, prompt=prompt)
    except (RuntimeError, ValueError) as error:
        raise ValueError(f"candidate {case_id} has an invalid assessed packet: {error}") from error
    evidence = _mapping(raw.get("mechanism_evidence"), f"candidate {case_id} mechanism evidence")
    _exact_keys(
        evidence,
        {
            "version",
            "mechanism_id",
            "mechanism_contract_sha256",
            "cohort_nonce",
            "cohort_assignment_sha256",
            "case_nonce",
            "assignment_sha256",
            "evidence_plan_sha256",
            "authoring_contract_sha256",
            "critic",
            "author",
            "compile_wall_ms",
            "total_wall_ms",
            "model_call_count",
            "restart_count",
            "total_tokens",
        },
        f"candidate {case_id} mechanism evidence",
    )
    expected_mechanism = {
        "version": MECHANISM_EVIDENCE_VERSION,
        "mechanism_id": MECHANISM_ID,
        "mechanism_contract_sha256": development_mechanism_contract_sha256(),
        "cohort_nonce": plan["cohort_nonce"],
        "cohort_assignment_sha256": plan["cohort_assignment_sha256"],
        "case_nonce": assignment["case_nonce"],
        "assignment_sha256": assignment["assignment_sha256"],
        "evidence_plan_sha256": plan_sha256,
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
    }
    for name, expected in expected_mechanism.items():
        if evidence.get(name) != expected:
            raise ValueError(f"candidate {case_id} mechanism evidence mismatch: {name}")
    assessment = verified.materiality_assessment
    materiality_sha = semantic_materiality_assessment_sha256(assessment)
    try:
        critic_input = materiality_critic_input_for_case(
            corpus=corpus,
            plan=plan,
            case_id=case_id,
        )
        author_input = semantic_graph_author_input_for_case(
            corpus=corpus,
            plan=plan,
            case_id=case_id,
            materiality_assessment=assessment,
        )
        critic = require_run_evidence(
            evidence.get("critic"),
            stage="critic",
            assignment=assignment["critic_assignment"],
            expected_input_sha256=canonical_sha256(critic_input),
            expected_output_sha256=canonical_sha256(assessment),
        )
        author_evidence = _mapping(
            evidence.get("author"),
            f"candidate {case_id} author evidence",
        )
        author = require_run_evidence(
            author_evidence,
            stage="author",
            assignment=assignment["author_assignment"],
            expected_input_sha256=canonical_sha256(author_input),
            expected_output_sha256=canonical_sha256(
                {
                    "semantic_intent": verified.semantic_intent,
                    "self_challenge": author_evidence.get("self_challenge"),
                }
            ),
            materiality_assessment_sha256=materiality_sha,
        )
        if critic["host_runtime"] != author["host_runtime"]:
            raise RuntimeError("critic and author host runtime receipts differ")
    except RuntimeError as error:
        raise ValueError(f"candidate {case_id} execution evidence is invalid: {error}") from error
    for stage, receipt in (("critic", critic), ("author", author)):
        nonce = str(receipt["run_nonce"])
        run_id = str(receipt["run_id"])
        if nonce in run_nonces or run_id in run_ids:
            raise ValueError(f"candidate {case_id} reuses a runner {stage} identity")
        run_nonces.add(nonce)
        run_ids.add(run_id)
    if (
        critic["host_profile"] != author["host_profile"]
        or critic["capability_profile"] != author["capability_profile"]
        or artifact["critic_run"]["critic_run_id"] != critic["run_id"]
        or artifact["author_run"]["author_run_id"] != author["run_id"]
        or artifact["critic_run"]["host_profile"] != critic["host_profile"]
        or artifact["critic_run"]["capability_profile"] != critic["capability_profile"]
        or artifact["author_run"]["capability_profile"] != author["capability_profile"]
    ):
        raise ValueError(f"candidate {case_id} packet and runner receipts disagree")
    outcome = raw.get("outcome")
    status = verified.semantic_intent.get("status")
    if (outcome, status) not in {
        ("commit", "complete"),
        ("clarify", "clarification_required"),
    }:
        raise ValueError(f"candidate {case_id} outcome disagrees with its assessed packet")
    transaction_proof = _require_transaction_proof(
        raw.get("transaction_proof"),
        outcome=str(outcome),
        case_id=case_id,
        law_report_sha256=law_report_sha256,
    )
    _require_review_package(
        raw.get("review_package"),
        outcome=str(outcome),
        case_id=case_id,
        package_sha256=str(transaction_proof["package_sha256"]),
    )
    compile_wall_ms = _positive_integer(
        evidence.get("compile_wall_ms"), f"candidate {case_id} compile_wall_ms"
    )
    total_wall_ms = _positive_integer(
        evidence.get("total_wall_ms"), f"candidate {case_id} total_wall_ms"
    )
    total_tokens = _positive_integer(
        evidence.get("total_tokens"), f"candidate {case_id} total_tokens"
    )
    if total_wall_ms != critic["wall_ms"] + author["wall_ms"] + compile_wall_ms:
        raise ValueError(f"candidate {case_id} wall telemetry does not add up")
    expected_tokens = (
        critic["token_usage"]["total_tokens"] + author["token_usage"]["total_tokens"]
    )
    if total_tokens != expected_tokens:
        raise ValueError(f"candidate {case_id} token telemetry does not add up")
    if evidence.get("model_call_count") != 2 or evidence.get("restart_count") != 0:
        raise ValueError(f"candidate {case_id} call or restart telemetry violates the mechanism")
    normalized = {
        **raw,
        "model_profile": author["capability_profile"],
        "host_profile": author["host_profile"],
    }
    semantic_intent = verified.semantic_intent
    return (
        normalized,
        {
            "candidate_sha256": canonical_sha256(raw),
            "fact_ids": frozenset(str(row["fact_id"]) for row in semantic_intent.get("facts", [])),
            "relation_ids": frozenset(
                str(row["relation_id"]) for row in semantic_intent.get("relations", [])
            ),
            "model_profile": author["capability_profile"],
            "host_profile": author["host_profile"],
            "author_run_id": author["run_id"],
            "critic_run_id": critic["run_id"],
            "assignment_sha256": assignment["assignment_sha256"],
            "mechanism_evidence_sha256": canonical_sha256(evidence),
            "critic_run_assignment_sha256": critic["run_assignment_sha256"],
            "critic_run_sha256": critic["run_sha256"],
            "critic_input_sha256": critic["input_sha256"],
            "critic_output_sha256": critic["output_sha256"],
            "author_run_assignment_sha256": author["run_assignment_sha256"],
            "author_run_sha256": author["run_sha256"],
            "author_input_sha256": author["input_sha256"],
            "author_output_sha256": author["output_sha256"],
        },
        {
            "total_wall_ms": total_wall_ms,
            "total_tokens": total_tokens,
            "model_calls": 2,
            "restarts": 0,
        },
    )


def _require_transaction_proof(
    value: Any,
    *,
    outcome: str,
    case_id: str,
    law_report_sha256: str,
) -> dict[str, Any]:
    row = _mapping(value, f"candidate {case_id} transaction_proof")
    _exact_keys(
        row,
        {
            "status",
            "transaction_sha256",
            "package_sha256",
            "deterministic_law_failures",
            "deterministic_law_evidence_sha256",
            "post_confirm_semantic_calls",
            "sealed_readback_equal",
            "rollback_recovery_passed",
        },
        f"candidate {case_id} transaction_proof",
    )
    failures = _unique_strings(
        row.get("deterministic_law_failures"),
        f"candidate {case_id} deterministic failures",
    )
    if failures or row.get("deterministic_law_evidence_sha256") != law_report_sha256:
        raise ValueError(f"candidate {case_id} does not bind passing deterministic laws")
    if row.get("post_confirm_semantic_calls") != 0:
        raise ValueError(f"candidate {case_id} performed semantic work after confirmation")
    if outcome == "commit":
        if row.get("status") != "passed":
            raise ValueError(f"candidate {case_id} commit proof did not pass")
        _sha256(row.get("transaction_sha256"), f"candidate {case_id} transaction sha")
        _sha256(row.get("package_sha256"), f"candidate {case_id} package sha")
        if row.get("sealed_readback_equal") is not True or row.get("rollback_recovery_passed") is not True:
            raise ValueError(f"candidate {case_id} lacks transaction readback or recovery proof")
    elif not (
        row.get("status") == "not_applicable"
        and row.get("transaction_sha256") == ""
        and row.get("package_sha256") == ""
        and row.get("sealed_readback_equal") is False
        and row.get("rollback_recovery_passed") is False
    ):
        raise ValueError(f"candidate {case_id} clarification claims transaction proof")
    return row


def _require_review_package(
    value: Any,
    *,
    outcome: str,
    case_id: str,
    package_sha256: str,
) -> None:
    if outcome == "clarify":
        if value is not None:
            raise ValueError(f"candidate {case_id} clarification carries a review package")
        return
    package = _mapping(value, f"candidate {case_id} review package")
    if canonical_sha256(package) != package_sha256:
        raise ValueError(f"candidate {case_id} review package does not match its transaction proof")


def resource_ceiling_checks(
    per_case: Mapping[str, Mapping[str, int]],
    *,
    ceilings: Mapping[str, int],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Compute exact per-case/cohort resource gates from candidate-bound telemetry."""

    if not per_case:
        raise ValueError("resource telemetry has a required zero denominator")
    rows: list[dict[str, Any]] = []
    totals = {
        "total_wall_ms": 0,
        "total_tokens": 0,
        "model_calls": 0,
        "restarts": 0,
    }
    case_bindings = (
        ("total_wall_ms", "maximum_case_total_wall_ms"),
        ("total_tokens", "maximum_case_total_tokens"),
        ("model_calls", "maximum_case_model_calls"),
        ("restarts", "maximum_case_restarts"),
    )
    for case_id in sorted(per_case):
        telemetry = per_case[case_id]
        for metric, ceiling_name in case_bindings:
            observed = _nonnegative_integer(telemetry.get(metric), f"{case_id}.{metric}")
            totals[metric] += observed
            threshold = int(ceilings[ceiling_name])
            rows.append(
                {
                    "scope": "case",
                    "case_id": case_id,
                    "metric": metric,
                    "ceiling": ceiling_name,
                    "observed": observed,
                    "threshold": threshold,
                    "evidence_status": "proven",
                    "passed": observed <= threshold,
                }
            )
    cohort_bindings = (
        ("total_wall_ms", "maximum_cohort_total_wall_ms"),
        ("total_tokens", "maximum_cohort_total_tokens"),
        ("model_calls", "maximum_cohort_model_calls"),
        ("restarts", "maximum_cohort_restarts"),
    )
    for metric, ceiling_name in cohort_bindings:
        observed = totals[metric]
        threshold = int(ceilings[ceiling_name])
        rows.append(
            {
                "scope": "cohort",
                "metric": metric,
                "ceiling": ceiling_name,
                "observed": observed,
                "threshold": threshold,
                "evidence_status": "proven",
                "passed": observed <= threshold,
            }
        )
    return {
        "case_count": len(per_case),
        "cases": {case_id: dict(per_case[case_id]) for case_id in sorted(per_case)},
        "cohort_totals": totals,
    }, rows


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


def _mapped_rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise ValueError(f"{label} must be a JSON object array")
    return [dict(row) for row in value]


def _unique_index(
    rows: list[Mapping[str, Any]], key: str, label: str,
) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        value = _text(row.get(key), f"{label}.{key}")
        if value in indexed:
            raise ValueError(f"{label} contains duplicate {key}: {value}")
        indexed[value] = row
    return indexed


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} fields do not match the versioned contract")


def _text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be non-empty text")
    return text


def _strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a string array")
    rows = [_text(item, label) for item in value]
    if not rows or len(rows) != len(set(rows)):
        raise ValueError(f"{label} must be non-empty and unique")
    return rows


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    return float(value)


def _positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _nonnegative_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _unique_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a string array")
    rows = [_text(item, label) for item in value]
    if len(rows) != len(set(rows)):
        raise ValueError(f"{label} contains duplicates")
    return sorted(rows)


def _sha256(value: Any, label: str, *, length: int = 64) -> str:
    text = _text(value, label).casefold()
    if len(text) != length or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{label} must be a {length}-character lowercase hexadecimal digest")
    return text


__all__ = [
    "CANDIDATE_BUNDLE_VERSION",
    "EVALUATION_CONTRACT_VERSION",
    "FLOOR_NAMES",
    "FROZEN_AUXILIARY_REPORT_VERSIONS",
    "FROZEN_FLOORS",
    "FROZEN_RESOURCE_CEILINGS",
    "REPORT_VERSION",
    "REQUIRED_AUXILIARY_REPORTS",
    "RESOURCE_CEILING_NAMES",
    "require_auxiliary_reports",
    "require_candidate_bundle",
    "require_evaluation_contract",
    "resource_ceiling_checks",
]
