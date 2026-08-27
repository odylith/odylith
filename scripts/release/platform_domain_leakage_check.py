#!/usr/bin/env python3
"""Fail when explicit semantic-fixture custody sentinels enter platform code."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import tarfile
import zipfile


DEFAULT_FIXTURE_PATH = "scripts/release/fixtures/greenfield-semantic-smoke.v37.json"
FIXTURE_AUTHORING_FILES = frozenset(
    {"scripts/release/generate_greenfield_semantic_smoke_fixture.py"}
)
TEXT_SUFFIXES = frozenset(
    {".css", ".html", ".js", ".json", ".md", ".mjs", ".py", ".sh", ".toml", ".txt", ".yaml", ".yml"}
)
SOURCE_SCAN_PATHS = (
    "src/odylith",
    "bin",
    "scripts/release",
    "README.md",
    "AGENTS.md",
    "pyproject.toml",
    "docs",
    "odylith/agents-guidelines",
    "odylith/skills",
    "odylith/registry/source/components",
    ".codex",
    ".agents",
    ".claude",
)
GOVERNANCE_EVIDENCE_PARTS = frozenset(
    {"casebook", "compass", "radar", "release-notes", "technical-plans"}
)
EVALUATION_EVIDENCE_FILES = frozenset(
    {
        "discipline-evaluation-corpus.v1.json",
        "guidance-behavior-evaluation-corpus.v1.json",
        "intervention-value-adjudication-corpus.v1.json",
        "optimization-evaluation-corpus.v1.json",
    }
)


@dataclass(frozen=True)
class LeakageFinding:
    location: str
    sentinel: str
    line: int


def load_custody_sentinels(
    *,
    repo_root: Path,
    fixture_paths: Iterable[Path] | None = None,
) -> tuple[str, ...]:
    """Load explicit, source-grounded sentinels from semantic release fixtures."""

    root = Path(repo_root).expanduser().resolve()
    paths = tuple(fixture_paths or (root / DEFAULT_FIXTURE_PATH,))
    if not paths:
        raise RuntimeError("platform custody check requires at least one semantic release fixture")
    sentinels: list[str] = []
    for value in paths:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"semantic release fixture is unreadable: {path}: {exc}") from exc
        if not isinstance(payload, Mapping):
            raise RuntimeError(f"semantic release fixture must be a JSON object: {path}")
        declared = payload.get("platform_custody_sentinels")
        if not isinstance(declared, list) or not declared:
            raise RuntimeError(f"semantic release fixture lacks platform_custody_sentinels: {path}")
        evidence = _fixture_evidence(payload)
        for raw in declared:
            sentinel = str(raw or "").strip()
            if not sentinel:
                raise RuntimeError(f"semantic release fixture contains an empty custody sentinel: {path}")
            if _normalized_text(sentinel) not in evidence:
                raise RuntimeError(
                    f"semantic release fixture custody sentinel is not grounded in its prompt or packet: {sentinel!r}"
                )
            sentinels.append(sentinel)
    normalized = [_normalized_text(value) for value in sentinels]
    if len(normalized) != len(set(normalized)):
        raise RuntimeError("semantic release fixtures contain duplicate platform custody sentinels")
    return tuple(sentinels)


def scan_platform_custody(
    *,
    repo_root: Path,
    dist_dir: Path | None = None,
    sentinels: Iterable[str] | None = None,
    fixture_paths: Iterable[Path] | None = None,
) -> tuple[LeakageFinding, ...]:
    root = Path(repo_root).expanduser().resolve()
    selected = tuple(sentinels or load_custody_sentinels(repo_root=root, fixture_paths=fixture_paths))
    findings = list(_scan_documents(_repo_documents(root), sentinels=selected))
    if dist_dir is not None:
        findings.extend(_scan_documents(_dist_documents(Path(dist_dir).expanduser().resolve()), sentinels=selected))
    return tuple(findings)


def scan_repo(repo_root: Path, sentinels: Iterable[str]) -> tuple[LeakageFinding, ...]:
    root = Path(repo_root).expanduser().resolve()
    return _scan_documents(_repo_documents(root), sentinels=tuple(sentinels))


def scan_dist(dist_dir: Path, sentinels: Iterable[str]) -> tuple[LeakageFinding, ...]:
    return _scan_documents(_dist_documents(Path(dist_dir).expanduser().resolve()), sentinels=tuple(sentinels))


def _fixture_evidence(payload: Mapping[str, object]) -> str:
    prompt = str(payload.get("prompt") or "")
    packet = payload.get("packet")
    packet_text = json.dumps(packet, ensure_ascii=False, sort_keys=True) if isinstance(packet, Mapping) else ""
    return _normalized_text(f"{prompt}\n{packet_text}")


def _normalized_text(value: str) -> str:
    """Normalize separators only; never infer words, stems, synonyms, or meaning."""

    output: list[str] = []
    separator_pending = False
    for character in str(value or "").casefold():
        if character.isalnum():
            if separator_pending and output:
                output.append(" ")
            output.append(character)
            separator_pending = False
        else:
            separator_pending = True
    return "".join(output).strip()


def _repo_documents(repo_root: Path) -> tuple[tuple[str, str], ...]:
    documents: list[tuple[str, str]] = []
    for relative in SOURCE_SCAN_PATHS:
        path = repo_root / relative
        if path.is_file() and _should_scan_source_file(path, repo_root):
            documents.extend(_file_document(path, location=relative))
        elif path.is_dir():
            for file_path in sorted(path.rglob("*")):
                if _should_scan_source_file(file_path, repo_root):
                    documents.extend(_file_document(file_path, location=file_path.relative_to(repo_root).as_posix()))
    return tuple(documents)


def _dist_documents(dist_dir: Path) -> tuple[tuple[str, str], ...]:
    documents: list[tuple[str, str]] = []
    if not dist_dir.exists():
        return ()
    for path in sorted(dist_dir.iterdir()):
        if path.is_file() and path.name.endswith(".whl"):
            with zipfile.ZipFile(path) as archive:
                for name in sorted(archive.namelist()):
                    if _should_scan_archive_member(name):
                        documents.extend(_decoded_document(archive.read(name), location=f"wheel:{path.name}:{name}"))
        elif path.is_file() and path.name.endswith(".tar.gz"):
            with tarfile.open(path) as archive:
                for member in sorted(archive.getmembers(), key=lambda item: item.name):
                    if not member.isfile() or not _should_scan_archive_member(member.name):
                        continue
                    extracted = archive.extractfile(member)
                    if extracted is not None:
                        documents.extend(_decoded_document(extracted.read(), location=f"tar:{path.name}:{member.name}"))
        elif path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            documents.extend(_file_document(path, location=f"dist:{path.name}"))
    return tuple(documents)


def _file_document(path: Path, *, location: str) -> tuple[tuple[str, str], ...]:
    try:
        return ((location, path.read_text(encoding="utf-8")),)
    except UnicodeDecodeError:
        return ()


def _decoded_document(value: bytes, *, location: str) -> tuple[tuple[str, str], ...]:
    try:
        return ((location, value.decode("utf-8")),)
    except UnicodeDecodeError:
        return ()


def _scan_documents(
    documents: Iterable[tuple[str, str]],
    *,
    sentinels: tuple[str, ...],
) -> tuple[LeakageFinding, ...]:
    normalized = tuple((sentinel, _normalized_text(sentinel)) for sentinel in sentinels)
    findings: list[LeakageFinding] = []
    for location, text in documents:
        for line_number, line in enumerate(text.splitlines(), start=1):
            normalized_line = _normalized_text(line)
            for sentinel, normalized_sentinel in normalized:
                if normalized_sentinel and normalized_sentinel in normalized_line:
                    findings.append(LeakageFinding(location=location, sentinel=sentinel, line=line_number))
    return tuple(findings)


def _should_scan_source_file(path: Path, repo_root: Path) -> bool:
    if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    relative = path.relative_to(repo_root)
    parts = set(relative.parts)
    if (
        relative.as_posix().startswith("scripts/release/fixtures/")
        or relative.as_posix() in FIXTURE_AUTHORING_FILES
    ):
        return False
    if path.name in EVALUATION_EVIDENCE_FILES or "tests" in parts:
        return False
    if parts & {"__pycache__", ".mypy_cache", ".pytest_cache", ".odylith", "worktrees"}:
        return False
    return not (parts & GOVERNANCE_EVIDENCE_PARTS and "agents-guidelines" not in parts and "skills" not in parts)


def _should_scan_archive_member(name: str) -> bool:
    path = Path(name)
    parts = set(path.parts)
    if path.suffix.lower() not in TEXT_SUFFIXES or parts & {"tests", "__pycache__"}:
        return False
    return name.startswith("odylith/") or "/odylith/" in name or name.endswith(".dist-info/METADATA")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--dist-dir", type=Path)
    parser.add_argument("--semantic-fixture", type=Path, action="append")
    args = parser.parse_args(argv)
    try:
        sentinels = load_custody_sentinels(repo_root=args.repo_root, fixture_paths=args.semantic_fixture)
        findings = scan_platform_custody(repo_root=args.repo_root, dist_dir=args.dist_dir, sentinels=sentinels)
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile, tarfile.TarError) as exc:
        print(f"platform custody check failed: {exc}", file=sys.stderr)
        return 1
    if findings:
        print("platform custody check failed", file=sys.stderr)
        for finding in findings[:40]:
            print(
                f"- {finding.location}:{finding.line}: fixture custody leaked `{finding.sentinel}`",
                file=sys.stderr,
            )
        return 1
    print(f"platform custody check passed: {len(sentinels)} explicit semantic sentinel(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
