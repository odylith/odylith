from __future__ import annotations

from collections import Counter
from functools import lru_cache
import json
import re
import time
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.intervention_engine.value_engine_selection import select_visible_signals
from odylith.runtime.intervention_engine.value_engine_types import CORPUS_PATH
from odylith.runtime.intervention_engine.value_engine_types import MIN_PUBLISHABLE_DUPLICATE_CASES
from odylith.runtime.intervention_engine.value_engine_types import MIN_PUBLISHABLE_NON_SYNTHETIC_CASES
from odylith.runtime.intervention_engine.value_engine_types import MIN_PUBLISHABLE_NO_OUTPUT_CASES
from odylith.runtime.intervention_engine.value_engine_types import MIN_PUBLISHABLE_POSITIVE_PER_LABEL
from odylith.runtime.intervention_engine.value_engine_types import MIN_PUBLISHABLE_VISIBILITY_CASES
from odylith.runtime.intervention_engine.value_engine_types import RUNTIME_POSTURE
from odylith.runtime.intervention_engine.value_engine_types import VALUE_ENGINE_VERSION
from odylith.runtime.intervention_engine.value_engine_types import VISIBLE_LABELS
from odylith.runtime.intervention_engine.value_engine_types import VisibleInterventionOption
from odylith.runtime.intervention_engine.value_engine_types import _fingerprint
from odylith.runtime.intervention_engine.value_engine_types import _mapping
from odylith.runtime.intervention_engine.value_engine_types import _normalize_string
from odylith.runtime.intervention_engine.value_engine_types import _normalize_token
from odylith.runtime.intervention_engine.value_engine_types import _sequence
from odylith.runtime.intervention_engine.value_engine_types import _string_list


_ALLOWED_CASE_ORIGINS = frozenset(
    {
        "synthetic_gate",
        "casebook_regression",
        "real_transcript",
        "benchmark_trace",
    }
)
_ALLOWED_VISIBILITY_EXPECTATIONS = frozenset(
    {
        "none",
        "visible",
        "failure",
        "force_visible",
        "assistant_visible_fallback",
    }
)
_DUPLICATE_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_:\.-]{1,80}")
_DUPLICATE_TOKEN_STOPWORDS = frozenset(
    {
        "about",
        "after",
        "again",
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
        "does",
        "from",
        "has",
        "have",
        "history",
        "inside",
        "insight",
        "into",
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
        "through",
        "useful",
        "when",
        "where",
        "while",
        "with",
        "without",
    }
)


def load_adjudication_corpus(*, repo_root: Path | str | None = None) -> dict[str, Any]:
    root = Path(repo_root).expanduser().resolve() if repo_root is not None else Path.cwd()
    path = root / CORPUS_PATH
    if not path.exists():
        return {"version": "intervention-value-adjudication-corpus.v1", "cases": []}
    return json.loads(path.read_text(encoding="utf-8"))


def validate_adjudication_corpus(corpus: Mapping[str, Any]) -> None:
    cases = _sequence(corpus.get("cases"))
    if not cases:
        raise ValueError("intervention value corpus has no cases")
    for case in cases:
        if not isinstance(case, Mapping):
            raise ValueError("intervention value corpus case is not a mapping")
        case_id = _normalize_string(case.get("id"))
        if not case_id:
            raise ValueError("intervention value corpus case is missing id")
        required = (
            "origin",
            "source_refs",
            "label_source",
            "adjudicator",
            "rationale",
            "expected_selected_propositions",
            "must_suppress_propositions",
            "duplicate_groups",
            "visibility_expectation",
            "no_output_reason",
            "counts_for_calibration",
        )
        for key in required:
            if key not in case:
                raise ValueError(f"intervention value corpus case {case_id} is missing {key}")
        origin = _normalize_token(case.get("origin"))
        if origin not in _ALLOWED_CASE_ORIGINS:
            raise ValueError(f"intervention value corpus case {case_id} has invalid origin: {origin}")
        if not _string_list(case.get("source_refs")):
            raise ValueError(f"intervention value corpus case {case_id} is missing source_refs provenance")
        for key in ("label_source", "adjudicator", "rationale"):
            if not _normalize_string(case.get(key)):
                raise ValueError(f"intervention value corpus case {case_id} is missing {key} provenance")
        visibility = _normalize_token(case.get("visibility_expectation"))
        if visibility not in _ALLOWED_VISIBILITY_EXPECTATIONS:
            raise ValueError(f"intervention value corpus case {case_id} has invalid visibility expectation: {visibility}")
        if origin == "synthetic_gate" and bool(case.get("counts_for_calibration")):
            raise ValueError(f"intervention value corpus case {case_id} lets synthetic data count for calibration")
        options = [
            VisibleInterventionOption.from_mapping(row)
            for row in _sequence(case.get("options"))
            if isinstance(row, Mapping)
        ]
        if not options:
            raise ValueError(f"intervention value corpus case {case_id} has no options")
        for option in _sequence(case.get("options")):
            if not isinstance(option, Mapping):
                continue
            if not isinstance(option.get("proposition"), Mapping):
                raise ValueError(f"intervention value corpus case {case_id} has an option without proposition provenance")
            if not isinstance(option.get("value_features"), Mapping):
                raise ValueError(f"intervention value corpus case {case_id} has an option without value_features")
        proposition_ids = {option.proposition.proposition_id for option in options}
        expected = set(_string_list(case.get("expected_selected_propositions")))
        suppressed = set(_string_list(case.get("must_suppress_propositions")))
        unknown = (expected | suppressed) - proposition_ids
        if unknown:
            raise ValueError(f"intervention value corpus case {case_id} references unknown propositions: {sorted(unknown)}")
        overlap = expected & suppressed
        if overlap:
            raise ValueError(f"intervention value corpus case {case_id} contradicts labels: {sorted(overlap)}")


