"""Template-context assembly for the tooling dashboard shell."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from odylith.runtime.surfaces import tooling_dashboard_frontend_contract


@dataclass(frozen=True)
class ToolingDashboardTemplateContext:
    shell_repo_label: str
    shell_repo_name: str
    shell_title: str
    shell_subtitle: str
    shell_version_label: str
    brand_head_html: str
    shell_brand_lockup_href: str
    shell_brand_icon_href: str
    style_css: str
    welcome_html: str
    maintainer_notes_html: str
    cheatsheet_html: str
    payload_json: str
    control_script: str


def build_template_context(
    payload: Mapping[str, Any],
    *,
    welcome_html: str,
    maintainer_notes_html: str,
    cheatsheet_html: str,
) -> ToolingDashboardTemplateContext:
    """Assemble the stable template context for one shell render."""

    tooling_dashboard_frontend_contract.assert_tooling_shell_header_contract()
    payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    shell_repo_label = str(payload.get("shell_repo_label", "")).strip() or "Repo"
    shell_repo_name = str(payload.get("shell_repo_name", "")).strip()
    shell_version_label = str(payload.get("shell_version_label", "")).strip()
    odylith_switch = (
        dict(payload.get("odylith_switch", {}))
        if isinstance(payload.get("odylith_switch"), Mapping)
        else {}
    )
    if odylith_switch and not bool(odylith_switch.get("enabled", True)):
        shell_title = "Odylith Dashboard"
        shell_subtitle = (
            "Shared operator dashboard with Odylith ablated for comparison runs across Registry, Casebook, Atlas, Radar, and Compass."
        )
    else:
        shell_title = "Odylith"
        shell_subtitle = "Delivery Governance and Intelligence"
    return ToolingDashboardTemplateContext(
        shell_repo_label=shell_repo_label,
        shell_repo_name=shell_repo_name,
        shell_title=shell_title,
        shell_subtitle=shell_subtitle,
        shell_version_label=shell_version_label,
        brand_head_html=str(payload.get("brand_head_html", "")).strip(),
        shell_brand_lockup_href=str(payload.get("shell_brand_lockup_href", "")).strip(),
        shell_brand_icon_href=str(payload.get("shell_brand_icon_href", "")).strip(),
        style_css=tooling_dashboard_frontend_contract.load_tooling_shell_style_css(),
        welcome_html=welcome_html,
        maintainer_notes_html=maintainer_notes_html,
        cheatsheet_html=cheatsheet_html,
        payload_json=payload_json,
        control_script=tooling_dashboard_frontend_contract.load_tooling_shell_control_js(),
    )
