from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import complete_confirmed_proposal
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import semantic_compiler_issues
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_intent_with_authority


def test_prd_style_proof_language_repairs_generated_modal_drift(tmp_path: Path) -> None:
    confirmed_intent = confirmed_intent_with_authority(
        """Product Requirements Draft: PDE Solver Evaluation Lab

1. Background
Researchers need a governed way to decide when neural PDE solvers are worth using instead of defaulting to novelty claims. The first version is for research engineers comparing neural and classical PDE solvers.

2. Primary user and job
Primary users: Evaluation researcher, Benchmark reviewer.
The job is to complete this release path: An evaluation researcher registers one elliptic PDE case, imports benchmark runs, compares a neural solver against a finite-element baseline, records uncertainty, and publishes an accepted or blocked solver decision.

3. Data model notes
The durable state is: A solver evaluation case tracks equation family, discretization, benchmark data, model configuration, classical baseline, tolerance, runtime budget, and review decision.
External integrations: Benchmark dataset repository, Compute job runner.
Internal services: Evaluation case ledger, Baseline comparison engine, Review decision board.

4. Release 0.0.1 rules
- The first release uses one PDE family and one baseline class.
- All reported claims include tolerance and reproducibility evidence.
- Success metric: Every accepted decision cites benchmark data, tolerance, baseline result, and reviewer signoff.
- Open product question: Whether GPU cost normalization belongs in the first release or the next release.

5. Risks and exclusions
Out of scope: Do not add general symbolic algebra or arbitrary solver synthesis.
Proof: A reviewer can reproduce the same accepted or blocked decision from the stored benchmark data, baseline run, tolerance, and model configuration.
""",
        prompt="Productize PDE Solver Evaluation Lab from a PRD intent document.",
        repo_root=tmp_path,
        source_format="markdown",
    )
    assert str(confirmed_intent["first_path"]).startswith("An evaluation researcher registers")
    assert str(confirmed_intent["state_object"]).startswith("A solver evaluation case tracks")
    assert str(confirmed_intent["proof_boundary"]).startswith("A reviewer can reproduce")
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Productize PDE Solver Evaluation Lab from a PRD intent document.",
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent,
    )

    completed = complete_confirmed_proposal(proposal, release_selector="0.0.1")

    modal_issues = [
        issue for issue in generated_semantic_slop_issues(completed, root="proposal") if "modal/base-form" in issue
    ]
    assert modal_issues == []
    assert semantic_compiler_issues(completed) == []
    assert "can reproduces" not in json.dumps(completed).casefold()
