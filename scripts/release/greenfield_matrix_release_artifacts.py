"""Shared filesystem and digest checks for release-corpus evidence artifacts."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Iterator
from typing import Mapping


_SAFE_ARTIFACT_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]{0,127}\Z")
RELEASE_PROOF_INPUT_SNAPSHOT_VERSION = "odylith.greenfield.release-input-snapshot.v1"
RELEASE_PROOF_INPUT_SNAPSHOT_FILENAME = "release-proof-input-snapshot.v1.json"
RETAINED_EVIDENCE_VERSION = "odylith.greenfield.retained-evidence.v1"
RETAINED_CASE_EVIDENCE_VERSION = "odylith.greenfield.retained-case-evidence.v1"
RETAINED_EVIDENCE_FILENAME = "retained-evidence-manifest.v1.json"
RETAINED_CASE_EVIDENCE_FILENAME = "case-evidence-manifest.v1.json"


@dataclass(frozen=True)
class RetainedEvidenceCase:
    case_id: str
    staging_root: Path
    final_root: Path


def is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def is_sha256(value: str) -> bool:
    return bool(value) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def safe_artifact_identifier(value: str) -> str | None:
    """Return a portable identifier that is safe to use in an artifact filename."""

    candidate = str(value or "").strip()
    return candidate if _SAFE_ARTIFACT_IDENTIFIER.fullmatch(candidate) else None


def repo_artifact_path(root: Path, value: str) -> Path | None:
    candidate = Path(value)
    if not value or candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def retained_evidence_manifest_path(root: Path) -> Path:
    return Path(root).expanduser().resolve() / RETAINED_EVIDENCE_FILENAME


def validate_retained_evidence_output_dir(*, output_dir: Path, temp_parent: Path) -> Path:
    """Resolve an external evidence destination without accepting symlink crossings."""

    unresolved = _path_without_symlink_segments(output_dir, label="retained evidence output")
    evidence_root = unresolved.resolve()
    temp_root = _path_without_symlink_segments(temp_parent, label="matrix temp parent").resolve()
    if evidence_root == Path(evidence_root.anchor):
        raise RuntimeError("retained evidence output cannot be a filesystem root")
    if _contains(temp_root, evidence_root) or _contains(evidence_root, temp_root):
        raise RuntimeError("retained evidence output must be outside and disjoint from the matrix temp parent")
    return evidence_root


def prepare_retained_evidence_output_dir(*, output_dir: Path, temp_parent: Path) -> Path:
    """Create one new immutable release-evidence root before product execution."""

    root = validate_retained_evidence_output_dir(output_dir=output_dir, temp_parent=temp_parent)
    root.parent.mkdir(parents=True, exist_ok=True)
    _path_without_symlink_segments(root.parent, label="retained evidence parent")
    try:
        root.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise RuntimeError("retained evidence output already exists") from exc
    _fsync_directory(root.parent)
    return root


def begin_retained_case_evidence(*, evidence_root: Path, case_id: str) -> RetainedEvidenceCase:
    """Open an isolated case staging directory that will be atomically published."""

    root = _safe_directory(evidence_root, label="retained evidence output")
    token = safe_artifact_identifier(str(case_id or "").strip().casefold())
    if token is None:
        raise RuntimeError("retained evidence case id is unsafe")
    final_root = root / token
    if final_root.exists() or final_root.is_symlink():
        raise RuntimeError(f"retained evidence already exists for case {case_id}")
    staging_root = Path(tempfile.mkdtemp(prefix=f".{token}.", suffix=".staging", dir=root))
    return RetainedEvidenceCase(case_id=str(case_id), staging_root=staging_root, final_root=final_root)


def record_retained_case_json(case: RetainedEvidenceCase, relative_path: str, payload: Any) -> Path:
    return _write_case_bytes(
        case,
        relative_path,
        (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8"),
    )


def record_retained_case_text(case: RetainedEvidenceCase, relative_path: str, value: str) -> Path:
    return _write_case_bytes(case, relative_path, str(value or "").encode("utf-8"))


def record_retained_case_bytes(case: RetainedEvidenceCase, relative_path: str, value: bytes) -> Path:
    """Persist exact binary evidence through the same exclusive-write boundary."""

    return _write_case_bytes(case, relative_path, value)


@contextmanager
def retained_case_evidence_fd(
    case: RetainedEvidenceCase, relative_path: str
) -> Iterator[int]:
    """Grant one inherited descriptor without exposing an evidence path to product code."""

    root = _safe_directory(case.staging_root, label="retained case staging root")
    target = repo_artifact_path(root, relative_path)
    if target is None:
        raise RuntimeError("retained case evidence path is unsafe")
    target.parent.mkdir(parents=True, exist_ok=True)
    _path_without_symlink_segments(target.parent, label="retained case evidence parent")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags, 0o600)
    try:
        yield descriptor
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def seal_interrupted_retained_evidence(
    *,
    output_dir: Path,
    temp_parent: Path,
    result_path: Path,
    case_id: str = "final-holdout-interruption",
    run_id: str = "",
) -> Path:
    """Seal finalized and byte-exact partial evidence after a reaped release child."""

    root = validate_retained_evidence_output_dir(
        output_dir=output_dir,
        temp_parent=temp_parent,
    )
    if not root.exists():
        root = prepare_retained_evidence_output_dir(output_dir=root, temp_parent=temp_parent)
    elif not root.is_dir():
        raise RuntimeError("semantic release interruption evidence root is unsafe")
    manifest = retained_evidence_manifest_path(root)
    if manifest.is_file():
        issues = retained_evidence_manifest_issues(manifest, expected_run_id=run_id)
        if issues:
            raise RuntimeError("semantic release interruption evidence is invalid")
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping) or not payload.get("case_ids"):
            raise RuntimeError("semantic release interruption evidence contains no cases")
        return manifest

    finalized_case_ids: list[str] = []
    partial_entries: list[Path] = []
    for entry in sorted(root.iterdir()):
        if entry.is_symlink():
            raise RuntimeError("semantic release interruption evidence contains a symlink")
        case_manifest = entry / RETAINED_CASE_EVIDENCE_FILENAME if entry.is_dir() else None
        if case_manifest is not None and case_manifest.is_file():
            safe_manifest = _safe_file_without_symlinks(
                case_manifest,
                label="retained case evidence manifest",
            )
            payload = json.loads(safe_manifest.read_text(encoding="utf-8"))
            finalized_case_id = str(payload.get("case_id") or "") if isinstance(payload, Mapping) else ""
            if not finalized_case_id or finalized_case_id in finalized_case_ids:
                raise RuntimeError("semantic release interruption found invalid finalized evidence")
            finalized_case_ids.append(finalized_case_id)
        else:
            partial_entries.append(entry)

    result = _safe_file_without_symlinks(result_path, label="semantic release interruption result")
    result_payload = json.loads(result.read_text(encoding="utf-8"))
    if not isinstance(result_payload, Mapping):
        raise RuntimeError("semantic release interruption result is unreadable")
    interruption_case = begin_retained_case_evidence(evidence_root=root, case_id=case_id)
    record_retained_case_bytes(
        interruption_case,
        "interrupted/parent-result.v1.json",
        result.read_bytes(),
    )
    for index, entry in enumerate(partial_entries, start=1):
        sources = (entry,) if entry.is_file() else tuple(sorted(entry.rglob("*")))
        for source in sources:
            if source.is_symlink():
                raise RuntimeError("semantic release interruption evidence contains a symlink")
            if not source.is_file():
                continue
            relative = Path(entry.name) if entry.is_file() else Path(entry.name) / source.relative_to(entry)
            record_retained_case_bytes(
                interruption_case,
                f"interrupted/partial-{index:03d}/{relative.as_posix()}",
                source.read_bytes(),
            )
    finalize_retained_case_evidence(
        case=interruption_case,
        repo_root=temp_parent,
        result_payload=result_payload,
    )
    for entry in partial_entries:
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    return write_retained_evidence_manifest(
        root=root,
        expected_case_ids=(*finalized_case_ids, case_id),
        run_id=run_id,
    )


def finalize_retained_case_evidence(
    *,
    case: RetainedEvidenceCase,
    repo_root: Path,
    result_payload: Mapping[str, Any],
) -> Path:
    """Retain the case result and exact Greenfield after-image before temp cleanup."""

    root = _safe_directory(case.staging_root, label="retained case staging root")
    try:
        record_retained_case_json(case, "case-result.v1.json", dict(result_payload))
        _retain_greenfield_repository_evidence(
            case=case,
            repo_root=repo_root,
            result_payload=result_payload,
        )
        entries = _retained_case_entries(root)
        required_kinds = _required_case_evidence_kinds(result_payload)
        present_kinds = {str(entry["kind"]) for entry in entries}
        missing = sorted(required_kinds - present_kinds)
        if missing:
            raise RuntimeError("retained case evidence is incomplete: " + ", ".join(missing))
        manifest = {
            "version": RETAINED_CASE_EVIDENCE_VERSION,
            "case_id": case.case_id,
            "case_status": str(result_payload.get("status") or ""),
            "required_kinds": sorted(required_kinds),
            "artifacts": entries,
        }
        _write_case_bytes(
            case,
            RETAINED_CASE_EVIDENCE_FILENAME,
            (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        _fsync_tree(root)
        root.replace(case.final_root)
        _fsync_directory(case.final_root.parent)
        return case.final_root / RETAINED_CASE_EVIDENCE_FILENAME
    except BaseException:
        shutil.rmtree(root, ignore_errors=True)
        raise


def write_retained_evidence_manifest(
    *,
    root: Path,
    expected_case_ids: Sequence[str],
    run_id: str = "",
) -> Path:
    """Seal all atomically published case packages into one hash-verifiable manifest."""

    evidence_root = _safe_directory(root, label="retained evidence output")
    run_binding = str(run_id or "").strip().casefold()
    if run_binding and not is_sha256(run_binding):
        raise RuntimeError("retained evidence run id is invalid")
    expected = tuple(str(value) for value in expected_case_ids)
    case_manifests: list[dict[str, Any]] = []
    for case_id in expected:
        token = safe_artifact_identifier(case_id.strip().casefold())
        if token is None:
            raise RuntimeError("retained evidence case id is unsafe")
        manifest = evidence_root / token / RETAINED_CASE_EVIDENCE_FILENAME
        issues = _retained_case_evidence_issues(manifest, expected_case_id=case_id)
        if issues:
            raise RuntimeError("retained case evidence failed validation: " + "; ".join(issues))
        case_manifests.append(
            {
                "case_id": case_id,
                "path": manifest.relative_to(evidence_root).as_posix(),
                "sha256": sha256_file(manifest),
            }
        )
    extras = [
        path.name
        for path in evidence_root.iterdir()
        if path.name != RETAINED_EVIDENCE_FILENAME
        and path.name not in {str(row["path"]).split("/", 1)[0] for row in case_manifests}
    ]
    if extras:
        raise RuntimeError("retained evidence output contains unsealed entries: " + ", ".join(sorted(extras)))
    manifest_path = evidence_root / RETAINED_EVIDENCE_FILENAME
    payload = {
        "version": RETAINED_EVIDENCE_VERSION,
        "evidence_root": str(evidence_root),
        "run_id": run_binding,
        "case_ids": list(expected),
        "case_manifests": case_manifests,
    }
    _exclusive_write_bytes(
        manifest_path,
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    _fsync_directory(evidence_root)
    return manifest_path


def retained_evidence_manifest_issues(
    manifest_path: Path,
    *,
    expected_case_ids: Sequence[str] = (),
    require_passed_cases: bool = False,
    expected_run_id: str = "",
) -> tuple[str, ...]:
    """Verify manifest custody, every retained byte, and exact case coverage."""

    try:
        manifest = _safe_file_without_symlinks(manifest_path, label="retained evidence manifest")
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        return (f"retained evidence manifest is missing or unsafe: {exc}",)
    if not isinstance(payload, Mapping):
        return ("retained evidence manifest must be an object",)
    root = manifest.parent.resolve()
    issues: list[str] = []
    if payload.get("version") != RETAINED_EVIDENCE_VERSION:
        issues.append("retained evidence manifest has an unsupported version")
    if str(payload.get("evidence_root") or "") != str(root):
        issues.append("retained evidence manifest does not bind its evidence root")
    manifest_run_id = str(payload.get("run_id") or "")
    if manifest_run_id and not is_sha256(manifest_run_id):
        issues.append("retained evidence manifest has an invalid run id")
    if expected_run_id and manifest_run_id != str(expected_run_id):
        issues.append("retained evidence manifest belongs to a different final holdout run")
    case_ids = payload.get("case_ids")
    manifests = payload.get("case_manifests")
    if not isinstance(case_ids, list) or not all(isinstance(value, str) and value for value in case_ids):
        issues.append("retained evidence manifest has invalid case ids")
        case_ids = []
    if expected_case_ids and list(expected_case_ids) != case_ids:
        issues.append("retained evidence manifest does not cover the expected cases")
    if require_passed_cases and not case_ids:
        issues.append("passing retained evidence must contain at least one case")
    if not isinstance(manifests, list) or len(manifests) != len(case_ids):
        issues.append("retained evidence manifest has invalid case manifest coverage")
        manifests = []
    bound_roots: set[str] = set()
    for index, row in enumerate(manifests):
        if not isinstance(row, Mapping):
            issues.append("retained evidence manifest has an invalid case reference")
            continue
        case_id = str(row.get("case_id") or "")
        relative = str(row.get("path") or "")
        expected_hash = str(row.get("sha256") or "")
        artifact = repo_artifact_path(root, relative)
        if case_id != case_ids[index]:
            issues.append("retained evidence manifest case order is inconsistent")
        if artifact is None:
            issues.append(f"retained evidence case manifest path is unsafe: {relative}")
            continue
        try:
            artifact = _safe_file_without_symlinks(artifact, label="retained case manifest")
        except RuntimeError as exc:
            issues.append(str(exc))
            continue
        if not is_sha256(expected_hash) or sha256_file(artifact) != expected_hash:
            issues.append(f"retained evidence case manifest hash changed: {case_id}")
        issues.extend(
            _retained_case_evidence_issues(
                artifact,
                expected_case_id=case_id,
                expected_case_status="passed" if require_passed_cases else "",
            )
        )
        bound_roots.add(relative.split("/", 1)[0])
    try:
        actual_roots = {
            path.name
            for path in root.iterdir()
            if path.name != RETAINED_EVIDENCE_FILENAME
        }
    except OSError as exc:
        issues.append(f"retained evidence output is unreadable: {exc}")
    else:
        if actual_roots != bound_roots:
            issues.append("retained evidence output contains unbound or missing case packages")
    return tuple(dict.fromkeys(issues))


def _retain_greenfield_repository_evidence(
    *,
    case: RetainedEvidenceCase,
    repo_root: Path,
    result_payload: Mapping[str, Any],
) -> None:
    source_root = Path(repo_root).expanduser().resolve()
    evidence = result_payload.get("evidence")
    evidence = evidence if isinstance(evidence, Mapping) else {}
    receipt = evidence.get("preconfirm_dry_run")
    receipt = receipt if isinstance(receipt, Mapping) else {}
    transaction_file = str(receipt.get("transaction_file") or "").strip()
    compiler_receipt_file = str(receipt.get("compiler_receipt_file") or "").strip()
    transaction_hash = str(receipt.get("transaction_hash") or "").strip()
    for relative, destination in (
        (transaction_file, "semantic/product-create-transaction.v1.json"),
        (compiler_receipt_file, "semantic/product-create-transaction.compiler-receipt.v1.json"),
        (
            ".odylith/runtime/greenfield/active-generation.v1.json",
            "semantic/active-generation.v1.json",
        ),
    ):
        if not relative:
            continue
        source = repo_artifact_path(source_root, relative)
        if source is not None and source.exists():
            _copy_case_source(case, source_root=source_root, source=source, destination=destination)
    if not is_sha256(transaction_hash):
        return
    generation = source_root / ".odylith/runtime/greenfield/generations" / transaction_hash
    manifest = generation / "generation-manifest.v1.json"
    if manifest.exists():
        _copy_case_source(
            case,
            source_root=source_root,
            source=manifest,
            destination="semantic/generation-manifest.v1.json",
        )
    repository = generation / "repository"
    if not repository.exists():
        return
    _safe_directory(repository, label="immutable Greenfield generation repository")
    for source in sorted(repository.rglob("*")):
        if source.is_symlink():
            raise RuntimeError("immutable Greenfield generation contains a symlink")
        if source.is_file():
            relative = source.relative_to(repository).as_posix()
            _copy_case_source(
                case,
                source_root=repository,
                source=source,
                destination=f"generated/{relative}",
            )


def _copy_case_source(
    case: RetainedEvidenceCase,
    *,
    source_root: Path,
    source: Path,
    destination: str,
) -> None:
    root = Path(source_root).expanduser().resolve()
    safe_source = _safe_file_without_symlinks(source, label="retained evidence source")
    try:
        safe_source.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("retained evidence source escaped its owning root") from exc
    _write_case_bytes(case, destination, safe_source.read_bytes())


def _required_case_evidence_kinds(result_payload: Mapping[str, Any]) -> set[str]:
    required = {"case_result"}
    evidence = result_payload.get("evidence")
    evidence = evidence if isinstance(evidence, Mapping) else {}
    receipt = evidence.get("preconfirm_dry_run")
    receipt = receipt if isinstance(receipt, Mapping) else {}
    browser = evidence.get("browser_surface_proof")
    browser = browser if isinstance(browser, Mapping) else {}
    if str(result_payload.get("status") or "") == "passed":
        required.update(("command_stream", "semantic_receipt"))
    if str(result_payload.get("status") or "") == "passed" and receipt.get("status") == "compiled":
        required.add("generated_artifact")
        required.add("rendered_atlas_asset")
    if browser.get("required") is True and browser.get("attempted") is True:
        required.add("browser_screenshot")
    return required


def _retained_case_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("retained case evidence contains a symlink")
        if not path.is_file() or path.name == RETAINED_CASE_EVIDENCE_FILENAME:
            continue
        relative = path.relative_to(root).as_posix()
        entries.append(
            {
                "kind": _retained_artifact_kind(relative),
                "path": relative,
                "sha256": sha256_file(path),
                "byte_count": path.stat().st_size,
            }
        )
    return entries


def _retained_artifact_kind(relative_path: str) -> str:
    if relative_path == "case-result.v1.json":
        return "case_result"
    if relative_path.startswith("commands/"):
        return "command_stream"
    if relative_path.startswith("browser/") and relative_path.endswith(".png"):
        return "browser_screenshot"
    if relative_path.startswith("semantic/"):
        return "semantic_receipt"
    if relative_path.startswith("generated/odylith/atlas/source/") and relative_path.endswith((".svg", ".png")):
        return "rendered_atlas_asset"
    if relative_path.startswith("generated/"):
        return "generated_artifact"
    return "supporting_evidence"


def _retained_case_evidence_issues(
    manifest_path: Path,
    *,
    expected_case_id: str,
    expected_case_status: str = "",
) -> tuple[str, ...]:
    try:
        manifest = _safe_file_without_symlinks(manifest_path, label="retained case evidence manifest")
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        return (f"retained case evidence manifest is missing or unsafe: {exc}",)
    if not isinstance(payload, Mapping):
        return ("retained case evidence manifest must be an object",)
    root = manifest.parent
    issues: list[str] = []
    if payload.get("version") != RETAINED_CASE_EVIDENCE_VERSION:
        issues.append("retained case evidence manifest has an unsupported version")
    if str(payload.get("case_id") or "") != str(expected_case_id):
        issues.append("retained case evidence manifest has the wrong case id")
    if expected_case_status and str(payload.get("case_status") or "") != expected_case_status:
        issues.append(f"retained case evidence for {expected_case_id} is not passed")
    required = payload.get("required_kinds")
    artifacts = payload.get("artifacts")
    if not isinstance(required, list) or not all(isinstance(value, str) and value for value in required):
        issues.append("retained case evidence manifest has invalid required kinds")
        required = []
    if not isinstance(artifacts, list) or not artifacts:
        issues.append("retained case evidence manifest has no artifacts")
        artifacts = []
    bound_paths: set[str] = set()
    kinds: set[str] = set()
    for row in artifacts:
        if not isinstance(row, Mapping):
            issues.append("retained case evidence manifest has an invalid artifact")
            continue
        relative = str(row.get("path") or "")
        kind = str(row.get("kind") or "")
        expected_hash = str(row.get("sha256") or "")
        expected_bytes = row.get("byte_count")
        artifact = repo_artifact_path(root, relative)
        if artifact is None:
            issues.append(f"retained case evidence path is unsafe: {relative}")
            continue
        try:
            artifact = _safe_file_without_symlinks(artifact, label="retained case artifact")
        except RuntimeError as exc:
            issues.append(str(exc))
            continue
        if relative in bound_paths:
            issues.append(f"retained case evidence path is duplicated: {relative}")
        bound_paths.add(relative)
        kinds.add(kind)
        if kind != _retained_artifact_kind(relative):
            issues.append(f"retained case evidence kind is invalid: {relative}")
        if not is_sha256(expected_hash) or sha256_file(artifact) != expected_hash:
            issues.append(f"retained case evidence hash changed: {relative}")
        if not isinstance(expected_bytes, int) or expected_bytes != artifact.stat().st_size:
            issues.append(f"retained case evidence byte count changed: {relative}")
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != RETAINED_CASE_EVIDENCE_FILENAME
    }
    if any(path.is_symlink() for path in root.rglob("*")):
        issues.append("retained case evidence contains a symlink")
    if actual_paths != bound_paths:
        issues.append("retained case evidence contains unbound or missing artifacts")
    missing = sorted(set(required) - kinds)
    if missing:
        issues.append("retained case evidence is missing required kinds: " + ", ".join(missing))
    return tuple(dict.fromkeys(issues))


def _write_case_bytes(case: RetainedEvidenceCase, relative_path: str, payload: bytes) -> Path:
    root = _safe_directory(case.staging_root, label="retained case staging root")
    target = repo_artifact_path(root, relative_path)
    if target is None:
        raise RuntimeError("retained case evidence path is unsafe")
    target.parent.mkdir(parents=True, exist_ok=True)
    _path_without_symlink_segments(target.parent, label="retained case evidence parent")
    _exclusive_write_bytes(target, payload)
    return target


def _exclusive_write_bytes(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _safe_directory(path: Path, *, label: str) -> Path:
    candidate = _path_without_symlink_segments(path, label=label).resolve()
    if not candidate.is_dir():
        raise RuntimeError(f"{label} is missing or unsafe")
    return candidate


def _safe_file_without_symlinks(path: Path, *, label: str) -> Path:
    candidate = _path_without_symlink_segments(path, label=label).resolve()
    if not candidate.is_file():
        raise RuntimeError(f"{label} is missing or unsafe")
    return candidate


def _path_without_symlink_segments(path: Path, *, label: str) -> Path:
    expanded = Path(path).expanduser()
    absolute = expanded if expanded.is_absolute() else Path.cwd() / expanded
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            raise RuntimeError(f"{label} crosses a symlink")
    return absolute


def _contains(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def _fsync_tree(root: Path) -> None:
    directories = [root, *(path for path in root.rglob("*") if path.is_dir())]
    for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        _fsync_directory(path)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def release_proof_input_snapshot_manifest_path(root: Path) -> Path:
    return Path(root).expanduser().resolve() / RELEASE_PROOF_INPUT_SNAPSHOT_FILENAME


def write_release_proof_input_snapshot_manifest(
    *,
    root: Path,
    case_files: Sequence[Path],
    audit_file: Path,
    input_references: Sequence[Mapping[str, Any]],
) -> Path:
    """Persist the immutable input contract consumed by one release-proof shard."""

    snapshot_root = Path(root).expanduser().resolve()
    manifest_path = release_proof_input_snapshot_manifest_path(snapshot_root)
    payload = {
        "version": RELEASE_PROOF_INPUT_SNAPSHOT_VERSION,
        "snapshot_root": str(snapshot_root),
        "case_files": [_snapshot_relative_path(snapshot_root, path) for path in case_files],
        "audit_file": _snapshot_relative_path(snapshot_root, audit_file),
        "input_references": [
            {
                "kind": str(reference.get("kind") or "release-proof-input"),
                "path": _snapshot_relative_path(snapshot_root, Path(str(reference.get("path") or ""))),
                "sha256": str(reference.get("sha256") or ""),
            }
            for reference in input_references
        ],
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def release_proof_input_snapshot_issues(
    *,
    root: Path,
    case_files: Sequence[Path],
    audit_file: Path,
) -> tuple[str, ...]:
    """Validate a campaign-created snapshot before any release evidence is loaded."""

    snapshot_root = Path(root).expanduser().resolve()
    manifest_path = release_proof_input_snapshot_manifest_path(snapshot_root)
    if not manifest_path.is_file():
        return ("release proof sealed input manifest is missing",)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (f"release proof sealed input manifest is unreadable: {exc}",)
    if not isinstance(payload, Mapping):
        return ("release proof sealed input manifest must be an object",)
    if payload.get("version") != RELEASE_PROOF_INPUT_SNAPSHOT_VERSION:
        return ("release proof sealed input manifest has an unsupported version",)
    if str(payload.get("snapshot_root") or "") != str(snapshot_root):
        return ("release proof sealed input manifest does not bind this input root",)

    expected_cases = tuple(_snapshot_relative_path(snapshot_root, path) for path in case_files)
    expected_audit = _snapshot_relative_path(snapshot_root, audit_file)
    if payload.get("case_files") != list(expected_cases) or payload.get("audit_file") != expected_audit:
        return ("release proof sealed input manifest does not match the selected case and audit files",)

    references = payload.get("input_references")
    if not isinstance(references, list) or not references:
        return ("release proof sealed input manifest has no hash-bound inputs",)
    issues: list[str] = []
    bound_paths: set[str] = set()
    for reference in references:
        if not isinstance(reference, Mapping):
            issues.append("release proof sealed input manifest has an invalid input reference")
            continue
        relative_path = str(reference.get("path") or "")
        expected_hash = str(reference.get("sha256") or "")
        artifact = repo_artifact_path(snapshot_root, relative_path)
        if artifact is None or not artifact.is_file():
            issues.append(f"release proof sealed input is missing: {relative_path or '<unnamed>'}")
            continue
        if not is_sha256(expected_hash):
            issues.append(f"release proof sealed input is not hash-bound: {relative_path}")
            continue
        if sha256_file(artifact) != expected_hash:
            issues.append(f"release proof sealed input hash changed: {relative_path}")
            continue
        bound_paths.add(relative_path)
    if expected_audit not in bound_paths or any(path not in bound_paths for path in expected_cases):
        issues.append("release proof sealed input manifest does not bind every selected case and audit file")
    return tuple(dict.fromkeys(issues))


def _snapshot_relative_path(root: Path, path: Path) -> str:
    candidate = Path(path).expanduser().resolve()
    try:
        return str(candidate.relative_to(root))
    except ValueError as exc:
        raise RuntimeError(f"release proof snapshot input is outside the sealed root: {candidate}") from exc
