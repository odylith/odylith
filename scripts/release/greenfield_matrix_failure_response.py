"""Failure aggregation and replay guidance for tiered Greenfield campaigns."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
import subprocess
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from greenfield_matrix_case_file import load_case_file


def campaign_failure_clusters(tier_results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Merge tier and shard failure evidence without double-counting aggregates."""

    grouped: dict[str, dict[str, Any]] = {}
    for tier in tier_results:
        tier_name = str(tier.get("tier") or "")
        for cluster, count in _mapping(tier.get("cluster_counts")).items():
            key = str(cluster).strip()
            if not key:
                continue
            row = _cluster_row(grouped, key)
            tier_counts = dict(row.get("_tier_counts") or {})
            tier_counts[tier_name] = max(int(tier_counts.get(tier_name) or 0), int(count or 0))
            row["_tier_counts"] = tier_counts
            row["tiers"] = list(dict.fromkeys([*row.get("tiers", []), tier_name]))
        for shard in _mapping_rows(tier.get("shards")):
            shard_name = str(shard.get("name") or "")
            for cluster in _mapping_rows(shard.get("failure_clusters")):
                key = str(cluster.get("cluster") or "").strip()
                if not key:
                    continue
                row = _cluster_row(
                    grouped,
                    key,
                    example_issue=_tail_excerpt(str(cluster.get("example_issue") or "")),
                )
                shard_counts = dict(row.get("_shard_counts") or {})
                shard_counts[tier_name] = int(shard_counts.get(tier_name) or 0) + int(cluster.get("count") or 1)
                row["_shard_counts"] = shard_counts
                row["tiers"] = list(dict.fromkeys([*row.get("tiers", []), tier_name]))
                row["shards"] = list(dict.fromkeys([*row.get("shards", []), shard_name]))
                row["cases"] = list(
                    dict.fromkeys(
                        [
                            *row.get("cases", []),
                            *(str(case) for case in cluster.get("cases", ()) if str(case).strip()),
                        ]
                    )
                )
                row["case_ids"] = _merge_string_list(row.get("case_ids"), cluster.get("case_ids"))
                row["case_fingerprints"] = _merge_string_list(
                    row.get("case_fingerprints"),
                    cluster.get("case_fingerprints"),
                )
                if not row.get("example_issue"):
                    row["example_issue"] = _tail_excerpt(str(cluster.get("example_issue") or ""))
    rows: list[dict[str, Any]] = []
    for row in grouped.values():
        tier_counts = _mapping(row.get("_tier_counts"))
        shard_counts = _mapping(row.get("_shard_counts"))
        tiers = set(tier_counts) | set(shard_counts)
        count = sum(max(int(tier_counts.get(tier) or 0), int(shard_counts.get(tier) or 0)) for tier in tiers)
        clean = {key: value for key, value in row.items() if not str(key).startswith("_")}
        clean["count"] = count
        rows.append(clean)
    return sorted(rows, key=lambda row: (-int(row.get("count") or 0), str(row.get("cluster") or "")))


def failure_response_plan(
    *,
    tier_results: Sequence[Mapping[str, Any]],
    failure_clusters: Sequence[Mapping[str, Any]],
    stopped_reason: str,
    release_readiness_proven: bool,
) -> dict[str, Any]:
    """Return the stop-fix-replay packet required after a campaign failure."""

    clusters = [dict(cluster) for cluster in failure_clusters if str(cluster.get("cluster") or "").strip()]
    if not clusters:
        return {
            "status": "not-required",
            "casebook_capture_required": False,
            "release_claim_allowed": bool(release_readiness_proven),
        }
    replay_paths = _failure_replay_paths(tier_results)
    return {
        "status": "required",
        "casebook_capture_required": True,
        "release_claim_allowed": False,
        "stop_reason": stopped_reason,
        "primary_cluster": str(clusters[0].get("cluster") or ""),
        "exact_failed_subset_available": bool(replay_paths["failed_result_jsons"]),
        "failed_result_jsons": replay_paths["failed_result_jsons"],
        "shard_replay_case_files": replay_paths["shard_replay_case_files"],
        "failed_case_ids": _cluster_values(clusters, "case_ids"),
        "failed_case_fingerprints": _cluster_values(clusters, "case_fingerprints"),
        "operator_loop": _operator_loop(
            exact_failed_subset_available=bool(replay_paths["failed_result_jsons"]),
            shard_replay_required=bool(replay_paths["shard_replay_case_files"]),
        ),
    }


