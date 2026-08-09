"""Regression proof for domain-term custody across governed projections."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_findings
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal


_CORPUS_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures/greenfield-release-corpus/retired-1c54-final-holdout-regressions.v1.json"
)
_CASE_IDS = frozenset(
    {
        "gfh-20260809-05",
        "gfh-20260809-10",
        "gfh-20260809-12",
        "gfh-20260809-19",
        "gfh-20260809-20",
        "gfh-20260809-22",
        "gfh-20260809-23",
    }
)
_CASES = tuple(
    case
    for case in json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))["cases"]
    if case["case_id"] in _CASE_IDS
)


@pytest.mark.parametrize("case", _CASES, ids=lambda case: str(case["case_id"]))
def test_required_terms_reach_projection_owned_meaning(
    tmp_path: Path,
    case: dict[str, object],
) -> None:
    prompt = str(case["prompt"])
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=str(case["name"]),
    )
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
        require_completion_ready=False,
    )
    owned_intent = json.dumps(
        {
            key: intent.get(key)
            for key in (
                "title",
                "human_actors",
                "first_path",
                "state_object",
                "external_systems",
                "operational_constraints",
                "non_goals",
            )
        },
        sort_keys=True,
    ).casefold()
    governed_projection = json.dumps(
        {
            key: proposal.get(key)
            for key in (
                "project_brief",
                "project_intelligence",
                "backlog",
                "components",
                "semantic_model",
                "diagrams",
            )
        },
        sort_keys=True,
    ).casefold()

    assert all(str(term).casefold() in owned_intent for term in case["required_terms"])
    assert all(str(term).casefold() in governed_projection for term in case["required_terms"])
    assert run_greenfield_tribunal(proposal, release_selector="0.0.1").passed
    assert not generated_public_copy_findings("proposal", proposal)
