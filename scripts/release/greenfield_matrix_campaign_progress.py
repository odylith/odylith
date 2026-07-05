"""Merged progress telemetry for tiered Greenfield matrix campaigns."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
import time
from threading import Lock
from typing import Any
from typing import TextIO
from typing import Mapping

CAMPAIGN_PROGRESS_VERSION = "odylith.greenfield.matrix.campaign-progress.v1"


class CampaignProgressWriter:
    """Merge shard JSONL telemetry into append-only campaign progress files."""

    def __init__(
        self,
        *,
        jsonl_path: Path,
        snapshot_path: Path,
        stream_progress: bool = False,
        stream: TextIO | None = None,
    ) -> None:
        self._jsonl_path = Path(jsonl_path).expanduser().resolve()
        self._snapshot_path = Path(snapshot_path).expanduser().resolve()
        self._stream_progress = bool(stream_progress)
        self._stream = stream or sys.stderr
        self._lock = Lock()
        self._started = time.perf_counter()
        self._state: dict[str, Any] = {
            "version": CAMPAIGN_PROGRESS_VERSION,
            "status": "running",
            "seconds": 0.0,
            "selected_shard_count": 0,
            "started_shard_count": 0,
            "started_case_count": 0,
            "completed_shard_count": 0,
            "completed_case_count": 0,
            "passed_case_count": 0,
            "failed_case_count": 0,
            "running_shards": [],
            "running_cases": [],
            "cluster_counts": {},
            "tiers": {},
            "last_event": {},
        }
        self._running_shards: set[str] = set()
        self._running_cases: dict[str, dict[str, Any]] = {}
        self._cluster_counts: Counter[str] = Counter()
        self._shard_case_counts: dict[str, Counter[str]] = {}
        self._shard_cluster_counts: dict[str, Counter[str]] = {}
        self._shard_failed_cases: dict[str, list[dict[str, Any]]] = {}
        self._tier_last_failed_shard: dict[str, str] = {}
        self._tier_cluster_origin_shards: dict[str, dict[str, str]] = {}
        self._tier_stop_decisions: dict[str, dict[str, Any]] = {}
        self._tier_stop_emitted: set[str] = set()
        self._jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self._jsonl_path.write_text("", encoding="utf-8")

    @property
    def jsonl_path(self) -> Path:
        return self._jsonl_path

    @property
    def snapshot_path(self) -> Path:
        return self._snapshot_path

    def emit(self, event: str, payload: dict[str, Any]) -> None:
        with self._lock:
            row = {
                "version": CAMPAIGN_PROGRESS_VERSION,
                "event": str(event),
                "emitted_at_epoch": round(time.time(), 3),
                **dict(payload),
            }
            self._apply(row)
            row["aggregate"] = self._snapshot()
            with self._jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            self._snapshot_path.write_text(
                json.dumps(self._snapshot(), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self._stream_row(row)

    def _stream_row(self, row: Mapping[str, Any]) -> None:
        if not self._stream_progress:
            return
        line = progress_console_line(row)
        if not line:
            return
        print(line, file=self._stream, flush=True)

    def forward_shard_telemetry(self, *, shard: Any, row: dict[str, Any]) -> None:
        event = str(row.get("event") or "").strip() or "telemetry"
        payload = {
            "tier": str(getattr(shard, "tier", "")),
            "shard": str(getattr(shard, "name", "")),
            "case_file": str(getattr(shard, "case_file", "")),
            "matrix_event": event,
            "matrix_telemetry": row,
        }
        if event == "case_started":
            self.emit("case_started", payload)
        elif event == "case_completed":
            self.emit("case_completed", payload)
        elif event == "run_stopped":
            self.emit("shard_run_stopped", payload)
        elif event == "run_finished":
            self.emit("shard_run_finished", payload)
        else:
            self.emit("shard_telemetry", payload)

    def tier_stop_decision(
        self,
        *,
        tier: str,
        current_shard: str,
        stop_after_failures: int,
        stop_after_cluster_failures: int,
    ) -> dict[str, Any]:
        with self._lock:
            existing = self._tier_stop_decisions.get(tier)
            if existing:
                return dict(existing)
            tier_state = _mapping(self._state.get("tiers", {}).get(tier))
            failed_case_count = int(tier_state.get("failed_case_count") or 0)
            reason = ""
            origin_shard = ""
            if stop_after_failures and failed_case_count >= stop_after_failures:
                reason = f"failure-threshold:{stop_after_failures}:live-telemetry"
                origin_shard = self._tier_last_failed_shard.get(tier, "")
            if stop_after_cluster_failures and not reason:
                cluster, count = first_cluster_at_threshold(
                    Counter(_mapping(tier_state.get("cluster_counts"))),
                    stop_after_cluster_failures,
                )
                if cluster:
                    reason = f"cluster-threshold:{cluster}:{count}:live-telemetry"
                    origin_shard = self._tier_cluster_origin_shards.get(tier, {}).get(cluster, "")
            if not reason:
                return {}
            decision = {
                "tier": tier,
                "reason": reason,
                "origin_shard": origin_shard or current_shard,
                "failed_case_count": failed_case_count,
                "cluster_counts": dict(_mapping(tier_state.get("cluster_counts"))),
            }
            self._tier_stop_decisions[tier] = decision
            return dict(decision)

    def tier_failure_snapshot(self, *, tier: str) -> dict[str, Any]:
        with self._lock:
            tier_state = _mapping(self._state.get("tiers", {}).get(tier))
            return {
                "failed_case_count": int(tier_state.get("failed_case_count") or 0),
                "completed_case_count": int(tier_state.get("completed_case_count") or 0),
                "cluster_counts": dict(_mapping(tier_state.get("cluster_counts"))),
                "status": str(tier_state.get("status") or ""),
                "stop_reason": str(tier_state.get("stop_reason") or ""),
            }

    def shard_failure_snapshot(self, *, shard: str) -> dict[str, Any]:
        with self._lock:
            shard_name = str(shard or "").strip()
            counts = self._shard_case_counts.get(shard_name, Counter())
            clusters = self._shard_cluster_counts.get(shard_name, Counter())
            return {
                "shard": shard_name,
                "completed_case_count": int(counts.get("completed") or 0),
                "failed_case_count": int(counts.get("failed") or 0),
                "cluster_counts": dict(sorted(clusters.items())),
                "failed_cases": list(self._shard_failed_cases.get(shard_name, ())),
            }

    def mark_tier_stop_emitted(self, tier: str) -> bool:
        with self._lock:
            if tier in self._tier_stop_emitted:
                return False
            self._tier_stop_emitted.add(tier)
            return True

    def _apply(self, row: dict[str, Any]) -> None:
        event = str(row.get("event") or "")
        tier = str(row.get("tier") or "")
        shard = str(row.get("shard") or "")
        if tier:
            self._state.setdefault("tiers", {}).setdefault(
                tier,
                {
                    "status": "running",
                    "selected_shard_count": 0,
                    "started_shard_count": 0,
                    "started_case_count": 0,
                    "completed_shard_count": 0,
                    "completed_case_count": 0,
                    "passed_case_count": 0,
                    "failed_case_count": 0,
                    "cluster_counts": {},
                },
            )
        tier_state = self._state.get("tiers", {}).get(tier, {}) if tier else {}
        if event == "campaign_started":
            self._state["selected_shard_count"] = int(row.get("selected_shard_count") or 0)
        elif event == "tier_started":
            tier_state["selected_shard_count"] = int(row.get("selected_shard_count") or 0)
            tier_state["status"] = "running"
        elif event == "shard_started":
            self._state["started_shard_count"] += 1
            tier_state["started_shard_count"] = int(tier_state.get("started_shard_count") or 0) + 1
            if shard:
                self._running_shards.add(shard)
        elif event == "case_started":
            self._state["started_case_count"] += 1
            tier_state["started_case_count"] = int(tier_state.get("started_case_count") or 0) + 1
            case_key = _case_key(row)
            if case_key:
                self._running_cases[case_key] = _running_case_summary(row)
        elif event == "case_completed":
            matrix_telemetry = _mapping(row.get("matrix_telemetry"))
            result = _mapping(matrix_telemetry.get("result"))
            failed = str(result.get("status") or "").strip() != "passed" or result.get("quality_passed") is False
            shard_name = str(row.get("shard") or "").strip()
            if shard_name:
                shard_counts = self._shard_case_counts.setdefault(shard_name, Counter())
                shard_counts["completed"] += 1
                shard_counts["failed" if failed else "passed"] += 1
            self._state["completed_case_count"] += 1
            tier_state["completed_case_count"] = int(tier_state.get("completed_case_count") or 0) + 1
            if failed:
                self._state["failed_case_count"] += 1
                tier_state["failed_case_count"] = int(tier_state.get("failed_case_count") or 0) + 1
                cluster = str(matrix_telemetry.get("failure_cluster") or "").strip()
                self._record_shard_failed_case(row=row, cluster=cluster)
                if shard_name:
                    self._tier_last_failed_shard[tier] = shard_name
                if cluster:
                    if shard_name:
                        self._shard_cluster_counts.setdefault(shard_name, Counter())[cluster] += 1
                        self._tier_cluster_origin_shards.setdefault(tier, {})[cluster] = shard_name
                    self._cluster_counts[cluster] += 1
                    tier_clusters = Counter(_mapping(tier_state.get("cluster_counts")))
                    tier_clusters[cluster] += 1
                    tier_state["cluster_counts"] = dict(sorted(tier_clusters.items()))
            else:
                self._state["passed_case_count"] += 1
                tier_state["passed_case_count"] = int(tier_state.get("passed_case_count") or 0) + 1
            self._remove_running_case(row)
        elif event == "shard_completed":
            self._state["completed_shard_count"] += 1
            tier_state["completed_shard_count"] = int(tier_state.get("completed_shard_count") or 0) + 1
            if shard:
                self._running_shards.discard(shard)
            self._merge_shard_completed_counts(row, tier_state)
        elif event == "tier_completed":
            tier_state["status"] = str(row.get("status") or "completed")
            tier_state["stop_reason"] = str(row.get("stop_reason") or "")
            if "selected_shard_count" in row:
                tier_state["selected_shard_count"] = int(row.get("selected_shard_count") or 0)
            if "completed_shard_count" in row:
                tier_state["completed_shard_count"] = int(row.get("completed_shard_count") or 0)
            if isinstance(row.get("cluster_counts"), Mapping):
                tier_state["cluster_counts"] = dict(row.get("cluster_counts") or {})
        elif event == "tier_stop_requested":
            tier_state["status"] = "stopping"
            tier_state["stop_reason"] = str(row.get("stop_reason") or row.get("reason") or "")
        elif event == "campaign_finished":
            self._state["status"] = str(row.get("status") or "completed")
            self._state["stop_reason"] = str(row.get("stopped_reason") or "")
        self._state["cluster_counts"] = dict(sorted(self._cluster_counts.items()))
        self._state["running_shards"] = sorted(self._running_shards)
        self._state["running_cases"] = list(self._running_cases.values())
        self._state["last_event"] = {key: value for key, value in row.items() if key != "aggregate"}
        self._state["seconds"] = round(time.perf_counter() - self._started, 3)

    def _remove_running_case(self, row: Mapping[str, Any]) -> None:
        case_key = _case_key(row)
        if case_key and case_key in self._running_cases:
            self._running_cases.pop(case_key, None)
            return
        shard = str(row.get("shard") or "").strip()
        completed_identity = _case_identity_for_key(row)
        candidates = [
            key
            for key, value in self._running_cases.items()
            if str(value.get("shard") or "") == shard
            and (
                not completed_identity
                or completed_identity
                in {str(value.get("case_id") or ""), str(value.get("case_name") or "")}
            )
        ]
        if candidates:
            self._running_cases.pop(candidates[0], None)

    def _record_shard_failed_case(self, *, row: Mapping[str, Any], cluster: str) -> None:
        shard_name = str(row.get("shard") or "").strip()
        if not shard_name:
            return
        matrix_telemetry = _mapping(row.get("matrix_telemetry"))
        result = _mapping(matrix_telemetry.get("result"))
        case = _mapping(result.get("case")) or _mapping(matrix_telemetry.get("case"))
        summary = {
            "id": str(case.get("id") or ""),
            "name": str(case.get("name") or result.get("name") or ""),
            "slug": str(case.get("slug") or ""),
            "prompt_sha256": str(case.get("prompt_sha256") or ""),
            "confirmed_intent_sha256": str(case.get("confirmed_intent_sha256") or ""),
            "stressors": list(case.get("stressors") or result.get("stressors") or ()),
            "cluster": str(cluster or ""),
        }
        rows = self._shard_failed_cases.setdefault(shard_name, [])
        identity = (
            summary["id"],
            summary["name"],
            summary["prompt_sha256"],
            summary["confirmed_intent_sha256"],
        )
        existing = {
            (
                str(item.get("id") or ""),
                str(item.get("name") or ""),
                str(item.get("prompt_sha256") or ""),
                str(item.get("confirmed_intent_sha256") or ""),
            )
            for item in rows
        }
        if identity not in existing:
            rows.append(summary)

    def _merge_shard_completed_counts(self, row: Mapping[str, Any], tier_state: dict[str, Any]) -> None:
        shard_name = str(row.get("shard") or "").strip()
        seen = self._shard_case_counts.setdefault(shard_name, Counter()) if shard_name else Counter()
        completed_delta = max(0, int(row.get("completed_case_count") or 0) - int(seen.get("completed") or 0))
        failed_delta = max(0, int(row.get("failed_case_count") or 0) - int(seen.get("failed") or 0))
        passed_delta = max(0, completed_delta - failed_delta)
        if completed_delta:
            self._state["completed_case_count"] += completed_delta
            tier_state["completed_case_count"] = int(tier_state.get("completed_case_count") or 0) + completed_delta
            seen["completed"] += completed_delta
        if failed_delta:
            self._state["failed_case_count"] += failed_delta
            tier_state["failed_case_count"] = int(tier_state.get("failed_case_count") or 0) + failed_delta
            seen["failed"] += failed_delta
        if passed_delta:
            self._state["passed_case_count"] += passed_delta
            tier_state["passed_case_count"] = int(tier_state.get("passed_case_count") or 0) + passed_delta
            seen["passed"] += passed_delta
        if failed_delta:
            self._merge_shard_completed_clusters(row, tier_state, shard_name)

    def _merge_shard_completed_clusters(
        self,
        row: Mapping[str, Any],
        tier_state: dict[str, Any],
        shard_name: str,
    ) -> None:
        seen_clusters = self._shard_cluster_counts.setdefault(shard_name, Counter()) if shard_name else Counter()
        tier_clusters = Counter(_mapping(tier_state.get("cluster_counts")))
        for cluster_row in _mapping_rows(row.get("failure_clusters")):
            cluster = str(cluster_row.get("cluster") or "").strip()
            if not cluster:
                continue
            try:
                total = int(cluster_row.get("count") or 1)
            except (TypeError, ValueError):
                total = 1
            delta = max(0, total - int(seen_clusters.get(cluster) or 0))
            if not delta:
                continue
            seen_clusters[cluster] += delta
            self._cluster_counts[cluster] += delta
            tier_clusters[cluster] += delta
        tier_state["cluster_counts"] = dict(sorted(tier_clusters.items()))

    def _snapshot(self) -> dict[str, Any]:
        snapshot = dict(self._state)
        snapshot["tiers"] = dict(self._state.get("tiers", {}))
        snapshot["running_shards"] = list(self._state.get("running_shards", ()))
        snapshot["cluster_counts"] = dict(self._state.get("cluster_counts", {}))
        snapshot["running_cases"] = list(self._state.get("running_cases", ()))
        snapshot["last_event"] = dict(self._state.get("last_event", {}))
        return snapshot


def first_cluster_at_threshold(counts: Counter[str], threshold: int) -> tuple[str, int]:
    for cluster, count in counts.most_common():
        if count >= threshold:
            return cluster, count
    return "", 0


def progress_console_line(row: Mapping[str, Any]) -> str:
    """Render one compact human progress line from canonical campaign telemetry."""

    event = str(row.get("event") or "").strip()
    tier = str(row.get("tier") or "").strip()
    shard = str(row.get("shard") or "").strip()
    prefix = "[greenfield-matrix]"
    if event == "campaign_started":
        return f"{prefix} campaign started shards={int(row.get('selected_shard_count') or 0)}"
    if event == "tier_started":
        return (
            f"{prefix} tier {tier or 'unknown'} started "
            f"shards={int(row.get('selected_shard_count') or 0)} workers={int(row.get('max_workers') or 0)}"
        )
    if event == "shard_started":
        return f"{prefix} shard {_scope(tier, shard)} started"
    if event == "case_started":
        telemetry = _mapping(row.get("matrix_telemetry"))
        case = _mapping(telemetry.get("case"))
        return (
            f"{prefix} case {_case_position(telemetry)} started "
            f"{_scope(tier, shard)} {_case_label(case)}{_stressors(case)}"
        )
    if event == "case_completed":
        telemetry = _mapping(row.get("matrix_telemetry"))
        result = _mapping(telemetry.get("result"))
        case = _mapping(result.get("case"))
        status = str(result.get("status") or "unknown")
        score = result.get("score")
        seconds = result.get("create_seconds")
        cluster = str(telemetry.get("failure_cluster") or "").strip()
        suffix = _join_nonempty(
            (
                f"score={score}/10" if score not in (None, "") else "",
                f"{float(seconds):.3f}s" if isinstance(seconds, (int, float)) else "",
                f"cluster={cluster}" if cluster else "",
                _issue_excerpt(str(result.get("first_issue") or "")),
            )
        )
        return (
            f"{prefix} case {_case_position(telemetry)} {status} "
            f"{_scope(tier, shard)} {_case_label(case or result)}"
            + (f" {suffix}" if suffix else "")
        )
    if event == "tier_stop_requested":
        reason = str(row.get("stop_reason") or row.get("reason") or "").strip()
        origin = str(row.get("origin_shard") or "").strip()
        return f"{prefix} tier {tier or 'unknown'} stop requested reason={reason or 'threshold'} origin={origin or shard or 'unknown'}"
    if event == "shard_completed":
        clusters = _cluster_counts(row.get("failure_clusters"))
        return (
            f"{prefix} shard {_scope(tier, shard)} {str(row.get('status') or 'completed')} "
            f"cases={int(row.get('completed_case_count') or 0)} failed={int(row.get('failed_case_count') or 0)}"
            + (f" clusters={clusters}" if clusters else "")
        )
    if event == "tier_completed":
        clusters = _cluster_counts(row.get("cluster_counts"))
        reason = str(row.get("stop_reason") or "").strip()
        return (
            f"{prefix} tier {tier or 'unknown'} {str(row.get('status') or 'completed')} "
            f"shards={int(row.get('completed_shard_count') or 0)}/{int(row.get('selected_shard_count') or 0)}"
            + (f" stop={reason}" if reason else "")
            + (f" clusters={clusters}" if clusters else "")
        )
    if event == "campaign_finished":
        reason = str(row.get("stopped_reason") or "").strip()
        return (
            f"{prefix} campaign {str(row.get('status') or 'completed')} "
            f"tiers={int(row.get('tier_count') or 0)}"
            + (f" stop={reason}" if reason else "")
            + (f" clusters={_cluster_counts(row.get('failure_clusters'))}" if row.get("failure_clusters") else "")
        )
    return ""


def _scope(tier: str, shard: str) -> str:
    return "/".join(item for item in (tier, shard) if item) or "unknown"


def _case_position(row: Mapping[str, Any]) -> str:
    index = int(row.get("index") or 0)
    total = int(row.get("total") or 0)
    return f"{index}/{total}" if index and total else "?"


def _case_label(row: Mapping[str, Any]) -> str:
    for key in ("name", "slug", "id"):
        token = _clean_text(str(row.get(key) or ""))
        if token:
            return token
    return "unnamed-case"


def _stressors(row: Mapping[str, Any]) -> str:
    values = [
        _clean_text(str(item))
        for item in row.get("stressors", ())
        if _clean_text(str(item))
    ]
    return " [" + ",".join(values[:4]) + "]" if values else ""


def _cluster_counts(value: Any) -> str:
    if isinstance(value, Mapping):
        pairs = [(str(key), int(count or 0)) for key, count in value.items() if str(key).strip()]
    else:
        pairs = [
            (str(row.get("cluster") or ""), int(row.get("count") or 0))
            for row in _mapping_rows(value)
            if str(row.get("cluster") or "").strip()
        ]
    ordered = sorted(pairs, key=lambda item: (-item[1], item[0]))[:3]
    return ",".join(f"{name}:{count}" for name, count in ordered if name)


def _issue_excerpt(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    if len(text) <= 100:
        return f"issue={text}"
    return f"issue={text[:100].rstrip()}..."


def _join_nonempty(values: tuple[str, ...]) -> str:
    return " ".join(value for value in values if value)


def _clean_text(value: str) -> str:
    return " ".join(str(value or "").split())


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _mapping_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _case_key(row: Mapping[str, Any]) -> str:
    tier = str(row.get("tier") or "").strip()
    shard = str(row.get("shard") or "").strip()
    identity = _case_identity_for_key(row)
    return "|".join(item for item in (tier, shard, identity) if item)


def _case_identity_for_key(row: Mapping[str, Any]) -> str:
    matrix_telemetry = _mapping(row.get("matrix_telemetry"))
    case = _mapping(matrix_telemetry.get("case"))
    if not case:
        case = _mapping(_mapping(matrix_telemetry.get("result")).get("case"))
    for key in ("id", "slug", "name"):
        token = str(case.get(key) or "").strip()
        if token:
            return token
    index = str(matrix_telemetry.get("index") or "").strip()
    return f"index-{index}" if index else ""


def _running_case_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    matrix_telemetry = _mapping(row.get("matrix_telemetry"))
    case = _mapping(matrix_telemetry.get("case"))
    return {
        "tier": str(row.get("tier") or ""),
        "shard": str(row.get("shard") or ""),
        "case_id": str(case.get("id") or ""),
        "case_name": str(case.get("name") or ""),
        "case_slug": str(case.get("slug") or ""),
        "index": int(matrix_telemetry.get("index") or 0),
        "total": int(matrix_telemetry.get("total") or 0),
        "stressors": list(case.get("stressors") or ()),
    }


__all__ = [
    "CAMPAIGN_PROGRESS_VERSION",
    "CampaignProgressWriter",
    "first_cluster_at_threshold",
    "progress_console_line",
]
