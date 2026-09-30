#!/usr/bin/env python3
"""Verify the final Greenfield release qualification against frozen evidence."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from greenfield_distribution_provenance import verify_distribution_provenance
from greenfield_final_holdout_guard import (
    FINAL_HOLDOUT_RUN_LEDGER_VERSION,
    read_final_holdout_run,
)
from greenfield_matrix_release_artifacts import (
    is_sha256,
    retained_evidence_manifest_issues,
    sha256_file,
)
from greenfield_onboarding_review import (
    ONBOARDING_REVIEW_PACKAGE_VERSION,
    ONBOARDING_REVIEW_SIDECAR_VERSION,
    build_onboarding_review_sidecar,
)


def verify_release_qualification(
    *,
    sidecar_path: Path,
    final_holdout_ledger_path: Path,
    distribution_provenance_path: Path,
    implementation_revision: str,
) -> dict[str, str]:
    """Fail closed unless one review qualifies the exact terminal holdout."""

    sidecar_file = _safe_json_file(sidecar_path, label="Greenfield review sidecar")
    sidecar = _json_object(sidecar_file, label="Greenfield review sidecar")
    if sidecar.get("version") != ONBOARDING_REVIEW_SIDECAR_VERSION:
        raise RuntimeError("Greenfield review sidecar has an unsupported version")
    if sidecar.get("status") != "passed":
        raise RuntimeError("Greenfield review sidecar did not pass")

    base_path, base_sha256 = _bound_file(
        sidecar.get("base_result"),
        path_key="path",
        sha_key="sha256",
        label="Greenfield matrix result",
    )
    retained_path, retained_sha256 = _bound_file(
        sidecar.get("retained_evidence"),
        path_key="manifest",
        sha_key="manifest_sha256",
        label="Greenfield retained evidence manifest",
    )
    review_path, review_sha256 = _bound_file(
        sidecar.get("review_package"),
        path_key="path",
        sha_key="sha256",
        label="Greenfield independent review package",
    )
    review_package = _json_object(review_path, label="Greenfield independent review package")
    if review_package.get("version") != ONBOARDING_REVIEW_PACKAGE_VERSION:
        raise RuntimeError("Greenfield independent review package has an unsupported version")
    rebuilt = build_onboarding_review_sidecar(
        base_result_path=base_path,
        retained_manifest_path=retained_path,
        review_package=review_package,
    )
    persisted_core = dict(sidecar)
    persisted_core.pop("review_package", None)
    if rebuilt != persisted_core or rebuilt.get("status") != "passed":
        raise RuntimeError("Greenfield review sidecar is stale, forged, or incomplete")

    proof_root = Path(final_holdout_ledger_path).expanduser().resolve().parent
    expected_paths = {
        "Greenfield review sidecar": (sidecar_file, proof_root / "onboarding-review-sidecar.v2.json"),
        "Greenfield matrix result": (base_path, proof_root / "matrix-result.v1.json"),
        "Greenfield retained evidence manifest": (
            retained_path,
            proof_root / "retained-evidence/retained-evidence-manifest.v1.json",
        ),
        "Greenfield independent review package": (
            review_path,
            proof_root / "independent-review-package.v1.json",
        ),
    }
    for label, (actual, expected) in expected_paths.items():
        if actual != expected:
            raise RuntimeError(f"{label} is outside the canonical release proof")

    base = _json_object(base_path, label="Greenfield matrix result")
    if base.get("status") != "awaiting-independent-review":
        raise RuntimeError("Greenfield matrix did not reach independent review")
    if _mapping(base.get("onboarding_quality_scorecard")).get("status") != "awaiting-independent-review":
        raise RuntimeError("Greenfield matrix scorecard did not await independent review")
    if _mapping(base.get("campaign")).get("proof_tier") != "release":
        raise RuntimeError("Greenfield matrix is not terminal release proof")
    semantic_release = _mapping(base.get("semantic_release"))
    if semantic_release.get("status") != "passed" or semantic_release.get("passed") is not True:
        raise RuntimeError("Greenfield semantic release proof did not pass")
    for key in ("lower_capability_control_proof", "unavailable_provider_proof", "commit_recovery_proof"):
        if _mapping(base.get(key)).get("status") != "passed":
            raise RuntimeError(f"Greenfield {key} did not pass")

    revision = str(implementation_revision or "").strip().casefold()
    if len(revision) != 40 or any(character not in "0123456789abcdef" for character in revision):
        raise RuntimeError("Greenfield release qualification requires a full Git revision")
    ledger_file = _safe_json_file(
        final_holdout_ledger_path,
        label="Greenfield final holdout ledger",
    )
    if ledger_file != proof_root / "final-holdout-ledger.v3.json":
        raise RuntimeError("Greenfield final holdout ledger is outside the canonical release proof")
    ledger = read_final_holdout_run(ledger_file)
    if ledger.get("version") != FINAL_HOLDOUT_RUN_LEDGER_VERSION:
        raise RuntimeError("Greenfield final holdout ledger has an unsupported version")
    if ledger.get("status") != "passed":
        raise RuntimeError("Greenfield final holdout did not pass")
    if (
        ledger.get("disclosed") is not True
        or ledger.get("protected_inputs_bound") is not True
        or not _valid_protected_inputs(ledger.get("protected_inputs"))
    ):
        raise RuntimeError("Greenfield final holdout ledger lacks protected-input custody")
    if str(ledger.get("implementation_revision") or "").casefold() != revision:
        raise RuntimeError("Greenfield qualification belongs to a different implementation revision")
    if str(ledger.get("result_sha256") or "") != base_sha256:
        raise RuntimeError("Greenfield review does not qualify the final holdout result")
    ledger_retained = _mapping(ledger.get("retained_evidence"))
    if str(ledger_retained.get("manifest_sha256") or "") != retained_sha256:
        raise RuntimeError("Greenfield review does not qualify the final retained evidence")
    ledger_manifest = Path(str(ledger_retained.get("manifest_path") or "")).expanduser()
    if ledger_manifest.resolve() != retained_path:
        raise RuntimeError("Greenfield review and final holdout name different retained evidence")
    run_id = str(ledger.get("run_id") or "")
    if not is_sha256(run_id):
        raise RuntimeError("Greenfield final holdout lacks a valid run ID")
    retained = _json_object(retained_path, label="Greenfield retained evidence manifest")
    if retained.get("run_id") != run_id:
        raise RuntimeError("Greenfield final holdout and retained evidence have different run IDs")
    retained_issues = retained_evidence_manifest_issues(
        retained_path,
        require_passed_cases=True,
        expected_run_id=run_id,
    )
    if retained_issues:
        raise RuntimeError("Greenfield retained evidence changed: " + "; ".join(retained_issues))

    provenance_path = _safe_json_file(
        distribution_provenance_path,
        label="Greenfield distribution provenance",
    )
    if provenance_path != proof_root / "build-provenance.v1.json":
        raise RuntimeError("Greenfield distribution provenance is outside the canonical release proof")
    provenance = verify_distribution_provenance(
        provenance_path=provenance_path,
        implementation_revision=revision,
    )
    if provenance["sha256"] != str(ledger.get("distribution_provenance_sha256") or ""):
        raise RuntimeError("Greenfield final holdout and distribution provenance differ")

    return {
        "status": "passed",
        "implementation_revision": revision,
        "matrix_result_sha256": base_sha256,
        "retained_evidence_manifest_sha256": retained_sha256,
        "independent_review_package_sha256": review_sha256,
        "review_sidecar_sha256": sha256_file(sidecar_file),
        "final_holdout_ledger_sha256": sha256_file(ledger_file),
        "distribution_provenance_sha256": provenance["sha256"],
    }


def _valid_protected_inputs(value: Any) -> bool:
    inputs = _mapping(value)
    required = {"final_holdout", "evaluation_manifest", "lower_capability_control"}
    if not required.issubset(inputs):
        return False
    case_labels = sorted(label for label in inputs if str(label).startswith("case_file_"))
    if not case_labels or case_labels != [f"case_file_{index:03d}" for index in range(1, len(case_labels) + 1)]:
        return False
    if set(inputs) != required.union(case_labels):
        return False
    return all(
        isinstance(binding, Mapping)
        and str(binding.get("filename") or "").strip()
        and is_sha256(str(binding.get("sha256") or ""))
        for binding in inputs.values()
    )


def _bound_file(
    value: Any,
    *,
    path_key: str,
    sha_key: str,
    label: str,
) -> tuple[Path, str]:
    binding = _mapping(value)
    token = str(binding.get(path_key) or "").strip()
    expected_sha256 = str(binding.get(sha_key) or "").strip().casefold()
    if not token or not is_sha256(expected_sha256):
        raise RuntimeError(f"{label} binding is incomplete")
    path = _safe_json_file(Path(token), label=label)
    if sha256_file(path) != expected_sha256:
        raise RuntimeError(f"{label} bytes changed after review")
    return path, expected_sha256


def _safe_json_file(path: Path, *, label: str) -> Path:
    expanded = Path(path).expanduser()
    if expanded.is_symlink():
        raise RuntimeError(f"{label} is missing or unsafe")
    resolved = expanded.resolve()
    if not resolved.is_file():
        raise RuntimeError(f"{label} is missing or unsafe")
    return resolved


def _json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label} is unreadable") from exc
    if not isinstance(payload, Mapping):
        raise RuntimeError(f"{label} must be an object")
    return dict(payload)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sidecar", type=Path, required=True)
    parser.add_argument("--final-holdout-ledger", type=Path, required=True)
    parser.add_argument("--distribution-provenance", type=Path, required=True)
    parser.add_argument("--implementation-revision", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = verify_release_qualification(
        sidecar_path=args.sidecar,
        final_holdout_ledger_path=args.final_holdout_ledger,
        distribution_provenance_path=args.distribution_provenance,
        implementation_revision=args.implementation_revision,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["verify_release_qualification"]
