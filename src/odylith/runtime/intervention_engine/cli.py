"""CLI helpers for the Odylith intervention engine layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from odylith.runtime.intervention_engine import apply as proposal_apply
from odylith.runtime.intervention_engine import engine


def _payload_text(raw: str) -> str:
    if str(raw or "").strip():
        return str(raw)
    import sys

    return sys.stdin.read()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith governance",
        description="Build or apply Odylith observation and proposal payloads.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preview = subparsers.add_parser(
        "intervention-preview",
        help="Build one Odylith Observation and Proposal bundle from an observation envelope.",
    )
    preview.add_argument("--repo-root", default=".")
    preview.add_argument("--payload-json", default="", help="Observation envelope JSON. Defaults to stdin.")

    apply_parser = subparsers.add_parser("capture-apply", help="Apply or decline one Odylith Proposal payload.")
    apply_parser.add_argument("--repo-root", default=".")
    apply_parser.add_argument("--payload-json", default="", help="Proposal payload JSON. Defaults to stdin.")
    apply_parser.add_argument("--decline", action="store_true")

    args = parser.parse_args(list(argv or ()))
    if args.command == "intervention-preview":
        payload = json.loads(_payload_text(str(args.payload_json)) or "{}")
        if not isinstance(payload, dict):
            print("{}")
            return 2
        result = engine.build_intervention_bundle(
            repo_root=Path(args.repo_root).expanduser().resolve(),
            observation=payload,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    return proposal_apply.main(
        [
            "--repo-root",
            str(args.repo_root),
            "--payload-json",
            _payload_text(str(args.payload_json)),
            *(["--decline"] if bool(args.decline) else []),
        ]
    )
