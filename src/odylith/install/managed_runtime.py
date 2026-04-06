from __future__ import annotations

import platform
from dataclasses import dataclass


MANAGED_RUNTIME_SCHEMA_VERSION = "odylith-runtime-bundle.v1"
MANAGED_RUNTIME_ROOT_NAME = "runtime"
MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION = "odylith-runtime-verification.v1"
MANAGED_RUNTIME_VERIFICATION_FILENAME = "runtime-verification.v1.json"
MANAGED_RUNTIME_FEATURE_PACK_SCHEMA_VERSION = "odylith-runtime-feature-packs.v1"
MANAGED_RUNTIME_FEATURE_PACK_FILENAME = "runtime-feature-packs.v1.json"
MANAGED_PYTHON_VERSION = "3.13.12"
MANAGED_PYTHON_RELEASE = "20260325"
MANAGED_PYTHON_BASE_URL = (
    "https://github.com/astral-sh/python-build-standalone/releases/download"
    f"/{MANAGED_PYTHON_RELEASE}"
)
CONTEXT_ENGINE_FEATURE_PACK_ID = "odylith-context-engine-memory"


@dataclass(frozen=True)
class ManagedRuntimePlatform:
    slug: str
    display_name: str
    system: str
    machine_aliases: tuple[str, ...]
    upstream_asset_name: str
    upstream_asset_sha256: str

    @property
    def asset_name(self) -> str:
        return f"odylith-runtime-{self.slug}.tar.gz"

    @property
    def upstream_asset_url(self) -> str:
        return f"{MANAGED_PYTHON_BASE_URL}/{self.upstream_asset_name}"


@dataclass(frozen=True)
class ManagedRuntimeFeaturePack:
    pack_id: str
    display_name: str
    python_requirements: tuple[str, ...]
    marker_modules: tuple[str, ...]
    platform_requirement_exclusions: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def asset_name(self, runtime_platform: ManagedRuntimePlatform) -> str:
        return f"{self.pack_id}-{runtime_platform.slug}.tar.gz"

    def python_requirements_for_platform(self, runtime_platform: ManagedRuntimePlatform) -> tuple[str, ...]:
        excluded: tuple[str, ...] = ()
        for slug, requirements in self.platform_requirement_exclusions:
            if slug == runtime_platform.slug:
                excluded = requirements
                break
        if not excluded:
            return self.python_requirements
        return tuple(requirement for requirement in self.python_requirements if requirement not in excluded)


SUPPORTED_MANAGED_RUNTIME_PLATFORMS: tuple[ManagedRuntimePlatform, ...] = (
    ManagedRuntimePlatform(
        slug="darwin-arm64",
        display_name="macOS (Apple Silicon)",
        system="Darwin",
        machine_aliases=("arm64", "aarch64"),
        upstream_asset_name=f"cpython-{MANAGED_PYTHON_VERSION}+{MANAGED_PYTHON_RELEASE}-aarch64-apple-darwin-install_only.tar.gz",
        upstream_asset_sha256="688da81bcaa6ed91792397c7d5433b13a4f02f021f940637c3972639bc516dca",
    ),
    ManagedRuntimePlatform(
        slug="linux-arm64",
        display_name="Linux (ARM64)",
        system="Linux",
        machine_aliases=("aarch64", "arm64"),
        upstream_asset_name=f"cpython-{MANAGED_PYTHON_VERSION}+{MANAGED_PYTHON_RELEASE}-aarch64-unknown-linux-gnu-install_only.tar.gz",
        upstream_asset_sha256="31c6e61eed48ca4e156d0e473025a792338641109e8277a63518ded438390c96",
    ),
    ManagedRuntimePlatform(
        slug="linux-x86_64",
        display_name="Linux (x86_64)",
        system="Linux",
        machine_aliases=("x86_64", "amd64"),
        upstream_asset_name=f"cpython-{MANAGED_PYTHON_VERSION}+{MANAGED_PYTHON_RELEASE}-x86_64-unknown-linux-gnu-install_only.tar.gz",
        upstream_asset_sha256="ebb1051ca2822b9803f46a5f10b6d51d153189ef1b1f1e142f733c0cbeaf86eb",
    ),
)

SUPPORTED_MANAGED_RUNTIME_FEATURE_PACKS: tuple[ManagedRuntimeFeaturePack, ...] = (
    ManagedRuntimeFeaturePack(
        pack_id=CONTEXT_ENGINE_FEATURE_PACK_ID,
        display_name="Odylith Context Engine memory pack",
        python_requirements=(
            "lancedb==0.30.0",
            "tantivy>=0.25.1,<0.26.0",
            "watchdog>=6.0,<7.0",
        ),
        marker_modules=("lancedb", "pyarrow", "tantivy", "numpy"),
        platform_requirement_exclusions=(
            ("linux-arm64", ("watchdog>=6.0,<7.0",)),
            ("linux-x86_64", ("watchdog>=6.0,<7.0",)),
        ),
    ),
)


def supported_managed_runtime_platforms() -> tuple[ManagedRuntimePlatform, ...]:
    return SUPPORTED_MANAGED_RUNTIME_PLATFORMS


def supported_managed_runtime_feature_packs() -> tuple[ManagedRuntimeFeaturePack, ...]:
    return SUPPORTED_MANAGED_RUNTIME_FEATURE_PACKS


def managed_runtime_platform_by_slug(slug: str) -> ManagedRuntimePlatform:
    token = str(slug or "").strip()
    for candidate in SUPPORTED_MANAGED_RUNTIME_PLATFORMS:
        if candidate.slug == token:
            return candidate
    raise ValueError(f"unsupported managed runtime platform slug: {slug!r}")


def managed_runtime_feature_pack_by_id(pack_id: str) -> ManagedRuntimeFeaturePack:
    token = str(pack_id or "").strip()
    for candidate in SUPPORTED_MANAGED_RUNTIME_FEATURE_PACKS:
        if candidate.pack_id == token:
            return candidate
    raise ValueError(f"unsupported managed runtime feature pack: {pack_id!r}")


def detect_managed_runtime_platform(
    *,
    system_name: str | None = None,
    machine_name: str | None = None,
) -> ManagedRuntimePlatform | None:
    observed_system = str(system_name or platform.system()).strip()
    observed_machine = str(machine_name or platform.machine()).strip().lower()
    for candidate in SUPPORTED_MANAGED_RUNTIME_PLATFORMS:
        if candidate.system != observed_system:
            continue
        if observed_machine in candidate.machine_aliases:
            return candidate
    return None


def supported_platform_labels() -> list[str]:
    return [candidate.display_name for candidate in SUPPORTED_MANAGED_RUNTIME_PLATFORMS]
