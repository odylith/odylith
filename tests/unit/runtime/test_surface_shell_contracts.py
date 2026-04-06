from __future__ import annotations

from pathlib import Path
import re

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _has_versioned_script_tag(*, html: str, src: str, script_id: str | None = None) -> bool:
    attrs = [f'src="{re.escape(src)}(?:\\?v=[^"]+)?"']
    if script_id is not None:
        attrs.insert(0, f'id="{re.escape(script_id)}"')
    return re.search("<script " + " ".join(attrs) + "></script>", html) is not None


def test_shell_index_declares_all_surface_tabs_and_frames() -> None:
    html = _read("odylith/index.html")

    for tab in ("radar", "registry", "casebook", "atlas", "compass"):
        assert f'id="tab-{tab}"' in html

    for frame_id in ("frame-radar", "frame-registry", "frame-casebook", "frame-atlas", "frame-compass"):
        assert f'id="{frame_id}"' in html


@pytest.mark.parametrize(
    ("path", "tab", "frame_id", "payload_id", "payload_src", "app_src", "query_targets"),
    (
        (
            "odylith/radar/radar.html",
            "radar",
            "frame-radar",
            "backlogData",
            "backlog-payload.v1.js",
            "backlog-app.v1.js",
            ("view", "workstream"),
        ),
        (
            "odylith/registry/registry.html",
            "registry",
            "frame-registry",
            "registryData",
            "registry-payload.v1.js",
            "registry-app.v1.js",
            ("component",),
        ),
        (
            "odylith/casebook/casebook.html",
            "casebook",
            "frame-casebook",
            "casebookData",
            "casebook-payload.v1.js",
            "casebook-app.v1.js",
            ("bug", "severity", "status"),
        ),
        (
            "odylith/atlas/atlas.html",
            "atlas",
            "frame-atlas",
            "catalogData",
            "mermaid-payload.v1.js",
            "mermaid-app.v1.js",
            ("workstream", "diagram"),
        ),
        (
            "odylith/compass/compass.html",
            "compass",
            "frame-compass",
            "compassShellData",
            "compass-payload.v1.js",
            "compass-app.v1.js",
            ("scope", "window", "date", "audit_day"),
        ),
    ),
)
def test_standalone_surface_html_keeps_shell_embed_contract(
    path: str,
    tab: str,
    frame_id: str,
    payload_id: str,
    payload_src: str,
    app_src: str,
    query_targets: tuple[str, ...],
) -> None:
    html = _read(path)

    assert f'const expectedFrameId = "{frame_id}";' in html
    assert f'nextParams.set("tab", "{tab}");' in html
    assert _has_versioned_script_tag(html=html, src=payload_src, script_id=payload_id)
    assert _has_versioned_script_tag(html=html, src=app_src)

    for token in query_targets:
        assert f'"target":"{token}"' in html
