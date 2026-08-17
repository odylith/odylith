from __future__ import annotations

import ast
import copy
from pathlib import Path
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[3] / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_semantic_mechanism_experiment import (
    EXPERIMENT_VERSION,
    evaluate_mechanism_experiment,
)


def test_only_gate_qualified_mechanism_is_retained_and_failures_are_removed() -> None:
    report = evaluate_mechanism_experiment(_experiment())

    assert report["decision"]["status"] == "single_mechanism_qualified"
    assert report["decision"]["winner"] == "axis_first_adjudicated"
    removals = {
        row["mechanism"]: row for row in report["decision"]["removal_recommendations"]
    }
    assert set(removals) == {
        "direct_full_graph",
        "independent_candidate_adjudication",
    }
    assert "recurring_unsupported_additions" in removals["direct_full_graph"]["reasons"]
    assert "mean_latency_ms_ceiling_exceeded" in removals[
        "independent_candidate_adjudication"
    ]["reasons"]
    assert report["decision"]["falsifiable_next_prediction"]["evaluation_set"] == (
        "fresh_non_holdout_development_cases"
    )


def test_multiple_qualified_mechanisms_do_not_force_a_global_winner() -> None:
    experiment = _experiment()
    axis_runs = copy.deepcopy(experiment["mechanisms"][1]["runs"])
    experiment["mechanisms"] = [
        {"name": "host_direct_v2", "runs": copy.deepcopy(axis_runs)},
        {"name": "challenge_then_graph_v2", "runs": copy.deepcopy(axis_runs)},
    ]

    report = evaluate_mechanism_experiment(experiment)

    assert report["decision"]["status"] == "multiple_mechanisms_qualified"
    assert report["decision"]["winner"] is None
    assert report["decision"]["qualified_mechanisms"] == [
        "host_direct_v2",
        "challenge_then_graph_v2",
    ]
    assert report["decision"]["removal_recommendations"] == []


def test_unsupported_facts_and_wrong_relation_endpoints_fail_independent_dimensions() -> None:
    experiment = _experiment()
    direct = experiment["mechanisms"][0]
    for run in direct["runs"]:
        produces = run["packet"]["semantic_intent"]["relations"][1]
        produces["subject_id"] = "actor.0"

    report = evaluate_mechanism_experiment(experiment)
    direct_report = _report(report, "direct_full_graph")

    assert direct_report["claim_counts"]["facts"]["unsupported"] == 4
    assert direct_report["semantic_fidelity"]["precision"] == 0.75
    assert direct_report["relation_correctness"]["domain_range"] == 0.5
    assert {trigger["id"] for trigger in direct_report["replacement_triggers"]} >= {
        "recurring_unsupported_additions",
        "recurring_relation_contract_failure",
        "recurring_relation_oracle_failure",
    }


def test_no_go_when_every_mechanism_repeats_validator_failure() -> None:
    experiment = _experiment()
    for mechanism in experiment["mechanisms"]:
        for run in mechanism["runs"]:
            run["validator"]["accepted"] = False

    report = evaluate_mechanism_experiment(experiment)

    assert report["decision"]["status"] == "no_go"
    assert report["decision"]["winner"] is None
    assert len(report["decision"]["removal_recommendations"]) == 3
    for mechanism_report in report["mechanism_reports"]:
        assert "recurring_validator_rejection" in {
            trigger["id"] for trigger in mechanism_report["replacement_triggers"]
        }


def test_wrong_source_citation_cannot_satisfy_typed_oracle() -> None:
    experiment = _experiment()
    axis = experiment["mechanisms"][1]
    for run in axis["runs"]:
        run["packet"]["semantic_intent"]["facts"][0]["source_refs"][0]["quote"] = (
            "different source bytes"
        )

    report = evaluate_mechanism_experiment(experiment)
    axis_report = _report(report, "axis_first_adjudicated")

    assert axis_report["semantic_fidelity"] == {"precision": 0.666667, "recall": 0.666667}
    assert axis_report["relation_correctness"]["precision"] == 0.5
    assert "recurring_fact_oracle_failure" in {
        trigger["id"] for trigger in axis_report["replacement_triggers"]
    }


