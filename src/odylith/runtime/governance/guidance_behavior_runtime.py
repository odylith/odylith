"""Low-latency runtime helpers for Guidance Behavior evidence."""

from __future__ import annotations

import hashlib
import shlex
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.contracts.severity import VALID_SEVERITIES
from odylith.runtime.common.value_coercion import mapping_copy as _mapping
from odylith.runtime.governance import guidance_behavior_platform_contracts
from odylith.runtime.governance import guidance_behavior_guidance_contracts
from odylith.runtime.governance import guidance_behavior_runtime_contracts
from odylith.runtime.governance import validate_guidance_behavior


RUNTIME_SUMMARY_CONTRACT = "odylith_guidance_behavior_runtime_summary.v1"
GUIDANCE_BEHAVIOR_SUMMARY_KEY = "guidance_behavior_summary"
VALIDATION_COMMAND = "odylith validate guidance-behavior --repo-root ."
PATH_MARKERS: tuple[str, ...] = (
    "guidance-behavior-evaluation-corpus.v1.json",
    "validate_guidance_behavior.py",
    "guidance_behavior",
    "odylith-guidance-behavior",
)


def _strings(*values: Any, limit: int = 16) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str):
            candidates = [value]
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            candidates = list(value)
        else:
            candidates = []
        for item in candidates:
            token = str(item or "").strip()
            if not token or token in seen:
                continue
            seen.add(token)
            rows.append(token)
            if len(rows) >= max(1, int(limit)):
                return rows
    return rows
def compact_summary(value: Any, *, limit: int = 6) -> dict[str, Any]:
    """Compact a Guidance Behavior summary for packet, memory, and transcript flow."""

    summary = _mapping(value)
    if not summary:
        return {}
    tribunal_signal = _mapping(summary.get("tribunal_signal"))
    runtime_layer_contract = _mapping(summary.get("runtime_layer_contract"))
    guidance_surface_contract = _mapping(summary.get("guidance_surface_contract"))
    platform_contract = _mapping(summary.get("platform_contract"))
    return {
        key: payload
        for key, payload in {
            "contract": str(summary.get("contract", "")).strip(),
            "validation_contract": str(summary.get("validation_contract", "")).strip(),
            "family": str(summary.get("family", "")).strip(),
            "status": str(summary.get("status", "")).strip(),
            "validation_status": str(summary.get("validation_status", "")).strip(),
            "case_count": int(summary.get("case_count", 0) or 0),
            "critical_or_high_case_count": int(summary.get("critical_or_high_case_count", 0) or 0),
            "selected_case_ids": _strings(summary.get("selected_case_ids"), limit=limit),
            "severity_counts": _mapping(summary.get("severity_counts")),
            "related_guidance_refs": _strings(summary.get("related_guidance_refs"), limit=limit),
            "failed_check_ids": _strings(summary.get("failed_check_ids"), limit=limit),
            "validator_command": str(summary.get("validator_command", "")).strip(),
            "case_validation_commands": _strings(summary.get("case_validation_commands"), limit=limit),
            "corpus_fingerprint": str(summary.get("corpus_fingerprint", "")).strip(),
            "source_refs": _strings(summary.get("source_refs"), limit=limit),
            "hot_path_contract": _mapping(summary.get("hot_path_contract")),
            "runtime_layer_contract": {
                contract_key: contract_value
                for contract_key, contract_value in {
                    "contract": str(runtime_layer_contract.get("contract", "")).strip(),
                    "layers": _strings(runtime_layer_contract.get("layers"), limit=limit),
                    "source_refs": _strings(runtime_layer_contract.get("source_refs"), limit=limit),
                    "hot_path": _mapping(runtime_layer_contract.get("hot_path")),
                }.items()
                if contract_value not in ("", [], {}, None)
            }
            if runtime_layer_contract
            else {},
            "guidance_surface_contract": {
                contract_key: contract_value
                for contract_key, contract_value in {
                    "contract": str(guidance_surface_contract.get("contract", "")).strip(),
                    "hosts": _strings(guidance_surface_contract.get("hosts"), limit=limit),
                    "lanes": _strings(guidance_surface_contract.get("lanes"), limit=limit),
                    "source_refs": _strings(guidance_surface_contract.get("source_refs"), limit=limit),
                    "hot_path": _mapping(guidance_surface_contract.get("hot_path")),
                }.items()
                if contract_value not in ("", [], {}, None)
            }
            if guidance_surface_contract
            else {},
            "platform_contract": {
                contract_key: contract_value
                for contract_key, contract_value in {
                    "contract": str(platform_contract.get("contract", "")).strip(),
                    "domains": _strings(platform_contract.get("domains"), limit=limit),
                    "source_refs": _strings(platform_contract.get("source_refs"), limit=limit),
                    "hot_path": _mapping(platform_contract.get("hot_path")),
                }.items()
                if contract_value not in ("", [], {}, None)
            }
            if platform_contract
            else {},
            "tribunal_signal": {
                signal_key: signal_value
                for signal_key, signal_value in {
                    "scope_type": str(tribunal_signal.get("scope_type", "")).strip(),
                    "scope_id": str(tribunal_signal.get("scope_id", "")).strip(),
                    "scope_label": str(tribunal_signal.get("scope_label", "")).strip(),
                    "operator_readout": _mapping(tribunal_signal.get("operator_readout")),
                }.items()
                if signal_value not in ("", [], {}, None)
            }
            if tribunal_signal
            else {},
        }.items()
        if payload not in ("", [], {}, None, 0)
    }


