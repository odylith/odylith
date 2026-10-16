#!/usr/bin/env python3
"""Prepare one release package and authenticate its public and terminal proofs."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
import os
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath
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


PREPARED_PACKAGE_VERSION = "odylith.greenfield.prepared-release-package.v2"
RELEASE_CUSTODY_REFS = frozenset(("checkpoint", "prepared_package", "activation", "profile"))
PREPARED_PACKAGE_FIELDS = frozenset(("version", "status", "implementation_revision", "source_tree", "source_repository",
    "release_version", "proof_root", "distribution_root", "session", "source_archive", "source_export", "artifact_sha256",
    "distribution_provenance", "build_logs", "wheel_source_bindings", "checksum_observations", "manifest_observations"))


def _source_git(repo: Path, *args: str, input_data: bytes | None = None) -> bytes:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    try:
        return subprocess.check_output(["git", "--no-replace-objects", "-C", str(repo), *args], env=environment, input=input_data)
    except subprocess.CalledProcessError as error:
        raise RuntimeError("immutable release source object is unavailable") from error


def _primary_repository(repo: Path) -> Path:
    from greenfield_matrix_release_artifacts import _path_without_symlink_segments
    repo = _path_without_symlink_segments(repo, label="source repository")
    if (not repo.is_absolute() or not repo.is_dir() or repo != repo.resolve()
            or _source_git(repo, "rev-parse", "--show-toplevel").decode().strip() != str(repo)):
        raise RuntimeError("source repository is not a safe absolute toplevel")
    common = Path(_source_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip())
    _path_without_symlink_segments(common, label="Git common directory")
    entries = [entry.removeprefix(b"worktree ").decode() for entry in
               _source_git(repo, "worktree", "list", "--porcelain", "-z").split(b"\0") if entry.startswith(b"worktree ")]
    if not entries or len(entries) != len(set(entries)):
        raise RuntimeError("release source has missing or ambiguous primary metadata")
    primary = _path_without_symlink_segments(Path(entries[0]), label="primary source repository")
    if not primary.is_absolute() or not primary.is_dir() or primary != primary.resolve():
        raise RuntimeError("release primary repository is missing or unsafe")
    git_dir = Path(_source_git(primary, "rev-parse", "--path-format=absolute", "--git-dir").decode().strip())
    _path_without_symlink_segments(git_dir, label="primary Git directory")
    if (not common.is_absolute() or not common.is_dir() or common != common.resolve() or git_dir != common
            or _source_git(primary, "rev-parse", "--show-toplevel").decode().strip() != str(primary)
            or _source_git(primary, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip() != str(common)):
        raise RuntimeError("release primary repository does not own the build common object store")
    return primary


def _require_build_source(repo: Path, revision: str) -> None:
    _source_inventory(repo, revision)
    if (_source_git(repo, "rev-parse", "HEAD").decode().strip() != revision
            or _source_git(repo, "status", "--porcelain").strip()):
        raise RuntimeError("release capture requires its clean canonical build source")


def _source_inventory(repo: Path, revision: str) -> tuple[str, dict[str, tuple[str, str]]]:
    from greenfield_matrix_release_artifacts import _path_without_symlink_segments
    if (not isinstance(revision, str) or len(revision) != 40
            or any(char not in "0123456789abcdef" for char in revision)):
        raise RuntimeError("release source requires an exact commit identity")
    safe = _path_without_symlink_segments(repo, label="source repository")
    if not safe.is_dir() or safe != safe.resolve() or _source_git(safe, "rev-parse", "--show-toplevel").decode().strip() != str(safe):
        raise RuntimeError("release source repository is not its safe canonical root")
    if _source_git(repo, "cat-file", "-t", revision).strip() != b"commit":
        raise RuntimeError("release source identity is not a commit")
    inventory = {}
    for entry in _source_git(repo, "ls-tree", "-rz", revision).split(b"\0"):
        if not entry:
            continue
        header, name_bytes = entry.split(b"\t", 1)
        mode, kind, identity = header.decode().split()
        name = name_bytes.decode()
        if (kind != "blob" or mode not in {"100644", "100755"} or name in inventory
                or PurePosixPath(name).as_posix() != name or ".." in PurePosixPath(name).parts):
            raise RuntimeError("release source contains unsupported or repeated owners")
        inventory[name] = (mode, identity)
    identities = sorted({identity for _, identity in inventory.values()})
    rows = _source_git(repo, "cat-file", "--batch-check", input_data=("\n".join(identities) + "\n").encode()).splitlines()
    if len(rows) != len(identities) or any(len(row.split()) != 3 or row.split()[:2] != [identity.encode(), b"blob"] for identity, row in zip(identities, rows)):
        raise RuntimeError("immutable release source blob is unavailable")
    return _source_git(repo, "rev-parse", revision + "^{tree}").decode().strip(), inventory


def _source_custody(root: Path, repo: Path, revision: str, *, extract: bool = False) -> tuple[str, dict[str, Any], dict[str, Any]]:
    from odylith.install.archive_safety import extract_validated_archive, validate_archive_members
    from greenfield_matrix_release_artifacts import _path_without_symlink_segments
    tree, inventory = _source_inventory(repo, revision)
    archive_path = _safe_file_without_symlinks(root / "source.tar.gz", label="source archive")
    export = _path_without_symlink_segments(root / "source-export", label="source export")
    directories = {"source-export", *(str(parent) for name in inventory
        for parent in (PurePosixPath("source-export") / name).parents if str(parent) != ".")}
    expected_files = {"source-export/" + name for name in inventory}
    files = {}
    try:
        archive = tarfile.open(archive_path, "r:gz")
    except (OSError, tarfile.TarError) as error:
        raise RuntimeError("release source archive is unreadable") from error
    with archive:
        members = archive.getmembers()
        names = [PurePosixPath(member.name).as_posix() for member in members]
        if (len(names) != len(set(names))
                or any(member.name not in ({name, name + "/"} if member.isdir() else {name}) for member, name in zip(members, names))):
            raise RuntimeError("source archive contains duplicate or noncanonical members")
        validate_archive_members(members=members, expected_root="source-export", label="source archive")
        if ({member.name.rstrip("/") for member in members if member.isdir()} != directories
                or {member.name for member in members if member.isfile()} != expected_files
                or any(not member.isdir() and not member.isfile() for member in members)):
            raise RuntimeError("source archive differs from complete Git member/type census")
        for member in members:
            if not member.isfile():
                continue
            name = member.name.removeprefix("source-export/")
            blob = hashlib.sha1(b"blob " + str(member.size).encode() + b"\0")
            digest = hashlib.sha256()
            with archive.extractfile(member) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    blob.update(chunk)
                    digest.update(chunk)
            if blob.hexdigest() != inventory[name][1] or bool(member.mode & 0o111) != (inventory[name][0] == "100755"):
                raise RuntimeError("source archive bytes or mode differ from immutable Git blob")
            files[name] = digest.hexdigest()
    if extract:
        if export.exists():
            raise FileExistsError(export)
        extract_validated_archive(archive_path=archive_path, destination=root, expected_root="source-export", label="source archive")
    if not export.is_dir():
        raise RuntimeError("source export is missing")
    actual_files, actual_directories = set(), {"source-export"}
    for path in export.rglob("*"):
        _path_without_symlink_segments(path, label="source export member")
        if path.is_dir():
            actual_directories.add("source-export/" + path.relative_to(export).as_posix())
        elif path.is_file():
            name = path.relative_to(export).as_posix()
            actual_files.add(name)
            if (name not in files or sha256_file(path) != files[name]
                    or bool(path.stat().st_mode & 0o111) != (inventory[name][0] == "100755")):
                raise RuntimeError("source export bytes differ from immutable archive")
        else:
            raise RuntimeError("source export contains an unsupported member")
    if actual_files != set(files) or actual_directories != directories:
        raise RuntimeError("source export differs from complete archive census")
    return tree, {"path": str(archive_path), "sha256": sha256_file(archive_path)}, {"path": str(export), "files": files}


def _package_bindings(dist: Path, artifacts: Mapping[str, str], export: Mapping[str, Any], wheel_name: str, version: str) -> dict[str, Any]:
    from odylith.install.managed_runtime import supported_managed_runtime_platforms, supported_managed_runtime_feature_packs
    source = Path(export["path"])
    config = tomllib.loads((source / "pyproject.toml").read_text())
    if config.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {}).get("packages") != ["src/odylith"]:
        raise RuntimeError("release package root differs from the declared Hatch contract")
    expected = {name.removeprefix("src/"): digest for name, digest in export["files"].items() if name.startswith("src/odylith/")}
    if not expected:
        raise RuntimeError("release package has no committed source owners")
    metadata = "odylith-" + version + ".dist-info/"
    metadata_names = {metadata + name for name in ("METADATA", "WHEEL", "RECORD", "entry_points.txt", "top_level.txt",
        "licenses/LICENSE", "licenses/NOTICE", "licenses/THIRD_PARTY_ATTRIBUTION.md", "extra_metadata/THIRD_PARTY_ATTRIBUTION.md")}
    try:
        with zipfile.ZipFile(dist / wheel_name) as wheel:
            names = wheel.namelist()
            canonical_names = [name.rstrip("/") for name in names]
            if (len(canonical_names) != len(set(canonical_names))
                    or any(PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
                           or name not in {PurePosixPath(name).as_posix(), PurePosixPath(name).as_posix() + "/"} for name in names)
                    or any((info.external_attr >> 16) & 0o170000 not in ({0, 0o040000} if info.is_dir() else {0, 0o100000}) for info in wheel.infolist())):
                raise RuntimeError("wheel contains duplicate or noncanonical members")
            regular = {info.filename for info in wheel.infolist() if not info.is_dir()}
            directories = {info.filename.rstrip("/") for info in wheel.infolist() if info.is_dir()}
            parents = {str(parent) for name in regular for parent in PurePosixPath(name).parents if str(parent) != "."}
            if (not directories <= parents or {name for name in regular if name.startswith("odylith/")} != set(expected)
                    or regular - set(expected) - metadata_names
                    or not {metadata + name for name in ("METADATA", "WHEEL", "RECORD")} <= regular):
                raise RuntimeError("wheel differs from complete package/metadata owner census")
            for name, digest in expected.items():
                with wheel.open(name) as stream:
                    if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                        raise RuntimeError("wheel source bytes differ from immutable Git source")
    except zipfile.BadZipFile as error:
        raise RuntimeError("release wheel is not a valid ZIP") from error
    provenance = _json_object(dist / "build-provenance.v1.json", label="distribution provenance")["artifacts"]
    platforms = supported_managed_runtime_platforms()
    runtimes = {platform.slug: platform.asset_name for platform in platforms}
    packs = {pack.pack_id: {platform.slug: pack.asset_name(platform) for platform in platforms}
             for pack in supported_managed_runtime_feature_packs()}
    if set(provenance) != {"wheel", "runtime_bundles", "feature_packs"} or set(provenance["runtime_bundles"]) != set(runtimes) or set(provenance["feature_packs"]) != set(packs):
        raise RuntimeError("release provenance has incomplete publisher asset families")
    declared = [(provenance["wheel"], wheel_name)]
    declared.extend((provenance["runtime_bundles"][key], name) for key, name in runtimes.items())
    for key, assets in packs.items():
        if set(provenance["feature_packs"][key]) != set(assets):
            raise RuntimeError("release provenance has incomplete feature-pack assets")
        declared.extend((provenance["feature_packs"][key][platform], name) for platform, name in assets.items())
    payload_names = {"install.sh", "release-manifest.json", "build-provenance.v1.json", "SHA256SUMS", "odylith.sbom.spdx.json", "THIRD_PARTY_ATTRIBUTION.md"}
    for row, name in declared:
        if (not isinstance(row, Mapping) or set(row) != {"name", "sha256"} or row["name"] != name
                or name in payload_names or artifacts.get(name) != row["sha256"]):
            raise RuntimeError("release provenance asset identity or bytes differ")
        payload_names.add(name)
    checksums = {}
    for line in (dist / "SHA256SUMS").read_text().splitlines():
        parts = line.split("  ")
        if len(parts) != 2 or not is_sha256(parts[0]) or Path(parts[1]).name != parts[1] or parts[1] in checksums:
            raise RuntimeError("release checksums contain malformed or repeated members")
        checksums[parts[1]] = parts[0]
    signatures = {name for name in artifacts if name.endswith(".sigstore.json")}
    payload = set(artifacts) - signatures
    if (payload != payload_names or set(checksums) != payload - {"SHA256SUMS"}
            or signatures != {name + ".sigstore.json" for name in checksums}
            or any(artifacts.get(name) != digest for name, digest in checksums.items())):
        raise RuntimeError("release checksum/signature census or bytes differ")
    manifest = _json_object(dist / "release-manifest.json", label="release manifest")
    assets = manifest.get("assets")
    if (not isinstance(assets, Mapping) or set(assets) != set(checksums) - {"release-manifest.json"}
            or any(not isinstance(row, Mapping) or set(row) != {"sha256"} or row["sha256"] != artifacts[name] for name, row in assets.items())):
        raise RuntimeError("release manifest census or bytes differ")
    return {"wheel_source_bindings": [{"source_path": "src/" + name, "wheel_path": name, "sha256": digest}
            for name, digest in sorted(expected.items())], "checksum_observations": checksums,
            "manifest_observations": {name: row["sha256"] for name, row in assets.items()}}


def _package_snapshot(*, proof_root: Path, session_path: Path, repo_root: Path,
                      implementation_revision: str, version: str) -> dict[str, Any]:
    from greenfield_matrix_release_artifacts import _path_without_symlink_segments
    root = _path_without_symlink_segments(proof_root, label="release proof root").resolve()
    repo = _path_without_symlink_segments(repo_root, label="source repository").resolve()
    session = _json_object(_safe_file_without_symlinks(session_path, label="release session"), label="release session")
    revision = implementation_revision
    if (root != session_path.expanduser().resolve().parent / "greenfield-release" / revision
            or session.get("head_sha") != revision or session.get("version") != version):
        raise RuntimeError("prepared package does not match its canonical release session/root")
    tree, archive, export = _source_custody(root, repo, revision)
    dist = root / "dist"
    artifacts = {path.name: sha256_file(_safe_file_without_symlinks(path, label="distribution artifact")) for path in sorted(dist.iterdir())}
    if not {"install.sh", "release-manifest.json", "build-provenance.v1.json", "SHA256SUMS"} <= set(artifacts):
        raise RuntimeError("prepared package lacks required distribution artifacts")
    provenance = verify_distribution_provenance(provenance_path=dist / "build-provenance.v1.json", implementation_revision=revision)
    payload = _json_object(Path(provenance["path"]), label="distribution provenance")
    wheel = _mapping(_mapping(payload.get("artifacts")).get("wheel"))
    wheel_name = wheel.get("name")
    if (not isinstance(wheel_name, str) or Path(wheel_name).name != wheel_name or not wheel_name.endswith(".whl")
            or not is_sha256(wheel.get("sha256")) or artifacts.get(wheel_name) != wheel["sha256"]):
        raise RuntimeError("prepared package wheel differs from distribution provenance")
    logs = {}
    for phase in ("wheel", "assets", "smoke"):
        log = _safe_file_without_symlinks(root / "package-logs" / (phase + ".log"), label="package phase log")
        logs[phase] = {"path": str(log), "sha256": sha256_file(log)}
    return {"version": PREPARED_PACKAGE_VERSION, "status": "prepared",
        "implementation_revision": revision, "source_tree": tree, "source_repository": str(repo),
        "release_version": version, "proof_root": str(root), "distribution_root": str(dist),
        "session": {"path": str(session_path.expanduser().resolve()), "head_sha": revision, "version": version},
        "source_archive": archive, "source_export": export, "artifact_sha256": artifacts,
        "distribution_provenance": provenance, "build_logs": logs,
        **_package_bindings(dist, artifacts, export, wheel_name, version)}


def prepare_release_package(**kwargs: Any) -> dict[str, Any]:
    """Capture committed source once and seal one already-built canonical package."""
    from greenfield_matrix_release_artifacts import _path_without_symlink_segments
    root = _path_without_symlink_segments(Path(kwargs["proof_root"]), label="release proof root")
    repo = _path_without_symlink_segments(Path(kwargs["repo_root"]), label="source repository")
    session_path = _safe_file_without_symlinks(Path(kwargs["session_path"]), label="release session")
    session = _json_object(session_path, label="release session")
    if (not root.is_dir() or root != session_path.parent / "greenfield-release" / kwargs["implementation_revision"]
            or session.get("head_sha") != kwargs["implementation_revision"] or session.get("version") != kwargs["version"]):
        raise RuntimeError("release capture requires its clean canonical source/session/root")
    _require_build_source(repo, kwargs["implementation_revision"])
    if any((root / name).exists() or (root / name).is_symlink() for name in ("prepared-package.v1.json", "prepared-package.v2.json", "source.tar.gz", "source-export")):
        raise FileExistsError("release source capture or prepared receipt already exists")
    anchor = _primary_repository(repo)
    _source_git(repo, "archive", "--format=tar.gz", "--prefix=source-export/", "--output=" + str(root / "source.tar.gz"), kwargs["implementation_revision"])
    _source_custody(root, anchor, kwargs["implementation_revision"], extract=True)
    snapshot = _package_snapshot(**{**kwargs, "repo_root": anchor})
    _require_build_source(repo, kwargs["implementation_revision"])
    receipt_path = root / "prepared-package.v2.json"
    _exclusive_write_json(receipt_path, snapshot)
    try:
        _require_build_source(repo, kwargs["implementation_revision"])
    except RuntimeError:
        receipt_path.unlink()
        raise
    return snapshot


def verify_prepared_release_package(**kwargs: Any) -> dict[str, Any]:
    """Recompute sealed immutable-H custody; caller worktree state is not authority."""
    path = _safe_file_without_symlinks(Path(kwargs["proof_root"]) / "prepared-package.v2.json", label="prepared package")
    receipt = _json_object(path, label="prepared package")
    if (set(receipt) != PREPARED_PACKAGE_FIELDS or receipt.get("version") != PREPARED_PACKAGE_VERSION
            or receipt.get("status") != "prepared" or not isinstance(receipt.get("source_repository"), str)):
        raise RuntimeError("prepared package lacks its closed current receipt")
    anchor = Path(receipt["source_repository"])
    if (str(anchor) != receipt["source_repository"] or _primary_repository(anchor) != anchor
            or _primary_repository(Path(kwargs["repo_root"])) != anchor):
        raise RuntimeError("prepared package source anchor/common store changed")
    for key, field in (("proof_root", "proof_root"), ("implementation_revision", "implementation_revision"), ("version", "release_version")):
        if str(kwargs[key]) != receipt[field]:
            raise RuntimeError("prepared package requested identity differs")
    if str(Path(kwargs["session_path"])) != receipt["session"]["path"]:
        raise RuntimeError("prepared package requested session differs")
    snapshot = _package_snapshot(**{**kwargs, "repo_root": anchor})
    if receipt != snapshot:
        raise RuntimeError("prepared package source/session/distribution custody changed")
    return snapshot


def _composition_release_custody(refs: Mapping[str, Any]) -> dict[str, Any]:
    """Authenticate one canonical prepared package and its actual activation/profile."""
    if not isinstance(refs, Mapping) or set(refs) != RELEASE_CUSTODY_REFS:
        raise ValueError("composition lacks its closed current release custody")
    data, paths = {}, {}
    for name, ref in refs.items():
        if not isinstance(ref, Mapping) or set(ref) != {"path", "sha256"}:
            raise ValueError("composition custody requires exact path/hash refs")
        paths[name], _ = _bound_file(ref, path_key="path", sha_key="sha256", label=name)
        data[name] = _json_object(paths[name], label=name)
    receipt = data["prepared_package"]
    if (set(receipt) != PREPARED_PACKAGE_FIELDS or receipt.get("version") != PREPARED_PACKAGE_VERSION
            or receipt.get("status") != "prepared" or not isinstance(receipt.get("source_repository"), str)):
        raise ValueError("composition requires the current canonical prepared receipt")
    anchor = Path(receipt["source_repository"])
    if not anchor.is_absolute() or str(anchor) != receipt["source_repository"] or anchor != anchor.resolve():
        raise ValueError("composition source repository anchor is not canonical")
    snapshot = verify_prepared_release_package(proof_root=Path(receipt["proof_root"]),
        session_path=Path(receipt["session"]["path"]), repo_root=Path(receipt["source_repository"]),
        implementation_revision=receipt["implementation_revision"], version=receipt["release_version"])
    head, tree = snapshot["implementation_revision"], snapshot["source_tree"]
    checkpoint, activation, profile = (data[name] for name in ("checkpoint", "activation", "profile"))
    if (checkpoint.get("status") != "passed" or checkpoint.get("head") != head or checkpoint.get("tree") != tree
            or checkpoint.get("current_source_pins_unchanged") is not True
            or paths["prepared_package"] != Path(snapshot["proof_root"]) / "prepared-package.v2.json"
            or activation.get("status") != "activated_after_package_pass"
            or activation.get("implementation_revision") != head or profile.get("implementation_revision") != head
            or activation.get("prepared_package") != refs["prepared_package"]
            or activation.get("source_export") != snapshot["source_export"]["path"]
            or activation.get("distribution") != snapshot["distribution_root"] or activation.get("profile") != profile):
        raise ValueError("composition canonical package/checkpoint/activation/profile differs")
    if not activation.get("file_pins"):
        raise ValueError("composition activation has no frozen file pins")
    for name, digest in activation["file_pins"].items():
        _bound_file({"path": name, "sha256": digest}, path_key="path", sha_key="sha256", label="activation pin")
    _bound_file({"path": profile["trusted_executable"], "sha256": profile["executable_sha256"]}, path_key="path", sha_key="sha256", label="native executable")
    wheel = _json_object(Path(snapshot["distribution_provenance"]["path"]), label="provenance")["artifacts"]["wheel"]
    return {"commit": head, "tree": tree, "archive_sha256": snapshot["source_archive"]["sha256"],
        "wheel_sha256": wheel["sha256"], "release_manifest_sha256": snapshot["artifact_sha256"]["release-manifest.json"],
        "prepared_package_sha256": refs["prepared_package"]["sha256"], "activation_sha256": refs["activation"]["sha256"],
        "source_export_root": snapshot["source_export"]["path"], "distribution_root": snapshot["distribution_root"],
        "trusted_executable": profile["trusted_executable"], "trusted_executable_sha256": profile["executable_sha256"],
        "profile_id": profile["profile_id"], "model": profile["model"], "reasoning_effort": profile["reasoning_effort"],
        "argv_shape_sha256": profile["argv_shape_sha256"]}


def claim_terminal_release(*, composed_public_evidence_path: Path, **kwargs: Any) -> dict[str, Any]:
    """Authenticate public qualification before reserving the one terminal attempt."""
    _require_build_source(Path(kwargs["repo_root"]), kwargs["implementation_revision"])
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
        "prepared_package_sha256": sha256_file(root / "prepared-package.v2.json"),
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
    custody = _composition_release_custody(declaration["release_custody"])
    prepared_path, _ = _bound_file(declaration["release_custody"]["prepared_package"], path_key="path", sha_key="sha256", label="prepared package")
    provenance_ref = _json_object(prepared_path, label="prepared package")["distribution_provenance"]
    if (common != custody or common.get("commit") != implementation_revision or common.get("distribution_root") != str(dist)
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
    receipt_path = _safe_file_without_symlinks(root / "prepared-package.v2.json", label="prepared package")
    receipt = _json_object(receipt_path, label="prepared package")
    dist = distribution_root.expanduser().resolve()
    if (receipt.get("version") != PREPARED_PACKAGE_VERSION or receipt.get("status") != "prepared"
            or receipt.get("implementation_revision") != implementation_revision
            or receipt.get("proof_root") != str(root) or receipt.get("distribution_root") != str(dist)
            or dist != root / "dist"):
        raise RuntimeError("terminal claim differs from its prepared package identity")
    verified = verify_prepared_release_package(proof_root=root,
        session_path=Path(receipt["session"]["path"]), repo_root=Path(receipt["source_repository"]),
        implementation_revision=implementation_revision, version=receipt["release_version"])
    provenance_path = _safe_file_without_symlinks(distribution_provenance_path, label="terminal distribution provenance")
    if (provenance_path != root / "build-provenance.v1.json"
            or sha256_file(provenance_path) != verified["distribution_provenance"]["sha256"]):
        raise RuntimeError("terminal distribution provenance differs from the prepared package")
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
    receipt = _json_object(_safe_file_without_symlinks(root / "prepared-package.v2.json", label="prepared package"), label="prepared package")
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
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError(f"{label} contains duplicate JSON keys")
            result[key] = value
        return result
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
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
