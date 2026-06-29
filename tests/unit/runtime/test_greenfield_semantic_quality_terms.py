from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_apply_components import (
    first_release_component_rows,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import (
    confirmed_components,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import (
    release_scope_for_component,
    sentence_overlap_ratio,
)


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"


def test_semantic_quality_terms_use_shared_index_aliases() -> None:
    index_source = (DOMAIN_INTELLIGENCE / "greenfield_domain_term_index.py").read_text(
        encoding="utf-8"
    )
    semantic_source = (DOMAIN_INTELLIGENCE / "greenfield_semantic_quality.py").read_text(
        encoding="utf-8"
    )

    assert "aliases:" in index_source
    assert "prefix_aliases:" in index_source
    assert (
        "from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms"
        in semantic_source
    )
    assert (
        "from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms"
        in semantic_source
    )
    assert "normalize_domain_token" not in semantic_source
    assert "re.findall" not in semantic_source

    assert ordered_terms(
        "shared sharing shares reminding reminded reminders statuses",
        stem_ing=True,
        prefix_aliases={"shar": "share", "remind": "reminder"},
    ) == ["share", "reminder", "status"]
    assert label_terms("AI CRM Status Windows", stopwords={"crm"}) == [
        "AI",
        "Status",
        "Windows",
    ]
    assert (
        sentence_overlap_ratio(
            "Reviewer submits safety report with photo proof",
            "Reviewer submits safety report with photo proof",
            ngram=3,
        )
        == 1.0
    )

    assert (
        release_scope_for_component(
            {
                "label": "Reminder and Sharing Service",
                "responsibility": (
                    "sends reminders and shares summaries after the core journal loop"
                ),
            },
            first_path="A person creates a pain entry, sees the persisted entry, and edits it.",
            proof_boundary="Release succeeds without claiming reminders or clinician sharing.",
            non_goals=[
                "Reminders and clinician sharing are deferred until the journal loop works."
            ],
        )
        == "out_of_scope"
    )


def test_release_scope_keeps_affirmative_proof_owner_despite_negative_claim_boundary() -> None:
    first_path = (
        "Project operators upload monitoring evidence, independent verifiers record validation decisions, "
        "registry reviewers resolve exceptions, and buyers inspect issuance readiness without claiming financial settlement."
    )
    proof_boundary = (
        "Release 0.0.1 succeeds when project operators upload monitoring evidence, independent verifiers record "
        "validation decisions, registry reviewers resolve exceptions, and buyers inspect issuance readiness without "
        "claiming financial settlement. The product shows issuance readiness without claiming financial settlement, "
        "handles missing input with a clear blocker, and keeps replayable evidence for review."
    )

    scope = release_scope_for_component(
        {
            "label": "Attestation Proof Ledger",
            "source_system_description": (
                "keeps validation results, release decisions, failure reasons, and replayable evidence for review"
            ),
            "responsibility": (
                "Keeps validation results, release decisions, failure reasons, and replayable evidence for review"
            ),
            "boundary": "Attestation Proof Ledger owns validation evidence and local handoff decisions.",
        },
        first_path=first_path,
        proof_boundary=proof_boundary,
        non_goals=[],
    )

    assert scope == "supporting"

    rows = confirmed_components(
        label="Carbon Removal MRV",
        label_slug="carbon-removal-mrv",
        internal_systems=[
            "Intake register — records source input, current status, owner, blocker, handoff, and version history.",
            "Review workspace — presents current state, missing input, user-facing confirmation, and next action.",
            "Proof ledger — keeps validation results, release decisions, failure reasons, and replayable evidence for review.",
        ],
        first_path=first_path,
        state_object="attestation readiness record",
        proof_boundary=proof_boundary,
        external_systems=[],
        non_goals=[],
    )
    scopes = {str(row["label"]): str(row["release_scope"]) for row in rows}

    assert any("Proof Ledger" in label and scope != "out_of_scope" for label, scope in scopes.items())
    assert len(first_release_component_rows({"components": rows})) == 3
