"""Validate implementation-plan traceability contract.

Contract scope:
- active technical plans under `odylith/technical-plans/in-progress/*.md`
- each plan must include a `## Traceability` section with:
  - `### Runbooks`
  - `### Developer Docs`
  - `### Code References`
- each subsection must include at least one file path entry and every path must exist.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Sequence


_REQUIRED_TRACEABILITY_SUBSECTIONS: tuple[str, ...] = (
    "Runbooks",
    "Developer Docs",
    "Code References",
)
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_CHECKBOX_RE = re.compile(r"^\[(?:x|X| )\]\s*")
_PATH_LIKE_RE = re.compile(r"^[A-Za-z0-9._/\-]+$")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description="Validate runbook/devdocs/code traceability in active implementation plans.",
    )
    parser.add_argument("--repo-root", default=".")
    return parser.parse_args(argv)


def _extract_sections(path: Path) -> dict[str, list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)
    return sections


def _extract_traceability_subsections(lines: list[str]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            current = stripped[4:].strip()
            buckets.setdefault(current, [])
            continue
        if current is None:
            continue
        if not stripped:
            continue
        buckets.setdefault(current, []).append(line)
    return buckets


def _extract_path_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for match in _MARKDOWN_LINK_RE.finditer(text):
        token = str(match.group(1)).strip()
        if token:
            tokens.append(token)
    for match in _INLINE_CODE_RE.finditer(text):
        token = str(match.group(1)).strip()
        if token:
            tokens.append(token)
    return tokens


def _infer_repo_root_from_path(path: Path) -> Path | None:
    target = path.resolve()
    for candidate in (target, *target.parents):
        try:
            if (candidate / ".git").exists() or (candidate / "AGENTS.md").is_file():
                return candidate
        except OSError:
            continue
    return None


def _normalize_path_token(*, repo_root: Path, token: str) -> str:
    raw = str(token or "").strip().strip(".,;:")
    if not raw:
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return ""
    if "<" in raw or ">" in raw or " " in raw:
        return ""
    if not _PATH_LIKE_RE.fullmatch(raw):
        return ""

    path = Path(raw)
    if path.is_absolute():
        resolved = path.resolve()
        repo_root_resolved = repo_root.resolve()
        try:
            rel = resolved.relative_to(repo_root_resolved)
            return rel.as_posix()
        except ValueError:
            linked_repo_root = _infer_repo_root_from_path(resolved)
            if linked_repo_root is None:
                return ""
            try:
                rel = resolved.relative_to(linked_repo_root.resolve())
            except ValueError:
                return ""
            rebased = (repo_root_resolved / rel).resolve()
            if rebased.exists():
                return rel.as_posix()
            return ""
    return path.as_posix().lstrip("./")


def _bucket_matches_path(*, bucket: str, rel_path: str) -> bool:
    if bucket == "Runbooks":
        return (
            rel_path.startswith("docs/runbooks/")
            or rel_path.endswith("RUNBOOK.md")
            or rel_path.endswith("OPERATIONS.md")
        )
    if bucket == "Developer Docs":
        if rel_path.startswith("docs/") and not rel_path.startswith("docs/runbooks/"):
            return True
        if rel_path.startswith("odylith/"):
            if rel_path.startswith(
                (
                    "odylith/radar/source/",
                    "odylith/casebook/bugs/",
                    "odylith/atlas/source/",
                    "odylith/compass/runtime/",
                    "odylith/technical-plans/",
                )
            ):
                return False
            return rel_path.endswith(".md")
        return False
    if bucket == "Code References":
        return not rel_path.startswith("docs/")
    return False


def validate_plan_traceability_contract(*, repo_root: Path) -> list[str]:
    errors: list[str] = []
    plan_root = repo_root / "odylith" / "technical-plans" / "in-progress"
    if not plan_root.is_dir():
        errors.append(f"missing directory: {plan_root}")
        return errors

    plan_paths = sorted(path for path in plan_root.glob("*.md") if path.is_file())
    if not plan_paths:
        return errors

    for plan_path in plan_paths:
        sections = _extract_sections(plan_path)
        traceability_lines = sections.get("Traceability")
        if traceability_lines is None:
            errors.append(f"{plan_path}: missing required section `## Traceability`")
            continue

        subsection_rows = _extract_traceability_subsections(traceability_lines)
        for subsection in _REQUIRED_TRACEABILITY_SUBSECTIONS:
            rows = subsection_rows.get(subsection, [])
            if not rows:
                errors.append(
                    f"{plan_path}: missing required subsection entries under `### {subsection}`"
                )
                continue

            normalized_paths: list[str] = []
            for raw in rows:
                stripped = raw.strip()
                if not stripped.lstrip().startswith("- "):
                    continue
                item = stripped.lstrip()[2:].strip()
                item = _CHECKBOX_RE.sub("", item).strip()
                for token in _extract_path_tokens(item):
                    normalized = _normalize_path_token(repo_root=repo_root, token=token)
                    if normalized:
                        normalized_paths.append(normalized)

            if not normalized_paths:
                errors.append(
                    f"{plan_path}: subsection `### {subsection}` must include at least one file path entry"
                )
                continue

            deduped = sorted(set(normalized_paths))
            for rel_path in deduped:
                target = (repo_root / rel_path).resolve()
                if not target.exists():
                    errors.append(
                        f"{plan_path}: traceability path does not exist in `### {subsection}`: `{rel_path}`"
                    )
                    continue
                if not _bucket_matches_path(bucket=subsection, rel_path=rel_path):
                    errors.append(
                        f"{plan_path}: path `{rel_path}` is in wrong bucket for `### {subsection}`"
                    )

    return errors


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    errors = validate_plan_traceability_contract(repo_root=repo_root)
    if errors:
        print("plan traceability contract FAILED")
        for error in errors:
            print(f"- {error}")
        return 2

    plan_count = len(list((repo_root / "odylith" / "technical-plans" / "in-progress").glob("*.md")))
    print("plan traceability contract passed")
    print(f"- plans validated: {plan_count}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
