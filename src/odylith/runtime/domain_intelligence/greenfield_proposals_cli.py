"""CLI adapter for confirmed greenfield proposal commands."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_cli_output import print_apply_result
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import GreenfieldPostConfirmEngineError
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import POST_CONFIRM_REPAIR_TIERS
from odylith.runtime.domain_intelligence.proposal_rendering import format_proposal_text
from odylith.runtime.project_intelligence.intent_confirmation import build_product_intent_confirmation
from odylith.runtime.project_intelligence.intent_confirmation import format_confirmation_choice_lines
from odylith.runtime.project_intelligence.intent_confirmation import format_product_intent_confirmation_text


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith greenfield",
        description="Preview and apply confirmation-gated greenfield product records.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    propose = subparsers.add_parser("propose", help="Preview a confirmation-gated greenfield product proposal.")
    propose.add_argument("--repo-root", default=".")
    propose.add_argument("--prompt", required=True)
    propose.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    propose.add_argument(
        "--detail",
        choices=("brief", "full"),
        default="brief",
        help="Text preview depth after intent is confirmed. Default propose shows only Product Intent Confirmation.",
    )
    propose.add_argument(
        "--confirm-intent",
        action="store_true",
        help="Build the full proposal preview or JSON after the operator confirms the Product Intent Confirmation.",
    )
    propose.add_argument(
        "--intent-file",
        "--confirmed-intent-file",
        default="",
        dest="intent_file",
        help="Markdown/text/JSON file containing the operator-confirmed Product Intent Confirmation.",
    )
    apply = subparsers.add_parser("apply", help="Apply a confirmed greenfield product proposal.")
    apply.add_argument("--repo-root", default=".")
    apply.add_argument("--proposal-file", default="")
    apply.add_argument("--proposal-json", default="")
    apply.add_argument("--confirm", action="store_true")
    apply.add_argument("--release", default="")
    apply.add_argument(
        "--repair-tier",
        choices=POST_CONFIRM_REPAIR_TIERS,
        default=greenfield_proposals.DEFAULT_POST_CONFIRM_REPAIR_TIER,
        help=(
            "Create-transaction compiler budget: auto keeps standard compilation under 60s and enters 90s "
            "rescue only for repairable semantic or quality gates; deep is explicit 120s premium/CI proof."
        ),
    )
    apply.add_argument("--json", action="store_true", dest="as_json")
    create = subparsers.add_parser("create", help="Commit a compiled ProductCreateTransaction.")
    create.add_argument("--repo-root", default=".")
    create.add_argument("--prompt", default="", help=argparse.SUPPRESS)
    create.add_argument(
        "--intent-file",
        "--confirmed-intent-file",
        default="",
        dest="intent_file",
        help=argparse.SUPPRESS,
    )
    create.add_argument(
        "--transaction-file",
        default="",
        help="JSON ProductCreateTransaction compiled before confirmation.",
    )
    create.add_argument(
        "--transaction-json",
        default="",
        help="Inline JSON ProductCreateTransaction compiled before confirmation.",
    )
    create.add_argument(
        "--transaction-hash",
        default="",
        help="Expected ProductCreateTransaction hash; required by confirmation UIs and checked before writes.",
    )
    create.add_argument("--confirm", action="store_true")
    create.add_argument("--release", default="", help=argparse.SUPPRESS)
    create.add_argument(
        "--repair-tier",
        default="",
        help=argparse.SUPPRESS,
    )
    create.add_argument("--json", action="store_true", dest="as_json")
    compile_transaction = subparsers.add_parser(
        "compile-transaction",
        help="Compile and quality-gate a ProductCreateTransaction without governed writes.",
    )
    compile_transaction.add_argument("--repo-root", default=".")
    compile_transaction.add_argument("--prompt", required=True)
    compile_transaction.add_argument(
        "--intent-file",
        "--confirmed-intent-file",
        default="",
        dest="intent_file",
        help="Markdown/text/JSON file containing the operator-confirmed Product Intent Confirmation.",
    )
    compile_transaction.add_argument("--release", default="")
    compile_transaction.add_argument(
        "--repair-tier",
        choices=POST_CONFIRM_REPAIR_TIERS,
        default=greenfield_proposals.DEFAULT_POST_CONFIRM_REPAIR_TIER,
        help=(
            "Create-transaction compiler budget: auto keeps standard compilation under 60s and enters 90s "
            "rescue only for repairable semantic or quality gates; deep is explicit 120s premium/CI proof."
        ),
    )
    compile_transaction.add_argument(
        "--output",
        default="",
        help="Optional path for the compiled transaction JSON. Omit to print only the confirmation view.",
    )
    compile_transaction.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    return parser.parse_args(argv)


def _run_with_optional_stdout_capture(
    *,
    enabled: bool,
    action: Callable[[], dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    if not enabled:
        return action(), []
    stdout_fd = 1
    try:
        probe_fd = os.dup(stdout_fd)
    except OSError:
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            result = action()
        return result, _captured_lines(captured_output.getvalue())
    else:
        os.close(probe_fd)
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as captured_output:
        sys.stdout.flush()
        saved_fd = os.dup(stdout_fd)
        try:
            os.dup2(captured_output.fileno(), stdout_fd)
            with contextlib.redirect_stdout(captured_output):
                result = action()
                captured_output.flush()
        finally:
            os.dup2(saved_fd, stdout_fd)
            os.close(saved_fd)
        captured_output.seek(0)
        return result, _captured_lines(captured_output.read())


def _captured_lines(text: str) -> list[str]:
    return [line.rstrip() for line in str(text or "").splitlines() if line.strip()]


def _with_operator_output(result: Mapping[str, Any], captured: Sequence[str]) -> dict[str, Any]:
    payload = dict(result)
    if captured:
        payload["operator_output"] = list(captured)
    return payload


def _transaction_confirmation_text(
    *,
    transaction: Any,
    output_path: str = "",
) -> str:
    summary = transaction.summary()
    manifest = transaction.quality_manifest if isinstance(transaction.quality_manifest, Mapping) else {}
    package = transaction.prewrite_package
    backlog_result = package.backlog_result if isinstance(package.backlog_result, Mapping) else {}
    created = backlog_result.get("created") if isinstance(backlog_result.get("created"), list) else []
    components = package.component_registry_preview if isinstance(package.component_registry_preview, tuple) else ()
    diagrams = package.rendered_atlas_sources if isinstance(package.rendered_atlas_sources, Mapping) else {}
    transaction_ref = output_path or "<compiled-transaction.json>"
    lines = [
        "ProductCreateTransaction ready for final command",
        f"- transaction hash: {summary['transaction_hash']}",
        f"- quality gate: {summary.get('quality_status') or manifest.get('status', 'unknown')}",
        f"- validation gate: {summary.get('validation_status') or manifest.get('validation_status', 'unknown')}",
        f"- governed package: {len(created)} workstreams, {len(components)} component previews, {len(diagrams)} Atlas previews",
        "- command rule: choose exactly one of CONFIRM, EDIT, or REJECT",
        "",
        *format_confirmation_choice_lines(
            (
                (
                    "CONFIRM",
                    "Commit this exact validated package now. Odylith verifies the hash and writes the transaction atomically with "
                    f"`odylith greenfield create --repo-root . --transaction-file {transaction_ref} "
                    f"--transaction-hash {summary['transaction_hash']} --confirm`.",
                ),
                ("EDIT", "Do not commit. Treat edits as new evidence, rebuild the package, and use the new hash."),
                ("REJECT", "Stop. No governed records are written."),
            )
        ),
    ]
    if output_path:
        lines.insert(1, f"- transaction file: {output_path}")
    return "\n".join(lines).rstrip() + "\n"


def _print_greenfield_error(exc: Exception, *, as_json: bool) -> None:
    if as_json:
        payload: dict[str, Any] = {"mode": "error", "error": str(exc)}
        if isinstance(exc, GreenfieldPostConfirmEngineError):
            payload["post_confirm_quality_manifest"] = exc.manifest
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(str(exc))


def _post_confirm_create_overrides(args: argparse.Namespace) -> list[str]:
    overrides: list[str] = []
    has_transaction_ref = bool(
        str(getattr(args, "transaction_file", "") or "").strip()
        or str(getattr(args, "transaction_json", "") or "").strip()
    )
    if has_transaction_ref and str(getattr(args, "prompt", "") or "").strip():
        overrides.append("--prompt")
    if str(getattr(args, "release", "") or "").strip():
        overrides.append("--release")
    if str(getattr(args, "repair_tier", "") or "").strip():
        overrides.append("--repair-tier")
    return overrides


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    if args.command == "propose":
        if not bool(args.confirm_intent):
            confirmation = build_product_intent_confirmation(
                prompt=str(args.prompt),
                title=greenfield_proposals.intent_title(str(args.prompt)),
                repo_name=repo_root.name,
                observed_source=greenfield_proposals.source_evidence(repo_root),
            )
            if args.output_format == "json":
                print(json.dumps(confirmation, indent=2, sort_keys=True))
            else:
                print(format_product_intent_confirmation_text(confirmation), end="")
            return 0
        try:
            confirmed_intent = greenfield_proposals.load_confirmed_intent_args(args, repo_root=repo_root)
            proposal = greenfield_proposals.build_greenfield_proposal(
                repo_root=repo_root,
                prompt=str(args.prompt),
                confirmed_intent=confirmed_intent,
            )
        except (ValueError, RuntimeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        if args.output_format == "json":
            print(json.dumps(proposal, indent=2, sort_keys=True))
        else:
            print(format_proposal_text(proposal, detail=str(args.detail)), end="")
        return 0
    if args.command == "apply":
        try:
            proposal = greenfield_proposals.load_proposal(args)
            result, captured = _run_with_optional_stdout_capture(
                enabled=bool(args.as_json),
                action=lambda: greenfield_proposals.apply_greenfield_proposal(
                    repo_root=repo_root,
                    proposal=proposal,
                    confirm=bool(args.confirm),
                    release_selector=str(args.release),
                    repair_tier=str(args.repair_tier),
                ),
            )
        except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=bool(args.as_json))
            return 2
        if args.as_json:
            result = _with_operator_output(result, captured)
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print_apply_result(result, verb="apply")
        return 0
    if args.command == "compile-transaction":
        try:
            confirmed_intent = greenfield_proposals.load_confirmed_intent_args(args, repo_root=repo_root)
            proposal = greenfield_proposals.build_greenfield_proposal(
                repo_root=repo_root,
                prompt=str(args.prompt),
                release_selector=str(args.release),
                confirmed_intent=confirmed_intent,
                require_completion_ready=False,
            )
            result, captured = _run_with_optional_stdout_capture(
                enabled=args.output_format == "json",
                action=lambda: {
                    "transaction": greenfield_proposals.compile_greenfield_create_transaction(
                        repo_root=repo_root,
                        proposal=proposal,
                        release_selector=str(args.release),
                        proposal_ready=True,
                        repair_tier=str(args.repair_tier),
                    )
                },
            )
            transaction = result["transaction"]
            output_path = str(args.output or "").strip()
            if output_path:
                path = Path(output_path).expanduser()
                if not path.is_absolute():
                    path = repo_root / path
                greenfield_proposals.write_product_create_transaction_file(path, transaction)
                output_path = str(path)
            if args.output_format == "json":
                payload = {
                    "mode": "product_create_transaction",
                    "product_create_transaction": transaction.summary(),
                    "transaction": greenfield_proposals.product_create_transaction_to_dict(transaction),
                    "confirmation": {
                        "confirm": "commit this validated package",
                        "edit": "treat edits as new evidence and rebuild the transaction",
                        "reject": "stop with no governed records written",
                    },
                }
                if output_path:
                    payload["transaction_file"] = output_path
                payload = _with_operator_output(payload, captured)
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(_transaction_confirmation_text(transaction=transaction, output_path=output_path), end="")
        except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        return 0
    if args.command == "create":
        if not bool(args.confirm):
            message = (
                "greenfield create requires --confirm after the Product Intent Confirmation is accepted. "
                "Run `odylith greenfield compile-transaction --repo-root . --prompt "
                + json.dumps(greenfield_proposals.prompt_text(str(args.prompt)))
                + "` first, then rerun create with --transaction-file, --transaction-hash, and --confirm "
                "when the validated package is correct."
            )
            if args.as_json:
                print(json.dumps({"mode": "error", "error": message}, indent=2, sort_keys=True))
            else:
                print(message)
            return 2
        try:
            if str(getattr(args, "intent_file", "") or "").strip():
                raise ValueError(
                    "greenfield create no longer accepts --intent-file. "
                    "Run `odylith greenfield compile-transaction --repo-root . --prompt "
                    + json.dumps(greenfield_proposals.prompt_text(str(args.prompt)))
                    + " --intent-file .odylith/runtime/greenfield/confirmed-intent.md "
                    "--output .odylith/runtime/greenfield/product-create-transaction.v1.json` first, "
                    "then run create with --transaction-file, --transaction-hash, and --confirm."
                )
            post_confirm_overrides = _post_confirm_create_overrides(args)
            if post_confirm_overrides:
                raise ValueError(
                    "greenfield create cannot accept post-confirm inputs: "
                    + ", ".join(post_confirm_overrides)
                    + ". Edit the Product Intent evidence and rebuild the ProductCreateTransaction; "
                    "create only verifies the hash and commits the compiled package."
                )
            transaction = greenfield_proposals.load_product_create_transaction_args(args, repo_root=repo_root)
            if transaction is None:
                raise ValueError(
                    "greenfield create requires --transaction-file or --transaction-json with --transaction-hash. "
                    "Run `odylith greenfield compile-transaction --repo-root . --prompt "
                    + json.dumps(greenfield_proposals.prompt_text(str(args.prompt)))
                    + " --intent-file .odylith/runtime/greenfield/confirmed-intent.md "
                    "--output .odylith/runtime/greenfield/product-create-transaction.v1.json` first; "
                    "post-confirm create only commits an already compiled ProductCreateTransaction."
                )
            result, captured = _run_with_optional_stdout_capture(
                enabled=bool(args.as_json),
                action=lambda: greenfield_proposals.commit_greenfield_create_transaction(
                    repo_root=repo_root,
                    transaction=transaction,
                    confirm=True,
                )
            )
        except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=bool(args.as_json))
            return 2
        if args.as_json:
            result = _with_operator_output(result, captured)
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print_apply_result(result, verb="create")
        return 0
    return 2
