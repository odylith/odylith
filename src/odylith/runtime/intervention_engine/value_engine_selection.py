from __future__ import annotations

from collections import Counter
import itertools
import re
import time
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.intervention_engine.value_engine_types import MAX_AMBIENT_BLOCKS
from odylith.runtime.intervention_engine.value_engine_types import MAX_ENUMERATED_OPTIONS
from odylith.runtime.intervention_engine.value_engine_types import MAX_LIVE_BLOCKS
from odylith.runtime.intervention_engine.value_engine_types import RUNTIME_POSTURE
from odylith.runtime.intervention_engine.value_engine_types import SELECTION_FLOOR
from odylith.runtime.intervention_engine.value_engine_types import URGENT_RISK_FLOOR
from odylith.runtime.intervention_engine.value_engine_types import VALUE_ENGINE_VERSION
from odylith.runtime.intervention_engine.value_engine_types import VISIBLE_LABELS
from odylith.runtime.intervention_engine.value_engine_types import VisibleInterventionOption
from odylith.runtime.intervention_engine.value_engine_types import VisibleSignalSelectionDecision
from odylith.runtime.intervention_engine.value_engine_types import _mapping
from odylith.runtime.intervention_engine.value_engine_types import _normalize_string
from odylith.runtime.intervention_engine.value_engine_types import _normalize_token
from odylith.runtime.intervention_engine.value_engine_types import _sequence
from odylith.runtime.intervention_engine.value_engine_types import _stable_id
from odylith.runtime.intervention_engine.value_engine_types import option_net_value
from odylith.runtime.intervention_engine.value_engine_types import proposition_evidence_confidence


_LABEL_ORDER = {"risks": 0, "history": 1, "insight": 2, "observation": 3, "proposal": 4}
_EVIDENCE_GATE_REASONS = frozenset(
    {
        "missing_evidence_signal",
        "weak_evidence_signal",
        "stale_signal",
        "generated_only_signal",
        "hidden_only_signal",
        "non_current_evidence_signal",
    }
)
_ALLOWED_BLOCK_KINDS = frozenset({"ambient", "observation", "proposal"})
_CURRENT_EVIDENCE_FRESHNESSES = frozenset({"", "current", "fresh", "live"})
_SEMANTIC_DUPLICATE_MIN_SHARED_TOKENS = 2
_SEMANTIC_DUPLICATE_OVERLAP_FLOOR = 0.75
_DUPLICATE_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_:\.-]{1,80}")
_DUPLICATE_TOKEN_STOPWORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "against",
        "all",
        "also",
        "and",
        "any",
        "are",
        "assist",
        "because",
        "before",
        "block",
        "blocks",
        "but",
        "can",
        "cannot",
        "could",
        "does",
        "from",
        "has",
        "have",
        "history",
        "inside",
        "insight",
        "into",
        "its",
        "must",
        "need",
        "needs",
        "observation",
        "odylith",
        "only",
        "proposal",
        "risk",
        "risks",
        "should",
        "signal",
        "signals",
        "that",
        "the",
        "this",
        "those",
        "through",
        "useful",
        "when",
        "where",
        "while",
        "with",
        "without",
    }
)


def _has_grounding_source(option: VisibleInterventionOption) -> bool:
    proposition = option.proposition
    if proposition.evidence:
        return True
    if any(_normalize_string(row.get("id") or row.get("path") or row.get("label")) for row in proposition.anchor_refs):
        return True
    return any(
        _normalize_string(key) and _normalize_string(value)
        for key, value in (proposition.source_fingerprints or {}).items()
    )


def _evidence_freshnesses(option: VisibleInterventionOption) -> list[str]:
    return [
        _normalize_token(row.freshness) or "current"
        for row in option.proposition.evidence
    ]


