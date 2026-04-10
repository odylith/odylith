"""Render the Compass shell from source-owned frontend assets."""

from __future__ import annotations

import json
from typing import Any

from odylith.runtime.surfaces import compass_dashboard_frontend_contract
from odylith.runtime.surfaces import dashboard_template_runtime


def _json_script_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False).replace("</", "<\\/")


def _render_shell_html(*, payload: dict[str, Any]) -> str:
    return dashboard_template_runtime.render_template(
        "compass_dashboard/page.html.j2",
        brand_head_html=str(payload.get("brand_head_html", "")).strip(),
        base_style_href=str(payload.get("base_style_href", "")).strip(),
        execution_wave_style_href=str(payload.get("execution_wave_style_href", "")).strip(),
        surface_style_href=str(payload.get("surface_style_href", "")).strip(),
        shared_js_href=str(payload.get("shared_js_href", "")).strip(),
        runtime_truth_js_href=str(payload.get("runtime_truth_js_href", "")).strip(),
        state_js_href=str(payload.get("state_js_href", "")).strip(),
        summary_js_href=str(payload.get("summary_js_href", "")).strip(),
        timeline_js_href=str(payload.get("timeline_js_href", "")).strip(),
        waves_js_href=str(payload.get("waves_js_href", "")).strip(),
        releases_js_href=str(payload.get("releases_js_href", "")).strip(),
        workstreams_js_href=str(payload.get("workstreams_js_href", "")).strip(),
        ui_runtime_js_href=str(payload.get("ui_runtime_js_href", "")).strip(),
        runtime_js_href=str(payload.get("runtime_js_href", "")).strip(),
        payload_json=_json_script_payload(payload),
        control_js=compass_dashboard_frontend_contract.load_compass_shell_control_js(),
    )
