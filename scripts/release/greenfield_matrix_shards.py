"""Build stratified greenfield matrix shard files from external case metadata."""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from greenfield_matrix_stressors import DEFAULT_HIGH_VARIANCE_STRESSORS
from greenfield_matrix_stressors import case_stratification
from greenfield_matrix_stressors import case_stressors
from greenfield_matrix_stressors import missing_required_stressors
from greenfield_matrix_stressors import required_stressors_from_values
from greenfield_matrix_stressors import stressor_coverage
from greenfield_matrix_stressors import variance_evaluation
from greenfield_matrix_case_file import load_case_file
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase


SHARD_BUILDER_VERSION = "odylith.greenfield.matrix.shards.v1"
CASE_FILE_VERSION = "odylith.greenfield.matrix.case-file.v1"
DEFAULT_SHARD_SIZE = 30
DEFAULT_REGRESSION_SIZE = 60
DEFAULT_VOLUME_SIZE = 120
DEFAULT_DEEP_VOLUME_SIZE = 240
DEFAULT_RELEASE_SIZE = 12


@dataclass(frozen=True)
class FailedCaseIdentities:
    strong: frozenset[str]
    weak: frozenset[str]

    @property
    def all(self) -> tuple[str, ...]:
        return tuple(sorted((*self.strong, *self.weak)))


def build_shards(
    *,
    case_files: Sequence[Path],
    output_dir: Path,
    failed_result_jsons: Sequence[Path] = (),
    shard_size: int = DEFAULT_SHARD_SIZE,
    regression_size: int = DEFAULT_REGRESSION_SIZE,
    volume_size: int = DEFAULT_VOLUME_SIZE,
    deep_volume_size: int = DEFAULT_DEEP_VOLUME_SIZE,
    release_size: int = DEFAULT_RELEASE_SIZE,
    required_stressors: Sequence[str] = (),
    failed_subset_only: bool = False,
) -> dict[str, Any]:
    cases = _dedupe_cases(_load_cases(case_files))
    if not cases:
        raise RuntimeError("greenfield shard builder requires at least one source case")
    if not failed_subset_only:
        _raise_for_undersized_default_tiers(
            source_count=len(cases),
            regression_size=regression_size,
            volume_size=volume_size,
            deep_volume_size=deep_volume_size,
            release_size=release_size,
        )
    normalized_required = required_stressors_from_values(required_stressors)
    missing = missing_required_stressors(cases, normalized_required)
    if missing:
        raise RuntimeError(
            "greenfield shard source case set does not cover required stressor classes: "
            + ", ".join(missing)
        )

    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    size = max(1, int(shard_size or DEFAULT_SHARD_SIZE))
    failed_identities = _failed_case_identities(failed_result_jsons)
    failed_cases = tuple(
        case for case in cases if _case_matches_any(case, failed_identities, all_cases=cases)
    )
    tiers = {
        "failed-subset": failed_cases,
    }
    if not failed_subset_only:
        tiers.update(
            {
                "60-case-regression": _stratified_select(
                    cases,
                    limit=_bounded_limit(regression_size, len(cases)),
                    required_stressors=normalized_required,
                ),
                "volume-discovery": _stratified_select(
                    cases,
                    limit=_bounded_limit(volume_size, len(cases)),
                    required_stressors=normalized_required,
                ),
                "240-case-discovery": _stratified_select(
                    cases,
                    limit=_bounded_limit(deep_volume_size, len(cases)),
                    required_stressors=normalized_required,
                ),
                "release-proof": _stratified_select(
                    cases,
                    limit=_bounded_limit(release_size, len(cases)),
                    required_stressors=normalized_required,
                ),
            }
        )
    tier_rows: dict[str, Any] = {}
    env: dict[str, str] = {}
    for tier, tier_cases in tiers.items():
        files = _write_tier_shards(
            output_dir=out,
            tier=tier,
            cases=tier_cases,
            shard_size=size if tier != "release-proof" else max(1, len(tier_cases) or 1),
        )
        tier_rows[tier] = {
            "case_count": len(tier_cases),
            "shard_count": len(files),
            "files": [str(path) for path in files],
            "stressor_coverage": stressor_coverage(tier_cases, normalized_required),
            "variance_evaluation": variance_evaluation(tier_cases, normalized_required),
            "case_stratification": case_stratification(tier_cases),
        }
        env[_env_key_for_tier(tier)] = ",".join(str(path) for path in files)

    payload = {
        "version": SHARD_BUILDER_VERSION,
        "source_case_count": len(cases),
        "source_case_files": [str(Path(path).expanduser().resolve()) for path in case_files],
        "failed_result_jsons": [str(Path(path).expanduser().resolve()) for path in failed_result_jsons],
        "failed_case_identities": list(failed_identities.all),
        "failed_case_identity_classes": {
            "strong": sorted(failed_identities.strong),
            "weak_unique": sorted(
                token for token in failed_identities.weak if _weak_identity_unique(token, cases)
            ),
            "weak_ambiguous": sorted(
                token for token in failed_identities.weak if not _weak_identity_unique(token, cases)
            ),
        },
        "shard_size": size,
        "failed_subset_only": bool(failed_subset_only),
        "required_stressors": list(normalized_required),
        "high_variance_taxonomy": list(DEFAULT_HIGH_VARIANCE_STRESSORS),
        "source_stressor_coverage": stressor_coverage(cases, normalized_required),
        "source_variance_evaluation": variance_evaluation(cases, normalized_required),
        "source_case_stratification": case_stratification(cases),
        "tiers": tier_rows,
        "campaign_env": env,
        "campaign_command_hint": "make greenfield-matrix-campaign",
    }
    summary_path = out / "greenfield-matrix-shards.v1.json"
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    payload["summary_json"] = str(summary_path)
    return payload


