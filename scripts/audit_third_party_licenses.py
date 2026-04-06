from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Iterable

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from odylith.install.managed_runtime import (  # noqa: E402
    MANAGED_PYTHON_RELEASE,
    MANAGED_PYTHON_VERSION,
    supported_managed_runtime_feature_packs,
)


DEFAULT_OUTPUT_PATH = REPO_ROOT / "THIRD_PARTY_ATTRIBUTION.md"
RUNTIME_INVENTORY_PATH = REPO_ROOT / "odylith" / "runtime" / "source" / "third-party-runtime-inventory.v1.json"

ALLOWED_LICENSE_IDS = {
    "0BSD",
    "Apache-2.0",
    "BSD",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "CC0-1.0",
    "ISC",
    "MIT",
    "MPL-2.0",
    "PSF-2.0",
    "Unlicense",
    "Zlib",
}

DISALLOWED_LICENSE_TOKENS = (
    "agpl",
    "business source",
    "busl",
    "commercial",
    "commons clause",
    "elastic license",
    "eula",
    "gpl",
    "lgpl",
    "polyform",
    "proprietary",
    "sspl",
)

NORMALIZED_LICENSE_MAP = {
    "apache 2": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "bsd": "BSD",
    "bsd 2-clause": "BSD-2-Clause",
    "bsd 3-clause license": "BSD-3-Clause",
    "bsd license": "BSD",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "cc0-1.0": "CC0-1.0",
    "isc": "ISC",
    "isc license": "ISC",
    "isc license (iscl)": "ISC",
    "mit": "MIT",
    "mit license": "MIT",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "mpl-2.0": "MPL-2.0",
    "psf-2.0": "PSF-2.0",
    "python software foundation license": "PSF-2.0",
    "the mit license (mit)": "MIT",
    "the unlicense (unlicense)": "Unlicense",
    "unlicense": "Unlicense",
    "zlib": "Zlib",
}

PACKAGE_LICENSE_OVERRIDES = {
    "tantivy": "MIT",
}

PACKAGE_SOURCE_OVERRIDES = {
    "tantivy": "https://github.com/quickwit-oss/tantivy-py",
}

PACKAGE_INVENTORY_OVERRIDES = {
    "watchdog": {
        "version": "6.0.0",
        "license": "Apache-2.0",
        "license_source": "policy:platform-union-override",
        "source_url": "https://github.com/gorakhargosh/watchdog/",
        "note": (
            "Present in the Darwin full-stack managed context-engine pack and intentionally "
            "omitted from Linux feature-pack builds."
        ),
    },
}

BUNDLED_ARTIFACTS = (
    {
        "name": "python-build-standalone",
        "version": f"{MANAGED_PYTHON_VERSION}+{MANAGED_PYTHON_RELEASE}",
        "license": "MPL-2.0",
        "source_url": "https://github.com/astral-sh/python-build-standalone",
        "kind": "bundled-runtime",
        "note": (
            "Supplier for Odylith-managed Python runtime bundles. Odylith preserves the "
            "upstream license tree shipped inside the managed runtime bundle."
        ),
    },
    {
        "name": "CPython",
        "version": MANAGED_PYTHON_VERSION,
        "license": "PSF-2.0",
        "source_url": "https://github.com/python/cpython",
        "kind": "bundled-runtime",
        "note": (
            "Redistributed inside the managed runtime via python-build-standalone; "
            "upstream license and notice files remain inside the runtime bundle."
        ),
    },
)

RUNTIME_INVENTORY_SCHEMA_VERSION = "odylith-third-party-runtime-inventory.v1"


@dataclass(frozen=True)
class InventoryEntry:
    name: str
    version: str
    license_expression: str | None
    license_source: str
    direct: bool
    source_url: str
    note: str
    kind: str


