"""CLI adapter for confirmed greenfield proposal commands."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import (
    greenfield_generation_store,
    greenfield_pending_transaction_store,
    greenfield_proposals,
)
from odylith.runtime.domain_intelligence.greenfield_cli import terminal_decision_offer
from odylith.runtime.domain_intelligence.greenfield_authority_gate import (
    greenfield_authority_gate_contract,
    load_greenfield_authority_gate_file,
    validate_greenfield_authority_gate,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    require_product_create_transaction_quality_approved,
    require_product_create_transaction_verified,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    greenfield_host_candidate_contract,
    load_greenfield_host_candidate_file,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import (
    materialize_host_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    GreenfieldClarificationRequired,
    prepare_model_authoring_evidence,
    render_product_intent_preview,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelRuntimeError,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
    GREENFIELD_NORMAL_CASE_TARGET_SECONDS,
    GREENFIELD_OPERATIONAL_TIMEOUT_SECONDS,
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
    model_profile_id_for_repair_tier,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_EVIDENCE_BYTES,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import (
    PRECONFIRM_REPAIR_TIERS,
    GreenfieldPreconfirmEngineError,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    load_greenfield_source_duty_file,
    preflight_greenfield_source_duty_ledger,
    validate_greenfield_source_duty_ledger,
    verify_greenfield_source_duty_ledger_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import (
    greenfield_edit_preservation_context,
    source_duty_entailment_task,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_compact import (
    expand_compact_source_duty_ledger,
)

_PUBLIC_INTENT_AUTHORITY_SUMMARY_VERSION = "odylith.product-intent-authority-summary.v1"
_PUBLIC_INTENT_AUTHORITY_SUMMARY_KEYS = (
    "product_facts_sha256",
    "source_format",
    "materiality_status",
)
_REPAIR_TIER_TIMING_HELP = (
    "Release-success proposal target: auto/standard "
    f"{get_greenfield_model_profile(STANDARD_PROFILE_ID).performance_target_seconds:g}s advisory. "
    "Declared non-success evidence profiles: Luna clarification/no-write control "
    f"{get_greenfield_model_profile(RESCUE_PROFILE_ID).performance_target_seconds:g}s advisory; "
    "Sol negative diagnostic "
    f"{get_greenfield_model_profile(DEEP_PROFILE_ID).performance_target_seconds:g}s advisory. "
    "Control and diagnostic profiles are not executable success choices."
    + f" Operational safety timeout: {GREENFIELD_OPERATIONAL_TIMEOUT_SECONDS:g}s for auto/standard; "
    + f"{get_greenfield_model_profile(RESCUE_PROFILE_ID).operational_timeout_seconds:g}s for control/diagnostic profiles."
    + f" Normal-case target: {GREENFIELD_NORMAL_CASE_TARGET_SECONDS:g}s (advisory)."
)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith greenfield",
        description="Review staged Greenfield packages and choose an explicit terminal decision.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    propose = subparsers.add_parser("propose", help="Stage a complete Greenfield package and show a read-only proposal.")
    propose.add_argument("--repo-root", default=".")
    propose.add_argument("--completion-receipt", default="")
    propose.add_argument("--prompt", required=True)
    propose.add_argument(
        "--candidate-file",
        default="",
        help=(
            "Path to one host-authored candidate matching the returned candidate-contract "
            "schema. Odylith treats it as an untrusted hypothesis, revalidates its source "
            "custody and deterministically validates the complete candidate once."
        ),
    )
    propose.add_argument(
        "--gate-file",
        required=True,
        help="Source-bound pre-author authority decision returned for this exact request.",
    )
    propose.add_argument(
        "--ledger-file", required=True,
        help="Accepted source-duty receipt for this exact request, written outside the repository.",
    )
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
        help="Reserved preview depth selector. `propose` always compiles the full staged transaction before review.",
    )
    propose.add_argument(
        "--repair-tier",
        choices=PRECONFIRM_REPAIR_TIERS,
        default=greenfield_proposals.DEFAULT_PRECONFIRM_REPAIR_TIER,
        help=_REPAIR_TIER_TIMING_HELP,
    )
    propose.add_argument(
        "--evidence-language",
        choices=("en",),
        default="en",
        help="Declared language of prompt and EDIT evidence. Greenfield v3 currently supports English evidence.",
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
        help="Legacy proposal apply is disabled; use propose, then choose a terminal decision.",
        description="Legacy proposal apply is disabled; use propose, then choose a terminal decision.",
    )
    apply.add_argument("--repo-root", default=".")
    apply.add_argument("--proposal-file", default="")
    apply.add_argument("--proposal-json", default="")
    apply.add_argument("--confirm", action="store_true")
    apply.add_argument("--release", default="")
    apply.add_argument(
        "--repair-tier",
        choices=PRECONFIRM_REPAIR_TIERS,
        default=greenfield_proposals.DEFAULT_PRECONFIRM_REPAIR_TIER,
        help=_REPAIR_TIER_TIMING_HELP,
    )
    apply.add_argument("--json", action="store_true", dest="as_json")
    compile_transaction = subparsers.add_parser(
        "compile-transaction",
        help="Compile a no-write ProductCreateTransaction for controlled tooling; normal product flow uses propose.",
    )
    compile_transaction.add_argument("--repo-root", default=".")
    compile_transaction.add_argument("--prompt", required=True)
    compile_transaction.add_argument(
        "--candidate-file",
        default="",
        help=(
            "Path to one host-authored candidate matching the returned candidate-contract "
            "schema for deterministic validation and sealing."
        ),
    )
    compile_transaction.add_argument(
        "--gate-file",
        required=True,
        help="Source-bound pre-author authority decision returned for this exact request.",
    )
    compile_transaction.add_argument("--ledger-file", required=True)
    compile_transaction.add_argument("--edit", default="", help=argparse.SUPPRESS)
    compile_transaction.add_argument("--edit-evidence", default="", help=argparse.SUPPRESS)
    compile_transaction.add_argument(
        "--evidence-language",
        choices=("en",),
        default="en",
        help=argparse.SUPPRESS,
    )
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
        choices=PRECONFIRM_REPAIR_TIERS,
        default=greenfield_proposals.DEFAULT_PRECONFIRM_REPAIR_TIER,
        help=_REPAIR_TIER_TIMING_HELP,
    )
    compile_transaction.add_argument(
        "--output",
        default="",
        help="Optional path for the compiled transaction JSON. The proposal view remains read-only.",
    )
    compile_transaction.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    candidate_contract = subparsers.add_parser(
        "candidate-contract",
        help="Show the typed host reasoning contract for one Greenfield request.",
    )
    candidate_contract.add_argument("--repo-root", default=".")
    candidate_source = candidate_contract.add_mutually_exclusive_group(required=True)
    candidate_source.add_argument("--prompt")
    candidate_source.add_argument(
        "--transaction-hash",
        help="Use the retained source from this sealed package for an EDIT candidate.",
    )
    candidate_contract.add_argument("--completion-receipt", default="")
    candidate_contract.add_argument("--edit", default="")
    candidate_contract.add_argument("--edit-evidence", default="")
    candidate_contract.add_argument(
        "--evidence-language",
        choices=("en",),
        default="en",
    )
    authority_check = subparsers.add_parser(
        "authority-check",
        help="Validate one host-authored source-authority decision without staging a package.",
    )
    authority_check.add_argument("--repo-root", default=".")
    authority_check.add_argument("--prompt", required=True)
    authority_check.add_argument("--edit", default="")
    authority_check.add_argument("--edit-evidence", default="")
    authority_check.add_argument("--gate-file", required=True)
    authority_check.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    source_ledger_check = subparsers.add_parser(
        "source-ledger-check",
        help="Preflight source duties, then admit one source-only decision set before candidate authoring.",
    )
    source_ledger_check.add_argument("--repo-root", default=".")
    source_ledger_check.add_argument("--prompt", required=True)
    source_ledger_check.add_argument("--transaction-hash", default="")
    source_ledger_check.add_argument("--completion-receipt", default="")
    source_ledger_check.add_argument("--edit", default="")
    source_ledger_check.add_argument("--edit-evidence", default="")
    source_ledger_check.add_argument("--ledger-file", required=True)
    source_ledger_check.add_argument(
        "--decision-file", default="",
        help="One source-only decision set for admitting the preflighted ledger.",
    )
    source_ledger_check.add_argument(
        "--format", choices=("text", "json"), default="json", dest="output_format",
    )
    return parser.parse_args(argv)


def _legacy_apply_disabled_error() -> str:
    return (
        "greenfield apply is disabled. Use `odylith greenfield propose --repo-root . --prompt <request>` "
        "for a read-only preview with explicit terminal decision commands. "
        "No governed records were written."
    )


def _transaction_review_text(
    *,
    repo_root: Path,
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
    confirmation = terminal_decision_offer(repo_root=repo_root, transaction_hash=summary["transaction_hash"])
    lines = [
        "## Review only",
        f"- transaction hash: {summary['transaction_hash']}",
        f"- product facts hash: {intent_authority.get('product_facts_sha256', '')}",
        f"- quality gate: {summary.get('quality_status') or manifest.get('status', 'unknown')}",
        f"- validation gate: {summary.get('validation_status') or manifest.get('validation_status', 'unknown')}",
        f"- governed package: {len(created)} workstreams, {len(components)} component previews, {len(diagrams)} Atlas previews",
        (
            f"- sealed commit: {summary.get('repository_write_count', 0)} exact file writes, "
            f"{summary.get('repository_delete_count', 0)} deletions, and hashed repo preconditions"
        ),
        "",
        str(confirmation["reason"]),
        "",
        "## Choose one command",
        "",
        *[f"**{choice['label']}**\n\n```sh\n{choice['command']}\n```\n" for choice in confirmation["choices"]],
    ]
    if output_path:
        lines.insert(1, f"- transaction file: {output_path}")
    return "\n".join(lines).rstrip() + "\n"


def _print_transaction_review(
    *, repo_root: Path, candidate_intent: Mapping[str, Any], transaction: Any,
    transaction_path: Path, as_json: bool,
) -> None:
    if as_json:
        print(json.dumps({
            "mode": "product_create_transaction",
            "intent_hypothesis": _public_intent_hypothesis(candidate_intent),
            "product_create_transaction": transaction.summary(),
            "transaction_file": str(transaction_path.relative_to(repo_root)),
            "confirmation": terminal_decision_offer(
                repo_root=repo_root, transaction_hash=transaction.transaction_hash,
            ),
        }, indent=2, sort_keys=True))
    else:
        preview = render_product_intent_preview(candidate_intent).rstrip()
        review = _transaction_review_text(
            repo_root=repo_root, transaction=transaction,
            output_path=str(transaction_path.relative_to(repo_root)),
        )
        print(f"{preview}\n\n{review}", end="")


def rebuild_pending_transaction(
    *, repo_root: Path, transaction_hash: str, edit_evidence: str,
    edit_evidence_file: str, as_json: bool, started_at: float | None = None,
    host_candidate_file: str = "",
    authority_gate_file: str = "",
    source_duty_file: str = "",
    completion_receipt: Path | str | None = None,
) -> int:
    """Re-author from verified retained evidence; never alter the sealed package."""
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
        load_compiled_product_create_transaction_file,
    )

    started = time.perf_counter() if started_at is None else started_at
    try:
        path = greenfield_pending_transaction_store.resolve_pending_transaction(
            repo_root=repo_root, transaction_hash=transaction_hash, completion_receipt=completion_receipt,
        )
        previous = load_compiled_product_create_transaction_file(path)
        correction = _edit_evidence_from_args(
            argparse.Namespace(edit=edit_evidence, edit_evidence=edit_evidence_file), repo_root=repo_root,
        )
        if not correction.strip():
            raise ValueError("Add your correction with --edit or --edit-evidence. No governed records were written.")
        prompt = previous.proposal.get("intent", {}).get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("The sealed package has no retained source evidence; start a new proposal.")
        decision = _authority_gate_from_args(
            argparse.Namespace(gate_file=authority_gate_file, evidence_language="en"),
            repo_root=repo_root, prompt=prompt, edit_evidence=correction,
        )
        _require_admitted_authority_gate(decision)
        ledger_receipt = _source_duty_receipt_from_args(
            argparse.Namespace(ledger_file=source_duty_file, evidence_language="en",
                               transaction_hash=transaction_hash, completion_receipt=completion_receipt),
            repo_root=repo_root, prompt=prompt, edit_evidence=correction,
        )
        if not str(host_candidate_file or "").strip():
            raise ValueError(
                "Greenfield EDIT requires one host-authored candidate matching the "
                "returned candidate-contract schema. No governed records were written."
            )
        candidate_path = Path(str(host_candidate_file)).expanduser()
        if candidate_path and not candidate_path.is_absolute():
            candidate_path = repo_root / candidate_path
        host_candidate = load_greenfield_host_candidate_file(candidate_path)
        candidate, transaction, staged_path = _compile_prompt_evidence_transaction(
            repo_root=repo_root, prompt=prompt, edit_evidence=correction,
            release_selector=previous.release_selector,
            repair_tier=previous.quality_manifest["requested_repair_tier"],
            source_language="en", started_at=started,
            host_candidate=host_candidate,
            source_duty_receipt=ledger_receipt, completion_receipt=completion_receipt,
        )
        if transaction.transaction_hash == transaction_hash:
            raise RuntimeError("The correction did not produce a new sealed package. The old package is unchanged.")
    except GreenfieldClarificationRequired as exc:
        return _finish_clarification(exc=exc, as_json=as_json)
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        _print_greenfield_error(exc, as_json=as_json)
        return 2
    _print_transaction_review(
        repo_root=repo_root, candidate_intent=candidate, transaction=transaction,
        transaction_path=staged_path, as_json=as_json,
    )
    return 0


def _print_greenfield_error(exc: Exception, *, as_json: bool) -> None:
    if as_json:
        payload: dict[str, Any] = {"mode": "error", "error": str(exc)}
        if isinstance(exc, GreenfieldModelRuntimeError):
            payload["outcome"] = exc.outcome
        if isinstance(exc, GreenfieldPreconfirmEngineError):
            payload["commit_manifest"] = exc.manifest
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(str(exc))


def _print_greenfield_clarification(exc: GreenfieldClarificationRequired, *, as_json: bool) -> None:
    clarification = {
        "question": exc.question,
        "required_fields": list(exc.required_fields),
    }
    consistency = exc.authoring_receipt.get("consistency_assessment")
    if isinstance(consistency, Mapping):
        clarification["consistency_assessment"] = dict(consistency)
    if as_json:
        print(json.dumps({"mode": "clarification_required", "clarification": clarification}, indent=2, sort_keys=True))
        return
    print("Odylith needs one product decision.")
    if isinstance(consistency, Mapping) and consistency.get("status") == "material_contradiction":
        print("Conflicting requirements from your request:")
        for span in consistency["source_spans"]:
            print(f"- {json.dumps(span['text'], ensure_ascii=False)}")
    print(exc.question)
    print("Reply with one plain-language sentence. No transaction or governed records were created.")


def _transaction_output_path(*, repo_root: Path, output_path: str) -> Path | None:
    value = str(output_path or "").strip()
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else repo_root / path


def _finish_clarification(
    *,
    exc: GreenfieldClarificationRequired,
    as_json: bool,
) -> int:
    _print_greenfield_clarification(exc, as_json=as_json)
    return 0


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
        with path.open("rb") as handle:
            payload = handle.read(MAX_EVIDENCE_BYTES + 1)
    except OSError as exc:
        raise RuntimeError("environment/IO failure while reading EDIT evidence") from exc
    if len(payload) > MAX_EVIDENCE_BYTES:
        raise ValueError("Greenfield EDIT evidence exceeds the declared model-input bound")
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Greenfield EDIT evidence must be valid UTF-8 text") from exc


def _host_candidate_from_args(
    args: argparse.Namespace, *, repo_root: Path,
) -> dict[str, Any]:
    value = str(getattr(args, "candidate_file", "") or "").strip()
    if not value:
        raise ValueError(
            "Greenfield requires one host-authored candidate matching the returned "
            "candidate-contract schema; no records were created."
        )
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    return load_greenfield_host_candidate_file(path)


def _authority_gate_from_args(
    args: argparse.Namespace, *, repo_root: Path, prompt: str, edit_evidence: str,
) -> dict[str, Any]:
    value = str(getattr(args, "gate_file", "") or "").strip()
    if not value:
        raise ValueError("Greenfield requires a source-authority gate for this request; no records were created.")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    prepared = prepare_model_authoring_evidence(
        prompt=prompt,
        edit_evidence=edit_evidence,
        source_language=str(getattr(args, "evidence_language", "en")),
    )
    return validate_greenfield_authority_gate(
        load_greenfield_authority_gate_file(path),
        evidence_source=prepared.evidence_source,
    )


def _edit_transaction_from_args(args: argparse.Namespace, *, repo_root: Path, correction: str):
    transaction_hash = str(getattr(args, "transaction_hash", "") or "")
    if not transaction_hash:
        if correction.strip():
            raise ValueError("Greenfield EDIT requires the prior transaction hash; bounded packages also require their delivered completion receipt.")
        return None
    if not correction.strip():
        raise ValueError("Greenfield EDIT requires an explicit correction.")
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
        load_compiled_product_create_transaction_file,
    )
    return load_compiled_product_create_transaction_file(
        greenfield_pending_transaction_store.resolve_pending_transaction(
            repo_root=repo_root, transaction_hash=transaction_hash,
            completion_receipt=getattr(args, "completion_receipt", None) or None,
        )
    )


def _edit_preservation(previous, *, correction: str, evidence_text: str):
    if previous is None:
        return None
    import hashlib
    from odylith.runtime.domain_intelligence.greenfield_authored_semantics import combined_prompt_evidence_segment
    from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import source_action_allocation_relations
    intent, authority = previous.proposal["intent"], previous.intent_authority
    raw = intent["prompt"].encode("utf-8")
    if hashlib.sha256(raw).hexdigest() != authority["markdown_source_sha256"]:
        raise ValueError("EDIT cannot recover the accepted reviewed-document source from this package. Start a new proposal with the complete source; no project records were created.")
    semantics = intent["authored_semantics"]
    duty = semantics["source_duty"]
    relations = semantics.get("source_event_relations")
    if not isinstance(relations, list):
        raise ValueError("EDIT requires authenticated complete source-action custody; no project records were created.")
    by_order = {row["order"]: row for row in relations}
    actions = {}
    for section in ("first_path_actions", "supporting_human_actions", "system_duties"):
        orders = {row["duty_id"]: row["event_order"] for row in duty["binding"][section]}
        actions[section] = []
        for row in duty["ledger_receipt"]["ledger"][section]:
            event = by_order[orders[row["id"]]]
            start, end = event["source_start_byte"], event["source_end_byte"]
            actions[section].append({"duty": row,
                "source_locator": {"relation_order": event["order"], "source_start_byte": start,
                    "source_end_byte": end, "text_sha256": hashlib.sha256(raw[start:end]).hexdigest()},
                "allocation_relations": source_action_allocation_relations(semantics["provisional_design"], event["order"])})
    systems = {field: [row for row in authority["atomic_facts"] if any(link["field"] == field for link in row["projection_links"])]
               for field in ("internal_systems", "external_systems")}
    for field, atoms in systems.items():
        paths = {link["path"]: atom["normalized_value"] for atom in atoms for link in atom["projection_links"]
                 if link["field"] == field and link["relation_order"] == 0}
        if paths != {f"/{field}/{i}": value for i, value in enumerate(intent.get(field, []))}:
            raise ValueError("EDIT requires complete accepted typed system custody; no project records were created.")
    framed, segment = combined_prompt_evidence_segment(prompt=intent["prompt"], edit_evidence=correction)
    if framed != evidence_text:
        raise ValueError("EDIT source frame does not match its authenticated prior request")
    return greenfield_edit_preservation_context(
        transaction_hash=previous.transaction_hash, prior_lifecycle=duty["lifecycle"],
        prior_identity=duty["ledger_receipt"]["ledger"]["product_identity"],
        correction=correction, evidence_text=evidence_text, prior_actions=actions, prior_system_facts=systems,
        prior_source_segment=segment, prior_authority_sha256=authority["authority_snapshot_sha256"],
        prior_relation_set_sha256=authority["authored_relation_set_sha256"],
    )


def _source_duty_receipt_from_args(
    args: argparse.Namespace, *, repo_root: Path, prompt: str, edit_evidence: str,
) -> dict[str, Any]:
    value = str(getattr(args, "ledger_file", "") or "").strip()
    if not value:
        raise ValueError("Greenfield requires an accepted source-duty ledger; no records were created.")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    prepared = prepare_model_authoring_evidence(
        prompt=prompt, edit_evidence=edit_evidence,
        source_language=str(getattr(args, "evidence_language", "en")),
    )
    previous = _edit_transaction_from_args(args, repo_root=repo_root, correction=edit_evidence)
    if previous is not None and previous.proposal.get("intent", {}).get("prompt") != prompt:
        raise ValueError("Greenfield EDIT source does not match the prior sealed request.")
    receipt = verify_greenfield_source_duty_ledger_receipt(
        load_greenfield_source_duty_file(path), evidence_text=prepared.evidence_source,
        edit_preservation=_edit_preservation(
            previous, correction=prepared.edit_evidence, evidence_text=prepared.evidence_source,
        ),
    )
    if previous is None and "edit_preservation" in receipt:
        raise ValueError("An EDIT receipt requires its prior sealed transaction.")
    return receipt


def _require_admitted_authority_gate(decision: Mapping[str, Any]) -> None:
    if decision["decision"] == "clarify":
        raise GreenfieldClarificationRequired(
            str(decision["question"]),
            required_fields=tuple(decision["required_fields"]),
        )


def _compile_prompt_evidence_transaction(
    *,
    repo_root: Path,
    prompt: str,
    edit_evidence: str,
    release_selector: str,
    repair_tier: str = "",
    source_language: str = "en",
    started_at: float | None = None,
    clock: Callable[[], float] | None = None,
    host_candidate: Mapping[str, Any],
    source_duty_receipt: Mapping[str, Any],
    completion_receipt: Path | str | None = None,
) -> tuple[dict[str, Any], Any, Path]:
    now = clock or time.perf_counter
    started = now() if started_at is None else float(started_at)
    requested_tier = str(repair_tier or greenfield_proposals.DEFAULT_PRECONFIRM_REPAIR_TIER).strip().casefold()
    prepared_evidence = prepare_model_authoring_evidence(
        prompt=prompt,
        edit_evidence=edit_evidence,
        source_language=source_language,
    )
    profile_id = model_profile_id_for_repair_tier(requested_tier)
    profile = get_greenfield_model_profile(profile_id)
    if profile.model_timeout_seconds - max(0.0, now() - started) < 1.0:
        raise GreenfieldModelRuntimeError("timeout")
    greenfield_generation_store.require_greenfield_working_generation(repo_root)
    authoring_receipt: dict[str, Any] = {}
    candidate_intent = materialize_host_authored_intent(
        prompt=prompt,
        repo_root=repo_root,
        host_candidate=host_candidate,
        source_duty_receipt=source_duty_receipt,
        edit_evidence=edit_evidence,
        authoring_profile_id=profile_id,
        source_language=source_language,
        prepared_evidence=prepared_evidence,
        authoring_receipt=authoring_receipt,
        clock=now,
    )
    authoring_tier = str(authoring_receipt.get("tier") or "").strip()
    if authoring_tier not in {"standard", "rescue", "deep"}:
        raise RuntimeError(
            "Greenfield did not receive a valid source-cited authoring receipt; no records were created."
        )
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=repo_root,
        prompt=prompt,
        confirmed_intent=candidate_intent,
        require_completion_ready=False,
    )
    candidate_authority = candidate_intent.get("product_intent_authority")
    if not isinstance(candidate_authority, Mapping):
        raise TypeError("pre-confirm typed Product Intent authority is missing")
    proposal = dict(proposal)
    proposal["product_intent_authority"] = candidate_authority
    elapsed_before_preconfirm_seconds = max(0.0, now() - started)
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=repo_root,
        proposal=proposal,
        release_selector=release_selector,
        proposal_ready=True,
        preconfirm_elapsed_seconds=elapsed_before_preconfirm_seconds,
        model_authoring_tier=authoring_tier,
        model_authoring_receipt=authoring_receipt,
        **({"repair_tier": repair_tier} if repair_tier else {}),
    )
    candidate_intent = dict(transaction.proposal.get("intent") or {})
    candidate_intent["product_intent_authority"] = transaction.intent_authority
    candidate_authority = candidate_intent.get("product_intent_authority")
    transaction_authority = transaction.intent_authority if isinstance(transaction.intent_authority, Mapping) else {}
    if not isinstance(candidate_authority, Mapping) or (
        str(candidate_authority.get("product_facts_sha256", "")).strip()
        != str(transaction_authority.get("product_facts_sha256", "")).strip()
    ):
        raise RuntimeError(
            "pre-confirm compiler produced a transaction whose product facts do not match the visible typed preview"
        )
    quality_manifest = dict(transaction.quality_manifest)
    quality_manifest["elapsed_seconds"] = round(max(0.0, now() - started), 3)
    transaction = replace(transaction, quality_manifest=quality_manifest)
    require_product_create_transaction_quality_approved(transaction.quality_manifest)
    require_product_create_transaction_verified(transaction)
    transaction_path = _stage_pending_transaction_with_deadline(
        repo_root=repo_root,
        transaction=transaction,
        started_at=started,
        clock=now, completion_receipt=completion_receipt,
    )
    return candidate_intent, transaction, transaction_path


def _stage_pending_transaction_with_deadline(
    *,
    repo_root: Path,
    transaction: Any,
    started_at: float,
    clock: Callable[[], float],
    completion_receipt: Path | str | None = None,
) -> Path:
    """Publish only while the sealed operational timeout remains valid."""

    operational_timeout_seconds = float(
        transaction.quality_manifest.get("operational_timeout_seconds") or 0.0
    )
    if max(0.0, clock() - started_at) >= operational_timeout_seconds:
        raise RuntimeError("Greenfield proposal exceeded its operational timeout; no records were created.")
    pending_directory = greenfield_pending_transaction_store.pending_transaction_directory(
        repo_root,
        transaction.transaction_hash,
    )
    pending_preexisted = pending_directory.exists()
    transaction_path = greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=repo_root,
        transaction=transaction, completion_receipt=completion_receipt,
    )
    final_elapsed_seconds = max(0.0, clock() - started_at)
    if final_elapsed_seconds >= operational_timeout_seconds:
        if not pending_preexisted and not (pending_directory / ".bounded-journey.v1.json").exists():
            try:
                greenfield_pending_transaction_store.discard_pending_transaction(
                    repo_root=repo_root,
                    transaction_hash=transaction.transaction_hash,
                )
            except (OSError, RuntimeError, ValueError) as exc:
                raise RuntimeError(
                    "Greenfield proposal exceeded its operational timeout and its pending transaction could not be retired; do not confirm it."
                ) from exc
        raise RuntimeError("Greenfield proposal exceeded its operational timeout; no records were created.")
    return transaction_path


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


def _retired_intent_file_message() -> str:
    return (
        "The separate Product Intent confirmation flow is retired. `propose` now compiles the typed evidence and "
        "full ProductCreateTransaction before its read-only review. Use `--edit` or `--edit-evidence` "
        "to rebuild from corrections; edited Markdown is evidence, never a confirmed product source."
    )


def main(argv: Sequence[str] | None = None) -> int:
    tokens = [str(token) for token in (argv or ())]
    if tokens[:1] == ["create"]:
        from odylith.runtime.domain_intelligence.greenfield_create_cli import (
            main as create_main,
        )

        return create_main(tokens)
    args = _parse_args(tokens)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    if args.command == "candidate-contract":
        try:
            edit_evidence = _edit_evidence_from_args(args, repo_root=repo_root)
            prompt = str(args.prompt or "")
            previous = _edit_transaction_from_args(args, repo_root=repo_root, correction=edit_evidence)
            if previous is not None:
                prompt = str(previous.proposal.get("intent", {}).get("prompt") or "")
                if not prompt.strip():
                    raise ValueError(
                        "The sealed package has no retained source evidence; start a new proposal."
                    )
            prepared = prepare_model_authoring_evidence(
                prompt=prompt,
                edit_evidence=edit_evidence,
                source_language=str(args.evidence_language),
            )
            contract = greenfield_host_candidate_contract(
                prepared.evidence_source, edit_preservation=_edit_preservation(
                    previous, correction=prepared.edit_evidence, evidence_text=prepared.evidence_source,
                ),
            )
            contract["authority_gate"] = greenfield_authority_gate_contract(
                prompt=prompt,
                edit_evidence=edit_evidence,
                evidence_source=prepared.evidence_source,
            )
            print(json.dumps(
                contract,
                indent=2,
                sort_keys=True,
            ))
        except (OSError, ValueError, RuntimeError) as exc:
            _print_greenfield_error(exc, as_json=True)
            return 2
        return 0
    if args.command == "authority-check":
        try:
            edit_evidence = _edit_evidence_from_args(args, repo_root=repo_root)
            decision = _authority_gate_from_args(
                args, repo_root=repo_root, prompt=str(args.prompt), edit_evidence=edit_evidence,
            )
            _require_admitted_authority_gate(decision)
        except GreenfieldClarificationRequired as exc:
            return _finish_clarification(exc=exc, as_json=args.output_format == "json")
        except (OSError, ValueError, RuntimeError, TypeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        if args.output_format == "json":
            print(json.dumps({"mode": "authority_admitted", "gate": decision}, sort_keys=True))
        else:
            print("The requested product path has an operator-owned first-path witness.")
        return 0
    if args.command == "source-ledger-check":
        try:
            edit_evidence = _edit_evidence_from_args(args, repo_root=repo_root)
            previous = _edit_transaction_from_args(args, repo_root=repo_root, correction=edit_evidence)
            if previous is not None and previous.proposal.get("intent", {}).get("prompt") != str(args.prompt):
                raise ValueError("Greenfield EDIT source does not match the prior sealed request.")
            prepared = prepare_model_authoring_evidence(
                prompt=str(args.prompt), edit_evidence=edit_evidence,
                source_language="en",
            )
            edit_preservation = _edit_preservation(
                previous, correction=prepared.edit_evidence, evidence_text=prepared.evidence_source,
            )
            path = Path(str(args.ledger_file)).expanduser()
            if not path.is_absolute():
                path = repo_root / path
            ledger = expand_compact_source_duty_ledger(
                load_greenfield_source_duty_file(path), evidence_text=prepared.evidence_source,
            )
            preflight = preflight_greenfield_source_duty_ledger(
                ledger, evidence_text=prepared.evidence_source,
            )
            if ledger["status"] == "clarification_required":
                result = {
                    "mode": "clarification_required",
                    "clarification": {"question": ledger["question"]},
                }
            elif not str(args.decision_file).strip():
                result = {
                    "mode": "source_duty_preflight",
                    "preflight": preflight,
                    "decision_task": source_duty_entailment_task(
                        preflight, evidence_text=prepared.evidence_source,
                        edit_preservation=edit_preservation,
                    ),
                }
            else:
                decision_path = Path(str(args.decision_file)).expanduser()
                if not decision_path.is_absolute():
                    decision_path = repo_root / decision_path
                decision_set = load_greenfield_source_duty_file(decision_path)
                receipt = validate_greenfield_source_duty_ledger(
                    ledger, evidence_text=prepared.evidence_source,
                    decision_set=decision_set,
                    edit_preservation=edit_preservation,
                )
                result = {"mode": "source_duty_admitted", "receipt": receipt}
        except (OSError, ValueError, RuntimeError, TypeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        print(json.dumps(result, indent=2, sort_keys=True) if args.output_format == "json" else result["mode"])
        return 0
    if args.command == "propose":
        if bool(args.confirm_intent) or str(args.intent_file or "").strip():
            _print_greenfield_error(ValueError(_retired_intent_file_message()), as_json=args.output_format == "json")
            return 2
        try:
            started_at = time.perf_counter()
            edit_evidence = _edit_evidence_from_args(args, repo_root=repo_root)
            decision = _authority_gate_from_args(
                args, repo_root=repo_root, prompt=str(args.prompt), edit_evidence=edit_evidence,
            )
            _require_admitted_authority_gate(decision)
            source_duty_receipt = _source_duty_receipt_from_args(
                args, repo_root=repo_root, prompt=str(args.prompt), edit_evidence=edit_evidence,
            )
            host_candidate = _host_candidate_from_args(args, repo_root=repo_root)
            candidate_intent, transaction, transaction_path = _compile_prompt_evidence_transaction(
                repo_root=repo_root,
                prompt=str(args.prompt),
                release_selector="",
                edit_evidence=edit_evidence,
                repair_tier=str(args.repair_tier),
                source_language=str(args.evidence_language),
                started_at=started_at,
                host_candidate=host_candidate,
                source_duty_receipt=source_duty_receipt, completion_receipt=args.completion_receipt or None,
            )
        except GreenfieldClarificationRequired as exc:
            return _finish_clarification(exc=exc, as_json=args.output_format == "json")
        except (OSError, ValueError, RuntimeError, TypeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        _print_transaction_review(
            repo_root=repo_root, candidate_intent=candidate_intent, transaction=transaction,
            transaction_path=transaction_path, as_json=args.output_format == "json",
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
        if str(args.intent_file or "").strip():
            _print_greenfield_error(ValueError(_retired_intent_file_message()), as_json=args.output_format == "json")
            return 2
        try:
            started_at = time.perf_counter()
            edit_evidence = _edit_evidence_from_args(args, repo_root=repo_root)
            decision = _authority_gate_from_args(
                args, repo_root=repo_root, prompt=str(args.prompt), edit_evidence=edit_evidence,
            )
            _require_admitted_authority_gate(decision)
            source_duty_receipt = _source_duty_receipt_from_args(
                args, repo_root=repo_root, prompt=str(args.prompt), edit_evidence=edit_evidence,
            )
            host_candidate = _host_candidate_from_args(args, repo_root=repo_root)
            candidate_intent, transaction, staged_path = _compile_prompt_evidence_transaction(
                repo_root=repo_root,
                prompt=str(args.prompt),
                release_selector=str(args.release),
                edit_evidence=edit_evidence,
                repair_tier=str(args.repair_tier),
                source_language=str(args.evidence_language),
                started_at=started_at,
                host_candidate=host_candidate,
                source_duty_receipt=source_duty_receipt,
            )
            output_path = str(args.output or "").strip()
            if output_path:
                path = _transaction_output_path(repo_root=repo_root, output_path=output_path)
                assert path is not None
                greenfield_proposals.write_product_create_transaction_file(path, transaction)
                output_path = str(path)
            else:
                output_path = str(staged_path)
            if args.output_format == "json":
                summary = transaction.summary()
                payload = {
                    "mode": "product_create_transaction",
                    "intent_hypothesis": _public_intent_hypothesis(candidate_intent),
                    "product_create_transaction": summary,
                    "transaction": greenfield_proposals.product_create_transaction_to_dict(transaction),
                    "confirmation": terminal_decision_offer(
                        repo_root=repo_root, transaction_hash=summary["transaction_hash"],
                    ),
                }
                if output_path:
                    payload["transaction_file"] = output_path
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                preview = render_product_intent_preview(candidate_intent).rstrip()
                print(f"{preview}\n\n{_transaction_review_text(repo_root=repo_root, transaction=transaction, output_path=output_path)}", end="")
        except GreenfieldClarificationRequired as exc:
            return _finish_clarification(
                exc=exc,
                as_json=args.output_format == "json",
            )
        except (OSError, ValueError, RuntimeError, TypeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        return 0
    return 2
