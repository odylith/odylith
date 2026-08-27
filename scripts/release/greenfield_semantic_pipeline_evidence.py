"""Release-grade validation for active Greenfield pipeline receipts."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import secrets
from typing import Any

from greenfield_semantic_release_support import (
    canonical_sha256,
    greenfield_runtime_source_fingerprint,
)
from greenfield_semantic_pipeline_receipts import (
    BOUNDED_PIPELINE_VERSION,
    PIPELINE_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    require_semantic_execution_evidence,
    semantic_execution_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    product_create_transaction_from_dict,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    SEMANTIC_REASONING_CAPABILITY_PROFILE,
    require_host_profiles,
    standard_author_profile,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_source_meaning_author_run,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning import (
    semantic_source_meaning_sha256,
)


ACTIVE_EVIDENCE_PLAN_VERSION = "odylith.greenfield.active-evidence-plan.v6"


def prepare_active_evidence_plan(
    *,
    corpus_path: Path,
    host_profiles: list[str],
    output_path: Path,
) -> dict[str, Any]:
    """Freeze prompt-only case/host assignments before any semantic run."""

    corpus_file = corpus_path.expanduser().resolve()
    corpus = _mapping(
        json.loads(corpus_file.read_text(encoding="utf-8")), "development corpus"
    )
    cases = _case_index(corpus)
    hosts = require_host_profiles(host_profiles)
    cohort_nonce = secrets.token_hex(16)
    assignments: list[dict[str, Any]] = []
    issued_nonces: set[str] = {cohort_nonce}
    for index, case_id in enumerate(sorted(cases)):
        nonce = secrets.token_hex(16)
        while nonce in issued_nonces:
            nonce = secrets.token_hex(16)
        issued_nonces.add(nonce)
        prompt = _text(cases[case_id].get("prompt"), f"{case_id} prompt")
        row = {
            "case_id": case_id,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "case_nonce": nonce,
            "host_profile": hosts[index % len(hosts)],
        }
        row["assignment_sha256"] = canonical_sha256(row)
        assignments.append(row)
    plan = {
        "version": ACTIVE_EVIDENCE_PLAN_VERSION,
        "corpus_sha256": hashlib.sha256(corpus_file.read_bytes()).hexdigest(),
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
        "mechanism_contract_sha256": semantic_execution_contract_sha256(),
        "implementation_fingerprint_sha256": greenfield_runtime_source_fingerprint(),
        "cohort_nonce": cohort_nonce,
        "required_host_profiles": hosts,
        "cases": assignments,
    }
    plan["cohort_assignment_sha256"] = canonical_sha256(
        {"cohort_nonce": cohort_nonce, "cases": assignments}
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(plan, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    return plan


def require_active_evidence_plan(
    value: Any,
    *,
    corpus: Mapping[str, Any],
    corpus_sha256: str,
) -> dict[str, Any]:
    """Validate frozen case identity without reading corpus annotations."""

    plan = _mapping(value, "active evidence plan")
    _exact_keys(
        plan,
        {
            "version",
            "corpus_sha256",
            "authoring_contract_sha256",
            "mechanism_contract_sha256",
            "implementation_fingerprint_sha256",
            "cohort_nonce",
            "required_host_profiles",
            "cases",
            "cohort_assignment_sha256",
        },
        "active evidence plan",
    )
    if plan.get("version") != ACTIVE_EVIDENCE_PLAN_VERSION:
        raise ValueError("active evidence plan version is unsupported")
    expected_contracts = {
        "corpus_sha256": _sha256(corpus_sha256, "corpus sha256"),
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
        "mechanism_contract_sha256": semantic_execution_contract_sha256(),
        "implementation_fingerprint_sha256": greenfield_runtime_source_fingerprint(),
    }
    if any(plan.get(name) != expected for name, expected in expected_contracts.items()):
        raise ValueError("active evidence plan changes a frozen contract")
    cohort_nonce = _text(plan.get("cohort_nonce"), "cohort nonce")
    hosts = require_host_profiles(plan.get("required_host_profiles"))
    cases = _case_index(corpus)
    raw_assignments = plan.get("cases")
    if not isinstance(raw_assignments, list):
        raise ValueError("active evidence plan cases must be a JSON array")
    if len(raw_assignments) != len(cases):
        raise ValueError("active evidence plan must assign every case exactly once")
    assignments: list[dict[str, Any]] = []
    seen_cases: set[str] = set()
    seen_nonces: set[str] = {cohort_nonce}
    for index, raw in enumerate(raw_assignments):
        row = _mapping(raw, "active evidence assignment")
        _exact_keys(
            row,
            {
                "case_id",
                "prompt_sha256",
                "case_nonce",
                "host_profile",
                "assignment_sha256",
            },
            "active evidence assignment",
        )
        case_id = _text(row.get("case_id"), "assignment case id")
        nonce = _text(row.get("case_nonce"), "assignment case nonce")
        if case_id not in cases or case_id in seen_cases or nonce in seen_nonces:
            raise ValueError("active evidence assignments are duplicated or unknown")
        seen_cases.add(case_id)
        seen_nonces.add(nonce)
        prompt = _text(cases[case_id].get("prompt"), f"{case_id} prompt")
        expected = {
            "case_id": case_id,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "case_nonce": nonce,
            "host_profile": row.get("host_profile"),
        }
        if (
            case_id != sorted(cases)[index]
            or expected["host_profile"] != hosts[index % len(hosts)]
            or row.get("assignment_sha256") != canonical_sha256(expected)
        ):
            raise ValueError("active evidence assignment changes its frozen binding")
        assignments.append({**expected, "assignment_sha256": row["assignment_sha256"]})
    if seen_cases != set(cases) or {row["host_profile"] for row in assignments} != set(hosts):
        raise ValueError("active evidence plan does not cover every case and host")
    if plan.get("cohort_assignment_sha256") != canonical_sha256(
        {"cohort_nonce": cohort_nonce, "cases": assignments}
    ):
        raise ValueError("active evidence plan cohort hash mismatch")
    return {**plan, "required_host_profiles": hosts, "cases": assignments}


def require_successful_pipeline_evidence(
    value: Any,
    *,
    case_id: str,
    prompt: str,
    semantic_artifact: Mapping[str, Any],
    assignment: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind one useful author receipt to one unchanged typed packet."""

    outer = _mapping(value, f"candidate {case_id} pipeline evidence")
    attempt, execution = _attempt_and_execution(outer, case_id=case_id)
    _exact_keys(
        attempt,
        {
            "version", "case_id", "tier", "status", "outcome", "wall_ms",
            "budget", "source_meaning_author", "packet", "transaction",
            "failed_stage", "failure", "model_call_count", "restart_count",
            "total_tokens", "mechanism_execution", "evidence_assignment",
        },
        f"candidate {case_id} pipeline attempt",
    )
    if attempt.get("version") != PIPELINE_VERSION or attempt.get("case_id") != case_id:
        raise ValueError(f"candidate {case_id} pipeline attempt identity is invalid")
    if assignment is not None and attempt.get("evidence_assignment") != dict(assignment):
        raise ValueError(f"candidate {case_id} pipeline changes its frozen assignment")
    if attempt.get("status") != "completed" or attempt.get("outcome") not in {
        "commit", "clarify",
    }:
        raise ValueError(f"candidate {case_id} pipeline did not reach a useful outcome")
    if attempt.get("failed_stage") or attempt.get("failure"):
        raise ValueError(f"candidate {case_id} successful pipeline carries a failure")
    if (
        attempt.get("model_call_count") != 1
        or execution["model_call_count"] != 1
        or attempt.get("restart_count") != 0
        or execution["restart_count"] != 0
        or execution["wall_ms"] != outer.get("wall_ms")
    ):
        raise ValueError(f"candidate {case_id} pipeline telemetry changes the mechanism")

    host_profile = str(execution["host_profile"])
    author = _mapping(
        attempt.get("source_meaning_author"), f"candidate {case_id} author"
    )
    authored = _source_meaning_author(
        author,
        case_id=case_id,
        host_profile=host_profile,
        profile=standard_author_profile(host_profile, 0),
    )
    graph = authored["graph"]
    graph_sha = authored["graph_sha256"]
    author_run = authored["author_run"]

    packet = _mapping(attempt.get("packet"), f"candidate {case_id} pipeline packet")
    if packet != dict(semantic_artifact):
        raise ValueError(f"candidate {case_id} pipeline does not bind its semantic packet")
    if (
        packet.get("source_meaning_graph") != graph
        or packet.get("source_meaning_sha256") != graph_sha
        or packet.get("author_run") != author_run
    ):
        raise ValueError(f"candidate {case_id} packet changes author bytes")
    outcome = str(attempt["outcome"])
    transaction = attempt.get("transaction")
    if outcome == "commit":
        if (
            not isinstance(transaction, Mapping)
            or transaction.get("verified") is not True
            or transaction.get("quality_status") != "passed"
        ):
            raise ValueError(f"candidate {case_id} commit lacks a verified transaction")
        transaction_sha256 = _sha256(
            transaction.get("transaction_hash"),
            f"candidate {case_id} pipeline transaction hash",
        )
        transaction_payload = _mapping(
            transaction.get("transaction_payload"),
            f"candidate {case_id} transaction payload",
        )
        try:
            bound_transaction = product_create_transaction_from_dict(transaction_payload)
        except ValueError as error:
            raise ValueError(
                f"candidate {case_id} pipeline transaction payload is invalid: {error}"
            ) from error
        if bound_transaction.transaction_hash != transaction_sha256:
            raise ValueError(f"candidate {case_id} pipeline transaction summary drifts")
        review_package = _mapping(
            transaction.get("review_package"),
            f"candidate {case_id} pipeline review package",
        )
        if review_package != dict(bound_transaction.prewrite_package.proposal):
            raise ValueError(
                f"candidate {case_id} pipeline review package changes sealed bytes"
            )
        review_package_sha256 = canonical_sha256(review_package)
    elif transaction is not None:
        raise ValueError(f"candidate {case_id} clarification carries a transaction")
    else:
        transaction_sha256 = ""
        review_package = None
        review_package_sha256 = ""
    return dict(outer), {
        "mechanism_evidence_sha256": canonical_sha256(outer),
        "model_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
        "host_profile": host_profile,
        "implementation_fingerprint_sha256": execution[
            "implementation_fingerprint_sha256"
        ],
        "author_run_id": str(author_run["run_id"]),
        "execution_tier": str(execution["tier"]),
        "total_wall_ms": int(execution["wall_ms"]),
        "total_tokens": _integer(outer.get("total_tokens"), "total tokens"),
        "model_calls": 1,
        "restarts": 0,
        "transaction_sha256": transaction_sha256,
        "review_package": review_package,
        "review_package_sha256": review_package_sha256,
    }


