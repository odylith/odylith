"""Minimal command adapter for commit-only Greenfield create transactions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence.greenfield_commit_transaction import load_sealed_product_create_commit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="odylith greenfield create")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--transaction-file", required=True)
    parser.add_argument("--transaction-hash", required=True)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(_create_arguments(argv))
    if not args.confirm:
        return _error(
            "greenfield create requires --confirm after the compiled ProductCreateTransaction is accepted. "
            "CONFIRM commits the exact validated package; EDIT rebuilds it from new evidence; REJECT writes nothing.",
            as_json=args.as_json,
        )
    root = Path(args.repo_root).expanduser().resolve()
    path = Path(args.transaction_file).expanduser()
    if not path.is_absolute():
        path = root / path
    try:
        transaction = load_sealed_product_create_commit(path)
        if args.transaction_hash != transaction.transaction_hash:
            raise ValueError("ProductCreateTransaction hash does not match --transaction-hash")
        result = greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=root,
            transaction=transaction,
            confirm=True,
        )
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as error:
        return _error(str(error), as_json=args.as_json, error=error)
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Odylith committed the validated Greenfield package.")
        print(f"- transaction hash: {transaction.transaction_hash}")
        print(f"- sealed writes: {transaction.summary()['repository_write_count']}")
        print("- readback: passed")
    return 0


def _create_arguments(argv: Sequence[str] | None) -> list[str]:
    tokens = [str(token) for token in (argv or ())]
    return tokens[1:] if tokens[:1] == ["create"] else tokens


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