def _rate(count: float, total: float) -> float:
    return round(count / total, 4) if total else 1.0


def _p95(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95)))
    return round(ordered[index], 4)


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


def _candidate_claim_text(row: Mapping[str, Any]) -> str:
    proposition = _mapping(row.get("proposition"))
    return _normalize_string(
        proposition.get("claim_text")
        or row.get("plain_text")
        or row.get("markdown_text")
    ).lower()


def _selected_semantic_duplicate_failure(rows: Sequence[Mapping[str, Any]]) -> bool:
    signatures: list[tuple[str, bool, str, set[str]]] = []
    for row in rows:
        proposition = _mapping(row.get("proposition"))
        tokens = {
            _normalize_token(token)
            for token in _string_list(proposition.get("semantic_signature"))
            if len(_normalize_token(token)) >= 2
            and _normalize_token(token) not in _DUPLICATE_TOKEN_STOPWORDS
        }
        tokens.update(
            _duplicate_text_tokens(
                proposition.get("claim_text"),
                row.get("plain_text"),
                row.get("markdown_text"),
            )
        )
        if tokens:
            signatures.append(
                (
                    _normalize_token(row.get("label") or row.get("proposed_label")),
                    bool(_sequence(_mapping(row.get("action_payload")).get("actions"))),
                    _candidate_claim_text(row),
                    tokens,
                )
            )
    for index, (left_label, left_has_action, left_claim, left) in enumerate(signatures):
        for right_label, right_has_action, right_claim, right in signatures[index + 1 :]:
            if left_claim and left_claim == right_claim:
                return True
            if {
                left_label,
                right_label,
            } == {"observation", "proposal"} and (left_has_action or right_has_action):
                continue
            shared_count = len(left & right)
            if shared_count < 2:
                continue
            overlap = shared_count / max(1, min(len(left), len(right)))
            if overlap >= 0.75:
                return True
    return False


def corpus_quality_summary(corpus: Mapping[str, Any]) -> dict[str, Any]:
    validate_adjudication_corpus(corpus)
    cases = [case for case in _sequence(corpus.get("cases")) if isinstance(case, Mapping)]
    non_synthetic = [
        case
        for case in cases
        if _normalize_token(case.get("origin")) != "synthetic_gate"
    ]
    positive_per_label = {label: 0 for label in VISIBLE_LABELS}
    no_output_cases = 0
    duplicate_cases = 0
    visibility_cases = 0
    for case in non_synthetic:
        expected = set(_string_list(case.get("expected_selected_propositions")))
        if not expected:
            no_output_cases += 1
        if _sequence(case.get("duplicate_groups")):
            duplicate_cases += 1
        if _normalize_token(case.get("visibility_expectation")) in {"failure", "force_visible", "assistant_visible_fallback"}:
            visibility_cases += 1
        options_by_prop = {
            option.proposition.proposition_id: option
            for option in (
                VisibleInterventionOption.from_mapping(row)
                for row in _sequence(case.get("options"))
                if isinstance(row, Mapping)
            )
        }
        for proposition_id in expected:
            option = options_by_prop.get(proposition_id)
            if option is not None and option.normalized_label() in positive_per_label:
                positive_per_label[option.normalized_label()] += 1
    publishable = (
        len(non_synthetic) >= MIN_PUBLISHABLE_NON_SYNTHETIC_CASES
        and min(positive_per_label.values()) >= MIN_PUBLISHABLE_POSITIVE_PER_LABEL
        and no_output_cases >= MIN_PUBLISHABLE_NO_OUTPUT_CASES
        and duplicate_cases >= MIN_PUBLISHABLE_DUPLICATE_CASES
        and visibility_cases >= MIN_PUBLISHABLE_VISIBILITY_CASES
    )
    return {
        "quality_state": "publishable" if publishable else "bootstrap",
        "publishable": publishable,
        "case_count": len(cases),
        "non_synthetic_case_count": len(non_synthetic),
        "positive_per_label": positive_per_label,
        "no_output_case_count": no_output_cases,
        "duplicate_case_count": duplicate_cases,
        "visibility_failure_case_count": visibility_cases,
        "density_requirements": {
            "non_synthetic_cases": MIN_PUBLISHABLE_NON_SYNTHETIC_CASES,
            "positive_per_label": MIN_PUBLISHABLE_POSITIVE_PER_LABEL,
            "no_output_cases": MIN_PUBLISHABLE_NO_OUTPUT_CASES,
            "duplicate_cases": MIN_PUBLISHABLE_DUPLICATE_CASES,
            "visibility_failure_cases": MIN_PUBLISHABLE_VISIBILITY_CASES,
        },
    }


