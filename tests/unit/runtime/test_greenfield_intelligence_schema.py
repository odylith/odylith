from __future__ import annotations

import copy

from odylith.runtime.domain_intelligence.greenfield_project_intelligence import project_intelligence_issues
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import domain_intelligence_issues
from tests.unit.runtime.test_greenfield_proposals import _host_reasoned_ecommerce_proposal


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