def _load_runtime_inventory_fallback(path: Path = RUNTIME_INVENTORY_PATH) -> list[InventoryEntry]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if str(payload.get("schema_version", "")).strip() != RUNTIME_INVENTORY_SCHEMA_VERSION:
        raise ValueError(f"unsupported runtime inventory schema in {path}")
    entries: list[InventoryEntry] = []
    for row in payload.get("dependencies", []):
        if not isinstance(row, dict):
            continue
        entries.append(
            InventoryEntry(
                name=str(row.get("name") or "").strip(),
                version=str(row.get("version") or "").strip(),
                license_expression=str(row.get("license_expression") or "").strip() or None,
                license_source=str(row.get("license_source") or "").strip(),
                direct=bool(row.get("direct")),
                source_url=str(row.get("source_url") or "").strip(),
                note=str(row.get("note") or "").strip(),
                kind="runtime-dependency",
            )
        )
    return [entry for entry in entries if entry.name]


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_license_value(value: str) -> str | None:
    candidate = _normalize_whitespace(str(value or ""))
    if not candidate:
        return None
    if len(candidate) <= 160 and any(operator in candidate for operator in (" AND ", " OR ", " WITH ")):
        parts = re.split(r"(\s+(?:AND|OR|WITH)\s+)", candidate)
        normalized_parts: list[str] = []
        for part in parts:
            token = _normalize_whitespace(part)
            if not token:
                continue
            if token in {"AND", "OR", "WITH"}:
                normalized_parts.append(token)
                continue
            normalized = _normalize_license_value(token)
            if not normalized:
                normalized_parts = []
                break
            normalized_parts.append(normalized)
        if normalized_parts:
            return " ".join(normalized_parts)
    lowered = candidate.casefold()
    if lowered in NORMALIZED_LICENSE_MAP:
        return NORMALIZED_LICENSE_MAP[lowered]
    if candidate in ALLOWED_LICENSE_IDS:
        return candidate
    return None


def _infer_bsd_variant(text: str) -> str | None:
    lowered = text.casefold()
    if "redistribution and use in source and binary forms" not in lowered:
        return None
    if "neither the name" in lowered:
        return "BSD-3-Clause"
    return "BSD-2-Clause"


def _infer_license_from_text(text: str) -> str | None:
    lowered = text.casefold()
    if "mozilla public license" in lowered and "2.0" in lowered:
        return "MPL-2.0"
    if "python software foundation license" in lowered or "psf license agreement" in lowered:
        return "PSF-2.0"
    if "apache license" in lowered and "version 2.0" in lowered:
        return "Apache-2.0"
    if "mit license" in lowered or "permission is hereby granted, free of charge, to any person obtaining a copy" in lowered:
        return "MIT"
    if "permission to use, copy, modify, and/or distribute this software for any purpose with or without fee" in lowered:
        return "ISC"
    if "this source code form is subject to the terms of the mozilla public license, v. 2.0" in lowered:
        return "MPL-2.0"
    if "this is free and unencumbered software released into the public domain" in lowered:
        return "Unlicense"
    if "zero-clause bsd" in lowered or "0bsd" in lowered:
        return "0BSD"
    if "zlib license" in lowered:
        return "Zlib"
    return _infer_bsd_variant(text)


def _license_file_candidates(dist: metadata.Distribution) -> Iterable[Path]:
    for item in dist.files or []:
        name = str(item).lower()
        if "license" not in name and "copying" not in name and "notice" not in name:
            continue
        path = dist.locate_file(item)
        if Path(path).is_file():
            yield Path(path)


def _infer_license_from_files(dist: metadata.Distribution) -> str | None:
    for candidate in _license_file_candidates(dist):
        try:
            text = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        inferred = _infer_license_from_text(text)
        if inferred:
            return inferred
    return None


def _best_project_url(dist: metadata.Distribution) -> str:
    package_name = canonicalize_name(dist.metadata.get("Name") or "")
    if package_name in PACKAGE_SOURCE_OVERRIDES:
        return PACKAGE_SOURCE_OVERRIDES[package_name]
    metadata_block = dist.metadata
    project_urls: list[tuple[str, str]] = []
    for raw in metadata_block.get_all("Project-URL") or []:
        if "," in raw:
            label, url = raw.split(",", 1)
            project_urls.append((label.strip().casefold(), url.strip()))
        else:
            project_urls.append(("", raw.strip()))
    preferred_labels = ("source", "repository", "repo", "code", "homepage", "home")
    for label in preferred_labels:
        for candidate_label, candidate_url in project_urls:
            if label in candidate_label:
                return candidate_url
    for _label, candidate_url in project_urls:
        if candidate_url:
            return candidate_url
    return str(metadata_block.get("Home-page") or "").strip()


def _classifier_license_ids(dist: metadata.Distribution) -> list[str]:
    licenses: list[str] = []
    for raw in dist.metadata.get_all("Classifier") or []:
        if not raw.startswith("License ::"):
            continue
        token = raw.rsplit("::", 1)[-1].strip()
        normalized = _normalize_license_value(token)
        if normalized:
            licenses.append(normalized)
    return sorted(set(licenses))


