from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    looks_mechanical_summary,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    proof_focus_phrase,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    semantic_words,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    shares_product_terms,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_occurrences


ROOT = Path(__file__).resolve().parents[3]
DOMAIN_INTELLIGENCE = ROOT / "src/odylith/runtime/domain_intelligence"
BACKLOG_TEXT_MODEL_PATH = DOMAIN_INTELLIGENCE / "greenfield_confirmed_backlog_text_model.py"


def test_confirmed_backlog_terms_use_shared_domain_index() -> None:
    source = BACKLOG_TEXT_MODEL_PATH.read_text(encoding="utf-8")

    assert "greenfield_domain_term_index import ordered_terms" in source
    assert "greenfield_confirmed_text import word_count" in source
    assert "greenfield_confirmed_text import word_occurrences" in source
    assert 're.findall(r"[a-z0-9][a-z0-9-]+"' not in source
    assert 'len(re.findall(r"[A-Za-z0-9][A-Za-z0-9' not in source
    assert 'len(re.findall(r"\\brequired\\b"' not in source
    assert semantic_words("Status windows, review services, and source-backed audit trails.") == {
        "audit",
        "review",
        "service",
        "source-backed",
        "status",
        "trail",
        "window",
    }
    assert shares_product_terms(
        "Deliver status windows with proof evidence.",
        "A window proof evidence summary remains visible.",
    )
    assert not shares_product_terms(
        "Deliver the accepted first product path.",
        "The release result lets the user complete that path.",
    )
    assert proof_focus_phrase(
        "Operator approval, with a very long release readiness decision and many additional words, final signoff",
        fallback="fallback",
    ) == "operator approval"
    assert looks_mechanical_summary("required actor identity and required validation context")
    assert word_occurrences("Required proof, source evidence, and required signoff.", "required") == 2
