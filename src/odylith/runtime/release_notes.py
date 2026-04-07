from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

_FRONT_MATTER_DELIMITER = "---"
_FRONT_MATTER_KEY_RE = re.compile(r"^(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*)$")
_PUBLIC_RELEASE_NOTES_REPO = "https://github.com/odylith/odylith"


@dataclass(frozen=True)
class ReleaseNotesSource:
    version: str
    title: str
    published_at: str
    summary: str
    highlights: tuple[str, ...]
    body: str
    note_link_label: str
    external_link_label: str
    reopen_label: str
    source_path: Path


def release_notes_path(*, repo_root: str | Path, version: str) -> Path:
    token = str(version or "").strip().lstrip("v")
    return (
        Path(repo_root).expanduser().resolve()
        / "odylith"
        / "runtime"
        / "source"
        / "release-notes"
        / f"v{token}.md"
    )


def github_release_notes_url(*, version: str, release_tag: str = "") -> str:
    version_token = str(version or "").strip().lstrip("v")
    if not version_token:
        return ""
    ref_token = str(release_tag or f"v{version_token}").strip() or f"v{version_token}"
    return f"{_PUBLIC_RELEASE_NOTES_REPO}/blob/{ref_token}/odylith/runtime/source/release-notes/v{version_token}.md"


def _normalize_text(value: Any, *, limit: int = 240) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    token = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", token)
    token = re.sub(r"<[^>]+>", "", token)
    token = re.sub(r"[*_`>#]", "", token)
    token = re.sub(r"\s+", " ", token).strip(" -:")
    if len(token) > limit:
        token = token[: limit - 3].rstrip() + "..."
    return token


def _paragraphs(body: str, *, limit: int) -> list[str]:
    text = str(body or "").strip()
    if not text:
        return []
    paragraphs: list[str] = []
    for segment in re.split(r"\n\s*\n", text):
        lines: list[str] = []
        for raw_line in segment.splitlines():
            line = str(raw_line or "").strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(("- ", "* ", "+ ")):
                continue
            numbered = re.match(r"^\d+\.\s+(?P<text>.+)$", line)
            if numbered:
                line = str(numbered.group("text") or "").strip()
            normalized = _normalize_text(line)
            if normalized:
                lines.append(normalized)
        paragraph = _normalize_text(" ".join(lines))
        if paragraph and paragraph not in paragraphs:
            paragraphs.append(paragraph)
        if len(paragraphs) >= limit:
            break
    return paragraphs[:limit]


def _heading_title(body: str) -> str:
    text = str(body or "").strip()
    if not text:
        return ""
    for raw_line in text.splitlines():
        line = str(raw_line or "").strip()
        if not line:
            continue
        heading = re.match(r"^#\s+(?P<text>.+)$", line)
        if heading is None:
            continue
        return _normalize_text(heading.group("text"), limit=120)
    return ""


def _parse_front_matter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith(f"{_FRONT_MATTER_DELIMITER}\n"):
        return {}, text
    end = text.find(f"\n{_FRONT_MATTER_DELIMITER}\n", len(_FRONT_MATTER_DELIMITER) + 1)
    if end < 0:
        return {}, text
    header = text[len(_FRONT_MATTER_DELIMITER) + 1 : end]
    body = text[end + len(_FRONT_MATTER_DELIMITER) + 2 :].lstrip("\n")
    payload: dict[str, object] = {}
    current_list_key = ""
    current_list: list[str] = []
    for raw_line in header.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if current_list_key and stripped.startswith("- "):
            token = _normalize_text(stripped[2:])
            if token:
                current_list.append(token)
            continue
        if current_list_key:
            payload[current_list_key] = tuple(current_list)
            current_list_key = ""
            current_list = []
        match = _FRONT_MATTER_KEY_RE.match(stripped)
        if match is None:
            continue
        key = str(match.group("key") or "").strip().lower()
        value = str(match.group("value") or "").strip()
        if not key:
            continue
        if key == "highlights" and not value:
            current_list_key = key
            current_list = []
            continue
        payload[key] = value
    if current_list_key:
        payload[current_list_key] = tuple(current_list)
    return payload, body


def load_release_notes_source(*, repo_root: str | Path, version: str) -> ReleaseNotesSource | None:
    path = release_notes_path(repo_root=repo_root, version=version)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    front_matter, body = _parse_front_matter(text)
    normalized_body = str(body or "").strip()
    raw_highlights = front_matter.get("highlights")
    highlights = (
        tuple(
            token
            for token in raw_highlights
            if str(token).strip()
        )[:3]
        if isinstance(raw_highlights, tuple)
        else ()
    )
    if not highlights and normalized_body:
        bullet_highlights: list[str] = []
        for raw_line in normalized_body.splitlines():
            line = str(raw_line or "").strip()
            if not line.startswith(("- ", "* ", "+ ")):
                continue
            token = _normalize_text(line[2:])
            if token and token not in bullet_highlights:
                bullet_highlights.append(token)
            if len(bullet_highlights) >= 3:
                break
        highlights = tuple(bullet_highlights[:3])
    paragraphs = _paragraphs(normalized_body, limit=2)
    summary = _normalize_text(front_matter.get("summary") or "") or (paragraphs[0] if paragraphs else "")
    return ReleaseNotesSource(
        version=_normalize_text(front_matter.get("version") or version, limit=64).lstrip("v"),
        title=_normalize_text(front_matter.get("title") or "", limit=120) or _heading_title(normalized_body),
        published_at=_normalize_text(front_matter.get("published_at") or "", limit=64),
        summary=summary,
        highlights=highlights,
        body=normalized_body,
        note_link_label=_normalize_text(front_matter.get("note_link_label") or "", limit=120),
        external_link_label=_normalize_text(front_matter.get("external_link_label") or "", limit=120),
        reopen_label=_normalize_text(front_matter.get("reopen_label") or "", limit=120),
        source_path=path,
    )