def test_insufficient_equivalent_source_evidence_cannot_select_a_winner() -> None:
    for retained_run_count in (0, 1):
        experiment = _experiment()
        for mechanism in experiment["mechanisms"]:
            mechanism["runs"] = mechanism["runs"][:retained_run_count]
        report = evaluate_mechanism_experiment(experiment)
        assert report["decision"]["status"] == "insufficient_evidence"
        assert all(not row["evidence_ready"] for row in report["mechanism_reports"])


def test_one_product_fixture_family_cannot_select_a_winner() -> None:
    experiment = _experiment()
    for mechanism in experiment["mechanisms"]:
        mechanism["runs"] = [
            run for run in mechanism["runs"] if run["case_family"] == "claim-desk"
        ]

    report = evaluate_mechanism_experiment(experiment)

    assert report["decision"]["status"] == "insufficient_evidence"
    assert all(
        row["development_corpus_evidence"]["distinct_case_family_count"] == 1
        for row in report["mechanism_reports"]
    )


def test_harness_has_no_regex_or_semantic_prose_parser() -> None:
    source_path = Path(__file__).resolve().parents[3] / (
        "scripts/release/greenfield_semantic_mechanism_experiment.py"
    )
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        str(node.module or "")
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }

    assert "re" not in imports
    assert not ({"httpx", "openai", "requests"} & imports)
    assert "regex" not in source.lower()
    assert "operator_prompt" not in source
    assert "prompt_text" not in source


def _experiment() -> dict:
    mechanisms = []
    for name in (
        "direct_full_graph",
        "axis_first_adjudicated",
        "independent_candidate_adjudication",
    ):
        mechanisms.append(
            {
                "name": name,
                "runs": [
                    _run(
                        name=name,
                        case_id="claim-equivalent-a",
                        case_family="claim-desk",
                        quote="claim source form a",
                    ),
                    _run(
                        name=name,
                        case_id="claim-equivalent-b",
                        case_family="claim-desk",
                        quote="claim source form b",
                    ),
                    _run(
                        name=name,
                        case_id="harbor-equivalent-a",
                        case_family="harbor-operations",
                        quote="harbor source form a",
                    ),
                    _run(
                        name=name,
                        case_id="harbor-equivalent-b",
                        case_family="harbor-operations",
                        quote="harbor source form b",
                    ),
                ],
            }
        )
    return {
        "version": EXPERIMENT_VERSION,
        "thresholds": {
            "minimum_runs_per_mechanism": 2,
            "minimum_equivalence_pairs": 1,
            "minimum_distinct_case_families": 2,
            "minimum_recurring_failure_count": 2,
            "minimum_winner_margin": 0.01,
            "maximum_unsupported_addition_rate": 0.0,
            "maximum_regression_count": 0,
            "quality_floors": {
                "validator_acceptance": 1.0,
                "fact_precision": 1.0,
                "fact_recall": 1.0,
                "relation_precision": 1.0,
                "relation_recall": 1.0,
                "relation_domain_range": 1.0,
                "equivalent_source_convergence": 1.0,
                "package_utility": 1.0,
                "package_differentiation": 1.0,
            },
            "resource_ceilings": {
                "mean_latency_ms": 100.0,
                "mean_cost_usd": 1.0,
                "mean_prompt_tokens": 1000.0,
                "mean_authoring_passes": 4.0,
                "mean_architecture_paths": 4.0,
            },
        },
        "mechanisms": mechanisms,
    }