def _proposal_has_concrete_action(option: VisibleInterventionOption) -> bool:
    actions = _sequence(_mapping(option.action_payload).get("actions"))
    for action in actions:
        row = _mapping(action)
        surface = _normalize_token(row.get("surface"))
        verb = _normalize_token(row.get("operation") or row.get("action") or row.get("cli_command"))
        target = _normalize_string(
            row.get("target_id")
            or row.get("target_kind")
            or row.get("title")
            or row.get("cli_command")
        )
        payload = _mapping(row.get("payload"))
        if surface and verb and (target or payload):
            return True
    return False


def _semantic_signature_tokens(option: VisibleInterventionOption) -> set[str]:
    tokens: set[str] = set()
    for token in option.proposition.semantic_signature:
        normalized = _normalize_token(token)
        if not normalized or len(normalized) < 2 or normalized in _DUPLICATE_TOKEN_STOPWORDS:
            continue
        tokens.add(normalized)
    tokens.update(_duplicate_text_tokens(option.proposition.claim_text))
    if len(tokens) < _SEMANTIC_DUPLICATE_MIN_SHARED_TOKENS:
        tokens.update(_duplicate_text_tokens(option.text()))
    return tokens


def _duplicate_text_tokens(*values: Any) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        text = _normalize_string(value).lower()
        if not text:
            continue
        for raw_token in _DUPLICATE_TOKEN_RE.findall(text):
            token = _normalize_token(raw_token.strip("_:.-"))
            if len(token) < 3 or token in _DUPLICATE_TOKEN_STOPWORDS:
                continue
            tokens.add(token)
    return tokens


def _normalized_claim_text(option: VisibleInterventionOption) -> str:
    return _normalize_string(option.proposition.claim_text or option.text()).lower()


def _proposal_action_exception(
    left: VisibleInterventionOption,
    right: VisibleInterventionOption,
) -> bool:
    labels = {left.normalized_label(), right.normalized_label()}
    if labels != {"observation", "proposal"}:
        return False
    proposal = left if left.normalized_label() == "proposal" else right
    return _proposal_has_concrete_action(proposal)


def _semantic_duplicate(
    left: VisibleInterventionOption,
    right: VisibleInterventionOption,
) -> bool:
    left_claim = _normalized_claim_text(left)
    right_claim = _normalized_claim_text(right)
    if left_claim and left_claim == right_claim:
        return True
    if _proposal_action_exception(left, right):
        return False
    left_tokens = _semantic_signature_tokens(left)
    right_tokens = _semantic_signature_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    shared_count = len(left_tokens & right_tokens)
    if shared_count < _SEMANTIC_DUPLICATE_MIN_SHARED_TOKENS:
        return False
    overlap = shared_count / max(1, min(len(left_tokens), len(right_tokens)))
    return overlap >= _SEMANTIC_DUPLICATE_OVERLAP_FLOOR


def _pair_key(left: VisibleInterventionOption, right: VisibleInterventionOption) -> tuple[str, str]:
    first, second = sorted((_normalize_string(left.option_id), _normalize_string(right.option_id)))
    return first, second


def _option_hard_gate_reason(option: VisibleInterventionOption) -> str:
    proposition = option.proposition
    support_state = proposition.normalized_support_state()
    label = option.normalized_label()
    kind = option.normalized_kind()
    if not option.text():
        return "empty_signal"
    if label not in VISIBLE_LABELS:
        return "unknown_visible_label"
    if kind not in _ALLOWED_BLOCK_KINDS:
        return "unknown_block_kind"
    if label in {"risks", "history", "insight"} and kind != "ambient":
        return "label_block_kind_mismatch"
    if label == "observation" and kind != "observation":
        return "label_block_kind_mismatch"
    if label == "proposal" and kind != "proposal":
        return "label_block_kind_mismatch"
    if support_state != "supported":
        return f"{support_state}_signal"
    freshness = _normalize_token(proposition.freshness_state) or "current"
    if freshness in {"stale", "expired"}:
        return "stale_signal"
    if freshness == "generated_only":
        return "generated_only_signal"
    if freshness == "hidden_only":
        return "hidden_only_signal"
    if not _has_grounding_source(option):
        return "missing_evidence_signal"
    evidence_freshnesses = _evidence_freshnesses(option)
    if evidence_freshnesses and all(row in {"stale", "expired"} for row in evidence_freshnesses):
        return "stale_signal"
    if evidence_freshnesses and all(row == "generated_only" for row in evidence_freshnesses):
        return "generated_only_signal"
    if evidence_freshnesses and all(row == "hidden_only" for row in evidence_freshnesses):
        return "hidden_only_signal"
    if evidence_freshnesses and not any(row in _CURRENT_EVIDENCE_FRESHNESSES for row in evidence_freshnesses):
        return "non_current_evidence_signal"
    if proposition_evidence_confidence(proposition) < 0.50:
        return "weak_evidence_signal"
    if label == "proposal" and not _proposal_has_concrete_action(option):
        return "proposal_without_concrete_action"
    return ""


