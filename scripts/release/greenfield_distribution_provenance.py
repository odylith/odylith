"""Own release JSON, complete package census and immutable distribution provenance."""

from __future__ import annotations

from collections.abc import Mapping
import json
import hashlib
from pathlib import Path, PurePosixPath
import tomllib
import zipfile
from typing import Any

from greenfield_matrix_release_artifacts import sha256_file, is_sha256


PROVENANCE_VERSION = "odylith-release-provenance.v1"


def verify_distribution_provenance(
    *,
    provenance_path: Path,
    implementation_revision: str,
) -> dict[str, str]:
    """Require clean package provenance for the exact claimed revision."""

    path = Path(provenance_path).expanduser()
    if path.is_symlink():
        raise RuntimeError("semantic release proof requires safe distribution build provenance")
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError("semantic release proof requires safe distribution build provenance")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"distribution build provenance is unreadable: {error}") from error
    if not isinstance(payload, Mapping) or payload.get("version") != PROVENANCE_VERSION:
        raise RuntimeError("semantic release proof requires supported distribution build provenance")
    source_tree = payload.get("source_tree")
    workflow = payload.get("workflow")
    source_head = str(source_tree.get("head") or "").strip().casefold() if isinstance(source_tree, Mapping) else ""
    workflow_sha = str(workflow.get("sha") or "").strip().casefold() if isinstance(workflow, Mapping) else ""
    revision = str(implementation_revision or "").strip().casefold()
    if not isinstance(source_tree, Mapping) or source_tree.get("dirty") is not False:
        raise RuntimeError("semantic release proof requires clean distribution source provenance")
    if source_head != workflow_sha or source_head != revision:
        raise RuntimeError("implementation revision does not match distribution build provenance")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "implementation_revision": source_head,
    }


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


def _unique_json_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise RuntimeError("release custody contains duplicate JSON keys")
        value[key] = item
    return value


def _json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_pairs)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label} is unreadable") from exc
    if not isinstance(payload, Mapping):
        raise RuntimeError(f"{label} must be an object")
    return dict(payload)


__all__ = ["PROVENANCE_VERSION", "verify_distribution_provenance"]
