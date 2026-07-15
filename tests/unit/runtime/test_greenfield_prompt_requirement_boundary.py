from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import contains_requirement_control_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import build_greenfield_package_report
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.project_intelligence.intent_confirmation import build_product_intent_confirmation
from odylith.runtime.project_intelligence.intent_confirmation import format_product_intent_confirmation_text
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_intent_with_authority
from tests.unit.runtime.greenfield_proposal_fixtures import stub_preconfirm_surface_refresh


_CRYOGENIC_REQUIREMENT_PROMPT = (
    "Create a greenfield proposal for a cryogenic ion trap calibration field evidence operations desk "
    "that helps a physicist ingest field observations, normalize measurements, link calibration evidence, "
    "flag anomalies, request expert review, and reopen the saved record with the same inputs. "
    "The first release must preserve ion trap, cryogenic calibration, motional heating, laser detuning, "
    "phonon readout, and kelvin drift evidence. Distinctive project vocabulary includes cryogenic ion trap "
    "calibration phonon readout evidence and cryogenic ion trap calibration kelvin drift review. "
    "It must capture measurement unit, calibration source, quality limit, reproducibility note, avoid "
    "unsupported operational claims, show uncertainty or confidence limits, and make the saved result "
    "reproducible for product, architecture, engineering, and domain-expert review."
)

_DRONE_REQUIREMENT_PROMPT = (
    "Create a greenfield proposal for a drone swarm search coordination intake-to-proof workspace that helps a "
    "robotics architect provide inputs, validate units and provenance, run the model, compare against a baseline, "
    "record uncertainty, and save a reviewable result. The first release must preserve drone swarm, search "
    "coordination, coverage cell, handoff beacon, battery reserve, and mission evidence evidence. Distinctive "
    "project vocabulary includes drone swarm search coordination battery reserve evidence and drone swarm search "
    "coordination mission evidence review. It must capture method version, parameter set, validation source, "
    "reviewer note, avoid unsupported operational claims, show uncertainty or confidence limits, and make the "
    "saved result reproducible for product, architecture, engineering, and domain-expert review."
)

_RADIOTHERAPY_REQUIREMENT_PROMPT = (
    "Create a greenfield proposal for a radiotherapy dose adaptation intake-to-proof workspace that helps a "
    "medical physicist provide inputs, validate units and provenance, run the model, compare against a baseline, "
    "record uncertainty, and save a reviewable result. The first release must preserve dose adaptation, "
    "radiotherapy plan, organ-at-risk, fraction response, dose-volume histogram, and toxicity constraint evidence. "
    "Distinctive project vocabulary includes radiotherapy dose adaptation dose-volume histogram evidence and "
    "radiotherapy dose adaptation toxicity constraint review. It must capture method version, parameter set, "
    "validation source, reviewer note, avoid unsupported operational claims, show uncertainty or confidence limits, "
    "and make the saved result reproducible for product, architecture, engineering, and domain-expert review."
)

_SECURE_MULTIPARTY_BOUNDARY_PROMPT = (
    "Create a greenfield proposal for a secure multiparty risk model model-risk release gate that helps a "
    "cryptography engineer register a model candidate, attach dataset identity, run comparison evidence, "
    "review uncertainty, block unsafe claims, and approve only bounded release evidence. The first release "
    "must preserve multiparty risk, secure computation, secret share, threat model, audit transcript, and "
    "leakage bound evidence. Distinctive project vocabulary includes secure multiparty risk model audit "
    "transcript evidence and secure multiparty risk model leakage bound review. It must capture method version, "
    "parameter set, validation source, reviewer note, avoid unsupported operational claims, show uncertainty or "
    "confidence limits, and make the saved result reproducible for product, architecture, engineering, and "
    "domain-expert review."
)


def _visible_confirmation_intent(prompt: str) -> dict[str, object]:
    confirmation = build_product_intent_confirmation(
        prompt=prompt,
        title="greenfield simulation",
        repo_name="greenfield-simulation",
        observed_source={},
    )
    return confirmed_intent_with_authority(
        format_product_intent_confirmation_text(confirmation),
        prompt=prompt,
        source_format="operator_prompt",
    )


