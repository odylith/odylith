"""Exact trusted host argv and installed Greenfield command transport."""
from __future__ import annotations
import hashlib
import json
import os
import shutil
from pathlib import Path
from collections.abc import Mapping, Sequence
from typing import Any
HOST_NATIVE_ARGV_RECEIPT_VERSION = "odylith.greenfield.host-argv-receipt.v1"

def _canonical_host_candidate_tokens(
    *, model: str, reasoning_effort: str, output_schema: str
) -> tuple[str, ...]:
    """Return the exact direct-Codex token contract used by release authoring."""

    return (
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--model",
        model,
        "--config",
        f"model_reasoning_effort={reasoning_effort}",
        "--output-schema",
        output_schema,
        "-",
    )


def canonical_host_candidate_argv_template() -> tuple[str, ...]:
    """Return the one placeholder argv accepted by Greenfield release proof."""

    return (
        "codex",
        *_canonical_host_candidate_tokens(
            model="{model}",
            reasoning_effort="{reasoning_effort}",
            output_schema="{candidate_schema}",
        ),
    )


def post_receipt_runtime_env(environ: Mapping[str, str]) -> dict[str, str]:
    """Disable every runtime provider route after host-candidate receipt."""

    values = dict(environ)
    values.update(
        {
            "ODYLITH_REASONING_MODE": "disabled",
            "ODYLITH_REASONING_PROVIDER": "auto-local",
            "ODYLITH_REASONING_TIMEOUT_SECONDS": "1",
            "ODYLITH_REASONING_CODEX_BIN": "/usr/bin/false",
            "ODYLITH_REASONING_CLAUDE_BIN": "/usr/bin/false",
        }
    )
    return values


HOST_NATIVE_ARGV_ARGUMENT_COUNT = 1 + len(
    _canonical_host_candidate_tokens(model="", reasoning_effort="", output_schema="")
)
HOST_NATIVE_ARGV_SHAPE_SHA256 = hashlib.sha256(
    json.dumps(
        (
            "exec", "ephemeral", "ignore-user-config", "skip-git-repo-check",
            "sandbox:read-only", "model", "config:model_reasoning_effort",
            "output-schema", "stdin",
        ),
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()


def resolve_trusted_codex_executable(
    *,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve the one PATH-trusted Codex executable used by release proof."""

    values = dict(os.environ if environ is None else environ)
    path_value = str(values.get("PATH") or "")
    located = shutil.which("codex", path=path_value)
    if not located:
        raise ValueError("trusted Codex executable is unavailable")
    trusted = _resolved_executable(located, path_value=path_value)
    configured = str(values.get("ODYLITH_REASONING_CODEX_BIN") or "").strip()
    if configured:
        configured_path = _resolved_executable(configured, path_value=path_value)
        if configured_path != trusted:
            raise ValueError("configured Codex executable does not match the trusted Codex binary")
    return str(trusted)


def qualify_host_candidate_argv(
    value: Sequence[str],
    *,
    trusted_codex_executable: str,
    expected_model: str,
    expected_reasoning_effort: str,
    expected_output_schema: str,
    path_value: str = "",
) -> tuple[tuple[str, ...], dict[str, Any]]:
    """Validate one direct Codex argv and return only a safe derived receipt."""

    argv = tuple(str(argument) for argument in value)
    if not argv or any(not argument for argument in argv):
        raise ValueError("host-native candidate command requires a non-empty argv")
    trusted = _resolved_executable(
        trusted_codex_executable,
        path_value=path_value or str(os.environ.get("PATH") or ""),
    )
    executable = _resolved_executable(
        argv[0],
        path_value=path_value or str(os.environ.get("PATH") or ""),
    )
    if executable != trusted:
        raise ValueError("host-native candidate command must invoke the trusted Codex binary directly")
    tokens = argv[1:]
    expected_tokens = _canonical_host_candidate_tokens(
        model=expected_model,
        reasoning_effort=expected_reasoning_effort,
        output_schema=expected_output_schema,
    )
    if tokens != expected_tokens:
        raise ValueError(
            "host-native candidate command does not match the canonical release argv contract"
        )
    canonical_argv = (str(trusted), *tokens)
    receipt = {
        "version": HOST_NATIVE_ARGV_RECEIPT_VERSION,
        "executable_sha256": _sha256_file(trusted),
        "argument_count": HOST_NATIVE_ARGV_ARGUMENT_COUNT,
        "model": expected_model,
        "reasoning_effort": expected_reasoning_effort,
        "output_schema_present": True,
        "argv_shape_sha256": HOST_NATIVE_ARGV_SHAPE_SHA256,
    }
    return canonical_argv, receipt


def _resolved_executable(value: str, *, path_value: str) -> Path:
    token = str(value or "").strip()
    candidate = Path(token).expanduser()
    located = (
        str(candidate)
        if candidate.is_absolute() or token != candidate.name
        else str(shutil.which(token, path=path_value) or "")
    )
    if not located:
        raise ValueError("host-native candidate executable is unavailable")
    resolved = Path(located).expanduser().resolve()
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise ValueError("host-native candidate executable is not executable")
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolved_host_argv(
    argv: Sequence[str],
    *,
    candidate_schema_path: Path,
) -> tuple[str, ...]:
    return tuple(
        str(argument).replace("{candidate_schema}", str(candidate_schema_path))
        for argument in argv
    )



def _main(argv: Sequence[str]) -> int:
    if tuple(argv) != ("--print-argv-template",):
        raise SystemExit("usage: python -m odylith.runtime.domain_intelligence.greenfield_host_transport --print-argv-template")
    print("\n".join(canonical_host_candidate_argv_template()))
    return 0

if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