def _attempt_and_execution(
    value: Mapping[str, Any], *, case_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    version = value.get("version")
    if version == PIPELINE_VERSION:
        execution = require_semantic_execution_evidence(
            value.get("mechanism_execution")
        )
        _require_current_implementation(execution, case_id=case_id)
        if execution["tier"] != "standard":
            raise ValueError(f"candidate {case_id} standard receipt changes tier")
        return dict(value), execution
    if version != BOUNDED_PIPELINE_VERSION:
        raise ValueError(f"candidate {case_id} pipeline evidence version is unsupported")
    _exact_keys(
        value,
        {
            "version",
            "case_id",
            "tier",
            "status",
            "outcome",
            "wall_ms",
            "attempt",
            "model_call_count",
            "restart_count",
            "total_tokens",
            "automatic_deep_tier",
            "mechanism_execution",
        },
        f"candidate {case_id} rescue evidence",
    )
    execution = require_semantic_execution_evidence(value.get("mechanism_execution"))
    attempt = _mapping(value.get("attempt"), f"candidate {case_id} rescue attempt")
    attempt_execution = require_semantic_execution_evidence(
        attempt.get("mechanism_execution")
    )
    _require_current_implementation(execution, case_id=case_id)
    _require_current_implementation(attempt_execution, case_id=case_id)
    if (
        value.get("case_id") != case_id
        or value.get("tier") != "rescue"
        or execution["tier"] != "rescue"
        or attempt_execution["tier"] != "rescue"
        or execution["prior_standard_failure_sha256"]
        != attempt_execution["prior_standard_failure_sha256"]
        or value.get("status") != attempt.get("status")
        or value.get("outcome") != attempt.get("outcome")
        or value.get("model_call_count") != attempt.get("model_call_count")
        or value.get("restart_count") != 0
        or value.get("automatic_deep_tier") is not False
    ):
        raise ValueError(f"candidate {case_id} rescue wrapper changes its attempt")
    return attempt, execution


def _require_current_implementation(
    execution: Mapping[str, Any], *, case_id: str
) -> None:
    if (
        execution.get("implementation_fingerprint_sha256")
        != greenfield_runtime_source_fingerprint()
    ):
        raise ValueError(f"candidate {case_id} was produced by different source bytes")


def _source_meaning_author(
    value: Any,
    *,
    case_id: str,
    host_profile: str,
    profile: Mapping[str, str],
) -> dict[str, Any]:
    row = _mapping(value, f"candidate {case_id} source-meaning author")
    _exact_keys(
        row,
        {
            "stage", "case_id", "host_profile", "model", "reasoning_effort", "status",
            "failure_kind", "failure", "graph", "graph_sha256", "author_run",
            "usage", "wall_ms", "model_call_count",
        },
        f"candidate {case_id} source-meaning author",
    )
    if (
        row.get("stage") != "source_meaning_author"
        or row.get("case_id") != case_id
        or row.get("model_call_count") != 1
        or row.get("host_profile") != host_profile
        or row.get("model") != profile["model"]
        or row.get("reasoning_effort") != profile["reasoning_effort"]
    ):
        raise ValueError(f"candidate {case_id} author changes its topology or profile")
    _integer(row.get("wall_ms"), "author attempt wall_ms")
    if row.get("status") != "completed" or row.get("failure_kind") or row.get("failure"):
        raise ValueError(f"candidate {case_id} successful author carries failure")
    graph = _mapping(row.get("graph"), "source-meaning graph")
    graph_sha = _sha256(row.get("graph_sha256"), "source-meaning graph hash")
    if semantic_source_meaning_sha256(graph) != graph_sha:
        raise ValueError(f"candidate {case_id} author graph hash drifts")
    run = require_semantic_source_meaning_author_run(
        row.get("author_run"), graph_sha256=graph_sha
    )
    if (
        run["host_profile"] != host_profile
        or run["model"] != profile["model"]
        or run["reasoning_effort"] != profile["reasoning_effort"]
    ):
        raise ValueError(f"candidate {case_id} author changes its host")
    return {**row, "graph": graph, "graph_sha256": graph_sha, "author_run": run}


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


def _case_index(corpus: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = corpus.get("cases")
    if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
        raise ValueError("development corpus cases must be a JSON object array")
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        case_id = _text(row.get("case_id"), "development case id")
        if case_id in result:
            raise ValueError("development corpus case ids are not unique")
        result[case_id] = dict(row)
    if not result:
        raise ValueError("development corpus is empty")
    return result


def _text(value: Any, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{label} must be non-empty")
    return result


def _sha256(value: Any, label: str) -> str:
    result = _text(value, label)
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        raise ValueError(f"{label} must be a lowercase SHA-256")
    return result


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} fields do not match its contract")


__all__ = [
    "ACTIVE_EVIDENCE_PLAN_VERSION",
    "prepare_active_evidence_plan",
    "require_active_evidence_plan",
    "require_successful_pipeline_evidence",
]
