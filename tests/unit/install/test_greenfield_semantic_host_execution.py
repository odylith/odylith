from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_semantic_host_execution as host_execution
from greenfield_semantic_development_evidence import prepare_development_evidence_plan
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    host_execution_profile,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_MANDATORY_CHALLENGES,
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    semantic_materiality_source_ref_catalog,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    semantic_graph_extension_from_intent,
)


def test_host_execution_builds_one_exact_two_stage_segment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path)
    observed: list[str] = []

    def fake_run_stage(**kwargs: Any) -> tuple[dict[str, Any], dict[str, Any], int]:
        stage = kwargs["stage"]
        observed.append(stage)
        output = (
            context["assessment"]
            if stage == "critic"
            else {
                "source_candidate_adjudication": context[
                    "source_candidate_adjudication"
                ],
                "semantic_extension": context["semantic_extension"],
                "self_challenge": _self_challenge(),
            }
        )
        return output, _usage(), 11 if stage == "critic" else 13

    monkeypatch.setattr(host_execution, "_run_stage", fake_run_stage)
    output = tmp_path / "segment.json"
    segment = host_execution.author_development_case(
        corpus_path=context["corpus"],
        evidence_plan_path=context["plan"],
        case_id="claim-desk",
        output_path=output,
        host_binaries={"codex": context["binary"]},
    )

    assert observed == ["critic", "author"]
    assert json.loads(output.read_text(encoding="utf-8")) == segment
    row = segment["cases"][0]
    assert row["outcome"] == "commit"
    assert row["critic_stage"]["execution_profile"] == host_execution_profile("codex")
    assert row["critic_stage"]["host_runtime"] == row["author_stage"]["host_runtime"]
    assert row["critic_stage"]["attempt_count"] == 1
    assert row["author_stage"]["validation_error_repair_count"] == 0


def test_host_execution_stops_after_invalid_critic_without_partial_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path)
    calls = 0

    def invalid_critic(**_kwargs: Any) -> tuple[dict[str, Any], dict[str, Any], int]:
        nonlocal calls
        calls += 1
        assessment = deepcopy(context["assessment"])
        assessment["authoring_contract_sha256"] = "0" * 64
        return assessment, _usage(), 10

    monkeypatch.setattr(host_execution, "_run_stage", invalid_critic)
    output = tmp_path / "must-not-exist.json"
    with pytest.raises(ValueError, match="does not match the authoring contract"):
        host_execution.author_development_case(
            corpus_path=context["corpus"],
            evidence_plan_path=context["plan"],
            case_id="claim-desk",
            output_path=output,
            host_binaries={"codex": context["binary"]},
        )

    assert calls == 1
    assert not output.exists()


def test_codex_jsonl_accepts_reasoning_and_rejects_tool_events(tmp_path: Path) -> None:
    valid = _jsonl_binary(tmp_path / "valid-codex", item_type="reasoning")
    output, usage = host_execution._run_codex(
        binary=valid,
        profile=host_execution_profile("codex"),
        prompt="bounded prompt",
        output_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["ok"],
            "properties": {"ok": {"type": "boolean"}},
        },
        working_root=tmp_path,
        timeout_seconds=10,
    )
    assert output == {"ok": True}
    assert usage == {
        "input_tokens": 10,
        "output_tokens": 6,
        "total_tokens": 16,
        "measurement_basis": "host_runtime_usage_receipt",
    }

    forbidden = _jsonl_binary(tmp_path / "tool-codex", item_type="command_execution")
    with pytest.raises(RuntimeError, match="forbidden tool"):
        host_execution._run_codex(
            binary=forbidden,
            profile=host_execution_profile("codex"),
            prompt="bounded prompt",
            output_schema={"type": "object"},
            working_root=tmp_path,
            timeout_seconds=10,
        )


def _context(tmp_path: Path) -> dict[str, Any]:
    fixture = json.loads(
        (SCRIPTS_ROOT / "fixtures" / "greenfield-semantic-smoke.v12.json").read_text(
            encoding="utf-8"
        )
    )
    corpus = tmp_path / "corpus.json"
    corpus.write_text(
        json.dumps(
            {"cases": [{"case_id": "claim-desk", "prompt": fixture["prompt"]}]},
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    plan = tmp_path / "plan.json"
    prepare_development_evidence_plan(
        corpus_path=corpus,
        host_profiles=["codex"],
        output_path=plan,
    )
    assessment = deepcopy(fixture["packet"]["materiality_assessment"])
    assessment["authoring_contract_sha256"] = semantic_intent_authoring_contract_sha256()
    binary = tmp_path / "codex"
    binary.write_text("#!/bin/sh\necho 'codex-cli test-v1'\n", encoding="utf-8")
    binary.chmod(0o700)
    semantic_extension = _intent_with_citation_handles(
        _extension_from_intent(fixture["packet"]["semantic_intent"]),
        assessment=assessment,
        prompt=fixture["prompt"],
    )
    return {
        "assessment": assessment,
        "binary": binary,
        "corpus": corpus,
        "plan": plan,
        "source_candidate_adjudication": deepcopy(
            fixture["packet"]["source_candidate_adjudication"]
        ),
        "semantic_extension": semantic_extension,
    }


def _extension_from_intent(semantic_intent: dict[str, Any]) -> dict[str, Any]:
    return semantic_graph_extension_from_intent(semantic_intent)


def _intent_with_citation_handles(
    semantic_intent: dict[str, Any],
    *,
    assessment: dict[str, Any],
    prompt: str,
) -> dict[str, Any]:
    catalog = semantic_materiality_source_ref_catalog(
        assessment,
        evidence_sources={"operator_prompt": prompt, "operator_edit": ""},
    )
    ids = {
        (row["source_id"], row["quote"], row["occurrence"]): row["ref_id"]
        for row in catalog
    }
    owners = [semantic_intent["clarification"], *semantic_intent["narratives"]]
    for node in semantic_intent["nodes"]:
        owners.append(node["fact"])
        for kind in (
            "depends_on",
            "implements",
            "constrained_by",
            "excludes",
            "incoming_changes",
        ):
            owners.extend(node[kind])
    for owner in owners:
        owner["source_refs"] = [
            {"ref_id": ids[(row["source_id"], row["quote"], row["occurrence"])]}
            for row in owner["source_refs"]
        ]
    return semantic_intent


def _jsonl_binary(path: Path, *, item_type: str) -> Path:
    item = (
        {"id": "reasoning", "type": "reasoning", "text": "bounded"}
        if item_type == "reasoning"
        else {"id": "tool", "type": item_type, "command": "forbidden"}
    )
    events = [
        {"type": "thread.started", "thread_id": "test"},
        {"type": "turn.started"},
        {"type": "item.completed", "item": item},
        {
            "type": "item.completed",
            "item": {"id": "message", "type": "agent_message", "text": '{"ok":true}'},
        },
        {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 4,
                "reasoning_output_tokens": 2,
            },
        },
    ]
    script = "#!/usr/bin/env python3\nimport json\n"
    script += f"events = {events!r}\n"
    script += "for event in events:\n    print(json.dumps(event))\n"
    path.write_text(script, encoding="utf-8")
    path.chmod(0o700)
    return path


def _self_challenge() -> list[dict[str, str]]:
    return [
        {"challenge": challenge, "status": "passed"}
        for challenge in SEMANTIC_INTENT_MANDATORY_CHALLENGES
    ]


def _usage() -> dict[str, Any]:
    return {
        "input_tokens": 10,
        "output_tokens": 20,
        "total_tokens": 30,
        "measurement_basis": "host_runtime_usage_receipt",
    }
