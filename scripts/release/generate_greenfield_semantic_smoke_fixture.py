"""Regenerate the current source-controlled Greenfield semantic smoke packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_intent_packet,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet = semantic_intent_packet()
    payload = {
        "case_id": "claim-desk-semantic-smoke",
        "platform_custody_sentinels": _platform_custody_sentinels(packet),
        "prompt": SEMANTIC_PROMPT,
        "packet": packet,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


def _platform_custody_sentinels(packet: dict[str, object]) -> list[str]:
    """Bind platform-leakage sentinels to the sealed semantic smoke packet."""

    intent = packet["semantic_intent"]
    if not isinstance(intent, dict):
        raise RuntimeError("semantic smoke packet lacks Semantic Intent")
    presentation = intent["presentation"]
    facts = intent["facts"]
    if not isinstance(presentation, dict) or not isinstance(facts, list):
        raise RuntimeError("semantic smoke packet is structurally invalid")

    def label(kind: str) -> str:
        for fact in facts:
            if isinstance(fact, dict) and fact.get("kind") == kind:
                value = str(fact.get("label") or "").strip()
                if value:
                    return value
        raise RuntimeError(f"semantic smoke packet lacks {kind} custody")

    title = str(presentation.get("title") or "").strip()
    if not title:
        raise RuntimeError("semantic smoke packet lacks presentation title custody")
    return [title, label("actor"), label("external_system")]


if __name__ == "__main__":
    raise SystemExit(main())
