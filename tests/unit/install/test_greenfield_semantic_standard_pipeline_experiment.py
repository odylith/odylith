from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import greenfield_semantic_clarification_author as clarification_author
import greenfield_semantic_materiality_screen_experiment as materiality_screen
import greenfield_semantic_source_graph_author as source_author
import greenfield_semantic_rescue_pipeline as rescue
import greenfield_semantic_standard_path_experiment as stages
import greenfield_semantic_standard_pipeline_experiment as pipeline
import greenfield_semantic_standard_prompts as prompts
from greenfield_semantic_pipeline_evidence import require_successful_pipeline_evidence
from greenfield_semantic_release_support import greenfield_runtime_source_fingerprint
from greenfield_semantic_structured_host import HostStageCancelled, HostStageTimeout
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    standard_host_stage_profile,
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
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
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
        "version": "odylith.greenfield.standard-host-stage-profile.v2",
        "host_profile": "codex",
        "critic_model": "gpt-5.6-sol",
        "critic_reasoning_effort": "low",
        "source_model": "gpt-5.6-luna",
        "source_reasoning_effort": "low",
        "completion_model": "gpt-5.6-luna",
        "completion_reasoning_effort": "low",
    }
    assert standard_host_stage_profile("claude") == {
        "version": "odylith.greenfield.standard-host-stage-profile.v2",
        "host_profile": "claude",
        "critic_model": "claude-opus-4-6",
        "critic_reasoning_effort": "low",
        "source_model": "claude-opus-4-6",
        "source_reasoning_effort": "low",
        "completion_model": "claude-opus-4-6",
        "completion_reasoning_effort": "low",
    }
    assert pipeline.standard_budget_contract() == {
        "tier": "standard",
        "deadline_seconds": 60,
        "comparison": "strictly_less_than",
        "parallel_materiality_and_source_seconds": 34,
        "semantic_authoring_shared_seconds": 54,
        "post_first_wave_completion_seconds": "remaining shared semantic budget",
        "packet_and_transaction_reserve_seconds": 5,
        "critical_path_seconds": 59,
        "retries": 0,
        "automatic_deep_tier": False,
        "minimum_standard_author_seconds": 20,
        "completion_topology": "single_system",
    }
    assert rescue.rescue_budget_contract(
        prior_standard_failure_sha256="a" * 64
    ) == {
        "tier": "rescue",
        "deadline_seconds": 90,
        "comparison": "less_than_or_equal",
        "parallel_materiality_and_source_seconds": 48,
        "semantic_authoring_shared_seconds": 84,
        "post_first_wave_completion_seconds": "remaining shared semantic budget",
        "packet_and_transaction_reserve_seconds": 5,
        "critical_path_seconds": 89,
        "retries": 0,
        "automatic_deep_tier": False,
        "minimum_completion_seconds": 20,
        "completion_topology": "adaptive",
        "prior_standard_failure_sha256": "a" * 64,
    }


