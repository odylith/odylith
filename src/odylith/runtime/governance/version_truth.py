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
_PACKAGE_VERSION_RE = re.compile(r'^__version__\s*=\s*["\'](?P<version>[^"\']+)["\']\s*$', re.MULTILINE)


@dataclass(frozen=True)
class VersionTruth:
    repo_root: Path
    source_version: str
    package_version: str
    pin: ProductVersionPin | None
    package_path: Path
    pin_path: Path

    @property
    def pin_version(self) -> str:
        return str(self.pin.odylith_version if self.pin is not None else "").strip()

    @property
    def is_product_repo(self) -> bool:
        return product_repo_role(repo_root=self.repo_root) == PRODUCT_REPO_ROLE


def package_version_path(*, repo_root: str | Path) -> Path:
    return Path(repo_root).expanduser().resolve() / _PACKAGE_INIT_RELATIVE


def load_package_version(*, repo_root: str | Path) -> str:
    path = package_version_path(repo_root=repo_root)
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    match = _PACKAGE_VERSION_RE.search(text)
    if match is None:
        return ""
    return str(match.group("version") or "").strip()


def collect_version_truth(*, repo_root: str | Path) -> VersionTruth:
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


def render_package_init(*, version: str) -> str:
    normalized = str(version or "").strip()
    return (
        '"""Odylith CLI and public contracts."""\n\n'
        '__all__ = ["__version__"]\n\n'
        f'__version__ = "{normalized}"\n'
    )


def sync_version_truth(*, repo_root: str | Path) -> list[Path]:
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
    parser = argparse.ArgumentParser(description="Inspect or synchronize Odylith version source truth.")
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show", help="Show current version truth.")
    subparsers.add_parser("check", help="Fail when generated version truth drifts from pyproject.")
    subparsers.add_parser("sync", help="Regenerate version truth files from pyproject.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
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
                print("odylith version truth FAILED")
                for item in errors:
                    print(f"- {item}")
                return 2
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
        raise ValueError(f"unsupported command: {args.command}")
    except ValueError as exc:
        print(f"error: {exc}")
        return 2

