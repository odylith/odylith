from odylith.runtime.domain_intelligence import artifact_enrichment
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
