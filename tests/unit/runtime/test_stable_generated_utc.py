from __future__ import annotations

import json
from pathlib import Path
import re

from odylith.runtime.common import stable_generated_utc


_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}Z$")


def test_resolve_for_json_file_reuses_previous_timestamp_when_payload_unchanged(tmp_path: Path) -> None:
    target = tmp_path / "payload.json"
    target.write_text(
        json.dumps({"generated_utc": "2026-03-01 00:00:00Z", "value": 7}, indent=2) + "\n",
        encoding="utf-8",
    )

    resolved = stable_generated_utc.resolve_for_json_file(
        output_path=target,
        payload={"value": 7},
    )
    assert resolved == "2026-03-01 00:00:00Z"


def test_resolve_for_json_file_rotates_timestamp_when_payload_changes(tmp_path: Path) -> None:
    target = tmp_path / "payload.json"
    target.write_text(
        json.dumps({"generated_utc": "2026-03-01 00:00:00Z", "value": 7}, indent=2) + "\n",
        encoding="utf-8",
    )

    resolved = stable_generated_utc.resolve_for_json_file(
        output_path=target,
        payload={"value": 8},
    )
    assert _UTC_PATTERN.match(resolved)
    assert resolved != "2026-03-01 00:00:00Z"


def test_resolve_for_embedded_json_html_reuses_previous_timestamp_when_payload_unchanged(
    tmp_path: Path,
) -> None:
    target = tmp_path / "index.html"
    target.write_text(
        (
            '<script id="catalogData" type="application/json">{\n'
            '  "generated_utc": "2026-03-01 00:00:00Z",\n'
            '  "value": 7\n'
            "}</script>\n"
        ),
        encoding="utf-8",
    )

    resolved = stable_generated_utc.resolve_for_embedded_json_html(
        html_path=target,
        script_id="catalogData",
        payload={"value": 7},
    )
    assert resolved == "2026-03-01 00:00:00Z"


def test_resolve_for_embedded_json_html_rotates_when_payload_changes(tmp_path: Path) -> None:
    target = tmp_path / "index.html"
    target.write_text(
        (
            '<script id="catalogData" type="application/json">{\n'
            '  "generated_utc": "2026-03-01 00:00:00Z",\n'
            '  "value": 7\n'
            "}</script>\n"
        ),
        encoding="utf-8",
    )

    resolved = stable_generated_utc.resolve_for_embedded_json_html(
        html_path=target,
        script_id="catalogData",
        payload={"value": 8},
    )
    assert _UTC_PATTERN.match(resolved)
    assert resolved != "2026-03-01 00:00:00Z"