def summary_from_sources(*sources: Any, limit: int = 6) -> dict[str, Any]:
    """Return the first compact Guidance Behavior summary found in local payloads."""

    for source in sources:
        row = _mapping(source)
        if not row:
            continue
        nested = _mapping(row.get(GUIDANCE_BEHAVIOR_SUMMARY_KEY))
        for candidate in (nested, row):
            summary = compact_summary(candidate, limit=limit)
            if summary:
                return summary
    return {}


def validator_command_from_sources(*sources: Any) -> str:
    """Return the validator command from the first local Guidance Behavior summary."""

    return str(summary_from_sources(*sources).get("validator_command", "")).strip()


def _file_fingerprint(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _severity_counts(cases: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {severity: 0 for severity in sorted(VALID_SEVERITIES)}
    for case in cases:
        severity = str(case.get("severity", "")).strip().lower()
        if severity in counts:
            counts[severity] += 1
    return {key: value for key, value in counts.items() if value}


def _selected_case_ids(cases: Sequence[Mapping[str, Any]]) -> list[str]:
    return _strings([case.get("id") for case in cases], limit=12)


def _related_guidance_refs(cases: Sequence[Mapping[str, Any]]) -> list[str]:
    refs: list[Any] = []
    for case in cases:
        value = case.get("related_guidance_refs", [])
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            refs.extend(value)
    return _strings(refs, limit=12)


def _case_validation_commands(cases: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        f"{VALIDATION_COMMAND} --case-id {case_id}"
        for case_id in _selected_case_ids(cases)[:4]
        if case_id
    ]


def _case_ids_from_commands(commands: Sequence[str]) -> list[str]:
    case_ids: list[str] = []
    for command in _strings(commands, limit=24):
        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()
        for index, part in enumerate(parts):
            if part == "--case-id" and index + 1 < len(parts):
                case_ids.append(parts[index + 1])
            elif part.startswith("--case-id="):
                case_ids.append(part.split("=", 1)[1])
    return _strings(case_ids, limit=12)


def _select_cases(
    cases: Sequence[Mapping[str, Any]],
    *,
    case_ids: Sequence[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    selected_ids = _strings(case_ids, limit=32)
    if not selected_ids:
        return [dict(case) for case in cases], []
    by_id = {str(case.get("id", "")).strip(): dict(case) for case in cases if str(case.get("id", "")).strip()}
    missing = [case_id for case_id in selected_ids if case_id not in by_id]
    if missing:
        return [], [
            {
                "check_id": "case_selection",
                "message": f"unknown guidance behavior case id(s): {', '.join(sorted(missing))}",
            }
        ]
    return [by_id[case_id] for case_id in selected_ids], []


def guidance_behavior_runtime_summary(
    *,
    repo_root: Path,
    case_ids: Sequence[str] = (),
    include_validation: bool = False,
) -> dict[str, Any]:
    """Return a compact local summary for Context/Execution hot paths."""

    root = Path(repo_root).expanduser().resolve()
    corpus_path = root / validate_guidance_behavior.CORPUS_RELATIVE_PATH
    payload: dict[str, Any] = {
        "contract": RUNTIME_SUMMARY_CONTRACT,
        "validation_contract": validate_guidance_behavior.CONTRACT,
        "family": validate_guidance_behavior.EXPECTED_FAMILY,
        "status": "unavailable",
        "validation_status": "not_run",
        "repo_relative_corpus_path": str(validate_guidance_behavior.CORPUS_RELATIVE_PATH),
        "repo_relative_bundle_corpus_path": str(validate_guidance_behavior.BUNDLE_CORPUS_RELATIVE_PATH),
        "corpus_fingerprint": _file_fingerprint(corpus_path),
        "validator_command": VALIDATION_COMMAND,
        "source_refs": [
            str(validate_guidance_behavior.CORPUS_RELATIVE_PATH),
            "src/odylith/runtime/governance/validate_guidance_behavior.py",
        ],
        "hot_path_contract": {
            "provider_calls": False,
            "repo_wide_scan": False,
            "context_store_expansion": False,
            "full_guidance_validation": bool(include_validation),
        },
        "runtime_layer_contract": guidance_behavior_runtime_contracts.runtime_layer_contract_summary(),
        "guidance_surface_contract": guidance_behavior_guidance_contracts.guidance_surface_contract_summary(),
        "platform_contract": guidance_behavior_platform_contracts.platform_contract_summary(),
        "case_count": 0,
        "selected_case_ids": [],
        "severity_counts": {},
        "critical_or_high_case_count": 0,
        "related_guidance_refs": [],
        "case_validation_commands": [],
        "failed_check_ids": [],
        "error_count": 0,
    }
    try:
        cases = validate_guidance_behavior.load_guidance_behavior_cases(repo_root=root)
        selected_cases, selection_errors = _select_cases(cases, case_ids=case_ids)
        if selection_errors:
            payload["status"] = "malformed"
            payload["error_count"] = len(selection_errors)
            payload["failed_check_ids"] = _strings([issue.get("check_id") for issue in selection_errors], limit=4)
            payload["errors"] = selection_errors[:4]
            return payload
    except validate_guidance_behavior.CorpusStateError as exc:
        payload["status"] = exc.status
        payload["error_count"] = 1
        payload["failed_check_ids"] = ["corpus_state"]
        payload["errors"] = [
            {
                "check_id": "corpus_state",
                "message": str(exc),
                "path": str(exc.path or corpus_path),
            }
        ]
        return payload

    severity_counts = _severity_counts(selected_cases)
    payload.update(
        {
            "status": "available",
            "case_count": len(selected_cases),
            "selected_case_ids": _selected_case_ids(selected_cases),
            "severity_counts": severity_counts,
            "critical_or_high_case_count": int(severity_counts.get("critical", 0) or 0)
            + int(severity_counts.get("high", 0) or 0),
            "related_guidance_refs": _related_guidance_refs(selected_cases),
            "case_validation_commands": _case_validation_commands(selected_cases),
            "tribunal_signal": {
                "scope_type": "component",
                "scope_id": "governance-intervention-engine",
                "scope_label": "Guidance Behavior Contract",
                "operator_readout": {
                    "severity": "info",
                    "issue": "Guidance behavior pressure cases are available as governed local evidence.",
                    "action": "Use the validator command for proof before claiming guidance behavior is passing.",
                },
            },
        }
    )
    if include_validation:
        validation = validate_guidance_behavior.validate_guidance_behavior(repo_root=root, case_ids=case_ids)
        validation_status = str(validation.get("status", "")).strip() or "unknown"
        failed_check_ids = _strings(
            [
                error.get("check_id")
                for error in validation.get("errors", [])
                if isinstance(error, Mapping)
            ],
            limit=8,
        )
        payload["status"] = validation_status
        payload["validation_status"] = validation_status
        payload["failed_check_ids"] = failed_check_ids
        payload["error_count"] = len(
            [error for error in validation.get("errors", []) if isinstance(error, Mapping)]
        )
        if validation_status != "passed":
            payload["errors"] = [
                dict(error)
                for error in validation.get("errors", [])[:4]
                if isinstance(error, Mapping)
            ]
            tribunal_signal = dict(payload.get("tribunal_signal", {}))
            readout = dict(tribunal_signal.get("operator_readout", {}))
            readout["severity"] = "p1"
            readout["issue"] = "Guidance behavior validation is not passing."
            readout["action"] = "Fix or scope the failing guidance contract before treating the guidance layer as proof-backed."
            tribunal_signal["operator_readout"] = readout
            payload["tribunal_signal"] = tribunal_signal
    return {
        key: value
        for key, value in payload.items()
        if value not in ("", [], {}, None, 0)
    }


def guidance_behavior_relevant(
    *,
    family_hint: str,
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str],
    docs: Sequence[str],
    recommended_commands: Sequence[str],
) -> bool:
    """Return true when a packet should carry Guidance Behavior evidence."""

    family = str(family_hint or "").strip()
    if family == validate_guidance_behavior.EXPECTED_FAMILY:
        return True
    path_tokens = _strings(changed_paths, explicit_paths, docs, limit=48)
    if family == "broad_shared_scope" and any(
        token == "AGENTS.md" or token.endswith("/AGENTS.md") or "agents-guidelines/" in token
        for token in path_tokens
    ):
        return True
    if any(any(marker in token for marker in PATH_MARKERS) for token in path_tokens):
        return True
    command_blob = "\n".join(_strings(recommended_commands, limit=24))
    return bool(
        ("validate guidance-behavior" in command_blob or "validate-guidance-behavior" in command_blob)
        and "--case-id" in command_blob
    )


def summary_for_packet(
    *,
    repo_root: Path,
    family_hint: str,
    changed_paths: Sequence[str],
    explicit_paths: Sequence[str],
    docs: Sequence[str],
    recommended_commands: Sequence[str],
) -> dict[str, Any]:
    """Return the compact runtime summary only for relevant packets."""

    if not guidance_behavior_relevant(
        family_hint=family_hint,
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
        docs=docs,
        recommended_commands=recommended_commands,
    ):
        return {}
    case_ids = _case_ids_from_commands(recommended_commands)
    return guidance_behavior_runtime_summary(
        repo_root=repo_root,
        case_ids=case_ids,
        include_validation=False,
    )


def commands_with_validator(
    recommended_commands: Any,
    summary: Mapping[str, Any],
    *,
    limit: int = 16,
) -> list[str]:
    """Append the validator command once when a Guidance Behavior summary exists."""

    if not isinstance(summary, Mapping) or not summary:
        return _strings(recommended_commands, limit=limit)
    return _strings(
        recommended_commands,
        summary.get("case_validation_commands"),
        summary.get("validator_command"),
        limit=limit,
    )


__all__ = [
    "commands_with_validator",
    "compact_summary",
    "GUIDANCE_BEHAVIOR_SUMMARY_KEY",
    "guidance_behavior_relevant",
    "guidance_behavior_runtime_summary",
    "summary_from_sources",
    "summary_for_packet",
    "validator_command_from_sources",
]
