from __future__ import annotations

import ast
from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from threading import Event

import pytest

import greenfield_semantic_authoring_wave as authoring_wave
import greenfield_semantic_materiality_screen_experiment as materiality_screen
import greenfield_semantic_source_graph_author as source_author
import greenfield_semantic_rescue_pipeline as rescue
import greenfield_semantic_source_pair_adjudicator as source_pair
import greenfield_semantic_standard_pipeline_experiment as pipeline
import greenfield_semantic_standard_path_experiment as standard_path
import greenfield_semantic_standard_prompts as prompts
from greenfield_semantic_pipeline_evidence import require_successful_pipeline_evidence
from greenfield_semantic_release_support import greenfield_runtime_source_fingerprint
from greenfield_semantic_structured_host import HostStageCancelled, HostStageTimeout
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    standard_host_stage_profile,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_layered_authoring import (
    SEMANTIC_PARTITIONED_AUTHOR_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    ACTIVE_SEMANTIC_MECHANISM_ID,
    semantic_execution_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    PARALLEL_MATERIALITY_DECISION_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import (
    SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
    SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
    SOURCE_BOUNDARY_COLLECTIONS,
    SOURCE_PATH_COLLECTIONS,
    combine_source_authoring_partitions,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    semantic_evidence_block_catalog,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_hypothesis_comparison import (
    independently_confirmed_discarded_refs,
    source_candidate_policy_kind_assignments,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    IDENTITY_EVIDENCE,
    PATH_EVIDENCE,
    SEMANTIC_PROMPT,
    STATE_EVIDENCE,
    semantic_clarification_packet,
    semantic_intent_packet,
)
from tests.unit.install.greenfield_semantic_release_test_fixtures import (
    verified_transaction_receipt_fixture,
)


def test_budget_contracts_reserve_transaction_time_inside_sixty_ninety() -> None:
    defaults = pipeline.run_standard_pipeline.__kwdefaults__
    assert defaults["host_profile"] == "codex"
    assert standard_host_stage_profile("codex") == {
        "version": "odylith.greenfield.standard-host-stage-profile.v13",
        "host_profile": "codex",
        "critic_model": "gpt-5.6-sol",
        "critic_reasoning_effort": "low",
        "source_hypothesis_model": "gpt-5.5",
        "source_hypothesis_reasoning_effort": "low",
        "final_adjudicator_model": "gpt-5.6-sol",
        "final_adjudicator_reasoning_effort": "low",
    }
    assert standard_host_stage_profile("claude") == {
        "version": "odylith.greenfield.standard-host-stage-profile.v13",
        "host_profile": "claude",
        "critic_model": "claude-opus-4-6",
        "critic_reasoning_effort": "medium",
        "source_hypothesis_model": "claude-opus-4-6",
        "source_hypothesis_reasoning_effort": "low",
        "final_adjudicator_model": "claude-opus-4-6",
        "final_adjudicator_reasoning_effort": "low",
    }
    assert pipeline.standard_budget_contract() == {
        "tier": "standard",
        "deadline_seconds": 60,
        "comparison": "strictly_less_than",
        "parallel_model_host_timeout_seconds": 48,
        "all_model_calls_start_at_entry": True,
        "standard_model_call_count": 3,
        "commit_semantic_authoring_shared_seconds": 48,
        "clarification_semantic_authoring_shared_seconds": 58,
        "candidate_admission": "paired_source_and_completion_end_to_end_packet",
        "packet_and_transaction_reserve_seconds": 11,
        "clarification_packet_reserve_seconds": 1,
        "critical_path_seconds": 59,
        "retries": 0,
        "automatic_deep_tier": False,
        "topology_mode": "single_system",
    }


def test_dedicated_source_author_always_owns_source_truth(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_started = Event()

    def full_graph(**kwargs: object) -> dict:
        assert source_started.wait(timeout=1)
        return {
            "candidate": {
                "source": _empty_source_graph(),
                "completion": {},
            },
            "usage": {"input_tokens": 11, "output_tokens": 7},
            "wall_ms": 12,
            "prompt_text": "full-graph hypothesis",
        }

    def source_only(**kwargs: object) -> dict:
        source_started.set()
        return {
            "source": _empty_source_graph(),
            "usage": {"input_tokens": 5, "output_tokens": 3},
            "wall_ms": 10,
            "prompt_text": "source-only hypothesis",
        }

    monkeypatch.setattr(standard_path, "run_partitioned_graph_hypothesis", full_graph)
    monkeypatch.setattr(standard_path, "run_source_graph_hypothesis", source_only)
    receipt = standard_path.run_hedged_source_graph_hypothesis_case(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        model="gpt-5.6-sol",
        reasoning_effort="low",
        output_path=tmp_path / "source.json",
        model_budget_seconds=20,
    )

    assert receipt["model_call_count"] == 2
    assert receipt["selected_run_index"] == 1
    assert receipt["source"] == _empty_source_graph()
    assert receipt["partitioned_candidate"] == {
        "version": SEMANTIC_PARTITIONED_AUTHOR_VERSION,
        "source": _empty_source_graph(),
        "completion": {},
    }
    assert receipt["usage"] == {"input_tokens": 16, "output_tokens": 10}
    assert [row["status"] for row in receipt["hypothesis_runs"]] == [
        "comparison_passed",
        "selected",
    ]
    assert [row["hypothesis_mode"] for row in receipt["hypothesis_runs"]] == [
        "full_graph",
        "source_only",
    ]
    assert json.loads((tmp_path / "source.json").read_text(encoding="utf-8")) == receipt
    assert rescue.rescue_budget_contract(
        prior_standard_failure_sha256="a" * 64,
        prior_standard_wall_ms=53_000,
    ) == {
        "tier": "rescue",
        "deadline_seconds": 90,
        "comparison": "less_than_or_equal",
        "reused_standard_hypotheses": True,
        "continuation_final_adjudication_seconds": 26,
        "packet_and_transaction_reserve_seconds": 11,
        "cumulative_prior_standard_wall_ms": 53_000,
        "critical_path_ms": 90_000,
        "retries": 0,
        "automatic_deep_tier": False,
        "topology_mode": "adaptive",
        "prior_standard_failure_sha256": "a" * 64,
    }


def test_heterogeneous_source_hedge_cross_binds_source_only_truth(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    incomplete_source = {**_empty_source_graph(), "marker": "incomplete"}
    complete_source = _empty_source_graph()
    completion = {"system": "full-graph architecture"}

    def full_graph(**kwargs: object) -> dict:
        return {
            "candidate": {
                "source": incomplete_source,
                "completion": completion,
            },
            "usage": {"input_tokens": 11, "output_tokens": 7},
            "wall_ms": 12,
            "prompt_text": "full-graph hypothesis",
        }

    def source_only(**kwargs: object) -> dict:
        return {
            "source": complete_source,
            "usage": {"input_tokens": 5, "output_tokens": 3},
            "wall_ms": 10,
            "prompt_text": "source-only hypothesis",
        }

    def validate(candidate: Mapping[str, object], hypothesis_mode: str) -> None:
        assert hypothesis_mode in {"full_graph", "source_only"}
        if candidate["source"] == incomplete_source:
            raise ValueError("full graph omitted source meaning")

    monkeypatch.setattr(standard_path, "run_partitioned_graph_hypothesis", full_graph)
    monkeypatch.setattr(standard_path, "run_source_graph_hypothesis", source_only)
    receipt = standard_path.run_hedged_source_graph_hypothesis_case(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        model="gpt-5.5",
        reasoning_effort="low",
        output_path=tmp_path / "source.json",
        model_budget_seconds=20,
        candidate_validator=validate,
    )

    assert receipt["selected_run_index"] == 1
    assert receipt["partitioned_candidate"] == {
        "version": SEMANTIC_PARTITIONED_AUTHOR_VERSION,
        "source": complete_source,
        "completion": completion,
    }
    assert receipt["usage"] == {"input_tokens": 16, "output_tokens": 10}
    assert [
        (row["hypothesis_mode"], row["status"])
        for row in receipt["hypothesis_runs"]
    ] == [("full_graph", "comparison_rejected"), ("source_only", "selected")]


def test_full_graph_timeout_preserves_completed_source_for_rescue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = _empty_source_graph()
    monkeypatch.setattr(
        standard_path,
        "run_partitioned_graph_hypothesis",
        lambda **_: (_ for _ in ()).throw(HostStageTimeout("full graph timed out")),
    )
    monkeypatch.setattr(
        standard_path,
        "run_source_graph_hypothesis",
        lambda **_: {
            "source": source,
            "usage": {"input_tokens": 5, "output_tokens": 3},
            "wall_ms": 18_000,
            "prompt_text": "source-only hypothesis",
        },
    )

    def validate(candidate: Mapping[str, object], _: str) -> None:
        raise standard_path.ReusableSourcePairDisagreement(
            "completion is unavailable",
            source=candidate["source"],
            source_adjudication={"status": "passed"},
            dispute="completion",
        )

    with pytest.raises(standard_path.CompletionStageIncomplete) as caught:
        standard_path.run_hedged_source_graph_hypothesis_case(
            corpus_path=_corpus(tmp_path),
            case_id="claim-desk",
            model="gpt-5.5",
            reasoning_effort="low",
            output_path=tmp_path / "source.json",
            model_budget_seconds=48,
            candidate_validator=validate,
        )

    receipt = caught.value.receipt
    assert receipt["validation_status"] == "reusable_source_handoff"
    assert receipt["selected_run_index"] == 1
    assert [row["status"] for row in receipt["hypothesis_runs"]] == [
        "failed",
        "source_pair_disagreement",
    ]
    assert [row["hypothesis_mode"] for row in receipt["hypothesis_candidates"]] == [
        "source_only"
    ]


def test_completion_disagreement_preserves_both_hypotheses_for_rescue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = _empty_source_graph()
    completion = {"system": "provisional completion"}
    full_candidate = {"source": source, "completion": completion}

    monkeypatch.setattr(
        standard_path,
        "run_partitioned_graph_hypothesis",
        lambda **_: {
            "candidate": full_candidate,
            "usage": {"input_tokens": 11},
            "wall_ms": 12,
            "prompt_text": "full graph",
        },
    )
    monkeypatch.setattr(
        standard_path,
        "run_source_graph_hypothesis",
        lambda **_: {
            "source": source,
            "usage": {"input_tokens": 7},
            "wall_ms": 10,
            "prompt_text": "source only",
        },
    )

    def validate(candidate: Mapping[str, object], hypothesis_mode: str) -> None:
        if hypothesis_mode == "source_only":
            raise standard_path.ReusableSourcePairDisagreement(
                "completion cites meaning absent from admitted source truth",
                source=source,
                source_adjudication={"version": "typed-source-adjudication"},
                dispute="completion",
            )

    output = tmp_path / "source.json"
    with pytest.raises(standard_path.CompletionStageIncomplete) as raised:
        standard_path.run_hedged_source_graph_hypothesis_case(
            corpus_path=_corpus(tmp_path),
            case_id="claim-desk",
            model="gpt-5.5",
            reasoning_effort="low",
            output_path=output,
            model_budget_seconds=20,
            candidate_validator=validate,
        )

    receipt = raised.value.receipt
    assert receipt["validation_status"] == "reusable_source_pair"
    assert receipt["source"] == source
    assert [row["hypothesis_mode"] for row in receipt["hypothesis_candidates"]] == [
        "full_graph",
        "source_only",
    ]
    assert receipt["hypothesis_runs"][1]["status"] == "source_pair_disagreement"
    assert json.loads(output.read_text(encoding="utf-8")) == receipt


def test_typed_source_rejection_preserves_the_structured_pair_for_rescue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = _empty_source_graph()
    completion = {"system": "validated full completion"}
    monkeypatch.setattr(
        standard_path,
        "run_partitioned_graph_hypothesis",
        lambda **_: {
            "candidate": {"source": source, "completion": completion},
            "usage": {"input_tokens": 11},
            "wall_ms": 12,
            "prompt_text": "full graph",
        },
    )
    monkeypatch.setattr(
        standard_path,
        "run_source_graph_hypothesis",
        lambda **_: (_ for _ in ()).throw(
            standard_path.StructuredSourceHypothesisRejected(
                "workflow transition does not change state",
                source=source,
                usage={"input_tokens": 7},
                wall_ms=10,
                prompt_text="source only",
            )
        ),
    )

    with pytest.raises(standard_path.CompletionStageIncomplete) as raised:
        standard_path.run_hedged_source_graph_hypothesis_case(
            corpus_path=_corpus(tmp_path),
            case_id="claim-desk",
            model="gpt-5.5",
            reasoning_effort="low",
            output_path=tmp_path / "source.json",
            model_budget_seconds=20,
            candidate_validator=lambda *_: None,
        )

    receipt = raised.value.receipt
    assert receipt["validation_status"] == "reusable_source_pair"
    assert receipt["source_pair_dispute"] == "source_authority"
    assert receipt["selected_run_index"] is None
    assert receipt["source_candidate_adjudication"] is None
    assert [row["hypothesis_mode"] for row in receipt["hypothesis_candidates"]] == [
        "full_graph",
        "source_only",
    ]


def test_discarded_evidence_requires_exact_independent_source_agreement() -> None:
    prompt = "Route one note. Ignore the retired sketch name Linen Meteor."
    exact = {
        "source_id": "operator_prompt",
        "quote": "Ignore the retired sketch name Linen Meteor.",
        "occurrence": 1,
    }
    overlapping = {
        "source_id": "operator_prompt",
        "quote": "the retired sketch name Linen Meteor",
        "occurrence": 1,
    }
    unrelated = {
        "source_id": "operator_prompt",
        "quote": "Route one note.",
        "occurrence": 1,
    }

    evidence_sources = {"operator_prompt": prompt, "operator_edit": ""}
    assert independently_confirmed_discarded_refs(
        [exact], [overlapping], evidence_sources=evidence_sources
    ) == [exact]
    assert independently_confirmed_discarded_refs(
        [exact], [unrelated], evidence_sources=evidence_sources
    ) == []


def test_policy_assignment_comes_from_typed_source_relation_not_wording() -> None:
    prompt = "Do not notify anyone automatically."
    source_ref = {
        "source_id": "operator_prompt",
        "quote": prompt,
        "occurrence": 1,
    }
    candidate = {
        "source": {
            "boundary": {
                "policies": [
                    {
                        "label": "Any presentation text may vary",
                        "policy_kind": "excluded_capability",
                        "source_refs": [source_ref],
                    }
                ]
            }
        }
    }

    assert source_candidate_policy_kind_assignments(
        candidate,
        conflict_refs=[source_ref],
        evidence_sources={"operator_prompt": prompt, "operator_edit": ""},
    ) == {("operator_prompt", prompt, 1): "excluded_capability"}


def test_source_hypothesis_and_final_authorities_are_disjoint() -> None:
    catalog = semantic_evidence_block_catalog(
        {"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""}
    )
    source_prompt = prompts.unified_source_graph_prompt(
        prompt_text=SEMANTIC_PROMPT,
        evidence_catalog=catalog,
        model_budget_seconds=34,
    )
    final_prompt = prompts.final_graph_adjudication_prompt(
        prompt_text=SEMANTIC_PROMPT,
        evidence_catalog=catalog,
        materiality_hypothesis=_decision(semantic_intent_packet()),
        source_hypothesis={
            "version": "typed-source",
            "facts": [
                {
                    "fact_id": "dependency.0",
                    "kind": "external_system",
                    "label": "Local duty roster",
                }
            ],
            "relations": [],
        },
        discarded_hypothesis=[],
        relation_catalog={},
        citation_registry={
            "citation.0": {"fact_ids": ("identity.0",), "source_ref": {}}
        },
        model_budget_seconds=25,
        topology_mode="single_system",
    )

    assert "whole-source Greenfield author" in source_prompt
    assert "decide neither final materiality" in source_prompt
    assert "input or dependency data" in source_prompt
    assert "are not produced outputs" in source_prompt
    assert "source-path partition" not in source_prompt
    assert "source-boundary partition" not in source_prompt
    assert "MATERIALITY_HYPOTHESIS" in final_prompt
    assert "TYPED_SOURCE_CANDIDATE" in final_prompt
    assert "select the exact admitted source relation IDs" in final_prompt
    assert "prompt-only materiality hypothesis as settled authority" in final_prompt
    assert "cannot reopen or clarify it" in final_prompt
    assert "already been aligned to that authority by exact citations" in final_prompt
    assert "replace every proposed source relation" not in final_prompt
    assert "admit only supported correctly typed facts by exact fact ID" in final_prompt
    assert (
        "reject the source when a required non-policy fact or relation is missing or wrong"
        in final_prompt
    )
    assert '"unassigned_source_dependency_ids":["dependency.0"]' in final_prompt
    assert "valid source fact, not a missing source relation" in final_prompt
    assert "must be bound by depends_on from at least one authored internal system" in final_prompt
    assert "author no governance narratives" in final_prompt
    assert "exactly one cohesive result system" in final_prompt
    assert "never invent an internal adapter" in final_prompt


def test_source_author_emits_source_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _empty_source_graph()
    calls: list[str] = []

    def host(**kwargs: object) -> tuple[dict, dict, int]:
        prefix = str(kwargs["temporary_prefix"])
        calls.append(prefix)
        return deepcopy(source), {"model_calls": 1}, 500

    monkeypatch.setattr(source_author, "run_structured_host", host)
    monkeypatch.setattr(
        source_author,
        "compile_source_partitioned_graph",
        lambda value: {"facts": [], "relations": []},
    )
    catalog = semantic_evidence_block_catalog(
        {"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""}
    )
    hypothesis = source_author.run_source_graph_hypothesis(
        prompt_text=SEMANTIC_PROMPT,
        evidence_catalog=catalog,
        model="frontier",
        reasoning_effort="medium",
        budget_seconds=34,
    )
    assert hypothesis["source"] == source
    assert calls == ["odylith-unified-source-author-"]
    assert hypothesis["usage"] == {"model_calls": 1}


def test_materiality_screen_authors_exact_atomic_refs_and_validates_source_bytes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    candidate = _decision(semantic_intent_packet())

    def structured_host(**kwargs: object) -> tuple[dict, dict, int]:
        schema = kwargs["schema"]
        assert "ref_id" not in json.dumps(schema)
        assert '"quote"' in json.dumps(schema)
        prompt = str(kwargs["prompt"])
        assert "accepted path's execution, access, or side effects" in prompt
        assert "capability or outcome that the product must not provide" in prompt
        assert "never decide by wording, grammar, tokens" in prompt
        assert "smallest exact source substring" in prompt
        return candidate, {"input_tokens": 1, "output_tokens": 1}, 500

    monkeypatch.setattr(materiality_screen, "run_structured_host", structured_host)
    receipt = materiality_screen.run_screen(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        model="gpt-5.6-sol",
        reasoning_effort="low",
        output_path=tmp_path / "screen.json",
        model_budget_seconds=20,
    )

    encoded = json.dumps(receipt["decision"])
    assert receipt["decision"]["version"] == PARALLEL_MATERIALITY_DECISION_VERSION
    assert '"ref_id"' not in encoded
    assert SEMANTIC_PROMPT.split(".", 1)[0] in encoded


def test_parallel_materiality_preserves_one_material_question_without_another_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    question = semantic_clarification_packet()
    monkeypatch.setattr(
        pipeline,
        "run_authoring_wave",
        lambda **_: (
            _critic_receipt(question),
            _source_hypothesis_receipt(),
            _partitioned_author_receipt(question),
            None,
        ),
    )
    receipt = pipeline.run_standard_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "receipt.json",
    )

    assert (receipt["status"], receipt["outcome"]) == ("completed", "clarify")
    assert receipt["source_hypothesis"]["authority_used"] is False
    assert receipt["source_hypothesis"]["validation_status"] == "passed"
    assert receipt["final_graph_adjudication"]["stage"] == "partitioned_graph_admission"
    assert receipt["packet"]["semantic_intent"]["status"] == "clarification_required"
    assert receipt["packet"]["semantic_intent"]["facts"] == []
    assert receipt["model_call_count"] == 3
    assert receipt["mechanism_execution"]["mechanism_id"] == (
        ACTIVE_SEMANTIC_MECHANISM_ID
    )
    assert receipt["mechanism_execution"]["tier"] == "standard"


def test_material_question_waits_for_independent_source_challenge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    question = semantic_clarification_packet()
    completed = Event()
    monkeypatch.setattr(
        authoring_wave, "run_screen", lambda **_: _critic_receipt(question)
    )

    def source_hypotheses(**kwargs: object) -> dict:
        assert not kwargs["cancel_event"].is_set()  # type: ignore[union-attr]
        completed.set()
        return _source_hypothesis_receipt()

    monkeypatch.setattr(
        authoring_wave,
        "run_hedged_source_graph_hypothesis_case",
        source_hypotheses,
    )

    critic, source, author, failure = authoring_wave.run_authoring_wave(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        root=tmp_path,
        host_profile="codex",
        critic_model="gpt-5.5",
        critic_reasoning_effort="low",
        source_hypothesis_model="gpt-5.5",
        source_hypothesis_reasoning_effort="low",
        final_adjudicator_model="gpt-5.6-sol",
        final_adjudicator_reasoning_effort="low",
        budget=authoring_wave.AuthoringWaveBudget(48, 48, 58, "single_system"),
    )

    assert failure is None
    assert completed.is_set()
    assert critic["model_call_count"] == 1
    assert source["validation_status"] == "passed"
    assert source["model_call_count"] == 2
    assert author["source_status"] == "not_applicable"
    assert author["model_call_count"] == 0
    assert author["candidate"] is None


def test_two_source_material_gap_overrides_a_commit_critic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet = semantic_intent_packet()
    monkeypatch.setattr(
        authoring_wave, "run_screen", lambda **_: _critic_receipt(packet)
    )
    monkeypatch.setattr(
        authoring_wave,
        "admit_partitioned_candidate",
        lambda candidate, **_: (candidate, candidate["source"], [], {}),
    )
    source_graph = _source_graph_with_ambiguity()

    def source_hypotheses(**kwargs: object) -> dict:
        candidate = {
            "version": SEMANTIC_PARTITIONED_AUTHOR_VERSION,
            "source": source_graph,
            "completion": {},
        }
        validator = kwargs["candidate_validator"]
        validator(candidate, "full_graph")  # type: ignore[operator]
        validator(candidate, "source_only")  # type: ignore[operator]
        return {
            "stage": "source_hypothesis",
            "case_id": "claim-desk",
            "source": source_graph,
            "partitioned_candidate": candidate,
            "partitioned_candidates": [
                {
                    "run_index": 1,
                    "hypothesis_mode": "source_only",
                    "candidate": candidate,
                }
            ],
            "model_call_count": 2,
            "usage": {},
            "wall_ms": 1,
            "validation_status": "passed",
        }

    monkeypatch.setattr(
        authoring_wave,
        "run_hedged_source_graph_hypothesis_case",
        source_hypotheses,
    )

    critic, source, author, failure = authoring_wave.run_authoring_wave(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        root=tmp_path,
        host_profile="codex",
        critic_model="gpt-5.5",
        critic_reasoning_effort="low",
        source_hypothesis_model="gpt-5.5",
        source_hypothesis_reasoning_effort="low",
        final_adjudicator_model="gpt-5.6-sol",
        final_adjudicator_reasoning_effort="low",
        budget=authoring_wave.AuthoringWaveBudget(48, 48, 58, "single_system"),
    )

    assert failure is None
    assert critic["initial_decision"]["outcome"]["decision"] == "authorize_graph"
    assert critic["decision"]["outcome"] == {
        "decision": "clarification_required",
        "clarification": {
            "field": "visible_result",
            "question": "What observable result should the consumer receive?",
            "source_refs": [
                {
                    "source_id": "operator_prompt",
                    "quote": PATH_EVIDENCE,
                    "occurrence": 1,
                },
            ],
            "alternatives": [],
        },
    }
    assert critic["independent_source_resolution"]["status"] == (
        "independently_confirmed_source_material_ambiguity"
    )
    assert source["authority_used"] is False
    assert author["source_status"] == "not_applicable"


def test_parallel_commit_uses_candidate_facts_and_final_relation_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet = semantic_intent_packet()
    critic = _critic_receipt(packet)
    source = _source_hypothesis_receipt()
    author = _partitioned_author_receipt(packet)
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        pipeline,
        "run_authoring_wave",
        lambda **_: (critic, source, author, None),
    )
    monkeypatch.setattr(
        pipeline,
        "_finalize_author",
        lambda **kwargs: captured.update(finalize=dict(kwargs))
        or {"packet": deepcopy(packet), "candidate": {"typed": True}},
    )
    monkeypatch.setattr(
        pipeline,
        "_compile_packet",
        lambda **_: verified_transaction_receipt_fixture(
            packet, prompt=SEMANTIC_PROMPT
        ),
    )
    receipt = pipeline.run_standard_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "receipt.json",
    )

    assert (receipt["status"], receipt["outcome"]) == ("completed", "commit")
    finalize_call = captured["finalize"]
    assert finalize_call["author"] == author
    assert finalize_call["assessment"] == packet["materiality_assessment"]
    assert receipt["source_hypothesis"]["authority_used"] is False
    assert receipt["final_graph_adjudication"]["source_status"] == "approved"
    assert receipt["model_call_count"] == 3
    assert receipt["restart_count"] == 0
    assert receipt["mechanism_execution"]["mechanism_id"] == (
        ACTIVE_SEMANTIC_MECHANISM_ID
    )
    assert receipt["mechanism_execution"]["model_call_count"] == 3
    _, evidence = require_successful_pipeline_evidence(
        receipt,
        case_id="claim-desk",
        prompt=SEMANTIC_PROMPT,
        semantic_artifact=packet,
    )
    assert evidence["execution_tier"] == "standard"
    assert evidence["model_calls"] == 3


def test_packet_records_host_identity_instead_of_model_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    def packet(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return {"version": "test-packet"}

    monkeypatch.setattr(pipeline, "build_semantic_intent_packet", packet)
    result = pipeline._finalize_author(
        case_id="claim-desk",
        prompt=SEMANTIC_PROMPT,
        assessment={"decision": "authorize_graph"},
        author={
            "candidate": {"source": {}, "completion": {}},
            "compiled_author_output": {"typed_graph": True},
        },
        critic_run_id="critic-run",
        semantic_host_profile="claude",
    )

    assert captured["kwargs"]["critic_host_profile"] == "claude"
    assert captured["args"][1] == {"typed_graph": True}
    assert result["packet"] == {"version": "test-packet"}


def test_unavailable_host_counts_every_attempt_and_never_retries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        authoring_wave,
        "run_screen",
        lambda **_: (_ for _ in ()).throw(RuntimeError("provider unavailable")),
    )
    monkeypatch.setattr(
        authoring_wave,
        "run_hedged_source_graph_hypothesis_case",
        lambda **_: (_ for _ in ()).throw(HostStageCancelled("cancelled")),
    )
    receipt = pipeline.run_standard_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "unavailable.json",
        host_profile="claude",
    )

    assert (receipt["status"], receipt["outcome"]) == (
        "failed",
        "environment_failure",
    )
    assert receipt["materiality_critic"]["host_profile"] == "claude"
    assert receipt["model_call_count"] == 3
    assert receipt["restart_count"] == 0


def test_incomplete_first_wave_is_not_eligible_for_rescue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet = semantic_intent_packet()
    monkeypatch.setattr(authoring_wave, "run_screen", lambda **_: _critic_receipt(packet))
    monkeypatch.setattr(
        authoring_wave,
        "run_hedged_source_graph_hypothesis_case",
        lambda **_: (_ for _ in ()).throw(HostStageTimeout("source timed out")),
    )

    receipt = pipeline.run_standard_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "source-timeout.json",
    )

    assert (receipt["status"], receipt["outcome"], receipt["failed_stage"]) == (
        "failed",
        "standard_deadline_exceeded",
        "source_hypothesis",
    )
    assert receipt["model_call_count"] == 3
    with pytest.raises(ValueError, match="reusable standard-path handoff"):
        rescue.run_rescue_pipeline(
            corpus_path=_corpus(tmp_path),
            case_id="claim-desk",
            output_path=tmp_path / "invalid-rescue.json",
            standard_failure_receipt=receipt,
        )


def test_two_validated_hypotheses_may_handoff_before_final_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet = semantic_intent_packet()
    monkeypatch.setattr(
        pipeline,
        "run_authoring_wave",
        lambda **_: (
            _critic_receipt(packet),
            {**_source_hypothesis_receipt(), "authority_used": False},
            None,
            (
                "handoff",
                "final_graph_adjudication",
                "parallel hypotheses left no bounded final-adjudication budget",
            ),
        ),
    )

    receipt = pipeline.run_standard_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "handoff.json",
    )

    assert (receipt["status"], receipt["outcome"], receipt["failed_stage"]) == (
        "rescue_required",
        "standard_deadline_exceeded",
        "final_graph_adjudication",
    )
    assert receipt["model_call_count"] == 3


