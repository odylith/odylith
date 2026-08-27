from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import greenfield_semantic_standard_pipeline_experiment as pipeline
import greenfield_semantic_authoring_wave as authoring_wave

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    build_semantic_intent_packet,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    standard_author_profile,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning import (
    semantic_source_meaning_sha256,
)
from tests.unit.runtime.test_greenfield_semantic_source_meaning import PROMPT, _graph
from tests.unit.runtime.test_greenfield_semantic_source_meaning_packet import _run


def _corpus(path: Path) -> Path:
    path.write_text(
        json.dumps({"cases": [{"case_id": "source-meaning", "prompt": PROMPT}]}),
        encoding="utf-8",
    )
    return path


def _author(graph: dict[str, object]) -> dict[str, object]:
    profile = standard_author_profile("codex", 0)
    author_run = {
        **_run(graph),
        "run_id": "standard:source-meaning-author:fixture",
        "model": profile["model"],
        "reasoning_effort": profile["reasoning_effort"],
    }
    return {
        "stage": "source_meaning_author",
        "case_id": "source-meaning",
        "host_profile": "codex",
        "model": profile["model"],
        "reasoning_effort": profile["reasoning_effort"],
        "status": "completed",
        "failure_kind": "",
        "failure": "",
        "graph": graph,
        "graph_sha256": author_run["graph_sha256"],
        "author_run": author_run,
        "usage": author_run["usage"],
        "wall_ms": author_run["wall_ms"],
        "model_call_count": 1,
    }


def test_standard_pipeline_compiles_one_call_transaction(monkeypatch, tmp_path: Path) -> None:
    graph = _graph()
    monkeypatch.setattr(
        pipeline,
        "run_authoring_wave",
        lambda **_: (_author(graph), None),
    )
    receipt = pipeline.run_standard_pipeline(
        corpus_path=_corpus(tmp_path / "corpus.json"),
        case_id="source-meaning",
        output_path=tmp_path / "receipt.json",
    )

    assert receipt["status"] == "completed"
    assert receipt["outcome"] == "commit"
    assert receipt["wall_ms"] < 60_000
    assert receipt["model_call_count"] == 1
    assert receipt["source_meaning_author"]["graph"] == graph
    assert receipt["transaction"]["verified"] is True
    assert receipt["transaction"]["transaction_payload"]["intent_authority"][
        "semantic_source_meaning_graph"
    ] == graph
    for retired in (
        "source_semantic_critic",
        "source_hypothesis",
        "selected_graph_author",
        "materiality_assessment",
    ):
        assert retired not in receipt


def test_standard_pipeline_returns_one_question_without_transaction(
    monkeypatch, tmp_path: Path
) -> None:
    graph = deepcopy(_graph())
    graph["workflow"][0]["entity_effects"] = [
        effect
        for effect in graph["workflow"][0]["entity_effects"]
        if effect["kind"] != "visible_result"
    ]
    graph["entities"] = graph["entities"][:1]
    graph["clarification"] = {
        "required": True,
        "question": "Which visible confirmation should the coordinator receive?",
        "source_refs": [
            {
                "source_id": "operator_prompt",
                "quote": "A shift coordinator claims one ready card.",
                "occurrence": 1,
            }
        ],
    }
    monkeypatch.setattr(
        pipeline,
        "run_authoring_wave",
        lambda **_: (_author(graph), None),
    )
    receipt = pipeline.run_standard_pipeline(
        corpus_path=_corpus(tmp_path / "corpus.json"),
        case_id="source-meaning",
        output_path=tmp_path / "receipt.json",
    )

    assert receipt["status"] == "completed"
    assert receipt["outcome"] == "clarify"
    assert receipt["model_call_count"] == 1
    assert receipt["transaction"] is None
    assert receipt["packet"]["semantic_intent"]["facts"] == []
    assert receipt["packet"]["source_meaning_graph"]["workflow"]


def test_budget_contract_is_strict_54_plus_5() -> None:
    contract = pipeline.standard_budget_contract()
    assert contract["source_meaning_author_max_seconds"] == 54
    assert contract["packet_and_transaction_reserve_seconds"] == 5
    assert contract["critical_path_seconds"] == 59
    assert contract["deadline_seconds"] == 60
    assert contract["comparison"] == "strictly_less_than"
    assert contract["successful_model_call_counts"] == {
        "commit": [1],
        "clarify": [1],
    }