@pytest.fixture(autouse=True)
def _preconfirm_surface_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_preconfirm_surface_refresh(monkeypatch)


def _proposal_and_prewrite(tmp_path: Path, prompt: str):
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=_visible_confirmation_intent(prompt),
        require_completion_ready=False,
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )
    return proposal, prewrite


def test_prompt_requirement_sentences_do_not_become_first_path_events() -> None:
    source = prompt_intent_source(_CRYOGENIC_REQUIREMENT_PROMPT)
    model = first_path_model(source.first_path)

    assert source.title == "cryogenic ion trap calibration field evidence operations desk"
    assert source.actor == "physicist"
    assert "first release must" not in source.first_path.casefold()
    assert "distinctive project vocabulary" not in source.first_path.casefold()
    assert "must capture measurement unit" not in source.first_path.casefold()
    assert "Reopen the saved record with the same inputs" in model.steps
    assert len(model.steps) >= 5
    assert not any(contains_requirement_control_clause(step) for step in model.steps)


def test_release_gate_title_does_not_capture_evidence_requirements_as_path() -> None:
    source = prompt_intent_source(_SECURE_MULTIPARTY_BOUNDARY_PROMPT)

    assert source.title == "secure multiparty risk model model-risk release gate"
    assert "first release must preserve" not in source.first_path.casefold()
    assert "secret share" not in source.first_path.casefold()
    assert "approve only bounded release evidence" in source.first_path.casefold()


def test_visible_confirmation_carries_typed_evidence_requirements() -> None:
    confirmation = build_product_intent_confirmation(
        prompt=_CRYOGENIC_REQUIREMENT_PROMPT,
        title="greenfield simulation",
        repo_name="greenfield-simulation",
        observed_source={},
    )
    rendered = format_product_intent_confirmation_text(confirmation)
    intent = confirmed_intent_with_authority(
        rendered,
        prompt=_CRYOGENIC_REQUIREMENT_PROMPT,
        source_format="operator_prompt",
    )

    assert "Evidence requirements" in rendered
    requirements = " ".join(intent["evidence_requirements"]).casefold()
    for term in ("ion trap", "cryogenic calibration", "motional heating", "laser detuning"):
        assert term in requirements


def test_confirmed_package_keeps_requirement_obligations_out_of_atlas_path_labels(tmp_path: Path) -> None:
    proposal, prewrite = _proposal_and_prewrite(tmp_path, _CRYOGENIC_REQUIREMENT_PROMPT)
    semantic = proposal["semantic_model"]["first_path_contract"]
    atlas_text = "\n".join(prewrite.package.rendered_atlas_sources.values())
    public_payload = json.dumps(
        {
            "intent": proposal.get("intent"),
            "semantic_model": proposal.get("semantic_model"),
            "atlas": prewrite.package.rendered_atlas_sources,
            "project_brief": prewrite.package.project_brief_preview,
        },
        sort_keys=True,
    )

    assert "Cryogenic Ion Trap Calibration Field Evidence Operations Desk" in public_payload
    assert "first release must" not in semantic["raw_path"].casefold()
    assert "distinctive project vocabulary" not in semantic["raw_path"].casefold()
    assert not any(contains_requirement_control_clause(row["text"]) for row in semantic["events"])
    assert "first release must" not in atlas_text.casefold()
    assert "distinctive project vocabulary" not in atlas_text.casefold()
    assert greenfield_quality_issues(proposal) == []
    assert build_greenfield_package_report(prewrite.package).issues == ()
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()


def test_scientific_requirement_anchors_survive_into_scored_governance_surfaces(tmp_path: Path) -> None:
    proposal, prewrite = _proposal_and_prewrite(tmp_path, _CRYOGENIC_REQUIREMENT_PROMPT)
    required_terms = ("ion trap", "cryogenic calibration", "motional heating", "laser detuning")
    anchors = " ".join(proposal["intent"]["evidence_requirements"]).casefold()
    evaluation = proposal["semantic_model"]["evaluation_semantics"]
    source_anchors = " ".join(evaluation["source_anchors"]).casefold()
    public_payload = json.dumps(
        {
            "backlog": proposal.get("backlog"),
            "project_brief": prewrite.package.project_brief_preview,
            "semantic_model": proposal.get("semantic_model"),
        },
        sort_keys=True,
    ).casefold()

    assert evaluation["applicability"] == "evidence_backed_model_or_research_evaluation"
    for term in required_terms:
        assert term in anchors
        assert term in source_anchors
        assert term in public_payload