def test_validated_source_completion_disagreement_enters_typed_rescue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet = semantic_intent_packet()
    source = {
        **_source_hypothesis_receipt(),
        "authority_used": False,
        "validation_status": "reusable_source_pair",
    }
    monkeypatch.setattr(
        pipeline,
        "run_authoring_wave",
        lambda **_: (
            _critic_receipt(packet),
            source,
            None,
            (
                "handoff",
                "graph_completion",
                "validated source requires completion adjudication",
            ),
        ),
    )

    receipt = pipeline.run_standard_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "typed-handoff.json",
    )

    assert (receipt["status"], receipt["outcome"], receipt["failed_stage"]) == (
        "rescue_required",
        "typed_standard_handoff",
        "graph_completion",
    )
    assert receipt["source_hypothesis"] == source


def test_transaction_environment_failure_returns_typed_outcome(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet = semantic_intent_packet()
    monkeypatch.setattr(
        pipeline,
        "run_authoring_wave",
        lambda **_: (
            _critic_receipt(packet),
            _source_hypothesis_receipt(),
            _partitioned_author_receipt(packet),
            None,
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "_finalize_author",
        lambda **_: {"packet": deepcopy(packet), "candidate": {"typed": True}},
    )
    monkeypatch.setattr(
        pipeline,
        "_compile_packet",
        lambda **_: (_ for _ in ()).throw(ModuleNotFoundError("missing dependency")),
    )

    receipt = pipeline.run_standard_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "receipt.json",
    )

    assert (receipt["status"], receipt["outcome"], receipt["failed_stage"]) == (
        "failed", "environment_failure", "transaction"
    )
    assert receipt["failure"] == "ModuleNotFoundError: missing dependency"


def test_bounded_controller_runs_one_attempt_without_automatic_deep(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []
    packet = semantic_intent_packet()
    monkeypatch.setattr(
        rescue,
        "run_final_adjudication_from_hypotheses",
        lambda **kwargs: (
            calls.append(dict(kwargs)) or _final_adjudication_receipt(packet),
            None,
        ),
    )
    monkeypatch.setattr(
        rescue,
        "_assessment_result",
        lambda **_: (deepcopy(packet["materiality_assessment"]), ""),
    )
    monkeypatch.setattr(
        rescue,
        "_finalize_author",
        lambda **_: {"packet": deepcopy(packet), "candidate": {"typed": True}},
    )
    monkeypatch.setattr(
        rescue,
        "_compile_packet",
        lambda **_: verified_transaction_receipt_fixture(
            packet, prompt=SEMANTIC_PROMPT
        ),
    )
    monkeypatch.setattr(rescue, "elapsed_ms", lambda _: 10_000)
    receipt = rescue.run_rescue_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "bounded.json",
        standard_failure_receipt=_deadline_standard_handoff(),
    )

    assert (receipt["status"], receipt["tier"], receipt["outcome"]) == (
        "completed", "rescue", "commit"
    )
    assert calls[0]["budget_seconds"] == 26
    assert calls[0]["topology_mode"] == "adaptive"
    assert calls[0]["critic"] == _deadline_standard_handoff()["materiality_critic"]
    assert calls[0]["source"] == _deadline_standard_handoff()["source_hypothesis"]
    assert receipt["automatic_deep_tier"] is False
    assert receipt["wall_ms"] == 63_000
    assert receipt["model_call_count"] == 4
    assert receipt["mechanism_execution"]["tier"] == "rescue"
    assert receipt["mechanism_execution"]["entry_reason"] == (
        "reusable_standard_handoff"
    )


def test_typed_completion_handoff_uses_source_pair_adjudication_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet = semantic_intent_packet()
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        rescue,
        "run_source_pair_adjudication",
        lambda **kwargs: (
            calls.append(dict(kwargs)) or _final_adjudication_receipt(packet)
        ),
    )
    monkeypatch.setattr(
        rescue,
        "_assessment_result",
        lambda **_: (deepcopy(packet["materiality_assessment"]), ""),
    )
    monkeypatch.setattr(
        rescue,
        "_finalize_author",
        lambda **_: {"packet": deepcopy(packet), "candidate": {"typed": True}},
    )
    monkeypatch.setattr(
        rescue,
        "_compile_packet",
        lambda **_: verified_transaction_receipt_fixture(
            packet, prompt=SEMANTIC_PROMPT
        ),
    )
    monkeypatch.setattr(rescue, "elapsed_ms", lambda _: 10_000)

    receipt = rescue.run_rescue_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "typed-rescue.json",
        standard_failure_receipt=_typed_completion_handoff(),
    )

    assert (receipt["status"], receipt["tier"], receipt["outcome"]) == (
        "completed",
        "rescue",
        "commit",
    )
    assert len(calls) == 1
    assert calls[0]["source_receipt"] == _typed_completion_handoff()[
        "source_hypothesis"
    ]
    assert receipt["wall_ms"] == 40_000
    assert receipt["model_call_count"] == 4