def _operator_loop(*, exact_failed_subset_available: bool, shard_replay_required: bool) -> list[str]:
    replay_step = (
        "Build failed-subset shards from failed_result_jsons and rerun the exact failed subset first."
        if exact_failed_subset_available
        else "Rerun the listed shard_replay_case_files because the failed case identity was not emitted before the shard died."
        if shard_replay_required
        else "Rerun the failing tier after Casebook capture because no replayable case identity was preserved."
    )
    return [
        "Capture or update a Casebook bug for the primary failure cluster before continuing volume discovery.",
        "Fix the Odylith platform root cause; do not mutate generated consumer repos by hand.",
        replay_step,
        "Resume 60-case, 120-case, and 240-case discovery only after the failed subset is green.",
        "Run strict release proof separately before making a release-readiness claim.",
    ]


def write_synthetic_shard_payload(
    *,
    output_json: Path,
    shard: Any,
    completed: subprocess.CompletedProcess[str],
    stop_reason: str,
    live_failure_snapshot: Mapping[str, Any] | None = None,
    force_failed: bool = False,
    forced_cluster: str = "",
    forced_detail: str = "",
    failure_status: str = "shard-process-failed",
) -> dict[str, Any]:
    """Write a replayable matrix payload when a child shard dies too early."""

    snapshot = _mapping(live_failure_snapshot)
    case_load_error = ""
    try:
        cases = load_case_file(Path(getattr(shard, "case_file")))
    except RuntimeError as exc:
        cases = ()
        case_load_error = str(exc)
    failed = bool(force_failed) or not stop_reason or int(snapshot.get("failed_case_count") or 0) > 0
    detail = _tail_excerpt(
        str(forced_detail or "").strip()
        or " ".join(item for item in (completed.stderr, completed.stdout) if item)
    )
    if case_load_error:
        detail = _tail_excerpt(" ".join(item for item in (detail, case_load_error) if item))
    if failed and not detail:
        detail = (
            "live shard telemetry recorded a failed case before the matrix result payload was written"
            if int(snapshot.get("failed_case_count") or 0) > 0
            else f"shard exited with return code {completed.returncode} before matrix result payload was written"
        )
    failed_cases = _cases_matching_live_failure_snapshot(cases, snapshot) if failed else ()
    replay_scope = _replay_scope(failed_cases=failed_cases, all_cases=cases, snapshot=snapshot)
    results = [
        _synthetic_failed_result(
            case,
            detail=detail,
            returncode=completed.returncode,
            failure_status=failure_status,
        )
        for case in failed_cases
    ] if failed and replay_scope == "exact-failed-cases" else []
    clusters = _synthetic_failure_clusters(
        cases=failed_cases,
        failed=failed,
        detail=detail,
        case_load_error=case_load_error,
        result_count=len(results),
        live_failure_snapshot=snapshot,
        forced_cluster=forced_cluster,
        replay_scope=replay_scope,
        source_case_file=str(getattr(shard, "case_file", "")),
    )
    payload = {
        "version": "odylith.greenfield.matrix.synthetic-shard-result.v1",
        "status": "failed" if failed else "stopped",
        "synthetic": True,
        "replayable": bool(failed),
        "exact_failed_subset_available": bool(results),
        "replay_scope": replay_scope,
        "shard_replay_case_file": (
            str(getattr(shard, "case_file", "")) if replay_scope == "source-shard" else ""
        ),
        "tier": str(getattr(shard, "tier", "")),
        "case_file": str(getattr(shard, "case_file", "")),
        "results": results,
        "campaign": {
            "phase": str(getattr(shard, "tier", "")),
            "proof_tier": str(getattr(shard, "proof_tier", "")),
            "selected_case_count": len(cases),
            "completed_case_count": len(results),
            "passed_case_count": 0,
            "failed_case_count": len(results) or (1 if failed else 0),
            "stopped_early": True,
            "stop_reason": stop_reason or "shard-process-failed-before-result-payload",
            "failure_clusters": clusters,
            "exact_failed_subset_available": bool(results),
            "replay_scope": replay_scope,
            "shard_replay_case_file": (
                str(getattr(shard, "case_file", "")) if replay_scope == "source-shard" else ""
            ),
            "release_readiness_boundary": (
                "synthetic shard payload preserves replay identity; it is not release-readiness proof"
            ),
        },
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _synthetic_failure_clusters(
    *,
    cases: Sequence[Any],
    failed: bool,
    detail: str,
    case_load_error: str,
    result_count: int,
    live_failure_snapshot: Mapping[str, Any],
    forced_cluster: str = "",
    replay_scope: str = "",
    source_case_file: str = "",
) -> list[dict[str, Any]]:
    if not failed:
        return []
    live_clusters = _mapping(live_failure_snapshot.get("cluster_counts"))
    cluster_name = str(forced_cluster or "").strip() or next(
        (str(key) for key in live_clusters if str(key).strip()),
        "",
    )
    failed_case_rows = _mapping_rows(live_failure_snapshot.get("failed_cases"))
    exact_scope = replay_scope == "exact-failed-cases"
    case_ids = _live_case_values(failed_case_rows, "id") or ([
        str(getattr(case, "case_id", "") or getattr(case, "slug", "")) for case in cases
    ] if exact_scope else [])
    fingerprints = _live_case_fingerprints(failed_case_rows) or (list(
        dict.fromkeys(
            fingerprint
            for case in cases
            for fingerprint in (
                _sha256_text(getattr(case, "prompt", "")),
                _sha256_text(getattr(case, "confirmed_intent_markdown", "") or ""),
            )
            if fingerprint
        )
    ) if exact_scope else [])
    stressors = _live_case_stressors(failed_case_rows) or (list(
        dict.fromkeys(
            str(stressor).strip()
            for case in cases
            for stressor in getattr(case, "stressors", ()) or ()
            if str(stressor).strip()
        )
    ) if exact_scope else [])
    return [
        {
            "cluster": cluster_name or "campaign.shard-process-failed",
            "count": result_count or 1,
            "cases": ([
                *(
                    _live_case_values(failed_case_rows, "name")
                    or [str(getattr(case, "name", "") or getattr(case, "slug", "")) for case in cases]
                ),
                *(["unreadable case file"] if case_load_error and not cases else []),
            ] if exact_scope else []),
            "case_ids": case_ids,
            "case_fingerprints": fingerprints,
            "stressors": stressors,
            "example_issue": detail,
            "replay_scope": replay_scope or "unknown",
            "shard_replay_case_file": source_case_file if replay_scope == "source-shard" else "",
        }
    ]


def _cases_matching_live_failure_snapshot(
    cases: Sequence[Any],
    snapshot: Mapping[str, Any],
) -> tuple[Any, ...]:
    failed_rows = _mapping_rows(snapshot.get("failed_cases"))
    if not failed_rows:
        return tuple(cases) if len(cases) == 1 else ()
    failed_ids = set(_live_case_values(failed_rows, "id"))
    failed_fingerprints = set(_live_case_fingerprints(failed_rows))
    strong_matched = [
        case
        for case in cases
        if str(getattr(case, "case_id", "") or getattr(case, "slug", "")) in failed_ids
        or _sha256_text(getattr(case, "prompt", "")) in failed_fingerprints
        or _sha256_text(getattr(case, "confirmed_intent_markdown", "") or "") in failed_fingerprints
    ]
    if strong_matched:
        return tuple(strong_matched)
    weak_tokens = set(_live_case_values(failed_rows, "name")) | set(_live_case_values(failed_rows, "slug"))
    matched = [
        case
        for case in cases
        if any(_weak_case_identity_unique(token, cases) and _case_matches_weak_identity(case, token) for token in weak_tokens)
    ]
    return tuple(matched)


def _replay_scope(*, failed_cases: Sequence[Any], all_cases: Sequence[Any], snapshot: Mapping[str, Any]) -> str:
    if failed_cases:
        return "exact-failed-cases"
    if _mapping_rows(snapshot.get("failed_cases")):
        return "source-shard" if all_cases else "unmatched-live-failed-cases"
    if all_cases:
        return "source-shard"
    return "unknown"


def _live_case_values(rows: Sequence[Mapping[str, Any]], key: str) -> list[str]:
    return list(
        dict.fromkeys(
            str(row.get(key) or "").strip()
            for row in rows
            if str(row.get(key) or "").strip()
        )
    )


def _live_case_fingerprints(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    values: list[str] = []
    for row in rows:
        for key in ("prompt_sha256", "confirmed_intent_sha256"):
            token = str(row.get(key) or "").strip()
            if token:
                values.append(token)
    return list(dict.fromkeys(values))


def _live_case_stressors(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    values: list[str] = []
    for row in rows:
        stressors = row.get("stressors")
        if isinstance(stressors, (str, bytes, bytearray)) or not isinstance(stressors, Sequence):
            continue
        values.extend(str(item).strip() for item in stressors if str(item).strip())
    return list(dict.fromkeys(values))


def _case_matches_weak_identity(case: Any, token: str) -> bool:
    value = str(token or "").strip()
    return value in {
        str(getattr(case, "name", "") or "").strip(),
        str(getattr(case, "slug", "") or "").strip(),
    }


def _weak_case_identity_unique(token: str, cases: Sequence[Any]) -> bool:
    value = str(token or "").strip()
    if not value:
        return False
    matches = 0
    for case in cases:
        if _case_matches_weak_identity(case, value):
            matches += 1
            if matches > 1:
                return False
    return matches == 1


def _synthetic_failed_result(
    case: Any,
    *,
    detail: str,
    returncode: int,
    failure_status: str,
) -> dict[str, Any]:
    case_identity = _synthetic_case_identity(case)
    status = str(failure_status or "shard-process-failed")
    return {
        "name": str(getattr(case, "name", "") or getattr(case, "slug", "")),
        "case": case_identity,
        "status": "failed",
        "create_seconds": 0.0,
        "create_returncode": int(returncode),
        "counts": {},
        "quality": {
            "passed": False,
            "issues": [f"{status}: {detail}"],
            "lenses": {
                "product_manager": False,
                "architect": False,
                "engineer": False,
                "domain_expert": False,
            },
            "scores": {},
            "score": 0,
            "score_explanation": ["pre-result shard failure blocks artifact-quality assessment"],
            "score_basis": "discovery",
        },
        "failure_detail": detail,
        "evidence": {
            "version": "odylith.greenfield.matrix.case_evidence.v1",
            "case": case_identity,
            "failure": {
                "status": status,
                "returncode": int(returncode),
                "detail_excerpt": detail,
            },
        },
    }


def _synthetic_case_identity(case: Any) -> dict[str, Any]:
    prompt = str(getattr(case, "prompt", "") or "")
    confirmed_intent = str(getattr(case, "confirmed_intent_markdown", "") or "")
    identity = {
        "id": str(getattr(case, "case_id", "") or getattr(case, "slug", "")),
        "name": str(getattr(case, "name", "")),
        "slug": str(getattr(case, "slug", "")),
        "tags": list(getattr(case, "tags", ()) or ()),
        "stressors": list(getattr(case, "stressors", ()) or ()),
        "prompt_sha256": _sha256_text(prompt),
    }
    if confirmed_intent.strip():
        identity["confirmed_intent_sha256"] = _sha256_text(confirmed_intent)
    return identity


def _cluster_row(
    grouped: dict[str, dict[str, Any]],
    key: str,
    *,
    example_issue: str = "",
) -> dict[str, Any]:
    return grouped.setdefault(
        key,
        {
            "cluster": key,
            "count": 0,
            "tiers": [],
            "shards": [],
            "cases": [],
            "case_ids": [],
            "case_fingerprints": [],
            "example_issue": example_issue,
            "_tier_counts": {},
            "_shard_counts": {},
        },
    )


def _failure_replay_paths(tier_results: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    failed_result_jsons: list[str] = []
    shard_replay_case_files: list[str] = []
    for tier in tier_results:
        for shard in _mapping_rows(tier.get("shards")):
            failed = int(shard.get("failed_case_count") or 0) > 0 or bool(
                _mapping_rows(shard.get("failure_clusters"))
            )
            path = str(shard.get("output_json") or "").strip()
            if not failed:
                continue
            payload = _read_json(path) if path else {}
            case_file = _shard_replay_case_file(payload) or str(shard.get("case_file") or "").strip()
            if _exact_failed_subset_available(
                payload,
                case_file=case_file,
                failed_case_count=int(shard.get("failed_case_count") or 0),
            ):
                failed_result_jsons.append(path)
                continue
            if case_file:
                shard_replay_case_files.append(case_file)
    return {
        "failed_result_jsons": list(dict.fromkeys(failed_result_jsons)),
        "shard_replay_case_files": list(dict.fromkeys(shard_replay_case_files)),
    }


def _exact_failed_subset_available(
    payload: Mapping[str, Any],
    *,
    case_file: str,
    failed_case_count: int,
) -> bool:
    if str(payload.get("replay_scope") or "") == "source-shard":
        return False
    campaign = _mapping(payload.get("campaign"))
    if str(campaign.get("replay_scope") or "") == "source-shard":
        return False
    source_cases = _source_cases(case_file)
    if not source_cases:
        return False
    matched_cases = _matched_failed_source_cases(
        payload,
        source_cases=source_cases,
    )
    if matched_cases is None:
        return False
    expected_count = _reported_failure_count(
        failed_case_count=failed_case_count,
        payload=payload,
    )
    return expected_count > 0 and len(matched_cases) == expected_count


def _shard_replay_case_file(payload: Mapping[str, Any]) -> str:
    for source in (payload, _mapping(payload.get("campaign"))):
        token = str(source.get("shard_replay_case_file") or "").strip()
        if token:
            return token
    for cluster in _mapping_rows(_mapping(payload.get("campaign")).get("failure_clusters")):
        token = str(cluster.get("shard_replay_case_file") or "").strip()
        if token:
            return token
    return ""


def _source_cases(case_file: str) -> tuple[Any, ...]:
    token = str(case_file or "").strip()
    if not token:
        return ()
    try:
        return load_case_file(Path(token))
    except RuntimeError:
        return ()


def _matched_failed_source_cases(
    payload: Mapping[str, Any],
    *,
    source_cases: Sequence[Any],
) -> set[int] | None:
    matches: set[int] = set()
    failed_results = [result for result in _mapping_rows(payload.get("results")) if _result_failed(result)]
    for result in failed_results:
        case_index = _single_source_case_match(_result_identity_mappings(result), source_cases)
        if case_index is None:
            return None
        matches.add(case_index)
    for cluster in _payload_failure_clusters(payload):
        count = int(cluster.get("count") or 0)
        identity_mappings = _cluster_identity_mappings(cluster)
        if count <= 0 or len(identity_mappings) < count:
            return None
        for identity in identity_mappings:
            case_index = _single_source_case_match((identity,), source_cases)
            if case_index is not None:
                matches.add(case_index)
        if len(matches) < count:
            return None
    return matches or None


def _result_identity_mappings(result: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    mappings = (
        _mapping(result.get("case")),
        _mapping(_mapping(result.get("evidence")).get("case")),
        _mapping(_mapping(result.get("result")).get("case")),
    )
    return tuple(mapping for mapping in mappings if mapping)


def _cluster_identity_mappings(cluster: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    mappings: list[Mapping[str, Any]] = []
    for case_id in _string_values(cluster.get("case_ids")):
        mappings.append({"id": case_id})
    for fingerprint in _string_values(cluster.get("case_fingerprints")):
        mappings.append(
            {
                "prompt_sha256": fingerprint,
                "confirmed_intent_sha256": fingerprint,
            }
        )
    return tuple(mappings)


def _single_source_case_match(
    identity_mappings: Sequence[Mapping[str, Any]],
    source_cases: Sequence[Any],
) -> int | None:
    matches: set[int] = set()
    for index, case in enumerate(source_cases):
        if any(_case_matches_identity(case, identity) for identity in identity_mappings):
            matches.add(index)
    return next(iter(matches)) if len(matches) == 1 else None


def _case_matches_identity(case: Any, identity: Mapping[str, Any]) -> bool:
    case_id = str(getattr(case, "case_id", "") or "").strip()
    if case_id and case_id == str(identity.get("id") or "").strip():
        return True
    for key, source_value in (
        ("prompt_sha256", getattr(case, "prompt", "")),
        ("confirmed_intent_sha256", getattr(case, "confirmed_intent_markdown", "")),
    ):
        token = str(identity.get(key) or "").strip().casefold()
        if _is_sha256(token) and token == _sha256_text(source_value):
            return True
    return False


def _payload_failure_clusters(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    candidates = (
        *_mapping_rows(payload.get("failure_clusters")),
        *_mapping_rows(_mapping(payload.get("campaign")).get("failure_clusters")),
    )
    unique: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for cluster in candidates:
        key = json.dumps(cluster, sort_keys=True, separators=(",", ":"))
        if key not in seen:
            seen.add(key)
            unique.append(cluster)
    return tuple(unique)


def _reported_failure_count(*, failed_case_count: int, payload: Mapping[str, Any]) -> int:
    if failed_case_count > 0:
        return failed_case_count
    campaign = _mapping(payload.get("campaign"))
    campaign_count = int(campaign.get("failed_case_count") or 0)
    if campaign_count > 0:
        return campaign_count
    return sum(int(cluster.get("count") or 0) for cluster in _payload_failure_clusters(payload))


def _string_values(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _read_json(path: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _cluster_values(clusters: Sequence[Mapping[str, Any]], key: str) -> list[str]:
    values: list[str] = []
    for cluster in clusters:
        for value in cluster.get(key, ()) or ():
            token = str(value or "").strip()
            if token:
                values.append(token)
    return list(dict.fromkeys(values))


def _result_failed(row: Mapping[str, Any]) -> bool:
    status = str(row.get("status") or "").strip().casefold()
    if status and status != "passed":
        return True
    quality = row.get("quality")
    return bool(isinstance(quality, Mapping) and quality.get("passed") is False)


def _merge_string_list(current: Any, added: Any) -> list[str]:
    values: list[str] = []
    for source in (current, added):
        if isinstance(source, (str, bytes, bytearray)) or not isinstance(source, Sequence):
            iterable = (source,) if str(source or "").strip() else ()
        else:
            iterable = source
        for value in iterable:
            token = str(value or "").strip()
            if token:
                values.append(token)
    return list(dict.fromkeys(values))


def _tail_excerpt(value: str, *, limit: int = 1200) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return "..." + text[-limit:].lstrip()


def _sha256_text(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _mapping_rows(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(dict(item) for item in value if isinstance(item, Mapping))


__all__ = [
    "campaign_failure_clusters",
    "failure_response_plan",
    "write_synthetic_shard_payload",
]
