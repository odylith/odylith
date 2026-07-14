from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import artifact_enrichment
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_confirmed_prewrite_gate
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_apply_components import component_dependency_lines
from odylith.runtime.domain_intelligence.greenfield_apply_components import component_dependency_lookup_for
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import PROJECT_INTELLIGENCE_LAYERS
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import render_project_intelligence_section
from odylith.runtime.domain_intelligence.greenfield_product_risks import build_product_risks
from odylith.runtime.domain_intelligence.greenfield_product_risks import risk_text_has_framework_leak
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import render_domain_intelligence_section
from odylith.runtime.domain_intelligence.greenfield_workstream_risk_projection import proposal_risk_lines
from odylith.runtime.domain_intelligence.artifact_tribunal_actors import _role_suffixed_label
from odylith.runtime.domain_intelligence.artifact_tribunal_actors import _looks_like_actor_label
from odylith.runtime.domain_intelligence.artifact_tribunal_actors import tribunal_actor_projection
from odylith.runtime.domain_intelligence.artifact_tribunal_actors import tribunal_visible_actor_quality_issues
from odylith.runtime.common import display_text
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import build_traceability_graph
from odylith.runtime.governance import release_planning_view_model
from odylith.runtime.project_intelligence import builder as project_intelligence_builder
from odylith.runtime.project_intelligence import greenfield as project_intelligence_greenfield
from odylith.runtime.project_intelligence import presenter as project_intelligence_presenter
from tests.unit.runtime.greenfield_proposal_fixtures import _confirmed_intent
from tests.unit.runtime.greenfield_proposal_fixtures import _governed_greenfield_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import _host_reasoned_crispr_without_parent
from tests.unit.runtime.greenfield_proposal_fixtures import _host_reasoned_ecommerce_proposal
from tests.unit.runtime.greenfield_proposal_fixtures import _host_reasoned_recipe_legacy_shape
from tests.unit.runtime.greenfield_proposal_fixtures import _ontology_term_labels
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import commit_precompiled_greenfield_proposal
from tests.unit.runtime.greenfield_proposal_fixtures import surface_refresh_preview_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import stub_preconfirm_surface_refresh


ROOT = Path(__file__).resolve().parents[3]
GREENFIELD_PROPOSALS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_proposals.py"
GREENFIELD_APPLY_WRITE_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_apply_write.py"
ARTIFACT_ENRICHMENT_PATH = ROOT / "src/odylith/runtime/domain_intelligence/artifact_enrichment.py"
ARTIFACT_GRAPH_PATH = ROOT / "src/odylith/runtime/domain_intelligence/artifact_graph.py"
ARTIFACT_TRIBUNAL_ACTORS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/artifact_tribunal_actors.py"
GREENFIELD_DOMAIN_TERM_INDEX_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_domain_term_index.py"
GREENFIELD_COMPONENT_TERM_INDEX_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_component_term_index.py"
GREENFIELD_PRODUCT_RISKS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_product_risks.py"