def test_source_pair_rescue_excludes_only_the_independently_invalid_hypothesis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def admit(candidate: Mapping[str, object], **_: object) -> tuple[dict, dict]:
        if candidate["mode"] == "source_only":
            raise ValueError("workflow transition does not change state")
        return {"mode": "full_graph"}, {"status": "passed"}

    monkeypatch.setattr(source_pair, "admit_source_only_authority", admit)
    monkeypatch.setattr(
        source_pair,
        "admit_partitioned_candidate",
        lambda candidate, **_: (
            {"completion": candidate["completion"]},
            {"compiled": candidate["source"]},
            [],
            {"status": "passed"},
        ),
    )

    admitted = source_pair._admissible_sources(
        {
            "host_profile": "codex",
            "hypothesis_candidates": [
                {
                    "hypothesis_mode": "full_graph",
                    "candidate": {"mode": "full_graph", "completion": {}},
                },
                {
                    "hypothesis_mode": "source_only",
                    "candidate": {"mode": "source_only", "completion": {}},
                },
            ]
        },
        decision={},
        evidence_sources={"operator_prompt": "Prompt", "operator_edit": ""},
    )

    assert tuple(admitted) == ("full_graph",)


def test_source_pair_rescue_settles_only_independently_discarded_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    confirmed = [{"label": "retired label", "source_refs": []}]
    monkeypatch.setattr(
        source_pair, "source_candidate_discarded_refs", lambda candidate: [candidate]
    )
    monkeypatch.setattr(
        source_pair,
        "independently_confirmed_discarded_refs",
        lambda first, second, **_: confirmed if first and second else [],
    )
    monkeypatch.setattr(
        source_pair,
        "settle_independently_confirmed_discarded_materiality_refs",
        lambda decision, **kwargs: {
            **decision,
            "settled_discarded": kwargs["discarded_source_refs"],
        },
    )

    settled = source_pair._settled_pair_materiality_decision(
        {"outcome": "authorize"},
        source_receipt={
            "hypothesis_candidates": [
                {"candidate": {"candidate": "full"}},
                {"candidate": {"candidate": "source"}},
            ]
        },
        evidence_sources={"operator_prompt": "Prompt", "operator_edit": ""},
    )

    assert settled["settled_discarded"] == confirmed


