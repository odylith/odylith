from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.domain_intelligence import greenfield_quality_gate
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence import proposal_validation
from odylith.runtime.domain_intelligence import proposal_memory
from odylith.runtime.domain_intelligence.greenfield_text import word_count


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"
COMMON_VALUE_COERCION = ROOT / "src/odylith/runtime/common/value_coercion.py"


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


def test_issue_and_id_dedupe_stays_in_common_value_owner() -> None:
    common_source = COMMON_VALUE_COERCION.read_text(encoding="utf-8")
    callers = [
        DOMAIN_INTELLIGENCE / "proposal_validation.py",
        DOMAIN_INTELLIGENCE / "greenfield_quality_gate.py",
        DOMAIN_INTELLIGENCE / "greenfield_traceability.py",
        DOMAIN_INTELLIGENCE / "proposal_memory.py",
    ]

    assert "def dedupe_strings" in common_source
    assert dedupe_strings([" missing fact ", "missing fact", "", "Other"]) == [
        "missing fact",
        "Other",
    ]
    report = proposal_validation.format_proposal_issue_report(
        "validation",
        [" missing fact ", "missing fact", "", "Other"],
    )
    assert "2 issue(s)" in report
    assert report.count("- missing fact") == 1
    assert greenfield_quality_gate._dedupe([" issue row ", "issue row", "Other"]) == [
        "issue row",
        "Other",
    ]
    assert greenfield_traceability._join_ids(["b-001", " B-001 ", "b-002"]) == "B-001,B-002"
    assert proposal_memory._first_nonempty([" **One** ", "One", "Two", "Three"], limit=2) == [
        "One",
        "Two",
    ]

    for caller in callers:
        source = caller.read_text(encoding="utf-8")
        assert "value_coercion import dedupe_strings" in source
        assert "seen: set[str]" not in source
        assert "seen.add(" not in source
