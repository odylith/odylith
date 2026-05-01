from __future__ import annotations

import hashlib
import json
from pathlib import Path

from odylith.install import runtime
from odylith.install.managed_runtime import (
    MANAGED_RUNTIME_FEATURE_PACK_FILENAME,
    MANAGED_RUNTIME_FEATURE_PACK_SCHEMA_VERSION,
    MANAGED_RUNTIME_SCHEMA_VERSION,
    MANAGED_RUNTIME_VERIFICATION_FILENAME,
    MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
    MANAGED_PYTHON_VERSION,
)
from odylith.install.migration_readiness import inspect_runtime_migration_readiness
from odylith.install.state import install_state_path, write_install_state


def _sha256(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _verification(version: str) -> dict[str, object]:
    return {
        "manifest_sha256": _sha256(f"manifest-{version}"),
        "provenance_sha256": _sha256(f"provenance-{version}"),
        "runtime_bundle_platform": "darwin-arm64",
        "runtime_bundle_sha256": _sha256(f"runtime-{version}"),
        "sbom_sha256": _sha256(f"sbom-{version}"),
        "wheel_sha256": _sha256(f"wheel-{version}"),
    }


def _seed_runtime(repo_root: Path, *, version: str = "1.2.3", verification: dict[str, object] | None = None) -> Path:
    version_root = repo_root / ".odylith" / "runtime" / "versions" / version
    bin_dir = version_root / "bin"
    bin_dir.mkdir(parents=True)
    for name in ("python", "python3", "odylith"):
        executable = bin_dir / name
        executable.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)
    (version_root / "pyvenv.cfg").write_text("version = 3.13.12\n", encoding="utf-8")
    (version_root / "runtime-metadata.json").write_text(
        json.dumps(
            {
                "platform": "darwin-arm64",
                "python_version": MANAGED_PYTHON_VERSION,
                "schema_version": MANAGED_RUNTIME_SCHEMA_VERSION,
                "source_wheel": f"odylith-{version}-py3-none-any.whl",
                "version": version,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    runtime_verification = dict(verification or _verification(version))
    (version_root / MANAGED_RUNTIME_VERIFICATION_FILENAME).write_text(
        json.dumps(
            {
                "schema_version": MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
                "verification": runtime_verification,
                "version": version,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    pack_payload_path = "lib/python3.13/site-packages/watchdog/__init__.py"
    payload = version_root / pack_payload_path
    payload.parent.mkdir(parents=True)
    payload.write_text("# context engine fixture\n", encoding="utf-8")
    pack = {
        "asset_name": "odylith-context-engine-memory-darwin-arm64.tar.gz",
        "display_name": "Odylith Context Engine memory pack",
        "installed_utc": "2026-04-30T00:00:00+00:00",
        "paths": [pack_payload_path],
        "platform": "darwin-arm64",
        "verification": {
            "feature_pack_id": "odylith-context-engine-memory",
            "feature_pack_sha256": _sha256(f"feature-pack-{version}"),
        },
    }
    (version_root / MANAGED_RUNTIME_FEATURE_PACK_FILENAME).write_text(
        json.dumps(
            {
                "packs": {"odylith-context-engine-memory": pack},
                "schema_version": MANAGED_RUNTIME_FEATURE_PACK_SCHEMA_VERSION,
                "version": version,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    runtime.write_managed_runtime_trust(
        repo_root=repo_root,
        version_root=version_root,
        verification=runtime_verification,
    )
    runtime.switch_runtime(repo_root=repo_root, target=version_root)
    write_install_state(
        repo_root=repo_root,
        payload={
            "active_version": version,
            "activation_history": [version],
            "installed_versions": {
                version: {
                    "feature_packs": {"odylith-context-engine-memory": pack},
                    "installed_utc": "2026-04-30T00:00:00+00:00",
                    "runtime_root": str(version_root),
                    "verification": runtime_verification,
                }
            },
            "last_known_good_version": version,
        },
    )
    return version_root


def test_runtime_migration_readiness_collects_future_contract_without_state_writes(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    version_root = _seed_runtime(repo_root)
    state_path = install_state_path(repo_root=repo_root)
    before_state = state_path.read_text(encoding="utf-8")

    report = inspect_runtime_migration_readiness(repo_root=repo_root)

    assert report.eligible is True
    assert report.version == "1.2.3"
    assert report.platform_slug == "darwin-arm64"
    assert report.active_runtime_root == version_root
    assert report.state_runtime_root == version_root
    assert report.runtime_bundle_sha256 == _sha256("runtime-1.2.3")
    assert report.wheel_sha256 == _sha256("wheel-1.2.3")
    assert report.manifest_sha256 == _sha256("manifest-1.2.3")
    assert report.provenance_sha256 == _sha256("provenance-1.2.3")
    assert report.sbom_sha256 == _sha256("sbom-1.2.3")
    assert report.activation_history == ("1.2.3",)
    assert len(report.content_identity) == 64
    assert report.hot_file_count > 0
    assert len(report.trust_env_sha256) == 64
    assert len(report.trust_tree_sha256) == 64
    assert len(report.trust_tree_digest) == 64
    assert report.feature_packs[0].asset_name == "odylith-context-engine-memory-darwin-arm64.tar.gz"
    assert report.feature_packs[0].platform == "darwin-arm64"
    assert report.feature_packs[0].paths == ("lib/python3.13/site-packages/watchdog/__init__.py",)
    assert report.feature_packs[0].feature_pack_sha256 == _sha256("feature-pack-1.2.3")
    assert report.missing == ()
    assert report.reasons == ()
    assert state_path.read_text(encoding="utf-8") == before_state

    install_state = json.loads(before_state)
    assert "shared_store" not in install_state
    assert "global_runtime_root" not in install_state
    assert "content_identity" not in install_state


def test_runtime_migration_readiness_rejects_missing_release_receipt_sha(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    verification = _verification("1.2.3")
    verification.pop("provenance_sha256")
    _seed_runtime(repo_root, verification=verification)

    report = inspect_runtime_migration_readiness(repo_root=repo_root)

    assert report.eligible is False
    assert "runtime_verification.provenance_sha256" in report.missing


def test_runtime_migration_readiness_rejects_missing_feature_pack_metadata(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    version_root = _seed_runtime(repo_root)
    (version_root / MANAGED_RUNTIME_FEATURE_PACK_FILENAME).unlink()
    runtime.write_managed_runtime_trust(
        repo_root=repo_root,
        version_root=version_root,
        verification=runtime.runtime_verification_evidence(version_root),
    )

    report = inspect_runtime_migration_readiness(repo_root=repo_root)

    assert report.eligible is False
    assert "runtime_feature_packs" in report.missing
