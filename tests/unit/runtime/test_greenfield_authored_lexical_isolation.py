"""Public regressions for lexical isolation of model-authored Greenfield intent."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import (
    greenfield_model_intent_authoring,
    greenfield_model_intent_materialization,
    greenfield_proposals_cli,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    combined_prompt_evidence_source,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
)


def _authored_intent(**overrides: Any) -> dict[str, Any]:
    intent: dict[str, Any] = {
        "title": "Harbor Desk",
        "product_story": "Dock attendants need clear berth placement",
        "state_object": "berth occupancy",
        "first_path": (
            "Dock attendant Ivo enters a vessel tag and the product records berth occupancy "
            "before the berth map shows the placement"
        ),
        "proof_boundary": "Verify the placement and retention receipt",
        "problem": "Berth placement is hard to track",
        "customer": "Dock attendants",
        "opportunity": "One reviewable berth workflow",
        "product_view": "Harbor Desk gives dock attendants a berth workflow",
        "success_metrics": ["The berth map shows the placement"],
        "evidence_requirements": ["Source evidence preserves berth history"],
        "operational_constraints": ["Retain source notes for seven years"],
        "component_responsibilities": ["Record berth occupancy"],
        "human_actors": ["Dock attendant Ivo"],
        "external_systems": ["Harbor Ledger"],
        "internal_systems": ["Berth map"],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": ["Do not manage vessel scheduling"],
    }
    intent.update(overrides)
    return intent


def _evidence_source(intent: Mapping[str, Any]) -> str:
    rows: list[str] = []
    for value in intent.values():
        if isinstance(value, list):
            rows.extend(str(item) for item in value)
        else:
            rows.append(str(value))
    return ". ".join(rows) + "."


def _first_path_relations() -> list[dict[str, Any]]:
    return [
        {
            "actor_kind": "human",
            "actor_quote": "Dock attendant Ivo",
            "event_quote": "Dock attendant Ivo enters a vessel tag",
            "action_verb_quote": "enters",
            "target_quote": "a vessel tag",
            "visible_result_quote": "",
            "recovery_path": False,
        },
        {
            "actor_kind": "product",
            "actor_quote": "the product",
            "owner_system_quote": "Berth map",
            "event_quote": "the product records berth occupancy",
            "action_verb_quote": "records",
            "target_quote": "berth occupancy",
            "visible_result_quote": "",
            "recovery_path": False,
        },
        {
            "actor_kind": "product",
            "actor_quote": "the berth map",
            "owner_system_quote": "Berth map",
            "event_quote": "the berth map shows the placement",
            "action_verb_quote": "shows",
            "target_quote": "the placement",
            "visible_result_quote": "the berth map shows the placement",
            "recovery_path": False,
        },
    ]


def _public_propose(
    *,
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
    intent: Mapping[str, Any],
    repair_tier: str = "",
) -> tuple[int, dict[str, Any], StructuredAuthoringProvider]:
    source = _evidence_source(intent)
    staged_evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    provider = StructuredAuthoringProvider(
        authored_response(
            intent,
            evidence_text=staged_evidence,
            first_path_relations=_first_path_relations(),
            component_responsibility_owners=["Berth map"],
        )
    )
    assert staged_evidence
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        lambda **_kwargs: (provider, "test-model", "low"),
    )

    arguments = ["propose", "--repo-root", str(tmp_path), "--prompt", source, "--format", "json"]
    if repair_tier:
        arguments.extend(("--repair-tier", repair_tier))
    rc = greenfield_proposals_cli.main(arguments)
    return rc, json.loads(capsys.readouterr().out), provider


def test_public_authored_propose_seals_exact_non_latin_customer(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    intent = _authored_intent(customer="港務員")

    rc, payload, provider = _public_propose(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        capsys=capsys,
        intent=intent,
    )

    assert rc == 0, payload
    assert provider.calls == 1
    assert payload["intent_hypothesis"]["customer"] == "港務員"
    assert payload["mode"] == "product_create_transaction"
    transaction_path = tmp_path / payload["transaction_file"]
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    assert transaction["proposal"]["intent"]["customer"] == "港務員"
    manifest = transaction["quality_manifest"]
    assert manifest["requested_repair_tier"] == "auto"
    assert manifest["repair_tier"] == "standard"
    assert manifest["budget_seconds"] == 60.0
    assert manifest["rescue_activated"] is False


def test_public_authored_rescue_tier_seals_the_90_second_budget(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    author_greenfield_intent = greenfield_model_intent_authoring.author_greenfield_intent

    def author_after_standard_window(**kwargs: Any) -> Any:
        ticks = iter((0.0, 55.0))
        return author_greenfield_intent(**kwargs, clock=lambda: next(ticks))

    monkeypatch.setattr(
        greenfield_model_intent_materialization,
        "author_greenfield_intent",
        author_after_standard_window,
    )
    rc, payload, provider = _public_propose(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        capsys=capsys,
        intent=_authored_intent(),
        repair_tier="rescue",
    )

    assert rc == 0, payload
    assert provider.calls == 1
    transaction = json.loads((tmp_path / payload["transaction_file"]).read_text(encoding="utf-8"))
    manifest = transaction["quality_manifest"]
    assert manifest["requested_repair_tier"] == "rescue"
    assert manifest["repair_tier"] == "rescue"
    assert manifest["budget_seconds"] == 90.0
    assert manifest["rescue_activated"] is True
    assert manifest["model_authoring"]["tier"] == "rescue"
    assert manifest["model_authoring"]["semantic_model_call_count"] == 1


def test_public_authored_propose_seals_exact_non_latin_product_title(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    intent = _authored_intent(
        title="港務台",
        product_story="港務台 helps dock attendants keep berth placement clear",
        product_view="港務台 gives dock attendants a berth workflow",
    )

    rc, payload, provider = _public_propose(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        capsys=capsys,
        intent=intent,
    )

    assert rc == 0, payload
    assert provider.calls == 1
    assert payload["intent_hypothesis"]["title"] == "港務台"
    transaction_path = tmp_path / payload["transaction_file"]
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    assert transaction["proposal"]["intent"]["title"] == "港務台"
    idea_paths = transaction["prewrite_package"]["backlog_result"]["idea_files"]
    assert any("deliver-港務台" in path for path in idea_paths)


def test_public_authored_propose_seals_exact_repeated_brand_without_rewriting(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    intent = _authored_intent(
        title="Miu Miu",
        product_story="Miu Miu helps dock attendants keep berth placement clear",
        product_view="Miu Miu gives dock attendants a berth workflow",
    )

    rc, payload, provider = _public_propose(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        capsys=capsys,
        intent=intent,
    )

    assert rc == 0, payload
    assert provider.calls == 1
    assert payload["intent_hypothesis"]["title"] == "Miu Miu"
    transaction_path = tmp_path / payload["transaction_file"]
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    assert transaction["proposal"]["intent"]["title"] == "Miu Miu"


def test_public_authored_deep_tier_stays_structural_and_seals_exact_unicode_custody(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    intent = _authored_intent(customer="港務員")
    source = _evidence_source(intent)
    staged_evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    rc, payload, provider = _public_propose(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        capsys=capsys,
        intent=intent,
        repair_tier="deep",
    )

    assert rc == 0, payload
    assert provider.calls == 1
    transaction = json.loads((tmp_path / payload["transaction_file"]).read_text(encoding="utf-8"))
    manifest = transaction["quality_manifest"]
    assert manifest["requested_repair_tier"] == "deep"
    assert manifest["repair_tier"] == "deep"
    assert manifest["budget_seconds"] == 120.0
    assert manifest["rescue_activated"] is True
    assert manifest["semantic_compiler"] == {
        "version": "odylith.greenfield.authored-semantic-validation.v1",
        "status": "passed",
        "semantic_owner": "single_model_authoring_response",
        "post_authoring_interpretation_calls": 0,
    }
    unicode_atom = next(
        atom
        for atom in transaction["intent_authority"]["atomic_facts"]
        if atom["normalized_value"] == "港務員"
    )
    source_ref = unicode_atom["source_span_refs"][0]
    source_bytes = staged_evidence.encode("utf-8")
    quote_bytes = "港務員".encode("utf-8")
    assert source_bytes[source_ref["source_start_byte"] : source_ref["source_end_byte"]] == quote_bytes
    assert source_ref["text_sha256"] == hashlib.sha256(quote_bytes).hexdigest()
