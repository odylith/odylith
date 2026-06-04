from __future__ import annotations

import copy
from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import project_intelligence_issues
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import domain_intelligence_issues
from tests.unit.runtime.greenfield_proposal_fixtures import _host_reasoned_ecommerce_proposal

ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"


def _apply_ready_fixture(tmp_path, prompt: str) -> dict[str, object]:  # noqa: ANN001
    _ = tmp_path, prompt
    return _host_reasoned_ecommerce_proposal()


def test_project_intelligence_requires_explicit_invalidation_rules(tmp_path) -> None:
    proposal = _apply_ready_fixture(tmp_path, "confirmed project")

    intelligence = proposal["project_intelligence"]

    assert "invalidation_rules" in intelligence
    assert "surface" not in "\n".join(intelligence["invalidation_rules"]).casefold()
    assert "Coding starts only after" in intelligence["coding_posture"]

    broken = copy.deepcopy(intelligence)
    broken.pop("invalidation_rules")

    assert "proposal `project_intelligence.invalidation_rules` must include at least 2 rows" in project_intelligence_issues(broken)


def test_workstream_intelligence_captures_scope_owners_and_invalidation_rules(tmp_path) -> None:
    proposal = _apply_ready_fixture(tmp_path, "confirmed project")
    workflow = next(row for row in proposal["backlog"] if row["title"] == "Define Storefront boundary")

    intelligence = workflow["domain_intelligence"]

    assert intelligence["scope"]
    assert intelligence["owners"]
    assert intelligence["invalidation_rules"]
    assert not domain_intelligence_issues(intelligence, owner="workflow")

    broken = copy.deepcopy(intelligence)
    broken.pop("owners")

    assert "workflow domain_intelligence.owners is missing or too shallow" in domain_intelligence_issues(
        broken,
        owner="workflow",
    )

    duplicate = copy.deepcopy(intelligence)
    duplicate["ontology"] = [
        *duplicate["ontology"],
        "Risk subject: first repeated term label.",
        "Risk subject: repeated term label that would make the workstream read like a padded template.",
    ]

    assert "workflow domain_intelligence.ontology repeats operational term(s): Risk subject" in domain_intelligence_issues(
        duplicate,
        owner="workflow",
    )

    malformed = copy.deepcopy(intelligence)
    malformed["scope"] = ["In scope: `Prove analyst watchlist and alert triage workflow` owns Own duplicated ownership text."]

    assert "workflow domain_intelligence contains malformed ownership phrase" in domain_intelligence_issues(
        malformed,
        owner="workflow",
    )


def test_semantic_model_term_extraction_uses_shared_domain_index() -> None:
    model_source = (DOMAIN_INTELLIGENCE / "greenfield_semantic_model.py").read_text(encoding="utf-8")
    index_source = (DOMAIN_INTELLIGENCE / "greenfield_domain_term_index.py").read_text(encoding="utf-8")
    text_source = (DOMAIN_INTELLIGENCE / "greenfield_confirmed_text.py").read_text(encoding="utf-8")

    assert "def ordered_terms" in index_source
    assert "def word_count" in text_source
    assert "from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms" in model_source
    assert "from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count" in model_source
    assert "def _semantic_terms" not in model_source
    assert "normalize_domain_token" not in model_source
    assert 're.findall(r"[A-Za-z0-9]+"' not in model_source
    assert "_SEMANTIC_MODEL_TERM_STOPWORDS" in model_source

    model = build_greenfield_semantic_model(
        title="Race Reading Review",
        state_object="Race reading record with gearbox status",
        first_path="A reviewer opens race readings, reviews gearbox status, and records evidence.",
        proof_boundary="Release succeeds when reviewed readings show evidence and status.",
        components=[],
        human_actors=["Race reviewer"],
    )

    assert model.domain_ontology.domain_terms == (
        "evidence",
        "gearbox",
        "open",
        "race",
        "reading",
        "review",
        "reviewed",
        "reviewer",
        "show",
        "status",
    )
    assert model.first_path_contract.required_fields[:4] == (
        "status",
        "evidence",
        "race",
        "reading",
    )

    proof_model = build_greenfield_semantic_model(
        title="AI Review",
        state_object="AI review record",
        first_path="Reviewer saves an AI/ML status note.",
        proof_boundary="Done means: save the `AI/ML` review status and source note.",
        components=[],
        human_actors=["Reviewer"],
    )
    assert proof_model.diagram_event_graph.proof_checkpoint == (
        "visible outcome proof: Reviewer saves an AI/ML status note"
    )
