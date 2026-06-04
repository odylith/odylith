from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence import proposal_tribunal_substance


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"


def test_confirmed_artifact_tribunal_terms_use_shared_index() -> None:
    substance_source = (DOMAIN_INTELLIGENCE / "proposal_tribunal_substance.py").read_text(
        encoding="utf-8"
    )
    index_source = (DOMAIN_INTELLIGENCE / "greenfield_domain_term_index.py").read_text(
        encoding="utf-8"
    )

    assert "def ordered_terms" in index_source
    assert (
        "from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms"
        in substance_source
    )
    assert "greenfield_domain_term_index import label_terms" in substance_source
    assert "normalize_domain_token" not in substance_source
    assert "for raw in re.findall" not in substance_source
    assert "len(re.findall" not in substance_source
    assert "accepted_terms = set(re.findall" not in substance_source
    assert "mermaid_text.numbered_flowchart_node_count" in substance_source
    assert "ordered_terms(" in substance_source
    assert "label_terms(accepted_text)" in substance_source

    tail_terms = proposal_tribunal_substance._atlas_tail_term_set(
        "Reviewer adds evidence, logs blockers, sees status, and publishes the outcome."
    )
    assert {"add", "log", "see", "publish"} <= tail_terms

    repeated_count = proposal_tribunal_substance._repeated_scaffold_count(
        "State object appears again. State object repeats. Evidence record repeats.",
        accepted_text="The accepted product stores evidence and record status.",
    )
    assert repeated_count == 2
