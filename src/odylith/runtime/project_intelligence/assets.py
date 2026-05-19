"""Static assets owned by the Project intelligence projection."""

from __future__ import annotations

from pathlib import Path

from odylith.runtime.surfaces.dashboard_ui_primitives import detail_label_chip_css
from odylith.runtime.surfaces.dashboard_ui_primitives import surface_workstream_button_chip_css


def project_tab_css_path() -> Path:
    """Return the source-owned Project tab stylesheet path."""

    return Path(__file__).resolve().with_name("project_tab.css")


def _project_shared_chip_css() -> str:
    """Return Project chip CSS generated from shared dashboard primitives."""

    return "\n\n".join(
        (
            surface_workstream_button_chip_css(selector=".project-workstream-chip"),
            detail_label_chip_css(
                selector=".project-label-chip",
                size_px=12,
                weight=700,
                padding="4px 10px",
                radius_px=4,
            ),
            """
.project-label-chip-neutral {
  --label-bg: #f4f8fd;
  --label-border: #c9dbf3;
  --label-text: #24466f;
}

.project-label-chip-success {
  --label-bg: #dcfce7;
  --label-border: #bbf7d0;
  --label-text: #15803d;
}

.project-label-chip-warning {
  --label-bg: #fff7ed;
  --label-border: #fed7aa;
  --label-text: #9a3412;
}
""".strip(),
        )
    )


def load_project_tab_css() -> str:
    """Load the source-owned Project tab stylesheet."""

    return f"{project_tab_css_path().read_text(encoding='utf-8')}\n\n{_project_shared_chip_css()}"