def test_source_pair_rescue_never_reauthors_when_both_sources_are_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        source_pair,
        "_settled_pair_materiality_decision",
        lambda decision, **_: dict(decision),
    )
    monkeypatch.setattr(source_pair, "_admissible_sources", lambda *_, **__: {})
    monkeypatch.setattr(
        source_pair,
        "run_structured_host",
        lambda **kwargs: calls.append(dict(kwargs)),
    )
    with pytest.raises(ValueError, match="fresh graph authorship is forbidden"):
        source_pair.run_source_pair_adjudication(
            corpus_path=_corpus(tmp_path),
            case_id="claim-desk",
            critic=_critic_receipt(semantic_intent_packet()),
            source_receipt={
                "hypothesis_candidates": [
                    {
                        "hypothesis_mode": "full_graph",
                        "candidate": {"source": {"candidate": "full"}},
                    },
                    {
                        "hypothesis_mode": "source_only",
                        "candidate": {"source": {"candidate": "source"}},
                    },
                ]
            },
            host_profile="codex",
            model="gpt-5.6-sol",
            reasoning_effort="low",
            budget_seconds=26,
        )
    assert calls == []


def test_source_pair_accepts_one_exact_ref_for_one_material_question(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet = semantic_intent_packet()
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        source_pair,
        "_settled_pair_materiality_decision",
        lambda decision, **_: dict(decision),
    )
    monkeypatch.setattr(
        source_pair,
        "_admissible_sources",
        lambda *_, **__: {
            "source_only": {
                "compiled_source": {},
                "admitted": {"completion": {}},
                "compiled_author_output": {},
                "source_candidate_rejections": [],
            }
        },
    )
    monkeypatch.setattr(source_pair, "_source_pair_schema", lambda **_: {})
    monkeypatch.setattr(
        source_pair,
        "run_structured_host",
        lambda **kwargs: (
            calls.append(dict(kwargs))
            or (
                {
                    "version": source_pair.SOURCE_PAIR_ADJUDICATION_VERSION,
                    "source_selection": "clarification_required",
                    "clarification": {
                        "question": "Which result should be visible?",
                        "fields": ["visible_result"],
                        "source_refs": [{"exact": True}],
                    },
                },
                {},
                4_000,
            )
        ),
    )
    monkeypatch.setattr(
        source_pair,
        "require_semantic_source_refs",
        lambda *_, **__: [{"exact": True}],
    )
    monkeypatch.setattr(
        source_pair,
        "clarification_from_source_ambiguity",
        lambda decision, **_: {**decision, "clarified": True},
    )

    receipt = source_pair.run_source_pair_adjudication(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        critic=_critic_receipt(packet),
        source_receipt={"hypothesis_candidates": [{"candidate": {}}]},
        host_profile="codex",
        model="gpt-5.6-sol",
        reasoning_effort="low",
        budget_seconds=26,
    )

    assert receipt["source_status"] == "not_applicable"
    assert "sole admitted source hypothesis" in str(calls[0]["prompt"])


