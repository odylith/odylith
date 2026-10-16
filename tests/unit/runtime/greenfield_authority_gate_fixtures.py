"""Explicit authority decisions for tests whose subject is not gate semantics."""

from __future__ import annotations

import json
from pathlib import Path


def write_admitted_authority_gate(path: Path, *, source_quote: str) -> Path:
    """Write a source-bound gate fixture without asserting product meaning."""

    if not source_quote.strip():
        raise ValueError("authority gate fixture requires a nonempty source quote")
    path.write_text(json.dumps({
        "decision": "admit",
        "required_fields": [],
        "owner_quote": source_quote,
        "task_quote": source_quote,
        "result_quote": source_quote,
        "question": "",
    }), encoding="utf-8")
    return path