def test_requirement_anchors_canonicalize_adjacent_duplicate_source_words(tmp_path: Path) -> None:
    proposal, prewrite = _proposal_and_prewrite(tmp_path, _DRONE_REQUIREMENT_PROMPT)
    evaluation = proposal["semantic_model"]["evaluation_semantics"]
    public_payload = json.dumps(
        {
            "intent": proposal.get("intent"),
            "semantic_model": proposal.get("semantic_model"),
            "backlog": proposal.get("backlog"),
            "project_brief": prewrite.package.project_brief_preview,
        },
        sort_keys=True,
    ).casefold()

    assert "mission evidence" in " ".join(proposal["intent"]["evidence_requirements"]).casefold()
    assert "mission evidence" in " ".join(evaluation["source_anchors"]).casefold()
    assert "mission evidence" in " ".join(evaluation["evidence_sources"]).casefold()
    assert "mission evidence evidence" not in public_payload
    assert greenfield_quality_issues(proposal) == []
    assert build_greenfield_package_report(prewrite.package).issues == ()
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()


def test_requirement_anchors_preserve_hyphenated_scientific_compounds(tmp_path: Path) -> None:
    proposal, prewrite = _proposal_and_prewrite(tmp_path, _RADIOTHERAPY_REQUIREMENT_PROMPT)
    evaluation = proposal["semantic_model"]["evaluation_semantics"]
    public_payload = json.dumps(
        {
            "intent": proposal.get("intent"),
            "semantic_model": proposal.get("semantic_model"),
            "backlog": proposal.get("backlog"),
            "project_brief": prewrite.package.project_brief_preview,
        },
        sort_keys=True,
    ).casefold()

    assert "organ-at-risk" in " ".join(proposal["intent"]["evidence_requirements"]).casefold()
    assert "organ-at-risk" in " ".join(evaluation["source_anchors"]).casefold()
    assert "organ-at-risk" in public_payload
    assert greenfield_quality_issues(proposal) == []
    assert build_greenfield_package_report(prewrite.package).issues == ()
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()


def test_source_title_boundary_duplicates_canonicalize_before_projection(tmp_path: Path) -> None:
    title = normalize_project_title("secure multiparty risk model model-risk release gate")
    proposal, prewrite = _proposal_and_prewrite(tmp_path, _SECURE_MULTIPARTY_BOUNDARY_PROMPT)
    public_payload = json.dumps(
        {
            "intent": proposal.get("intent"),
            "semantic_model": proposal.get("semantic_model"),
            "backlog": proposal.get("backlog"),
            "project_brief": prewrite.package.project_brief_preview,
            "next_steps": prewrite.package.next_steps_preview,
            "accepted_project": prewrite.package.accepted_project_preview,
            "atlas": prewrite.package.rendered_atlas_sources,
            "registry": prewrite.package.rendered_component_specs,
            "source_launch": prewrite.package.next_steps_preview,
        },
        sort_keys=True,
        default=str,
    )
    public_lower = public_payload.casefold()

    assert title.canonical_title == "secure multiparty risk model-risk release gate"
    assert proposal["intent"]["title"] == "Secure Multiparty Risk Model-risk Release Gate Workspace"
    assert proposal["intent"].get("source_title") is None
    assert "model model-risk" not in public_lower
    assert "model model risk" not in public_lower
    for term in ("multiparty risk", "secure computation", "secret share", "threat model"):
        assert term in public_lower
    assert greenfield_quality_issues(proposal) == []
    assert build_greenfield_package_report(prewrite.package).issues == ()
    assert greenfield_rendered_package_quality_issues(prewrite.package) == ()
