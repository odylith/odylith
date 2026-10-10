"""Supported product-owned bounded Greenfield preparation, without publication."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_host_flow import (
    HostCandidateFlow, HostCandidateFlowError, run_host_candidate_flow, _text_stream,
)
from odylith.runtime.domain_intelligence.greenfield_host_transport import (
    canonical_host_candidate_argv_template, resolve_trusted_codex_executable,
    post_receipt_runtime_env,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID, get_greenfield_model_profile,
)
from odylith.runtime.domain_intelligence.greenfield_process import (
    CommandLifecycleObserverError, run_command_with_group_timeout,
)


def _diagnostic_retention(destination: str, *, repo_root: Path):
    """Private custody requires an operator-controlled, stable private parent.

    Pinned inodes and exclusive files preserve artifact identity under that
    assumption. POSIX ancestry checks and writes are not atomic against external
    renames: detected changes refuse, but reparenting can relocate written bytes.
    This evidence is never an admission or completion receipt.
    """
    directory = Path(destination)
    if (not directory.is_absolute() or directory != directory.resolve()
            or directory.is_relative_to(repo_root) or os.path.lexists(directory)
            or not directory.parent.is_dir()):
        raise ValueError("Diagnostic evidence requires a new absolute directory outside the consumer")
    if not all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW")):
        raise ValueError("Private diagnostics require descriptor-relative filesystem custody")
    parent_stat = directory.parent.stat()
    parent_identity = (parent_stat.st_dev, parent_stat.st_ino)
    directory_fd = None
    artifacts, failures = {}, []

    def check_directory(parent_fd: int) -> None:
        parent = os.fstat(parent_fd)
        current_parent = directory.parent.stat()
        if ((parent.st_dev, parent.st_ino) != parent_identity
                or (current_parent.st_dev, current_parent.st_ino) != parent_identity
                or directory.parent.resolve() != directory.parent):
            raise ValueError("Diagnostic parent changed; a stable private parent is required")
        if directory_fd is not None:
            named = os.stat(directory.name, dir_fd=parent_fd, follow_symlinks=False)
            pinned = os.fstat(directory_fd)
            if (named.st_dev, named.st_ino) != (pinned.st_dev, pinned.st_ino):
                raise ValueError("Diagnostic destination changed; a stable private parent is required")

    def retain(name: str, data: bytes) -> None:
        nonlocal directory_fd
        try:
            if Path(name).name != name or name in {"", ".", ".."} or not isinstance(data, bytes):
                raise ValueError("Invalid diagnostic artifact")
            parent_fd = os.open(directory.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                check_directory(parent_fd)
                if directory_fd is None:
                    os.mkdir(directory.name, mode=0o700, dir_fd=parent_fd)
                    created = os.stat(directory.name, dir_fd=parent_fd, follow_symlinks=False)
                    opened_fd = os.open(directory.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                        dir_fd=parent_fd)
                    try:
                        opened = os.fstat(opened_fd)
                        if (opened.st_dev, opened.st_ino) != (created.st_dev, created.st_ino):
                            raise ValueError("Diagnostic destination changed; a stable private parent is required")
                        os.fchmod(opened_fd, 0o700)
                        directory_fd = opened_fd
                    finally:
                        if directory_fd is None:
                            os.close(opened_fd)
                check_directory(parent_fd)
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=directory_fd)
                with os.fdopen(fd, "wb", buffering=0) as stream:
                    remaining = memoryview(data)
                    while remaining:
                        count = stream.write(remaining)
                        if not count:
                            raise OSError("Diagnostic artifact write did not complete")
                        remaining = remaining[count:]
                    stream.flush()
                    os.fsync(stream.fileno())
                check_directory(parent_fd)
            finally:
                os.close(parent_fd)
            artifacts[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        except (OSError, ValueError, TypeError) as exc:
            failures.append({"artifact": name, "error_type": type(exc).__name__})
            raise

    def observe(snapshot) -> None:
        nonlocal directory_fd
        try:
            retain("observation-snapshot.json", json.dumps(dict(snapshot), ensure_ascii=False,
                   sort_keys=True).encode("utf-8"))
            incomplete = failures or snapshot.get("host_command_diagnostic", {}).get(
                "stderr_retention_status") == "rejected_over_bound"
            retain("artifact-index.json", json.dumps({
                "version": "odylith.greenfield.private-diagnostic-evidence.v1",
                "authority": "none", "status": "incomplete" if incomplete else "retained_through_returned_stage",
                "representation": "returned streams re-encoded as UTF8; exact input/schema bytes; not pipe octets",
                "observation_scope": "advisory snapshot before final journey clock",
                "journey_completion": "not certified by this index",
                "artifacts": artifacts, "retention_failures": failures,
            }, ensure_ascii=False, sort_keys=True).encode("utf-8"))
            parent_fd = os.open(directory.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                check_directory(parent_fd)
                os.fsync(directory_fd)
                check_directory(parent_fd)
            finally:
                os.close(parent_fd)
        finally:
            if directory_fd is not None:
                os.close(directory_fd)
                directory_fd = None

    return retain, observe


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
        from odylith.runtime.domain_intelligence.greenfield_proposals_cli import _edit_preservation
        from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
        prompt = str(previous.proposal.get("intent", {}).get("prompt") or "")
        prepared = prepare_model_authoring_evidence(prompt=prompt, edit_evidence=correction)
        _edit_preservation(previous, correction=prepared.edit_evidence, evidence_text=prepared.evidence_source)
        return prompt, correction
    if correction.strip():
        raise ValueError("Correction evidence requires the old transaction hash")
    return str(args.prompt), ""


def prepare_request(args) -> tuple[dict, dict]:
    root = Path(args.repo_root).expanduser().resolve()
    prompt, correction = _request(args, root)
    retain = observe = None
    if getattr(args, "diagnostic_evidence_dir", ""):
        retain, observe = _diagnostic_retention(args.diagnostic_evidence_dir, repo_root=root)
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
    def invoke(command, timeout, *, passive=False):
        error = None
        try:
            result = run_command_with_group_timeout(cwd=root,
                env=post_receipt_runtime_env(env) if passive else env,
                command=list(command), timeout=timeout)
        except CommandLifecycleObserverError as exc:
            if retain is None:
                raise
            result, error = exc.result, exc
        if retain is not None:
            stage = "proposal" if passive else command[len(installed) + 1]
            if stage == "candidate-contract":
                stage = "contract"
            elif stage == "source-ledger-check" and "--decision-file" not in command:
                stage = "source-ledger-preflight"
            for stream in ("stdout", "stderr"):
                retain(stage + "." + stream, _text_stream(getattr(result, stream, "")).encode("utf-8"))
        if error is not None:
            raise error
        return result
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
        return invoke(command, timeout, passive=True)
    observation = {}
    flow = HostCandidateFlow(
        repo_root=root, temp_parent=Path(tempfile.gettempdir()), host_argv=host_argv,
        prompt=prompt, edit_evidence=correction, timeout=profile.operational_timeout_seconds,
        env=env, trusted_codex_executable=trusted, expected_model=profile.model,
        expected_reasoning_effort=profile.reasoning_effort, invoke_installed=invoke,
        invoke_propose=propose, installed_command=installed, observation_sink=observation,
        transaction_hash=args.transaction_hash or "", completion_receipt=getattr(args,"completion_receipt","") or "",
        retain_diagnostic_bytes=retain, observe=observe,
        **({
            "retain_authority_gate_bytes": lambda data: retain("authority-gate.stdout", data),
            "retain_source_ledger_bytes": lambda data: retain("source-ledger.stdout", data),
            "retain_source_duty_decision_bytes": lambda data: retain("source-duty-verifier.stdout", data),
            "retain_candidate_bytes": lambda data: retain("candidate.stdout", data),
            "retain_host_stderr_bytes": lambda stage, data: retain(stage + ".stderr", data),
        } if retain is not None else {}),
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


def _flow_failure_message(exc: HostCandidateFlowError) -> str:
    stage = str(exc.observation.get("stage") or "preparation")
    label = "source inventory verification" if stage == "source-ledger-check" else stage.replace("-", " ")
    message = f"Greenfield preparation stopped during {label} before publication."
    if stage == "source-ledger-check":
        verdict = exc.observation.get("source_completeness_verdict")
        if verdict == "no":
            message += " The verifier reported an incomplete source inventory."
        elif verdict == "uncertain":
            message += " The verifier could not confirm source inventory completeness."
        elif verdict == "missing":
            message += " The verifier did not report source completeness."
    return message


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
    parser.add_argument("--diagnostic-evidence-dir", default="",
        help="Retain private returned UTF8 streams and exact inputs in a new directory outside the consumer; no admission authority.")
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
        if args.format == "text" and args.diagnostic_evidence_dir:
            print("\nPrivate diagnostics requested at: " + args.diagnostic_evidence_dir + " (non-authoritative)")
        return 0
    except (OSError, ValueError, RuntimeError, TypeError, HostCandidateFlowError) as exc:
        message = _flow_failure_message(exc) if isinstance(exc, HostCandidateFlowError) else str(exc)
        payload = {"mode": "error", "error": message}
        if isinstance(exc, HostCandidateFlowError):
            payload["bounded_journey"] = exc.observation
        print(json.dumps(payload) if args.format == "json" else message)
        if args.format == "text" and args.diagnostic_evidence_dir:
            print("\nPrivate diagnostics requested at: " + args.diagnostic_evidence_dir + " (non-authoritative)")
        return 2