def _run(*, name: str, case_id: str, case_family: str, quote: str) -> dict:
    source_refs = [{"source_id": "operator_prompt", "quote": quote, "occurrence": 1}]
    family_key = case_family.replace("-", ".")
    facts = [
        _fact("actor.0", "actor", f"{family_key}.actor", source_refs),
        _fact("step.0", "workflow_step", f"{family_key}.step", source_refs),
        _fact("output.0", "visible_output", f"{family_key}.output", source_refs),
    ]
    fact_claims = [
        {"fact_id": fact["fact_id"], "semantic_key": semantic_key}
        for fact, semantic_key in zip(
            facts,
            (f"{family_key}.actor", f"{family_key}.step", f"{family_key}.output"),
            strict=True,
        )
    ]
    if name == "direct_full_graph":
        facts.append(_fact("actor.ghost", "actor", f"{family_key}.unsupported", source_refs))
        fact_claims.append(
            {"fact_id": "actor.ghost", "semantic_key": f"{family_key}.unsupported"}
        )
    latency = 150.0 if name == "independent_candidate_adjudication" else 20.0
    cost = 2.0 if name == "independent_candidate_adjudication" else 0.1
    passes = 3.0 if name == "independent_candidate_adjudication" else 1.0
    paths = 3.0 if name == "independent_candidate_adjudication" else 1.0
    return {
        "case_id": case_id,
        "case_family": case_family,
        "equivalence_group": f"{case_family}-same-intent",
        "packet": {
            "semantic_intent": {
                "facts": facts,
                "relations": [
                    {
                        "relation_id": "owned.0",
                        "kind": "owned_by",
                        "subject_id": "step.0",
                        "object_id": "actor.0",
                        "source_refs": copy.deepcopy(source_refs),
                    },
                    {
                        "relation_id": "produces.0",
                        "kind": "produces",
                        "subject_id": "step.0",
                        "object_id": "output.0",
                        "source_refs": copy.deepcopy(source_refs),
                    },
                ],
            }
        },
        "fact_claims": fact_claims,
        "oracle": {
            "facts": [
                _oracle_fact(f"{family_key}.actor", "actor", source_refs),
                _oracle_fact(f"{family_key}.step", "workflow_step", source_refs),
                _oracle_fact(f"{family_key}.output", "visible_output", source_refs),
            ],
            "relations": [
                {
                    "kind": "owned_by",
                    "subject_key": f"{family_key}.step",
                    "object_key": f"{family_key}.actor",
                    "source_refs": copy.deepcopy(source_refs),
                },
                {
                    "kind": "produces",
                    "subject_key": f"{family_key}.step",
                    "object_key": f"{family_key}.output",
                    "source_refs": copy.deepcopy(source_refs),
                },
            ],
        },
        "package_evidence": {
            "utility_checks": {
                "brief_is_coherent": True,
                "backlog_is_actionable": True,
                "diagrams_are_traceable": True,
            },
            "component_responsibility_keys": ["intake", "decision"],
            "minimum_distinct_component_responsibilities": 2,
        },
        "validator": {"accepted": True, "regression_count": 0},
        "performance": {"latency_ms": latency, "cost_usd": cost},
        "complexity": {
            "prompt_tokens": 100.0,
            "authoring_passes": passes,
            "architecture_paths": paths,
        },
    }


def _fact(fact_id: str, kind: str, semantic_key: str, source_refs: list[dict]) -> dict:
    return {
        "fact_id": fact_id,
        "kind": kind,
        "label": semantic_key,
        "source_refs": copy.deepcopy(source_refs),
    }


def _oracle_fact(semantic_key: str, kind: str, source_refs: list[dict]) -> dict:
    return {
        "semantic_key": semantic_key,
        "kind": kind,
        "source_refs": copy.deepcopy(source_refs),
        "required_fields": {"label": semantic_key},
    }


def _report(report: dict, mechanism: str) -> dict:
    return next(row for row in report["mechanism_reports"] if row["mechanism"] == mechanism)
