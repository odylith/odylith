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
    create = subparsers.add_parser("create", help="Create confirmed greenfield records from Product Intent.")
    create.add_argument("--repo-root", default=".")
    create.add_argument("--prompt", required=True)
    create.add_argument(
        "--intent-file",
        "--confirmed-intent-file",
        default="",
        dest="intent_file",
        help="Markdown/text/JSON file containing the operator-confirmed Product Intent Confirmation.",
    )
    create.add_argument("--confirm", action="store_true")
    create.add_argument("--release", default="")
    create.add_argument(
        "--repair-tier",
        choices=POST_CONFIRM_REPAIR_TIERS,
        default=greenfield_proposals.DEFAULT_POST_CONFIRM_REPAIR_TIER,
        help=(
            "Create-transaction compiler budget: auto keeps standard compilation under 60s and enters 90s "
            "rescue only for repairable semantic or quality gates; deep is explicit 120s premium/CI proof."
        ),
    )
    create.add_argument("--json", action="store_true", dest="as_json")
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


def _print_greenfield_error(exc: Exception, *, as_json: bool) -> None:
    if as_json:
        payload: dict[str, Any] = {"mode": "error", "error": str(exc)}
        if isinstance(exc, GreenfieldPostConfirmEngineError):
            payload["post_confirm_quality_manifest"] = exc.manifest
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(str(exc))


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
    if args.command == "create":
        if not bool(args.confirm):
            message = (
                "greenfield create requires --confirm after the Product Intent Confirmation is accepted. "
                "Run `odylith greenfield propose --repo-root . --prompt "
                + json.dumps(greenfield_proposals.prompt_text(str(args.prompt)))
                + "` first, then rerun create with --confirm when the interpretation is correct."
            )
            if args.as_json:
                print(json.dumps({"mode": "error", "error": message}, indent=2, sort_keys=True))
            else:
                print(message)
            return 2
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
                enabled=bool(args.as_json),
                action=lambda: greenfield_proposals.apply_greenfield_proposal(
                    repo_root=repo_root,
                    proposal=proposal,
                    confirm=True,
                    release_selector=str(args.release),
                    proposal_ready=True,
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
            print_apply_result(result, verb="create")
        return 0
    return 2
