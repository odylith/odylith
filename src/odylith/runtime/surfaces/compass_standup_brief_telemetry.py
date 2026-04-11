"""Local telemetry for Compass brief provider spend, skips, and repairs."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache


TELEMETRY_VERSION = "v1"
TELEMETRY_PATH = ".odylith/compass/standup-brief-telemetry.v1.json"
_MAX_ATTEMPTS = 200


def telemetry_path(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / TELEMETRY_PATH).resolve()


def _now_utc_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(repo_root: Path) -> dict[str, Any]:
    payload = odylith_context_cache.read_json_object(telemetry_path(repo_root=repo_root))
    attempts = payload.get("attempts") if isinstance(payload, Mapping) else []
    return {
        "version": TELEMETRY_VERSION,
        "attempts": [
            dict(item)
            for item in (attempts if isinstance(attempts, Sequence) and not isinstance(attempts, (str, bytes, bytearray)) else [])
            if isinstance(item, Mapping)
        ],
    }


def _write(repo_root: Path, payload: Mapping[str, Any]) -> None:
    path = telemetry_path(repo_root=repo_root)
    odylith_context_cache.write_text_if_changed(
        repo_root=repo_root,
        path=path,
        content=json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        lock_key=str(path),
    )


def _estimate_tokens(chars: int) -> int:
    return max(0, int(round(max(0, int(chars)) / 4.0)))


def _cost_estimate(*, input_chars: int, output_chars: int) -> dict[str, Any]:
    input_tokens = _estimate_tokens(input_chars)
    output_tokens = _estimate_tokens(output_chars)
    return {
        "pricing_known": False,
        "basis": "chars_div_4",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def record_attempt(
    *,
    repo_root: Path,
    runtime_packet_fingerprint: str,
    bundle_fingerprint: str,
    substrate_fingerprints: Mapping[str, str],
    provider_decision: str,
    input_chars: int,
    output_chars: int,
    latency_ms: float,
    repair_count: int,
    salvage_count: int,
    repair_input_chars: int = 0,
    provider_call_count: int = 0,
    skip_reason: str = "",
    failure_kind: str = "",
    provider_code: str = "",
    provider_detail: str = "",
    model: str = "",
    reasoning_effort: str = "",
) -> None:
    repo_root = Path(repo_root).resolve()
    payload = _load(repo_root=repo_root)
    attempts = list(payload.get("attempts", []))
    attempts.append(
        {
            "recorded_utc": _now_utc_iso(),
            "runtime_packet_fingerprint": str(runtime_packet_fingerprint).strip(),
            "bundle_fingerprint": str(bundle_fingerprint).strip(),
            "substrate_fingerprints": {
                str(key).strip(): str(value).strip()
                for key, value in dict(substrate_fingerprints).items()
                if str(key).strip() and str(value).strip()
            },
            "provider_decision": str(provider_decision).strip(),
            "input_chars": int(input_chars),
            "output_chars": int(output_chars),
            "latency_ms": round(float(latency_ms), 3),
            "repair_count": int(repair_count),
            "salvage_count": int(salvage_count),
            "repair_input_chars": int(repair_input_chars),
            "provider_call_count": int(provider_call_count),
            "skip_reason": str(skip_reason).strip(),
            "failure_kind": str(failure_kind).strip(),
            "provider_code": str(provider_code).strip(),
            "provider_detail": str(provider_detail).strip(),
            "model": str(model).strip(),
            "reasoning_effort": str(reasoning_effort).strip(),
            "estimated_cost": _cost_estimate(input_chars=int(input_chars), output_chars=int(output_chars)),
        }
    )
    payload["attempts"] = attempts[-_MAX_ATTEMPTS:]
    _write(repo_root=repo_root, payload=payload)


__all__ = [
    "TELEMETRY_PATH",
    "TELEMETRY_VERSION",
    "record_attempt",
    "telemetry_path",
]
