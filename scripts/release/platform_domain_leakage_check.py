#!/usr/bin/env python3
"""Fail release proof when matrix fixture vocabulary leaks into platform code."""

from __future__ import annotations

import argparse
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from greenfield_post_confirm_matrix_cases import default_cases  # noqa: E402


TEXT_SUFFIXES = frozenset(
    {
        ".css",
        ".html",
        ".js",
        ".json",
        ".md",
        ".mjs",
        ".py",
        ".sh",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)
SOURCE_SCAN_PATHS = (
    "src/odylith",
    "bin",
    "README.md",
    "AGENTS.md",
    "pyproject.toml",
    "odylith/agents-guidelines",
    "odylith/skills",
    ".agents",
    ".claude",
)
MATRIX_FIXTURE_PATHS = frozenset(
    {
        "scripts/release/greenfield_post_confirm_matrix_cases.py",
    }
)
GOVERNANCE_EVIDENCE_PARTS = frozenset(
    {
        "casebook",
        "compass",
        "radar",
        "release-notes",
        "technical-plans",
    }
)
EVALUATION_EVIDENCE_FILES = frozenset(
    {
        "discipline-evaluation-corpus.v1.json",
        "guidance-behavior-evaluation-corpus.v1.json",
        "intervention-value-adjudication-corpus.v1.json",
        "optimization-evaluation-corpus.v1.json",
    }
)
DIST_EVIDENCE_PREFIXES = (
    "greenfield-post-confirm-",
)
GENERIC_PRODUCT_TERMS = frozenset(
    {
        "archive",
        "care",
        "certification",
        "credit",
        "custody",
        "dependency",
        "deployment",
        "developer",
        "disclosure",
        "evidence",
        "flood",
        "credential",
        "guardian",
        "incident",
        "open",
        "package",
        "placement",
        "port",
        "product",
        "provenance",
        "reliability",
        "resident",
        "review",
        "rights",
        "runbook",
        "screening",
        "security",
        "source",
        "union",
        "waiver",
    }
)


@dataclass(frozen=True)
class LeakageFinding:
    location: str
    term: str
    line: int


def domain_leakage_terms() -> tuple[str, ...]:
    """Return distinctive release-matrix terms that must not enter platform custody."""

    terms: set[str] = set()
    for case in default_cases():
        for term in case.required_terms:
            normalized = _normalize_term(term)
            if normalized and normalized not in GENERIC_PRODUCT_TERMS:
                terms.add(normalized)
    return tuple(sorted(terms))


def scan_repo(repo_root: Path, terms: tuple[str, ...] | None = None) -> tuple[LeakageFinding, ...]:
    scan_terms = terms or domain_leakage_terms()
    findings: list[LeakageFinding] = []
    for scan_path in SOURCE_SCAN_PATHS:
        path = repo_root / scan_path
        if path.is_file():
            findings.extend(_scan_file(path, repo_root=repo_root, location_prefix="", terms=scan_terms))
        elif path.is_dir():
            for file_path in sorted(path.rglob("*")):
                if _should_scan_source_file(file_path, repo_root):
                    findings.extend(_scan_file(file_path, repo_root=repo_root, location_prefix="", terms=scan_terms))
    return tuple(findings)


def scan_dist(dist_dir: Path, terms: tuple[str, ...] | None = None) -> tuple[LeakageFinding, ...]:
    scan_terms = terms or domain_leakage_terms()
    findings: list[LeakageFinding] = []
    if not dist_dir.exists():
        return ()
    for file_path in sorted(dist_dir.iterdir()):
        if file_path.is_file() and file_path.name.endswith(".whl"):
            findings.extend(_scan_wheel(file_path, terms=scan_terms))
        elif file_path.is_file() and _should_scan_dist_text_file(file_path):
            findings.extend(_scan_file(file_path, repo_root=dist_dir, location_prefix="dist:", terms=scan_terms))
    return tuple(findings)


def _scan_wheel(wheel: Path, *, terms: tuple[str, ...]) -> tuple[LeakageFinding, ...]:
    findings: list[LeakageFinding] = []
    with zipfile.ZipFile(wheel) as zf:
        for name in sorted(zf.namelist()):
            if not _should_scan_wheel_member(name):
                continue
            try:
                text = zf.read(name).decode("utf-8")
            except UnicodeDecodeError:
                continue
            findings.extend(_scan_text(text, location=f"wheel:{wheel.name}:{name}", terms=terms))
    return tuple(findings)


def _scan_file(
    path: Path,
    *,
    repo_root: Path,
    location_prefix: str,
    terms: tuple[str, ...],
) -> tuple[LeakageFinding, ...]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ()
    location = f"{location_prefix}{path.relative_to(repo_root).as_posix()}"
    return _scan_text(text, location=location, terms=terms)


def _scan_text(text: str, *, location: str, terms: tuple[str, ...]) -> tuple[LeakageFinding, ...]:
    findings: list[LeakageFinding] = []
    lowered_lines = text.casefold().splitlines()
    for line_number, line in enumerate(lowered_lines, start=1):
        line_tokens = set(_tokens(line))
        for term in terms:
            term_tokens = _tokens(term)
            if len(term_tokens) == 1:
                if term_tokens[0] in line_tokens:
                    findings.append(LeakageFinding(location=location, term=term, line=line_number))
            elif _contains_phrase(line, term_tokens):
                findings.append(LeakageFinding(location=location, term=term, line=line_number))
    return tuple(findings)


def _should_scan_source_file(path: Path, repo_root: Path) -> bool:
    if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    relative = path.relative_to(repo_root).as_posix()
    if relative in MATRIX_FIXTURE_PATHS:
        return False
    if path.name in EVALUATION_EVIDENCE_FILES:
        return False
    parts = set(Path(relative).parts)
    if "worktrees" in parts or ".odylith" in parts:
        return False
    if "__pycache__" in parts or ".mypy_cache" in parts or ".pytest_cache" in parts:
        return False
    if "tests" in parts:
        return False
    if parts & GOVERNANCE_EVIDENCE_PARTS and "agents-guidelines" not in parts and "skills" not in parts:
        return False
    return True


def _should_scan_wheel_member(name: str) -> bool:
    path = Path(name)
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    parts = set(path.parts)
    if "tests" in parts or "__pycache__" in parts:
        return False
    return name.startswith("odylith/") or name.endswith(".dist-info/METADATA")


def _should_scan_dist_text_file(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    return not any(path.name.startswith(prefix) for prefix in DIST_EVIDENCE_PREFIXES)


def _normalize_term(term: str) -> str:
    return " ".join(_tokens(term))


def _tokens(text: str) -> tuple[str, ...]:
    tokens: list[str] = []
    current: list[str] = []
    for char in text.casefold():
        if char.isalnum():
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tuple(tokens)


def _contains_phrase(line: str, term_tokens: tuple[str, ...]) -> bool:
    line_tokens = _tokens(line)
    if len(term_tokens) > len(line_tokens):
        return False
    width = len(term_tokens)
    return any(line_tokens[index : index + width] == term_tokens for index in range(len(line_tokens) - width + 1))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--dist-dir", type=Path)
    args = parser.parse_args(argv)

    terms = domain_leakage_terms()
    findings = list(scan_repo(args.repo_root.resolve(), terms=terms))
    if args.dist_dir is not None:
        findings.extend(scan_dist(args.dist_dir.resolve(), terms=terms))

    if findings:
        print("platform domain leakage check failed", file=sys.stderr)
        for finding in findings[:40]:
            print(f"- {finding.location}:{finding.line}: leaked `{finding.term}`", file=sys.stderr)
        remaining = len(findings) - 40
        if remaining > 0:
            print(f"- ... {remaining} additional finding(s)", file=sys.stderr)
        return 1

    print(f"platform domain leakage check passed: {len(terms)} distinctive fixture term(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