def _load_cases(case_files: Sequence[Path]) -> tuple[GreenfieldMatrixCase, ...]:
    loaded: list[GreenfieldMatrixCase] = []
    for case_file in case_files:
        token = str(case_file or "").strip()
        if token:
            loaded.extend(load_case_file(Path(token)))
    return tuple(loaded)


def _dedupe_cases(cases: Sequence[GreenfieldMatrixCase]) -> tuple[GreenfieldMatrixCase, ...]:
    seen: set[str] = set()
    deduped: list[GreenfieldMatrixCase] = []
    for case in cases:
        key = _primary_identity(case)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(case)
    return tuple(deduped)


def _raise_for_undersized_default_tiers(
    *,
    source_count: int,
    regression_size: int,
    volume_size: int,
    deep_volume_size: int,
    release_size: int,
) -> None:
    required = {
        "60-case-regression": int(regression_size or 0),
        "volume-discovery": int(volume_size or 0),
        "240-case-discovery": int(deep_volume_size or 0),
        "release-proof": int(release_size or 0),
    }
    undersized = [
        f"{tier} requires {size} case(s), source pool has {source_count}"
        for tier, size in required.items()
        if size > 0 and source_count < size
    ]
    if undersized:
        raise RuntimeError("greenfield shard source pool is undersized for requested tiers: " + "; ".join(undersized))


def _failed_case_identities(paths: Sequence[Path]) -> FailedCaseIdentities:
    strong: set[str] = set()
    weak: set[str] = set()
    for path in paths:
        token = str(path or "").strip()
        if not token:
            continue
        payload = _read_json(Path(token))
        identities = _failed_identities_from_payload(payload)
        strong.update(identities.strong)
        weak.update(identities.weak)
    return FailedCaseIdentities(
        strong=frozenset(item for item in strong if item),
        weak=frozenset(item for item in weak if item),
    )


