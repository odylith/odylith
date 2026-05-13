"""Project intelligence projection for the tooling dashboard Project tab."""

from __future__ import annotations

from odylith.runtime.project_intelligence.builder import build_project_intelligence_payload
from odylith.runtime.project_intelligence.intent_confirmation import build_product_intent_confirmation
from odylith.runtime.project_intelligence.intent_confirmation import format_product_intent_confirmation_text
from odylith.runtime.project_intelligence.presenter import render_project_html

__all__ = [
    "build_project_intelligence_payload",
    "build_product_intent_confirmation",
    "format_product_intent_confirmation_text",
    "render_project_html",
]