def _option_sort_key(option: VisibleInterventionOption) -> tuple[float, int, str, str]:
    return (
        -option_net_value(option),
        _LABEL_ORDER.get(option.normalized_label(), 99),
        option.duplicate_group(),
        _normalize_string(option.option_id),
    )


def _render_order_key(option: VisibleInterventionOption) -> tuple[int, float, str, str]:
    return (
        _LABEL_ORDER.get(option.normalized_label(), 99),
        -option_net_value(option),
        option.duplicate_group(),
        _normalize_string(option.option_id),
    )


def _passes_value_floor(option: VisibleInterventionOption, *, value: float | None = None) -> bool:
    value = option_net_value(option) if value is None else value
    features = option.features.normalized()
    return _passes_value_floor_cached(
        label=option.normalized_label(),
        value=value,
        correctness=features.correctness_confidence,
        materiality=features.materiality,
    )


def _passes_value_floor_cached(
    *,
    label: str,
    value: float,
    correctness: float,
    materiality: float,
) -> bool:
    if value >= SELECTION_FLOOR:
        return True
    return (
        label == "risks"
        and value >= URGENT_RISK_FLOOR
        and correctness >= 0.78
        and materiality >= 0.90
    )


def adaptive_budget(
    options: Sequence[VisibleInterventionOption],
    *,
    context: Mapping[str, Any] | None = None,
) -> dict[str, int | bool]:
    ctx = _mapping(context)
    explicit_intent = bool(ctx.get("explicit_diagnosis_or_planning"))
    intent_token = _normalize_token(ctx.get("intent"))
    if intent_token in {"diagnosis", "planning", "architecture", "review"}:
        explicit_intent = True
    high_materiality = [
        option
        for option in options
        if option.features.normalized().materiality >= 0.85 and not _option_hard_gate_reason(option)
    ]
    actionable_proposal = any(
        option.normalized_label() == "proposal"
        and _proposal_has_concrete_action(option)
        and option.features.normalized().actionability >= 0.75
        for option in options
    )
    budget = 1
    if explicit_intent:
        budget += 1
    if len({option.duplicate_group() for option in high_materiality}) >= 2:
        budget += 1
    if actionable_proposal:
        budget += 1
    return {
        "live_block_budget": min(MAX_LIVE_BLOCKS, budget),
        "ambient_block_budget": MAX_AMBIENT_BLOCKS,
        "explicit_diagnosis_or_planning": explicit_intent,
        "high_materiality_distinct_count": len({option.duplicate_group() for option in high_materiality}),
        "actionable_proposal_present": actionable_proposal,
    }


def _valid_subset(
    options: Sequence[VisibleInterventionOption],
    *,
    budget: Mapping[str, Any],
    semantic_conflict_pairs: set[tuple[str, str]] | frozenset[tuple[str, str]] | None = None,
) -> bool:
    if len(options) > int(budget.get("live_block_budget") or 1):
        return False
    labels: set[str] = set()
    duplicate_groups: set[str] = set()
    ambient_count = 0
    has_observation = False
    for option in options:
        label = option.normalized_label()
        if label in labels and label in {"observation", "proposal"}:
            return False
        labels.add(label)
        duplicate = option.duplicate_group()
        if duplicate and duplicate in duplicate_groups:
            return False
        duplicate_groups.add(duplicate)
        if option.normalized_kind() == "ambient":
            ambient_count += 1
        if label == "observation":
            has_observation = True
    if ambient_count > int(budget.get("ambient_block_budget") or MAX_AMBIENT_BLOCKS):
        return False
    for left, right in itertools.combinations(options, 2):
        if semantic_conflict_pairs is not None:
            if _pair_key(left, right) in semantic_conflict_pairs:
                return False
            continue
        if _semantic_duplicate(left, right):
            return False
    for option in options:
        if option.normalized_label() == "proposal" and not has_observation:
            return False
    return True