def _failed_identities_from_payload(payload: Any) -> FailedCaseIdentities:
    strong_found: set[str] = set()
    weak_found: set[str] = set()
    if not isinstance(payload, Mapping):
        return FailedCaseIdentities(frozenset(), frozenset())
    for result in _mapping_rows(payload.get("results")):
        if _result_failed(result):
            strong: set[str] = set()
            weak: set[str] = set()
            for case_mapping in (
                _nested(result, "case"),
                _nested(result, "evidence", "case"),
                _nested(result, "result", "case"),
            ):
                strong.update(_case_mapping_strong_tokens(case_mapping))
                weak.update(_case_mapping_weak_tokens(case_mapping))
            if strong:
                strong_found.update(strong)
            elif weak:
                weak_found.update(weak)
            else:
                weak_found.update(_identity_tokens(result.get("name")))
    campaign = payload.get("campaign")
    if isinstance(campaign, Mapping):
        cluster_identities = _cluster_case_identities(campaign.get("failure_clusters"))
        strong_found.update(cluster_identities.strong)
        weak_found.update(cluster_identities.weak)
    cluster_identities = _cluster_case_identities(payload.get("failure_clusters"))
    strong_found.update(cluster_identities.strong)
    weak_found.update(cluster_identities.weak)
    for tier in _mapping_rows(payload.get("tiers")):
        for shard in _mapping_rows(tier.get("shards")):
            cluster_identities = _cluster_case_identities(shard.get("failure_clusters"))
            strong_found.update(cluster_identities.strong)
            weak_found.update(cluster_identities.weak)
    return FailedCaseIdentities(frozenset(strong_found), frozenset(weak_found))


def _result_failed(row: Mapping[str, Any]) -> bool:
    status = str(row.get("status") or "").strip().casefold()
    if status and status != "passed":
        return True
    quality = row.get("quality")
    if isinstance(quality, Mapping):
        return quality.get("passed") is False
    return False


def _cluster_case_identities(clusters: Any) -> FailedCaseIdentities:
    strong: set[str] = set()
    weak: set[str] = set()
    for cluster in _mapping_rows(clusters):
        for case_id in _string_rows(cluster.get("case_ids")):
            strong.update(_identity_tokens(case_id))
        for fingerprint in _string_rows(cluster.get("case_fingerprints")):
            strong.update(_identity_tokens(fingerprint))
        for case_name in _string_rows(cluster.get("cases")):
            weak.update(_identity_tokens(case_name))
    return FailedCaseIdentities(frozenset(strong), frozenset(weak))


def _stratified_select(
    cases: Sequence[GreenfieldMatrixCase],
    *,
    limit: int,
    required_stressors: Sequence[str],
) -> tuple[GreenfieldMatrixCase, ...]:
    target = max(0, min(int(limit), len(cases)))
    if target <= 0:
        return ()
    ordered = sorted(cases, key=lambda case: (_primary_identity(case), str(case.name)))
    groups = _stressor_groups(ordered)
    selected: list[GreenfieldMatrixCase] = []
    selected_keys: set[str] = set()

    for stressor in required_stressors:
        _append_first_available(groups.get(_slug(stressor), ()), selected, selected_keys, target)
    stressor_order = tuple(dict.fromkeys((*required_stressors, *sorted(groups))))
    while len(selected) < target:
        progressed = False
        for stressor in stressor_order:
            if _append_first_available(groups.get(_slug(stressor), ()), selected, selected_keys, target):
                progressed = True
            if len(selected) >= target:
                break
        if not progressed:
            break
    for case in ordered:
        if len(selected) >= target:
            break
        _append_case(case, selected, selected_keys)
    return tuple(selected)


def _stressor_groups(cases: Sequence[GreenfieldMatrixCase]) -> dict[str, tuple[GreenfieldMatrixCase, ...]]:
    groups: dict[str, list[GreenfieldMatrixCase]] = defaultdict(list)
    for case in cases:
        stressors = case_stressors(case)
        for stressor in stressors or ("unstressed",):
            groups[stressor].append(case)
    return {key: tuple(value) for key, value in groups.items()}