def test_packet_can_compile_directly_without_authoring_helpers(tmp_path: Path) -> None:
    graph = _graph()
    packet = build_semantic_intent_packet(
        graph, prompt=PROMPT, author_run=_run(graph)
    )
    result = pipeline._compile_packet(
        packet=packet, prompt=PROMPT, repo_root=tmp_path / "consumer"
    )
    assert result["verified"] is True
    assert result["transaction_payload"]["prewrite_package"]["proposal"]["intent"]["title"] == (
        "Claim Desk"
    )


def test_working_title_changes_transaction_but_not_accepted_semantic_facts(
    tmp_path: Path,
) -> None:
    graph = _graph()
    retitled = deepcopy(graph)
    retitled["presentation"] = {
        "title": "Coordinator Console",
        "status": "working_assumption",
        "source_refs": [],
    }
    baseline_packet = build_semantic_intent_packet(
        graph, prompt=PROMPT, author_run=_run(graph)
    )
    retitled_packet = build_semantic_intent_packet(
        retitled, prompt=PROMPT, author_run=_run(retitled)
    )
    baseline = pipeline._compile_packet(
        packet=baseline_packet,
        prompt=PROMPT,
        repo_root=tmp_path / "consumer",
    )["transaction_payload"]
    changed = pipeline._compile_packet(
        packet=retitled_packet,
        prompt=PROMPT,
        repo_root=tmp_path / "consumer",
    )["transaction_payload"]

    assert baseline["transaction_hash"] != changed["transaction_hash"]
    assert baseline["intent_authority"]["semantic_intent_sha256"] != changed[
        "intent_authority"
    ]["semantic_intent_sha256"]
    assert baseline["intent_authority"]["semantic_meaning_sha256"] == changed[
        "intent_authority"
    ]["semantic_meaning_sha256"]
    assert baseline["intent_authority"]["product_facts_sha256"] == changed[
        "intent_authority"
    ]["product_facts_sha256"]
    baseline_slug = baseline["prewrite_package"]["proposal"]["intent"]["project_slug"]
    assert baseline_slug == changed["prewrite_package"]["proposal"]["intent"]["project_slug"]
    assert baseline_slug.startswith("consumer-")


def _author_result(graph: dict[str, object]) -> dict[str, object]:
    return {
        "graph": graph,
        "graph_sha256": semantic_source_meaning_sha256(graph),
        "usage": {"input_tokens": 10, "output_tokens": 20},
        "wall_ms": 100,
    }


def test_single_author_wave_fails_closed_on_invalid_graph(
    monkeypatch, tmp_path: Path
) -> None:
    def author(**_kwargs):
        raise ValueError("graph is structurally invalid")

    monkeypatch.setattr(authoring_wave, "run_source_meaning_author", author)
    result, failure = authoring_wave.run_authoring_wave(
        corpus_path=_corpus(tmp_path / "corpus.json"),
        case_id="source-meaning",
        host_profile="codex",
        budget=authoring_wave.AuthoringWaveBudget(54, "single_system"),
    )

    assert failure == (
        "typed",
        "source_meaning_author",
        "graph is structurally invalid",
    )
    assert result is not None
    assert result["failure_kind"] == "typed"
    assert result["graph"] is None
    assert result["model_call_count"] == 1


def test_single_author_wave_returns_unchanged_graph(
    monkeypatch, tmp_path: Path
) -> None:
    graph = _graph()

    def author(**_kwargs):
        return _author_result(graph)

    monkeypatch.setattr(authoring_wave, "run_source_meaning_author", author)
    result, failure = authoring_wave.run_authoring_wave(
        corpus_path=_corpus(tmp_path / "corpus.json"),
        case_id="source-meaning",
        host_profile="codex",
        budget=authoring_wave.AuthoringWaveBudget(54, "single_system"),
    )

    assert failure is None
    assert result is not None
    assert result["stage"] == "source_meaning_author"
    assert result["graph"] == graph
    assert result["model_call_count"] == 1
