from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import proposal_validation
from odylith.runtime.domain_intelligence.greenfield_text import word_count


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"


def test_proposal_validation_word_count_stays_in_text_owner() -> None:
    validation_source = (DOMAIN_INTELLIGENCE / "proposal_validation.py").read_text(
        encoding="utf-8"
    )
    text_source = (DOMAIN_INTELLIGENCE / "greenfield_text.py").read_text(encoding="utf-8")

    assert "def word_count" in text_source
    assert (
        "from odylith.runtime.domain_intelligence.greenfield_text import word_count"
        in validation_source
    )
    assert "def _meaningful_word_count" not in validation_source
    assert 'len(re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*"' not in validation_source
    assert word_count("source-backed checkout-recovery status-window proof") == 7

    value = "source-backed checkout-recovery status-window proof"
    assert (
        proposal_validation._require_text(
            {"responsibility": value},
            "responsibility",
            owner="component row 1",
            min_words=6,
        )
        == value
    )
    with pytest.raises(ValueError, match="must contain at least 6 meaningful words"):
        proposal_validation._require_text(
            {"responsibility": "source-backed proof"},
            "responsibility",
            owner="component row 1",
            min_words=6,
        )
