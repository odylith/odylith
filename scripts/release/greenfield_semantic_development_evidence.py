"""Runner-owned evidence contracts for two-stage Greenfield authoring."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path
import secrets
from typing import Any

from greenfield_semantic_host_execution_contract import (
    TOKEN_MEASUREMENT_BASES,
    positive_integer,
    require_host_runtime_receipt,
    require_token_usage,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_MANDATORY_CHALLENGES,
    semantic_intent_authoring_contract_payload,
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_PACKET_VERSION,
    semantic_evidence_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    SEMANTIC_REASONING_CAPABILITY_PROFILE,
    require_semantic_materiality_assessment,
    semantic_materiality_assessment_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    host_execution_profile,
    require_host_execution_profile,
    require_host_profiles,
)


DEVELOPMENT_EVIDENCE_PLAN_VERSION = "odylith.greenfield.development-evidence-plan.v3"
AUTHOR_SEGMENT_VERSION = "odylith.greenfield.development-author-segment.v3"
CRITIC_INPUT_VERSION = "odylith.greenfield.development-materiality-critic-input.v3"
AUTHOR_INPUT_VERSION = "odylith.greenfield.development-graph-author-input.v3"
MECHANISM_EVIDENCE_VERSION = "odylith.greenfield.semantic-development-mechanism-evidence.v3"
MECHANISM_ID = "prompt_only_materiality_gate_then_independent_graph_author"
DETERMINISTIC_LAW_REPORT_VERSION = "odylith.greenfield.deterministic-law-report.v3"
REQUIRED_DETERMINISTIC_LAW_IDS = (
    "no_post_confirm_semantic_or_model_work",
    "exact_sealed_byte_publication",
    "no_unsupported_accepted_facts_at_type_boundary",
    "idempotent_retry",
    "no_temporary_paths",
    "no_destructive_clipping",
    "no_partial_visible_generation_under_injected_failure",
)
ACCESS_FIELDS = (
    "prompt",
    "authoring_contract",
    "materiality_assessment",
    "annotations",
    "prior_candidates",
    "semantic_reviews",
    "validator_errors",
)


def canonical_sha256(value: Any) -> str:
    """Hash one JSON value using the release evidence encoding."""

    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def development_mechanism_contract() -> dict[str, Any]:
    """Return the frozen, mechanism-specific execution proof contract."""

    return {
        "version": MECHANISM_EVIDENCE_VERSION,
        "mechanism_id": MECHANISM_ID,
        "critic_input_version": CRITIC_INPUT_VERSION,
        "author_input_version": AUTHOR_INPUT_VERSION,
        "semantic_intent_packet_version": SEMANTIC_INTENT_PACKET_VERSION,
        "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
        "attempts_per_stage": 1,
        "model_calls_per_case": 2,
        "restarts_per_case": 0,
        "validation_error_repairs_per_stage": 0,
        "token_measurement_bases": list(TOKEN_MEASUREMENT_BASES),
        "mandatory_challenges": list(SEMANTIC_INTENT_MANDATORY_CHALLENGES),
        "critic_access": _expected_access("critic"),
        "author_access": _expected_access("author"),
    }


def development_mechanism_contract_sha256() -> str:
    return canonical_sha256(development_mechanism_contract())


def prepare_development_evidence_plan(
    *,
    corpus_path: Path,
    host_profiles: Sequence[str],
    output_path: Path,
) -> dict[str, Any]:
    """Create exclusive runner assignments without exposing corpus annotations."""

    corpus_file = safe_json_file(corpus_path, "development corpus")
    corpus = json_mapping(corpus_file, "development corpus")
    cases = _case_index(corpus)
    hosts = require_host_profiles(host_profiles)
    issue_nonce = secrets.token_hex
    cohort_nonce = _issued_nonce(issue_nonce, "cohort")
    rows: list[dict[str, Any]] = []
    issued_nonces = {cohort_nonce}
    issued_run_ids: set[str] = set()
    for position, case_id in enumerate(sorted(cases)):
        host = hosts[position % len(hosts)]
        prompt = text(cases[case_id].get("prompt"), f"{case_id} prompt", maximum=500_000)
        case_nonce = _fresh_nonce(issue_nonce, issued_nonces, f"{case_id} case")
        critic = _run_assignment(
            stage="critic",
            case_nonce=case_nonce,
            host_profile=host,
            issue_nonce=issue_nonce,
            issued_nonces=issued_nonces,
            issued_run_ids=issued_run_ids,
        )
        author = _run_assignment(
            stage="author",
            case_nonce=case_nonce,
            host_profile=host,
            issue_nonce=issue_nonce,
            issued_nonces=issued_nonces,
            issued_run_ids=issued_run_ids,
        )
        row = {
            "case_id": case_id,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "case_nonce": case_nonce,
            "critic_assignment": critic,
            "author_assignment": author,
        }
        row["assignment_sha256"] = canonical_sha256(row)
        rows.append(row)
    plan = {
        "version": DEVELOPMENT_EVIDENCE_PLAN_VERSION,
        "corpus_sha256": _sha256_file(corpus_file),
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
        "mechanism_contract_sha256": development_mechanism_contract_sha256(),
        "cohort_nonce": cohort_nonce,
        "required_host_profiles": hosts,
        "host_execution_profiles": [host_execution_profile(host) for host in hosts],
        "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
        "cases": rows,
    }
    plan["cohort_assignment_sha256"] = _cohort_assignment_sha256(plan)
    exclusive_json(Path(output_path).expanduser().resolve(), plan)
    return plan


def require_development_evidence_plan(
    value: Any,
    *,
    corpus: Mapping[str, Any],
    corpus_sha256: str,
) -> dict[str, Any]:
    """Validate all runner-owned assignments and their nested hashes."""

    plan = mapping(value, "development evidence plan")
    exact_keys(
        plan,
        {
            "version", "corpus_sha256", "authoring_contract_sha256",
            "mechanism_contract_sha256", "cohort_nonce", "cohort_assignment_sha256",
            "required_host_profiles", "host_execution_profiles", "capability_profile", "cases",
        },
        "development evidence plan",
    )
    if plan.get("version") != DEVELOPMENT_EVIDENCE_PLAN_VERSION:
        raise RuntimeError("development evidence plan uses an unsupported version")
    if plan.get("corpus_sha256") != corpus_sha256:
        raise RuntimeError("development evidence plan does not match the development corpus")
    if plan.get("authoring_contract_sha256") != semantic_intent_authoring_contract_sha256():
        raise RuntimeError("development evidence plan uses a stale authoring contract")
    if plan.get("mechanism_contract_sha256") != development_mechanism_contract_sha256():
        raise RuntimeError("development evidence plan uses a stale mechanism contract")
    hosts = require_host_profiles(plan.get("required_host_profiles"))
    expected_execution_profiles = [host_execution_profile(host) for host in hosts]
    if plan.get("host_execution_profiles") != expected_execution_profiles:
        raise RuntimeError("development evidence plan changes a pinned host execution profile")
    if plan.get("capability_profile") != SEMANTIC_REASONING_CAPABILITY_PROFILE:
        raise RuntimeError("development evidence plan uses an unsupported capability profile")
    cohort_nonce = text(plan.get("cohort_nonce"), "cohort nonce", maximum=200)
    cases = _case_index(corpus)
    assignments = unique_index(
        mapped_rows(plan.get("cases"), "development evidence assignments"),
        "case_id",
        "development evidence assignments",
    )
    if set(assignments) != set(cases):
        raise RuntimeError("development evidence plan must assign every corpus case exactly once")
    nonces = {cohort_nonce}
    run_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for case_id in sorted(assignments):
        raw = mapping(assignments[case_id], f"{case_id} assignment")
        exact_keys(
            raw,
            {
                "case_id", "prompt_sha256", "case_nonce", "assignment_sha256",
                "critic_assignment", "author_assignment",
            },
            f"{case_id} assignment",
        )
        prompt = text(cases[case_id].get("prompt"), f"{case_id} prompt", maximum=500_000)
        if raw.get("prompt_sha256") != hashlib.sha256(prompt.encode("utf-8")).hexdigest():
            raise RuntimeError(f"{case_id} assignment does not match its source prompt")
        case_nonce = _unique_nonce(raw.get("case_nonce"), nonces, f"{case_id} case nonce")
        host = text(
            mapping(raw.get("critic_assignment"), "critic assignment").get("host_profile"),
            f"{case_id} host profile",
            maximum=100,
        )
        expected_host = hosts[sorted(assignments).index(case_id) % len(hosts)]
        if host != expected_host:
            raise RuntimeError(f"{case_id} violates the runner host assignment")
        critic = _require_run_assignment(
            raw.get("critic_assignment"), stage="critic", case_nonce=case_nonce,
            host_profile=host, nonces=nonces, run_ids=run_ids,
        )
        author = _require_run_assignment(
            raw.get("author_assignment"), stage="author", case_nonce=case_nonce,
            host_profile=host, nonces=nonces, run_ids=run_ids,
        )
        row = {
            "case_id": case_id,
            "prompt_sha256": raw["prompt_sha256"],
            "case_nonce": case_nonce,
            "critic_assignment": critic,
            "author_assignment": author,
        }
        if raw.get("assignment_sha256") != canonical_sha256(row):
            raise RuntimeError(f"{case_id} assignment hash mismatch")
        row["assignment_sha256"] = raw["assignment_sha256"]
        normalized.append(row)
    result = {
        "version": DEVELOPMENT_EVIDENCE_PLAN_VERSION,
        "corpus_sha256": corpus_sha256,
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
        "mechanism_contract_sha256": development_mechanism_contract_sha256(),
        "cohort_nonce": cohort_nonce,
        "required_host_profiles": hosts,
        "host_execution_profiles": expected_execution_profiles,
        "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
        "cases": normalized,
    }
    expected_cohort_sha = _cohort_assignment_sha256(result)
    if plan.get("cohort_assignment_sha256") != expected_cohort_sha:
        raise RuntimeError("development evidence cohort assignment hash mismatch")
    result["cohort_assignment_sha256"] = expected_cohort_sha
    return result


def build_materiality_critic_input(
    *, corpus_path: Path, evidence_plan_path: Path, case_id: str,
) -> dict[str, Any]:
    """Build the critic's exact prompt-and-contract-only input."""

    corpus, plan, _, _ = _validated_context(corpus_path, evidence_plan_path)
    return materiality_critic_input_for_case(corpus=corpus, plan=plan, case_id=case_id)


