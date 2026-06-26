from odylith.runtime.domain_intelligence import artifact_enrichment
from odylith.runtime.domain_intelligence import greenfield_traceability


def test_traceability_validation_items_reuse_shared_article_normalizer() -> None:
    rows = greenfield_traceability._validation_section_items(
        ["Browser proof covers happy path and failed-checkout recovery."]
    )

    assert rows == ["Browser proof covers the happy path and failed-checkout recovery."]


def test_artifact_enrichment_preserves_validate_that_predicates() -> None:
    validation_line = artifact_enrichment._scoped_sentence(
        "Validation gate",
        "Define first release boundary",
        "Validate that the story, workstreams, components, diagrams, and release plan describe the same first path.",
    )

    assert validation_line == (
        "Validation gate: Define first release boundary — Validate that the story, workstreams, "
        "components, diagrams, and release plan describe the same first path"
    )
    assert not validation_line.endswith("and components")
