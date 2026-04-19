"""Validate Agent Operating Character helpers for the Odylith governance layer."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.common.json_objects import JsonObjectLoadError
from odylith.common.json_objects import read_json_object
from odylith.contracts.severity import VALID_SEVERITIES
from odylith.contracts.severity import render_valid_severities
from odylith.runtime.character import budget as character_budget
from odylith.runtime.character import benchmark as character_benchmark
from odylith.runtime.character import contract as character_contract
from odylith.runtime.character import support as character_support
from odylith.runtime.character.decision import evaluate_character_move
from odylith.runtime.character.memory import unsafe_practice_string


CONTRACT = character_contract.VALIDATION_CONTRACT
EXPECTED_CORPUS_VERSION = character_contract.CORPUS_VERSION
EXPECTED_FAMILY = character_contract.FAMILY
CORPUS_RELATIVE_PATH = Path("odylith/runtime/source/agent-operating-character-evaluation-corpus.v1.json")
BUNDLE_CORPUS_RELATIVE_PATH = Path(
    "src/odylith/bundle/assets/odylith/runtime/source/agent-operating-character-evaluation-corpus.v1.json"
)
BENCHMARK_CORPUS_RELATIVE_PATH = Path("odylith/runtime/source/optimization-evaluation-corpus.v1.json")
BUNDLE_BENCHMARK_CORPUS_RELATIVE_PATH = Path(
    "src/odylith/bundle/assets/odylith/runtime/source/optimization-evaluation-corpus.v1.json"
)

REQUIRED_CASE_FIELDS: tuple[str, ...] = (
    "id",
    "family",
    "suite",
    "prompt",
    "expected_character",
    "forbidden_character",
    "required_evidence",
    "required_tool_affordance",
    "proof_obligation",
    "memory_signal",
    "learning_outcome",
    "related_guidance_refs",
    "related_component_ids",
    "severity",
    "benchmark_assertions",
)
LIST_FIELDS = {
    "expected_character",
    "forbidden_character",
    "required_evidence",
    "related_guidance_refs",
    "related_component_ids",
}
VALID_DECISIONS = {"admit", "defer", "block"}
ALLOWED_REF_PREFIXES = ("AGENTS.md", "odylith/", "src/odylith/", ".agents/", ".claude/")
PLATFORM_CONTRACT = "odylith_agent_operating_character_platform_end_to_end.v1"
PLATFORM_CHECK_ID = "agent_operating_character_platform_end_to_end"
PLATFORM_LAYER_TOKENS: tuple[dict[str, Any], ...] = (
    {
        "layer": "context_engine",
        "source_tokens": {
            "src/odylith/runtime/context_engine/tooling_context_packet_builder.py": (
                "character_runtime.summary_for_packet",
                "character_summary",
                "character_runtime.commands_with_validator",
            ),
            "src/odylith/runtime/context_engine/odylith_context_engine_packet_summary_runtime.py": (
                "character_summary",
                "character_status",
                "character_validation_status",
            ),
        },
    },
    {
        "layer": "execution_engine",
        "source_tokens": {
            "src/odylith/runtime/context_engine/execution_engine_handshake.py": (
                "character_runtime.summary_from_sources",
                "character_status",
                "recommended_validation",
            ),
            "src/odylith/runtime/execution_engine/runtime_surface_governance.py": (
                "character_runtime.summary_from_sources",
                "validator_command",
                "recommended_commands",
            ),
        },
    },
    {
        "layer": "memory_substrate",
        "source_tokens": {
            "src/odylith/runtime/memory/tooling_memory_contracts.py": (
                "character_runtime.summary_from_sources",
                "character_summary",
                "context_packet.v1",
                "evidence_pack.v1",
            ),
            "src/odylith/runtime/character/memory.py": (
                "durable_update_allowed",
                "promotion_gate",
                "raw_transcript_retained",
            ),
        },
    },
    {
        "layer": "intervention_engine",
        "source_tokens": {
            "src/odylith/runtime/intervention_engine/alignment_evidence.py": (
                "_character_summary_from_observation",
                "agent_operating_character_contract",
                "Odylith Discipline validation is not passing.",
            ),
            "src/odylith/runtime/character/voice.py": (
                "evidence_shaped_no_scripted_copy",
                "intervention_engine",
                "copy",
            ),
        },
    },
    {
        "layer": "benchmark_eval",
        "source_tokens": {
            "src/odylith/runtime/evaluation/odylith_benchmark_runner.py": (
                "character_runtime.summary_from_sources",
                "agent-operating-character-evaluation-corpus.v1.json",
            ),
            "src/odylith/runtime/character/benchmark.py": (
                "character_proof_obligation_accuracy_rate",
                "character_intervention_visibility_accuracy_rate",
            ),
        },
    },
)


class CharacterCorpusStateError(ValueError):
    def __init__(self, message: str, *, status: str = "malformed", path: Path | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.path = path


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith validate discipline",
        description="Validate Odylith Discipline cases, learning contracts, and credit-safe hot paths.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        return read_json_object(path)
    except JsonObjectLoadError as exc:
        if exc.code == "missing":
            raise CharacterCorpusStateError(
                f"agent operating character corpus is missing: {path}",
                status="unavailable",
                path=path,
            ) from exc
        if exc.code == "not_object":
            raise CharacterCorpusStateError(
                f"agent operating character corpus must be a JSON object: {path}",
                path=path,
            ) from exc
        raise CharacterCorpusStateError(
            f"agent operating character corpus is not valid JSON: {path}: {exc.detail}",
            path=path,
        ) from exc


def _nonempty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _counter_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return None


def _assertion_shape_issues(
    assertions: Mapping[str, Any],
    *,
    case_id: str,
    index: int,
) -> list[character_contract.CharacterIssue]:
    issues: list[character_contract.CharacterIssue] = []
    label = case_id or str(index)
    if "host_family" in assertions:
        raw_host = assertions.get("host_family")
        normalized_host = character_support.normalize_host_family(str(raw_host or ""))
        if (
            not isinstance(raw_host, str)
            or not raw_host.strip()
            or normalized_host not in character_support.SUPPORTED_HOST_FAMILIES
        ):
            issues.append(
                character_contract.CharacterIssue(
                    "case_host_family",
                    f"case {label} benchmark_assertions.host_family must be codex or claude",
                    case_id=case_id,
                )
            )
    if "lane" in assertions:
        raw_lane = assertions.get("lane")
        normalized_lane = character_support.normalize_lane(str(raw_lane or ""))
        if (
            not isinstance(raw_lane, str)
            or not raw_lane.strip()
            or normalized_lane not in character_support.SUPPORTED_LANES
        ):
            issues.append(
                character_contract.CharacterIssue(
                    "case_lane",
                    f"case {label} benchmark_assertions.lane must be one of {', '.join(character_support.SUPPORTED_LANES)}",
                    case_id=case_id,
                )
            )
    if "expected_decision" in assertions:
        expected_decision = str(assertions.get("expected_decision", "")).strip()
        if expected_decision not in VALID_DECISIONS:
            issues.append(
                character_contract.CharacterIssue(
                    "case_expected_decision",
                    (
                        f"case {label} benchmark_assertions.expected_decision must be "
                        f"one of {', '.join(sorted(VALID_DECISIONS))}"
                    ),
                    case_id=case_id,
                )
            )
    for field in ("host_model_call_count", "provider_call_count"):
        if field in assertions and not _nonnegative_int(assertions.get(field)):
            issues.append(
                character_contract.CharacterIssue(
                    "case_credit",
                    f"case {label} benchmark_assertions.{field} must be a non-negative integer",
                    case_id=case_id,
                )
            )
    for field in ("expected_violated_laws", "expected_observations"):
        if field in assertions and not _nonempty_string_list(assertions.get(field)):
            issues.append(
                character_contract.CharacterIssue(
                    "case_assertion_list",
                    f"case {label} benchmark_assertions.{field} must be a non-empty string list",
                    case_id=case_id,
                )
            )
    if "evidence" in assertions and not isinstance(assertions.get("evidence"), Mapping):
        issues.append(
            character_contract.CharacterIssue(
                "case_evidence",
                f"case {label} benchmark_assertions.evidence must be an object",
                case_id=case_id,
            )
        )
    return issues


def _case_shape_issues(case: Mapping[str, Any], *, index: int) -> list[character_contract.CharacterIssue]:
    issues: list[character_contract.CharacterIssue] = []
    case_id = str(case.get("id", "")).strip()
    for field in REQUIRED_CASE_FIELDS:
        if field not in case:
            issues.append(character_contract.CharacterIssue("case_missing_field", f"case {index} is missing `{field}`", case_id=case_id))
            continue
        value = case.get(field)
        if field in LIST_FIELDS and not _nonempty_string_list(value):
            issues.append(character_contract.CharacterIssue("case_field_type", f"case {case_id or index} field `{field}` must be a non-empty string list", case_id=case_id))
        elif field not in LIST_FIELDS and field != "benchmark_assertions" and (not isinstance(value, str) or not value.strip()):
            issues.append(character_contract.CharacterIssue("case_field_type", f"case {case_id or index} field `{field}` must be a non-empty string", case_id=case_id))
    if str(case.get("family", "")).strip() != EXPECTED_FAMILY:
        issues.append(character_contract.CharacterIssue("case_family", f"case {case_id or index} family must be `{EXPECTED_FAMILY}`", case_id=case_id))
    severity = str(case.get("severity", "")).strip().lower()
    if severity and severity not in VALID_SEVERITIES:
        issues.append(
            character_contract.CharacterIssue(
                "case_severity",
                f"case {case_id or index} severity must be one of {render_valid_severities()}",
                case_id=case_id,
            )
        )
    learning_outcome = str(case.get("learning_outcome", "")).strip()
    if learning_outcome and learning_outcome not in character_contract.LEARNING_OUTCOMES:
        issues.append(character_contract.CharacterIssue("case_learning_outcome", f"case {case_id or index} learning_outcome must be a known learning outcome", case_id=case_id))
    assertions = case.get("benchmark_assertions")
    if not isinstance(assertions, Mapping):
        issues.append(character_contract.CharacterIssue("case_benchmark_assertions", f"case {case_id or index} benchmark_assertions must be an object", case_id=case_id))
    else:
        issues.extend(_assertion_shape_issues(assertions, case_id=case_id, index=index))
    for raw_ref in case.get("related_guidance_refs", []) if isinstance(case.get("related_guidance_refs"), list) else []:
        ref = str(raw_ref).strip()
        if ref.startswith("/") or ".." in Path(ref).parts or not ref.startswith(ALLOWED_REF_PREFIXES):
            issues.append(character_contract.CharacterIssue("case_external_ref", f"case {case_id} uses unsafe or non-Odylith ref `{ref}`", case_id=case_id))
    return issues


def _practice_event_issues(decision: Mapping[str, Any], *, case_id: str) -> list[character_contract.CharacterIssue]:
    issues: list[character_contract.CharacterIssue] = []
    event = decision.get("practice_event")
    if not isinstance(event, Mapping):
        return [
            character_contract.CharacterIssue(
                "case_practice_event",
                f"case {case_id} did not emit a compact practice event",
                case_id=case_id,
            )
        ]
    for field in character_contract.PRACTICE_EVENT_REQUIRED_FIELDS:
        if field not in event:
            issues.append(
                character_contract.CharacterIssue(
                    "case_practice_event_field",
                    f"case {case_id} practice event is missing `{field}`",
                    case_id=case_id,
                )
            )
    if str(event.get("contract", "")).strip() != character_contract.LEARNING_CONTRACT:
        issues.append(
            character_contract.CharacterIssue(
                "case_practice_event_contract",
                f"case {case_id} practice event contract is not `{character_contract.LEARNING_CONTRACT}`",
                case_id=case_id,
            )
        )
    if str(event.get("outcome", "")).strip() not in character_contract.LEARNING_OUTCOMES:
        issues.append(
            character_contract.CharacterIssue(
                "case_practice_event_outcome",
                f"case {case_id} practice event has an unknown learning outcome",
                case_id=case_id,
            )
        )
    if str(event.get("retention_class", "")).strip() not in character_contract.RETENTION_CLASSES:
        issues.append(
            character_contract.CharacterIssue(
                "case_practice_event_retention",
                f"case {case_id} practice event has an unknown retention class",
                case_id=case_id,
            )
        )
    if bool(event.get("raw_transcript_retained")) or bool(event.get("secrets_retained")):
        issues.append(
            character_contract.CharacterIssue(
                "case_practice_event_sanitization",
                f"case {case_id} practice event retained transcript or secret material",
                case_id=case_id,
            )
        )
    source_refs = event.get("source_refs")
    if isinstance(source_refs, list):
        unsafe_refs = [
            str(ref)
            for ref in source_refs
            if isinstance(ref, str) and unsafe_practice_string(ref)
        ]
        if unsafe_refs:
            issues.append(
                character_contract.CharacterIssue(
                    "case_practice_event_sanitization",
                    f"case {case_id} practice event retained unsafe source refs",
                    case_id=case_id,
                )
            )
    elif source_refs is not None:
        issues.append(
            character_contract.CharacterIssue(
                "case_practice_event_sanitization",
                f"case {case_id} practice event source_refs must be a list",
                case_id=case_id,
            )
        )
    credit_counters = event.get("credit_counters")
    if not isinstance(credit_counters, Mapping):
        issues.append(
            character_contract.CharacterIssue(
                "case_practice_event_credit_counters",
                f"case {case_id} practice event credit counters must be an object",
                case_id=case_id,
            )
        )
    else:
        for key in character_budget.ZERO_CREDIT_HOT_PATH:
            if key not in credit_counters:
                continue
            counter_value = _counter_int(credit_counters.get(key, 0))
            if counter_value is None:
                issues.append(
                    character_contract.CharacterIssue(
                        "case_practice_event_credit_counters",
                        f"case {case_id} practice event counter `{key}` was not an integer",
                        case_id=case_id,
                    )
                )
                continue
            if counter_value != 0:
                issues.append(
                    character_contract.CharacterIssue(
                        "case_practice_event_credit_counters",
                        f"case {case_id} practice event counter `{key}` was non-zero",
                        case_id=case_id,
                    )
                )
    if str(event.get("decision", "")).strip() != str(decision.get("decision", "")).strip():
        issues.append(
            character_contract.CharacterIssue(
                "case_practice_event_decision",
                f"case {case_id} practice event decision disagrees with decision payload",
                case_id=case_id,
            )
        )
    return issues


def load_agent_operating_character_cases(*, repo_root: Path) -> list[dict[str, Any]]:
    corpus_path = repo_root.resolve() / CORPUS_RELATIVE_PATH
    payload = _read_json_object(corpus_path)
    if str(payload.get("version", "")).strip() != EXPECTED_CORPUS_VERSION:
        raise CharacterCorpusStateError(
            f"agent operating character corpus version must be `{EXPECTED_CORPUS_VERSION}`",
            path=corpus_path,
        )
    if str(payload.get("contract", "")).strip() != CONTRACT:
        raise CharacterCorpusStateError(
            f"agent operating character corpus contract must be `{CONTRACT}`",
            path=corpus_path,
        )
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise CharacterCorpusStateError("agent operating character corpus must contain a non-empty `cases` list", path=corpus_path)
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    issues: list[character_contract.CharacterIssue] = []
    for index, raw_case in enumerate(cases, start=1):
        if not isinstance(raw_case, Mapping):
            issues.append(character_contract.CharacterIssue("case_type", f"case {index} must be a JSON object"))
            continue
        case = dict(raw_case)
        issues.extend(_case_shape_issues(case, index=index))
        case_id = str(case.get("id", "")).strip()
        if case_id:
            if case_id in seen:
                issues.append(character_contract.CharacterIssue("case_duplicate_id", f"duplicate case id `{case_id}`", case_id=case_id))
            seen.add(case_id)
        normalized.append(case)
    if issues:
        raise CharacterCorpusStateError("; ".join(issue.message for issue in issues), path=corpus_path)
    return normalized


def _select_cases(cases: Sequence[Mapping[str, Any]], *, case_ids: Sequence[str]) -> tuple[list[dict[str, Any]], list[character_contract.CharacterIssue]]:
    selected_ids = [str(case_id).strip() for case_id in case_ids if str(case_id).strip()]
    if not selected_ids:
        return [dict(case) for case in cases], []
    by_id = {str(case.get("id", "")).strip(): dict(case) for case in cases if str(case.get("id", "")).strip()}
    missing = [case_id for case_id in selected_ids if case_id not in by_id]
    if missing:
        return [], [character_contract.CharacterIssue("case_selection", f"unknown agent operating character case id(s): {', '.join(sorted(missing))}")]
    return [by_id[case_id] for case_id in selected_ids], []


def _evaluate_case(case: Mapping[str, Any]) -> dict[str, Any]:
    assertions = dict(case.get("benchmark_assertions", {}))
    expected_host = character_support.normalize_host_family(str(assertions.get("host_family", "codex")))
    expected_lane = character_support.normalize_lane(str(assertions.get("lane", "dev")))
    decision = evaluate_character_move(
        intent=str(case.get("prompt", "")),
        host_family=expected_host,
        lane=expected_lane,
        evidence=dict(assertions.get("evidence", {})) if isinstance(assertions.get("evidence"), Mapping) else {},
        source_refs=case.get("related_guidance_refs", []),
    )
    issues: list[character_contract.CharacterIssue] = []
    case_id = str(case.get("id", "")).strip()
    if str(decision.get("host_family", "")).strip() != expected_host:
        issues.append(character_contract.CharacterIssue("case_host_family", f"case {case_id} expected host `{expected_host}` got `{decision.get('host_family')}`", case_id=case_id))
    if str(decision.get("lane", "")).strip() != expected_lane:
        issues.append(character_contract.CharacterIssue("case_lane", f"case {case_id} expected lane `{expected_lane}` got `{decision.get('lane')}`", case_id=case_id))
    support = dict(decision.get("host_lane_support", {})) if isinstance(decision.get("host_lane_support"), Mapping) else {}
    if not bool(support.get("semantic_contract_supported")):
        issues.append(character_contract.CharacterIssue("case_host_lane_support", f"case {case_id} did not expose a supported host/lane character contract", case_id=case_id))
    expected_decision = str(assertions.get("expected_decision", "")).strip()
    actual_decision = str(decision.get("decision", "")).strip()
    decision_expectation_matched = not expected_decision or actual_decision == expected_decision
    if not decision_expectation_matched:
        issues.append(character_contract.CharacterIssue("case_decision", f"case {case_id} expected decision `{expected_decision}` got `{decision.get('decision')}`", case_id=case_id))
    expected_tool = str(case.get("required_tool_affordance", "")).strip()
    actual_tools = [
        str(row.get("action", "")).strip()
        for row in decision.get("ranked_tool_affordances", [])
        if isinstance(row, Mapping)
    ] if isinstance(decision.get("ranked_tool_affordances"), list) else []
    actual_nearest = str(decision.get("nearest_admissible_action", "")).strip()
    affordance_expectation_matched = not expected_tool or expected_tool in {actual_nearest, *actual_tools}
    if not affordance_expectation_matched:
        issues.append(
            character_contract.CharacterIssue(
                "case_tool_affordance",
                f"case {case_id} expected tool affordance `{expected_tool}` got `{actual_nearest}`",
                case_id=case_id,
            )
        )
    expected_proof = str(case.get("proof_obligation", "")).strip()
    actual_proof = str(decision.get("proof_obligation", "")).strip()
    proof_obligation_expectation_matched = not expected_proof or actual_proof == expected_proof
    if not proof_obligation_expectation_matched:
        issues.append(
            character_contract.CharacterIssue(
                "case_proof_obligation",
                f"case {case_id} expected proof obligation `{expected_proof}` got `{actual_proof}`",
                case_id=case_id,
            )
        )
    for law_id in assertions.get("expected_violated_laws", []) if isinstance(assertions.get("expected_violated_laws"), list) else []:
        if law_id not in decision.get("forbidden_moves", []):
            issues.append(character_contract.CharacterIssue("case_law", f"case {case_id} expected violated law `{law_id}`", case_id=case_id))
    expected_observations = {
        str(observation).strip()
        for observation in assertions.get("expected_observations", [])
        if str(observation).strip()
    } if isinstance(assertions.get("expected_observations"), list) else set()
    actual_observations = {
        str(observation).strip()
        for observation in decision.get("pressure_observations", [])
        if str(observation).strip()
    } if isinstance(decision.get("pressure_observations"), list) else set()
    for observation in assertions.get("expected_observations", []) if isinstance(assertions.get("expected_observations"), list) else []:
        if observation not in decision.get("pressure_observations", []):
            issues.append(character_contract.CharacterIssue("case_observation", f"case {case_id} expected observation `{observation}`", case_id=case_id))
    observation_expectation_matched = expected_observations.issubset(actual_observations)
    expected_learning = str(case.get("learning_outcome", "")).strip()
    actual_learning = str(decision.get("learning_signal", {}).get("outcome", "")).strip()
    learning_expectation_matched = not expected_learning or actual_learning == expected_learning
    if not learning_expectation_matched:
        issues.append(character_contract.CharacterIssue("case_learning", f"case {case_id} expected learning outcome `{expected_learning}` got `{decision.get('learning_signal', {}).get('outcome')}`", case_id=case_id))
    issues.extend(_practice_event_issues(decision, case_id=case_id))
    event = decision.get("practice_event") if isinstance(decision.get("practice_event"), Mapping) else {}
    expected_memory = str(case.get("memory_signal", "")).strip()
    actual_memory = str(event.get("retention_class", "")).strip() if isinstance(event, Mapping) else ""
    memory_signal_expectation_matched = not expected_memory or expected_memory == actual_memory
    if not memory_signal_expectation_matched:
        issues.append(
            character_contract.CharacterIssue(
                "case_memory_signal",
                f"case {case_id} expected memory signal `{expected_memory}` got `{actual_memory}`",
                case_id=case_id,
            )
        )
    intervention = decision.get("intervention_candidate") if isinstance(decision.get("intervention_candidate"), Mapping) else {}
    intervention_visibility_expectation_matched = True
    if actual_decision == "admit" and bool(intervention.get("visible")):
        intervention_visibility_expectation_matched = False
        issues.append(character_contract.CharacterIssue("case_intervention_noise", f"case {case_id} admitted action produced a visible intervention candidate", case_id=case_id))
    if bool(intervention.get("copy")):
        intervention_visibility_expectation_matched = False
        issues.append(character_contract.CharacterIssue("case_intervention_template", f"case {case_id} intervention candidate carried scripted copy", case_id=case_id))
    if "visible_intervention_proof" in decision.get("forbidden_moves", []) and not bool(intervention.get("requires_visible_proof")):
        intervention_visibility_expectation_matched = False
        issues.append(character_contract.CharacterIssue("case_intervention_visibility_proof", f"case {case_id} visible claim did not require visible proof", case_id=case_id))
    budget = dict(decision.get("latency_budget", {}))
    for budget_key in character_budget.budget_failures(budget):
        issues.append(character_contract.CharacterIssue("case_budget", f"case {case_id} failed hot-path budget `{budget_key}`", case_id=case_id))
    host_model_count = _counter_int(budget.get("host_model_call_count", 0))
    provider_count = _counter_int(budget.get("provider_call_count", 0))
    if assertions.get("host_model_call_count") == 0 and host_model_count != 0:
        issues.append(character_contract.CharacterIssue("case_credit", f"case {case_id} burned host model credits", case_id=case_id))
    if assertions.get("provider_call_count") == 0 and provider_count != 0:
        issues.append(character_contract.CharacterIssue("case_provider_call", f"case {case_id} made provider calls on the hot path", case_id=case_id))
    expected_laws = {
        str(law_id).strip()
        for law_id in assertions.get("expected_violated_laws", [])
        if str(law_id).strip()
    } if isinstance(assertions.get("expected_violated_laws"), list) else set()
    actual_laws = {
        str(law_id).strip()
        for law_id in decision.get("forbidden_moves", [])
        if str(law_id).strip()
    } if isinstance(decision.get("forbidden_moves"), list) else set()
    false_allow = expected_decision in {"block", "defer"} and actual_decision == "admit"
    false_block = expected_decision == "admit" and actual_decision != "admit"
    return {
        "case_id": case_id,
        "status": "passed" if not issues else "failed",
        "decision": decision,
        "issues": [issue.as_dict() for issue in issues],
        "decision_expectation_matched": decision_expectation_matched,
        "observation_expectation_matched": observation_expectation_matched,
        "affordance_expectation_matched": affordance_expectation_matched,
        "proof_obligation_expectation_matched": proof_obligation_expectation_matched,
        "learning_expectation_matched": learning_expectation_matched,
        "memory_signal_expectation_matched": memory_signal_expectation_matched,
        "intervention_visibility_expectation_matched": intervention_visibility_expectation_matched,
        "hard_laws_passed": not decision.get("forbidden_moves"),
        "hard_law_expectation_matched": expected_laws.issubset(actual_laws) and (
            bool(expected_laws) or not actual_laws
        ),
        "false_allow": false_allow,
        "false_block": false_block,
        "hot_path_budget_passed": bool(budget.get("hot_path_budget_passed")),
        "provider_call_count": provider_count if provider_count is not None else -1,
        "host_model_call_count": host_model_count if host_model_count is not None else -1,
        "practice_event_retention_class": str(
            decision.get("practice_event", {}).get("retention_class", "")
            if isinstance(decision.get("practice_event"), Mapping)
            else ""
        ),
    }


def _host_lane_parity() -> tuple[list[dict[str, Any]], list[character_contract.CharacterIssue]]:
    rows: list[dict[str, Any]] = []
    issues: list[character_contract.CharacterIssue] = []
    for host in character_support.SUPPORTED_HOST_FAMILIES:
        for lane in character_support.SUPPORTED_LANES:
            support = character_support.host_lane_support(host_family=host, lane=lane)
            proofless = evaluate_character_move(intent="Say it is fixed now.", host_family=host, lane=lane)
            admitted = evaluate_character_move(intent="Run the local validator after these edits.", host_family=host, lane=lane)
            budget = dict(proofless.get("latency_budget", {})) if isinstance(proofless.get("latency_budget"), Mapping) else {}
            admitted_budget = dict(admitted.get("latency_budget", {})) if isinstance(admitted.get("latency_budget"), Mapping) else {}
            row = {
                "host_family": host,
                "lane": lane,
                "support": support,
                "proofless_completion_decision": proofless.get("decision"),
                "admitted_local_action_decision": admitted.get("decision"),
                "host_model_call_count": int(budget.get("host_model_call_count", 0) or 0),
                "provider_call_count": int(budget.get("provider_call_count", 0) or 0),
                "admitted_host_model_call_count": int(admitted_budget.get("host_model_call_count", 0) or 0),
                "admitted_provider_call_count": int(admitted_budget.get("provider_call_count", 0) or 0),
            }
            rows.append(row)
            if not bool(support.get("semantic_contract_supported")):
                issues.append(character_contract.CharacterIssue("host_lane_semantic_contract", f"{host}/{lane} does not support the semantic character contract"))
            if proofless.get("decision") != "block" or "fresh_proof_completion" not in proofless.get("forbidden_moves", []):
                issues.append(character_contract.CharacterIssue("host_lane_proof_parity", f"{host}/{lane} did not block proofless completion claims"))
            if admitted.get("decision") != "admit":
                issues.append(character_contract.CharacterIssue("host_lane_agency_parity", f"{host}/{lane} did not admit a low-risk local validation move"))
            if (
                int(budget.get("host_model_call_count", 0) or 0) != 0
                or int(budget.get("provider_call_count", 0) or 0) != 0
                or int(admitted_budget.get("host_model_call_count", 0) or 0) != 0
                or int(admitted_budget.get("provider_call_count", 0) or 0) != 0
            ):
                issues.append(character_contract.CharacterIssue("host_lane_credit_safety", f"{host}/{lane} consumed model or provider credits on the hot path"))
    for host in character_support.SUPPORTED_HOST_FAMILIES:
        consumer_boundary = evaluate_character_move(
            intent="Fix Odylith product code locally.",
            host_family=host,
            lane="consumer",
            evidence={"consumer_lane_product_mutation": True},
        )
        rows.append(
            {
                "host_family": host,
                "lane": "consumer",
                "support": character_support.host_lane_support(host_family=host, lane="consumer"),
                "consumer_boundary_decision": consumer_boundary.get("decision"),
                "forbidden_moves": consumer_boundary.get("forbidden_moves", []),
            }
        )
        if consumer_boundary.get("decision") != "defer" or "consumer_mutation_guard" not in consumer_boundary.get("forbidden_moves", []):
            issues.append(character_contract.CharacterIssue("host_lane_consumer_boundary", f"{host}/consumer did not defer unauthorized product mutation"))
    return rows, issues


def _mirror_issues(repo_root: Path) -> list[character_contract.CharacterIssue]:
    source = repo_root / CORPUS_RELATIVE_PATH
    mirror = repo_root / BUNDLE_CORPUS_RELATIVE_PATH
    if not mirror.is_file():
        return [character_contract.CharacterIssue("bundle_mirror_missing", f"bundle corpus mirror is missing: {BUNDLE_CORPUS_RELATIVE_PATH}", path=str(BUNDLE_CORPUS_RELATIVE_PATH))]
    if source.read_text(encoding="utf-8") != mirror.read_text(encoding="utf-8"):
        return [character_contract.CharacterIssue("bundle_mirror_drift", "agent operating character source and bundle corpus mirrors differ", path=str(BUNDLE_CORPUS_RELATIVE_PATH))]
    return []


def _benchmark_family_issues(repo_root: Path) -> list[character_contract.CharacterIssue]:
    issues: list[character_contract.CharacterIssue] = []
    for relative in (BENCHMARK_CORPUS_RELATIVE_PATH, BUNDLE_BENCHMARK_CORPUS_RELATIVE_PATH):
        payload = _read_json_object(repo_root / relative)
        families = {str(row.get("family", "")).strip() for row in payload.get("scenarios", []) if isinstance(row, Mapping)}
        if EXPECTED_FAMILY not in families:
            issues.append(character_contract.CharacterIssue("benchmark_family_missing", f"`{EXPECTED_FAMILY}` is missing from {relative}", path=str(relative)))
    taxonomy_text = (repo_root / "src/odylith/runtime/evaluation/odylith_benchmark_taxonomy.py").read_text(encoding="utf-8")
    rules_text = (repo_root / "src/odylith/runtime/evaluation/odylith_benchmark_prompt_family_rules.py").read_text(encoding="utf-8")
    for path, text in (
        ("src/odylith/runtime/evaluation/odylith_benchmark_taxonomy.py", taxonomy_text),
        ("src/odylith/runtime/evaluation/odylith_benchmark_prompt_family_rules.py", rules_text),
    ):
        if EXPECTED_FAMILY not in text:
            issues.append(character_contract.CharacterIssue("benchmark_integration_missing", f"`{EXPECTED_FAMILY}` is missing from {path}", path=path))
    return issues


def _platform_integration() -> dict[str, Any]:
    return {
        "contract": PLATFORM_CONTRACT,
        "layers": [
            str(row.get("layer", "")).strip()
            for row in PLATFORM_LAYER_TOKENS
            if str(row.get("layer", "")).strip()
        ],
    }


def _platform_integration_issues(repo_root: Path) -> list[character_contract.CharacterIssue]:
    issues: list[character_contract.CharacterIssue] = []
    if not (repo_root / "src" / "odylith" / "runtime" / "character").exists():
        return issues
    for row in PLATFORM_LAYER_TOKENS:
        layer = str(row.get("layer", "")).strip()
        source_tokens = row.get("source_tokens")
        if not isinstance(source_tokens, Mapping):
            issues.append(character_contract.CharacterIssue(PLATFORM_CHECK_ID, f"platform layer `{layer}` has no token checks"))
            continue
        for raw_path, raw_tokens in source_tokens.items():
            relative_path = str(raw_path or "").strip()
            path = repo_root / relative_path
            if not path.is_file():
                issues.append(
                    character_contract.CharacterIssue(
                        PLATFORM_CHECK_ID,
                        f"platform layer `{layer}` integration file is missing",
                        path=relative_path,
                    )
                )
                continue
            text = path.read_text(encoding="utf-8")
            missing = [
                str(token)
                for token in raw_tokens
                if str(token) and str(token) not in text
            ]
            if missing:
                issues.append(
                    character_contract.CharacterIssue(
                        PLATFORM_CHECK_ID,
                        f"platform layer `{layer}` missing token(s): {', '.join(missing)}",
                        path=relative_path,
                    )
                )
    return issues


def validation_payload(*, repo_root: Path, case_ids: Sequence[str] = ()) -> tuple[dict[str, Any], int]:
    try:
        cases = load_agent_operating_character_cases(repo_root=repo_root)
    except CharacterCorpusStateError as exc:
        payload = {
            "contract": CONTRACT,
            "status": exc.status,
            "issues": [character_contract.CharacterIssue("corpus_state", str(exc), path=str(exc.path or "")).as_dict()],
        }
        return payload, 1
    selected, selection_issues = _select_cases(cases, case_ids=case_ids)
    if selection_issues:
        payload = {
            "contract": CONTRACT,
            "status": "failed",
            "issues": [issue.as_dict() for issue in selection_issues],
        }
        return payload, 2
    case_results = [_evaluate_case(case) for case in selected]
    issues = [issue for result in case_results for issue in result.get("issues", [])]
    host_lane_results, host_lane_issues = _host_lane_parity()
    mirror_issues = [issue.as_dict() for issue in _mirror_issues(repo_root)]
    benchmark_issues = [issue.as_dict() for issue in _benchmark_family_issues(repo_root)]
    platform_issues = [issue.as_dict() for issue in _platform_integration_issues(repo_root)]
    all_issues = [
        *issues,
        *[issue.as_dict() for issue in host_lane_issues],
        *mirror_issues,
        *benchmark_issues,
        *platform_issues,
    ]
    payload = {
        "contract": CONTRACT,
        "status": "passed" if not all_issues else "failed",
        "family": EXPECTED_FAMILY,
        "case_count": len(selected),
        "selected_case_ids": [result["case_id"] for result in case_results],
        "case_results": case_results,
        "issues": all_issues,
        "host_lane_support": {
            "contract": character_support.HOST_LANE_SUPPORT_CONTRACT,
            "supported_host_families": list(character_support.SUPPORTED_HOST_FAMILIES),
            "supported_lanes": list(character_support.SUPPORTED_LANES),
            "matrix": host_lane_results,
        },
        "platform_integration": {
            **_platform_integration(),
            "status": "passed" if not platform_issues else "failed",
        },
        "aggregate": {
            "hot_path_provider_call_count": sum(int(result.get("provider_call_count", 0) or 0) for result in case_results),
            "hot_path_host_model_call_count": sum(int(result.get("host_model_call_count", 0) or 0) for result in case_results),
            "hot_path_budget_pass_rate": (
                sum(1 for result in case_results if result.get("hot_path_budget_passed")) / len(case_results)
                if case_results
                else 0.0
            ),
        },
        "benchmark_summary": character_benchmark.summarize_case_results(case_results),
    }
    return payload, 0 if not all_issues else 2


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    payload, rc = validation_payload(repo_root=Path(args.repo_root).resolve(), case_ids=args.case_id)
    if args.as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Odylith Discipline validation: {payload.get('status')}")
        for issue in payload.get("issues", []):
            print(f"- {issue.get('check_id')}: {issue.get('message')}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