def materiality_critic_input_for_case(
    *, corpus: Mapping[str, Any], plan: Mapping[str, Any], case_id: str,
) -> dict[str, Any]:
    """Build a critic input from an already validated corpus and plan."""

    cases = _case_index(corpus)
    assignments = unique_index(plan["cases"], "case_id", "assignments")
    assignment = _selected_assignment(assignments, case_id)
    prompt = text(cases[case_id].get("prompt"), f"{case_id} prompt", maximum=500_000)
    return _phase_input(
        version=CRITIC_INPUT_VERSION,
        assignment=assignment,
        run_assignment=assignment["critic_assignment"],
        prompt=prompt,
        plan=plan,
        materiality_assessment=None,
    )


def build_semantic_graph_author_input(
    *,
    corpus_path: Path,
    evidence_plan_path: Path,
    case_id: str,
    materiality_assessment: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the author input after deterministic materiality validation."""

    corpus, plan, _, _ = _validated_context(corpus_path, evidence_plan_path)
    return semantic_graph_author_input_for_case(
        corpus=corpus,
        plan=plan,
        case_id=case_id,
        materiality_assessment=materiality_assessment,
    )


def semantic_graph_author_input_for_case(
    *,
    corpus: Mapping[str, Any],
    plan: Mapping[str, Any],
    case_id: str,
    materiality_assessment: Mapping[str, Any],
) -> dict[str, Any]:
    """Build an author input from an already validated corpus and plan."""

    cases = _case_index(corpus)
    assignments = unique_index(plan["cases"], "case_id", "assignments")
    assignment = _selected_assignment(assignments, case_id)
    prompt = text(cases[case_id].get("prompt"), f"{case_id} prompt", maximum=500_000)
    evidence_sources = {"operator_prompt": prompt, "operator_edit": ""}
    assessment = require_semantic_materiality_assessment(
        materiality_assessment,
        evidence_sources=evidence_sources,
        evidence_sha256=semantic_evidence_sha256(evidence_sources),
        authoring_contract_sha256=semantic_intent_authoring_contract_sha256(),
    )
    return _phase_input(
        version=AUTHOR_INPUT_VERSION,
        assignment=assignment,
        run_assignment=assignment["author_assignment"],
        prompt=prompt,
        plan=plan,
        materiality_assessment=assessment,
    )


def run_evidence_sha256(value: Mapping[str, Any]) -> str:
    """Hash one frozen run receipt without its self-binding field."""

    payload = dict(value)
    payload.pop("run_sha256", None)
    return canonical_sha256(payload)


def require_run_evidence(
    value: Any,
    *,
    stage: str,
    assignment: Mapping[str, Any],
    expected_input_sha256: str,
    expected_output_sha256: str,
    materiality_assessment_sha256: str = "",
) -> dict[str, Any]:
    """Validate a complete run receipt against its runner-owned assignment."""

    if stage not in {"critic", "author"}:
        raise RuntimeError("development evidence stage must be critic or author")
    row = mapping(value, f"{stage} run evidence")
    expected_fields = {
        "run_nonce", "run_id", "run_assignment_sha256", "run_sha256",
        "host_profile", "capability_profile", "execution_profile", "host_runtime",
        "independent_context", "attempt_count",
        "validation_error_repair_count", "input_sha256", "output_sha256",
        "access_receipt", "wall_ms", "token_usage",
    }
    if stage == "author":
        expected_fields.update({"materiality_assessment_sha256", "self_challenge"})
    exact_keys(row, expected_fields, f"{stage} run evidence")
    for name in (
        "run_nonce", "run_id", "run_assignment_sha256", "host_profile", "capability_profile",
    ):
        if row.get(name) != assignment.get(name):
            raise RuntimeError(f"{stage} run evidence does not match its assignment: {name}")
    if (
        row.get("independent_context") is not True
        or row.get("attempt_count") != 1
        or row.get("validation_error_repair_count") != 0
    ):
        raise RuntimeError(f"{stage} run evidence violates isolation, attempt, or repair limits")
    require_sha256(row.get("input_sha256"), f"{stage} input hash")
    require_sha256(row.get("output_sha256"), f"{stage} output hash")
    if row.get("input_sha256") != expected_input_sha256:
        raise RuntimeError(f"{stage} run input hash mismatch")
    if row.get("output_sha256") != expected_output_sha256:
        raise RuntimeError(f"{stage} run output hash mismatch")
    access = mapping(row.get("access_receipt"), f"{stage} access receipt")
    exact_keys(access, set(ACCESS_FIELDS), f"{stage} access receipt")
    if access != expected_access_receipt(stage):
        raise RuntimeError(f"{stage} run used forbidden or missing evidence access")
    execution_profile = require_host_execution_profile(
        row.get("execution_profile"), host_profile=assignment["host_profile"]
    )
    if execution_profile != assignment.get("execution_profile"):
        raise RuntimeError(f"{stage} run evidence changes its pinned execution profile")
    host_runtime = require_host_runtime_receipt(
        row.get("host_runtime"), host_profile=assignment["host_profile"]
    )
    wall_ms = positive_integer(row.get("wall_ms"), f"{stage} wall_ms")
    token_usage = require_token_usage(row.get("token_usage"), stage=stage)
    normalized = {
        "run_nonce": assignment["run_nonce"],
        "run_id": assignment["run_id"],
        "run_assignment_sha256": assignment["run_assignment_sha256"],
        "host_profile": assignment["host_profile"],
        "capability_profile": assignment["capability_profile"],
        "execution_profile": execution_profile,
        "host_runtime": host_runtime,
        "independent_context": True,
        "attempt_count": 1,
        "validation_error_repair_count": 0,
        "input_sha256": expected_input_sha256,
        "output_sha256": expected_output_sha256,
        "access_receipt": access,
        "wall_ms": wall_ms,
        "token_usage": token_usage,
    }
    if stage == "author":
        require_sha256(materiality_assessment_sha256, "materiality assessment hash")
        if row.get("materiality_assessment_sha256") != materiality_assessment_sha256:
            raise RuntimeError("author run does not bind the validated materiality assessment")
        challenges = mapped_rows(row.get("self_challenge"), "author self challenge")
        expected_challenges = [
            {"challenge": name, "status": "passed"}
            for name in SEMANTIC_INTENT_MANDATORY_CHALLENGES
        ]
        if challenges != expected_challenges:
            raise RuntimeError("author run lacks exact passing mandatory self-challenge coverage")
        normalized["materiality_assessment_sha256"] = materiality_assessment_sha256
        normalized["self_challenge"] = expected_challenges
    expected_run_sha = run_evidence_sha256(normalized)
    if row.get("run_sha256") != expected_run_sha:
        raise RuntimeError(f"{stage} run evidence hash mismatch")
    normalized["run_sha256"] = expected_run_sha
    return normalized


def _phase_input(
    *,
    version: str,
    assignment: Mapping[str, Any],
    run_assignment: Mapping[str, Any],
    prompt: str,
    plan: Mapping[str, Any],
    materiality_assessment: Mapping[str, Any] | None,
) -> dict[str, Any]:
    evidence_sources = {"operator_prompt": prompt, "operator_edit": ""}
    value = {
        "version": version,
        "cohort_nonce": plan["cohort_nonce"],
        "case_id": assignment["case_id"],
        "case_nonce": assignment["case_nonce"],
        "assignment_sha256": assignment["assignment_sha256"],
        "run_nonce": run_assignment["run_nonce"],
        "run_id": run_assignment["run_id"],
        "run_assignment_sha256": run_assignment["run_assignment_sha256"],
        "host_profile": run_assignment["host_profile"],
        "capability_profile": run_assignment["capability_profile"],
        "execution_profile": run_assignment["execution_profile"],
        "independent_context": True,
        "attempt_limit": 1,
        "evidence": evidence_sources,
        "evidence_sha256": semantic_evidence_sha256(evidence_sources),
        "authoring_contract": semantic_intent_authoring_contract_payload(),
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
    }
    if materiality_assessment is not None:
        value["materiality_assessment"] = dict(materiality_assessment)
        value["materiality_assessment_sha256"] = semantic_materiality_assessment_sha256(
            materiality_assessment
        )
    return value


def _validated_context(
    corpus_path: Path, evidence_plan_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    corpus_file = safe_json_file(corpus_path, "development corpus")
    corpus = json_mapping(corpus_file, "development corpus")
    plan = require_development_evidence_plan(
        json_mapping(safe_json_file(evidence_plan_path, "development evidence plan"), "development evidence plan"),
        corpus=corpus,
        corpus_sha256=_sha256_file(corpus_file),
    )
    return corpus, plan, _case_index(corpus), unique_index(plan["cases"], "case_id", "assignments")


def _selected_assignment(
    assignments: Mapping[str, Mapping[str, Any]], case_id: str,
) -> Mapping[str, Any]:
    selected = text(case_id, "case id", maximum=200)
    if selected not in assignments:
        raise RuntimeError(f"development evidence plan does not assign case: {selected}")
    return assignments[selected]


def _run_assignment(
    *, stage: str, case_nonce: str, host_profile: str,
    issue_nonce: Callable[[], str], issued_nonces: set[str], issued_run_ids: set[str],
) -> dict[str, Any]:
    run_nonce = _fresh_nonce(issue_nonce, issued_nonces, f"{stage} run")
    run_id = f"{stage}-{run_nonce}"
    if run_id in issued_run_ids:
        raise RuntimeError("runner generated a duplicate run id")
    issued_run_ids.add(run_id)
    row = {
        "stage": stage,
        "run_nonce": run_nonce,
        "run_id": run_id,
        "host_profile": host_profile,
        "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
        "execution_profile": host_execution_profile(host_profile),
        "independent_context": True,
        "attempt_limit": 1,
        "case_nonce": case_nonce,
    }
    row["run_assignment_sha256"] = canonical_sha256(row)
    return row


def _require_run_assignment(
    value: Any, *, stage: str, case_nonce: str, host_profile: str,
    nonces: set[str], run_ids: set[str],
) -> dict[str, Any]:
    raw = mapping(value, f"{stage} run assignment")
    exact_keys(
        raw,
        {
            "stage", "run_nonce", "run_id", "run_assignment_sha256", "host_profile",
            "capability_profile", "execution_profile", "independent_context", "attempt_limit", "case_nonce",
        },
        f"{stage} run assignment",
    )
    if raw.get("stage") != stage or raw.get("case_nonce") != case_nonce:
        raise RuntimeError(f"{stage} run assignment is bound to the wrong case")
    run_nonce = _unique_nonce(raw.get("run_nonce"), nonces, f"{stage} run nonce")
    run_id = text(raw.get("run_id"), f"{stage} run id", maximum=200)
    if run_id in run_ids:
        raise RuntimeError("development evidence plan reuses a run id")
    run_ids.add(run_id)
    if (
        raw.get("host_profile") != host_profile
        or raw.get("capability_profile") != SEMANTIC_REASONING_CAPABILITY_PROFILE
        or raw.get("execution_profile") != host_execution_profile(host_profile)
        or raw.get("independent_context") is not True
        or raw.get("attempt_limit") != 1
    ):
        raise RuntimeError(f"{stage} run assignment violates the frozen execution profile")
    row = {
        "stage": stage,
        "run_nonce": run_nonce,
        "run_id": run_id,
        "host_profile": host_profile,
        "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
        "execution_profile": host_execution_profile(host_profile),
        "independent_context": True,
        "attempt_limit": 1,
        "case_nonce": case_nonce,
    }
    if raw.get("run_assignment_sha256") != canonical_sha256(row):
        raise RuntimeError(f"{stage} run assignment hash mismatch")
    row["run_assignment_sha256"] = raw["run_assignment_sha256"]
    return row


def _cohort_assignment_sha256(plan: Mapping[str, Any]) -> str:
    return canonical_sha256(
        {
            "version": plan["version"],
            "corpus_sha256": plan["corpus_sha256"],
            "authoring_contract_sha256": plan["authoring_contract_sha256"],
            "mechanism_contract_sha256": plan["mechanism_contract_sha256"],
            "cohort_nonce": plan["cohort_nonce"],
            "required_host_profiles": plan["required_host_profiles"],
            "host_execution_profiles": plan["host_execution_profiles"],
            "capability_profile": plan["capability_profile"],
            "assignment_sha256s": [row["assignment_sha256"] for row in plan["cases"]],
        }
    )


def _expected_access(stage: str) -> dict[str, bool]:
    return {
        "prompt": True,
        "authoring_contract": True,
        "materiality_assessment": stage == "author",
        "annotations": False,
        "prior_candidates": False,
        "semantic_reviews": False,
        "validator_errors": False,
    }


def expected_access_receipt(stage: str) -> dict[str, bool]:
    if stage not in {"critic", "author"}:
        raise RuntimeError("development evidence stage must be critic or author")
    return _expected_access(stage)


def _case_index(corpus: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return unique_index(mapped_rows(corpus.get("cases"), "development corpus cases"), "case_id", "development corpus cases")


def _issued_nonce(issue_nonce: Callable[[], str], label: str) -> str:
    return text(issue_nonce(), f"runner-issued {label} nonce", maximum=200)


def _fresh_nonce(issue_nonce: Callable[[], str], issued: set[str], label: str) -> str:
    value = _issued_nonce(issue_nonce, label)
    if value in issued:
        raise RuntimeError("runner generated a reused development evidence nonce")
    issued.add(value)
    return value


def _unique_nonce(value: Any, seen: set[str], label: str) -> str:
    nonce = text(value, label, maximum=200)
    if nonce in seen:
        raise RuntimeError("development evidence plan reuses a nonce")
    seen.add(nonce)
    return nonce


def safe_json_file(path: Path | str, label: str) -> Path:
    expanded = Path(path).expanduser()
    if expanded.is_symlink():
        raise RuntimeError(f"{label} is missing or unsafe")
    candidate = expanded.resolve()
    if not candidate.is_file():
        raise RuntimeError(f"{label} is missing or unsafe")
    return candidate


def json_mapping(path: Path, label: str) -> dict[str, Any]:
    try:
        return mapping(json.loads(path.read_text(encoding="utf-8")), label)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{label} is unreadable: {error}") from error


def exclusive_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise RuntimeError(f"development evidence output already exists: {path}") from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(value), sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a JSON object")
    return dict(value)


def mapped_rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise RuntimeError(f"{label} must be a JSON object array")
    return [dict(row) for row in value]


def unique_index(
    rows: Sequence[Mapping[str, Any]], key: str, label: str,
) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        value = text(row.get(key), f"{label}.{key}", maximum=200)
        if value in indexed:
            raise RuntimeError(f"{label} contains duplicate {key}: {value}")
        indexed[value] = row
    return indexed


def exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise RuntimeError(f"{label} fields do not match the versioned contract")


def text(value: Any, label: str, *, maximum: int) -> str:
    result = str(value or "").strip()
    if not result or len(result) > maximum:
        raise RuntimeError(f"{label} must be bounded non-empty text")
    return result


def require_sha256(value: Any, label: str, *, length: int = 64) -> str:
    result = text(value, label, maximum=length)
    if len(result) != length or any(character not in "0123456789abcdef" for character in result):
        raise RuntimeError(f"{label} must be a lowercase SHA-256 digest")
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "ACCESS_FIELDS",
    "AUTHOR_INPUT_VERSION",
    "AUTHOR_SEGMENT_VERSION",
    "CRITIC_INPUT_VERSION",
    "DETERMINISTIC_LAW_REPORT_VERSION",
    "DEVELOPMENT_EVIDENCE_PLAN_VERSION",
    "MECHANISM_EVIDENCE_VERSION",
    "MECHANISM_ID",
    "REQUIRED_DETERMINISTIC_LAW_IDS",
    "TOKEN_MEASUREMENT_BASES",
    "build_materiality_critic_input",
    "build_semantic_graph_author_input",
    "canonical_sha256",
    "development_mechanism_contract",
    "development_mechanism_contract_sha256",
    "expected_access_receipt",
    "exclusive_json",
    "json_mapping",
    "mapped_rows",
    "mapping",
    "prepare_development_evidence_plan",
    "materiality_critic_input_for_case",
    "require_development_evidence_plan",
    "require_run_evidence",
    "require_sha256",
    "run_evidence_sha256",
    "semantic_graph_author_input_for_case",
    "unique_index",
]
