from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from odylith.install.fs import atomic_write_text
from odylith.install.manager import PRODUCT_REPO_ROLE, product_repo_role, product_source_version
from odylith.install.state import ProductVersionPin, load_version_pin, version_pin_path, write_version_pin

_PACKAGE_INIT_RELATIVE = Path("src/odylith/__init__.py")
_PIN_RELATIVE = Path("odylith/runtime/source/product-version.v1.json")
_SECURITY_OVERVIEW_RELATIVE = Path("SECURITY.md")
_PRODUCT_SECURITY_POSTURE_RELATIVE = Path("odylith/SECURITY_POSTURE.md")
_BUNDLED_SECURITY_POSTURE_RELATIVE = Path("src/odylith/bundle/assets/odylith/SECURITY_POSTURE.md")
_RELEASE_SECURITY_DOCS = (
    _SECURITY_OVERVIEW_RELATIVE,
    _PRODUCT_SECURITY_POSTURE_RELATIVE,
    _BUNDLED_SECURITY_POSTURE_RELATIVE,
)
_PACKAGE_VERSION_RE = re.compile(r'^__version__\s*=\s*["\'](?P<version>[^"\']+)["\']\s*$', re.MULTILINE)


@dataclass(frozen=True)
class VersionTruth:
    """Resolved version-truth surfaces for the current repository."""

    repo_root: Path
    source_version: str
    package_version: str
    pin: ProductVersionPin | None
    package_path: Path
    pin_path: Path

    @property
    def pin_version(self) -> str:
        """Return the currently tracked pinned product version."""
        return str(self.pin.odylith_version if self.pin is not None else "").strip()

    @property
    def is_product_repo(self) -> bool:
        """Return whether the repo root is the Odylith product repository."""
        return product_repo_role(repo_root=self.repo_root) == PRODUCT_REPO_ROLE


def package_version_path(*, repo_root: str | Path) -> Path:
    """Return the package `__init__` path that owns the shipped version token."""
    return Path(repo_root).expanduser().resolve() / _PACKAGE_INIT_RELATIVE


def load_package_version(*, repo_root: str | Path) -> str:
    """Read the package version assignment from `src/odylith/__init__.py`."""
    path = package_version_path(repo_root=repo_root)
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    match = _PACKAGE_VERSION_RE.search(text)
    if match is None:
        return ""
    return str(match.group("version") or "").strip()


def collect_version_truth(*, repo_root: str | Path) -> VersionTruth:
    """Collect all current version-truth surfaces for the repo."""
    root = Path(repo_root).expanduser().resolve()
    return VersionTruth(
        repo_root=root,
        source_version=product_source_version(repo_root=root),
        package_version=load_package_version(repo_root=root),
        pin=load_version_pin(repo_root=root, fallback_version=None),
        package_path=package_version_path(repo_root=root),
        pin_path=version_pin_path(repo_root=root),
    )


def validate_version_truth(*, repo_root: str | Path) -> list[str]:
    """Validate that package and pin files agree with `pyproject.toml`."""
    truth = collect_version_truth(repo_root=repo_root)
    if not truth.is_product_repo:
        return []
    errors: list[str] = []
    if not truth.source_version:
        errors.append("missing or unreadable `[project].version` in `pyproject.toml`")
        return errors
    if not truth.package_version:
        errors.append(f"missing package version assignment in `{_PACKAGE_INIT_RELATIVE.as_posix()}`")
    elif truth.package_version != truth.source_version:
        errors.append(
            f"package version `{truth.package_version}` does not match `pyproject.toml` version `{truth.source_version}`"
        )
    if truth.pin is None:
        errors.append(f"missing tracked product version pin at `{_PIN_RELATIVE.as_posix()}`")
    else:
        if not truth.pin_version:
            errors.append("tracked product version pin is empty")
        elif truth.pin_version != truth.source_version:
            errors.append(
                f"tracked product pin `{truth.pin_version}` does not match `pyproject.toml` version `{truth.source_version}`"
            )
    return errors


def _normalize_release_version(version: str) -> str:
    """Normalize version input so callers can pass either `0.x.y` or `v0.x.y`."""
    normalized = str(version or "").strip()
    if normalized.startswith("v"):
        normalized = normalized[1:]
    return normalized


def validate_release_security_docs(*, repo_root: str | Path, expected_version: str) -> list[str]:
    """Validate that release-facing security docs mention the expected release tag."""
    truth = collect_version_truth(repo_root=repo_root)
    if not truth.is_product_repo:
        return []
    normalized_version = _normalize_release_version(expected_version)
    if not normalized_version:
        raise ValueError("expected release version is required")
    expected_tag = f"v{normalized_version}"
    errors: list[str] = []
    for relative_path in _RELEASE_SECURITY_DOCS:
        path = truth.repo_root / relative_path
        if not path.is_file():
            errors.append(f"missing release-facing security doc `{relative_path.as_posix()}`")
            continue
        text = path.read_text(encoding="utf-8")
        if expected_tag not in text:
            errors.append(
                f"release-facing security doc `{relative_path.as_posix()}` does not mention expected release `{expected_tag}`"
            )
    return errors


