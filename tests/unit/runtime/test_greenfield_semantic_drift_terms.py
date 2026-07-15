from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_drift import (
    semantic_overlap_ratio,
)
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import term_frequencies
from odylith.runtime.domain_intelligence.greenfield_text import word_count


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"


def test_post_confirm_semantic_drift_terms_use_shared_index() -> None:
    drift_source = (DOMAIN_INTELLIGENCE / "greenfield_preconfirm_semantic_drift.py").read_text(
        encoding="utf-8"
    )
    index_source = (DOMAIN_INTELLIGENCE / "greenfield_domain_term_index.py").read_text(
        encoding="utf-8"
    )
    text_source = (DOMAIN_INTELLIGENCE / "greenfield_text.py").read_text(encoding="utf-8")
    confirmed_text_source = (DOMAIN_INTELLIGENCE / "greenfield_confirmed_text.py").read_text(
        encoding="utf-8"
    )

    assert "def ordered_terms" in index_source
    assert "def term_frequencies" in index_source
    assert "def word_count" in text_source
    assert (
        "from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms"
        in drift_source
    )
    assert (
        "from odylith.runtime.domain_intelligence.greenfield_domain_term_index import term_frequencies"
        in drift_source
    )
    assert "from odylith.runtime.domain_intelligence.greenfield_text import word_count" in drift_source
    assert (
        "from odylith.runtime.domain_intelligence.greenfield_text import word_count as _generic_word_count"
        in confirmed_text_source
    )
    assert "normalize_domain_token" not in drift_source
    assert "for raw in re.findall" not in drift_source
    assert "len(re.findall" not in drift_source
    assert "ordered_terms(" in drift_source
    assert "term_frequencies(" in drift_source

    assert (
        semantic_overlap_ratio(
            "gearbox-reading evidence and permit-status context",
            "permit status context with gearbox reading evidence",
        )
        == 1.0
    )
    assert term_frequencies("gearbox reading gearbox reading permit status", minimum=4) == {
        "gearbox": 2,
        "reading": 2,
        "permit": 1,
        "status": 1,
    }
    assert word_count("`AI/ML` status review keeps source evidence visible.") == 8
