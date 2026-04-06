"""Normalize `Risks & Mitigations` sections across plan markdown files.

This script standardizes Risk -> Mitigation nesting so plans are consistent
for historical, active, and future workstreams.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Sequence


_PLAN_GLOBS: tuple[str, ...] = (
    "odylith/technical-plans/in-progress/*.md",
    "odylith/technical-plans/done/**/*.md",
)
_RISK_SECTION_HEADING_RE = re.compile(
    r"^##\s+Risks(?:\s*(?:&|/)\s*Mitigations)?\s*$",
    re.IGNORECASE,
)
_LEVEL2_HEADING_RE = re.compile(r"^##\s+")
_BULLET_RE = re.compile(r"^(?P<indent>\s*)[-*]\s+(?P<body>.+?)\s*$")
_CHECKBOX_RE = re.compile(r"^\[(?P<mark>[xX ])\]\s*(?P<body>.*)$")
_RISK_LABEL_RE = re.compile(r"^(?:\*\*)?\s*Risk(?:\*\*)?\s*:\s*(?P<body>.+?)\s*$", re.IGNORECASE)
_MITIGATION_LABEL_RE = re.compile(
    r"^(?:\*\*)?\s*Mitigation(?:\*\*)?\s*:\s*(?P<body>.+?)\s*$",
    re.IGNORECASE,
)
_INLINE_RISK_MITIGATION_RE = re.compile(
    r"^\s*(?:\*\*)?\s*Risk(?:\*\*)?\s*:\s*(?P<risk>.+?)\s+"
    r"(?:\*\*)?\s*Mitigation(?:\*\*)?\s*:\s*(?P<mitigation>.+?)\s*$",
    re.IGNORECASE,
)
_PLACEHOLDER_MITIGATION = "TODO (add explicit mitigation)."


@dataclass
class _RiskEntry:
    checked: bool
    risk_text: str
    mitigations: list[tuple[bool, str]] = field(default_factory=list)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith sync",
        description=(
            "Normalize `## Risks & Mitigations` sections so each top-level risk has nested mitigations."
        ),
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail closed when normalization would change files (no writes).",
    )
    return parser.parse_args(argv)


def _list_plan_files(*, repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in _PLAN_GLOBS:
        files.extend(path for path in repo_root.glob(pattern) if path.is_file())
    return sorted(set(path.resolve() for path in files))


def _trimmed(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def _parse_checkbox(*, body: str) -> tuple[bool, str]:
    match = _CHECKBOX_RE.match(body.strip())
    if not match:
        return False, body.strip()
    checked = str(match.group("mark")).lower() == "x"
    return checked, str(match.group("body") or "").strip()


def _parse_risk_or_mitigation(text: str) -> tuple[str | None, str]:
    raw = _trimmed(text)
    if not raw:
        return None, ""

    inline = _INLINE_RISK_MITIGATION_RE.match(raw)
    if inline:
        risk = _trimmed(str(inline.group("risk")))
        mitigation = _trimmed(str(inline.group("mitigation")))
        return "inline", f"{risk}\n{mitigation}"

    risk_match = _RISK_LABEL_RE.match(raw)
    if risk_match:
        return "risk", _trimmed(str(risk_match.group("body")))

    mitigation_match = _MITIGATION_LABEL_RE.match(raw)
    if mitigation_match:
        return "mitigation", _trimmed(str(mitigation_match.group("body")))

    return None, raw


def _emit_entry(lines: list[str], entry: _RiskEntry) -> None:
    risk_checked = "x" if entry.checked else " "
    risk_text = _trimmed(entry.risk_text) or "Unspecified risk (legacy backfill)."
    lines.append(f"- [{risk_checked}] Risk: {risk_text}")
    mitigations = [
        (checked, _trimmed(text))
        for checked, text in entry.mitigations
        if _trimmed(text)
    ]
    has_real_mitigation = any(text != _PLACEHOLDER_MITIGATION for _, text in mitigations)
    if has_real_mitigation:
        mitigations = [
            (checked, text)
            for checked, text in mitigations
            if text != _PLACEHOLDER_MITIGATION
        ]
    if not mitigations:
        mitigations = [(False, _PLACEHOLDER_MITIGATION)]

    for mitigation_checked, mitigation_text in mitigations:
        mark = "x" if mitigation_checked else " "
        body = _trimmed(mitigation_text) or _PLACEHOLDER_MITIGATION
        lines.append(f"  - [{mark}] Mitigation: {body}")


def _normalize_risk_section_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    pending: _RiskEntry | None = None

    def flush_pending() -> None:
        nonlocal pending
        if pending is None:
            return
        _emit_entry(out, pending)
        pending = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_pending()
            if out and out[-1] != "":
                out.append("")
            continue

        bullet_match = _BULLET_RE.match(line)
        if not bullet_match:
            plain_tag, plain_payload = _parse_risk_or_mitigation(stripped)
            if plain_tag == "inline":
                risk_text, mitigation_text = plain_payload.split("\n", 1)
                flush_pending()
                pending = _RiskEntry(
                    checked=False,
                    risk_text=risk_text,
                    mitigations=[(False, mitigation_text)],
                )
                continue
            if plain_tag == "risk":
                flush_pending()
                pending = _RiskEntry(checked=False, risk_text=plain_payload)
                continue
            if plain_tag == "mitigation":
                if pending is None:
                    pending = _RiskEntry(checked=False, risk_text="Unspecified risk (legacy backfill).")
                pending.mitigations.append((pending.checked, plain_payload))
                continue

            flush_pending()
            out.append(line)
            continue

        indent = len(str(bullet_match.group("indent")).expandtabs(2))
        checked, bullet_body = _parse_checkbox(body=str(bullet_match.group("body")))
        tag, payload = _parse_risk_or_mitigation(bullet_body)

        if tag == "inline":
            risk_text, mitigation_text = payload.split("\n", 1)
            flush_pending()
            pending = _RiskEntry(
                checked=checked,
                risk_text=risk_text,
                mitigations=[(checked, mitigation_text)],
            )
            continue

        if tag == "risk":
            flush_pending()
            pending = _RiskEntry(checked=checked, risk_text=payload)
            continue

        if tag == "mitigation":
            if pending is None:
                pending = _RiskEntry(checked=False, risk_text="Unspecified risk (legacy backfill).")
            pending.mitigations.append((checked, payload))
            continue

        if pending is not None and indent >= 2:
            pending.mitigations.append((checked, payload))
            continue

        flush_pending()
        out.append(f"- [{'x' if checked else ' '}] {payload}")

    flush_pending()

    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def normalize_risk_mitigation_markdown(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        if not _RISK_SECTION_HEADING_RE.match(line.strip()):
            out.append(line)
            idx += 1
            continue

        out.append("## Risks & Mitigations")
        idx += 1
        section_lines: list[str] = []
        while idx < len(lines) and not _LEVEL2_HEADING_RE.match(lines[idx]):
            section_lines.append(lines[idx])
            idx += 1

        normalized = _normalize_risk_section_lines(section_lines)
        out.append("")
        out.extend(normalized)
        out.append("")

    rendered = "\n".join(out).rstrip() + "\n"
    return rendered


def normalize_plan_risk_mitigation(*, repo_root: Path, check_only: bool) -> tuple[int, list[str]]:
    changed: list[str] = []
    for plan_path in _list_plan_files(repo_root=repo_root):
        source = plan_path.read_text(encoding="utf-8")
        rendered = normalize_risk_mitigation_markdown(source)
        if source == rendered:
            continue
        rel = plan_path.relative_to(repo_root).as_posix()
        changed.append(rel)
        if not check_only:
            plan_path.write_text(rendered, encoding="utf-8")
    return len(changed), changed


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    changed_count, changed_files = normalize_plan_risk_mitigation(
        repo_root=repo_root,
        check_only=bool(args.check),
    )

    if changed_count == 0:
        print("plan risk/mitigation normalization passed")
        print("- files changed: 0")
        return 0

    if args.check:
        print("plan risk/mitigation normalization FAILED")
        print("- run: odylith sync --repo-root . --force")
        for rel in changed_files:
            print(f"- would change: {rel}")
        return 2

    print("plan risk/mitigation normalization applied")
    print(f"- files changed: {changed_count}")
    for rel in changed_files:
        print(f"- updated: {rel}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
