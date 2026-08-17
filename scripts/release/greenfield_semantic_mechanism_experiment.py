"""Compare authored semantic mechanisms without inferring labels from prose."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from itertools import combinations
import hashlib
import json
from pathlib import Path
import statistics
import sys
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import semantic_intent_authoring_contract


EXPERIMENT_VERSION = "odylith.greenfield.semantic-mechanism-experiment.v1"
REPORT_VERSION = "odylith.greenfield.semantic-mechanism-report.v1"
RESOURCE_METRICS = (
    "mean_latency_ms", "mean_cost_usd", "mean_prompt_tokens", "mean_authoring_passes", "mean_architecture_paths"
)
QUALITY_WEIGHTS = {
    "validator_acceptance": 0.10,
    "fact_precision": 0.15,
    "fact_recall": 0.15,
    "relation_precision": 0.10,
    "relation_recall": 0.10,
    "relation_domain_range": 0.10,
    "equivalent_source_convergence": 0.15,
    "package_utility": 0.075,
    "package_differentiation": 0.075,
}
QUALITY_METRICS = tuple(QUALITY_WEIGHTS)
OUTCOME_WEIGHT, EFFICIENCY_WEIGHT = 0.85, 0.15


def evaluate_mechanism_experiment(experiment: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic go/no-go comparison for all three mechanisms."""

    payload = _mapping(experiment, "experiment")
    _exact_keys(payload, {"version", "thresholds", "mechanisms"}, "experiment")
    if payload.get("version") != EXPERIMENT_VERSION:
        raise ValueError("semantic mechanism experiment uses an unsupported version")
    thresholds = _thresholds(payload.get("thresholds"))
    mechanisms = _mechanism_inputs(payload.get("mechanisms"))
    reports = [_score_mechanism(name=name, runs=runs, thresholds=thresholds) for name, runs in mechanisms.items()]
    decision = _decision(reports=reports, thresholds=thresholds)
    canonical_input = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return {
        "version": REPORT_VERSION,
        "input_sha256": hashlib.sha256(canonical_input.encode("utf-8")).hexdigest(),
        "mechanisms_compared": list(mechanisms),
        "thresholds": thresholds,
        "ranking_contract": {
            "quality_weights": QUALITY_WEIGHTS,
            "outcome_weight": OUTCOME_WEIGHT,
            "efficiency_weight": EFFICIENCY_WEIGHT,
            "winner_requires_all_go_no_gates": True,
            "winner_requires_minimum_score_margin": thresholds["minimum_winner_margin"],
        },
        "mechanism_reports": reports,
        "decision": decision,
    }

def _thresholds(value: Any) -> dict[str, Any]:
    thresholds = _mapping(value, "thresholds")
    integer_minimums = {
        "minimum_runs_per_mechanism": 1,
        "minimum_equivalence_pairs": 1,
        "minimum_distinct_case_families": 2,
        "minimum_recurring_failure_count": 2,
        "maximum_regression_count": 0,
    }
    rate_names = ("minimum_winner_margin", "maximum_unsupported_addition_rate")
    _exact_keys(
        thresholds,
        set(integer_minimums) | set(rate_names) | {"quality_floors", "resource_ceilings"},
        "thresholds",
    )
    quality_floors = _mapping(thresholds.get("quality_floors"), "quality_floors")
    resource_ceilings = _mapping(thresholds.get("resource_ceilings"), "resource_ceilings")
    _exact_keys(quality_floors, set(QUALITY_METRICS), "quality_floors")
    _exact_keys(resource_ceilings, set(RESOURCE_METRICS), "resource_ceilings")
    return {
        **{
            name: _integer(thresholds.get(name), name, minimum=minimum)
            for name, minimum in integer_minimums.items()
        },
        **{name: _rate(thresholds.get(name), name) for name in rate_names},
        "quality_floors": {
            name: _rate(quality_floors.get(name), f"quality_floors.{name}")
            for name in QUALITY_METRICS
        },
        "resource_ceilings": {
            name: _number(resource_ceilings.get(name), f"resource_ceilings.{name}")
            for name in RESOURCE_METRICS
        },
    }