def evaluate_adjudication_corpus(corpus: Mapping[str, Any]) -> dict[str, Any]:
    validate_adjudication_corpus(corpus)
    cases = [case for case in _sequence(corpus.get("cases")) if isinstance(case, Mapping)]
    selected_total = 0
    selected_correct = 0
    expected_total = 0
    expected_found = 0
    must_suppress_total = 0
    must_suppress_correct = 0
    duplicate_failures = 0
    visibility_total = 0
    visibility_found = 0
    no_output_total = 0
    no_output_correct = 0
    origin_counts: Counter[str] = Counter()
    calibration_case_count = 0
    synthetic_case_count = 0
    latencies: list[float] = []
    for case in cases:
        origin = _normalize_token(case.get("origin"))
        origin_counts[origin] += 1
        if origin == "synthetic_gate":
            synthetic_case_count += 1
        if bool(case.get("counts_for_calibration")) and origin != "synthetic_gate":
            calibration_case_count += 1
        options = [
            VisibleInterventionOption.from_mapping(row)
            for row in _sequence(case.get("options"))
            if isinstance(row, Mapping)
        ]
        started = time.perf_counter()
        decision = select_visible_signals(
            options,
            context=_mapping(case.get("selection_context")),
        )
        latencies.append((time.perf_counter() - started) * 1000.0)
        selected = {
            _normalize_string(row.get("proposition_id"))
            for row in decision.selected_candidates
        }
        expected = set(_string_list(case.get("expected_selected_propositions")))
        selected_total += len(selected)
        selected_correct += len(selected & expected)
        expected_total += len(expected)
        expected_found += len(selected & expected)
        must_suppress = set(_string_list(case.get("must_suppress_propositions")))
        must_suppress_total += len(must_suppress)
        must_suppress_correct += len(must_suppress - selected)
        duplicate_groups = [
            _normalize_string(row.get("duplicate_group"))
            for row in decision.selected_candidates
            if _normalize_string(row.get("duplicate_group"))
        ]
        if len(duplicate_groups) != len(set(duplicate_groups)) or _selected_semantic_duplicate_failure(decision.selected_candidates):
            duplicate_failures += 1
        if _normalize_token(case.get("visibility_expectation")) in {"failure", "force_visible", "assistant_visible_fallback"}:
            visibility_total += 1
            if selected & expected:
                visibility_found += 1
        if not expected:
            no_output_total += 1
            if not selected and _normalize_token(case.get("no_output_reason")) == _normalize_token(decision.no_output_reason):
                no_output_correct += 1
    precision = _rate(selected_correct, selected_total)
    recall = _rate(expected_found, expected_total)
    beta = 0.5
    f_beta = (
        round((1 + beta**2) * precision * recall / ((beta**2 * precision) + recall), 4)
        if precision or recall
        else 0.0
    )
    return {
        "version": VALUE_ENGINE_VERSION,
        "runtime_posture": RUNTIME_POSTURE,
        "corpus_fingerprint": _fingerprint(dict(corpus)),
        "case_count": len(cases),
        "precision": precision,
        "recall": recall,
        "f_beta": f_beta,
        "must_suppress_accuracy": _rate(must_suppress_correct, must_suppress_total),
        "duplicate_visible_block_rate": _rate(duplicate_failures, len(cases)),
        "visibility_failure_recall": _rate(visibility_found, visibility_total),
        "no_output_accuracy": _rate(no_output_correct, no_output_total),
        "latency_p95_ms": _p95(latencies),
        "origin_counts": dict(sorted(origin_counts.items())),
        "calibration_case_count": calibration_case_count,
        "synthetic_case_count": synthetic_case_count,
        "corpus_quality": corpus_quality_summary(corpus),
    }


@lru_cache(maxsize=1)
def runtime_calibration_publishable() -> bool:
    return False


def advisory_report(corpus: Mapping[str, Any]) -> dict[str, Any]:
    metrics = evaluate_adjudication_corpus(corpus)
    return {
        "family": "intervention_value_engine",
        "status": "pass",
        "runtime_posture": RUNTIME_POSTURE,
        "advisory_to_live_proof": True,
        "metric_summary": metrics,
        "proof_claims": {
            "duplicate_visible_block_rate": metrics["duplicate_visible_block_rate"],
            "visible_block_precision": metrics["precision"],
            "must_surface_recall": metrics["recall"],
            "must_suppress_accuracy": metrics["must_suppress_accuracy"],
            "visibility_failure_recall": metrics["visibility_failure_recall"],
            "selector_latency_p95_ms": metrics["latency_p95_ms"],
            "corpus_quality_state": metrics["corpus_quality"]["quality_state"],
            "calibration_publishable": metrics["corpus_quality"]["publishable"],
        },
    }
