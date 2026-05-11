"""Static assets owned by the Project intelligence projection."""

from __future__ import annotations

from pathlib import Path


def project_tab_css_path() -> Path:
    """Return the source-owned Project tab stylesheet path."""

    return Path(__file__).resolve().with_name("project_tab.css")


def load_project_tab_css() -> str:
    """Load the source-owned Project tab stylesheet."""

    return project_tab_css_path().read_text(encoding="utf-8")
