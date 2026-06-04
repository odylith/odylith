from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_experience import (
    _workstream_title_matches_component,
)


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"
EXPERIENCE_PATH = DOMAIN_INTELLIGENCE / "greenfield_experience.py"

HANDOFF_MATCH_STOPWORDS = {
    "adapter",
    "build",
    "component",
    "first",
    "handoffs",
    "implement",
    "path",
    "proof",
    "review",
    "service",
    "state",
    "surface",
    "system",
}


def test_experience_handoff_terms_use_shared_domain_index() -> None:
    source = EXPERIENCE_PATH.read_text(encoding="utf-8")

    assert "greenfield_domain_term_index import ordered_terms" in source
    assert "def _meaningful_terms" not in source
    assert "re.findall" not in source

    assert ordered_terms(
        "Status dashboards, status windows, and review services.",
        minimum=4,
        stopwords=HANDOFF_MATCH_STOPWORDS,
    ) == ["status", "dashboard", "window"]
    assert _workstream_title_matches_component(
        "Build status dashboards proof",
        {"label": "Status Dashboard Surface"},
    )
    assert not _workstream_title_matches_component(
        "Build dashboard targets",
        {"label": "Status Dashboard Surface"},
    )
    assert not _workstream_title_matches_component(
        "Build reviews service handoffs",
        {"label": "Review Service"},
    )