def test_source_pair_selects_one_existing_candidate_without_completion_authorship(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet = semantic_intent_packet()
    calls: list[dict[str, object]] = []
    selected = {
        "compiled_source": {"facts": ["sealed-source"]},
        "admitted": {"completion": {"internal_systems": ["sealed-system"]}},
        "compiled_author_output": {"status": "passed"},
        "source_candidate_rejections": [],
    }
    monkeypatch.setattr(
        source_pair,
        "_settled_pair_materiality_decision",
        lambda decision, **_: dict(decision),
    )
    monkeypatch.setattr(
        source_pair,
        "_admissible_sources",
        lambda *_, **__: {"full_graph": selected},
    )
    monkeypatch.setattr(
        source_pair,
        "source_candidate_discarded_refs",
        lambda _: [],
    )
    monkeypatch.setattr(
        source_pair,
        "run_structured_host",
        lambda **kwargs: (
            calls.append(dict(kwargs))
            or (
                {
                    "version": source_pair.SOURCE_PAIR_ADJUDICATION_VERSION,
                    "source_selection": "full_graph",
                    "clarification": {
                        "question": "",
                        "fields": [],
                        "source_refs": [],
                    },
                },
                {},
                2_000,
            )
        ),
    )

    receipt = source_pair.run_source_pair_adjudication(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        critic=_critic_receipt(packet),
        source_receipt={"hypothesis_candidates": [{"candidate": {}}]},
        host_profile="codex",
        model="gpt-5.6-sol",
        reasoning_effort="low",
        budget_seconds=26,
    )

    assert calls[0]["schema"]["required"] == [
        "version",
        "source_selection",
        "clarification",
    ]
    assert "completion" not in calls[0]["schema"]["properties"]
    assert "reuse that already validated candidate unchanged" in str(
        calls[0]["prompt"]
    )
    assert receipt["candidate"] == {
        "source": selected["compiled_source"],
        "completion": selected["admitted"]["completion"],
    }


def test_final_adjudication_deadline_does_not_trigger_retry_or_deep(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        rescue,
        "run_final_adjudication_from_hypotheses",
        lambda **_: (
            None,
            ("deadline", "final_graph_adjudication", "final timed out"),
        ),
    )
    monkeypatch.setattr(rescue, "elapsed_ms", lambda _: 32_000)
    receipt = rescue.run_rescue_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "bounded.json",
        standard_failure_receipt=_deadline_standard_handoff(),
    )
    assert (receipt["status"], receipt["tier"], receipt["outcome"]) == (
        "failed", "failed", "rescue_deadline_exceeded"
    )
    assert receipt["automatic_deep_tier"] is False


