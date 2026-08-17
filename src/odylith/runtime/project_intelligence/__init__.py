"""Project intelligence projection for the tooling dashboard Project tab."""

from __future__ import annotations

from odylith.runtime.project_intelligence.builder import build_project_intelligence_payload
from odylith.runtime.project_intelligence.presenter import render_project_html

__all__ = [
    "build_project_intelligence_payload",
    "render_project_html",
]
