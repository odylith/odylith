from __future__ import annotations

import ast
from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_confirmation_rail import (
    format_confirmation_choice_lines,
)
from odylith.runtime.domain_intelligence.greenfield_proposals_cli import _parse_args


def test_hash_bound_confirmation_rail_is_graph_native() -> None:
    assert format_confirmation_choice_lines(
        (
            ("CONFIRM abc123", "Commit the sealed bytes."),
            ("EDIT abc123 <corrections>", "Rebuild from new evidence."),
            ("REJECT abc123", "Write nothing."),
        )
    ) == [
        "## Choose one command",
        "",
        "Use one complete command below. Copy CONFIRM or REJECT exactly. For EDIT, replace `<corrections>` with "
        "your changes. The approval code binds your choice to this reviewed package.",
        "",
        "### CONFIRM",
        "```text\nCONFIRM abc123\n```",
        "Commit the sealed bytes.",
        "",
        "### EDIT",
        "```text\nEDIT abc123 <corrections>\n```",
        "Rebuild from new evidence.",
        "",
        "### REJECT",
        "```text\nREJECT abc123\n```",
        "Write nothing.",
    ]


def test_public_greenfield_help_exposes_semantic_packet_entrypoints() -> None:
    assert _parse_args(["semantic-intent-schema"]).command == "semantic-intent-schema"
    assert _parse_args(["semantic-intent-request", "--prompt", "Build a product"]).command == (
        "semantic-intent-request"
    )
    parsed = _parse_args(
        [
            "propose",
            "--prompt",
            "Build a product",
            "--semantic-intent-file",
            "semantic-intent.json",
        ]
    )
    assert parsed.intent_file == "semantic-intent.json"


def test_public_entrypoint_imports_no_retired_prose_authority() -> None:
    source_path = Path(
        "src/odylith/runtime/domain_intelligence/greenfield_proposals_cli.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_modules = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }

    assert not any("greenfield_confirmed_" in module for module in imported_modules)
    assert not any("greenfield_first_path_" in module for module in imported_modules)
    assert "odylith.runtime.project_intelligence.intent_confirmation" not in imported_modules