@pytest.fixture(autouse=True)
def _stub_rendered_surface_custody_for_legacy_proposal_units(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_preconfirm_surface_refresh(monkeypatch)


def test_actor_label_detection_rejects_domain_objects_but_keeps_known_roles() -> None:
    assert _looks_like_actor_label("resident") is True
    assert _looks_like_actor_label("incident") is False
    assert _looks_like_actor_label("patient") is False


def test_greenfield_apply_write_stays_in_dedicated_owner() -> None:
    parent_source = GREENFIELD_PROPOSALS_PATH.read_text(encoding="utf-8")
    write_source = GREENFIELD_APPLY_WRITE_PATH.read_text(encoding="utf-8")
    cli_source = (ROOT / "src/odylith/runtime/domain_intelligence/greenfield_proposals_cli.py").read_text(
        encoding="utf-8"
    )
    diagram_source = (ROOT / "src/odylith/runtime/domain_intelligence/greenfield_apply_diagrams.py").read_text(
        encoding="utf-8"
    )

    assert len(parent_source.splitlines()) < 800
    assert "greenfield_create_commit.commit_greenfield_create_transaction" not in parent_source
    assert "greenfield_create_commit.commit_greenfield_create_transaction" in cli_source
    assert "greenfield_apply_write.write_greenfield_proposal" not in parent_source
    assert "greenfield_apply_write.release_assignment_note" in parent_source
    for moved in (
        "def write_greenfield_proposal",
        "def _scaffold_proposal_diagram",
        "def _upsert_existing_proposal_diagram",
        "def _raise_for_component_spec_quality",
        "def _remove_stale_workstream_artifacts",
        "def _refresh_greenfield_dashboard",
        "owned_surface_refresh.raise_for_failed_refreshes",
        "scaffold_mermaid_diagram",
        "component_authoring.register_component",
        "record_greenfield_acceptance",
    ):
        assert moved not in parent_source
    assert "def write_greenfield_proposal" in write_source
    assert "def _scaffold_proposal_diagram" not in write_source
    assert "scaffold_mermaid_diagram" not in write_source
    assert "greenfield_apply_diagrams.materialize_apply_diagrams" in write_source
    assert "def _scaffold_proposal_diagram" in diagram_source
    assert "def _upsert_existing_proposal_diagram" in diagram_source
    assert "def materialize_apply_diagrams" in diagram_source
    assert "def _raise_for_component_spec_quality" in write_source
    assert "record_greenfield_acceptance" in write_source
    assert "greenfield_component_commit.register_component_from_authoring_input" in write_source


def test_artifact_enrichment_graph_and_tribunal_actors_stay_in_dedicated_owners() -> None:
    enrichment_source = ARTIFACT_ENRICHMENT_PATH.read_text(encoding="utf-8")
    graph_source = ARTIFACT_GRAPH_PATH.read_text(encoding="utf-8")
    actors_source = ARTIFACT_TRIBUNAL_ACTORS_PATH.read_text(encoding="utf-8")

    assert len(enrichment_source.splitlines()) < 800
    assert "artifact_tribunal_actors.tribunal_actor_projection" in enrichment_source
    assert "from odylith.runtime.domain_intelligence.artifact_graph import domain_graph_from_workstream" in enrichment_source
    assert "value_coercion import dedupe_by_key" in enrichment_source
    assert "DomainIntelligenceGraph" not in artifact_enrichment.__all__
    assert "domain_graph_from_workstream" not in artifact_enrichment.__all__
    assert "seen: set[str]" not in enrichment_source
    assert "seen.add(key)" not in enrichment_source
    for moved in (
        "class DomainIntelligenceGraph",
        "def domain_graph_from_workstream",
        "def _pick_state_objects",
        "def _primary_lens",
        "def tribunal_actor_projection",
        "def _domain_actor_names",
        "def _proposal_actor_candidates",
        "def _actor_candidate_label",
        "def _dedupe_visible_actor_names",
    ):
        assert moved not in enrichment_source
    for moved in (
        "class DomainIntelligenceGraph",
        "def domain_graph_from_workstream",
        "def _pick_state_objects",
        "def _primary_lens",
    ):
        assert moved in graph_source
    for moved in (
        "def tribunal_actor_projection",
        "def _domain_actor_names",
        "def _proposal_actor_candidates",
        "def _actor_candidate_label",
        "def _dedupe_visible_actor_names",
    ):
        assert moved in actors_source
    assert artifact_enrichment._bullets(["Proof: accepted path", "accepted path", "Risk: review gap"]) == (
        "- Proof: accepted path\n- Risk: review gap"
    )


def test_artifact_enrichment_dedupes_focus_detail_boundary_terms() -> None:
    review_line = artifact_enrichment._scoped_sentence(
        "Evidence record",
        "Let Communications Coordinator Send It for Review",
        "Review evidence belongs in Public Response Drafting Queue Proof Record.",
    )
    evidence_line = artifact_enrichment._scoped_sentence(
        "Evidence record",
        "Let Case Worker Record Evidence",
        "Evidence contents belong in Appeal Proof Record.",
    )

    assert "Review Review" not in review_line
    assert review_line.endswith("Review — evidence belongs in Public Response Drafting Queue Proof Record")
    assert "Evidence Evidence" not in evidence_line
    assert evidence_line.endswith("Evidence — contents belong in Appeal Proof Record")


def test_artifact_enrichment_preserves_complete_short_validation_predicates() -> None:
    validation_line = artifact_enrichment._scoped_sentence(
        "Validation gate",
        "Show Why Permit Case Can Be Trusted",
        "Proof review fails closed when success evidence, replay evidence, access proof, privacy proof, or review evidence is missing.",
    )

    assert validation_line == (
        "Validation gate: Show Why Permit Case Can Be Trusted — Proof review fails closed when success evidence, "
        "replay evidence, access proof, privacy proof, or review evidence is missing"
    )
    assert not validation_line.endswith("access proof")


def test_artifact_enrichment_splits_long_first_path_action_chains() -> None:
    lines = artifact_enrichment._first_path_enrichment_lines(
        focus="Prove One Complete Municipal Permit Review Path",
        first_slice=(
            "Prove one first-release path: enter parcel details, attach required document references, "
            "record fee status and contact information, submit the packet, receive completeness feedback, "
            "and review record, then let the permit staff reviewer publish a decision."
        ),
    )

    assert len(lines) == 3
    assert lines[0].startswith("First path:")
    assert lines[1].startswith("Path actions:")
    assert lines[2].startswith("Completion check:")
    assert all(len(line) < 220 for line in lines)


def test_product_risk_specificity_uses_shared_term_index() -> None:
    domain_index_source = GREENFIELD_DOMAIN_TERM_INDEX_PATH.read_text(encoding="utf-8")
    component_index_source = GREENFIELD_COMPONENT_TERM_INDEX_PATH.read_text(encoding="utf-8")
    risk_source = GREENFIELD_PRODUCT_RISKS_PATH.read_text(encoding="utf-8")

    assert len(domain_index_source.splitlines()) < 800
    assert len(component_index_source.splitlines()) < 800
    assert len(risk_source.splitlines()) < 800
    assert "def ordered_terms" in domain_index_source
    assert "ordered_terms(text, stopwords=TERM_STOPWORDS)" in component_index_source
    assert "from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms" in risk_source
    assert "def _domain_terms(" not in risk_source

    assert ordered_terms("Permit statuses, applicant readings, and permit statuses.", stopwords={"and"}) == [
        "permit",
        "status",
        "applicant",
        "reading",
    ]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _markdown_section(text: str, heading: str) -> str:
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end == -1 else text[start:end]


def _assert_project_story_cards(story: dict[str, object]) -> None:
    labels = [row.get("label") for row in story["release_contract"]]
    assert labels == ["User Problem", "First Path", "Product Boundary", "Owned Capabilities", "Proof"]
    encoded = json.dumps(story["release_contract"], sort_keys=True).casefold()
    assert all(len(str(row.get("body", "")).split()) >= 18 for row in story["release_contract"])
    assert "accepted first path" not in encoded
    assert "additional accepted capabilities" not in encoded
    assert "proof boundary blocks" not in encoded


def test_greenfield_prompt_returns_governed_confirmed_proposal(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
        confirmed_intent=_confirmed_intent(),
    )

    greenfield_proposals.validate_host_reasoned_proposal(proposal)
    encoded = json.dumps(proposal)
    assert proposal["mode"] == "host_reasoned_greenfield_proposal"
    assert proposal["provider_calls"] == 0
    assert proposal["host_agnostic"] is True
    assert proposal["intent"]["reasoning_mode"] == "odylith_confirmed_governed_proposal"
    assert proposal["classification"]["method"] == "confirmed_open_world_product_shape"
    assert proposal["intent"]["title"] == "Municipal Permit Review Workspace"
    assert "catalog" not in proposal
    assert len(proposal["backlog"]) >= 4
    assert len(proposal["components"]) >= 4
    assert len(proposal["diagrams"]) >= 6
    assert {row["title"] for row in proposal["diagrams"]} >= {
        "System Context View",
        "First Path Sequence",
        "State and Evidence View",
        "Component Boundary View",
        "Ownership and Proof View",
        "Release Proof Review",
    }
    assert "Permit File Registry" in encoded
    assert "Zoning Check Ledger" in encoded
    assert "Release 0.0.1 succeeds when a supervisor can inspect one permit review file" in encoded
    assert "Municipal Permit Review Workspace Workflow Service" not in encoded
    assert proposal["project_brief"]["blueprint_sections"]
    assert proposal["project_intelligence"]["intent"]
    assert proposal["observed_source"]["source_posture"] == "confirmed_intent_only"
    assert proposal["intent"]["prompt"] == ""
    assert proposal["apply_commands"][0].startswith("odylith greenfield propose --repo-root . --prompt ")
    assert "greenfield compile-transaction" not in "\n".join(proposal["apply_commands"])
    assert "--intent-file" not in "\n".join(proposal["apply_commands"])
    assert not any(str(command).startswith("odylith greenfield create") for command in proposal["apply_commands"])
    assert "CONFIRM, EDIT, and REJECT" in proposal["apply_commands"][1]
    assert "hash-bound transaction" in proposal["apply_commands"][2]
    paths = proposal["project_brief"]["host_independent_paths"]
    assert len(paths) == 1
    assert paths[0]["path"] == "Review the creation-ready transaction"
    assert paths[0]["command"].startswith("odylith greenfield propose --repo-root . --prompt ")
    assert "--intent-file" not in paths[0]["command"]
    assert "internal apply payload" not in encoded
    assert "active-proposal.v1.json" not in encoded
    assert "Make product-owned systems explicit:" not in encoded
    assert "releaseable" not in encoded
    risk_text = json.dumps(proposal["risks"], sort_keys=True).casefold()
    assert "accepted first path" not in risk_text
    assert "proof boundary" not in risk_text
    assert "release records" not in risk_text
    assert "governance records" not in risk_text
    assert "permit" in risk_text
    assert any("decision" in row["statement"].casefold() or "zoning" in row["statement"].casefold() for row in proposal["risks"])
    for row in proposal["backlog"]:
        for line in row.get("rationale_bullets", []):
            assert len(line) <= 260
    assert "host_instruction" not in proposal
    assert "reasoning_contract" not in proposal
    assert "proposal_template" not in proposal
    assert "canonical_proposal" not in proposal
    assert "canonical_proposal_gate" not in proposal


def test_greenfield_confirmed_builder_rejects_shallow_confirmed_intent(tmp_path) -> None:
    with pytest.raises(ValueError, match="Product Intent authority is missing"):
        greenfield_proposals.build_greenfield_proposal(
            repo_root=tmp_path,
            prompt="Create a community archive",
            confirmed_intent={"title": "Community Archive"},
        )


def test_greenfield_validation_rejects_old_generic_risk_boilerplate(tmp_path) -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["risks"][0] = {
        "statement": (
            "Starting implementation without a named product spine, component ownership, and proof gates can create "
            "disconnected source slices."
        )
    }

    with pytest.raises(ValueError, match="generic greenfield boilerplate"):
        greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_validation_rejects_framework_risks(tmp_path) -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["risks"][0] = {
        "title": "Ownership clarity",
        "statement": "If the accepted proof boundary is not visible in the release records, reviewers cannot trust release 0.0.1.",
    }

    with pytest.raises(ValueError, match="describes Odylith process"):
        greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_risk_leak_detection_keeps_domain_registry_reviewers() -> None:
    assert not risk_text_has_framework_leak(
        {
            "title": "Summary accuracy",
            "statement": (
                "Registry reviewers may trust a soil carbon result when sampling plans, lab results, field histories, "
                "or reversal risks are incomplete."
            ),
            "mitigation": "Show missing evidence and uncertainty before credit issuance decisions proceed.",
        }
    )
    assert not risk_text_has_framework_leak("Compass records show driver heading corrections before dispatch review.")
    assert not risk_text_has_framework_leak("Atlas records preserve parcel survey views for county reviewers.")
    assert not risk_text_has_framework_leak("The dashboard shows compass headings for hikers before the route is saved.")
    assert risk_text_has_framework_leak(
        {
            "title": "Surface leakage",
            "statement": "If Registry component specs are missing, reviewers cannot trust release 0.0.1.",
        }
    )


def test_greenfield_product_risks_allow_domain_registry_language() -> None:
    risks = build_product_risks(
        title="Soil Carbon Verification Workspace",
        product_story=(
            "Registry reviewers connect sampling plans, lab results, field histories, uncertainty ranges, reversal risks, "
            "credit issuance gates, and claim-limiting proof."
        ),
        first_path=(
            "Growers, agronomists, auditors, and registry reviewers connect sampling plans, lab results, field histories, "
            "uncertainty ranges, reversal risks, credit issuance gates, and claim-limiting proof."
        ),
        state_object="A soil carbon verification result record tracks evidence, uncertainty, and credit readiness.",
        proof_boundary=(
            "The product shows missing evidence, uncertain inputs, and claim limits before any credit issuance gate proceeds."
        ),
        human_actors=("Registry Reviewers: review sampling plans, lab results, and claim-limiting proof",),
        release="0.0.1",
    )

    assert len(risks) == 4
    assert not any(risk_text_has_framework_leak(row) for row in risks)
    assert "registry reviewers" in json.dumps(risks, sort_keys=True).casefold()


def test_project_dashboard_renders_product_risks_not_framework_risks(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
        confirmed_intent=_confirmed_intent(),
    )
    proposal["risks"] = [
        {
            "title": "Ownership clarity",
            "statement": "If the accepted proof boundary is not visible in the release records, reviewers cannot trust release 0.0.1.",
        }
    ]

    payload = project_intelligence_greenfield.build_greenfield_payload(proposal=proposal, repo_root=tmp_path)
    risk_text = json.dumps(payload["risk_items"], sort_keys=True).casefold()

    assert payload["risk_note"].startswith("Real-world failure modes")
    assert "proposal risk" not in risk_text
    assert "ownership clarity" not in risk_text
    assert "accepted first path" not in risk_text
    assert "proof boundary" not in risk_text
    assert "release records" not in risk_text
    assert "permit" in risk_text
    assert any(row["risk"] in {"Decision Accuracy", "Policy Drift", "External Dependency", "User Trust"} for row in payload["risk_items"])


def test_greenfield_workstreams_require_host_authored_intelligence(tmp_path) -> None:
    proposal = _governed_greenfield_fixture(tmp_path, "plant sensor")
    brief = proposal["project_brief"]

    workflow = next(row for row in proposal["backlog"] if row["title"] == "Define Storefront boundary")
    intelligence = workflow["domain_intelligence"]
    rendered = render_domain_intelligence_section(intelligence)
    project_intelligence = proposal["project_intelligence"]
    project_rendered = render_project_intelligence_section(project_intelligence)

    assert "Host Authored Greenfield Project" not in project_rendered
    assert "Make Plant Sensor" in project_rendered
    assert intelligence["family"] == "host_reasoned_project"
    assert "Actor:" in rendered
    assert "State object:" in rendered
    assert "Evidence record:" in rendered
    assert "Release gate:" in rendered
    assert "source_of_truth_map" in intelligence
    assert "validation_obligations" in intelligence
    assert "conflict_model" in intelligence
    assert "transfer_priors" in intelligence
    assert "Product story" in json.dumps(brief)
    assert "Actors and systems" in json.dumps(brief)
    assert not any(prompt.startswith("defer ") for prompt in brief["customization_prompts"])
    assert all(prompt[:1].isupper() for prompt in brief["customization_prompts"])
    assert "first implementation lane" in " ".join(brief["coding_readiness_gates"]).casefold()
    assert "prompt title" not in rendered.lower()
    risk_text = json.dumps(proposal["risks"])
    assert "Starting implementation without a named product spine" not in risk_text
    assert "under-modeled in broad greenfield prompts" not in risk_text
    proposal_text = greenfield_proposals.format_proposal_text(proposal)
    assert "Product Story" not in proposal_text
    for row in proposal["backlog"]:
        row_rendered = render_domain_intelligence_section(row["domain_intelligence"])
        labels = _ontology_term_labels(row["domain_intelligence"]["ontology"])
        assert len(labels) == len(set(labels))
        assert "owns Own" not in row_rendered
        assert "owns owns" not in row_rendered.casefold()
    greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_tribunal_uses_domain_specific_visible_actors(tmp_path) -> None:
    proposal = _governed_greenfield_fixture(tmp_path, "plant sensor")

    decision = greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1")
    actor_labels = {row["visible_actor"] for row in decision.to_dict()["visible_actors"]}
    stable_roles = {row["stable_role"] for row in decision.to_dict()["visible_actors"]}

    assert decision.passed
    assert "beneficiary_advocate" in stable_roles
    assert "Plant owner advocate" in actor_labels
    assert "Care routine operator" in actor_labels
    assert "Plant safety reviewer" in actor_labels
    assert "Care proof reviewer" in actor_labels
    assert "Plant monitor build owner" in actor_labels
    assert "Plant sensor risk reviewer" not in actor_labels
    assert "Plant sensor proof reviewer" not in actor_labels
    assert "beneficiary advocate" not in actor_labels
    assert not any("Host Reasoned Project" in label for label in actor_labels)
    assert not any(label in {"Actor", "State object", "Evidence record", "Release gate"} for label in actor_labels)
    assert "grounded product actors or explicit governance owner roles" in decision.dimensions["validation_roles"]


def test_tribunal_role_suffixes_do_not_repeat_existing_role_words() -> None:
    assert _role_suffixed_label("Pattern Relief Studio proof", "proof reviewer") == "Pattern Relief Studio proof reviewer"
    assert _role_suffixed_label("Decision Workspace", "proof reviewer") == "Decision Workspace proof reviewer"


def test_greenfield_tribunal_preserves_lower_first_source_symbols_in_visible_roles() -> None:
    projection = tribunal_actor_projection(
        {
            "title": "mRNA Stability Batch Comparison Workspace",
            "intent": {"title": "mRNA Stability Batch Comparison Workspace"},
            "backlog": [
                {
                    "title": "Show proof",
                    "customer": "Formulation Scientist",
                    "domain_intelligence": {
                        "actors": ["Formulation Scientist"],
                        "evidence_model": ["Review evidence belongs in mRNA Stability Batch Proof Record."],
                        "proof_standards": ["mRNA Stability Batch Proof Record must show accepted input."],
                    },
                }
            ],
        }
    )
    role_labels = {row["stable_role"]: row["visible_actor"] for row in projection}

    assert role_labels["risk_owner"] == "mRNA Stability Batch risk reviewer"
    assert role_labels["evidence_owner"] == "mRNA Stability Batch proof reviewer"
    assert not any("MRNA Stability" in row["visible_actor"] for row in projection)


def test_greenfield_tribunal_splits_collapsed_judgment_roles() -> None:
    projection = tribunal_actor_projection(
        {
            "title": "Cross-Boundary Evidence Workspace",
            "intent": {"title": "Cross-Boundary Evidence Workspace"},
            "backlog": [
                {
                    "title": "Prove one complete evidence path",
                    "customer": "Regional Evidence",
                    "domain_intelligence": {
                        "actors": [
                            "Regional Evidence: needs the product to collect reports and keep the result reviewable"
                        ],
                        "evidence_model": [
                            "Review evidence belongs in Cross-Boundary Proof Record; proof checks stay separate from narrative claims."
                        ],
                        "proof_standards": [
                            "Cross-Boundary Proof Record must show accepted input, changed state, validation result, and decision."
                        ],
                    },
                }
            ],
        }
    )
    role_labels = {row["stable_role"]: row["visible_actor"] for row in projection}

    assert role_labels["beneficiary_advocate"] == "Cross-Boundary Evidence Workspace beneficiary advocate"
    assert role_labels["domain_operator"] == "Cross-Boundary Evidence Workspace workflow operator"
    assert role_labels["risk_owner"] == "Cross-Boundary Evidence Workspace risk reviewer"
    assert role_labels["evidence_owner"] == "Cross-Boundary Evidence Workspace proof reviewer"
    assert len({role_labels[role] for role in ("beneficiary_advocate", "domain_operator", "risk_owner", "evidence_owner")}) == 4
    assert tribunal_visible_actor_quality_issues(projection) == ()


@pytest.mark.parametrize(
    ("title", "actor", "expected_role"),
    (
        ("Decision Evidence Review", "Algorithmic Accountability Auditor", "evidence_owner"),
        ("Safety Finding Review", "Maternal Safety Reviewer", "risk_owner"),
    ),
)
def test_greenfield_tribunal_does_not_reuse_explicit_reviewer_as_beneficiary(
    title: str,
    actor: str,
    expected_role: str,
) -> None:
    projection = tribunal_actor_projection(
        {
            "title": title,
            "intent": {"title": title},
            "project_intelligence": {"actors": [actor]},
            "backlog": [
                {
                    "customer": actor,
                    "domain_intelligence": {
                        "actors": [actor],
                        "operators": [actor],
                        "risks": [f"{actor} owns review exposure"],
                        "validation_obligations": [f"{actor} checks proof"],
                    },
                }
            ],
            "semantic_model": {"first_path_contract": {"actor": actor}},
        }
    )
    role_labels = {row["stable_role"]: row["visible_actor"] for row in projection}

    assert role_labels[expected_role] == actor
    assert role_labels["beneficiary_advocate"] != actor
    assert role_labels["beneficiary_advocate"].endswith("beneficiary advocate")
    assert len({role_labels[role] for role in ("beneficiary_advocate", "risk_owner", "evidence_owner")}) == 3
    assert tribunal_visible_actor_quality_issues(projection) == ()


def test_greenfield_tribunal_quality_rejects_collapsed_judgment_roles() -> None:
    collapsed = tuple(
        {
            "stable_role": role,
            "visible_actor": "Cross-Boundary Evidence Workspace proof reviewer",
            "responsibility": "Checks the generated proposal.",
        }
        for role in ("beneficiary_advocate", "domain_operator", "risk_owner", "evidence_owner")
    )

    issues = tribunal_visible_actor_quality_issues(collapsed)

    assert any("collapse distinct judgment roles" in issue for issue in issues)
    assert any("beneficiary_advocate uses evidence_owner role language" in issue for issue in issues)


def test_greenfield_tribunal_quality_rejects_collapsed_explicit_proof_labels() -> None:
    collapsed = tuple(
        {
            "stable_role": role,
            "visible_actor": "Neonatal Medication Compounding proof reviewer",
            "actor_source": "explicit_intent_actor",
            "responsibility": "Checks the generated proposal.",
        }
        for role in ("beneficiary_advocate", "domain_operator", "risk_owner", "evidence_owner")
    )

    issues = tribunal_visible_actor_quality_issues(collapsed)

    assert any("collapse distinct judgment roles" in issue for issue in issues)
    assert any("beneficiary_advocate uses evidence_owner role language" in issue for issue in issues)


def test_greenfield_tribunal_keeps_evidence_system_out_of_judgment_actor() -> None:
    projection = tribunal_actor_projection(
        {
            "title": "Consent Revocation Ledger",
            "intent": {"title": "Consent Revocation Ledger"},
            "project_intelligence": {
                "actors": [
                    "Consent coordinator - imports revocation requests.",
                    "Compliance reviewer - approves or blocks the revocation decision package.",
                    "Audit reviewer - checks blocked release evidence.",
                ]
            },
            "backlog": [
                {
                    "customer": "Consent coordinator; Compliance reviewer; Audit reviewer",
                    "domain_intelligence": {
                        "actors": [
                            "Consent coordinator - imports revocation requests.",
                            "Compliance reviewer - approves or blocks the revocation decision package.",
                            "Audit reviewer - checks blocked release evidence.",
                        ],
                        "evidence_types": ["Specimen Link Ledger"],
                        "proof_standards": ["Specimen Link Ledger must show applied restriction scope."],
                    },
                }
            ],
        }
    )
    role_labels = {row["stable_role"]: row["visible_actor"] for row in projection}

    assert role_labels["evidence_owner"].casefold() == "audit reviewer"
    assert role_labels["evidence_owner"] != "Specimen Link Ledger"
    assert tribunal_visible_actor_quality_issues(projection) == ()


def test_greenfield_tribunal_quality_rejects_generated_system_as_judgment_actor() -> None:
    issues = tribunal_visible_actor_quality_issues(
        (
            {
                "stable_role": "beneficiary_advocate",
                "visible_actor": "Consent Revocation Ledger beneficiary advocate",
                "actor_source": "generated_role_projection",
            },
            {
                "stable_role": "domain_operator",
                "visible_actor": "Consent Revocation Ledger workflow operator",
                "actor_source": "generated_role_projection",
            },
            {
                "stable_role": "risk_owner",
                "visible_actor": "Consent Revocation Ledger risk reviewer",
                "actor_source": "generated_role_projection",
            },
            {
                "stable_role": "evidence_owner",
                "visible_actor": "Specimen Link Ledger",
                "actor_source": "generated_role_projection",
            },
        )
    )

    assert any("lacks role-specific judgment language" in issue for issue in issues)


def test_greenfield_tribunal_ignores_runtime_behavior_scaffold_as_actor() -> None:
    projection = tribunal_actor_projection(
        {
            "title": "Municipal Permit Review Portal",
            "project_intelligence": {
                "actors": ["Resident", "Permit reviewer"],
                "operators": ["Runtime behavior to exercise: permit submission and correction handling"],
            },
            "semantic_model": {"first_path_contract": {"actor": "Resident"}},
        }
    )
    actor_labels = {row["visible_actor"] for row in projection}

    assert "Runtime behavior to exercise" not in actor_labels
    assert not any("Runtime behavior" in label for label in actor_labels)
    assert "Resident" in actor_labels
    assert "Project implementation owner" in actor_labels


def test_greenfield_tribunal_rejects_stable_proof_owner_as_visible_actor() -> None:
    projection = tribunal_actor_projection(
        {
            "title": "Municipal Permit Review Portal",
            "project_intelligence": {
                "actors": ["Resident applicant", "Permit reviewer"],
                "owners": ["Proof Owner"],
            },
            "backlog": [
                {
                    "customer": "Resident applicant",
                    "domain_intelligence": {
                        "actors": ["Resident applicant", "Permit reviewer"],
                        "risk_owners": ["Proof Owner"],
                        "evidence_types": ["Proof Owner"],
                        "proof_standards": ["Proof Owner"],
                    },
                }
            ],
            "semantic_model": {"first_path_contract": {"actor": "Resident applicant"}},
        }
    )
    actor_labels = [row["visible_actor"] for row in projection]
    normalized = {label.casefold() for label in actor_labels}

    assert "Proof Owner" not in actor_labels
    assert "resident applicant" in normalized
    assert "permit reviewer" in normalized or "project release owner" in normalized


def test_greenfield_tribunal_projection_keeps_explicit_actor_roles_distinct() -> None:
    projection = tribunal_actor_projection(
        {
            "project_intelligence": {"actors": ["Field technician", "Dispatch reviewer"]},
            "backlog": [
                {
                    "customer": "Field technician; Dispatch reviewer",
                    "domain_intelligence": {
                        "actors": ["Field technician", "Dispatch reviewer"],
                        "operators": ["Field technician"],
                        "risks": ["Dispatch reviewer owns release risk"],
                        "validation_obligations": ["Field technician proof"],
                        "evidence_types": ["visit evidence"],
                    },
                }
            ],
        }
    )
    labels = [row["visible_actor"] for row in projection]

    assert "Field Technician" in labels
    assert labels.count("Field Technician") >= 2
    assert "Dispatch risk reviewer" in labels
    assert "Dispatch proof reviewer" in labels
    assert "Field Technician Proof" not in labels
    assert any("risk reviewer" in label.casefold() for label in labels)
    assert tribunal_visible_actor_quality_issues(projection) == ()


def test_greenfield_tribunal_projection_repairs_project_title_proof_reviewer_labels() -> None:
    projection = tribunal_actor_projection(
        {
            "title": "Neonatal Medication Compounding Exception",
            "intent": {"title": "Neonatal Medication Compounding Exception"},
            "project_intelligence": {
                "actors": [
                    "Neonatal Medication Compounding proof reviewer",
                ],
            },
            "backlog": [
                {
                    "title": "Review compounding exception",
                    "customer": "Neonatal Medication Compounding proof reviewer",
                    "domain_intelligence": {
                        "actors": [
                            "Neonatal Medication Compounding proof reviewer",
                        ],
                        "operators": [],
                        "risk_owners": [],
                    },
                }
            ],
        }
    )
    role_labels = {row["stable_role"]: row["visible_actor"] for row in projection}

    assert role_labels["beneficiary_advocate"] == "Neonatal Medication Compounding beneficiary advocate"
    assert role_labels["domain_operator"] == "Neonatal Medication Compounding workflow operator"
    assert role_labels["risk_owner"] == "Neonatal Medication Compounding risk reviewer"
    assert role_labels["evidence_owner"] == "Neonatal Medication Compounding proof reviewer"
    assert tribunal_visible_actor_quality_issues(projection) == ()


def test_greenfield_artifacts_are_bound_to_project_intelligence_root(tmp_path) -> None:
    proposal = _governed_greenfield_fixture(tmp_path, "DeFi risk sentinel app")
    schema = proposal["project_intelligence"]["schema_version"]
    keys = list(proposal)

    assert keys.index("artifact_derivation") == keys.index("project_intelligence") + 1
    assert proposal["artifact_derivation"]["root"] == "project_intelligence"
    assert proposal["artifact_derivation"]["root_schema_version"] == schema
    assert proposal["release_plan"]["project_intelligence_binding"]["source"] == "project_intelligence"
    assert proposal["program"]["project_intelligence_binding"]["source"] == "project_intelligence"
    for collection in (
        proposal["program"]["waves"],
        proposal["backlog"],
        proposal["components"],
        proposal["diagrams"],
    ):
        for row in collection:
            binding = row["project_intelligence_binding"]
            assert binding["source"] == "project_intelligence"
            assert binding["schema_version"] == schema
            assert binding["artifact_kind"]
            assert binding["artifact_id"]


def test_greenfield_validation_rejects_artifacts_without_project_intelligence_binding(tmp_path) -> None:
    proposal = _governed_greenfield_fixture(tmp_path, "DeFi risk sentinel app")
    proposal["components"][0].pop("project_intelligence_binding")

    with pytest.raises(ValueError, match="project_intelligence_binding"):
        greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_tribunal_rejects_unbound_artifact_projection(tmp_path) -> None:
    proposal = _governed_greenfield_fixture(tmp_path, "DeFi risk sentinel app")
    proposal["diagrams"][0].pop("project_intelligence_binding")

    decision = greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1")

    assert not decision.passed
    assert any("project_intelligence_binding" in issue for issue in decision.issues)


def test_traceability_open_questions_render_without_repeated_labels() -> None:
    line = greenfield_traceability._question_impact_line(
        "Does the first release need applicant self-service?",
        "Changes the visible flow and validation target",
        prefix=False,
    )

    assert line == "Does the first release need applicant self-service? Changes the visible flow and validation target."
    assert "Question:" not in line
    assert "Impact:" not in line


def test_artifact_enrichment_projects_domain_graph_into_native_artifact_shapes(tmp_path) -> None:
    from odylith.runtime.domain_intelligence.artifact_enrichment import build_artifact_enrichment

    proposal = _governed_greenfield_fixture(tmp_path, "plant sensor")
    row = next(item for item in proposal["backlog"] if item["title"] == "Define Storefront boundary")

    enrichment = build_artifact_enrichment(row=row, proposal=proposal)

    assert "Domain Intelligence" not in enrichment.radar_sections
    assert enrichment.registry_contract["proof_obligations"]
    assert enrichment.atlas_contract["state_objects"]
    assert enrichment.plan_contract["validation"]
    assert enrichment.casebook_contract["prevention_rules"]
    assert enrichment.compass_contract["proof_boundary"]
    assert enrichment.project_contract["first_path"]


def test_greenfield_apply_shapes_radar_specs_with_domain_intelligence_substrate(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_surface_refresh_proof,
        "build_prewrite_surface_refresh_preview",
        lambda **_kwargs: surface_refresh_preview_fixture(),
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "passed", "atlas_surface_count": 3, "atlas_diagram_count": 2},
    )
    proposal = _governed_greenfield_fixture(tmp_path, "plant sensor")
    proposal["intent"]["summary"] = "**Primary reviewer** can compare the accepted path, state, and evidence."
    proposal["backlog"][1]["customer"] = "**Primary reviewer** and __source reviewer__"
    proposal["diagrams"][0]["components"][0]["description"] = "__Surface reviewer__ checks the visible behavior boundary."
    proposal = display_text.strip_inline_markdown_emphasis_tree(proposal)

    result = commit_precompiled_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    specs_by_title = {
        row["title"]: Path(row["idea_path"]).read_text(encoding="utf-8")
        for row in result["backlog"]
    }
    child_specs = [
        text
        for title, text in specs_by_title.items()
        if not title.startswith("Govern Commerce Launch System")
    ]
    joined = "\n".join(child_specs)

    assert "## Domain Intelligence" not in joined
    assert "## First Path And Boundary" in joined
    assert "## Domain Model" not in joined
    assert "## Proof And Acceptance Gates" in joined
    assert "## Ownership And Risk" in joined
    assert "Evidence record:" in joined
    assert "Validation gate:" in joined
    assert "\n- Proof:" not in joined
    assert "\n- Gate:" not in joined
    assert "source-backed implementation claims" in joined
    parent_spec = specs_by_title["Govern Commerce Launch System"]
    all_radar_text = parent_spec + "\n" + joined
    assert "impacted_parts: application,registry,atlas,radar" not in all_radar_text
    assert "impacted_parts: Storefront, Checkout Orchestrator, Catalog Boundary" in parent_spec
    assert "impacted_parts: Storefront, Checkout Orchestrator" in specs_by_title["Define Storefront boundary"]
    assert "impacted_parts: Catalog Boundary" in specs_by_title["Define Catalog boundary"]
    assert "## Project Intelligence" not in all_radar_text
    assert "## Project Brief" not in all_radar_text
    assert "## Project Requirements" not in all_radar_text
    assert "Do not start coding from the proposal closeout" not in all_radar_text
    assert "Starting implementation without a named product spine" not in all_radar_text
    assert "under-modeled in broad greenfield prompts" not in all_radar_text
    assert "Combining cart, payment, and order state would hide failure recovery" in all_radar_text
    assert all_radar_text.count("Combining cart, payment, and order state would hide failure recovery") == 1
    assert "Storefront can accept incomplete input" in all_radar_text
    assert "Catalog Boundary can accept incomplete input" in all_radar_text
    assert "owns Own" not in all_radar_text
    assert "owns owns" not in all_radar_text.casefold()
    assert "Which stack owns the storefront?" in all_radar_text
    assert "- R1." not in all_radar_text
    assert "- Q1." not in all_radar_text
    assert "- domain contract.\n" not in all_radar_text
    assert "- command.\n" not in all_radar_text
    assert "release targeting.\n- and proof sequencing." not in all_radar_text
    assert "?.\n" not in all_radar_text
    assert "**Primary reviewer**" not in all_radar_text
    assert "__source reviewer__" not in all_radar_text
    assert "Primary reviewer and source reviewer" in all_radar_text
    accepted_path = tmp_path / "odylith" / "runtime" / "source" / "accepted-project.v1.json"
    accepted_text = accepted_path.read_text(encoding="utf-8")
    accepted = json.loads(accepted_text)
    assert accepted["schema_version"] == "odylith.accepted_project.v1"
    assert accepted["origin"] == "greenfield"
    assert accepted["proposal"]["artifact_derivation"]["root"] == "project_intelligence"
    assert accepted["validation_gate"]["status"] == "passed"
    assert accepted["validation_gate"]["visible_actors"]
    assert '"tribunal"' not in accepted_text
    assert "greenfield-tribunal" not in accepted_text
    assert "governed-artifact-tribunal" not in accepted_text
    assert "**Primary reviewer**" not in accepted_text
    assert "__Surface reviewer__" not in accepted_text


