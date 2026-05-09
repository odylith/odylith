from __future__ import annotations

import copy

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import project_intelligence_issues
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import domain_intelligence_issues


def test_project_intelligence_requires_explicit_invalidation_rules(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="DeFi risk sentinel app",
    )["proposal_template"]

    intelligence = proposal["project_intelligence"]
    rendered = greenfield_proposals.render_project_intelligence_section(intelligence)

    assert "invalidation_rules" in intelligence
    assert "### Invalidation Rules" in rendered
    assert "oracle provenance" in "\n".join(intelligence["invalidation_rules"])
    assert "Do not start coding from the proposal closeout" in intelligence["coding_posture"]

    broken = copy.deepcopy(intelligence)
    broken.pop("invalidation_rules")

    assert "proposal `project_intelligence.invalidation_rules` must include at least 2 rows" in project_intelligence_issues(broken)


def test_workstream_intelligence_captures_scope_owners_and_invalidation_rules(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="DeFi risk sentinel app",
    )["proposal_template"]
    workflow = next(row for row in proposal["backlog"] if row["title"] == "Prove analyst watchlist and alert triage workflow")

    intelligence = workflow["domain_intelligence"]
    rendered = greenfield_proposals.render_domain_intelligence_section(intelligence)

    assert intelligence["scope"]
    assert intelligence["owners"]
    assert intelligence["invalidation_rules"]
    assert "### Scope And Boundary" in rendered
    assert "### Ownership Map" in rendered
    assert "### Invalidation Rules" in rendered
    assert "oracle freshness" in rendered
    assert "Operator owner" in rendered
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
