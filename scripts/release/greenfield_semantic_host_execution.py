"""Run one isolated critic and graph author under a pinned Greenfield host profile."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any

from greenfield_semantic_development_evidence import AUTHOR_SEGMENT_VERSION
from greenfield_semantic_development_evidence import build_materiality_critic_input
from greenfield_semantic_development_evidence import build_semantic_graph_author_input
from greenfield_semantic_development_evidence import canonical_sha256
from greenfield_semantic_development_evidence import expected_access_receipt
from greenfield_semantic_development_evidence import exclusive_json
from greenfield_semantic_development_evidence import json_mapping
from greenfield_semantic_development_evidence import require_run_evidence
from greenfield_semantic_development_evidence import run_evidence_sha256
from greenfield_semantic_development_evidence import safe_json_file
from greenfield_semantic_development_evidence import unique_index
from greenfield_semantic_host_execution_contract import HOST_RUNTIME_RECEIPT_VERSION
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    host_execution_profile,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_MANDATORY_CHALLENGES,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    require_semantic_intent_ir,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_schema import (
    semantic_intent_output_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    require_materiality_intent_alignment,
    semantic_materiality_assessment_schema,
    semantic_materiality_assessment_sha256,
)


def author_development_case(
    *,
    corpus_path: Path,
    evidence_plan_path: Path,
    case_id: str,
    output_path: Path,
    host_binaries: Mapping[str, Path] | None = None,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    """Produce one complete two-run segment; fail without retry or partial output."""

    corpus_file = safe_json_file(corpus_path, "development corpus")
    plan_file = safe_json_file(evidence_plan_path, "development evidence plan")
    plan = json_mapping(plan_file, "development evidence plan")
    assignments = unique_index(plan.get("cases", []), "case_id", "development assignments")
    if case_id not in assignments:
        raise RuntimeError(f"development evidence plan does not assign case: {case_id}")
    assignment = assignments[case_id]
    host_profile = str(assignment["critic_assignment"]["host_profile"])
    if assignment["author_assignment"]["host_profile"] != host_profile:
        raise RuntimeError("critic and author host assignments differ")
    binary = _host_binary(host_profile, host_binaries)
    runtime_receipt = _host_runtime_receipt(binary, host_profile=host_profile)

    critic_input = build_materiality_critic_input(
        corpus_path=corpus_file,
        evidence_plan_path=plan_file,
        case_id=case_id,
    )
    assessment, critic_usage, critic_wall_ms = _run_stage(
        stage="critic",
        phase_input=critic_input,
        output_schema=semantic_materiality_assessment_schema(),
        binary=binary,
        host_profile=host_profile,
        timeout_seconds=timeout_seconds,
    )
    author_input = build_semantic_graph_author_input(
        corpus_path=corpus_file,
        evidence_plan_path=plan_file,
        case_id=case_id,
        materiality_assessment=assessment,
    )
    author_output, author_usage, author_wall_ms = _run_stage(
        stage="author",
        phase_input=author_input,
        output_schema=_author_output_schema(),
        binary=binary,
        host_profile=host_profile,
        timeout_seconds=timeout_seconds,
    )
    semantic_intent = _mapping(author_output.get("semantic_intent"), "Semantic Intent")
    self_challenge = _rows(author_output.get("self_challenge"), "author self challenge")
    evidence_sources = _mapping(author_input.get("evidence"), "author evidence")
    verified_intent = require_semantic_intent_ir(
        semantic_intent,
        evidence_sources={key: str(value) for key, value in evidence_sources.items()},
    )
    require_materiality_intent_alignment(assessment, verified_intent)

    materiality_sha256 = semantic_materiality_assessment_sha256(assessment)
    critic_receipt = _run_receipt(
        stage="critic",
        assignment=assignment["critic_assignment"],
        input_value=critic_input,
        output_value=assessment,
        runtime_receipt=runtime_receipt,
        wall_ms=critic_wall_ms,
        token_usage=critic_usage,
    )
    author_receipt = _run_receipt(
        stage="author",
        assignment=assignment["author_assignment"],
        input_value=author_input,
        output_value=author_output,
        runtime_receipt=runtime_receipt,
        wall_ms=author_wall_ms,
        token_usage=author_usage,
        materiality_sha256=materiality_sha256,
        self_challenge=self_challenge,
    )
    outcome = "commit" if verified_intent["status"] == "complete" else "clarify"
    segment = {
        "version": AUTHOR_SEGMENT_VERSION,
        "evidence_plan_sha256": canonical_sha256(plan),
        "cohort_nonce": plan["cohort_nonce"],
        "cases": [
            {
                "case_id": case_id,
                "case_nonce": assignment["case_nonce"],
                "outcome": outcome,
                "critic_stage": {
                    **critic_receipt,
                    "materiality_assessment": assessment,
                },
                "author_stage": {
                    **author_receipt,
                    "semantic_intent": verified_intent,
                },
            }
        ],
    }
    exclusive_json(Path(output_path).expanduser().resolve(), segment)
    return segment


def _run_stage(
    *,
    stage: str,
    phase_input: Mapping[str, Any],
    output_schema: Mapping[str, Any],
    binary: Path,
    host_profile: str,
    timeout_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    profile = host_execution_profile(host_profile)
    if phase_input.get("execution_profile") != profile:
        raise RuntimeError(f"{stage} input changes its assigned execution profile")
    prompt = _stage_prompt(stage=stage, phase_input=phase_input)
    started_ns = time.monotonic_ns()
    with tempfile.TemporaryDirectory(prefix=f"odylith-greenfield-{stage}-") as temporary:
        working_root = Path(temporary)
        if host_profile == "codex":
            output, usage = _run_codex(
                binary=binary,
                profile=profile,
                prompt=prompt,
                output_schema=output_schema,
                working_root=working_root,
                timeout_seconds=timeout_seconds,
            )
        elif host_profile == "claude":
            output, usage = _run_claude(
                binary=binary,
                profile=profile,
                prompt=prompt,
                output_schema=output_schema,
                working_root=working_root,
                timeout_seconds=timeout_seconds,
            )
        else:
            raise RuntimeError("unsupported Greenfield host execution profile")
    wall_ms = max(1, (time.monotonic_ns() - started_ns + 999_999) // 1_000_000)
    return output, usage, wall_ms


def _run_codex(
    *,
    binary: Path,
    profile: Mapping[str, str],
    prompt: str,
    output_schema: Mapping[str, Any],
    working_root: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema_path = working_root / "output-schema.json"
    schema_path.write_text(_json(output_schema), encoding="utf-8")
    command = [
        str(binary),
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--cd",
        str(working_root),
        "--model",
        profile["model"],
        "-c",
        f'model_reasoning_effort="{profile["reasoning_effort"]}"',
        "--json",
        "--output-schema",
        str(schema_path),
        prompt,
    ]
    result = _subprocess(command, working_root=working_root, timeout_seconds=timeout_seconds)
    messages: list[dict[str, Any]] = []
    usage: Mapping[str, Any] | None = None
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        event = _json_mapping(line, "Codex JSONL event")
        event_type = event.get("type")
        if event_type == "item.completed":
            item = _mapping(event.get("item"), "Codex completed item")
            if item.get("type") == "agent_message":
                messages.append(
                    _json_mapping(str(item.get("text") or ""), "Codex structured output")
                )
            elif item.get("type") != "reasoning":
                raise RuntimeError("Codex host emitted a forbidden tool or non-message event")
        elif event_type == "turn.completed":
            if usage is not None:
                raise RuntimeError("Codex host emitted multiple usage receipts")
            usage = _mapping(event.get("usage"), "Codex usage receipt")
        elif event_type not in {"thread.started", "turn.started"}:
            raise RuntimeError("Codex host emitted an unsupported execution event")
    if len(messages) != 1 or usage is None:
        raise RuntimeError("Codex host did not emit one complete structured response")
    input_tokens = _positive_int(usage.get("input_tokens"), "Codex input tokens")
    output_tokens = _positive_int(usage.get("output_tokens"), "Codex output tokens")
    reasoning_tokens = _nonnegative_int(
        usage.get("reasoning_output_tokens", 0), "Codex reasoning tokens"
    )
    measured_output = output_tokens + reasoning_tokens
    return messages[0], _usage(input_tokens, measured_output)


def _run_claude(
    *,
    binary: Path,
    profile: Mapping[str, str],
    prompt: str,
    output_schema: Mapping[str, Any],
    working_root: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    command = [
        str(binary),
        "--print",
        "--safe-mode",
        "--disable-slash-commands",
        "--tools",
        "",
        "--no-session-persistence",
        "--permission-mode",
        "dontAsk",
        "--model",
        profile["model"],
        "--effort",
        profile["reasoning_effort"],
        "--json-schema",
        _json(output_schema),
        "--output-format",
        "json",
        prompt,
    ]
    result = _subprocess(command, working_root=working_root, timeout_seconds=timeout_seconds)
    envelope = _json_mapping(result.stdout, "Claude result envelope")
    if envelope.get("is_error") is True or envelope.get("subtype") not in {None, "success"}:
        raise RuntimeError("Claude host returned an unsuccessful result")
    output = _mapping(envelope.get("structured_output"), "Claude structured output")
    usage = _mapping(envelope.get("usage"), "Claude usage receipt")
    input_tokens = _positive_int(usage.get("input_tokens"), "Claude input tokens")
    output_tokens = _positive_int(usage.get("output_tokens"), "Claude output tokens")
    return output, _usage(input_tokens, output_tokens)


def _run_receipt(
    *,
    stage: str,
    assignment: Mapping[str, Any],
    input_value: Mapping[str, Any],
    output_value: Mapping[str, Any],
    runtime_receipt: Mapping[str, Any],
    wall_ms: int,
    token_usage: Mapping[str, Any],
    materiality_sha256: str = "",
    self_challenge: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "run_nonce": assignment["run_nonce"],
        "run_id": assignment["run_id"],
        "run_assignment_sha256": assignment["run_assignment_sha256"],
        "host_profile": assignment["host_profile"],
        "capability_profile": assignment["capability_profile"],
        "execution_profile": assignment["execution_profile"],
        "host_runtime": dict(runtime_receipt),
        "independent_context": True,
        "attempt_count": 1,
        "validation_error_repair_count": 0,
        "input_sha256": canonical_sha256(input_value),
        "output_sha256": canonical_sha256(output_value),
        "access_receipt": expected_access_receipt(stage),
        "wall_ms": wall_ms,
        "token_usage": dict(token_usage),
    }
    if stage == "author":
        row["materiality_assessment_sha256"] = materiality_sha256
        row["self_challenge"] = [dict(challenge) for challenge in self_challenge]
    row["run_sha256"] = run_evidence_sha256(row)
    return require_run_evidence(
        row,
        stage=stage,
        assignment=assignment,
        expected_input_sha256=row["input_sha256"],
        expected_output_sha256=row["output_sha256"],
        materiality_assessment_sha256=materiality_sha256,
    )


def _author_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["semantic_intent", "self_challenge"],
        "properties": {
            "semantic_intent": semantic_intent_output_schema(),
            "self_challenge": {
                "type": "array",
                "minItems": len(SEMANTIC_INTENT_MANDATORY_CHALLENGES),
                "maxItems": len(SEMANTIC_INTENT_MANDATORY_CHALLENGES),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["challenge", "status"],
                    "properties": {
                        "challenge": {
                            "type": "string",
                            "enum": list(SEMANTIC_INTENT_MANDATORY_CHALLENGES),
                        },
                        "status": {"type": "string", "enum": ["passed", "failed"]},
                    },
                },
            },
        },
    }


def _stage_prompt(*, stage: str, phase_input: Mapping[str, Any]) -> str:
    role = (
        "independent prompt-only materiality critic"
        if stage == "critic"
        else "independent source-grounded semantic graph author"
    )
    return (
        f"Act as the {role}. Work only from CANONICAL_INPUT_JSON below. "
        "Do not use tools, inspect files, browse, read annotations, access prior candidates, "
        "or infer from validator feedback. Copy exact hashes and version strings from the input. "
        "Return only the required structured output. For self-challenges, report failed when the "
        "graph does not actually satisfy the named challenge; never claim a pass to satisfy a gate.\n"
        f"CANONICAL_INPUT_JSON\n{_json(phase_input)}"
    )


def _host_binary(
    host_profile: str, host_binaries: Mapping[str, Path] | None
) -> Path:
    supplied = host_binaries.get(host_profile) if host_binaries else None
    candidate = Path(supplied) if supplied is not None else Path(
        shutil.which("codex" if host_profile == "codex" else "claude") or ""
    )
    if not str(candidate) or not candidate.expanduser().resolve().is_file():
        raise RuntimeError(f"{host_profile} host executable is unavailable")
    return candidate.expanduser().resolve()


def _host_runtime_receipt(binary: Path, *, host_profile: str) -> dict[str, Any]:
    result = subprocess.run(
        [str(binary), "--version"],
        cwd=str(binary.parent),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("host runtime version probe failed")
    return {
        "version": HOST_RUNTIME_RECEIPT_VERSION,
        "host_profile": host_profile,
        "runtime_name": "codex-cli" if host_profile == "codex" else "claude-code",
        "runtime_version": result.stdout.strip(),
        "runtime_binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
    }


def _subprocess(
    command: Sequence[str], *, working_root: Path, timeout_seconds: int
) -> subprocess.CompletedProcess[str]:
    if timeout_seconds <= 0:
        raise RuntimeError("host execution timeout must be positive")
    try:
        result = subprocess.run(
            list(command),
            cwd=str(working_root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("host execution exceeded its one-attempt timeout") from error
    if result.returncode != 0:
        detail = "\n".join(
            part for part in (result.stderr.strip(), result.stdout.strip()) if part
        )[-2000:]
        raise RuntimeError(f"host execution failed without retry: {detail}")
    return result


def _usage(input_tokens: int, output_tokens: int) -> dict[str, Any]:
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "measurement_basis": "host_runtime_usage_receipt",
    }


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RuntimeError(f"{label} must be a positive integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"{label} must be a non-negative integer")
    return value


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a JSON object")
    return dict(value)


def _rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise RuntimeError(f"{label} must be a JSON object array")
    return [dict(row) for row in value]


def _json_mapping(value: str, label: str) -> dict[str, Any]:
    try:
        return _mapping(json.loads(value), label)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{label} is not valid JSON") from error


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--evidence-plan", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--codex-bin", type=Path)
    parser.add_argument("--claude-bin", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    args = parser.parse_args(argv)
    host_binaries = {
        host: path
        for host, path in (("codex", args.codex_bin), ("claude", args.claude_bin))
        if path is not None
    }
    author_development_case(
        corpus_path=args.corpus,
        evidence_plan_path=args.evidence_plan,
        case_id=args.case_id,
        output_path=args.output,
        host_binaries=host_binaries,
        timeout_seconds=args.timeout_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
