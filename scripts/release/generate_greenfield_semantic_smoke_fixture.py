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
    payload = {
        "case_id": "claim-desk-semantic-smoke",
        "prompt": SEMANTIC_PROMPT,
        "packet": semantic_intent_packet(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
