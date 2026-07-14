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

from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import materialize_prompt_intent_hypothesis
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import render_product_intent_preview
from odylith.runtime.domain_intelligence.greenfield_cli_output import print_apply_result
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import GreenfieldPostConfirmEngineError
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import POST_CONFIRM_REPAIR_TIERS
from odylith.runtime.project_intelligence.intent_confirmation import format_confirmation_choice_lines


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith greenfield",
        description="Preview and commit confirmation-gated greenfield product records.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    propose = subparsers.add_parser("propose", help="Preview a confirmation-gated greenfield product proposal.")
    propose.add_argument("--repo-root", default=".")
    propose.add_argument("--prompt", required=True)
    propose.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    propose.add_argument(
        "--edit",
        default="",
        help="New product evidence after EDIT. It rebuilds a staged transaction and never writes governed records.",
    )
    propose.add_argument(
        "--edit-evidence",
        default="",
        help="Path to Markdown or text edit evidence. The contents are untrusted evidence, not product truth.",
    )
    propose.add_argument(
        "--detail",
        choices=("brief", "full"),
        default="brief",
        help="Reserved preview depth selector. `propose` always compiles the full staged transaction before the final rail.",
    )
    propose.add_argument(
        "--confirm-intent",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    propose.add_argument(
        "--intent-file",
        "--confirmed-intent-file",
        default="",
        dest="intent_file",
        help=argparse.SUPPRESS,
    )
    apply = subparsers.add_parser(
        "apply",
        help="Legacy proposal apply is disabled; use propose, then hash-bound create.",
        description="Legacy proposal apply is disabled; use propose, then hash-bound create.",
    )
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
        help="Compile a no-write ProductCreateTransaction for controlled tooling; normal product flow uses propose.",
    )
    compile_transaction.add_argument("--repo-root", default=".")
    compile_transaction.add_argument("--prompt", required=True)
    compile_transaction.add_argument("--edit", default="", help=argparse.SUPPRESS)
    compile_transaction.add_argument("--edit-evidence", default="", help=argparse.SUPPRESS)
    compile_transaction.add_argument(
        "--intent-file",
        "--confirmed-intent-file",
        default="",
        dest="intent_file",
        help=argparse.SUPPRESS,
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


def _legacy_apply_disabled_error() -> str:
    return (
        "greenfield apply is disabled for confirmed writes. Confirm now commits only an already compiled "
        "ProductCreateTransaction. Run `odylith greenfield propose --repo-root . --prompt <request>`, then run `odylith greenfield create "
        "--repo-root . --transaction-file .odylith/runtime/greenfield/product-create-transaction.v1.json "
        "--transaction-hash <hash> --confirm`. No governed records were written."
    )


def _transaction_confirmation_text(
    *,
    transaction: Any,
    output_path: str = "",
) -> str:
    summary = transaction.summary()
    manifest = transaction.quality_manifest if isinstance(transaction.quality_manifest, Mapping) else {}
    intent_authority = transaction.intent_authority if isinstance(transaction.intent_authority, Mapping) else {}
    package = transaction.prewrite_package
    backlog_result = package.backlog_result if isinstance(package.backlog_result, Mapping) else {}
    created = backlog_result.get("created") if isinstance(backlog_result.get("created"), list) else []
    components = package.component_registry_preview if isinstance(package.component_registry_preview, tuple) else ()
    diagrams = package.rendered_atlas_sources if isinstance(package.rendered_atlas_sources, Mapping) else {}
    transaction_ref = output_path or "<compiled-transaction.json>"
    lines = [
        "ProductCreateTransaction ready for final command",
        f"- transaction hash: {summary['transaction_hash']}",
        f"- product facts hash: {intent_authority.get('product_facts_sha256', '')}",
        f"- quality gate: {summary.get('quality_status') or manifest.get('status', 'unknown')}",
        f"- validation gate: {summary.get('validation_status') or manifest.get('validation_status', 'unknown')}",
        f"- governed package: {len(created)} workstreams, {len(components)} component previews, {len(diagrams)} Atlas previews",
        f"- sealed commit: {summary.get('repository_write_count', 0)} exact file writes, "
        f"{summary.get('repository_delete_count', 0)} deletions, and hashed repo preconditions",
        "- commands: CONFIRM commits this transaction hash; EDIT rebuilds from new evidence; REJECT stops with no writes",
        "",
        *format_confirmation_choice_lines(
            (
                (
                    "CONFIRM",
                    "Commit this exact validated package now. Odylith verifies the hash and repo preconditions, writes the sealed bytes, and validates readback with "
                    f"`odylith greenfield create --repo-root . --transaction-file {transaction_ref} "
                    f"--transaction-hash {summary['transaction_hash']} --confirm`. "
                    "No product reinterpretation, repair, or generation runs after CONFIRM.",
                ),
                (
                    "EDIT",
                    "Do not commit. Put corrections after EDIT; Odylith treats them as new evidence, rebuilds the package, and uses the new hash.",
                ),
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
        if isinstance(exc, greenfield_create_commit.GreenfieldCreateCommitError):
            payload["commit_failure"] = exc.to_dict()
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(str(exc))


def _post_confirm_create_overrides(args: argparse.Namespace) -> list[str]:
    overrides: list[str] = []
    has_transaction_ref = bool(str(getattr(args, "transaction_file", "") or "").strip())
    if has_transaction_ref and str(getattr(args, "prompt", "") or "").strip():
        overrides.append("--prompt")
    if str(getattr(args, "release", "") or "").strip():
        overrides.append("--release")
    if str(getattr(args, "repair_tier", "") or "").strip():
        overrides.append("--repair-tier")
    return overrides


def _edit_evidence_from_args(args: argparse.Namespace, *, repo_root: Path) -> str:
    inline = str(getattr(args, "edit", "") or "").strip()
    evidence_file = str(getattr(args, "edit_evidence", "") or "").strip()
    if inline and evidence_file:
        raise ValueError("use either --edit or --edit-evidence, not both")
    if not evidence_file:
        return inline
    path = Path(evidence_file).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError("environment/IO failure while reading EDIT evidence") from exc


def _compile_prompt_evidence_transaction(
    *,
    repo_root: Path,
    prompt: str,
    edit_evidence: str,
    release_selector: str,
    repair_tier: str = "",
) -> tuple[dict[str, Any], Any, Path]:
    candidate_intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=repo_root,
        fallback_title=greenfield_proposals.intent_title(prompt),
        edit_evidence=edit_evidence,
    )
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=repo_root,
        prompt=prompt,
        confirmed_intent=candidate_intent,
        require_completion_ready=False,
    )
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=repo_root,
        proposal=proposal,
        release_selector=release_selector,
        proposal_ready=True,
        **({"repair_tier": repair_tier} if repair_tier else {}),
    )
    candidate_authority = candidate_intent.get("product_intent_authority")
    transaction_authority = transaction.intent_authority if isinstance(transaction.intent_authority, Mapping) else {}
    if not isinstance(candidate_authority, Mapping) or (
        str(candidate_authority.get("product_facts_sha256", "")).strip()
        != str(transaction_authority.get("product_facts_sha256", "")).strip()
    ):
        raise RuntimeError(
            "pre-confirm compiler produced a transaction whose product facts do not match the visible typed preview"
        )
    transaction_path = repo_root / ".odylith" / "runtime" / "greenfield" / "product-create-transaction.v1.json"
    greenfield_proposals.write_product_create_transaction_file(transaction_path, transaction)
    return candidate_intent, transaction, transaction_path


def _retired_intent_file_message() -> str:
    return (
        "The separate Product Intent confirmation flow is retired. `propose` now compiles the typed evidence and "
        "full ProductCreateTransaction before it shows the only CONFIRM rail. Use `--edit` or `--edit-evidence` "
        "to rebuild from corrections; edited Markdown is evidence, never a confirmed product source."
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    if args.command == "propose":
        if bool(args.confirm_intent) or str(args.intent_file or "").strip():
            _print_greenfield_error(ValueError(_retired_intent_file_message()), as_json=args.output_format == "json")
            return 2
        try:
            edit_evidence = _edit_evidence_from_args(args, repo_root=repo_root)
            candidate_intent, transaction, transaction_path = _compile_prompt_evidence_transaction(
                repo_root=repo_root,
                prompt=str(args.prompt),
                release_selector="",
                edit_evidence=edit_evidence,
            )
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        if args.output_format == "json":
            print(json.dumps({
                "mode": "product_create_transaction",
                "intent_hypothesis": candidate_intent,
                "product_create_transaction": transaction.summary(),
                "transaction_file": str(transaction_path),
            }, indent=2, sort_keys=True))
        else:
            preview = render_product_intent_preview(candidate_intent).rstrip()
            print(f"{preview}\n\n{_transaction_confirmation_text(transaction=transaction, output_path=str(transaction_path))}", end="")
        return 0
    if args.command == "apply":
        message = _legacy_apply_disabled_error()
        if args.as_json:
            print(json.dumps({"mode": "error", "error": message}, indent=2, sort_keys=True))
        else:
            print(message)
        return 2
    if args.command == "compile-transaction":
        if str(args.intent_file or "").strip():
            _print_greenfield_error(ValueError(_retired_intent_file_message()), as_json=args.output_format == "json")
            return 2
        try:
            edit_evidence = _edit_evidence_from_args(args, repo_root=repo_root)
            candidate_intent, transaction, staged_path = _compile_prompt_evidence_transaction(
                repo_root=repo_root,
                prompt=str(args.prompt),
                release_selector=str(args.release),
                edit_evidence=edit_evidence,
                repair_tier=str(args.repair_tier),
            )
            output_path = str(args.output or "").strip()
            if output_path:
                path = Path(output_path).expanduser()
                if not path.is_absolute():
                    path = repo_root / path
                greenfield_proposals.write_product_create_transaction_file(path, transaction)
                output_path = str(path)
            else:
                output_path = str(staged_path)
            if args.output_format == "json":
                summary = transaction.summary()
                transaction_ref = output_path or "<compiled-transaction.json>"
                commit_command = (
                    "odylith greenfield create --repo-root . "
                    f"--transaction-file {transaction_ref} "
                    f"--transaction-hash {summary['transaction_hash']} --confirm"
                )
                payload = {
                    "mode": "product_create_transaction",
                    "intent_hypothesis": candidate_intent,
                    "product_create_transaction": summary,
                    "transaction": greenfield_proposals.product_create_transaction_to_dict(transaction),
                    "confirmation": {
                        "command_rule": "Start your reply with exactly one command: CONFIRM, EDIT, or REJECT.",
                        "first_word_rule": "Only the first command counts. Do not paste Odylith system commands in your reply.",
                        "edit_rule": "For EDIT, put corrections after the command so Odylith can rebuild from the new evidence.",
                        "post_confirm_contract": (
                            "CONFIRM commits only this hash-bound transaction; post-confirm create verifies the hash, "
                            "compiler receipt, and repo preconditions, writes only sealed bytes under the rollback "
                            "guard, validates readback, and reports success or environment/IO failure."
                        ),
                        "choices": [
                            {
                                "command": "CONFIRM",
                                "description": "Commit this exact validated package now.",
                                "commit_command": commit_command,
                            },
                            {
                                "command": "EDIT",
                                "description": "Do not commit. Put corrections after EDIT; Odylith treats them as new evidence, rebuilds the package, and uses the new hash.",
                            },
                            {
                                "command": "REJECT",
                                "description": "Stop. No governed records are written.",
                            },
                        ],
                        "confirm": "CONFIRM - commit this exact validated package now",
                        "edit": "EDIT - add corrections after the command and rebuild the transaction",
                        "reject": "REJECT - stop with no governed records written",
                    },
                }
                if output_path:
                    payload["transaction_file"] = output_path
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                preview = render_product_intent_preview(candidate_intent).rstrip()
                print(f"{preview}\n\n{_transaction_confirmation_text(transaction=transaction, output_path=output_path)}", end="")
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        return 0
    if args.command == "create":
        if not bool(args.confirm):
            message = (
                "greenfield create requires --confirm after the compiled ProductCreateTransaction is accepted. "
                "Run `odylith greenfield propose --repo-root . --prompt "
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
                    "Run `odylith greenfield propose --repo-root . --prompt "
                    + json.dumps(greenfield_proposals.prompt_text(str(args.prompt)))
                    + "` first, "
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
                    "greenfield create requires --transaction-file with --transaction-hash. "
                    "Run `odylith greenfield propose --repo-root . --prompt "
                    + json.dumps(greenfield_proposals.prompt_text(str(args.prompt)))
                    + "` first; "
                    "post-confirm create only commits an already compiled ProductCreateTransaction."
                )
            result, captured = _run_with_optional_stdout_capture(
                enabled=bool(args.as_json),
                action=lambda: greenfield_create_commit.commit_greenfield_create_transaction(
                    repo_root=repo_root,
                    transaction=transaction,
                    confirm=True,
                )
            )
        except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=bool(args.as_json))
            return 2
        if args.as_json:
            result = _with_operator_output(result, captured)
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print_apply_result(result, verb="create")
        return 0
    return 2