def test_rescue_rejects_missing_reusable_standard_handoff(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="reusable standard-path handoff"):
        rescue.run_rescue_pipeline(
            corpus_path=_corpus(tmp_path),
            case_id="claim-desk",
            output_path=tmp_path / "bounded.json",
            standard_failure_receipt={
                "case_id": "claim-desk",
                "mechanism_execution": semantic_execution_evidence(
                    host_profile="codex",
                    tier="standard",
                    status="failed",
                    outcome="environment_failure",
                    wall_ms=1,
                    model_call_count=1,
                    restart_count=0,
                    implementation_fingerprint_sha256=greenfield_runtime_source_fingerprint(),
                ),
            },
        )


def test_rescue_rejects_implementation_drift(tmp_path: Path) -> None:
    handoff = _deadline_standard_handoff()
    handoff["mechanism_execution"]["implementation_fingerprint_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="different implementation bytes"):
        rescue.run_rescue_pipeline(
            corpus_path=_corpus(tmp_path),
            case_id="claim-desk",
            output_path=tmp_path / "bounded.json",
            standard_failure_receipt=handoff,
        )


def test_standard_mechanism_has_no_regex_stack_or_retired_combined_authority() -> None:
    roots = [
        Path("scripts/release/greenfield_semantic_authoring_wave.py"),
        Path("scripts/release/greenfield_semantic_final_graph_author.py"),
        Path("scripts/release/greenfield_semantic_materiality_screen_experiment.py"),
        Path("scripts/release/greenfield_semantic_source_graph_author.py"),
        Path("scripts/release/greenfield_semantic_standard_path_experiment.py"),
        Path("scripts/release/greenfield_semantic_standard_pipeline_experiment.py"),
        Path("scripts/release/greenfield_semantic_rescue_pipeline.py"),
        Path("scripts/release/greenfield_semantic_source_pair_adjudicator.py"),
        Path("scripts/release/greenfield_semantic_standard_prompts.py"),
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_parallel_materiality.py"),
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_source_authoring.py"),
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_final_adjudication.py"),
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_layered_authoring.py"),
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_narrative_projection.py"),
    ]
    banned = {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
    combined = ""
    for source in roots:
        text = source.read_text(encoding="utf-8")
        combined += text
        tree = ast.parse(text)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert imports.isdisjoint(banned)
    for retired in (
        "run_challenged_source_author",
        "challenged_source_graph_prompt",
        "run_materiality_source_case",
        "materiality_source_graph",
        "semantic_challenged_graph_completion_schema",
        "select_independent_materiality_decision",
        "run_source_graph_case",
        "run_graph_completion_case",
        "run_source_graph_reconciliation",
        "reconciled_source_graph_prompt",
        "completion_graph_prompt",
        "automatic_deep_tier\": True",
    ):
        assert retired not in combined
    assert "admit_source_candidates_by_materiality" not in roots[0].read_text(
        encoding="utf-8"
    )
    standard_path_source = roots[4].read_text(encoding="utf-8")
    assert standard_path_source.count("run_partitioned_graph_hypothesis(") == 1
    assert standard_path_source.count("run_source_graph_hypothesis(") == 1


def _deadline_standard_handoff() -> dict:
    packet = semantic_intent_packet()
    source = {**_source_hypothesis_receipt(), "authority_used": False}
    return {
        "case_id": "claim-desk",
        "wall_ms": 53_000,
        "failed_stage": "final_graph_adjudication",
        "materiality_critic": _critic_receipt(packet),
        "source_hypothesis": source,
        "mechanism_execution": semantic_execution_evidence(
            host_profile="codex",
            tier="standard",
            status="rescue_required",
            outcome="standard_deadline_exceeded",
            wall_ms=53_000,
            model_call_count=3,
            restart_count=0,
            implementation_fingerprint_sha256=greenfield_runtime_source_fingerprint(),
        ),
    }


def _typed_completion_handoff() -> dict:
    packet = semantic_intent_packet()
    source = {
        **_source_hypothesis_receipt(),
        "validation_status": "reusable_source_pair",
        "authority_used": False,
    }
    return {
        "case_id": "claim-desk",
        "wall_ms": 30_000,
        "failed_stage": "graph_completion",
        "materiality_critic": _critic_receipt(packet),
        "source_hypothesis": source,
        "mechanism_execution": semantic_execution_evidence(
            host_profile="codex",
            tier="standard",
            status="rescue_required",
            outcome="typed_standard_handoff",
            wall_ms=30_000,
            model_call_count=3,
            restart_count=0,
            implementation_fingerprint_sha256=greenfield_runtime_source_fingerprint(),
        ),
    }


def _final_adjudication_receipt(packet: dict) -> dict:
    return {
        "stage": "final_graph_adjudication",
        "case_id": "claim-desk",
        "host_profile": "codex",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "model_budget_seconds": 32,
        "wall_ms": 9_000,
        "usage": {},
        "model_call_count": 1,
        "materiality_decision": _decision(packet),
        "source_status": "approved",
        "findings": [],
        "discarded_source_refs": [],
        "candidate": {"source": {}, "completion": {}},
        "validation_status": "passed",
        "validation_error": "",
        "adjudicator_run_id": "standard:final-graph-adjudicator:" + "a" * 64,
    }


def _final_adjudication_result(packet: dict) -> dict:
    clarification = packet["materiality_assessment"]["decision"] == "clarification_required"
    return {
        "decision": _decision(packet),
        "adjudication": {
            "source_status": "not_applicable" if clarification else "approved",
            "findings": [],
            "discarded_source_refs": [],
            "source": {"version": "typed-source", "facts": [], "relations": []},
            "completion": {"version": "typed-completion"},
        },
        "usage": {},
        "wall_ms": 1_000,
        "prompt_text": "final adjudication",
    }


def _critic_receipt(packet: dict) -> dict:
    return {
        "stage": "materiality_critic",
        "case_id": "claim-desk",
        "decision": _decision(packet),
        "host_profile": "codex",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "model_call_count": 1,
        "usage": {},
        "wall_ms": 1_000,
        "validation_status": "passed",
        "prompt_sha256": hashlib.sha256(SEMANTIC_PROMPT.encode("utf-8")).hexdigest(),
    }


def _source_hypothesis_receipt() -> dict:
    return {
        "stage": "source_hypothesis",
        "case_id": "claim-desk",
        "source": _empty_source_graph(),
        "model_call_count": 2,
        "host_profile": "codex",
        "model": "gpt-5.5",
        "reasoning_effort": "low",
        "usage": {},
        "wall_ms": 1_000,
        "prompt_text": "source hypothesis",
        "validation_status": "passed",
        "authority_used": False,
        "selected_run_index": 1,
        "hypothesis_runs": [
            {
                "run_index": 0,
                "hypothesis_mode": "full_graph",
                "status": "comparison_passed",
                "wall_ms": 1_000,
                "usage": {},
            },
            {
                "run_index": 1,
                "hypothesis_mode": "source_only",
                "status": "selected",
                "wall_ms": 1_000,
                "usage": {},
            },
        ],
    }


def _partitioned_author_receipt(packet: dict) -> dict:
    return {
        "stage": "partitioned_graph_admission",
        "case_id": "claim-desk",
        "host_profile": "codex",
        "model": "gpt-5.5",
        "reasoning_effort": "low",
        "model_budget_seconds": 48,
        "wall_ms": 0,
        "usage": {},
        "model_call_count": 0,
        "materiality_decision": _decision(packet),
        "source_status": (
            "not_applicable"
            if packet["materiality_assessment"]["decision"] == "clarification_required"
            else "approved"
        ),
        "findings": [],
        "discarded_source_refs": [],
        "candidate": {"source": _empty_source_graph(), "completion": {}},
        "compiled_author_output": {"typed_graph": True},
        "validation_status": "passed",
        "validation_error": "",
        "adjudicator_run_id": "standard:partitioned-graph-author:" + "a" * 64,
    }


def _decision(packet: dict) -> dict:
    assessment = packet["materiality_assessment"]
    fields = {
        row["field"]: {
            key: deepcopy(value) for key, value in row.items() if key != "field"
        }
        for row in assessment["fields"]
    }
    if assessment["decision"] == "clarification_required":
        clarification = assessment["clarification"]
        fields[clarification["field"]] = {
            "status": "explicit",
            "source_refs": deepcopy(clarification["source_refs"]),
            "alternatives": [],
        }
    return {
        "version": PARALLEL_MATERIALITY_DECISION_VERSION,
        "outcome": {
            "decision": assessment["decision"],
            "clarification": deepcopy(assessment["clarification"]),
        },
        "fields": fields,
    }


def _source_graph_with_ambiguity() -> dict:
    def ref(quote: str) -> dict[str, object]:
        return {
            "source_id": "operator_prompt",
            "quote": quote,
            "occurrence": 1,
        }

    source = _empty_source_graph()
    source["path"]["identities"] = [
        {
            "label": "Claim Desk",
            "source_title": "claim desk",
            "source_refs": [ref(IDENTITY_EVIDENCE)],
        }
    ]
    source["path"]["workflow_steps"] = [
        {
            "owner": {"kind": "product"},
            "steps": [
                {
                    "label": "Claim one ready card",
                    "action": "claim one ready card",
                    "action_phrase": "Claim one ready card.",
                    "source_refs": [ref(PATH_EVIDENCE)],
                }
            ],
        }
    ]
    source["path"]["visible_outputs"] = []
    source["boundary"]["ambiguities"] = [
        {
            "label": "Observable result is unresolved",
            "materiality_field": "visible_result",
            "question": "What observable result should the consumer receive?",
            "source_refs": [ref(PATH_EVIDENCE)],
        }
    ]
    return source


def _empty_source_graph() -> dict:
    return combine_source_authoring_partitions(
        {
            "version": SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
            "path": {**{name: [] for name in SOURCE_PATH_COLLECTIONS}, "relations": {}},
        },
        {
            "version": SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
            "boundary": {
                **{name: [] for name in SOURCE_BOUNDARY_COLLECTIONS}, "relations": {},
            },
        },
    )


def _corpus(tmp_path: Path) -> Path:
    path = tmp_path / "corpus.json"
    path.write_text(
        json.dumps({"cases": [{"case_id": "claim-desk", "prompt": SEMANTIC_PROMPT}]}),
        encoding="utf-8",
    )
    return path