def _append_first_available(
    cases: Sequence[GreenfieldMatrixCase],
    selected: list[GreenfieldMatrixCase],
    selected_keys: set[str],
    limit: int,
) -> bool:
    if len(selected) >= limit:
        return False
    for case in cases:
        if _primary_identity(case) not in selected_keys:
            _append_case(case, selected, selected_keys)
            return True
    return False


def _append_case(
    case: GreenfieldMatrixCase,
    selected: list[GreenfieldMatrixCase],
    selected_keys: set[str],
) -> None:
    key = _primary_identity(case)
    if key in selected_keys:
        return
    selected.append(case)
    selected_keys.add(key)


def _write_tier_shards(
    *,
    output_dir: Path,
    tier: str,
    cases: Sequence[GreenfieldMatrixCase],
    shard_size: int,
) -> tuple[Path, ...]:
    if not cases:
        return ()
    files: list[Path] = []
    for shard_index, start in enumerate(range(0, len(cases), max(1, shard_size)), start=1):
        shard_cases = tuple(cases[start : start + max(1, shard_size)])
        path = output_dir / f"{tier}-{shard_index:03d}.cases.json"
        payload = {
            "version": CASE_FILE_VERSION,
            "tier": tier,
            "shard_index": shard_index,
            "case_count": len(shard_cases),
            "cases": [_case_to_dict(case) for case in shard_cases],
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        files.append(path)
    return tuple(files)


def _case_to_dict(case: GreenfieldMatrixCase) -> dict[str, Any]:
    row = {
        "name": case.name,
        "prompt": case.prompt,
        "required_terms": list(case.required_terms),
        "leakage_terms": list(case.leakage_terms),
        "tags": list(case.tags),
        "stressors": list(case.stressors),
    }
    if case.case_id:
        row["case_id"] = case.case_id
    if case.confirmed_intent_markdown:
        row["confirmed_intent_markdown"] = case.confirmed_intent_markdown
    return row


def _case_matches_any(
    case: GreenfieldMatrixCase,
    identities: FailedCaseIdentities,
    *,
    all_cases: Sequence[GreenfieldMatrixCase],
) -> bool:
    if not identities.strong and not identities.weak:
        return False
    strong_tokens, weak_tokens = _case_identity_tokens(case)
    if strong_tokens & set(identities.strong):
        return True
    return any(token in identities.weak and _weak_identity_unique(token, all_cases) for token in weak_tokens)


def _case_identity_tokens(case: GreenfieldMatrixCase) -> tuple[set[str], set[str]]:
    strong: set[str] = set()
    weak: set[str] = set()
    if case.case_id:
        strong.update(_identity_tokens(case.case_id))
    else:
        weak.update(_identity_tokens(case.name))
        weak.update(_identity_tokens(case.slug))
    strong.update(_identity_tokens(_sha256_text(case.prompt)))
    strong.update(_identity_tokens(_sha256_text(case.confirmed_intent_markdown)))
    return strong, weak


def _weak_identity_unique(token: str, cases: Sequence[GreenfieldMatrixCase]) -> bool:
    value = str(token or "").strip()
    if not value:
        return False
    matches = 0
    for case in cases:
        _, weak_tokens = _case_identity_tokens(case)
        if value in weak_tokens:
            matches += 1
            if matches > 1:
                return False
    return matches == 1


def _identity_tokens(value: Any) -> set[str]:
    text = str(value or "").strip()
    slug = _slug(text)
    return {item for item in (text, slug) if item}


def _sha256_text(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _case_mapping_strong_tokens(value: Any) -> set[str]:
    if not isinstance(value, Mapping):
        return set()
    tokens: set[str] = set()
    stable_id = str(value.get("id") or "").strip()
    if stable_id:
        for key in ("id", "slug"):
            tokens.update(_identity_tokens(value.get(key)))
    for key in ("prompt_sha256", "confirmed_intent_sha256"):
        tokens.update(_identity_tokens(value.get(key)))
    return tokens


def _case_mapping_weak_tokens(value: Any) -> set[str]:
    if not isinstance(value, Mapping):
        return set()
    tokens: set[str] = set()
    for key in ("name", "slug"):
        tokens.update(_identity_tokens(value.get(key)))
    return tokens


def _primary_identity(case: GreenfieldMatrixCase) -> str:
    if case.case_id:
        return "case-id:" + _slug(case.case_id)
    prompt_hash = _sha256_text(case.prompt)
    if prompt_hash:
        return "prompt:" + prompt_hash
    return "slug:" + _slug(case.slug or case.name)


def _bounded_limit(value: int, total: int) -> int:
    number = int(value or 0)
    if number <= 0:
        return total
    return min(number, total)


def _env_key_for_tier(tier: str) -> str:
    return {
        "failed-subset": "GREENFIELD_MATRIX_FAILED_CASE_FILES",
        "60-case-regression": "GREENFIELD_MATRIX_REGRESSION_CASE_FILES",
        "volume-discovery": "GREENFIELD_MATRIX_VOLUME_CASE_FILES",
        "240-case-discovery": "GREENFIELD_MATRIX_DEEP_VOLUME_CASE_FILES",
        "release-proof": "GREENFIELD_MATRIX_RELEASE_CASE_FILES",
    }[tier]


def _read_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"unable to read matrix result JSON {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"matrix result JSON is invalid {path}: {exc}") from exc


def _mapping_rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(row for row in value if isinstance(row, Mapping))


def _string_rows(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _nested(row: Mapping[str, Any], *keys: str) -> Any:
    current: Any = row
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _slug(value: Any) -> str:
    parts: list[str] = []
    last_dash = False
    for char in str(value or "").strip().casefold().replace("_", "-"):
        if char.isalnum():
            parts.append(char)
            last_dash = False
        elif not last_dash:
            parts.append("-")
            last_dash = True
    return "".join(parts).strip("-")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build tiered greenfield matrix shard case files.")
    parser.add_argument("--case-file", action="append", required=True)
    parser.add_argument("--failed-result-json", action="append", default=None)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--shard-size", type=int, default=DEFAULT_SHARD_SIZE)
    parser.add_argument("--regression-size", type=int, default=DEFAULT_REGRESSION_SIZE)
    parser.add_argument("--volume-size", type=int, default=DEFAULT_VOLUME_SIZE)
    parser.add_argument("--deep-volume-size", type=int, default=DEFAULT_DEEP_VOLUME_SIZE)
    parser.add_argument("--release-size", type=int, default=DEFAULT_RELEASE_SIZE)
    parser.add_argument(
        "--failed-subset-only",
        action="store_true",
        help="Write only the failed-subset tier from failed-result identity evidence.",
    )
    parser.add_argument("--require-high-variance-stressors", action="store_true")
    parser.add_argument("--required-stressor", action="append", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    required_stressors = required_stressors_from_values(
        args.required_stressor or (),
        use_default=bool(args.require_high_variance_stressors),
    )
    payload = build_shards(
        case_files=tuple(Path(path) for path in args.case_file),
        output_dir=Path(args.output_dir),
        failed_result_jsons=tuple(Path(path) for path in args.failed_result_json or ()),
        shard_size=max(1, int(args.shard_size)),
        regression_size=max(0, int(args.regression_size)),
        volume_size=max(0, int(args.volume_size)),
        deep_volume_size=max(0, int(args.deep_volume_size)),
        release_size=max(0, int(args.release_size)),
        required_stressors=required_stressors,
        failed_subset_only=bool(args.failed_subset_only),
    )
    if str(args.output_json or "").strip():
        output_json = Path(args.output_json).expanduser().resolve()
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