def test_source_and_completion_authorities_are_disjoint() -> None:
    catalog = semantic_evidence_block_catalog(
        {"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""}
    )
    path_prompt = prompts.source_path_prompt(
        prompt_text=SEMANTIC_PROMPT,
        evidence_catalog=catalog,
        model_budget_seconds=34,
    )
    boundary_prompt = prompts.source_boundary_prompt(
        prompt_text=SEMANTIC_PROMPT,
        evidence_catalog=catalog,
        model_budget_seconds=34,
    )
    completion_prompt = prompts.completion_graph_prompt(
        source={"version": "typed-source", "facts": [], "relations": []},
        citation_registry={
            "citation.0": {"fact_ids": ("identity.0",), "source_ref": {}}
        },
        edge_object_ids={
            "depends_on": (), "implements": (), "constrained_by": (), "excludes": (),
        },
        model_budget_seconds=25,
        topology_mode="single_system",
    )

    assert "Do not decide materiality" in path_prompt
    assert "one complete typed source-path partition" in path_prompt
    assert "source_boundary" not in path_prompt
    assert "one complete typed source-boundary partition" in boundary_prompt
    assert "source_path" not in boundary_prompt
    assert "SOURCE_GRAPH" in completion_prompt
    assert "OPERATOR_PROMPT" not in completion_prompt
    assert "Materiality is already settled" in completion_prompt
    assert "materiality_field_semantics" not in completion_prompt
    assert "challenge_decision" not in completion_prompt
    assert "clarification_required" not in completion_prompt
    assert "exactly one cohesive result system" in completion_prompt
    assert "never invent an internal adapter" in completion_prompt


def test_source_author_emits_source_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _empty_source_graph()
    calls: list[str] = []

    def host(**kwargs: object) -> tuple[dict, dict, int]:
        prefix = str(kwargs["temporary_prefix"])
        calls.append(prefix)
        if prefix == "odylith-source-path-author-":
            result = {
                "version": SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
                "path": deepcopy(source["path"]),
            }
        else:
            result = {
                "version": SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
                "boundary": deepcopy(source["boundary"]),
            }
        return result, {"model_calls": 1}, 500

    monkeypatch.setattr(source_author, "run_structured_host", host)
    monkeypatch.setattr(
        source_author, "compile_source_partitioned_graph", lambda value: value
    )
    catalog = semantic_evidence_block_catalog(
        {"operator_prompt": SEMANTIC_PROMPT, "operator_edit": ""}
    )
    result = source_author.run_source_graph_author(
        prompt_text=SEMANTIC_PROMPT,
        evidence_catalog=catalog,
        model="frontier",
        reasoning_effort="medium",
        budget_seconds=34,
    )

    assert result["source"] == source
    assert result["phase_wall_ms"] == {
        "source_path": 500,
        "source_boundary": 500,
    }
    assert set(calls) == {
        "odylith-source-path-author-",
        "odylith-source-boundary-author-",
    }
    assert len(result["usage_rows"]) == 2
    assert "decision" not in result


def test_clarification_author_independently_seals_one_question(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_packet = semantic_clarification_packet()
    clarification = source_packet["materiality_assessment"]["clarification"]

    def structured_host(**kwargs: object) -> tuple[dict, dict, int]:
        schema = kwargs["schema"]
        assert isinstance(schema, dict)
        assert schema["properties"]["unsupported_additions"] == {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 0,
        }
        return (
            {
                "version": clarification_author.CLARIFICATION_AUTHOR_VERSION,
                "decision": "approve",
                "field": clarification["field"],
                "question": clarification["question"],
                "evidence_support": "source_supported",
                "one_question_sufficient": True,
                "unsupported_additions": [],
                "rationale": "The prompt leaves exactly this release boundary unresolved.",
            },
            {"input_tokens": 1, "output_tokens": 1},
            500,
        )

    monkeypatch.setattr(
        clarification_author,
        "run_structured_host",
        structured_host,
    )

    receipt = clarification_author.run_clarification_author(
        case_id="claim-desk",
        prompt_text=SEMANTIC_PROMPT,
        assessment=source_packet["materiality_assessment"],
        critic_run_id="critic-run",
        host_profile="codex",
        model="gpt-5.6-luna",
        reasoning_effort="low",
        model_budget_seconds=20,
        output_path=tmp_path / "clarification-author.json",
    )

    assert receipt["model_call_count"] == 1
    assert receipt["packet"]["semantic_intent"]["status"] == (
        "clarification_required"
    )
    assert receipt["packet"]["semantic_intent"]["facts"] == []
    assert receipt["packet"]["author_run"]["author_run_id"] == receipt["author_run_id"]


def test_materiality_screen_selects_handles_and_never_authors_quote_bytes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    candidate = _decision(semantic_intent_packet())

    def handles(value: object) -> object:
        if isinstance(value, dict):
            if set(value) == {"source_id", "quote", "occurrence"}:
                return {"ref_id": "operator_prompt.block.0"}
            return {key: handles(nested) for key, nested in value.items()}
        if isinstance(value, list):
            return [handles(nested) for nested in value]
        return value

    def structured_host(**kwargs: object) -> tuple[dict, dict, int]:
        schema = kwargs["schema"]
        assert "ref_id" in json.dumps(schema)
        assert '"quote"' not in json.dumps(schema)
        return handles(candidate), {"input_tokens": 1, "output_tokens": 1}, 500  # type: ignore[return-value]

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


def test_clarification_author_rejection_is_a_typed_attempt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_packet = semantic_clarification_packet()
    clarification = source_packet["materiality_assessment"]["clarification"]
    monkeypatch.setattr(
        clarification_author,
        "run_structured_host",
        lambda **_: (
            {
                "version": clarification_author.CLARIFICATION_AUTHOR_VERSION,
                "decision": "reject",
                "field": clarification["field"],
                "question": clarification["question"],
                "evidence_support": "source_insufficient",
                "one_question_sufficient": False,
                "unsupported_additions": [],
                "rationale": "The proposed question does not settle the material boundary.",
            },
            {"input_tokens": 1, "output_tokens": 1},
            500,
        ),
    )

    with pytest.raises(
        clarification_author.ClarificationStageIncomplete,
        match="rejected",
    ) as caught:
        clarification_author.run_clarification_author(
            case_id="claim-desk",
            prompt_text=SEMANTIC_PROMPT,
            assessment=source_packet["materiality_assessment"],
            critic_run_id="critic-run",
            host_profile="codex",
            model="gpt-5.6-luna",
            reasoning_effort="low",
            model_budget_seconds=20,
            output_path=tmp_path / "clarification-author.json",
        )

    assert caught.value.failure_kind == "typed"
    assert caught.value.receipt["model_call_count"] == 1
    assert caught.value.receipt["validation_status"] == "failed"


def test_completion_author_cannot_reopen_materiality(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authorized = _decision(semantic_intent_packet())
    source = _empty_source_graph()
    monkeypatch.setattr(stages, "source_with_authorized_assumptions", lambda value, _: value)
    monkeypatch.setattr(stages, "require_authorized_source_assumptions", lambda *_: None)
    monkeypatch.setattr(stages, "compile_source_partitioned_graph", lambda value: value)
    monkeypatch.setattr(
        stages,
        "semantic_completion_citation_registry",
        lambda _: {
            "citation.0": {
                "source_ref": {
                    "source_id": "operator_prompt",
                    "quote": SEMANTIC_PROMPT,
                    "occurrence": 1,
                },
                "fact_ids": ("identity.0",),
            }
        },
    )
    monkeypatch.setattr(
        stages,
        "semantic_architecture_edge_object_ids",
        lambda _: {
            "depends_on": (), "implements": (), "constrained_by": (), "excludes": (),
        },
    )
    monkeypatch.setattr(
        stages, "bind_semantic_evidence_blocks", lambda value, **_: deepcopy(value)
    )
    monkeypatch.setattr(
        stages, "accepted_partitioned_evidence_catalog", lambda *_, **__: {}
    )
    monkeypatch.setattr(
        stages,
        "apply_semantic_implementation_assignments",
        lambda value, **_: deepcopy(value),
    )
    monkeypatch.setattr(
        stages,
        "run_structured_host",
        lambda **_: ({"typed_completion": True}, {"model_calls": 1}, 700),
    )

    receipt = stages.run_graph_completion_case(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        model="completion-model",
        reasoning_effort="low",
        output_path=tmp_path / "completion.json",
        model_budget_seconds=25,
        resume_source=source,
        materiality_decision=authorized,
        completion_topology="single_system",
    )

    assert "decision" not in receipt
    assert "source_candidate" not in receipt
    assert receipt["candidate"]["source"] == source
    assert receipt["candidate"]["completion"] == {
        "typed_completion": True,
        "clarification": {"question": "", "fields": [], "source_refs": []},
    }


def test_parallel_critic_question_cancels_source_and_never_seals(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    question = semantic_clarification_packet()
    cancelled: list[bool] = []
    monkeypatch.setattr(
        pipeline, "run_screen", lambda **_: _critic_receipt(question)
    )

    def source(**kwargs: object) -> dict:
        event = kwargs["cancel_event"]
        assert hasattr(event, "wait")
        cancelled.append(bool(event.wait(1)))
        raise HostStageCancelled("cancelled")

    monkeypatch.setattr(pipeline, "run_source_graph_case", source)
    monkeypatch.setattr(
        pipeline, "run_graph_completion_case", lambda **_: pytest.fail("must not complete")
    )
    monkeypatch.setattr(
        pipeline,
        "run_clarification_author",
        lambda **_: {
            "stage": "clarification_author",
            "case_id": "claim-desk",
            "host_profile": "codex",
            "model": "gpt-5.6-luna",
            "reasoning_effort": "low",
            "packet": deepcopy(question),
            "model_call_count": 1,
            "usage": {},
            "validation_status": "passed",
        },
    )
    receipt = pipeline.run_standard_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "receipt.json",
    )

    assert (receipt["status"], receipt["outcome"]) == ("completed", "clarify")
    assert cancelled == [True]
    assert receipt["source_graph"]["authority_used"] is False
    assert receipt["source_graph"]["validation_status"] == "cancelled"
    assert receipt["packet"] == question
    assert receipt["model_call_count"] == 4
    assert receipt["mechanism_execution"]["mechanism_id"] == (
        ACTIVE_SEMANTIC_MECHANISM_ID
    )
    assert receipt["mechanism_execution"]["tier"] == "standard"


def test_parallel_commit_uses_immutable_source_and_three_role_receipts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet = semantic_intent_packet()
    critic = _critic_receipt(packet)
    source = _source_receipt()
    captured: dict[str, object] = {}
    monkeypatch.setattr(pipeline, "run_screen", lambda **_: critic)
    monkeypatch.setattr(pipeline, "run_source_graph_case", lambda **_: source)
    monkeypatch.setattr(
        pipeline,
        "admit_source_candidates_by_materiality",
        lambda _, value, **__: {
            "version": "test-admission",
            "source": value,
            "rejected_candidates": [],
        },
    )
    monkeypatch.setattr(
        pipeline, "require_materiality_source_coverage", lambda *_, **__: None
    )
    monkeypatch.setattr(pipeline, "compile_source_partitioned_graph", lambda _: {})
    monkeypatch.setattr(
        pipeline,
        "run_graph_completion_case",
        lambda **kwargs: captured.update(kwargs) or _author_receipt(packet),
    )
    monkeypatch.setattr(
        pipeline,
        "_finalize_author",
        lambda **_: {"packet": deepcopy(packet), "candidate": {"typed": True}},
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
    assert captured["resume_source"] == combine_source_authoring_partitions(
        source["source_path"], source["source_boundary"]
    )
    assert captured["materiality_decision"] == critic["decision"]
    assert captured["completion_topology"] == "single_system"
    assert receipt["source_graph"]["authority_used"] is True
    assert receipt["model_call_count"] == 4
    assert receipt["restart_count"] == 0
    assert receipt["mechanism_execution"]["mechanism_id"] == (
        ACTIVE_SEMANTIC_MECHANISM_ID
    )
    assert receipt["mechanism_execution"]["model_call_count"] == 4
    _, evidence = require_successful_pipeline_evidence(
        receipt,
        case_id="claim-desk",
        prompt=SEMANTIC_PROMPT,
        semantic_artifact=packet,
    )
    assert evidence["execution_tier"] == "standard"
    assert evidence["model_calls"] == 4


def test_packet_records_host_identity_instead_of_model_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        pipeline,
        "compile_partitioned_authoring_graph",
        lambda *_, **__: {"typed_graph": True},
    )

    def packet(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return {"version": "test-packet"}

    monkeypatch.setattr(pipeline, "build_semantic_intent_packet", packet)
    result = pipeline._finalize_author(
        case_id="claim-desk",
        prompt=SEMANTIC_PROMPT,
        assessment={"decision": "authorize_graph"},
        author={"candidate": {"typed": True}},
        critic_run_id="critic-run",
        semantic_host_profile="claude",
    )

    assert captured["kwargs"]["critic_host_profile"] == "claude"
    assert result["packet"] == {"version": "test-packet"}


def test_unavailable_host_counts_every_attempt_and_never_retries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        pipeline,
        "run_screen",
        lambda **_: (_ for _ in ()).throw(RuntimeError("provider unavailable")),
    )
    monkeypatch.setattr(
        pipeline,
        "run_source_graph_case",
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


def test_transaction_environment_failure_returns_typed_outcome(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    packet = semantic_intent_packet()
    monkeypatch.setattr(pipeline, "run_screen", lambda **_: _critic_receipt(packet))
    monkeypatch.setattr(pipeline, "run_source_graph_case", lambda **_: _source_receipt())
    monkeypatch.setattr(
        pipeline,
        "admit_source_candidates_by_materiality",
        lambda _, value, **__: {
            "version": "test-admission",
            "source": value,
            "rejected_candidates": [],
        },
    )
    monkeypatch.setattr(
        pipeline, "require_materiality_source_coverage", lambda *_, **__: None
    )
    monkeypatch.setattr(pipeline, "compile_source_partitioned_graph", lambda _: {})
    monkeypatch.setattr(
        pipeline, "run_graph_completion_case", lambda **_: _author_receipt(packet)
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
    monkeypatch.setattr(
        rescue,
        "run_standard_pipeline",
        lambda **kwargs: calls.append(dict(kwargs))
        or _completed_rescue_attempt(kwargs),
    )
    monkeypatch.setattr(pipeline, "elapsed_ms", lambda _: 70_000)
    receipt = rescue.run_rescue_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "bounded.json",
        standard_failure_receipt=_typed_standard_failure_receipt(),
    )

    assert (receipt["status"], receipt["tier"], receipt["outcome"]) == (
        "completed", "rescue", "commit"
    )
    assert calls[0]["_first_wave_budget"] == 48
    assert calls[0]["_semantic_budget"] == 84
    assert calls[0]["_deadline_seconds"] == 90
    assert calls[0]["_completion_topology"] == "adaptive"
    assert receipt["automatic_deep_tier"] is False
    assert receipt["mechanism_execution"]["tier"] == "rescue"
    assert receipt["mechanism_execution"]["entry_reason"] == (
        "typed_standard_failure"
    )


def test_source_deadline_does_not_trigger_retry_or_deep(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        pipeline, "run_screen", lambda **_: _critic_receipt(semantic_intent_packet())
    )
    monkeypatch.setattr(
        pipeline,
        "run_source_graph_case",
        lambda **_: (_ for _ in ()).throw(HostStageTimeout("source timed out")),
    )
    receipt = rescue.run_rescue_pipeline(
        corpus_path=_corpus(tmp_path),
        case_id="claim-desk",
        output_path=tmp_path / "bounded.json",
        standard_failure_receipt=_typed_standard_failure_receipt(),
    )
    assert (receipt["status"], receipt["tier"], receipt["outcome"]) == (
        "failed", "failed", "standard_deadline_exceeded"
    )
    assert receipt["automatic_deep_tier"] is False


def test_rescue_rejects_missing_typed_standard_failure(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="typed standard-path failure"):
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


def test_standard_mechanism_has_no_regex_stack_or_retired_combined_authority() -> None:
    roots = [
        Path("scripts/release/greenfield_semantic_clarification_author.py"),
        Path("scripts/release/greenfield_semantic_materiality_screen_experiment.py"),
        Path("scripts/release/greenfield_semantic_source_graph_author.py"),
        Path("scripts/release/greenfield_semantic_standard_path_experiment.py"),
        Path("scripts/release/greenfield_semantic_standard_pipeline_experiment.py"),
        Path("scripts/release/greenfield_semantic_rescue_pipeline.py"),
        Path("scripts/release/greenfield_semantic_standard_prompts.py"),
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_parallel_materiality.py"),
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_source_authoring.py"),
        Path("src/odylith/runtime/domain_intelligence/greenfield_semantic_layered_authoring.py"),
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
        "automatic_deep_tier\": True",
    ):
        assert retired not in combined


def _typed_standard_failure_receipt() -> dict:
    return {
        "case_id": "claim-desk",
        "mechanism_execution": semantic_execution_evidence(
            host_profile="codex",
            tier="standard",
            status="rescue_required",
            outcome="typed_standard_failure",
            wall_ms=40_000,
            model_call_count=4,
            restart_count=0,
            implementation_fingerprint_sha256=greenfield_runtime_source_fingerprint(),
        ),
    }


def _completed_rescue_attempt(kwargs: dict[str, object]) -> dict:
    budget = kwargs["_budget_contract"]
    assert isinstance(budget, dict)
    return {
        "status": "completed",
        "outcome": "commit",
        "model_call_count": 4,
        "restart_count": 0,
        "total_tokens": 0,
        "mechanism_execution": semantic_execution_evidence(
            host_profile=str(kwargs["host_profile"]),
            tier="rescue",
            status="completed",
            outcome="commit",
            wall_ms=70_000,
            model_call_count=4,
            restart_count=0,
            implementation_fingerprint_sha256=greenfield_runtime_source_fingerprint(),
            prior_standard_failure_sha256=str(
                budget["prior_standard_failure_sha256"]
            ),
        ),
    }


def _author_receipt(packet: dict) -> dict:
    return {
        "stage": "graph_completion",
        "case_id": "claim-desk",
        "candidate": {"partitioned_author": True},
        "host_profile": "codex",
        "model": "gpt-5.6-luna",
        "reasoning_effort": "low",
        "model_call_count": 1,
        "usage": {},
        "validation_status": "passed",
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


def _source_receipt() -> dict:
    source = _empty_source_graph()
    return {
        "stage": "source_graph",
        "case_id": "claim-desk",
        "source_path": {
            "version": SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
            "path": deepcopy(source["path"]),
        },
        "source_boundary": {
            "version": SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
            "boundary": deepcopy(source["boundary"]),
        },
        "model_call_count": 2,
        "host_profile": "codex",
        "model": "gpt-5.6-luna",
        "reasoning_effort": "low",
        "usage": {},
        "wall_ms": 1_000,
        "validation_status": "passed",
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