def _subset_utility(options: Sequence[VisibleInterventionOption]) -> float:
    score = sum(option_net_value(option) for option in options)
    labels = {option.normalized_label() for option in options}
    if {"observation", "proposal"} <= labels:
        score += 0.04
    if len({option.duplicate_group() for option in options}) >= 2:
        score += 0.03
    ambient_label_counts = Counter(
        option.normalized_label()
        for option in options
        if option.normalized_kind() == "ambient"
    )
    repeated_ambient_labels = sum(max(0, count - 1) for count in ambient_label_counts.values())
    if repeated_ambient_labels:
        score -= repeated_ambient_labels * 0.025
    if len(options) > 1:
        score -= (len(options) - 1) * 0.045
    return round(max(0.0, score), 6)


def _subset_tiebreak_key(options: Sequence[VisibleInterventionOption]) -> tuple[int, tuple[tuple[float, int, str, str], ...]]:
    return (
        len(options),
        tuple(_option_sort_key(option) for option in options),
    )


def _conflict_edge_count(options: Sequence[VisibleInterventionOption]) -> int:
    edges = 0
    duplicates = Counter(option.duplicate_group() for option in options if option.duplicate_group())
    edges += sum((count * (count - 1)) // 2 for count in duplicates.values() if count > 1)
    non_ambient_labels = Counter(
        option.normalized_label()
        for option in options
        if option.normalized_label() in {"observation", "proposal"}
    )
    edges += sum((count * (count - 1)) // 2 for count in non_ambient_labels.values() if count > 1)
    proposal_count = sum(1 for option in options if option.normalized_label() == "proposal")
    has_observation = any(option.normalized_label() == "observation" for option in options)
    if proposal_count and not has_observation:
        edges += proposal_count
    edges += sum(
        1
        for left, right in itertools.combinations(options, 2)
        if _semantic_duplicate(left, right)
    )
    return edges


def _selected_block_set_id(options: Sequence[VisibleInterventionOption]) -> str:
    payload = [
        {
            "option_id": option.option_id,
            "proposition_id": option.proposition.proposition_id,
            "label": option.normalized_label(),
            "duplicate_group": option.duplicate_group(),
        }
        for option in options
    ]
    return _stable_id("visible-set", {"version": VALUE_ENGINE_VERSION, "options": payload})


def select_visible_signals(
    options: Sequence[VisibleInterventionOption | Mapping[str, Any]],
    *,
    context: Mapping[str, Any] | None = None,
) -> VisibleSignalSelectionDecision:
    started = time.perf_counter()
    rows = [
        option if isinstance(option, VisibleInterventionOption) else VisibleInterventionOption.from_mapping(option)
        for option in options
    ]
    label_by_id = {option.option_id: option.normalized_label() for option in rows}
    kind_by_id = {option.option_id: option.normalized_kind() for option in rows}
    duplicate_by_id = {option.option_id: option.duplicate_group() for option in rows}
    feature_by_id = {option.option_id: option.features.normalized() for option in rows}
    proposal_action_by_id = {
        option.option_id: _proposal_has_concrete_action(option)
        for option in rows
    }
    semantic_tokens_by_id = {
        option.option_id: _semantic_signature_tokens(option)
        for option in rows
    }
    semantic_claim_by_id = {
        option.option_id: _normalized_claim_text(option)
        for option in rows
    }
    hard_gate_reasons = {option.option_id: _option_hard_gate_reason(option) for option in rows}
    net_values = {option.option_id: option_net_value(option) for option in rows}
    ctx = _mapping(context)
    explicit_intent = bool(ctx.get("explicit_diagnosis_or_planning"))
    intent_token = _normalize_token(ctx.get("intent"))
    if intent_token in {"diagnosis", "planning", "architecture", "review"}:
        explicit_intent = True
    high_materiality_duplicates = {
        duplicate_by_id.get(option.option_id, "")
        for option in rows
        if feature_by_id[option.option_id].materiality >= 0.85
        and not hard_gate_reasons.get(option.option_id)
        and duplicate_by_id.get(option.option_id, "")
    }
    actionable_proposal = any(
        label_by_id.get(option.option_id) == "proposal"
        and proposal_action_by_id.get(option.option_id)
        and feature_by_id[option.option_id].actionability >= 0.75
        for option in rows
    )
    live_block_budget = 1
    if explicit_intent:
        live_block_budget += 1
    if len(high_materiality_duplicates) >= 2:
        live_block_budget += 1
    if actionable_proposal:
        live_block_budget += 1
    budget = {
        "live_block_budget": min(MAX_LIVE_BLOCKS, live_block_budget),
        "ambient_block_budget": MAX_AMBIENT_BLOCKS,
        "explicit_diagnosis_or_planning": explicit_intent,
        "high_materiality_distinct_count": len(high_materiality_duplicates),
        "actionable_proposal_present": actionable_proposal,
    }
    eligible_unpruned = [
        option
        for option in rows
        if not hard_gate_reasons.get(option.option_id)
        and _passes_value_floor_cached(
            label=label_by_id.get(option.option_id, ""),
            value=net_values.get(option.option_id, 0.0),
            correctness=feature_by_id[option.option_id].correctness_confidence,
            materiality=feature_by_id[option.option_id].materiality,
        )
    ]
    eligible = sorted(
        eligible_unpruned,
        key=lambda option: (
            -net_values.get(option.option_id, 0.0),
            _LABEL_ORDER.get(label_by_id.get(option.option_id, ""), 99),
            duplicate_by_id.get(option.option_id, ""),
            _normalize_string(option.option_id),
        ),
    )[:MAX_ENUMERATED_OPTIONS]

    def semantic_duplicate_ids(left: VisibleInterventionOption, right: VisibleInterventionOption) -> bool:
        left_id = left.option_id
        right_id = right.option_id
        labels = {label_by_id.get(left_id, ""), label_by_id.get(right_id, "")}
        left_claim = semantic_claim_by_id.get(left_id, "")
        right_claim = semantic_claim_by_id.get(right_id, "")
        if left_claim and left_claim == right_claim:
            return True
        if labels == {"observation", "proposal"} and (
            proposal_action_by_id.get(left_id) or proposal_action_by_id.get(right_id)
        ):
            return False
        left_tokens = semantic_tokens_by_id.get(left_id, set())
        right_tokens = semantic_tokens_by_id.get(right_id, set())
        if not left_tokens or not right_tokens:
            return False
        shared_count = len(left_tokens & right_tokens)
        if shared_count < _SEMANTIC_DUPLICATE_MIN_SHARED_TOKENS:
            return False
        overlap = shared_count / max(1, min(len(left_tokens), len(right_tokens)))
        return overlap >= _SEMANTIC_DUPLICATE_OVERLAP_FLOOR

    semantic_conflict_pairs = frozenset(
        _pair_key(left, right)
        for left, right in itertools.combinations(eligible, 2)
        if semantic_duplicate_ids(left, right)
    )
    duplicate_counts = Counter(
        duplicate_by_id.get(option.option_id, "")
        for option in eligible
        if duplicate_by_id.get(option.option_id, "")
    )
    label_conflict_counts = Counter(
        label_by_id.get(option.option_id, "")
        for option in eligible
        if label_by_id.get(option.option_id, "") in {"observation", "proposal"}
    )
    proposal_count = sum(1 for option in eligible if label_by_id.get(option.option_id, "") == "proposal")
    has_observation_candidate = any(label_by_id.get(option.option_id, "") == "observation" for option in eligible)
    conflict_graph_edges = (
        sum((count * (count - 1)) // 2 for count in duplicate_counts.values() if count > 1)
        + sum((count * (count - 1)) // 2 for count in label_conflict_counts.values() if count > 1)
        + (proposal_count if proposal_count and not has_observation_candidate else 0)
        + len(semantic_conflict_pairs)
    )

    def valid_subset(subset: Sequence[VisibleInterventionOption]) -> bool:
        if len(subset) > int(budget.get("live_block_budget") or 1):
            return False
        labels: set[str] = set()
        duplicate_groups: set[str] = set()
        ambient_count = 0
        has_observation = False
        has_proposal = False
        for option in subset:
            option_id = option.option_id
            label = label_by_id.get(option_id, "")
            if label in labels and label in {"observation", "proposal"}:
                return False
            labels.add(label)
            duplicate = duplicate_by_id.get(option_id, "")
            if duplicate and duplicate in duplicate_groups:
                return False
            duplicate_groups.add(duplicate)
            if kind_by_id.get(option_id, "") == "ambient":
                ambient_count += 1
            if label == "observation":
                has_observation = True
            if label == "proposal":
                has_proposal = True
        if ambient_count > int(budget.get("ambient_block_budget") or MAX_AMBIENT_BLOCKS):
            return False
        for left, right in itertools.combinations(subset, 2):
            if _pair_key(left, right) in semantic_conflict_pairs:
                return False
        return not (has_proposal and not has_observation)

    def subset_utility(subset: Sequence[VisibleInterventionOption]) -> float:
        score = sum(net_values.get(option.option_id, 0.0) for option in subset)
        labels = {label_by_id.get(option.option_id, "") for option in subset}
        if {"observation", "proposal"} <= labels:
            score += 0.04
        if len({duplicate_by_id.get(option.option_id, "") for option in subset}) >= 2:
            score += 0.03
        ambient_label_counts = Counter(
            label_by_id.get(option.option_id, "")
            for option in subset
            if kind_by_id.get(option.option_id, "") == "ambient"
        )
        repeated_ambient_labels = sum(max(0, count - 1) for count in ambient_label_counts.values())
        if repeated_ambient_labels:
            score -= repeated_ambient_labels * 0.025
        if len(subset) > 1:
            score -= (len(subset) - 1) * 0.045
        return round(max(0.0, score), 6)

    def subset_tiebreak_key(subset: Sequence[VisibleInterventionOption]) -> tuple[int, tuple[tuple[float, int, str, str], ...]]:
        return (
            len(subset),
            tuple(
                (
                    -net_values.get(option.option_id, 0.0),
                    _LABEL_ORDER.get(label_by_id.get(option.option_id, ""), 99),
                    duplicate_by_id.get(option.option_id, ""),
                    _normalize_string(option.option_id),
                )
                for option in subset
            ),
        )

    best_subset: tuple[VisibleInterventionOption, ...] = ()
    best_utility = 0.0
    enumerated_subset_count = 0
    valid_subset_count = 0
    for size in range(1, min(len(eligible), int(budget.get("live_block_budget") or 1)) + 1):
        for subset in itertools.combinations(eligible, size):
            enumerated_subset_count += 1
            if not valid_subset(subset):
                continue
            valid_subset_count += 1
            utility = subset_utility(subset)
            if utility > best_utility:
                best_subset = subset
                best_utility = utility
            elif utility == best_utility and subset:
                if subset_tiebreak_key(subset) < subset_tiebreak_key(best_subset):
                    best_subset = subset
    ordered_best_subset = tuple(
        sorted(
            best_subset,
            key=lambda option: (
                _LABEL_ORDER.get(label_by_id.get(option.option_id, ""), 99),
                -net_values.get(option.option_id, 0.0),
                duplicate_by_id.get(option.option_id, ""),
                _normalize_string(option.option_id),
            ),
        )
    )
    selected_ids = {option.option_id for option in ordered_best_subset}
    selected_labels = {label_by_id.get(option.option_id, "") for option in ordered_best_subset}
    selected_duplicates = {duplicate_by_id.get(option.option_id, "") for option in ordered_best_subset if duplicate_by_id.get(option.option_id, "")}
    block_set_id = _selected_block_set_id(ordered_best_subset) if ordered_best_subset else ""
    selected = [
        option.with_value(
            selected_block_set_id=block_set_id,
            net_value=net_values.get(option.option_id, 0.0),
        )
        for option in ordered_best_subset
    ]
    suppressed: list[dict[str, Any]] = []
    for option in rows:
        if option.option_id in selected_ids:
            continue
        reason = hard_gate_reasons.get(option.option_id)
        if not reason and not _passes_value_floor_cached(
            label=label_by_id.get(option.option_id, ""),
            value=net_values.get(option.option_id, 0.0),
            correctness=feature_by_id[option.option_id].correctness_confidence,
            materiality=feature_by_id[option.option_id].materiality,
        ):
            reason = "below_value_floor"
        if (
            not reason
            and label_by_id.get(option.option_id, "") == "proposal"
            and "observation" not in selected_labels
        ):
            reason = "proposal_requires_observation"
        if not reason and duplicate_by_id.get(option.option_id, "") in selected_duplicates:
            reason = "duplicate_visible_proposition"
        if not reason and any(semantic_duplicate_ids(option, selected_option) for selected_option in ordered_best_subset):
            reason = "duplicate_visible_proposition"
        if not reason and label_by_id.get(option.option_id, "") in selected_labels and label_by_id.get(option.option_id, "") in {"observation", "proposal"}:
            reason = "duplicate_visible_label"
        if not reason and kind_by_id.get(option.option_id, "") == "ambient" and label_by_id.get(option.option_id, "") in selected_labels:
            reason = "ambient_label_crowding"
        if not reason:
            reason = "not_in_optimal_visible_set"
        suppressed.append(
            option.with_value(
                selected_block_set_id=block_set_id,
                suppressed_reason=reason,
                net_value=net_values.get(option.option_id, 0.0),
            )
        )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    no_output_reason = "" if selected else "no_high_value_supported_signal"
    return VisibleSignalSelectionDecision(
        selected_candidates=selected,
        suppressed_candidates=suppressed,
        no_output_reason=no_output_reason,
        selected_block_set_id=block_set_id,
        value_engine_version=VALUE_ENGINE_VERSION,
        runtime_posture=RUNTIME_POSTURE,
        metric_summary={
            "candidate_count": len(rows),
            "eligible_count": len(eligible),
            "eligible_unpruned_count": len(eligible_unpruned),
            "hard_gated_count": sum(1 for reason in hard_gate_reasons.values() if reason),
            "evidence_gated_count": sum(1 for reason in hard_gate_reasons.values() if reason in _EVIDENCE_GATE_REASONS),
            "candidate_pruned_count": max(0, len(eligible_unpruned) - len(eligible)),
            "enumerated_subset_count": enumerated_subset_count,
            "valid_subset_count": valid_subset_count,
            "conflict_graph_nodes": len(eligible),
            "conflict_graph_edges": conflict_graph_edges,
            "selected_count": len(selected),
            "selected_utility": round(best_utility, 4),
            "live_block_budget": int(budget.get("live_block_budget") or 1),
            "ambient_block_budget": int(budget.get("ambient_block_budget") or MAX_AMBIENT_BLOCKS),
            "duplicate_visible_block_rate": 0.0,
            "latency_ms": round(max(0.0, elapsed_ms), 4),
        },
        decision_log={
            "runtime_posture": RUNTIME_POSTURE,
            "budget": dict(budget),
            "selected_proposition_ids": [
                _normalize_string(row.get("proposition_id"))
                for row in selected
            ],
            "suppressed": [
                {
                    "proposition_id": _normalize_string(row.get("proposition_id")),
                    "label": _normalize_token(row.get("label")),
                    "reason": _normalize_string(row.get("suppressed_reason")),
                    "net_value": row.get("net_value"),
                }
                for row in suppressed
            ],
        },
    )
