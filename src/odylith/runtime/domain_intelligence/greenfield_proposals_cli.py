"""CLI adapter for confirmed greenfield proposal commands."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import shlex
from typing import Any, Mapping

from odylith.runtime.domain_intelligence.greenfield_create_contract import product_intent_authorities_match


_PUBLIC_INTENT_AUTHORITY_SUMMARY_VERSION = "odylith.product-intent-authority-summary.v1"
_PUBLIC_INTENT_AUTHORITY_SUMMARY_KEYS = (
    "product_facts_sha256",
    "source_format",
    "materiality_status",
)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith greenfield",
        description="Verify host-authored Semantic Intent and stage confirmation-gated product records.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    schema = subparsers.add_parser(
        "semantic-intent-schema",
        help="Print the exact host-authored Semantic Intent packet schema.",
    )
    schema.add_argument("--repo-root", default=".", help=argparse.SUPPRESS)
    authoring = subparsers.add_parser(
        "semantic-intent-request",
        help="Print exact evidence and the deterministic host authoring contract.",
    )
    authoring.add_argument("--repo-root", default=".")
    authoring.add_argument("--prompt", default="")
    authoring.add_argument("--edit", default="")
    authoring.add_argument("--edit-evidence", default="")
    authoring.add_argument("--supersedes-hash", default="")
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
        "--semantic-intent-file",
        default="",
        dest="intent_file",
        help="Source-cited Semantic Intent packet authored by the active host model.",
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
    apply.add_argument("--json", action="store_true", dest="as_json")
    compile_transaction = subparsers.add_parser(
        "compile-transaction",
        help="Compile a no-write ProductCreateTransaction for controlled tooling; normal product flow uses propose.",
    )
    compile_transaction.add_argument("--repo-root", default=".")
    compile_transaction.add_argument("--prompt", required=True)
    compile_transaction.add_argument("--edit", default="", help=argparse.SUPPRESS)
    compile_transaction.add_argument("--edit-evidence", default="", help=argparse.SUPPRESS)
    compile_transaction.add_argument(
        "--semantic-intent-file",
        default="",
        dest="intent_file",
        help="Source-cited Semantic Intent packet authored by the active host model.",
    )
    compile_transaction.add_argument("--release", default="")
    compile_transaction.add_argument(
        "--output",
        default="",
        help="Optional path for the compiled transaction JSON. Omit to print only the confirmation view.",
    )
    compile_transaction.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    return parser.parse_args(argv)


def _legacy_apply_disabled_error() -> str:
    return (
        "greenfield apply is disabled for confirmed writes. Confirm now commits only an already compiled "
        "ProductCreateTransaction. Run `odylith greenfield propose --repo-root . --prompt <request>`, then run `odylith greenfield create "
        "--repo-root . --transaction-file .odylith/runtime/greenfield/pending/<hash>/product-create-transaction.v1.json "
        "--transaction-hash <hash> --confirm`. No governed records were written."
    )


def _transaction_confirmation_payload(
    *,
    transaction: Any,
    output_path: str = "",
) -> dict[str, Any]:
    summary = transaction.summary()
    transaction_hash = str(summary["transaction_hash"])
    transaction_ref = shlex.quote(output_path or "<compiled-transaction.json>")
    commit_command = (
        "odylith greenfield create --repo-root . "
        f"--transaction-file {transaction_ref} "
        f"--transaction-hash {summary['transaction_hash']} --confirm"
    )
    return {
        "command_rule": "Use exactly one hash-bound command: CONFIRM, EDIT, or REJECT.",
        "first_word_rule": "The transaction hash is part of the command and binds the decision to these reviewed bytes.",
        "edit_rule": "For EDIT, put corrections after the hash so Odylith can rebuild from the new evidence.",
        "post_confirm_contract": (
            "CONFIRM commits only this hash-bound transaction; commit-only create verifies the hash, "
            "compiler receipt, and repo preconditions, writes only sealed bytes under the rollback "
            "guard, validates readback, and reports success or environment/IO failure."
        ),
        "choices": [
            {
                "command": f"CONFIRM {transaction_hash}",
                "description": "Commit this exact validated package now. Odylith verifies the hash and repo "
                "preconditions, writes the sealed bytes, and validates readback. No product reinterpretation, "
                "repair, or generation runs after CONFIRM.",
                "commit_command": commit_command,
            },
            {
                "command": f"EDIT {transaction_hash} <corrections>",
                "description": "Do not commit. Replace <corrections> with your changes; Odylith treats them as new "
                "evidence, rebuilds the package, and uses the new hash.",
            },
            {
                "command": f"REJECT {transaction_hash}",
                "description": "Stop this exact pending package. No governed records are written.",
            },
        ],
        "confirm": f"CONFIRM {transaction_hash}",
        "edit": f"EDIT {transaction_hash} <corrections>",
        "reject": f"REJECT {transaction_hash}",
    }


def _transaction_confirmation_text(
    *,
    transaction: Any,
    output_path: str = "",
) -> str:
    from odylith.runtime.domain_intelligence.greenfield_confirmation_rail import (
        format_confirmation_choice_lines,
    )

    summary = transaction.summary()
    manifest = transaction.quality_manifest if isinstance(transaction.quality_manifest, Mapping) else {}
    intent_authority = transaction.intent_authority if isinstance(transaction.intent_authority, Mapping) else {}
    package = transaction.prewrite_package
    backlog_result = package.backlog_result if isinstance(package.backlog_result, Mapping) else {}
    created = backlog_result.get("created") if isinstance(backlog_result.get("created"), list) else []
    components = package.component_registry_preview if isinstance(package.component_registry_preview, tuple) else ()
    diagrams = package.rendered_atlas_sources if isinstance(package.rendered_atlas_sources, Mapping) else {}
    confirmation = _transaction_confirmation_payload(transaction=transaction, output_path=output_path)
    lines = [
        "ProductCreateTransaction ready for final command",
        f"- transaction hash: {summary['transaction_hash']}",
        f"- product facts hash: {intent_authority.get('product_facts_sha256', '')}",
        f"- quality gate: {summary.get('quality_status') or manifest.get('status', 'unknown')}",
        f"- validation gate: {summary.get('validation_status') or manifest.get('validation_status', 'unknown')}",
        f"- governed package: {len(created)} workstreams, {len(components)} component previews, {len(diagrams)} Atlas previews",
        f"- sealed commit: {summary.get('repository_write_count', 0)} exact file writes, "
        f"{summary.get('repository_delete_count', 0)} deletions, and hashed repo preconditions",
        "- commands below include this exact transaction hash; copy CONFIRM or REJECT unchanged, or replace the "
        "EDIT corrections placeholder",
        "",
        *format_confirmation_choice_lines(
            tuple(
                (
                    str(choice["command"]),
                    (
                        f"{choice['description']} Run `{choice['commit_command']}`"
                        if str(choice["command"]).startswith("CONFIRM ")
                        else str(choice["description"])
                    ),
                )
                for choice in confirmation["choices"]
            )
        ),
    ]
    if output_path:
        lines.insert(1, f"- transaction file: {output_path}")
    return "\n".join(lines).rstrip() + "\n"


def _print_greenfield_error(exc: Exception, *, as_json: bool) -> None:
    if as_json:
        payload: dict[str, Any] = {"mode": "error", "error": str(exc)}
        manifest = getattr(exc, "manifest", None)
        if isinstance(manifest, Mapping):
            payload["commit_manifest"] = dict(manifest)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(str(exc))


def _transaction_output_path(*, repo_root: Path, output_path: str) -> Path | None:
    value = str(output_path or "").strip()
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else repo_root / path


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
    semantic_intent_file: str,
) -> tuple[dict[str, Any], Any, Path]:
    from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store
    from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
        load_semantic_intent_packet,
        semantic_intent_authority,
    )
    from odylith.runtime.domain_intelligence.greenfield_semantic_workflow import (
        build_verified_semantic_proposal_for_repo,
        compile_verified_semantic_transaction,
    )

    packet_path = Path(semantic_intent_file).expanduser()
    if not packet_path.is_absolute():
        packet_path = repo_root / packet_path
    verified = load_semantic_intent_packet(
        packet_path,
        prompt=prompt,
        edit_evidence=edit_evidence,
    )
    candidate_intent = dict(verified.product_facts)
    candidate_intent["product_intent_authority"] = semantic_intent_authority(
        verified,
        prompt=prompt,
        edit_evidence=edit_evidence,
    )
    proposal = build_verified_semantic_proposal_for_repo(
        repo_root=repo_root,
        authority=candidate_intent["product_intent_authority"],
        release_selector=release_selector,
    )
    candidate_authority = candidate_intent.get("product_intent_authority")
    if not isinstance(candidate_authority, Mapping):
        raise RuntimeError("pre-confirm typed Product Intent authority is missing")
    proposal = dict(proposal)
    proposal["product_intent_authority"] = candidate_authority
    transaction = compile_verified_semantic_transaction(
        repo_root=repo_root,
        proposal=proposal,
        release_selector=release_selector,
    )
    proposal_authority = (
        transaction.proposal.get("product_intent_authority")
        if isinstance(transaction.proposal, Mapping)
        else None
    )
    transaction_authority = transaction.intent_authority if isinstance(transaction.intent_authority, Mapping) else {}
    if not product_intent_authorities_match(proposal_authority, transaction_authority):
        raise RuntimeError(
            "pre-confirm compiler produced a transaction whose Product Intent authority bytes do not match "
            "the visible typed preview"
        )
    candidate_intent = dict(transaction.proposal.get("intent") or {})
    candidate_intent["product_intent_authority"] = transaction_authority
    transaction_path = greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=repo_root,
        transaction=transaction,
    )
    return candidate_intent, transaction, transaction_path


def _public_intent_hypothesis(candidate_intent: Mapping[str, Any]) -> dict[str, Any]:
    """Return typed Product Intent without exposing the private custody receipt."""

    visible = dict(candidate_intent)
    authority = visible.pop("product_intent_authority", None)
    if isinstance(authority, Mapping):
        visible["product_intent_authority_summary"] = {
            "schema_version": _PUBLIC_INTENT_AUTHORITY_SUMMARY_VERSION,
            "authority_version": str(authority.get("version", "")).strip(),
            **{
                key: authority[key]
                for key in _PUBLIC_INTENT_AUTHORITY_SUMMARY_KEYS
                if str(authority.get(key, "")).strip()
            },
        }
    return visible


def _semantic_intent_file_message() -> str:
    return (
        "Greenfield requires a source-cited Semantic Intent packet authored by the active host model. "
        "Run `odylith greenfield semantic-intent-request --repo-root . --prompt <request>`, author the packet "
        "at the returned destination, then use the returned next invocation. Plain prompt and EDIT text remain "
        "evidence, never parser-derived product authority."
    )


def _render_product_intent_preview(intent: Mapping[str, Any]) -> str:
    from odylith.runtime.domain_intelligence.greenfield_candidate_intent_stage import render_candidate_intent_markdown

    return render_candidate_intent_markdown(intent).replace(
        "Product Intent Confirmation", "Product Intent Preview", 1
    )


def main(argv: Sequence[str] | None = None) -> int:
    tokens = [str(token) for token in (argv or ())]
    if tokens[:1] == ["create"]:
        from odylith.runtime.domain_intelligence.greenfield_create_cli import main as create_main

        return create_main(tokens)
    args = _parse_args(tokens)
    if args.command == "semantic-intent-schema":
        from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
            semantic_intent_packet_schema,
        )

        print(json.dumps(semantic_intent_packet_schema(), indent=2, sort_keys=True))
        return 0
    if args.command == "semantic-intent-request":
        from odylith.runtime.domain_intelligence.greenfield_semantic_intent_request import (
            semantic_intent_authoring_request,
            semantic_intent_revision_request,
        )

        repo_root = Path(str(args.repo_root)).expanduser().resolve()
        try:
            edit_evidence = _edit_evidence_from_args(args, repo_root=repo_root)
            supersedes = str(args.supersedes_hash or "").strip()
            if supersedes:
                request = semantic_intent_revision_request(
                    repo_root=repo_root,
                    transaction_hash=supersedes,
                    correction=edit_evidence,
                )
            else:
                prompt = str(args.prompt or "")
                if not prompt:
                    raise ValueError("Greenfield Semantic Intent authoring requires --prompt")
                request = semantic_intent_authoring_request(
                    prompt=prompt,
                    edit_evidence=edit_evidence,
                )
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=True)
            return 2
        print(json.dumps(request, indent=2, sort_keys=True))
        return 0
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    if args.command == "propose":
        semantic_intent_file = str(args.intent_file or "").strip()
        if bool(args.confirm_intent) or not semantic_intent_file:
            _print_greenfield_error(ValueError(_semantic_intent_file_message()), as_json=args.output_format == "json")
            return 2
        try:
            edit_evidence = _edit_evidence_from_args(args, repo_root=repo_root)
            candidate_intent, transaction, transaction_path = _compile_prompt_evidence_transaction(
                repo_root=repo_root,
                prompt=str(args.prompt),
                release_selector="",
                edit_evidence=edit_evidence,
                semantic_intent_file=semantic_intent_file,
            )
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        if args.output_format == "json":
            print(json.dumps({
                "mode": "product_create_transaction",
                "intent_hypothesis": _public_intent_hypothesis(candidate_intent),
                "product_create_transaction": transaction.summary(),
                "transaction_file": str(transaction_path.relative_to(repo_root)),
                "confirmation": _transaction_confirmation_payload(
                    transaction=transaction,
                    output_path=str(transaction_path.relative_to(repo_root)),
                ),
            }, indent=2, sort_keys=True))
        else:
            preview = _render_product_intent_preview(candidate_intent).rstrip()
            print(
                f"{preview}\n\n{_transaction_confirmation_text(transaction=transaction, output_path=str(transaction_path.relative_to(repo_root)))}",
                end="",
            )
        return 0
    if args.command == "apply":
        message = _legacy_apply_disabled_error()
        if args.as_json:
            print(json.dumps({"mode": "error", "error": message}, indent=2, sort_keys=True))
        else:
            print(message)
        return 2
    if args.command == "compile-transaction":
        semantic_intent_file = str(args.intent_file or "").strip()
        if not semantic_intent_file:
            _print_greenfield_error(ValueError(_semantic_intent_file_message()), as_json=args.output_format == "json")
            return 2
        try:
            edit_evidence = _edit_evidence_from_args(args, repo_root=repo_root)
            candidate_intent, transaction, staged_path = _compile_prompt_evidence_transaction(
                repo_root=repo_root,
                prompt=str(args.prompt),
                release_selector=str(args.release),
                edit_evidence=edit_evidence,
                semantic_intent_file=semantic_intent_file,
            )
            output_path = str(args.output or "").strip()
            if output_path:
                path = _transaction_output_path(repo_root=repo_root, output_path=output_path)
                assert path is not None
                from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
                    write_compiled_product_create_transaction_file,
                )

                write_compiled_product_create_transaction_file(path, transaction)
                output_path = str(path)
            else:
                output_path = str(staged_path)
            if args.output_format == "json":
                from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
                    product_create_transaction_to_dict,
                )

                summary = transaction.summary()
                payload = {
                    "mode": "product_create_transaction",
                    "intent_hypothesis": _public_intent_hypothesis(candidate_intent),
                    "product_create_transaction": summary,
                    "transaction": product_create_transaction_to_dict(transaction),
                    "confirmation": _transaction_confirmation_payload(
                        transaction=transaction,
                        output_path=output_path,
                    ),
                }
                if output_path:
                    payload["transaction_file"] = output_path
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                preview = _render_product_intent_preview(candidate_intent).rstrip()
                print(f"{preview}\n\n{_transaction_confirmation_text(transaction=transaction, output_path=output_path)}", end="")
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        return 0
    return 2
