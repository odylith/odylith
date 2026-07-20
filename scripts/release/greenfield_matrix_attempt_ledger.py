"""Fsync individual matrix-case identities before installed execution begins."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from greenfield_matrix_types import GreenfieldMatrixResult
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase


ATTEMPT_LEDGER_VERSION = "odylith.greenfield.matrix.attempt-ledger.v1"


class MatrixAttemptLedger:
    """Append case lifecycle records that survive a child matrix-process failure."""

    def __init__(self, path: Path | None) -> None:
        self._path = Path(path).expanduser().resolve() if path else None
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path | None:
        return self._path

    def ensure_planned(self, cases: Sequence[GreenfieldMatrixCase]) -> None:
        """Persist every exact case identity before any case can be launched."""

        existing = _planned_case_ids(self._path)
        for index, case in enumerate(cases, start=1):
            identity = _case_identity(case)
            case_id = str(identity.get("id") or "")
            if case_id and case_id in existing:
                continue
            self._append("case_planned", {"index": index, "case": identity})
            if case_id:
                existing.add(case_id)

    def record_started(self, *, case: GreenfieldMatrixCase, index: int, total: int) -> None:
        self._append(
            "case_started",
            {"index": int(index), "total": int(total), "case": _case_identity(case)},
        )

    def record_completed(self, result: GreenfieldMatrixResult) -> None:
        evidence = result.evidence if isinstance(result.evidence, Mapping) else {}
        case = evidence.get("case") if isinstance(evidence.get("case"), Mapping) else {}
        self._append(
            "case_completed",
            {
                "case": _identity_from_case_evidence(case),
                "status": str(result.status),
                "quality_passed": bool(result.quality.passed),
                "create_returncode": int(result.create_returncode),
            },
        )

    def _append(self, event: str, payload: Mapping[str, Any]) -> None:
        if self._path is None:
            return
        row = {"version": ATTEMPT_LEDGER_VERSION, "event": event, **dict(payload)}
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def initialize_attempt_ledger(path: Path, cases: Sequence[GreenfieldMatrixCase]) -> Path:
    """Create the durable planned-case inventory used for individual replay."""

    ledger = MatrixAttemptLedger(path)
    ledger.ensure_planned(cases)
    return Path(ledger.path or path)


def replay_case_identities(
    path: Path | None,
    *,
    include_unstarted: bool = False,
) -> tuple[dict[str, Any], ...]:
    """Return failed or started case identities; unstarted plans are not exact replay evidence."""

    states: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in _rows(path):
        case = _mapping(row.get("case"))
        case_id = str(case.get("id") or "").strip()
        if not case_id:
            continue
        if row.get("event") == "case_planned":
            if case_id not in states:
                states[case_id] = {"case": case, "state": "planned"}
                order.append(case_id)
            continue
        state = states.get(case_id)
        if state is None:
            state = {"case": case, "state": "planned"}
            states[case_id] = state
            order.append(case_id)
        if row.get("event") == "case_started":
            state["state"] = "started"
        elif row.get("event") == "case_completed":
            passed = row.get("status") == "passed" and row.get("quality_passed") is True
            state["state"] = "passed" if passed else "failed"

    return tuple(
        {**_mapping(states[case_id].get("case")), "attempt_state": str(states[case_id].get("state") or "planned")}
        for case_id in order
        if states[case_id].get("state") in {"failed", "started"}
        or (include_unstarted and states[case_id].get("state") == "planned")
    )


def _planned_case_ids(path: Path | None) -> set[str]:
    return {
        str(_mapping(row.get("case")).get("id") or "").strip()
        for row in _rows(path)
        if row.get("event") == "case_planned" and str(_mapping(row.get("case")).get("id") or "").strip()
    }


def _rows(path: Path | None) -> tuple[dict[str, Any], ...]:
    if path is None:
        return ()
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    rows: list[dict[str, Any]] = []
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, Mapping) and row.get("version") == ATTEMPT_LEDGER_VERSION:
            rows.append(dict(row))
    return tuple(rows)


def _case_identity(case: GreenfieldMatrixCase) -> dict[str, Any]:
    identity = {
        "id": str(getattr(case, "case_id", "") or case.slug),
        "prompt_sha256": _sha256_text(getattr(case, "prompt", "")),
    }
    confirmed_intent = str(getattr(case, "confirmed_intent_markdown", "") or "").strip()
    if confirmed_intent:
        identity["confirmed_intent_sha256"] = _sha256_text(confirmed_intent)
    return identity


def _identity_from_case_evidence(case: Mapping[str, Any]) -> dict[str, Any]:
    identity = {
        key: str(case.get(key) or "").strip()
        for key in ("id", "prompt_sha256", "confirmed_intent_sha256")
        if str(case.get(key) or "").strip()
    }
    return identity


def _sha256_text(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "ATTEMPT_LEDGER_VERSION",
    "MatrixAttemptLedger",
    "initialize_attempt_ledger",
    "replay_case_identities",
]
