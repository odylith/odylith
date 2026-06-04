from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import (
    release_scope_for_component,
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
    assert "normalize_domain_token" not in semantic_source
    assert "for raw in re.findall" not in semantic_source

    assert ordered_terms(
        "shared sharing shares reminding reminded reminders statuses",
        stem_ing=True,
        prefix_aliases={"shar": "share", "remind": "reminder"},
    ) == ["share", "reminder", "status"]

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