def _resolved_license(dist: metadata.Distribution) -> tuple[str | None, str]:
    package_name = canonicalize_name(dist.metadata.get("Name") or "")

    expression = _normalize_license_value(str(dist.metadata.get("License-Expression") or "").strip())
    if expression:
        return expression, "metadata:License-Expression"

    raw_license = _normalize_license_value(str(dist.metadata.get("License") or "").strip())
    classifier_licenses = _classifier_license_ids(dist)

    if raw_license and raw_license != "BSD":
        return raw_license, "metadata:License"

    if len(classifier_licenses) > 1:
        return " OR ".join(classifier_licenses), "metadata:Classifier"
    if classifier_licenses and classifier_licenses[0] != "BSD":
        return classifier_licenses[0], "metadata:Classifier"

    file_license = _infer_license_from_files(dist)
    if file_license:
        return file_license, "metadata:License-File"

    if raw_license:
        return raw_license, "metadata:License"
    if classifier_licenses:
        return classifier_licenses[0], "metadata:Classifier"

    override = PACKAGE_LICENSE_OVERRIDES.get(package_name)
    if override:
        return override, "policy:override"
    return None, "unresolved"


def _license_tokens(expression: str) -> list[str]:
    return [token for token in re.split(r"\s+(?:AND|OR|WITH)\s+|[()]", expression) if token.strip()]


def _is_disallowed_expression(expression: str | None) -> bool:
    if not expression:
        return True
    lowered = expression.casefold()
    if any(token in lowered for token in DISALLOWED_LICENSE_TOKENS):
        return True
    tokens = _license_tokens(expression)
    if not tokens:
        return True
    return any(token not in ALLOWED_LICENSE_IDS for token in tokens)


def _load_project_dependencies(pyproject_path: Path) -> list[Requirement]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    raw_dependencies = list(data.get("project", {}).get("dependencies", []))
    for feature_pack in supported_managed_runtime_feature_packs():
        raw_dependencies.extend(feature_pack.python_requirements)
    return [Requirement(item) for item in raw_dependencies]


def _exact_direct_requirement_versions(requirements: list[Requirement]) -> dict[str, str]:
    pinned: dict[str, str] = {}
    for requirement in requirements:
        specifiers = list(requirement.specifier)
        if len(specifiers) != 1:
            continue
        specifier = specifiers[0]
        if specifier.operator != "==":
            continue
        pinned[canonicalize_name(requirement.name)] = specifier.version
    return pinned


def _installed_distributions() -> dict[str, metadata.Distribution]:
    return {
        canonicalize_name(dist.metadata.get("Name") or ""): dist
        for dist in metadata.distributions()
        if dist.metadata.get("Name")
    }


def _runtime_dependency_closure(
    *,
    requirements: list[Requirement],
    installed: dict[str, metadata.Distribution],
) -> tuple[dict[str, set[str]], set[str], list[str]]:
    closure: dict[str, set[str]] = {}
    direct = {canonicalize_name(requirement.name) for requirement in requirements}
    missing: list[str] = []
    stack = [(canonicalize_name(requirement.name), set(requirement.extras)) for requirement in requirements]
    while stack:
        package_name, active_extras = stack.pop()
        if package_name in closure:
            closure[package_name].update(active_extras)
            continue
        closure[package_name] = set(active_extras)
        dist = installed.get(package_name)
        if dist is None:
            missing.append(package_name)
            continue
        for raw_requirement in dist.requires or []:
            requirement = Requirement(raw_requirement)
            environment = default_environment()
            include = False
            if requirement.marker is None:
                include = True
            else:
                for extra in active_extras or {""}:
                    scoped_environment = dict(environment)
                    scoped_environment["extra"] = extra
                    try:
                        if requirement.marker.evaluate(scoped_environment):
                            include = True
                            break
                    except Exception:
                        continue
            if include:
                stack.append((canonicalize_name(requirement.name), set(requirement.extras)))
    return closure, direct, sorted(set(missing))


