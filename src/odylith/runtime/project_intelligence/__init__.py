"""Project intelligence projection for the tooling dashboard Project tab."""

from __future__ import annotations

from typing import Any


def build_project_intelligence_payload(*args: Any, **kwargs: Any) -> Any:
    """Load the general repo-intelligence builder only when that API is called."""

    from odylith.runtime.project_intelligence.builder import (
        build_project_intelligence_payload as build,
    )

    return build(*args, **kwargs)


def render_project_html(*args: Any, **kwargs: Any) -> Any:
    """Load the HTML presenter only when that API is called."""

    from odylith.runtime.project_intelligence.presenter import render_project_html as render

    return render(*args, **kwargs)

__all__ = [
    "build_project_intelligence_payload",
    "render_project_html",
]