def _mechanism_inputs(value: Any) -> dict[str, list[Mapping[str, Any]]]:
    rows = _sequence(value, "mechanisms")
    if not 2 <= len(rows) <= 8:
        raise ValueError("semantic mechanism experiment requires 2 to 8 alternatives")
    by_name: dict[str, list[Mapping[str, Any]]] = {}
    for index, raw in enumerate(rows):
        row = _mapping(raw, f"mechanisms[{index}]")
        _exact_keys(row, {"name", "runs"}, f"mechanisms[{index}]")
        name = _nonempty_text(row.get("name"), f"mechanisms[{index}].name")
        if name in by_name:
            raise ValueError(f"semantic mechanism is duplicated: {name}")
        by_name[name] = _mapped_rows(row.get("runs"), f"{name}.runs")
    return by_name

def _score_mechanism(
    *,
    name: str,
    runs: Sequence[Mapping[str, Any]],
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    scored_runs = [_score_run(run, name=name, index=index) for index, run in enumerate(runs)]
    case_ids = [str(run["case_id"]) for run in scored_runs]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError(f"{name} contains duplicate case IDs")
    fact_totals = _sum_counts(scored_runs, "fact_counts")
    relation_totals = _sum_counts(scored_runs, "relation_counts")
    domain_totals = _sum_counts(scored_runs, "relation_domain_range_counts")
    convergence = _equivalent_source_convergence(scored_runs)
    case_families = sorted({str(run["case_family"]) for run in scored_runs})
    run_count = len(scored_runs)
    quality = {
        "validator_acceptance": _fraction(sum(bool(run["validator_accepted"]) for run in scored_runs), run_count),
        "fact_precision": _fraction(fact_totals["matched"], fact_totals["observed"]),
        "fact_recall": _fraction(fact_totals["matched"], fact_totals["expected"]),
        "relation_precision": _fraction(relation_totals["matched"], relation_totals["observed"]),
        "relation_recall": _fraction(relation_totals["matched"], relation_totals["expected"]),
        "relation_domain_range": _fraction(domain_totals["valid"], domain_totals["total"]),
        "equivalent_source_convergence": convergence["score"],
        "package_utility": _mean([run["package_utility"] for run in scored_runs]),
        "package_differentiation": _mean([run["package_differentiation"] for run in scored_runs]),
    }
    resources = {
        "mean_latency_ms": _mean([run["performance"]["latency_ms"] for run in scored_runs]),
        "mean_cost_usd": _mean([run["performance"]["cost_usd"] for run in scored_runs]),
        "mean_prompt_tokens": _mean([run["complexity"]["prompt_tokens"] for run in scored_runs]),
        "mean_authoring_passes": _mean([run["complexity"]["authoring_passes"] for run in scored_runs]),
        "mean_architecture_paths": _mean([run["complexity"]["architecture_paths"] for run in scored_runs]),
    }
    unsupported_count = fact_totals["unsupported"] + relation_totals["unsupported"]
    observed_claim_count = fact_totals["observed"] + relation_totals["observed"]
    unsupported_rate = _fraction(unsupported_count, observed_claim_count)
    regression_count = sum(int(run["regression_count"]) for run in scored_runs)
    evidence_checks = [
        _check("run_count", ">=", run_count, int(thresholds["minimum_runs_per_mechanism"])),
        _check("equivalence_pair_count", ">=", convergence["pair_count"], int(thresholds["minimum_equivalence_pairs"])),
        _check("distinct_case_family_count", ">=", len(case_families), int(thresholds["minimum_distinct_case_families"])),
    ]
    gate_checks = evidence_checks + [
        _check(metric, ">=", quality[metric], thresholds["quality_floors"][metric])
        for metric in QUALITY_METRICS
    ] + [
        _check("unsupported_addition_rate", "<=", unsupported_rate, thresholds["maximum_unsupported_addition_rate"]),
        _check("regression_count", "<=", regression_count, thresholds["maximum_regression_count"]),
    ] + [
        _check(metric, "<=", resources[metric], thresholds["resource_ceilings"][metric])
        for metric in RESOURCE_METRICS
    ]
    quality_score = sum(quality[metric] * QUALITY_WEIGHTS[metric] for metric in QUALITY_METRICS)
    efficiency_scores = {
        metric: _lower_is_better_score(resources[metric], thresholds["resource_ceilings"][metric])
        for metric in RESOURCE_METRICS
    }
    efficiency_score = _mean(list(efficiency_scores.values()))
    final_score = (quality_score * OUTCOME_WEIGHT) + (efficiency_score * EFFICIENCY_WEIGHT)
    failure_counts = {
        "validator_rejection": sum(not run["validator_accepted"] for run in scored_runs),
        "fact_oracle_failure": sum(
            run["fact_precision"] < thresholds["quality_floors"]["fact_precision"]
            or run["fact_recall"] < thresholds["quality_floors"]["fact_recall"]
            for run in scored_runs
        ),
        "unsupported_additions": sum(run["unsupported_count"] > 0 for run in scored_runs),
        "relation_contract_failure": sum(
            run["relation_domain_range"] < thresholds["quality_floors"]["relation_domain_range"]
            for run in scored_runs
        ),
        "relation_oracle_failure": sum(
            run["relation_precision"] < thresholds["quality_floors"]["relation_precision"]
            or run["relation_recall"] < thresholds["quality_floors"]["relation_recall"]
            for run in scored_runs
        ),
        "package_utility_failure": sum(
            run["package_utility"] < thresholds["quality_floors"]["package_utility"] for run in scored_runs
        ),
        "package_differentiation_failure": sum(
            run["package_differentiation"] < thresholds["quality_floors"]["package_differentiation"]
            for run in scored_runs
        ),
        "cross_surface_regression": sum(run["regression_count"] > 0 for run in scored_runs),
        "equivalent_source_drift": convergence["failed_pair_count"],
    }
    triggers = _replacement_triggers(failure_counts=failure_counts, resources=resources, thresholds=thresholds)
    return {
        "mechanism": name,
        "run_count": run_count,
        "development_corpus_evidence": {"case_families": case_families, "distinct_case_family_count": len(case_families)},
        "validator_acceptance": _rounded(quality["validator_acceptance"]),
        "semantic_fidelity": {"precision": _rounded(quality["fact_precision"]), "recall": _rounded(quality["fact_recall"])},
        "relation_correctness": {
            "precision": _rounded(quality["relation_precision"]),
            "recall": _rounded(quality["relation_recall"]),
            "domain_range": _rounded(quality["relation_domain_range"]),
        },
        "equivalent_source_convergence": _rounded(quality["equivalent_source_convergence"]),
        "package_quality": {"utility": _rounded(quality["package_utility"]), "differentiation": _rounded(quality["package_differentiation"])},
        "claim_counts": {
            "facts": fact_totals,
            "relations": relation_totals,
            "relation_domain_range": domain_totals,
            "unsupported_total": unsupported_count,
            "unsupported_addition_rate": _rounded(unsupported_rate),
        },
        "equivalent_source_evidence": convergence,
        "performance": {key: _rounded(resources[key]) for key in ("mean_latency_ms", "mean_cost_usd")},
        "implementation_complexity": {key: _rounded(resources[key]) for key in RESOURCE_METRICS[2:]},
        "regression_count": regression_count,
        "evidence_ready": all(check["passed"] for check in evidence_checks),
        "go_no": "go" if all(check["passed"] for check in gate_checks) else "no_go",
        "gate_checks": gate_checks,
        "failure_counts": failure_counts,
        "replacement_triggers": triggers,
        "scores": {
            "outcome": _rounded(quality_score),
            "efficiency": _rounded(efficiency_score),
            "efficiency_dimensions": {
                key: _rounded(value) for key, value in efficiency_scores.items()
            },
            "final": _rounded(final_score),
        },
    }

def _score_run(run: Mapping[str, Any], *, name: str, index: int) -> dict[str, Any]:
    context = f"{name}.runs[{index}]"
    required = {
        "case_id",
        "case_family",
        "equivalence_group",
        "packet",
        "fact_claims",
        "oracle",
        "package_evidence",
        "validator",
        "performance",
        "complexity",
    }
    _exact_keys(run, required, context)
    case_id = _nonempty_text(run.get("case_id"), f"{context}.case_id")
    case_family = _nonempty_text(run.get("case_family"), f"{context}.case_family")
    equivalence_group = _nonempty_text(
        run.get("equivalence_group"), f"{context}.equivalence_group"
    )
    packet = _mapping(run.get("packet"), f"{context}.packet")
    semantic_intent = _mapping(packet.get("semantic_intent"), f"{context}.packet.semantic_intent")
    intent_context = f"{context}.packet.semantic_intent"
    facts = _mapped_rows(semantic_intent.get("facts"), f"{intent_context}.facts")
    relations = _mapped_rows(semantic_intent.get("relations"), f"{intent_context}.relations")
    facts_by_id: dict[str, Mapping[str, Any]] = {}
    for fact in facts:
        fact_id = _nonempty_text(fact.get("fact_id"), f"{context}.fact.fact_id")
        if fact_id in facts_by_id:
            raise ValueError(f"{context} contains duplicate fact ID: {fact_id}")
        facts_by_id[fact_id] = fact
    claims = _fact_claims(run.get("fact_claims"), facts_by_id=facts_by_id, context=context)
    oracle = _mapping(run.get("oracle"), f"{context}.oracle")
    _exact_keys(oracle, {"facts", "relations"}, f"{context}.oracle")
    oracle_facts = _oracle_facts(oracle.get("facts"), context=context)
    oracle_relations = _oracle_relations(oracle.get("relations"), context=context)
    fact_score = _score_facts(
        facts=facts,
        facts_by_id=facts_by_id,
        claims=claims,
        oracle_facts=oracle_facts,
        context=context,
    )
    relation_score = _score_relations(
        relations=relations,
        facts_by_id=facts_by_id,
        claim_key_by_fact_id=claims,
        valid_fact_keys=fact_score["valid_fact_keys"],
        oracle_relations=oracle_relations,
        context=context,
    )
    package_score = _score_package(run.get("package_evidence"), context=context)
    validator = _mapping(run.get("validator"), f"{context}.validator")
    _exact_keys(validator, {"accepted", "regression_count"}, f"{context}.validator")
    if not isinstance(validator.get("accepted"), bool):
        raise ValueError(f"{context}.validator.accepted must be boolean")
    performance = _numeric_record(
        run.get("performance"),
        keys=("latency_ms", "cost_usd"),
        context=f"{context}.performance",
    )
    complexity = _numeric_record(
        run.get("complexity"),
        keys=("prompt_tokens", "authoring_passes", "architecture_paths"),
        context=f"{context}.complexity",
    )
    return {
        "case_id": case_id,
        "case_family": case_family,
        "equivalence_group": equivalence_group,
        "validator_accepted": validator["accepted"],
        "regression_count": _integer(
            validator.get("regression_count"), f"{context}.validator.regression_count", minimum=0
        ),
        "fact_counts": fact_score["counts"],
        "relation_counts": relation_score["counts"],
        "relation_domain_range_counts": relation_score["domain_range_counts"],
        "fact_precision": _fraction(fact_score["counts"]["matched"], len(facts)),
        "fact_recall": _fraction(
            fact_score["counts"]["matched"], fact_score["counts"]["expected"]
        ),
        "relation_precision": _fraction(
            relation_score["counts"]["matched"], len(relations)
        ),
        "relation_recall": _fraction(
            relation_score["counts"]["matched"], relation_score["counts"]["expected"]
        ),
        "relation_domain_range": _fraction(
            relation_score["domain_range_counts"]["valid"], len(relations)
        ),
        "unsupported_count": (
            fact_score["counts"]["unsupported"] + relation_score["counts"]["unsupported"]
        ),
        "package_utility": package_score["utility"],
        "package_differentiation": package_score["differentiation"],
        "performance": performance,
        "complexity": complexity,
        "semantic_signature": {
            "facts": fact_score["signature"],
            "relations": relation_score["signature"],
        },
    }

def _fact_claims(
    value: Any,
    *,
    facts_by_id: Mapping[str, Mapping[str, Any]],
    context: str,
) -> dict[str, str]:
    claims: dict[str, str] = {}
    for index, raw in enumerate(_sequence(value, f"{context}.fact_claims")):
        claim = _mapping(raw, f"{context}.fact_claims[{index}]")
        _exact_keys(claim, {"fact_id", "semantic_key"}, f"{context}.fact_claims[{index}]")
        fact_id = _nonempty_text(claim.get("fact_id"), f"{context}.fact_claims[{index}].fact_id")
        semantic_key = _nonempty_text(claim.get("semantic_key"), f"{context}.fact_claims[{index}].semantic_key")
        if fact_id not in facts_by_id:
            raise ValueError(f"{context} fact claim references unknown fact: {fact_id}")
        if fact_id in claims:
            raise ValueError(f"{context} contains duplicate fact claim: {fact_id}")
        claims[fact_id] = semantic_key
    return claims

def _oracle_facts(value: Any, *, context: str) -> dict[str, Mapping[str, Any]]:
    oracle: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(_sequence(value, f"{context}.oracle.facts")):
        fact = _mapping(raw, f"{context}.oracle.facts[{index}]")
        allowed = {"semantic_key", "kind", "source_refs", "required_fields"}
        if not {"semantic_key", "kind", "source_refs"} <= set(fact) or not set(fact) <= allowed:
            raise ValueError(f"{context}.oracle.facts[{index}] has invalid fields")
        semantic_key = _nonempty_text(fact.get("semantic_key"), f"{context}.oracle.facts[{index}].semantic_key")
        if semantic_key in oracle:
            raise ValueError(f"{context} contains duplicate oracle fact: {semantic_key}")
        _nonempty_text(fact.get("kind"), f"{context}.oracle.facts[{index}].kind")
        _source_ref_signature(fact.get("source_refs"), f"{context}.oracle.facts[{index}]")
        if "required_fields" in fact:
            _mapping(fact.get("required_fields"), f"{context}.oracle.facts[{index}].required_fields")
        oracle[semantic_key] = fact
    return oracle

def _oracle_relations(value: Any, *, context: str) -> dict[
    tuple[str, str, str], tuple[tuple[str, str, int], ...]
]:
    relations: dict[tuple[str, str, str], tuple[tuple[str, str, int], ...]] = {}
    rows = _sequence(value, f"{context}.oracle.relations")
    for index, raw in enumerate(rows):
        relation = _mapping(raw, f"{context}.oracle.relations[{index}]")
        _exact_keys(relation, {"kind", "subject_key", "object_key", "source_refs"}, f"{context}.oracle.relations[{index}]")
        key = (
            _nonempty_text(relation.get("kind"), f"{context}.oracle.relations[{index}].kind"),
            _nonempty_text(relation.get("subject_key"), f"{context}.oracle.relations[{index}].subject_key"),
            _nonempty_text(relation.get("object_key"), f"{context}.oracle.relations[{index}].object_key"),
        )
        if key in relations:
            raise ValueError(f"{context} contains duplicate oracle relation: {key}")
        relations[key] = _source_ref_signature(relation.get("source_refs"), f"{context}.oracle.relations[{index}]")
    return relations

def _score_facts(
    *,
    facts: Sequence[Mapping[str, Any]],
    facts_by_id: Mapping[str, Mapping[str, Any]],
    claims: Mapping[str, str],
    oracle_facts: Mapping[str, Mapping[str, Any]],
    context: str,
) -> dict[str, Any]:
    matched_keys: set[str] = set()
    valid_fact_keys: dict[str, str] = {}
    signature: list[str] = []
    for fact_id, fact in facts_by_id.items():
        semantic_key = claims.get(fact_id, f"unbound:{fact_id}")
        kind = str(fact.get("kind") or "")
        signature.append(f"fact|{semantic_key}|{kind}")
        actual_refs = _source_ref_signature(fact.get("source_refs"), f"{context}.fact[{fact_id}]")
        expected = oracle_facts.get(semantic_key)
        if expected is None or semantic_key in matched_keys:
            continue
        if kind != str(expected.get("kind") or ""):
            continue
        expected_refs = _source_ref_signature(expected.get("source_refs"), f"{context}.oracle[{semantic_key}]")
        if actual_refs != expected_refs:
            continue
        required_fields = _mapping(expected.get("required_fields", {}), "required_fields")
        if any(fact.get(field) != required for field, required in required_fields.items()):
            continue
        matched_keys.add(semantic_key)
        valid_fact_keys[fact_id] = semantic_key
    matched = len(matched_keys)
    return {
        "counts": {
            "matched": matched,
            "observed": len(facts),
            "expected": len(oracle_facts),
            "unsupported": len(facts) - matched,
            "missing": len(oracle_facts) - matched,
        },
        "valid_fact_keys": valid_fact_keys,
        "signature": sorted(signature),
    }

def _score_relations(
    *,
    relations: Sequence[Mapping[str, Any]],
    facts_by_id: Mapping[str, Mapping[str, Any]],
    claim_key_by_fact_id: Mapping[str, str],
    valid_fact_keys: Mapping[str, str],
    oracle_relations: Mapping[tuple[str, str, str], tuple[tuple[str, str, int], ...]],
    context: str,
) -> dict[str, Any]:
    relation_contracts = semantic_intent_authoring_contract()["relation_contracts"]
    matched: set[tuple[str, str, str]] = set()
    valid_domain_range = 0
    signature: list[str] = []
    for index, relation in enumerate(relations):
        kind = _nonempty_text(relation.get("kind"), f"{context}.relation[{index}].kind")
        subject_id = _nonempty_text(relation.get("subject_id"), f"{context}.relation[{index}].subject_id")
        object_id = _nonempty_text(relation.get("object_id"), f"{context}.relation[{index}].object_id")
        subject_key = claim_key_by_fact_id.get(subject_id, f"unbound:{subject_id}")
        object_key = claim_key_by_fact_id.get(object_id, f"unbound:{object_id}")
        relation_key = (kind, subject_key, object_key)
        signature.append("relation|" + "|".join(relation_key))
        actual_refs = _source_ref_signature(relation.get("source_refs"), f"{context}.relation[{index}]")
        contract = relation_contracts.get(kind)
        subject_fact = facts_by_id.get(subject_id)
        object_fact = facts_by_id.get(object_id)
        if (
            isinstance(contract, Mapping)
            and subject_fact is not None
            and object_fact is not None
            and subject_fact.get("kind") in contract.get("subject_kinds", ())
            and object_fact.get("kind") in contract.get("object_kinds", ())
        ):
            valid_domain_range += 1
        if (
            subject_id in valid_fact_keys
            and object_id in valid_fact_keys
            and relation_key in oracle_relations
            and relation_key not in matched
            and actual_refs == oracle_relations[relation_key]
        ):
            matched.add(relation_key)
    return {
        "counts": {
            "matched": len(matched),
            "observed": len(relations),
            "expected": len(oracle_relations),
            "unsupported": len(relations) - len(matched),
            "missing": len(oracle_relations) - len(matched),
        },
        "domain_range_counts": {"valid": valid_domain_range, "total": len(relations)},
        "signature": sorted(signature),
    }

def _score_package(value: Any, *, context: str) -> dict[str, float]:
    package = _mapping(value, f"{context}.package_evidence")
    _exact_keys(
        package,
        {
            "utility_checks",
            "component_responsibility_keys",
            "minimum_distinct_component_responsibilities",
        },
        f"{context}.package_evidence",
    )
    checks = _mapping(package.get("utility_checks"), f"{context}.package_evidence.utility_checks")
    if not checks or any(not isinstance(value, bool) for value in checks.values()):
        raise ValueError(f"{context}.package_evidence.utility_checks must be non-empty booleans")
    responsibilities = [
        _nonempty_text(value, f"{context}.package_evidence.component_responsibility_keys")
        for value in _sequence(
            package.get("component_responsibility_keys"),
            f"{context}.package_evidence.component_responsibility_keys",
        )
    ]
    minimum = _integer(
        package.get("minimum_distinct_component_responsibilities"),
        f"{context}.package_evidence.minimum_distinct_component_responsibilities",
        minimum=1,
    )
    unique_count = len(set(responsibilities))
    denominator = max(len(responsibilities), minimum)
    return {
        "utility": _fraction(sum(checks.values()), len(checks)),
        "differentiation": _fraction(unique_count, denominator),
    }

def _equivalent_source_convergence(runs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for run in runs:
        groups.setdefault(str(run["equivalence_group"]), []).append(run)
    pair_scores: list[float] = []
    failed_pair_count = 0
    exact_pair_count = 0
    for group_runs in groups.values():
        for left, right in combinations(group_runs, 2):
            left_claims = set(left["semantic_signature"]["facts"]) | set(
                left["semantic_signature"]["relations"]
            )
            right_claims = set(right["semantic_signature"]["facts"]) | set(
                right["semantic_signature"]["relations"]
            )
            union = left_claims | right_claims
            score = 1.0 if not union else len(left_claims & right_claims) / len(union)
            pair_scores.append(score)
            if score == 1.0:
                exact_pair_count += 1
            else:
                failed_pair_count += 1
    return {
        "pair_count": len(pair_scores),
        "exact_pair_count": exact_pair_count,
        "failed_pair_count": failed_pair_count,
        "exact_pair_rate": _rounded(_fraction(exact_pair_count, len(pair_scores))),
        "score": _rounded(_mean(pair_scores)),
    }

def _replacement_triggers(
    *,
    failure_counts: Mapping[str, int],
    resources: Mapping[str, float],
    thresholds: Mapping[str, Any],
) -> list[dict[str, Any]]:
    recurring = int(thresholds["minimum_recurring_failure_count"])
    triggers = [
        {
            "id": f"recurring_{name}",
            "observed_count": count,
            "trigger_count": recurring,
        }
        for name, count in failure_counts.items()
        if count >= recurring
    ]
    for metric in RESOURCE_METRICS:
        observed = resources[metric]
        ceiling = thresholds["resource_ceilings"][metric]
        if observed > ceiling:
            triggers.append(
                {
                    "id": f"{metric}_ceiling_exceeded",
                    "observed": _rounded(observed),
                    "ceiling": ceiling,
                }
            )
    return triggers

def _decision(
    *,
    reports: Sequence[Mapping[str, Any]],
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    winner: str | None = None
    margin: float | None = None
    if not all(report["evidence_ready"] for report in reports):
        status = "insufficient_evidence"
        rationale = "every mechanism needs the declared run, diversity, and equivalent-source evidence"
    else:
        ranked = sorted(
            (report for report in reports if report["go_no"] == "go"),
            key=lambda report: (-float(report["scores"]["final"]), str(report["mechanism"])),
        )
        if not ranked:
            status = "no_go"
            rationale = "no mechanism satisfies the fixed outcome and operating-envelope gates"
        elif len(ranked) == 1:
            best = ranked[0]
            status = "single_mechanism_qualified"
            winner = str(best["mechanism"])
            rationale = "only one mechanism clears every fixed outcome and operating-envelope gate"
        else:
            margin = float(ranked[0]["scores"]["final"]) - float(
                ranked[1]["scores"]["final"]
            )
            status = "multiple_mechanisms_qualified"
            rationale = (
                "multiple mechanisms clear the fixed gates; this evidence does not justify "
                "one universal implementation path"
            )
    return _decision_payload(
        status=status,
        winner=winner,
        reports=reports,
        thresholds=thresholds,
        rationale=rationale,
        winner_margin=margin,
    )

def _decision_payload(
    *,
    status: str,
    winner: str | None,
    reports: Sequence[Mapping[str, Any]],
    thresholds: Mapping[str, Any],
    rationale: str,
    winner_margin: float | None = None,
) -> dict[str, Any]:
    removals: list[dict[str, Any]] = []
    if status in {"single_mechanism_qualified", "multiple_mechanisms_qualified"}:
        for report in reports:
            if report["go_no"] == "go":
                continue
            reasons = [trigger["id"] for trigger in report["replacement_triggers"]]
            removals.append({
                "mechanism": report["mechanism"],
                "action": "remove_superseded_path",
                "reasons": reasons or ["lower_falsifiable_comparison_score"],
            })
    elif status == "no_go":
        for report in reports:
            removals.append({
                "mechanism": report["mechanism"],
                "action": "replace_or_redesign",
                "reasons": [check["id"] for check in report["gate_checks"] if not check["passed"]],
            })
    return {
        "status": status,
        "winner": winner,
        "qualified_mechanisms": [
            report["mechanism"] for report in reports if report["go_no"] == "go"
        ],
        "winner_margin": None if winner_margin is None else _rounded(winner_margin),
        "rationale": rationale,
        "removal_recommendations": removals,
        "falsifiable_next_prediction": {
            "evaluation_set": "fresh_non_holdout_development_cases",
            "prediction": (
                f"{winner} repeats every go/no gate and the minimum winner margin"
                if winner
                else "qualified mechanisms remain provisional until prospective evidence separates their operating regimes"
            ),
            "failure_condition": (
                "any fixed quality or resource gate fails, equivalent-source evidence is "
                "insufficient, corpus diversity is too narrow, or the winner margin is not met"
            ),
            "minimum_winner_margin": thresholds["minimum_winner_margin"],
        },
    }

def _source_ref_signature(value: Any, context: str) -> tuple[tuple[str, str, int], ...]:
    refs = _sequence(value, f"{context}.source_refs")
    signature = []
    for index, raw in enumerate(refs):
        ref = _mapping(raw, f"{context}.source_refs[{index}]")
        _exact_keys(ref, {"source_id", "quote", "occurrence"}, f"{context}.source_refs[{index}]")
        signature.append(
            (
                _nonempty_text(ref.get("source_id"), f"{context}.source_id"),
                _nonempty_text(ref.get("quote"), f"{context}.quote"),
                _integer(ref.get("occurrence"), f"{context}.occurrence", minimum=1),
            )
        )
    if not signature:
        raise ValueError(f"{context}.source_refs must not be empty")
    return tuple(sorted(signature))

def _numeric_record(value: Any, *, keys: Sequence[str], context: str) -> dict[str, float]:
    record = _mapping(value, context)
    _exact_keys(record, set(keys), context)
    return {key: _number(record.get(key), f"{context}.{key}") for key in keys}

def _mapped_rows(value: Any, context: str) -> list[Mapping[str, Any]]:
    return [
        _mapping(row, f"{context}[{index}]")
        for index, row in enumerate(_sequence(value, context))
    ]

def _sum_counts(runs: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    names = (
        {"valid", "total"}
        if key == "relation_domain_range_counts"
        else {"matched", "observed", "expected", "unsupported", "missing"}
    )
    return {name: sum(int(run[key].get(name, 0)) for run in runs) for name in sorted(names)}

def _check(identifier: str, operator: str, observed: float, threshold: float) -> dict[str, Any]:
    return {
        "id": identifier,
        "operator": operator,
        "observed": _rounded(observed),
        "threshold": threshold,
        "passed": observed >= threshold if operator == ">=" else observed <= threshold,
    }

def _lower_is_better_score(observed: float, ceiling: float) -> float:
    if ceiling == 0:
        return 1.0 if observed == 0 else 0.0
    return max(0.0, 1.0 - (observed / ceiling))

def _fraction(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 1.0 if numerator == 0 else 0.0
    return float(numerator) / float(denominator)

def _mean(values: Sequence[int | float]) -> float:
    return float(statistics.fmean(values)) if values else 0.0

def _rounded(value: int | float) -> float:
    return round(float(value), 6)

def _mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value

def _sequence(value: Any, context: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{context} must be an array")
    return value

def _exact_keys(value: Mapping[str, Any], expected: set[str], context: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{context} must contain exactly: {', '.join(sorted(expected))}")

def _nonempty_text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} must be a non-empty string")
    return value

def _number(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{context} must be a non-negative number")
    return float(value)

def _integer(value: Any, context: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{context} must be an integer >= {minimum}")
    return value

def _rate(value: Any, context: str) -> float:
    number = _number(value, context)
    if number > 1:
        raise ValueError(f"{context} must be between 0 and 1")
    return number

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare externally authored Greenfield semantic mechanisms."
    )
    parser.add_argument("--experiment-file", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    return parser

def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        experiment = json.loads(args.experiment_file.read_text(encoding="utf-8"))
        report = evaluate_mechanism_experiment(experiment)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
