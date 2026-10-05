"""Supported product-owned bounded Greenfield preparation, without publication."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_host_flow import (
    HostCandidateFlow, HostCandidateFlowError, run_host_candidate_flow,
)
from odylith.runtime.domain_intelligence.greenfield_host_transport import (
    canonical_host_candidate_argv_template, resolve_trusted_codex_executable,
    post_receipt_runtime_env,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID, get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_process import run_command_with_group_timeout


def _request(args, root: Path) -> tuple[str, str]:
    correction = str(args.edit or "")
    if args.edit_evidence:
        from odylith.runtime.domain_intelligence.greenfield_proposals_cli import _edit_evidence_from_args
        correction = _edit_evidence_from_args(args, repo_root=root)
    if args.transaction_hash:
        if args.release:
            raise ValueError("EDIT preparation preserves the original release selector")
        from odylith.runtime.domain_intelligence.greenfield_pending_transaction_store import resolve_pending_transaction
        from odylith.runtime.domain_intelligence.greenfield_create_transaction import load_compiled_product_create_transaction_file
        previous = load_compiled_product_create_transaction_file(resolve_pending_transaction(
            repo_root=root, transaction_hash=args.transaction_hash, completion_receipt=getattr(args,"completion_receipt",None)))
        if not correction.strip():
            raise ValueError("Add correction evidence for an EDIT preparation")
        return str(previous.proposal.get("intent", {}).get("prompt") or ""), correction
    if correction.strip():
        raise ValueError("Correction evidence requires the old transaction hash")
    return str(args.prompt), ""


def prepare_request(args) -> tuple[dict, dict]:
    root = Path(args.repo_root).expanduser().resolve()
    prompt, correction = _request(args, root)
    profile = get_greenfield_model_profile(STANDARD_PROFILE_ID)
    env = dict(os.environ)
    env.update(ODYLITH_GREENFIELD_MODEL_PROFILE=profile.profile_id,
               ODYLITH_REASONING_MODEL=profile.model,
               ODYLITH_REASONING_CODEX_REASONING_EFFORT=profile.reasoning_effort)
    trusted = resolve_trusted_codex_executable(environ=env)
    template = canonical_host_candidate_argv_template()
    host_argv = (trusted, *(argument.replace("{model}", profile.model)
                            .replace("{reasoning_effort}", profile.reasoning_effort)
                            for argument in template[1:]))
    # Invoke this installed interpreter and CLI; never a source-repository module
    # or another host fallback. Both orchestration hosts use the same transport.
    installed = (sys.executable, "-m", "odylith.cli")
    def invoke(command, timeout):
        return run_command_with_group_timeout(cwd=root, env=env, command=list(command), timeout=timeout)
    def propose(candidate, gate, ledger, timeout):
        if args.transaction_hash:
            command = [*installed, "greenfield", "decide", "--repo-root", str(root),
                       "EDIT", args.transaction_hash, "--edit", correction, "--json"]
        else:
            command = [*installed, "greenfield", "propose", "--repo-root", str(root),
                       "--prompt", prompt, "--format", "json"]
            if args.release:
                command.extend(("--release", args.release))
        if getattr(args,"completion_receipt",""):
            command.extend(("--completion-receipt", args.completion_receipt))
        command.extend(("--candidate-file", str(candidate), "--gate-file", str(gate),
                        "--ledger-file", str(ledger)))
        return run_command_with_group_timeout(cwd=root, env=post_receipt_runtime_env(env),
                                               command=command, timeout=timeout)
    observation = {}
    flow = HostCandidateFlow(
        repo_root=root, temp_parent=Path(tempfile.gettempdir()), host_argv=host_argv,
        prompt=prompt, edit_evidence=correction, timeout=profile.operational_timeout_seconds,
        env=env, trusted_codex_executable=trusted, expected_model=profile.model,
        expected_reasoning_effort=profile.reasoning_effort, invoke_installed=invoke,
        invoke_propose=propose, installed_command=installed, observation_sink=observation,
        transaction_hash=args.transaction_hash or "", completion_receipt=getattr(args,"completion_receipt","") or "",
    )
    result = run_host_candidate_flow(flow)
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise ValueError("Greenfield preparation did not return an object")
    if payload.get("mode") == "product_create_transaction":
        from odylith.runtime.domain_intelligence.greenfield_cli import terminal_decision_offer
        from odylith.runtime.domain_intelligence.greenfield_pending_transaction_store import write_completion_receipt_delivery
        try:
            delivered = (write_completion_receipt_delivery(repo_root=root, receipt=flow.completion_receipt_sink)
                         if flow.completion_receipt_sink else getattr(args,"completion_receipt","") or None)
            if delivered:
                payload["completion_receipt"] = str(delivered)
                payload["confirmation"] = terminal_decision_offer(repo_root=root,
                    transaction_hash=payload["product_create_transaction"]["transaction_hash"], completion_receipt=delivered)
        except (OSError, ValueError, KeyError) as exc:
            raise RuntimeError("Greenfield completion was accepted; receipt delivery failed and the package may be unconfirmable") from exc
    return payload, observation


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="odylith greenfield prepare", allow_abbrev=False,
        description="Prepare one read-only sealed package or one material question under one owned deadline.")
    parser.add_argument("--repo-root", default=".")
    request = parser.add_mutually_exclusive_group(required=True)
    request.add_argument("--prompt")
    request.add_argument("--transaction-hash", help="Preserve this old seal and prepare one correction.")
    correction = parser.add_mutually_exclusive_group()
    correction.add_argument("--edit")
    correction.add_argument("--edit-evidence")
    parser.add_argument("--completion-receipt", default="", help="Original delivered receipt for bounded EDIT or an equal existing seal.")
    parser.add_argument("--release", default="")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        payload, observation = prepare_request(args)
        if args.format == "json":
            print(json.dumps({**payload, "bounded_journey": observation}, indent=2, sort_keys=True))
        elif payload.get("mode") == "clarification_required":
            question = payload.get("question") or payload.get("clarification", {}).get("question")
            if not isinstance(question, str) or not question.strip():
                raise ValueError("Greenfield clarification has no question")
            print(question)
        else:
            from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import render_product_intent_preview
            print(render_product_intent_preview(payload["intent_hypothesis"]).rstrip())
            offer = payload["confirmation"]
            print("\n" + offer["reason"])
            for choice in offer["choices"]:
                print(f"\n**{choice['label']}**\n\n```sh\n{choice['command']}\n```")
        return 0
    except (OSError, ValueError, RuntimeError, TypeError, HostCandidateFlowError) as exc:
        message = ("Greenfield preparation stopped before publication." if isinstance(exc, HostCandidateFlowError) else str(exc))
        payload = {"mode": "error", "error": message}
        if isinstance(exc, HostCandidateFlowError):
            payload["bounded_journey"] = exc.observation
        print(json.dumps(payload) if args.format == "json" else message)
        return 2
