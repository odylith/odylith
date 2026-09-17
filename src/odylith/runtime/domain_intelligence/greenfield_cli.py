"""Greenfield command routing and explicit terminal decisions, without model imports."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import shlex
import time
from typing import Any


COMMANDS = (
    ("propose", "Compile and review a complete Greenfield package before confirmation."),
    ("decide", "Confirm, edit or reject one reviewed package in the terminal."),
    ("apply", "Disabled legacy command; use propose to review a package."),
    ("create", "Commit a compiled ProductCreateTransaction."),
    ("compile-transaction", "Compile and quality-gate a ProductCreateTransaction without governed writes."),
)
COMMAND_NAMES = frozenset(command for command, _help_text in COMMANDS)


def terminal_decision_offer(*, repo_root: Path, transaction_hash: str) -> dict[str, Any]:
    """Offer operator process invocation, never unqualified ordinary-chat approval."""
    prefix = ["odylith", "greenfield", "decide", "--repo-root", str(repo_root)]
    return {
        "status": "terminal_only",
        "interface": "terminal",
        "reason": (
            "Nothing has been published. Run one command in a terminal; ordinary chat approval "
            "does not authorize publication. For EDIT, replace <corrections> with your changes."
        ),
        "choices": [
            {
                "label": command,
                "command": shlex.join([
                    *prefix, command, transaction_hash,
                    *(["--edit", "<corrections>"] if command == "EDIT" else []),
                ]),
            }
            for command in ("CONFIRM", "EDIT", "REJECT")
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    started_at = time.perf_counter()
    tokens = list(argv or ())
    if tokens[:1] == ["create"]:
        from odylith.runtime.domain_intelligence.greenfield_create_cli import main as create_main

        return create_main(tokens[1:])
    if tokens[:1] != ["decide"]:
        from odylith.runtime.domain_intelligence.greenfield_proposals_cli import main as proposal_main

        return proposal_main(tokens)

    parser = argparse.ArgumentParser(prog="odylith greenfield decide", allow_abbrev=False)
    parser.add_argument("command", choices=("CONFIRM", "EDIT", "REJECT"))
    parser.add_argument("transaction_hash")
    parser.add_argument("--repo-root", default=".")
    evidence = parser.add_mutually_exclusive_group()
    evidence.add_argument("--edit")
    evidence.add_argument("--edit-evidence")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(tokens[1:])
    if len(args.transaction_hash) != 64 or not set(args.transaction_hash) <= set("0123456789abcdef"):
        parser.error("use the exact 64-character approval hash from the reviewed package")
    if args.command != "EDIT" and (args.edit is not None or args.edit_evidence is not None):
        parser.error("correction evidence is accepted only with EDIT")
    args.edit = args.edit or ""
    args.edit_evidence = args.edit_evidence or ""
    root = Path(args.repo_root).expanduser().resolve()

    if args.command == "EDIT" and (args.edit.strip() or args.edit_evidence.strip()):
        from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store

        try:
            greenfield_pending_transaction_store.resolve_pending_transaction(
                repo_root=root, transaction_hash=args.transaction_hash,
            )
        except (OSError, RuntimeError, ValueError) as error:
            message = f"This reviewed package is unavailable: {error}. No governed records were written."
            print(json.dumps({"status": "STALE_TRANSACTION", "error": message}) if args.as_json else message)
            return 2
        from odylith.runtime.domain_intelligence.greenfield_proposals_cli import rebuild_pending_transaction

        return rebuild_pending_transaction(
            repo_root=root, transaction_hash=args.transaction_hash,
            edit_evidence=args.edit, edit_evidence_file=args.edit_evidence,
            as_json=args.as_json, started_at=started_at,
        )

    from odylith.runtime.surfaces.greenfield_host_confirmation import handle_greenfield_decision

    decision = handle_greenfield_decision(
        repo_root=root, command=args.command, transaction_hash=args.transaction_hash, edit_evidence=None,
    )
    if decision["status"] == "edit_evidence_required":
        decision["visible_markdown"] = (
            "**What would you like to change?**\n\n"
            "Run EDIT with --edit '<corrections>' or --edit-evidence <file>. "
            "The existing package is unchanged; nothing has been published by this decision."
        )
    elif decision["status"] == "BUSY_NO_WRITE":
        choice = next(
            choice for choice in terminal_decision_offer(
                repo_root=root, transaction_hash=args.transaction_hash,
            )["choices"] if choice["label"] == args.command
        )
        decision["visible_markdown"] += f"\n\nRetry in a terminal:\n\n```sh\n{choice['command']}\n```"
    print(json.dumps(decision, indent=2, sort_keys=True) if args.as_json else decision["visible_markdown"])
    return 0 if decision["status"] in {"CLOSED", "ABORTED", "edit_evidence_required"} else 2
