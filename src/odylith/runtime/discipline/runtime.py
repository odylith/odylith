"""Expose compact runtime summary surfaces for the discipline family.

These helpers are used when other packets or CLI surfaces need a small,
stable description of the discipline proof path without executing the full
validator or benchmark on every call.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common.value_coercion import mapping_copy as _mapping
from odylith.runtime.discipline import contract
from odylith.runtime.governance import validate_discipline


RUNTIME_SUMMARY_CONTRACT = "odylith_discipline_runtime_summary.v1"
DISCIPLINE_SUMMARY_KEY = "discipline_summary"
VALIDATION_COMMAND = "odylith validate discipline --repo-root ."
BENCHMARK_COMMAND = "odylith benchmark --profile quick --family discipline --no-write-report --json"
PATH_MARKERS: tuple[str, ...] = (
    "discipline-evaluation-corpus.v1.json",
    "validate_discipline.py",
    "discipline",
    "odylith-discipline",
    "runtime/discipline",
)


def _strings(*values: Any, limit: int = 16) -> list[str]:
    """Collect unique string tokens from mixed scalar/sequence inputs."""
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


def _file_fingerprint(path: Path) -> str:
    """Return a short content fingerprint for an existing file."""
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _relevant_text(values: Sequence[Any]) -> str:
    """Collapse candidate path/doc inputs into one lowercase search string."""
    return "\n".join(_strings(*values, limit=48)).lower()


def should_attach_summary(
    *,
    family_hint: str = "",
    changed_paths: Sequence[Any] = (),
    explicit_paths: Sequence[Any] = (),
    docs: Sequence[Any] = (),
    recommended_commands: Sequence[Any] = (),
) -> bool:
    """Decide whether a packet should carry a discipline runtime summary."""
    family = str(family_hint or "").strip().lower().replace("-", "_")
    if family == contract.FAMILY:
        return True
    # Marker matching is intentionally broad because packets may mention the
    # family indirectly through paths, docs, or recommended commands.
    text = _relevant_text([changed_paths, explicit_paths, docs, recommended_commands])
    return any(marker in text for marker in PATH_MARKERS)


def compact_summary(value: Any, *, limit: int = 6) -> dict[str, Any]:
    """Reduce a rich runtime summary to the small packet-safe subset."""
    summary = _mapping(value)
    if not summary:
        return {}
    hot_path = _mapping(summary.get("hot_path_contract"))
    learning = _mapping(summary.get("learning_contract"))
    return {
        key: payload
        for key, payload in {
            "contract": str(summary.get("contract", "")).strip(),
            "decision_contract": str(summary.get("decision_contract", "")).strip(),
            "learning_contract": {
                "contract": str(learning.get("contract", "")).strip(),
                "retention_classes": _strings(learning.get("retention_classes"), limit=limit),
                "durable_learning_gate": str(learning.get("durable_learning_gate", "")).strip(),
            }
            if learning
            else {},
            "runtime_budget_contract": str(summary.get("runtime_budget_contract", "")).strip(),
            "family": str(summary.get("family", "")).strip(),
            "status": str(summary.get("status", "")).strip(),
            "validation_status": str(summary.get("validation_status", "")).strip(),
            "case_count": int(summary.get("case_count", 0) or 0),
            "selected_case_ids": _strings(summary.get("selected_case_ids"), limit=limit),
            "validator_command": str(summary.get("validator_command", "")).strip(),
            "benchmark_command": str(summary.get("benchmark_command", "")).strip(),
            "corpus_fingerprint": str(summary.get("corpus_fingerprint", "")).strip(),
            "source_refs": _strings(summary.get("source_refs"), limit=limit),
            "hot_path_contract": {
                key: hot_path.get(key)
                for key in (
                    "provider_calls",
                    "host_model_calls",
                    "subagent_spawn",
                    "broad_scan",
                    "projection_expansion",
                    "full_validation",
                    "benchmark_execution",
                )
                if key in hot_path
            }
            if hot_path
            else {},
        }.items()
        if payload not in ("", [], {}, None, 0)
    }


def summary_from_sources(*sources: Any, limit: int = 6) -> dict[str, Any]:
    """Extract the first usable discipline summary from nested source payloads."""
    for source in sources:
        row = _mapping(source)
        if not row:
            continue
        nested = _mapping(row.get(DISCIPLINE_SUMMARY_KEY))
        for candidate in (nested, row):
            summary = compact_summary(candidate, limit=limit)
            if summary:
                return summary
    return {}


def validator_command_from_sources(*sources: Any) -> str:
    """Return the validator command from the first embedded discipline summary."""
    return str(summary_from_sources(*sources).get("validator_command", "")).strip()


def commands_with_validator(commands: Sequence[Any], summary: Mapping[str, Any], *, limit: int = 16) -> list[str]:
    """Append the validator command to a command list when it is not already present."""
    rows = _strings(commands, limit=limit)
    command = str(summary.get("validator_command", "")).strip()
    if command and command not in rows:
        rows.append(command)
    return rows[:limit]


def runtime_summary(
    *,
    repo_root: Path,
    case_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a local summary of the available discipline proof surface."""
    root = Path(repo_root).expanduser().resolve()
    corpus_path = root / validate_discipline.CORPUS_RELATIVE_PATH
    cases: list[dict[str, Any]] = []
    status = "unavailable"
    try:
        # Selection is reused here so the summary reflects the same case slicing
        # semantics as the validator, without claiming that validation has run.
        cases = validate_discipline.load_discipline_cases(repo_root=root)
        selected, issues = validate_discipline._select_cases(cases, case_ids=case_ids)  # noqa: SLF001
        cases = selected if not issues else []
        status = "available" if cases else "unavailable"
    except (OSError, ValueError):
        cases = []
    selected_ids = _strings([case.get("id") for case in cases], limit=12)
    return {
        "contract": RUNTIME_SUMMARY_CONTRACT,
        "decision_contract": contract.DISCIPLINE_CONTRACT,
        "learning_contract": {
            "contract": contract.LEARNING_CONTRACT,
            "retention_classes": list(contract.RETENTION_CLASSES),
            "durable_learning_gate": "validator_benchmark_or_tribunal",
        },
        "runtime_budget_contract": contract.RUNTIME_BUDGET_CONTRACT,
        "family": contract.FAMILY,
        "status": status,
        "validation_status": "not_run",
        "case_count": len(cases),
        "selected_case_ids": selected_ids,
        "validator_command": VALIDATION_COMMAND,
        "benchmark_command": BENCHMARK_COMMAND,
        "repo_relative_corpus_path": str(validate_discipline.CORPUS_RELATIVE_PATH),
        "repo_relative_bundle_corpus_path": str(validate_discipline.BUNDLE_CORPUS_RELATIVE_PATH),
        "corpus_fingerprint": _file_fingerprint(corpus_path),
        "source_refs": [
            str(validate_discipline.CORPUS_RELATIVE_PATH),
            "src/odylith/runtime/governance/validate_discipline.py",
            "src/odylith/runtime/discipline",
        ],
        "hot_path_contract": {
            "provider_calls": False,
            "host_model_calls": False,
            "subagent_spawn": False,
            "broad_scan": False,
            "projection_expansion": False,
            "full_validation": False,
            "benchmark_execution": False,
        },
    }


def summary_for_packet(
    *,
    repo_root: Path,
    family_hint: str = "",
    changed_paths: Sequence[Any] = (),
    explicit_paths: Sequence[Any] = (),
    docs: Sequence[Any] = (),
    recommended_commands: Sequence[Any] = (),
) -> dict[str, Any]:
    """Return a compact runtime summary only when the packet actually needs it."""
    if not should_attach_summary(
        family_hint=family_hint,
        changed_paths=changed_paths,
        explicit_paths=explicit_paths,
        docs=docs,
        recommended_commands=recommended_commands,
    ):
        return {}
    return compact_summary(runtime_summary(repo_root=repo_root), limit=6)