def render_package_init(*, version: str) -> str:
    """Render the canonical contents for `src/odylith/__init__.py`."""
    normalized = str(version or "").strip()
    return (
        '"""Odylith CLI and public contracts."""\n\n'
        '__all__ = ["__version__"]\n\n'
        f'__version__ = "{normalized}"\n'
    )


def sync_version_truth(*, repo_root: str | Path) -> list[Path]:
    """Regenerate tracked version-truth files from the source version."""
    truth = collect_version_truth(repo_root=repo_root)
    if not truth.is_product_repo:
        raise ValueError("version truth sync is only supported in the Odylith product repo")
    if not truth.source_version:
        raise ValueError("missing or unreadable `[project].version` in `pyproject.toml`")

    changed: list[Path] = []
    package_text = render_package_init(version=truth.source_version)
    existing_package = truth.package_path.read_text(encoding="utf-8") if truth.package_path.is_file() else ""
    if existing_package != package_text:
        truth.package_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(truth.package_path, package_text, encoding="utf-8")
        changed.append(truth.package_path)

    current_pin_text = truth.pin_path.read_text(encoding="utf-8") if truth.pin_path.is_file() else ""
    write_version_pin(
        repo_root=truth.repo_root,
        version=truth.source_version,
        repo_schema_version=(truth.pin.repo_schema_version if truth.pin is not None else 1),
        migration_required=bool(truth.pin.migration_required) if truth.pin is not None else False,
    )
    updated_pin_text = truth.pin_path.read_text(encoding="utf-8")
    if updated_pin_text != current_pin_text:
        changed.append(truth.pin_path)
    return changed


def render_version_truth(*, repo_root: str | Path) -> dict[str, object]:
    """Return the current version-truth state as a JSON-friendly payload."""
    truth = collect_version_truth(repo_root=repo_root)
    return {
        "repo_root": str(truth.repo_root),
        "product_repo": truth.is_product_repo,
        "source_version": truth.source_version,
        "package_version": truth.package_version,
        "pin_version": truth.pin_version,
        "package_path": str(truth.package_path),
        "pin_path": str(truth.pin_path),
        "errors": validate_version_truth(repo_root=truth.repo_root),
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for version-truth inspection and sync commands."""
    parser = argparse.ArgumentParser(description="Inspect or synchronize Odylith version source truth.")
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show", help="Show current version truth.")
    subparsers.add_parser("check", help="Fail when generated version truth drifts from pyproject.")
    subparsers.add_parser("sync", help="Regenerate version truth files from pyproject.")
    release_check = subparsers.add_parser(
        "release-check",
        help="Fail when release-facing security docs do not mention the expected release version.",
    )
    release_check.add_argument("--expected-version", required=True)
    return parser


def _print_errors(header: str, errors: Sequence[str]) -> int:
    """Print a failed validation block and return the standard CLI exit code."""
    print(header)
    for item in errors:
        print(f"- {item}")
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for version-truth inspection and synchronization."""
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    try:
        if args.command == "show":
            print(json.dumps(render_version_truth(repo_root=repo_root), indent=2, sort_keys=True))
            return 0
        if args.command == "check":
            errors = validate_version_truth(repo_root=repo_root)
            if errors:
                return _print_errors("odylith version truth FAILED", errors)
            payload = render_version_truth(repo_root=repo_root)
            print("odylith version truth passed")
            print(f"- source_version: {payload['source_version']}")
            print(f"- package_version: {payload['package_version']}")
            print(f"- pin_version: {payload['pin_version']}")
            return 0
        if args.command == "sync":
            changed = sync_version_truth(repo_root=repo_root)
            print("odylith version truth synchronized")
            for path in changed:
                print(f"- updated: {path.relative_to(repo_root)}")
            if not changed:
                print("- updated: <none>")
            return 0
        if args.command == "release-check":
            errors = validate_release_security_docs(repo_root=repo_root, expected_version=args.expected_version)
            if errors:
                return _print_errors("odylith release security docs FAILED", errors)
            print("odylith release security docs passed")
            print(f"- expected_version: v{_normalize_release_version(args.expected_version)}")
            return 0
        raise ValueError(f"unsupported command: {args.command}")
    except ValueError as exc:
        print(f"error: {exc}")
        return 2
