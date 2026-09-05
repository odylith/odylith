"""Exact-byte staging contracts for model-authored Greenfield candidates."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_confirmed_text
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_SEMANTICS_KEY,
    authored_semantics_mapping,
)
from odylith.runtime.domain_intelligence.greenfield_candidate_intent_stage import (
    candidate_intent_stage_paths,
    stage_candidate_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    author_greenfield_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    RESCUE_PROFILE_ID,
    get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_FACTS_HASH_KEY,
    build_product_intent_envelope,
    product_intent_authority_from_envelope,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
)


def _authored_stage_inputs(repo_root: Path) -> tuple[dict[str, object], dict[str, object], dict[str, object], str]:
    actor = "Optional or Future Council"
    first_event = f"{actor} records café evidence AND OR provenance"
    visible_event = "Evidence Ledger shows the receipt"
    intent: dict[str, object] = {
        "title": "Café AND OR Ledger",
        "product_story": f"{actor} needs exact café evidence custody",
        "state_object": "café evidence",
        "first_path": f"{first_event} before {visible_event}",
        "proof_boundary": "The same café evidence yields the exact receipt",
        "problem": "Café evidence custody is difficult to verify",
        "customer": actor,
        "opportunity": "One exact evidence path",
        "product_view": f"Café AND OR Ledger gives {actor} an exact evidence path",
        "success_metrics": ["The receipt preserves the exact café evidence digest"],
        "evidence_requirements": ["Retain exact UTF-8 source bytes"],
        "operational_constraints": ["Preserve café evidence AND OR marker bytes"],
        "component_responsibilities": [visible_event],
        "human_actors": [actor],
        "external_systems": ["Café Archive"],
        "internal_systems": ["Evidence Ledger"],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": ["Do not rewrite source conjunctions"],
    }
    evidence = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    ) + "."
    result = author_greenfield_intent(
        evidence_text=evidence,
        provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                evidence_text=evidence,
                component_responsibility_owners=["Evidence Ledger"],
                first_path_relations=[
                    {
                        "actor_kind": "human",
                        "actor_fact_quote": actor,
                        "event_quote": first_event,
                        "action_verb_quote": "records",
                        "target_quote": "café evidence AND OR provenance",
                        "visible_result_quote": "",
                    },
                    {
                        "actor_kind": "product",
                        "actor_fact_quote": "Evidence Ledger",
                        "owner_system_quote": "Evidence Ledger",
                        "event_quote": visible_event,
                        "action_verb_quote": "shows",
                        "target_quote": "the receipt",
                        "visible_result_quote": visible_event,
                    },
                ],
            )
        ),
        model_profile_id=RESCUE_PROFILE_ID,
        clock=lambda: 0.0,
    )
    authored_intent: dict[str, object] = {
        **result.intent,
        AUTHORED_SEMANTICS_KEY: authored_semantics_mapping(
            result.first_path_relations,
            result.component_responsibility_relations,
            first_path_context_relations=result.first_path_context_relations,
        ),
    }
    profile = get_greenfield_model_profile(RESCUE_PROFILE_ID)
    paths = candidate_intent_stage_paths(repo_root)
    envelope = build_product_intent_envelope(
        authored_intent,
        source_text=evidence,
        source_path=paths.evidence_markdown.relative_to(repo_root),
        source_format="operator_prompt",
        model_authoring={
            "profile_id": profile.profile_id,
            "provider": profile.provider,
            "model": profile.model,
            "reasoning_effort": profile.reasoning_effort,
            "effective_timeout_seconds": profile.model_timeout_seconds,
            "authoring_tier": profile.repair_tier,
        },
        authored_source_spans=result.source_spans,
        authored_atomic_claims=result.atomic_claims,
        authored_source_sha256=result.source_sha256,
    )
    authority = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path=paths.structured.relative_to(repo_root),
        markdown_source_path=paths.evidence_markdown.relative_to(repo_root),
    )
    return authored_intent, envelope, authority, evidence


def test_authored_stage_preserves_exact_utf8_connector_and_actor_marker_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intent, envelope, authority, evidence = _authored_stage_inputs(tmp_path)

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("authored staging must not invoke legacy semantic normalization")

    monkeypatch.setattr(greenfield_confirmed_text, "normalize_connector_sequence", forbidden)

    candidate = stage_candidate_intent(
        repo_root=tmp_path,
        intent=intent,
        envelope=envelope,
        authority=authority,
        prompt=evidence,
        edit_evidence="",
        evidence_source=evidence,
    )

    paths = candidate_intent_stage_paths(tmp_path)
    structured_bytes = paths.structured.read_bytes()
    structured = json.loads(structured_bytes)
    markdown = paths.markdown.read_text(encoding="utf-8")
    assert structured["product_facts"] == envelope["product_facts"]
    assert structured["human_actors"] == ["Optional or Future Council"]
    assert structured["operational_constraints"] == [
        "Preserve café evidence AND OR marker bytes"
    ]
    assert structured["decision_record"][PRODUCT_FACTS_HASH_KEY] == authority[PRODUCT_FACTS_HASH_KEY]
    assert "café".encode("utf-8") in structured_bytes
    assert "- Optional or Future Council" in markdown
    assert "- Preserve café evidence AND OR marker bytes" in markdown
    assert candidate["human_actors"] == envelope["product_facts"]["human_actors"]


@pytest.mark.parametrize("drift_owner", ["intent", "authority"])
def test_authored_stage_rejects_fact_or_authority_drift_before_writing(
    tmp_path: Path,
    drift_owner: str,
) -> None:
    intent, envelope, authority, evidence = _authored_stage_inputs(tmp_path)
    drifted_intent = copy.deepcopy(intent)
    drifted_authority = copy.deepcopy(authority)
    if drift_owner == "intent":
        drifted_intent["human_actors"] = ["Rewritten Council"]
        error = "facts drifted"
    else:
        paths = candidate_intent_stage_paths(tmp_path)
        drifted_authority = product_intent_authority_from_envelope(
            envelope,
            structured_intent_path=Path("wrong-candidate-intent.json"),
            markdown_source_path=paths.evidence_markdown.relative_to(tmp_path),
        )
        error = "authority does not match"

    with pytest.raises(ValueError, match=error):
        stage_candidate_intent(
            repo_root=tmp_path,
            intent=drifted_intent,
            envelope=envelope,
            authority=drifted_authority,
            prompt=evidence,
            edit_evidence="",
            evidence_source=evidence,
        )

    assert not candidate_intent_stage_paths(tmp_path).markdown.exists()