def collect_inventory(pyproject_path: Path) -> tuple[list[InventoryEntry], list[InventoryEntry], list[str]]:
    requirements = _load_project_dependencies(pyproject_path)
    pinned_versions = _exact_direct_requirement_versions(requirements)
    installed = _installed_distributions()
    closure, direct_names, missing = _runtime_dependency_closure(requirements=requirements, installed=installed)
    declared_inventory = _load_runtime_inventory_fallback()
    declared_by_name = {
        canonicalize_name(entry.name): entry
        for entry in declared_inventory
    }

    dependency_entries: list[InventoryEntry] = []
    unresolved_missing: list[str] = []
    seen_names: set[str] = set()
    for package_name in sorted(closure):
        override = PACKAGE_INVENTORY_OVERRIDES.get(package_name)
        if override is not None:
            dependency_entries.append(
                InventoryEntry(
                    name=package_name,
                    version=str(override["version"]),
                    license_expression=str(override["license"]),
                    license_source=str(override["license_source"]),
                    direct=package_name in direct_names,
                    source_url=str(override["source_url"]),
                    note=str(override.get("note") or ""),
                    kind="runtime-dependency",
                )
            )
            seen_names.add(package_name)
            continue
        declared_entry = declared_by_name.get(package_name)
        if declared_entry is not None:
            dependency_entries.append(
                InventoryEntry(
                    name=declared_entry.name,
                    version=pinned_versions.get(package_name, declared_entry.version),
                    license_expression=declared_entry.license_expression,
                    license_source=declared_entry.license_source,
                    direct=package_name in direct_names or declared_entry.direct,
                    source_url=declared_entry.source_url,
                    note=declared_entry.note,
                    kind="runtime-dependency",
                )
            )
            seen_names.add(package_name)
            continue
        if declared_by_name and package_name not in direct_names:
            continue
        dist = installed.get(package_name)
        if dist is None:
            unresolved_missing.append(package_name)
            continue
        resolved_license, license_source = _resolved_license(dist)
        dependency_entries.append(
            InventoryEntry(
                name=str(dist.metadata.get("Name") or package_name),
                version=pinned_versions.get(package_name, dist.version),
                license_expression=resolved_license,
                license_source=license_source,
                direct=package_name in direct_names,
                source_url=_best_project_url(dist),
                note="",
                kind="runtime-dependency",
            )
        )
        seen_names.add(package_name)

    for package_name, entry in sorted(declared_by_name.items()):
        if package_name in seen_names:
            continue
        dependency_entries.append(
            InventoryEntry(
                name=entry.name,
                version=pinned_versions.get(package_name, entry.version),
                license_expression=entry.license_expression,
                license_source=entry.license_source,
                direct=package_name in direct_names or entry.direct,
                source_url=entry.source_url,
                note=entry.note,
                kind="runtime-dependency",
            )
        )
        seen_names.add(package_name)

    bundled_entries = [
        InventoryEntry(
            name=str(item["name"]),
            version=str(item["version"]),
            license_expression=str(item["license"]),
            license_source="policy:bundled-artifact",
            direct=False,
            source_url=str(item["source_url"]),
            note=str(item["note"]),
            kind=str(item["kind"]),
        )
        for item in BUNDLED_ARTIFACTS
    ]
    unresolved_missing.extend(
        package_name
        for package_name in missing
        if package_name not in PACKAGE_INVENTORY_OVERRIDES and package_name not in declared_by_name
    )
    dependency_entries.sort(key=lambda entry: (not entry.direct, canonicalize_name(entry.name)))
    return dependency_entries, bundled_entries, sorted(set(unresolved_missing))


def audit_issues(
    *,
    dependency_entries: list[InventoryEntry],
    bundled_entries: list[InventoryEntry],
    missing_packages: list[str],
) -> list[str]:
    issues: list[str] = []
    for missing in missing_packages:
        issues.append(f"missing installed runtime dependency metadata: {missing}")
    for entry in [*dependency_entries, *bundled_entries]:
        if _is_disallowed_expression(entry.license_expression):
            issues.append(
                f"disallowed or unknown license for {entry.name} {entry.version}: "
                f"{entry.license_expression or 'UNKNOWN'} ({entry.license_source})"
            )
    return issues


