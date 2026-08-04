from __future__ import annotations

import subprocess

from odylith.runtime.domain_intelligence import greenfield_component_contract_differentiation as differentiation
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_term_index import (
    component_domain_terms,
    component_local_terms,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)


def test_preconfirm_component_contracts_keep_local_first_path_meaning(tmp_path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    prompt = (
        "Create a greenfield proposal for a package supply chain exception desk that receives vulnerable "
        "dependency reports, tracks provenance and waiver evidence, coordinates package manager review, "
        "preserves release readiness proof, and blocks shipment until exceptions are approved."
    )
    candidate = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=greenfield_proposals.intent_title(prompt),
    )

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        confirmed_intent=candidate,
        require_completion_ready=False,
    )
    specs = differentiation._render_component_specs(proposal)

    assert rendered_component_spec_quality_issues(
        specs,
        project_title=differentiation._project_title(proposal),
    ) == []

    names = tuple(specs)
    name_terms = {name: component_domain_terms(name) for name in names}
    repeated_name_terms = {
        term
        for terms in name_terms.values()
        for term in terms
        if sum(term in sibling_terms for sibling_terms in name_terms.values()) > 1
    }
    spec_terms = {name: component_domain_terms(text) for name, text in specs.items()}
    all_spec_terms = tuple(spec_terms.values())
    for name in names:
        assert len(
            component_local_terms(
                text_terms=spec_terms[name],
                name_terms=name_terms[name],
                all_text_terms=all_spec_terms,
                repeated_name_terms=repeated_name_terms,
            )
        ) >= 4

    intake = next(
        row
        for row in proposal["components"]
        if str(row.get("label", "")).startswith("Vulnerable Dependency Reports")
    )
    intake_io = " ".join(
        str(intake["component_contract"].get(key, ""))
        for key in ("accepted_inputs", "produced_outputs")
    ).casefold()
    for sibling_fact in ("provenance", "waiver", "manager", "readiness", "shipment"):
        assert sibling_fact not in intake_io