def test_greenfield_apply_replaces_child_copies_of_parent_risk(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _governed_greenfield_fixture(tmp_path, "Build an ecommerce checkout recovery product")
    parent_risk = proposal["risks"][0]
    parent_risk_line = proposal_risk_lines(proposal)[0]
    proposal["backlog"][1]["domain_risk"] = parent_risk
    proposal["backlog"][1]["risks"] = [parent_risk]
    proposal["backlog"][2]["domain_risk"] = parent_risk_line
    proposal["backlog"][2]["risks"] = [parent_risk_line]

    result = commit_precompiled_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    rendered = "\n".join(Path(row["idea_path"]).read_text(encoding="utf-8") for row in result["backlog"])

    assert rendered.count("Combining cart, payment, and order state would hide failure recovery") == 1
    assert "Storefront can accept incomplete input" in rendered
    assert "Catalog Boundary can accept incomplete input" in rendered


def test_greenfield_apply_feeds_project_tab_from_accepted_project_and_tribunal(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    prompt = "Build an ecommerce site with checkout recovery"
    proposal = _governed_greenfield_fixture(tmp_path, prompt)

    commit_precompiled_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )
    payload = project_intelligence_builder.build_project_intelligence_payload(
        repo_root=tmp_path,
        shell_payload={},
    )
    html = project_intelligence_presenter.render_project_html({"project_intelligence": payload})
    accepted = json.loads((tmp_path / "odylith" / "runtime" / "source" / "accepted-project.v1.json").read_text(encoding="utf-8"))
    backlog_index = (tmp_path / "odylith" / "radar" / "source" / "INDEX.md").read_text(encoding="utf-8")
    b002 = accepted["proposal"]["backlog"][1]
    text = json.dumps(payload, sort_keys=True).casefold()

    assert accepted["proposal"]["intent"]["title"] == "Build An Ecommerce Site With Checkout Recovery"
    assert accepted["proposal"]["intent"]["project_slug"] == "build-an-ecommerce-site-with-checkout-recovery"
    assert b002["title"] == "Define Storefront boundary"
    assert b002["problem"].startswith("The user-facing browse and checkout UI")
    assert "created as a new queued workstream" not in backlog_index
    assert "deeper scope decomposition waits" not in backlog_index
    assert "Define Storefront boundary" in backlog_index
    assert "an-ecommerce-site-with-checkout-recovery" not in text
    assert payload["title"] == "Ecommerce Site with Checkout Recovery"
    assert payload["projection"]["origin"] == "accepted greenfield project"
    assert "accepted greenfield project" in payload["chips"]
    story = payload["product_story"]
    assert story["headline"] == "Ecommerce Site with Checkout Recovery"
    assert "Make Build" not in " ".join(story["paragraphs"])
    assert len(story["paragraphs"]) >= 2
    assert not any("keeps the work focused" in paragraph for paragraph in story["paragraphs"])
    assert not any("The first path defines" in paragraph for paragraph in story["paragraphs"])
    assert not any("Together, those records keep release" in paragraph for paragraph in story["paragraphs"])
    assert story["supporting_records"] == []
    _assert_project_story_cards(story)
    assert all(term not in json.dumps(story) for term in ("Radar", "Registry", "Atlas", "Compass"))
    assert "Product Story" in html
    assert "Storefront" in html
    assert "How the story becomes governance" not in html
    assert "Topology spine" not in html
    assert "Story root" not in html
    assert "Project not defined yet" not in html
    assert "Current orienting work" not in html
    assert "No active release detected" not in html
    assert prompt not in json.dumps(story, sort_keys=True)
    assert "checkout" in text
    assert "shopper" in text
    assert "storefront" in text
    assert "funding" not in text
    assert "underwriting" not in text
    assert any("Shopper advocate" == row[1] for row in payload["actors"])
    assert any("Commerce operator" == row[1] for row in payload["actors"])
    assert any("Payment risk reviewer" == row[1] for row in payload["actors"])
    assert any(
        row["claim"] == "Accepted product check" and row["value"] == "passed" and row["source"].endswith("accepted-project.v1.json")
        for row in payload["claim_evidence"]
    )


def test_greenfield_project_tab_participants_prefer_project_actors_over_internal_tribunal_concepts(
    tmp_path,
) -> None:
    proposal = _governed_greenfield_fixture(tmp_path, "plant sensor")
    proposal["_accepted_project"] = {
        "validation_gate": {
            "visible_actors": [
                {
                    "stable_role": "beneficiary_advocate",
                    "visible_actor": "Safety envelope",
                    "responsibility": "Protects the person receiving the value.",
                },
                {
                    "stable_role": "domain_operator",
                    "visible_actor": "Program Boundary operator",
                    "responsibility": "Checks workflow coherence.",
                },
                {
                    "stable_role": "evidence_owner",
                    "visible_actor": "Program Boundary proof owner",
                    "responsibility": "Decides proof strength.",
                },
            ]
        }
    }

    payload = project_intelligence_greenfield.build_greenfield_payload(proposal=proposal, repo_root=tmp_path)
    participants = list(payload["participants"])
    titles = [row[1] for row in participants]
    kickers = [row[0] for row in participants]

    assert "Plant owner advocate" in titles
    assert "Care routine operator" in titles
    assert "Plant safety reviewer" in titles
    assert "Safety envelope" not in titles
    assert "Program Boundary operator" not in titles
    assert "Program Boundary proof owner" not in titles
    assert all(kicker == "" for kicker in kickers)
    assert payload["participants_title"] == "Who participates?"
    assert "claim_evidence_title" not in payload
    assert payload["state_title"] == "Where does this stand?"
    assert payload["next_title"] in {"What should move next?", "Start source creation"}
    assert proposal["intent"]["title"] not in payload["participants_title"]


def test_greenfield_apply_runs_artifact_tribunal_for_each_atlas_diagram(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    original = greenfield_confirmed_prewrite_gate.artifact_tribunal.run_governed_artifact_tribunal
    diagram_payloads: list[dict[str, object]] = []

    def capture_tribunal(*, artifact_kind: str, payload: Mapping[str, object]) -> object:
        if artifact_kind == "atlas_diagram":
            diagram_payloads.append(dict(payload))
        return original(artifact_kind=artifact_kind, payload=payload)

    monkeypatch.setattr(
        greenfield_confirmed_prewrite_gate.artifact_tribunal,
        "run_governed_artifact_tribunal",
        capture_tribunal,
    )
    proposal = _governed_greenfield_fixture(tmp_path, "DeFi risk sentinel app")

    greenfield_confirmed_prewrite_gate.preflight_issues(
        proposal,
        release_selector="0.0.1",
    )

    assert len(diagram_payloads) == len(proposal["diagrams"])
    assert all(payload["watch_paths"] for payload in diagram_payloads)


def test_greenfield_normalization_preserves_host_authored_intelligence() -> None:
    proposal = greenfield_proposals.normalize_host_reasoned_proposal(_host_reasoned_ecommerce_proposal())
    child = next(row for row in proposal["backlog"] if row["title"] == "Define Storefront boundary")
    intelligence = child["domain_intelligence"]
    rendered = render_domain_intelligence_section(intelligence)
    brief = proposal["project_brief"]
    project_intelligence = proposal["project_intelligence"]

    assert intelligence["family"] == "host_reasoned_project"
    actor_text = json.dumps(intelligence["actors"])
    assert "Shopper advocate" in actor_text
    assert "Commerce operator" in actor_text
    assert "Payment risk reviewer" in actor_text
    assert "Checkout proof reviewer" in actor_text
    assert "commerce" not in intelligence["family"]
    assert "Payment callback" not in rendered
    assert "Product story" in json.dumps(brief)
    assert "Actors and systems" in json.dumps(brief)
    assert len(brief["customization_options"]) >= 5
    assert len(brief["customization_prompts"]) >= 3
    assert len(brief["coding_readiness_gates"]) >= 4
    assert "Payment callback" not in "\n".join(project_intelligence["ontology"])
    assert set(PROJECT_INTELLIGENCE_LAYERS).issubset(project_intelligence.keys())
    assert len(project_intelligence["change_model"]) >= 2
    greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_normalization_does_not_invent_dependency_gaps() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][1].pop("dependencies")
    proposal["backlog"][1].pop("interfaces")
    proposal["components"][0]["dependencies"] = []

    normalized = greenfield_proposals.normalize_host_reasoned_proposal(proposal)
    child = next(row for row in normalized["backlog"] if row["title"] == "Define Storefront boundary")
    component = next(row for row in normalized["components"] if row["component_id"] == "commerce-storefront")

    assert "dependencies" not in child
    assert "interfaces" not in child
    assert component["dependencies"] == []
    assert "planned boundary" not in json.dumps(normalized)
    assert "No upstream component dependency is claimed" not in json.dumps(normalized)


def test_greenfield_normalization_compacts_verbose_release_plan_label_to_selector() -> None:
    proposal = greenfield_proposals.normalize_host_reasoned_proposal(_host_reasoned_recipe_legacy_shape())

    assert proposal["release_plan"]["selector"] == "0.0.1"
    assert proposal["release_plan"]["label"] == "0.0.1"


def test_greenfield_normalization_splits_scalar_quality_fields() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    identity = proposal["backlog"][1]
    identity["success_metrics"] = (
        "Checkout recovery measured by browser proof; "
        "Order idempotency measured by replay contract tests"
    )
    identity.pop("recommended_first_slice")
    identity["validation"] = [
        "Browser proof passes for failed-checkout recovery.",
        "Replay proof blocks duplicate order creation.",
    ]
    proposal["release_plan"]["target_workstreams"] = "Define Storefront boundary, Define Catalog boundary"
    proposal["program"]["waves"][0].pop("validation_gate", None)
    proposal["program"]["waves"][0]["validation"] = [
        "Browse-to-cart proof passes",
        "Failed-payment recovery proof passes",
    ]

    normalized = greenfield_proposals.normalize_host_reasoned_proposal(proposal)
    normalized_identity = next(
        row for row in normalized["backlog"] if row["title"] == "Define Storefront boundary"
    )
    tribunal = greenfield_proposals.run_greenfield_tribunal(normalized, release_selector="0.0.1")

    assert normalized_identity["success_metrics"] == [
        "Checkout recovery measured by browser proof",
        "Order idempotency measured by replay contract tests",
    ]
    assert normalized_identity["recommended_first_slice"] == (
        "Start Define Storefront boundary with the smallest source-backed slice for this product view: "
        "Storefront should own browse, cart entry, checkout entry, and user-visible errors."
    )
    assert normalized["release_plan"]["target_workstreams"] == ["Define Storefront boundary", "Define Catalog boundary"]
    assert normalized["program"]["waves"][0]["validation_gate"] == (
        "Browse-to-cart proof passes; Failed-payment recovery proof passes"
    )
    assert "['" not in normalized_identity["recommended_first_slice"]
    assert "['" not in normalized["program"]["waves"][0]["validation_gate"]
    greenfield_proposals.validate_host_reasoned_proposal(normalized)
    assert tribunal.passed


def test_greenfield_apply_scalar_wave_validation_dedupes_handoff_gates(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _host_reasoned_ecommerce_proposal()
    identity = proposal["backlog"][1]
    identity["success_metrics"] = (
        "Checkout recovery measured by browser proof; "
        "Order idempotency measured by replay contract tests"
    )
    identity.pop("recommended_first_slice")
    identity["validation"] = [
        "Browser proof covers happy path and failed-checkout recovery",
        "Replay proof blocks duplicate order creation",
    ]
    proposal["program"]["waves"][0].pop("validation_gate", None)
    proposal["program"]["waves"][0]["validation"] = [
        "Browse-to-cart proof passes",
        "Failed-payment recovery proof passes",
    ]

    result = commit_precompiled_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )
    first_wave = result["program"]["waves"][0]
    joined_wave_gate = "Browse-to-cart proof passes; Failed-payment recovery proof passes"

    assert first_wave["exit_gate"] == joined_wave_gate
    assert first_wave["validation"] == [
        "Browse-to-cart proof passes",
        "Failed-payment recovery proof passes",
    ]
    assert joined_wave_gate not in result["next_steps"]["validation_gates"]
    assert "Browser proof covers the happy path and failed-checkout recovery" in result["next_steps"]["validation_gates"]
    assert "Browser proof covers happy path" not in json.dumps(result["next_steps"], sort_keys=True)
    assert result["next_steps"]["validation_gates"][-2:] == first_wave["validation"]


def test_greenfield_release_target_label_extracts_numeric_selector_from_custom_text() -> None:
    assert greenfield_proposals.greenfield_programs.compact_release_target_label("Recipe-sharing 0.0.1") == "0.0.1"
    assert greenfield_proposals.greenfield_programs.compact_release_target_label("launch candidate release target") == (
        "launch candidat..."
    )


def test_greenfield_apply_rejects_shallow_child_backlog_metrics(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _governed_greenfield_fixture(tmp_path, "checkout recovery")
    proposal["backlog"][1]["success_metrics"] = ["Component linked."]

    with pytest.raises(ValueError, match="at least two success_metrics"):
        greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_apply_rejects_control_plane_terms_in_consumer_product_fields(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][1]["success_metrics"][0] = "The checkout boundary appears in Registry and Atlas."
    proposal["components"][0]["description"] = "The storefront succeeds when Radar and Compass expose the work."

    with pytest.raises(ValueError) as excinfo:
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    message = str(excinfo.value)
    assert "greenfield public product content leaks Odylith control-plane term `Radar`" in message
    assert "greenfield public product content leaks Odylith control-plane term `Registry`" in message
    assert "greenfield public product content leaks Odylith control-plane term `Atlas`" in message
    assert "greenfield public product content leaks Odylith control-plane term `Compass`" in message


def test_greenfield_quality_gate_allows_control_plane_homonym_from_accepted_intent() -> None:
    proposal = {
        "intent": {
            "title": "Landslide Warning Review",
            "first_path": (
                "Field hydrologists combine rainfall radar, slope sensor readings, "
                "soil moisture estimates, and inspection notes before publishing a warning status."
            ),
            "state_object": "Hillside segment warning record with rainfall radar evidence.",
        },
        "backlog": [
            {
                "title": "Let Field Hydrologists Review Rainfall Radar",
                "problem": "Rainfall radar evidence is hard to compare with field inspection notes.",
            }
        ],
    }

    issues = greenfield_quality_issues(proposal)

    assert not any("control-plane term `Radar`" in issue for issue in issues)


def test_greenfield_apply_reports_validation_issues_in_one_batch(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _governed_greenfield_fixture(tmp_path, "checkout recovery")
    proposal["backlog"][1].pop("problem")
    proposal["backlog"][2]["success_metrics"] = ["Too shallow."]
    proposal["components"][0]["responsibility"] = "UI"

    with pytest.raises(ValueError) as excinfo:
        greenfield_proposals.validate_host_reasoned_proposal(proposal)

    message = str(excinfo.value)
    assert "greenfield proposal validation failed with" in message
    assert "backlog row 2 `problem` must be non-empty" in message
    assert "backlog row 3 must include at least two success_metrics" in message
    assert "component row 1 `responsibility` must contain at least 6 meaningful words" in message
    assert "auto-enrichment:" in message
    assert "needs operator/proposal input:" in message


def test_greenfield_validation_rejects_missing_project_first_brief(tmp_path) -> None:
    proposal = _governed_greenfield_fixture(tmp_path, "warehouse dispatch planning app")
    proposal.pop("project_brief")

    with pytest.raises(ValueError) as excinfo:
        greenfield_proposals.validate_host_reasoned_proposal(proposal)

    assert "proposal `project_brief` must be an object" in str(excinfo.value)


def test_greenfield_validation_rejects_missing_project_intelligence(tmp_path) -> None:
    proposal = _governed_greenfield_fixture(tmp_path, "warehouse dispatch planning app")
    proposal.pop("project_intelligence")

    with pytest.raises(ValueError) as excinfo:
        greenfield_proposals.validate_host_reasoned_proposal(proposal)

    assert "proposal `project_intelligence` must be an object" in str(excinfo.value)


def test_project_brief_blocks_coding_rush_without_domain_scaffold(tmp_path) -> None:
    proposal = _governed_greenfield_fixture(tmp_path, "warehouse dispatch planning app")
    brief = proposal["project_brief"]
    rendered = greenfield_proposals.format_proposal_text(proposal)

    assert "Simulation and hardware boundary" not in json.dumps(brief)
    assert "safety envelope" not in json.dumps(brief)
    assert "Project requirements" in rendered
    assert "Coding starts only after the accepted project story" in rendered
    assert rendered.index("Project requirements") < rendered.index("Backlog proposal")
    assert "greenfield propose --repo-root ." in rendered
    assert "greenfield compile-transaction --repo-root ." not in rendered
    assert "greenfield create --repo-root ." not in rendered
    assert "Warehouse Dispatch Planning App Operator Workspace" not in rendered


def test_greenfield_apply_rejects_shallow_component_responsibility(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _governed_greenfield_fixture(tmp_path, "checkout recovery")
    proposal["components"][0]["responsibility"] = "UI stuff."

    with pytest.raises(ValueError, match="responsibility"):
        greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_apply_rejects_missing_security_compliance_posture(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal.pop("security_compliance")

    with pytest.raises(ValueError, match="security_compliance"):
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_backlog_overrides_preserve_child_specific_sections() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][0]["impacted_parts"] = "application,registry,atlas,radar"
    child = next(row for row in proposal["backlog"] if row["title"].startswith("Define "))
    overrides = greenfield_proposals._backlog_section_overrides(proposal)
    args = argparse.Namespace(
        problem="parent",
        customer="parent",
        opportunity="parent",
        product_view="parent",
        success_metrics="parent",
        domain_risk="parent domain risk",
        security_posture="parent security posture",
        priority="P1",
        impacted_parts="parent",
        sizing="M",
        complexity="Medium",
        ordering_rationale="parent",
        section_overrides_by_title=overrides,
    )

    resolved = backlog_authoring._title_specific_args(title=child["title"], args=args)

    assert (
        overrides[proposal["backlog"][0]["title"]]["impacted_parts"]
        == "Storefront, Checkout Orchestrator, Catalog Boundary"
    )
    assert resolved.problem == child["problem"]
    assert resolved.product_view == child["product_view"]
    assert child["success_metrics"][0] in resolved.success_metrics
    assert resolved.impacted_parts == "Storefront, Checkout Orchestrator"


def test_greenfield_apply_bootstraps_first_release_selector(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    refresh_calls: list[dict[str, object]] = []
    def capture_prewrite_refresh(**kwargs: object) -> dict[str, object]:
        refresh_calls.append(
            {
                "repo_root": kwargs["repo_root"],
                "surfaces": greenfield_surface_refresh_proof.GREENFIELD_VISIBLE_SURFACES,
                "operation_label": "Greenfield pre-confirm staged surface refresh",
            }
        )
        return surface_refresh_preview_fixture()

    monkeypatch.setattr(
        greenfield_surface_refresh_proof,
        "build_prewrite_surface_refresh_preview",
        capture_prewrite_refresh,
    )
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["release_plan"].pop("selector")

    result = commit_precompiled_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="",
    )

    registry = json.loads((tmp_path / "odylith/radar/source/releases/releases.v1.json").read_text(encoding="utf-8"))
    events = (tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl").read_text(encoding="utf-8")
    system_context = (tmp_path / "odylith/atlas/source/commerce-launch-system-context.mmd").read_text(encoding="utf-8")
    program_waves = (tmp_path / "odylith/atlas/source/commerce-launch-program-waves.mmd").read_text(encoding="utf-8")
    execution_program = json.loads(
        (tmp_path / "odylith/radar/source/programs/B-001.execution-waves.v1.json").read_text(encoding="utf-8")
    )
    atlas_catalog = json.loads((tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json").read_text(encoding="utf-8"))
    parent_idea = Path(result["backlog"][0]["idea_path"]).read_text(encoding="utf-8")
    child_idea = Path(result["backlog"][1]["idea_path"]).read_text(encoding="utf-8")
    storefront_spec = (
        tmp_path / "odylith/registry/source/components/commerce-storefront/CURRENT_SPEC.md"
    ).read_text(encoding="utf-8")
    component_registry = json.loads(
        (tmp_path / "odylith/registry/source/component_registry.v1.json").read_text(encoding="utf-8")
    )
    assert result["release_bootstrap"]["created"] is True
    assert registry["aliases"]["0.0.1"] == "release-commerce-launch-first"
    assert registry["aliases"]["current"] == "release-commerce-launch-first"
    assert registry["releases"][0]["name"] == "0.0.1"
    assert len(result["backlog"]) == 3
    assert len(result["components"]) == 3
    assert len(result["diagrams"]) == 2
    assert result["validation_gate"]["status"] == "passed"
    assert result["dashboard_refresh"]["surfaces"] == ["radar", "registry", "atlas", "compass", "tooling_shell"]
    assert result["dashboard_refresh"]["view"] == "odylith/index.html?tab=project"
    assert refresh_calls
    assert all(call["repo_root"] != tmp_path.resolve() for call in refresh_calls)
    assert all(
        call["operation_label"] == "Greenfield pre-confirm staged surface refresh"
        for call in refresh_calls
    )
    assert result["program"]["created"] is True
    assert result["program"]["umbrella_id"] == "B-001"
    assert len(result["program"]["waves"]) == 2
    assert result["program"]["waves"][0]["wave_id"] == "W1"
    assert result["program"]["waves"][0]["primary_workstreams"] == ["B-002"]
    assert result["program"]["waves"][1]["wave_id"] == "W2"
    assert result["program"]["waves"][1]["primary_workstreams"] == ["B-003"]
    assert execution_program["waves"][0]["label"] == "Checkout spine"
    assert execution_program["waves"][0]["primary_workstreams"] == ["B-002"]
    assert execution_program["waves"][1]["label"] == "Catalog integrity"
    assert execution_program["waves"][1]["primary_workstreams"] == ["B-003"]
    assert result["release_bootstrap"]["release"]["version"] == "0.0.1"
    assert result["release_bootstrap"]["release"]["tag"] == "v0.0.1"
    assert result["release_bootstrap"]["release"]["name"] == "0.0.1"
    assert result["release_target"]["workstream_ids"] == ["B-001", "B-002"]
    release_payload, release_errors, _release_state = release_planning_view_model.build_release_view_from_repo(
        repo_root=tmp_path,
        idea_specs=None,
    )
    assert release_errors == []
    assert release_payload["current_release"]["release_id"] == "release-commerce-launch-first"
    assert release_payload["current_release"]["display_label"] == "0.0.1"
    assert release_payload["current_release"]["active_workstreams"] == ["B-001", "B-002"]
    assert build_traceability_graph.main(["--repo-root", str(tmp_path)]) == 0
    traceability_graph = json.loads((tmp_path / "odylith/radar/traceability-graph.v1.json").read_text(encoding="utf-8"))
    assert traceability_graph["current_release"]["release_id"] == "release-commerce-launch-first"
    assert traceability_graph["current_release"]["active_workstreams"] == ["B-001", "B-002"]
    assert result["backlog_topology"] == [
        Path(result["backlog"][0]["idea_path"]).relative_to(tmp_path).as_posix(),
        Path(result["backlog"][1]["idea_path"]).relative_to(tmp_path).as_posix(),
        Path(result["backlog"][2]["idea_path"]).relative_to(tmp_path).as_posix(),
    ]
    assert "Payment sandbox" in system_context
    assert "Order reliability" in program_waves
    assert system_context != program_waves
    assert "related_diagram_ids: D-001,D-002" in parent_idea
    assert "related_diagram_ids: D-001,D-002" in child_idea
    assert "## Impacted Components" in child_idea
    assert "`commerce-storefront`" in child_idea
    backlog_paths = {
        Path(str(row["idea_path"])).relative_to(tmp_path).as_posix()
        for row in result["backlog"]
    }
    atlas_backlog_paths = {
        str(path)
        for row in atlas_catalog["diagrams"]
        for path in row["related_backlog"]
    }
    assert backlog_paths & atlas_backlog_paths
    assert all(not Path(path).is_absolute() for path in atlas_backlog_paths)
    assert "odylith-greenfield-prewrite" not in json.dumps(atlas_catalog)
    storefront = next(row for row in component_registry["components"] if row["component_id"] == "commerce-storefront")
    assert storefront["workstreams"] == ["B-002"]
    assert storefront["diagrams"] == []
    assert storefront["what_it_is"].startswith("Storefront defines the planned application ownership boundary")
    assert all(
        token in storefront["what_it_is"]
        for token in ("local result", "blocked cases", "recovery path", "review evidence")
    )
    assert "responsible for" not in storefront["what_it_is"]
    assert "browse" in storefront_spec
    assert "cart entry" in storefront_spec
    assert "checkout entry" in storefront_spec
    assert "user-facing errors" in storefront_spec
    assert "It owns browse, cart entry, checkout entry, and user-facing errors" not in storefront_spec
    assert "Trace links for Storefront: workstreams B-002" in storefront_spec
    assert "| Workstreams | `B-002` |" not in storefront_spec
    assert "| Diagrams | none yet |" not in storefront_spec
    assert "Browser smoke proof for browse-to-cart and failed-checkout messaging" in storefront_spec
    assert result["memory"]["recorded"] is True
    assert result["memory"]["event"]["source"] == "domain-intelligence"
    assert '"release_id": "release-commerce-launch-first"' in events


def test_greenfield_apply_reuses_existing_diagram_ids_for_backlog_traceability(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    atlas_catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    atlas_catalog_path.write_text(
        json.dumps(
            {
                "schema_version": "odylith.diagrams.v1",
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "slug": "commerce-launch-system-context",
                        "title": "Old Context",
                    },
                    {
                        "diagram_id": "D-002",
                        "slug": "commerce-launch-program-waves",
                        "title": "Old Waves",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    result = commit_precompiled_greenfield_proposal(
        repo_root=tmp_path,
        proposal=_host_reasoned_ecommerce_proposal(),
        confirm=True,
        release_selector="0.0.1",
    )

    parent_idea = Path(result["backlog"][0]["idea_path"]).read_text(encoding="utf-8")
    child_idea = Path(result["backlog"][1]["idea_path"]).read_text(encoding="utf-8")
    atlas_catalog = json.loads(atlas_catalog_path.read_text(encoding="utf-8"))

    assert result["diagrams"] == ["D-001", "D-002"]
    assert {row["diagram_id"] for row in atlas_catalog["diagrams"]} == {"D-001", "D-002"}
    assert "related_diagram_ids: D-001,D-002" in parent_idea
    assert "related_diagram_ids: D-001,D-002" in child_idea
    assert "D-003" not in parent_idea
    assert "D-003" not in child_idea
    assert build_traceability_graph.main(["--repo-root", str(tmp_path)]) == 0
    traceability_graph = json.loads((tmp_path / "odylith/radar/traceability-graph.v1.json").read_text(encoding="utf-8"))
    assert not any("not found in catalog" in warning for warning in traceability_graph["warnings"])


def test_greenfield_apply_rejects_legacy_recipe_shape_without_host_authored_project_intelligence(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    with pytest.raises(ValueError, match="project_intelligence|domain_intelligence|program parent|quality gate"):
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_recipe_legacy_shape(),
            confirm=True,
            release_selector="0.0.1",
        )

    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()


def test_greenfield_apply_rejects_missing_host_authored_program_parent(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    with pytest.raises(ValueError, match="program parent|project_intelligence|domain_intelligence|quality gate"):
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_crispr_without_parent(),
            confirm=True,
            release_selector="0.0.1",
        )

    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/radar/source/programs").exists()
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()


def test_greenfield_apply_writes_host_authored_component_specs(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _governed_greenfield_fixture(tmp_path, "Build an ecommerce checkout recovery product")

    result = commit_precompiled_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    spec_root = tmp_path / "odylith/registry/source/components"
    storefront_spec = (spec_root / "commerce-storefront/CURRENT_SPEC.md").read_text(encoding="utf-8")
    checkout_spec = (spec_root / "commerce-checkout/CURRENT_SPEC.md").read_text(encoding="utf-8")
    catalog_spec = (spec_root / "commerce-catalog/CURRENT_SPEC.md").read_text(encoding="utf-8")
    atlas_catalog = json.loads((tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json").read_text(encoding="utf-8"))

    assert result["validation_gate"]["status"] == "passed"
    assert [row["label"] for row in proposal["components"]] == [
        "Storefront",
        "Checkout Orchestrator",
        "Catalog Boundary",
    ]
    assert "browse, cart entry, checkout entry, and user-facing errors" in storefront_spec
    assert "payment handoff, order draft, idempotency, and recovery boundaries" in checkout_spec
    assert "product facts, price snapshots, inventory visibility, and merchandising review" in catalog_spec
    assert "Trace links for Storefront: workstreams B-002" in storefront_spec
    assert "Trace links for Checkout Orchestrator: workstreams B-002" in checkout_spec
    assert "Trace links for Catalog Boundary: workstreams B-003" in catalog_spec
    assert "Implementation anchor for Storefront: B-002 (Define Storefront boundary)" in storefront_spec
    assert "Implementation anchor for Catalog Boundary: B-003 (Define Catalog boundary)" in catalog_spec
    assert "Implementation anchor for Catalog Boundary: B-002 (Define Storefront boundary)" not in catalog_spec
    assert "## Component Brief" not in storefront_spec
    assert "## Boundary Narrative" not in storefront_spec
    assert "## First Release Proof" not in checkout_spec
    assert "## First Release Proof" not in catalog_spec
    assert "## Storefront Interaction Boundary" not in storefront_spec
    assert "## Checkout Orchestrator Runtime Boundary" not in checkout_spec
    assert "## Catalog Boundary Runtime Boundary" not in catalog_spec
    assert len({storefront_spec, checkout_spec, catalog_spec}) == 3
    assert "browse, cart entry, checkout entry" in storefront_spec
    assert "payment handoff, order draft" in checkout_spec
    assert "price snapshots" in catalog_spec
    for text in (storefront_spec, checkout_spec, catalog_spec):
        assert "Accepted intent" in text
        assert "Suggested fixture:" not in text
        assert "Product context:" not in text
        assert "Project outcome:" not in text
        assert "Release 0.0.1 contribution:" not in text
        assert "Required proof:" not in text
        assert "Contract focus:" not in text
        assert "Primary interface:" not in text
        assert "Proof obligation:" not in text
        assert "accepted first release path" not in text
        assert "**" not in text
        assert "…" not in text
        assert "Experience Boundary" not in text
        assert "registered through `odylith component register`" not in text
        assert "first operator-visible workflow, view or command entrypoint" not in text
        assert "Source-backed runtime behavior until implementation proof lands" not in text
        assert "Production readiness, storage ownership, or external-provider guarantees" not in text
        assert "Starting implementation without a named product spine" not in text
        assert "Security, privacy, accessibility, and operational risks can be under-modeled" not in text
        assert "Security posture starts with authentication or operator access boundaries" not in text
        assert "Policy posture tracks privacy, retention, accessibility" not in text
        assert "The first workstream has a technical plan" not in text
        assert "The workflow boundary appears in Registry and Atlas" not in text
        assert "Registry spec" not in text
        assert "Compass projection" not in text
        assert "Radar lane" not in text
        assert "| Diagrams | `D-001`" not in text
        assert "R1." not in text
        assert "odylith_assumption" not in text
    assert storefront_spec != checkout_spec
    assert checkout_spec != catalog_spec
    assert {row["link_state"] for row in atlas_catalog["diagrams"]} == {"atlas_first_draft"}


def test_greenfield_component_dependency_lines_are_grammatical_from_component_rows() -> None:
    lookup = component_dependency_lookup_for(
        [
            {
                "component_id": "observation-ledger",
                "label": "Observation Ledger",
                "responsibility": "Capture and serve append-only observations.",
            },
            {
                "component_id": "evidence-linker",
                "label": "Evidence Linker",
                "responsibility": "Bind observations to claims and produce signed evidence bundles.",
            },
            {
                "component_id": "condition-deriver",
                "label": "Condition Deriver",
                "responsibility": "Compute the current condition from the evidence trail.",
            },
        ]
    )

    lines = component_dependency_lines(
        ["observation-ledger", "evidence-linker", "condition-deriver"],
        lookup=lookup,
    )

    assert "Depends on Observation Ledger for capturing and serving append-only observations" in lines
    assert "Depends on Evidence Linker for binding observations to claims and producing signed evidence bundles" in lines
    assert "Depends on Condition Deriver for computing the current condition from the evidence trail" in lines


def test_greenfield_apply_namespaces_partial_project_diagram_slugs_before_scaffold(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    atlas_catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    atlas_catalog_path.write_text(
        json.dumps(
            {
                "schema_version": "odylith.diagrams.v1",
                "diagrams": [{"diagram_id": "D-001", "slug": "checkout-flow"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["diagrams"][0]["slug"] = "checkout-flow"
    for row in proposal["backlog"]:
        if "related_diagram_slugs" in row:
            row["related_diagram_slugs"] = [
                "checkout-flow" if value == "commerce-launch-system-context" else value
                for value in row["related_diagram_slugs"]
            ]

    result = commit_precompiled_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    atlas_catalog = json.loads(atlas_catalog_path.read_text(encoding="utf-8"))
    assert result["validation_gate"]["status"] == "passed"
    assert "checkout-flow" in {row["slug"] for row in atlas_catalog["diagrams"]}
    assert "commerce-launch-system-checkout-flow" in {row["slug"] for row in atlas_catalog["diagrams"]}
    assert (tmp_path / "odylith/atlas/source/commerce-launch-system-checkout-flow.mmd").is_file()


def test_greenfield_apply_rolls_back_partial_writes_when_late_step_fails(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    original_index = (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8")

    def fail_scaffold(**_kwargs: object) -> object:
        raise RuntimeError("synthetic scaffold failure")

    monkeypatch.setattr(greenfield_apply_diagrams, "materialize_apply_diagrams", fail_scaffold)

    with pytest.raises(ValueError, match="synthetic scaffold failure"):
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_ecommerce_proposal(),
            confirm=True,
            release_selector="0.0.1",
        )

    assert (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8") == original_index
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/radar/source/releases").exists()
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not (tmp_path / "odylith/atlas/source/commerce-launch-system-context.mmd").exists()


def test_greenfield_apply_rolls_back_partial_writes_when_dashboard_refresh_fails(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    original_index = (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8")

    def fail_refreshes(**kwargs: object) -> dict[str, object]:
        staged_root = Path(str(kwargs["repo_root"]))
        _write(staged_root / "odylith/radar/radar.html", "partial dashboard\n")
        _write(staged_root / "odylith/runtime/delivery_intelligence.v4.json", "{}\n")
        raise RuntimeError("synthetic dashboard refresh failure")

    monkeypatch.setattr(
        greenfield_surface_refresh_proof,
        "build_prewrite_surface_refresh_preview",
        fail_refreshes,
    )
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    with pytest.raises(ValueError, match="synthetic dashboard refresh failure"):
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_ecommerce_proposal(),
            confirm=True,
            release_selector="0.0.1",
        )

    assert (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8") == original_index
    assert not (tmp_path / "odylith/radar/radar.html").exists()
    assert not (tmp_path / "odylith/runtime/delivery_intelligence.v4.json").exists()
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not (tmp_path / "odylith/atlas/source/commerce-launch-system-context.mmd").exists()


def test_greenfield_transaction_restores_symlinked_snapshot_root_without_traversal(tmp_path) -> None:
    external_radar = tmp_path / "external-radar"
    external_radar.mkdir()
    _write(external_radar / "outside.md", "external truth\n")
    radar_link = tmp_path / "odylith/radar"
    radar_link.parent.mkdir(parents=True)
    try:
        radar_link.symlink_to(external_radar, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    with pytest.raises(RuntimeError, match="synthetic failure"):
        with GreenfieldApplyTransaction(tmp_path):
            radar_link.unlink()
            _write(tmp_path / "odylith/radar/partial.md", "partial write\n")
            raise RuntimeError("synthetic failure")

    assert radar_link.is_symlink()
    assert radar_link.resolve() == external_radar.resolve()
    assert (external_radar / "outside.md").read_text(encoding="utf-8") == "external truth\n"
    assert not (tmp_path / "odylith/radar/partial.md").exists()


def test_greenfield_transaction_restores_nested_symlink_without_copying_target(tmp_path) -> None:
    radar_root = tmp_path / "odylith/radar"
    radar_root.mkdir(parents=True)
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside\n", encoding="utf-8")
    nested_link = radar_root / "linked.txt"
    try:
        nested_link.symlink_to(outside_file)
    except OSError as exc:
        pytest.skip(f"file symlink unavailable: {exc}")

    with pytest.raises(RuntimeError, match="synthetic failure"):
        with GreenfieldApplyTransaction(tmp_path):
            nested_link.unlink()
            nested_link.write_text("regular replacement\n", encoding="utf-8")
            raise RuntimeError("synthetic failure")

    assert nested_link.is_symlink()
    assert nested_link.resolve() == outside_file.resolve()
    assert outside_file.read_text(encoding="utf-8") == "outside\n"


def test_greenfield_transaction_rolls_back_managed_brand_assets(tmp_path) -> None:
    brand_asset = tmp_path / "odylith/surfaces/brand/lockup/odylith-lockup-horizontal.svg"

    with pytest.raises(RuntimeError, match="synthetic failure"):
        with GreenfieldApplyTransaction(tmp_path):
            brand_asset.parent.mkdir(parents=True, exist_ok=True)
            brand_asset.write_text("<svg></svg>\n", encoding="utf-8")
            raise RuntimeError("synthetic failure")

    assert not brand_asset.exists()


def test_greenfield_apply_requires_confirmation(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)

    with pytest.raises(ValueError, match="--confirm is required"):
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_ecommerce_proposal(),
            confirm=False,
            release_selector="0.0.1",
        )