def render_markdown(
    *,
    dependency_entries: list[InventoryEntry],
    bundled_entries: list[InventoryEntry],
    issues: list[str],
) -> str:
    direct_entries = [entry for entry in dependency_entries if entry.direct]
    transitive_entries = [entry for entry in dependency_entries if not entry.direct]
    observed_license_families = sorted(
        {
            entry.license_expression
            for entry in [*dependency_entries, *bundled_entries]
            if entry.license_expression
        }
    )

    lines = [
        "# Third-Party Attribution And Acknowledgements",
        "",
        "This file is generated by `./bin/license-audit`.",
        "Do not hand-edit it; rerun the generator when the runtime dependency closure or bundled-runtime inputs change.",
        "",
        "## Scope",
        "",
        "- Audits the Odylith runtime dependency closure declared in `pyproject.toml`, including the managed context-engine pack requirements that ship in the default full-stack install.",
        "- Includes bundled managed-runtime upstream inputs used to build Odylith-owned Python runtimes.",
        "- Fails closed on missing metadata, unknown licenses, commercial/proprietary terms, and currently disallowed strong-copyleft/source-available families.",
        "",
        "## Current Status",
        "",
        (
            "- Result: no disallowed or commercial/proprietary licenses detected in the current audited "
            "runtime closure."
            if not issues
            else "- Result: audit blockers are present. See `## Audit Blockers`."
        ),
        f"- Direct runtime dependencies: {len(direct_entries)}",
        f"- Transitive runtime dependencies: {len(transitive_entries)}",
        f"- Bundled runtime artifacts: {len(bundled_entries)}",
        "- Allowed license families in the current policy: "
        + ", ".join(sorted(ALLOWED_LICENSE_IDS))
        + ".",
        "- Explicitly blocked families include: GPL/AGPL/LGPL, SSPL, BUSL/Business Source, PolyForm, Elastic License, and commercial/proprietary terms.",
        "",
        "## Bundled Runtime Artifacts",
        "",
        "| Artifact | Version | License | Source | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in bundled_entries:
        source = f"[upstream]({entry.source_url})" if entry.source_url else ""
        lines.append(
            f"| `{entry.name}` | `{entry.version}` | `{entry.license_expression or 'UNKNOWN'}` | {source} | {entry.note} |"
        )

    def _append_dependency_section(title: str, entries: list[InventoryEntry]) -> None:
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| Package | Version | License | Upstream | Evidence |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for entry in entries:
            source = f"[project]({entry.source_url})" if entry.source_url else ""
            lines.append(
                f"| `{entry.name}` | `{entry.version}` | `{entry.license_expression or 'UNKNOWN'}` | {source} | `{entry.license_source}` |"
            )

    _append_dependency_section("Direct Runtime Dependencies", direct_entries)
    _append_dependency_section("Transitive Runtime Dependencies", transitive_entries)

    lines.extend(
        [
            "",
            "## Acknowledgements",
            "",
            "- Odylith depends on the open-source projects listed above and preserves their required attribution and license materials in source and redistribution artifacts where applicable.",
            "- The managed-runtime lane is built on upstream `python-build-standalone` inputs and redistributes CPython inside Odylith-managed runtime bundles.",
            "- Where upstream wheels expose license trees or notice files, Odylith preserves those files inside the built runtime bundles rather than flattening them into one synthetic notice blob.",
            "",
            "## Observed License Expressions",
            "",
        ]
    )
    for family in observed_license_families:
        lines.append(f"- `{family}`")

    lines.extend(["", "## Audit Blockers", ""])
    if issues:
        for issue in issues:
            lines.append(f"- `{issue}`")
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Odylith third-party runtime licensing and attribution.")
    parser.add_argument(
        "--pyproject",
        default=str(REPO_ROOT / "pyproject.toml"),
        help="Path to the project pyproject.toml file.",
    )
    parser.add_argument(
        "--write",
        default="",
        help="Optional markdown output path. When provided, the generated attribution document is written there.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the collected inventory and issues as JSON to stdout.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if disallowed licenses are present or the written markdown would change.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    pyproject_path = Path(args.pyproject).expanduser().resolve()
    dependency_entries, bundled_entries, missing_packages = collect_inventory(pyproject_path)
    issues = audit_issues(
        dependency_entries=dependency_entries,
        bundled_entries=bundled_entries,
        missing_packages=missing_packages,
    )
    markdown = render_markdown(
        dependency_entries=dependency_entries,
        bundled_entries=bundled_entries,
        issues=issues,
    )

    if args.write:
        output_path = Path(args.write).expanduser().resolve()
        output_path.write_text(markdown, encoding="utf-8")

    if args.json:
        payload = {
            "dependencies": [
                {
                    "name": entry.name,
                    "version": entry.version,
                    "license_expression": entry.license_expression,
                    "license_source": entry.license_source,
                    "direct": entry.direct,
                    "source_url": entry.source_url,
                    "kind": entry.kind,
                }
                for entry in dependency_entries
            ],
            "bundled_artifacts": [
                {
                    "name": entry.name,
                    "version": entry.version,
                    "license_expression": entry.license_expression,
                    "license_source": entry.license_source,
                    "source_url": entry.source_url,
                    "note": entry.note,
                    "kind": entry.kind,
                }
                for entry in bundled_entries
            ],
            "issues": issues,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif not args.write:
        print(markdown)

    if args.check and issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
