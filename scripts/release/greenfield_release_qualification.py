#!/usr/bin/env python3
"""Prepare one release package and authenticate its public and terminal proofs."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import subprocess
from typing import Any

from greenfield_distribution_provenance import verify_distribution_provenance
from greenfield_final_holdout_guard import (
    FINAL_HOLDOUT_RUN_LEDGER_VERSION,
    read_final_holdout_run,
)
from greenfield_matrix_release_artifacts import (
    is_sha256,
    _safe_file_without_symlinks,
    retained_evidence_manifest_issues,
    sha256_file,
)
from greenfield_onboarding_review import (
    ONBOARDING_REVIEW_PACKAGE_VERSION,
    ONBOARDING_REVIEW_SIDECAR_VERSION,
    build_onboarding_review_sidecar,
    _exclusive_write_json,
)


PREPARED_PACKAGE_VERSION = "odylith.greenfield.prepared-release-package.v1"


def _package_snapshot(*, proof_root: Path, session_path: Path, repo_root: Path,
                      implementation_revision: str, version: str) -> dict[str, Any]:
    """Bind a clean canonical source and every distribution byte before disclosure."""
    from greenfield_matrix_release_artifacts import _path_without_symlink_segments

    root = _path_without_symlink_segments(proof_root, label="release proof root").resolve()
    session = _json_object(_safe_file_without_symlinks(session_path, label="release session"), label="release session")
    revision = implementation_revision
    if (len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision)
            or root != session_path.expanduser().resolve().parent / "greenfield-release" / revision
            or session.get("head_sha") != revision or session.get("version") != version):
        raise RuntimeError("prepared package does not match its canonical release session/root")
    def git(*args: str) -> str:
        return subprocess.check_output(["git", "-C", str(repo_root), *args], text=True).strip()
    if git("rev-parse", "HEAD") != revision:
        raise RuntimeError("prepared package belongs to another source revision")
    if git("ls-files", "--others", "--exclude-standard"):
        raise RuntimeError("prepared release source has nonignored untracked files")
    for arguments in (("diff", "--quiet", "HEAD", "--"), ("diff", "--quiet", "--cached", "--")):
        subprocess.run(["git", "-C", str(repo_root), *arguments], check=True)
    dist = root / "dist"
    artifacts = {}
    for path in sorted(dist.iterdir()):
        _safe_file_without_symlinks(path, label="distribution artifact")
        artifacts[path.name] = sha256_file(path)
    required = {"install.sh", "release-manifest.json", "build-provenance.v1.json", "SHA256SUMS"}
    if not required.issubset(artifacts):
        raise RuntimeError("prepared package lacks required distribution artifacts")
    provenance = verify_distribution_provenance(
        provenance_path=dist / "build-provenance.v1.json", implementation_revision=revision)
    payload = _json_object(Path(provenance["path"]), label="distribution provenance")
    wheel = _mapping(_mapping(payload.get("artifacts")).get("wheel"))
    wheel_name = wheel.get("name")
    if (not isinstance(wheel_name, str) or Path(wheel_name).name != wheel_name
            or not wheel_name.endswith(".whl") or not is_sha256(wheel.get("sha256"))
            or artifacts.get(wheel_name) != wheel["sha256"]):
        raise RuntimeError("prepared package wheel differs from distribution provenance")
    manifest = _json_object(dist / "release-manifest.json", label="release manifest")
    if not manifest.get("assets") or any(artifacts.get(name) != row.get("sha256")
            for name, row in manifest["assets"].items()):
        raise RuntimeError("prepared package differs from its release manifest")
    logs = {}
    for phase in ("wheel", "assets", "smoke"):
        log = _safe_file_without_symlinks(root / "package-logs" / (phase + ".log"), label="package phase log")
        logs[phase] = {"path": str(log), "sha256": sha256_file(log)}
    return {"version": PREPARED_PACKAGE_VERSION, "status": "prepared",
        "implementation_revision": revision, "source_tree": git("rev-parse", "HEAD^{tree}"),
        "release_version": version, "proof_root": str(root), "distribution_root": str(dist),
        "session": {"path": str(session_path.expanduser().resolve()), "head_sha": revision, "version": version},
        "artifact_sha256": artifacts, "distribution_provenance": provenance, "build_logs": logs}


def prepare_release_package(**kwargs: Any) -> dict[str, Any]:
    """Seal a successfully built package; prepared never means release qualified."""
    snapshot = _package_snapshot(**kwargs)
    _exclusive_write_json(Path(snapshot["proof_root"]) / "prepared-package.v1.json", snapshot)
    return snapshot


def verify_prepared_release_package(**kwargs: Any) -> dict[str, Any]:
    snapshot = _package_snapshot(**kwargs)
    path = Path(snapshot["proof_root"]) / "prepared-package.v1.json"
    if _json_object(_safe_file_without_symlinks(path, label="prepared package"), label="prepared package") != snapshot:
        raise RuntimeError("prepared package source/session/distribution custody changed")
    return snapshot


def claim_terminal_release(*, composed_public_evidence_path: Path, **kwargs: Any) -> dict[str, Any]:
    """Authenticate public qualification before reserving the one terminal attempt."""
    snapshot = verify_prepared_release_package(**kwargs)
    root = Path(snapshot["proof_root"])
    if any((root / name).exists() or (root / name).is_symlink() for name in
           ("matrix-result.v1.json", "final-holdout-ledger.v3.json", "retained-evidence")):
        raise RuntimeError("terminal proof has already started; preserve it without replay")
    public = authenticate_composed_release_evidence(
        path=composed_public_evidence_path, implementation_revision=snapshot["implementation_revision"],
        distribution_root=Path(snapshot["distribution_root"]))
    if public["qualification"]["same_release_observations"].get("tree") != snapshot["source_tree"]:
        raise RuntimeError("composed public source tree differs from the prepared package")
    result = {"version": PREPARED_PACKAGE_VERSION + ".terminal-attempt.v1", "status": "claimed",
        "prepared_package_sha256": sha256_file(root / "prepared-package.v1.json"),
        "composed_public_evidence": public["evidence_ref"]}
    _exclusive_write_json(root / "terminal-attempt.v1.json", result)
    return result


def authenticate_composed_release_evidence(*, path: Path, implementation_revision: str,
                                         distribution_root: Path) -> dict[str, Any]:
    """Recompute the original composed qualification and bind its actual package."""
    from greenfield_public_qualification import qualify_composed_public_evidence, read_public_evidence_reference

    evidence_path = _safe_file_without_symlinks(path, label="composed public evidence")
    evidence_sha256 = sha256_file(evidence_path)
    evidence = _json_object(evidence_path, label="composed public evidence")
    report = qualify_composed_public_evidence(evidence=evidence)
    if report.get("status") != "passed" or report.get("passed") is not True:
        raise RuntimeError("composed public qualification did not pass: " + "; ".join(report.get("issues", ())))
    common = _mapping(report.get("same_release_observations"))
    dist = distribution_root.expanduser().resolve()
    declaration = read_public_evidence_reference(evidence["declaration"], label="composition declaration")
    provenance_ref = declaration["release_custody"]["build_provenance"]
    if (common.get("commit") != implementation_revision or common.get("distribution_root") != str(dist)
            or Path(provenance_ref["path"]).resolve() != dist / "build-provenance.v1.json"
            or provenance_ref["sha256"] != sha256_file(dist / "build-provenance.v1.json")):
        raise RuntimeError("composed public qualification belongs to another release package/revision")
    if sha256_file(evidence_path) != evidence_sha256:
        raise RuntimeError("composed public evidence changed during qualification")
    return {"evidence_ref": {"path": str(evidence_path), "sha256": evidence_sha256},
        "qualification": report}


def verify_terminal_release_claim(*, proof_root: Path, implementation_revision: str,
                                  distribution_root: Path, evidence_ref: Mapping[str, Any],
                                  distribution_provenance_path: Path) -> None:
    """Recheck the consumed package identity without reserving or replaying a journey."""
    root = proof_root.expanduser().resolve()
    receipt_path = _safe_file_without_symlinks(root / "prepared-package.v1.json", label="prepared package")
    receipt = _json_object(receipt_path, label="prepared package")
    dist = distribution_root.expanduser().resolve()
    if (receipt.get("version") != PREPARED_PACKAGE_VERSION or receipt.get("status") != "prepared"
            or receipt.get("implementation_revision") != implementation_revision
            or receipt.get("proof_root") != str(root) or receipt.get("distribution_root") != str(dist)
            or dist != root / "dist"):
        raise RuntimeError("terminal claim differs from its prepared package identity")
    artifacts = {path.name: sha256_file(_safe_file_without_symlinks(path, label="prepared distribution artifact"))
        for path in sorted(dist.iterdir())}
    if artifacts != receipt.get("artifact_sha256"):
        raise RuntimeError("terminal prepared distribution artifacts changed")
    provenance_path = _safe_file_without_symlinks(distribution_provenance_path, label="terminal distribution provenance")
    prepared_provenance = receipt.get("distribution_provenance", {})
    if (provenance_path != root / "build-provenance.v1.json"
            or prepared_provenance.get("path") != str(dist / "build-provenance.v1.json")
            or sha256_file(provenance_path) != prepared_provenance.get("sha256")):
        raise RuntimeError("terminal distribution provenance differs from the prepared package")
    for binding in receipt.get("build_logs", {}).values():
        _bound_file(binding, path_key="path", sha_key="sha256", label="prepared package phase log")
    claim = _json_object(_safe_file_without_symlinks(root / "terminal-attempt.v1.json", label="terminal attempt"), label="terminal attempt")
    expected = {"version": PREPARED_PACKAGE_VERSION + ".terminal-attempt.v1", "status": "claimed",
        "prepared_package_sha256": sha256_file(receipt_path), "composed_public_evidence": dict(evidence_ref)}
    if claim != expected:
        raise RuntimeError("terminal attempt has changed prepared/public evidence custody")


def authenticate_terminal_release_inputs(args: Any) -> dict[str, Any] | None:
    """Finish nonprotected prerequisites before the existing holdout owner is entered."""
    token = str(getattr(args, "composed_public_evidence", "") or "").strip()
    if not token:
        if str(getattr(args, "final_holdout_run_ledger", "") or "").strip():
            raise RuntimeError("terminal holdout requires qualified composed public evidence")
        return None
    if args.proof_tier != "release":
        raise RuntimeError("composed public evidence belongs only to terminal release proof")
    public = authenticate_composed_release_evidence(path=Path(token),
        implementation_revision=args.implementation_revision, distribution_root=Path(args.dist_dir))
    verify_terminal_release_claim(proof_root=Path(args.output_json).expanduser().resolve().parent,
        implementation_revision=args.implementation_revision, distribution_root=Path(args.dist_dir),
        evidence_ref=public["evidence_ref"], distribution_provenance_path=Path(args.distribution_provenance_file))
    return public


def terminal_composed_evidence(args: Any) -> Mapping[str, Any] | None:
    """Reauthenticate the original refs before the profile owner consumes them."""
    public = authenticate_terminal_release_inputs(args)
    return public["qualification"]["evidence_refs"] if public is not None else None


def terminal_public_evidence_reference(args: Any) -> dict[str, str] | None:
    token = str(getattr(args, "composed_public_evidence", "") or "").strip()
    if not token:
        return None
    path = _safe_file_without_symlinks(Path(token), label="composed public evidence")
    return {"path": str(path), "sha256": sha256_file(path)}


def authenticate_review_composition(*, base: Mapping[str, Any], base_path: Path,
                                    evidence_path: Path | None = None) -> dict[str, Any] | None:
    """A final review can authenticate, never introduce, terminal public evidence."""
    binding = base.get("composed_public_evidence")
    if binding is None:
        if evidence_path is not None:
            raise RuntimeError("review cannot add public composition to an earlier matrix")
        return None
    path, _ = _bound_file(binding, path_key="path", sha_key="sha256", label="terminal public composition")
    if evidence_path is not None and evidence_path.expanduser().resolve() != path:
        raise RuntimeError("review public composition differs from original terminal input")
    root = base_path.expanduser().resolve().parent
    receipt = _json_object(_safe_file_without_symlinks(root / "prepared-package.v1.json", label="prepared package"), label="prepared package")
    public = authenticate_composed_release_evidence(path=path,
        implementation_revision=receipt["implementation_revision"], distribution_root=root / "dist")
    if public["qualification"]["same_release_observations"].get("tree") != receipt.get("source_tree"):
        raise RuntimeError("reviewed public source tree differs from the prepared package")
    verify_terminal_release_claim(proof_root=root, implementation_revision=receipt["implementation_revision"],
        distribution_root=root / "dist", evidence_ref=public["evidence_ref"],
        distribution_provenance_path=root / "build-provenance.v1.json")
    if _mapping(_mapping(base.get("model_profile_proof")).get("measured_public_families")).get("evidence_refs") != public["qualification"]["evidence_refs"]:
        raise RuntimeError("terminal profile and public composition reference different families")
    from greenfield_model_profile_proof import model_profile_release_proof
    from greenfield_public_qualification import typed_saved_matrix_results
    rows = (*typed_saved_matrix_results(base.get("results")),
        *typed_saved_matrix_results(_mapping(base.get("lower_capability_control_proof")).get("results")))
    rebuilt = model_profile_release_proof(rows, require_complete=True,
        composed_public_evidence=public["qualification"]["evidence_refs"])
    if rebuilt.get("status") != "passed" or rebuilt != base.get("model_profile_proof"):
        raise RuntimeError("terminal model-profile proof differs from original observations/public bounds")
    return public


def verify_release_qualification(
    *,
    sidecar_path: Path,
    final_holdout_ledger_path: Path,
    distribution_provenance_path: Path,
    implementation_revision: str,
) -> dict[str, str]:
    """Fail closed unless one review qualifies the exact terminal holdout."""

    sidecar_file = _safe_file_without_symlinks(sidecar_path, label="Greenfield review sidecar")
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
    ledger_file = _safe_file_without_symlinks(
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

    provenance_path = _safe_file_without_symlinks(
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
    public = authenticate_review_composition(base=base, base_path=base_path)
    if public is None:
        raise RuntimeError("Greenfield release lacks its original qualified public composition")
    if _mapping(sidecar.get("composed_public_qualification")) != public:
        raise RuntimeError("Greenfield release sidecar and original public composition differ")
    declaration = public["qualification"]["same_release_observations"]
    if declaration.get("commit") != revision:
        raise RuntimeError("Greenfield public composition belongs to another implementation revision")

    return {
        "status": "passed",
        "implementation_revision": revision,
        "matrix_result_sha256": base_sha256,
        "retained_evidence_manifest_sha256": retained_sha256,
        "independent_review_package_sha256": review_sha256,
        "review_sidecar_sha256": sha256_file(sidecar_file),
        "final_holdout_ledger_sha256": sha256_file(ledger_file),
        "distribution_provenance_sha256": provenance["sha256"],
        "composed_public_evidence_sha256": public["evidence_ref"]["sha256"],
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
    path = _safe_file_without_symlinks(Path(token), label=label)
    if sha256_file(path) != expected_sha256:
        raise RuntimeError(f"{label} bytes changed after review")
    return path, expected_sha256


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
    parser.add_argument("--sidecar", type=Path)
    parser.add_argument("--final-holdout-ledger", type=Path)
    parser.add_argument("--distribution-provenance", type=Path)
    parser.add_argument("--implementation-revision", required=True)
    parser.add_argument("--package-phase", choices=("prepare", "claim"))
    parser.add_argument("--proof-root", type=Path)
    parser.add_argument("--session", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--version")
    parser.add_argument("--composed-public-evidence", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.package_phase:
        if any(value is None for value in (args.proof_root, args.session, args.repo_root, args.version)):
            raise RuntimeError("package phase requires proof root, release session, source root and version")
        kwargs = dict(proof_root=args.proof_root, session_path=args.session, repo_root=args.repo_root,
            implementation_revision=args.implementation_revision, version=args.version)
        if args.package_phase == "prepare":
            result = prepare_release_package(**kwargs)
        else:
            if args.composed_public_evidence is None:
                raise RuntimeError("terminal claim requires composed public evidence")
            result = claim_terminal_release(composed_public_evidence_path=args.composed_public_evidence, **kwargs)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if any(value is None for value in (args.sidecar, args.final_holdout_ledger, args.distribution_provenance)):
        raise RuntimeError("release qualification requires sidecar, final holdout ledger and distribution provenance")
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
