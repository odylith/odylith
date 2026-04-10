"""Validate Odylith product-repo self-host posture.

Two modes are intentionally supported:
- `local-runtime`: validates the live `.odylith/runtime/current` posture for a
  maintainer checkout and fails unless the product repo is dogfooding the
  pinned release lane.
- `release`: validates source-only invariants so CI can gate release cutting
  without requiring a local `.odylith/` runtime checkout.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Sequence

from odylith import __version__
from odylith.runtime.common import agent_runtime_contract
from odylith.install.manager import (
    PINNED_RELEASE_POSTURE,
    PINNED_RUNTIME_SOURCE,
    PRODUCT_REPO_ROLE,
    product_repo_role,
    product_source_version,
    version_status,
)
from odylith.install.state import SIGNER_WORKFLOW_PATH, SIGNER_WORKFLOW_REF, load_version_pin
from odylith.install.state import AUTHORITATIVE_RELEASE_ACTOR, AUTHORITATIVE_RELEASE_REPO
from odylith.runtime.common import log_compass_timeline_event as timeline_logger
from odylith.runtime.governance import version_truth

_TAG_RE = re.compile(r"^v?(?P<version>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?)$")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith validate self-host-posture",
        description="Validate Odylith product-repo self-host posture for local dogfooding or release gating.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--mode",
        choices=("local-runtime", "release"),
        required=True,
        help="Validate either the live local runtime posture or the source-only release contract.",
    )
    parser.add_argument(
        "--expected-tag",
        default="",
        help="Optional release tag like v0.1.0. Required for strict release-tag validation in release mode.",
    )
    return parser.parse_args(argv)


def _normalize_expected_version(tag: str) -> tuple[str, str | None]:
    token = str(tag or "").strip()
    if not token:
        return "", None
    match = _TAG_RE.fullmatch(token)
    if match is None:
        return "", f"expected tag must look like vX.Y.Z, got `{token}`"
    return str(match.group("version") or "").strip(), None


def _append_failure_event(*, repo_root: Path, summary: str) -> None:
    if product_repo_role(repo_root=repo_root) != PRODUCT_REPO_ROLE:
        return
    try:
        timeline_logger.append_event(
            repo_root=repo_root,
            stream_path=agent_runtime_contract.resolve_agent_stream_path(repo_root=repo_root),
            kind="statement",
            summary=summary,
            workstream_values=[],
            artifact_values=[
                "odylith/runtime/source/product-version.v1.json",
                ".odylith/install.json",
                SIGNER_WORKFLOW_PATH,
            ],
            component_values=["odylith", "compass", "dashboard"],
            author="odylith",
            source="odylith.self_host_validator",
        )
    except Exception:
        return


def _workflow_has_release_gate(*, workflow_path: Path) -> bool:
    if not workflow_path.is_file():
        return False
    body = workflow_path.read_text(encoding="utf-8")
    return (
        "validate self-host-posture" in body
        and "--mode release" in body
        and "--expected-tag" in body
    )


def _workflow_has_release_authority_guard(*, workflow_path: Path) -> bool:
    if not workflow_path.is_file():
        return False
    body = workflow_path.read_text(encoding="utf-8")
    required_snippets = (
        f"ODYLITH_RELEASE_REPO: {AUTHORITATIVE_RELEASE_REPO}",
        f"ODYLITH_RELEASE_ACTOR: {AUTHORITATIVE_RELEASE_ACTOR}",
        f"ODYLITH_RELEASE_REF: {SIGNER_WORKFLOW_REF}",
        '[[ "${GITHUB_REPOSITORY}" != "${ODYLITH_RELEASE_REPO}" ]]',
        '[[ "${GITHUB_ACTOR}" != "${ODYLITH_RELEASE_ACTOR}" ]]',
        '[[ "${GITHUB_REF}" != "${ODYLITH_RELEASE_REF}" ]]',
    )
    return all(snippet in body for snippet in required_snippets)


def _workflow_has_release_commit_guard(*, workflow_path: Path) -> bool:
    if not workflow_path.is_file():
        return False
    body = workflow_path.read_text(encoding="utf-8")
    required_snippets = (
        "expected_sha:",
        'tag_sha="$(git rev-parse "${{ inputs.tag }}^{commit}")"',
        'if [[ "${GITHUB_SHA}" != "${{ inputs.expected_sha }}" ]]',
        'if [[ "${tag_sha}" != "${{ inputs.expected_sha }}" ]]',
    )
    return all(snippet in body for snippet in required_snippets)


def validate_local_runtime(*, repo_root: Path) -> list[str]:
    errors: list[str] = []
    if product_repo_role(repo_root=repo_root) != PRODUCT_REPO_ROLE:
        return ["self-host posture validation is only supported in the Odylith product repo"]

    status = version_status(repo_root=repo_root)
    if status.posture != PINNED_RELEASE_POSTURE:
        errors.append(
            f"local self-host posture must be `{PINNED_RELEASE_POSTURE}`, got `{status.posture}`"
        )
    if status.release_eligible is not True:
        errors.append("local self-host posture is not release eligible")
    if status.runtime_source != PINNED_RUNTIME_SOURCE:
        errors.append(f"runtime source must be `{PINNED_RUNTIME_SOURCE}`, got `{status.runtime_source}`")
    return errors


def validate_release_contract(*, repo_root: Path, expected_tag: str) -> list[str]:
    errors: list[str] = []
    if product_repo_role(repo_root=repo_root) != PRODUCT_REPO_ROLE:
        return ["release self-host posture validation is only supported in the Odylith product repo"]

    pin = load_version_pin(repo_root=repo_root, fallback_version=None)
    source_version = product_source_version(repo_root=repo_root)
    expected_version, tag_error = _normalize_expected_version(expected_tag)

    if tag_error is not None:
        errors.append(tag_error)
    errors.extend(version_truth.validate_version_truth(repo_root=repo_root))
    pinned_version = str(pin.odylith_version or "").strip() if pin is not None else ""
    if pin is not None:
        if pinned_version == "source-local":
            errors.append("tracked product version pin must not be `source-local` for release")
        if bool(pin.migration_required):
            errors.append("tracked product version pin is marked migration_required and is not eligible for normal release")
        if expected_version and pinned_version and expected_version != pinned_version:
            errors.append(f"expected release tag version `{expected_version}` does not match tracked product pin `{pinned_version}`")

    if not source_version:
        errors.append("missing or unreadable `[project].version` in `pyproject.toml`")
    elif __version__ != source_version:
        errors.append(f"package version `odylith.__version__={__version__}` does not match `pyproject.toml` version `{source_version}`")
    if expected_version and source_version and expected_version != source_version:
        errors.append(f"expected release tag version `{expected_version}` does not match `pyproject.toml` version `{source_version}`")

    workflow_path = repo_root / SIGNER_WORKFLOW_PATH
    if not workflow_path.is_file():
        errors.append(f"missing release workflow at `{SIGNER_WORKFLOW_PATH}`")
    elif not _workflow_has_release_gate(workflow_path=workflow_path):
        errors.append(
            "release workflow must invoke `odylith validate self-host-posture --mode release --expected-tag ...` before publishing assets"
        )
    elif not _workflow_has_release_authority_guard(workflow_path=workflow_path):
        errors.append(
            f"release workflow must enforce canonical release authority for `{AUTHORITATIVE_RELEASE_REPO}` as `{AUTHORITATIVE_RELEASE_ACTOR}` on `{SIGNER_WORKFLOW_REF}`"
        )
    elif not _workflow_has_release_commit_guard(workflow_path=workflow_path):
        errors.append(
            "release workflow must bind the requested tag to the maintainer session commit via `expected_sha` and `GITHUB_SHA` checks"
        )
    if SIGNER_WORKFLOW_REF != "refs/heads/main":
        errors.append(f"release signer workflow ref must stay pinned to `refs/heads/main`, got `{SIGNER_WORKFLOW_REF}`")

    return errors


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()

    if args.mode == "local-runtime":
        errors = validate_local_runtime(repo_root=repo_root)
        if errors:
            _append_failure_event(
                repo_root=repo_root,
                summary="Self-host release preflight failed because the product repo is not in pinned dogfood posture.",
            )
            print("odylith self-host posture validation FAILED")
            for item in errors:
                print(f"- {item}")
            return 2
        status = version_status(repo_root=repo_root)
        print("odylith self-host posture validation passed")
        print(f"- repo_role: {status.repo_role}")
        print(f"- posture: {status.posture}")
        print(f"- runtime_source: {status.runtime_source}")
        print(f"- release_eligible: {'yes' if status.release_eligible else 'no'}")
        return 0

    errors = validate_release_contract(repo_root=repo_root, expected_tag=str(args.expected_tag))
    if errors:
        print("odylith self-host release contract FAILED")
        for item in errors:
            print(f"- {item}")
        return 2

    print("odylith self-host release contract passed")
    print(f"- expected_tag: {str(args.expected_tag or '<none>').strip()}")
    print(f"- product_version: {product_source_version(repo_root=repo_root)}")
    print(f"- authoritative_release_repo: {AUTHORITATIVE_RELEASE_REPO}")
    print(f"- authoritative_release_actor: {AUTHORITATIVE_RELEASE_ACTOR}")
    print(f"- signer_workflow: {SIGNER_WORKFLOW_PATH}@{SIGNER_WORKFLOW_REF}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
