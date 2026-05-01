from __future__ import annotations

import json
from pathlib import Path

from odylith.install import runtime_integrity
from odylith.install.managed_runtime import (
    MANAGED_RUNTIME_FEATURE_PACK_FILENAME,
    MANAGED_RUNTIME_SCHEMA_VERSION,
    MANAGED_RUNTIME_VERIFICATION_FILENAME,
    MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
    MANAGED_PYTHON_VERSION,
)


def _seed_runtime(version_root: Path) -> dict[str, object]:
    bin_dir = version_root / "bin"
    bin_dir.mkdir(parents=True)
    for executable_name in ("python", "python3", "odylith"):
        executable = bin_dir / executable_name
        executable.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)
    (version_root / "pyvenv.cfg").write_text("version = 3.13.12\n", encoding="utf-8")
    (version_root / "runtime-metadata.json").write_text(
        json.dumps(
            {
                "schema_version": MANAGED_RUNTIME_SCHEMA_VERSION,
                "version": version_root.name,
                "platform": "darwin-arm64",
                "python_version": MANAGED_PYTHON_VERSION,
                "source_wheel": "odylith-1.2.3-py3-none-any.whl",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    verification = {"wheel_sha256": "wheel-1.2.3"}
    (version_root / MANAGED_RUNTIME_VERIFICATION_FILENAME).write_text(
        json.dumps(
            {
                "schema_version": MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
                "version": version_root.name,
                "verification": verification,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (version_root / MANAGED_RUNTIME_FEATURE_PACK_FILENAME).write_text("{}\n", encoding="utf-8")
    return verification


def test_runtime_trust_manifest_ignores_macos_metadata_but_not_other_dotfiles(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    version_root = repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"
    version_root.mkdir(parents=True)
    verification = _seed_runtime(version_root)
    (version_root / ".DS_Store").write_text("finder\n", encoding="utf-8")
    package_dir = version_root / "lib" / "python3.13" / "site-packages" / "odylith"
    package_dir.mkdir(parents=True)
    (package_dir / "._module.py").write_text("appledouble\n", encoding="utf-8")

    runtime_integrity.write_managed_runtime_trust(
        repo_root=repo_root,
        version_root=version_root,
        verification=verification,
    )

    assert runtime_integrity.managed_runtime_integrity_reasons(repo_root=repo_root, runtime_root=version_root) == []

    unexpected = package_dir / ".unexpected"
    unexpected.write_text("real drift\n", encoding="utf-8")

    reasons = runtime_integrity.managed_runtime_integrity_reasons(repo_root=repo_root, runtime_root=version_root)

    assert reasons == [f"managed runtime tree entry unexpected: {unexpected}"]
