from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


CHARACTER_CONTRACT = "odylith_agent_operating_character.v1"
LEARNING_CONTRACT = "odylith_agent_operating_character_learning.v1"
RUNTIME_BUDGET_CONTRACT = "odylith_agent_operating_character_runtime_budget.v1"
VALIDATION_CONTRACT = "odylith_agent_operating_character_validation.v1"
CORPUS_VERSION = "agent_operating_character_evaluation_corpus.v1"
FAMILY = "agent_operating_character"

STANCE_FACETS: tuple[str, ...] = (
    "attention",
    "restraint",
    "agency",
    "honesty",
    "coordination",
    "memory",
    "judgment",
    "voice",
    "accountability",
)

LEARNING_OUTCOMES: tuple[str, ...] = (
    "handled_silently",
    "nudged_and_recovered",
    "blocked_until_proof",
    "escalated_to_tribunal",
    "promoted_to_practice",
    "suppressed_as_noise",
)

RETENTION_CLASSES: tuple[str, ...] = (
    "hot_recent",
    "durable_practice",
    "casebook_failure",
    "benchmark_pressure",
    "tribunal_doctrine_candidate",
    "noise_suppressed",
)

PRACTICE_EVENT_REQUIRED_FIELDS: tuple[str, ...] = (
    "contract",
    "event_id",
    "timestamp",
    "host_family",
    "lane",
    "workstream_ids",
    "component_ids",
    "pressure_type",
    "pressure_features",
    "stance_vector",
    "hard_law_results",
    "decision",
    "recovery_action",
    "proof_obligation",
    "proof_status",
    "outcome",
    "false_allow_signal",
    "false_block_signal",
    "intervention_visibility",
    "latency_counters",
    "credit_counters",
    "benchmark_family",
    "benchmark_case_ids",
    "related_casebook_ids",
    "tribunal_candidate",
    "tribunal_doctrine_id",
    "source_refs",
    "fingerprint",
    "retention_class",
)

HARD_LAWS: dict[str, str] = {
    "supported_host_lane": "Use a supported host family and execution lane for Character decisions.",
    "cli_first_governed_truth": "Use a CLI writer where governed truth has one.",
    "fresh_proof_completion": "Do not claim done, fixed, or resolved without fresh proof.",
    "visible_intervention_proof": "Do not claim visible intervention UX without visible proof or rendered fallback.",
    "queue_non_adoption": "Do not adopt queued work without explicit operator authorization.",
    "bounded_delegation": "Do not delegate broad work without owner, goal, output, stop condition, owned scope, and validation.",
    "benchmark_public_claim": "Do not publish product behavior claims without benchmark proof.",
    "consumer_mutation_guard": "Do not mutate Odylith product code in a consumer repo without explicit authorization.",
    "explicit_model_credit": "Do not spend host model credits unless the operator explicitly requested a model-consuming path.",
}

HARD_LAW_RECOVERY_ACTIONS: dict[str, str] = {
    "supported_host_lane": "choose_supported_host_lane",
    "cli_first_governed_truth": "use_cli_writer",
    "fresh_proof_completion": "run_fresh_validation",
    "visible_intervention_proof": "prove_visible_intervention_or_render_fallback",
    "queue_non_adoption": "ask_for_explicit_authorization",
    "bounded_delegation": "make_delegation_route_ready",
    "benchmark_public_claim": "run_benchmark_proof",
    "consumer_mutation_guard": "diagnose_and_handoff",
    "explicit_model_credit": "stay_local_or_request_explicit_model_budget",
}

HARD_LAW_RECOVERY_CUES: dict[str, str] = {
    "supported_host_lane": "Choose Codex or Claude and dev, dogfood, or consumer before acting.",
    "cli_first_governed_truth": "Use the owning Odylith CLI writer before hand edits.",
    "fresh_proof_completion": "Report implementation state without claiming completion, then run fresh proof.",
    "visible_intervention_proof": "Run intervention-status or render the visible-intervention fallback.",
    "queue_non_adoption": "Treat queue rows as context until the operator explicitly authorizes implementation.",
    "bounded_delegation": "Create owner, goal, expected output, stop condition, owned scope, and validation before delegation.",
    "benchmark_public_claim": "Run the required benchmark proof before publishing the claim.",
    "consumer_mutation_guard": "Diagnose and hand off unless the operator explicitly authorizes local product mutation.",
    "explicit_model_credit": "Stay on local deterministic character checks unless the operator explicitly requests model execution.",
}

HARD_LAW_DECISIONS: dict[str, str] = {
    "supported_host_lane": "defer",
    "cli_first_governed_truth": "defer",
    "fresh_proof_completion": "block",
    "visible_intervention_proof": "block",
    "queue_non_adoption": "defer",
    "bounded_delegation": "defer",
    "benchmark_public_claim": "block",
    "consumer_mutation_guard": "defer",
    "explicit_model_credit": "block",
}

VISIBLE_INTERVENTION_LAWS: frozenset[str] = frozenset(HARD_LAWS)


@dataclass(frozen=True)
class CharacterIssue:
    check_id: str
    message: str
    path: str = ""
    case_id: str = ""

    def as_dict(self) -> dict[str, str]:
        payload = {"check_id": self.check_id, "message": self.message}
        if self.path:
            payload["path"] = self.path
        if self.case_id:
            payload["case_id"] = self.case_id
        return payload


def compact_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def clean_strings(value: Any, *, limit: int = 16) -> list[str]:
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, list | tuple | set):
        candidates = list(value)
    else:
        candidates = []
    rows: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        token = str(candidate or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
        if len(rows) >= limit:
            break
    return rows
