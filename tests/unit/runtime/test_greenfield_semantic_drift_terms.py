from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_post_confirm_semantic_drift import (
    semantic_overlap_ratio,
)


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"


def test_post_confirm_semantic_drift_terms_use_shared_index() -> None:
    drift_source = (DOMAIN_INTELLIGENCE / "greenfield_post_confirm_semantic_drift.py").read_text(
        encoding="utf-8"
    )
    index_source = (DOMAIN_INTELLIGENCE / "greenfield_domain_term_index.py").read_text(
        encoding="utf-8"
    )

    assert "def ordered_terms" in index_source
    assert (
        "from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms"
        in drift_source
    )
    assert "normalize_domain_token" not in drift_source
    assert "for raw in re.findall" not in drift_source
    assert "ordered_terms(" in drift_source

    assert (
        semantic_overlap_ratio(
            "gearbox-reading evidence and permit-status context",
            "permit status context with gearbox reading evidence",
        )
        == 1.0
    )
