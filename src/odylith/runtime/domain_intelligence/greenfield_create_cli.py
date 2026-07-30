"""Minimal command adapter for commit-only Greenfield create transactions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from odylith.runtime.domain_intelligence import greenfield_create_commit


_POST_CONFIRM_NAVIGATION = {
    "project": "odylith/index.html?tab=project",
    "radar": "odylith/index.html?tab=radar",
    "registry": "odylith/index.html?tab=registry",
    "atlas": "odylith/index.html?tab=atlas",
    "compass": "odylith/index.html?tab=compass&date=live",
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="odylith greenfield create")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--transaction-file", default="")
    parser.add_argument("--transaction-hash", default="")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--prompt", default="", help=argparse.SUPPRESS)
    parser.add_argument("--intent-file", "--confirmed-intent-file", default="", dest="intent_file", help=argparse.SUPPRESS)
    parser.add_argument("--release", default="", help=argparse.SUPPRESS)
    parser.add_argument("--repair-tier", default="", help=argparse.SUPPRESS)
    args, unknown = parser.parse_known_args(_create_arguments(argv))
    if not args.confirm:
        return _error(
            "greenfield create requires --confirm after the compiled ProductCreateTransaction is accepted. "
            "CONFIRM commits the exact validated package; EDIT rebuilds it from new evidence; REJECT writes nothing.",
            as_json=args.as_json,
        )
    if str(args.intent_file or "").strip():
        return _error(
            "greenfield create no longer accepts --intent-file. Run `odylith greenfield propose --repo-root . --prompt <request>` first, "
            "then run create with --transaction-file, --transaction-hash, and --confirm.",
            as_json=args.as_json,
        )
    overrides = _create_input_overrides(args, unknown)
    if overrides:
        return _error(
            "greenfield create accepts only --transaction-file, --transaction-hash, and --confirm; unexpected options: "
            + ", ".join(overrides)
            + ". Use EDIT to add evidence and rebuild the ProductCreateTransaction; create only verifies the hash and commits the compiled package.",
            as_json=args.as_json,
        )
    if not str(args.transaction_file or "").strip():
        return _error(
            "greenfield create requires --transaction-file. "
            "Run `odylith greenfield propose --repo-root . --prompt <request>` first; "
            "commit-only create only commits an already compiled ProductCreateTransaction.",
            as_json=args.as_json,
        )
    if not str(args.transaction_hash or "").strip():
        return _error(
            "greenfield create requires --transaction-hash for the compiled ProductCreateTransaction. "
            "Use the hash shown by the CONFIRM rail; EDIT rebuilds the package with a new hash.",
            as_json=args.as_json,
        )
    root = Path(args.repo_root).expanduser().resolve()
    path = Path(args.transaction_file).expanduser()
    if not path.is_absolute():
        path = root / path
    try:
        result = greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=root,
            transaction_file=path,
            transaction_hash=args.transaction_hash,
            confirm=True,
        )
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as error:
        return _error(str(error), as_json=args.as_json, error=error)
    navigation = _post_confirm_navigation()
    if args.as_json:
        response = dict(result)
        response["post_confirm_navigation"] = navigation
        print(json.dumps(response, indent=2, sort_keys=True))
    else:
        summary = dict(result.get("product_create_transaction") or {})
        print("Odylith committed the validated Greenfield package.")
        print(f"- transaction hash: {args.transaction_hash}")
        print(f"- quality gate: {summary['quality_status']}")
        print(f"- validation gate: {summary['validation_status']}")
        print(f"- sealed writes: {summary['repository_write_count']}")
        print("- readback: passed")
        _print_post_confirm_navigation(navigation)
    return 0


def _post_confirm_navigation() -> dict[str, str]:
    """Return the stable, host-agnostic route contract after a confirmed create."""

    return dict(_POST_CONFIRM_NAVIGATION)


def _print_post_confirm_navigation(navigation: dict[str, str]) -> None:
    print("")
    print("Open the generated governance workspace:")
    print(f"- Project: `{navigation['project']}`")
    print(f"- Radar: `{navigation['radar']}`")
    print(f"- Registry: `{navigation['registry']}`")
    print(f"- Atlas: `{navigation['atlas']}`")
    print(f"- Compass: `{navigation['compass']}`")
    print(
        "Next: Review the committed governance package before beginning implementation; "
        "no application code has been built."
    )


def _create_arguments(argv: Sequence[str] | None) -> list[str]:
    tokens = [str(token) for token in (argv or ())]
    return tokens[1:] if tokens[:1] == ["create"] else tokens


def _create_input_overrides(args: argparse.Namespace, unknown: Sequence[str]) -> list[str]:
    overrides: list[str] = []
    if str(args.prompt or "").strip():
        overrides.append("--prompt")
    if str(args.release or "").strip():
        overrides.append("--release")
    if str(args.repair_tier or "").strip():
        overrides.append("--repair-tier")
    overrides.extend(token for token in unknown if token.startswith("-"))
    if unknown and not overrides:
        overrides.append("unsupported arguments")
    return overrides


def _error(message: str, *, as_json: bool, error: Exception | None = None) -> int:
    if as_json:
        payload: dict[str, object] = {"mode": "error", "error": message}
        if isinstance(error, greenfield_create_commit.GreenfieldCreateCommitError):
            payload["commit_failure"] = error.to_dict()
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(message)
    return 2


__all__ = ["main"]
