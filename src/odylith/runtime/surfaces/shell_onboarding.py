"""Shared first-run onboarding contract for the Odylith shell and installer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from odylith.common.release_text import normalize_release_text as _normalize_release_note_text
from odylith.install.state import load_install_state
from odylith.install.state import load_upgrade_spotlight
from odylith.install.state import load_version_pin
from odylith.install.state import version_pin_path
from odylith.runtime import release_notes

STARTER_PROMPT = (
    "Use Odylith to start this repo from one real code path. Pick one path that matters, then create the "
    "first Radar item, first Registry boundary, and first Atlas map around that same path. First show me "
    "5 bullets with the path you picked and why. Then create the Odylith files. Plain English. Real file "
    "paths only. No IDs. Only write under odylith/."
)
AUTO_REFRESH_NOTE = "The shell refreshes itself as Odylith updates local surfaces."
LATEST_INSTALL_COMMAND = "curl -fsSL https://odylith.ai/install.sh | bash"
_LEGACY_CONSUMER_UPGRADE_VERSIONS = frozenset({"0.1.0", "0.1.1"})
_LAUNCHER_BOOTSTRAP_MARKER = "odylith_launcher_bootstrap_upgrade"

_GENERIC_FOCUS_TOKENS = {
    "api",
    "app",
    "apps",
    "backend",
    "client",
    "cmd",
    "frontend",
    "internal",
    "lib",
    "packages",
    "repo",
    "server",
    "service",
    "services",
    "src",
    "web",
}
_IGNORED_TOP_LEVEL_DIRS = {
    ".git",
    ".hg",
    ".idea",
    ".odylith",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "odylith",
    "target",
    "venv",
}
_STACK_MARKERS: tuple[tuple[str, str], ...] = (
    ("pyproject.toml", "Python"),
    ("package.json", "Node"),
    ("go.mod", "Go"),
    ("Cargo.toml", "Rust"),
    ("pom.xml", "Java"),
    ("build.gradle", "Gradle"),
    ("Gemfile", "Ruby"),
)
_PRIORITY_DIRS: tuple[str, ...] = (
    "packages",
    "apps",
    "services",
    "src",
    "backend",
    "frontend",
    "web",
    "api",
    "server",
    "client",
    "cmd",
    "internal",
    "lib",
)
_WELCOME_DISMISS_VERSION = "welcome-v2"
_UPGRADE_SPOTLIGHT_MAX_AGE = timedelta(minutes=10)


@dataclass(frozen=True)
class _RepoFocus:
    focus_path: str
    component_id: str
    component_label: str
    stack_labels: tuple[str, ...]
    visible_roots: tuple[str, ...]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _parse_iso_utc(value: Any) -> datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    normalized = token.replace("Z", "+00:00") if token.endswith("Z") else token
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _release_spotlight_has_aged_out(payload: dict[str, object]) -> bool:
    recorded_at = _parse_iso_utc(payload.get("recorded_utc")) or _parse_iso_utc(payload.get("release_published_at"))
    if recorded_at is None:
        return False
    return (_utc_now() - recorded_at) > _UPGRADE_SPOTLIGHT_MAX_AGE


def _release_placeholder_markers(*, version: str) -> set[str]:
    normalized_version = re.sub(r"[^a-z0-9]", "", str(version or "").strip().lower().removeprefix("v"))
    if not normalized_version:
        return set()
    return {
        f"odylithreleasev{normalized_version}",
        f"odylithrelease{normalized_version}",
        f"releasev{normalized_version}",
        f"release{normalized_version}",
        f"odylithv{normalized_version}",
        f"odylith{normalized_version}",
        f"vodylithrelease{normalized_version}",
    }


def _release_copy_is_placeholder(value: Any, *, version: str) -> bool:
    token = _normalize_release_note_text(value, limit=240)
    if not token:
        return False
    normalized = re.sub(r"[^a-z0-9]", "", token.lower())
    return normalized in _release_placeholder_markers(version=version)


def _clean_release_story_body(*, release_body: str, version: str) -> str:
    paragraphs = _release_note_paragraphs(release_body, limit=4)
    kept = [paragraph for paragraph in paragraphs if not _release_copy_is_placeholder(paragraph, version=version)]
    return "\n\n".join(kept[:2])


def _clean_release_story_highlights(raw_highlights: Any, *, version: str) -> list[str]:
    if not isinstance(raw_highlights, list):
        return []
    cleaned: list[str] = []
    for raw_item in raw_highlights:
        token = _normalize_release_note_text(raw_item, limit=180)
        if not token or _release_copy_is_placeholder(token, version=version) or token in cleaned:
            continue
        cleaned.append(token)
        if len(cleaned) >= 3:
            break
    return cleaned


def _format_release_story_version(value: Any) -> str:
    token = str(value or "").strip().removeprefix("v")
    if not token:
        return ""
    return f"v{token}" if token[:1].isdigit() else token


def _release_story_title(
    *,
    authored_notes: release_notes.ReleaseNotesSource | None,
    release_tag: str,
    to_version: str,
) -> str:
    if authored_notes is not None and authored_notes.title:
        return authored_notes.title
    return _format_release_story_version(release_tag or to_version)


def _release_story_note_link_label(
    *,
    authored_notes: release_notes.ReleaseNotesSource | None,
    title: str,
    release_tag: str,
    to_version: str,
) -> str:
    if authored_notes is not None and authored_notes.note_link_label:
        return authored_notes.note_link_label
    return "Open release note on GitHub"


def _release_story_external_link_label(
    *,
    authored_notes: release_notes.ReleaseNotesSource | None,
    release_url: str,
    release_tag: str,
    to_version: str,
) -> str:
    if authored_notes is not None and authored_notes.external_link_label:
        return authored_notes.external_link_label
    host = ""
    token = str(release_url or "").strip()
    if token:
        parsed = urlparse(token)
        host = str(parsed.netloc or "").strip().removeprefix("www.")
    return host or _format_release_story_version(release_tag or to_version)


def _release_story_reopen_label(
    *,
    authored_notes: release_notes.ReleaseNotesSource | None,
    title: str,
    release_tag: str,
    to_version: str,
) -> str:
    if authored_notes is not None and authored_notes.reopen_label:
        return authored_notes.reopen_label
    return _format_release_story_version(to_version or release_tag) or title


def _release_story_notes_url(
    *,
    authored_notes: release_notes.ReleaseNotesSource | None,
    release_tag: str,
    to_version: str,
) -> str:
    version = (
        authored_notes.version
        if authored_notes is not None and str(authored_notes.version).strip()
        else str(to_version or "").strip()
    )
    if not version:
        return ""
    return release_notes.github_release_notes_url(
        version=version,
        release_tag=str(release_tag or f"v{version.lstrip('v')}").strip(),
    )


def build_welcome_state(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).expanduser().resolve()
    focus = _detect_repo_focus(root)
    grounded_focus = _is_grounded_focus(root=root, focus=focus)
    focus_path = focus.focus_path if grounded_focus else ""
    component_id = focus.component_id if grounded_focus else ""
    component_label = focus.component_label if grounded_focus else ""
    chosen_slice = _chosen_slice(
        root=root,
        focus=focus,
        focus_path=focus_path,
        component_id=component_id,
        component_label=component_label,
    )
    missing_backlog = not _has_backlog_ideas(root)
    missing_component = not _has_component_specs(root)
    missing_atlas = not _has_atlas_diagrams(root)
    notices = _welcome_notices(root=root)
    dismiss_key = _welcome_dismiss_key(
        focus_path=focus_path,
        missing_backlog=missing_backlog,
        missing_component=missing_component,
        missing_atlas=missing_atlas,
        notices=notices,
    )
    show = missing_backlog or missing_component or missing_atlas
    if not show:
        return {
            "show": False,
            "notices": notices,
            "chosen_slice": chosen_slice,
            "dismiss_key": dismiss_key,
        }

    component_targets = _candidate_component_targets(root=root, focus=focus)
    facts = _repo_fact_lines(
        root=root,
        focus=focus,
        grounded_focus=grounded_focus,
        missing_backlog=missing_backlog,
        missing_component=missing_component,
        missing_atlas=missing_atlas,
    )
    quick_steps = _quick_steps(
        focus_path=focus_path,
        component_label=component_label,
        missing_backlog=missing_backlog,
        missing_component=missing_component,
        missing_atlas=missing_atlas,
    )
    surface_handoff = _surface_handoff(
        focus_path=focus_path,
        component_label=component_label,
    )
    first_uses = _first_use_suggestions(
        focus=focus,
        missing_backlog=missing_backlog,
        missing_component=missing_component,
        missing_atlas=missing_atlas,
    )
    component_suggestions = _component_suggestions(component_targets=component_targets)
    atlas_diagram_suggestions = _atlas_diagram_suggestions(
        root=root,
        focus=focus,
        component_targets=component_targets,
    )
    surface_flow = _surface_flow(focus=focus)
    surface_explainers = _surface_explainers(
        focus_path=focus_path,
        component_label=component_label,
    )
    focus_label = component_label or "first grounded slice"
    first_tasks = _first_tasks(
        focus_path=focus_path,
        component_id=component_id,
        component_label=component_label,
    )

    return {
        "show": True,
        "headline": "Start Odylith from one real code path",
        "subhead": "Open the cheatsheet drawer on the left and try out commands in this repo.",
        "dismiss_key": dismiss_key,
        "starter_prompt": STARTER_PROMPT,
        "auto_refresh_note": AUTO_REFRESH_NOTE,
        "notices": notices,
        "chosen_slice": chosen_slice,
        "quick_steps": quick_steps,
        "repo_readout": facts,
        "surface_handoff": surface_handoff,
        "repo_facts": facts,
        "first_uses": first_uses,
        "first_tasks": first_tasks,
        "component_suggestions": component_suggestions,
        "atlas_diagram_suggestions": atlas_diagram_suggestions,
        "surface_flow": surface_flow,
        "surface_explainers": surface_explainers,
        "backlog": {
            "missing": missing_backlog,
            "title": "First Radar item",
            "reason": (
                f"Seed the first Radar item around `{focus_path}`."
                if focus_path
                else "Seed the first Radar item around the code path you choose."
            ),
            "path_hint": "odylith/radar/source/ideas/",
            "preview_note": "This opens the live Radar surface. It starts empty until the first backlog item exists.",
        },
        "component": {
            "missing": missing_component,
            "component_id": component_id,
            "label": component_label,
            "title": "First Registry boundary",
            "reason": (
                f"Define the first Registry boundary for `{focus_path}`."
                if focus_path
                else "Define the first Registry boundary for the area you choose."
            ),
            "path_hint": (
                f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md"
                if component_id
                else "odylith/registry/source/components/<component>/CURRENT_SPEC.md"
            ),
            "preview_note": "This opens the live Registry surface. It fills in after the first boundary spec exists.",
        },
        "atlas": {
            "missing": missing_atlas,
            "title": "First Atlas map",
            "reason": (
                f"Add the first Atlas map for `{focus_path}`."
                if focus_path
                else "Add the first Atlas map for the area you choose."
            ),
            "path_hint": "odylith/atlas/source/",
            "preview_note": "This opens the live Atlas catalog. It fills in after the first Atlas map exists.",
        },
    }


def _welcome_dismiss_key(
    *,
    focus_path: str,
    missing_backlog: bool,
    missing_component: bool,
    missing_atlas: bool,
    notices: list[dict[str, str]],
) -> str:
    notice_titles = ",".join(
        _slugify(str(notice.get("title", "")).strip()) or "notice"
        for notice in notices
        if str(notice.get("title", "")).strip()
    ) or "none"
    focus_token = str(focus_path or "").strip() or "none"
    return "|".join(
        (
            _WELCOME_DISMISS_VERSION,
            focus_token,
            f"backlog={int(bool(missing_backlog))}",
            f"component={int(bool(missing_component))}",
            f"atlas={int(bool(missing_atlas))}",
            f"notices={notice_titles}",
        )
    )


def build_release_spotlight(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).expanduser().resolve()
    if _looks_like_product_repo(root):
        return {}
    payload = load_upgrade_spotlight(repo_root=root)
    if not payload:
        return {}
    if _release_spotlight_has_aged_out(payload):
        return {}
    from_version = str(payload.get("from_version", "")).strip()
    to_version = str(payload.get("to_version", "")).strip()
    install_state = _install_state(root)
    active_version = str(install_state.get("active_version") or "").strip()
    activation_history = [
        str(value).strip()
        for value in install_state.get("activation_history", [])
        if str(value).strip()
    ]
    if not from_version or not to_version or not active_version or from_version == to_version or to_version != active_version:
        return {}
    if len(activation_history) < 2 or activation_history[-1] != to_version or activation_history[-2] != from_version:
        return {}
    release_tag = str(payload.get("release_tag", "")).strip()
    release_url = str(payload.get("release_url", "")).strip()
    release_body = _clean_release_story_body(
        release_body=str(payload.get("release_body", "")).strip(),
        version=to_version,
    )
    authored_notes = release_notes.load_release_notes_source(repo_root=root, version=to_version)
    if authored_notes is not None:
        release_body = authored_notes.body or release_body
    highlights = _clean_release_story_highlights(payload.get("highlights"), version=to_version)
    if authored_notes is not None and authored_notes.highlights:
        highlights = [str(item).strip() for item in authored_notes.highlights if str(item).strip()][:3]
    summary, detail = _release_spotlight_copy(
        from_version=from_version,
        to_version=to_version,
        release_body=release_body,
        highlights=highlights,
    )
    if authored_notes is not None and authored_notes.summary:
        summary = authored_notes.summary
    if not summary and highlights:
        summary = highlights[0]
    if not detail:
        detail = next((item for item in highlights if item != summary), "")
    highlights = [
        item
        for item in highlights
        if item not in {summary, detail}
    ][:3]
    title = _release_story_title(
        authored_notes=authored_notes,
        release_tag=release_tag,
        to_version=to_version,
    )
    return {
        "show": True,
        "from_version": from_version,
        "to_version": to_version,
        "title": title,
        "release_tag": release_tag,
        "release_url": release_url,
        "release_published_at": (
            authored_notes.published_at
            if authored_notes is not None and authored_notes.published_at
            else str(payload.get("release_published_at", "")).strip()
        ),
        "release_body": release_body,
        "highlights": highlights,
        "summary": summary,
        "detail": detail,
        "notes_url": _release_story_notes_url(
            authored_notes=authored_notes,
            release_tag=release_tag,
            to_version=to_version,
        ),
        "notes_label": _release_story_note_link_label(
            authored_notes=authored_notes,
            title=title,
            release_tag=release_tag,
            to_version=to_version,
        ),
        "external_label": _release_story_external_link_label(
            authored_notes=authored_notes,
            release_url=release_url,
            release_tag=release_tag,
            to_version=to_version,
        ),
        "reopen_label": _release_story_reopen_label(
            authored_notes=authored_notes,
            title=title,
            release_tag=release_tag,
            to_version=to_version,
        ),
        "recorded_utc": str(payload.get("recorded_utc", "")).strip(),
        "expires_utc": _release_spotlight_expires_utc(payload),
    }


def build_version_story(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).expanduser().resolve()
    if _looks_like_product_repo(root):
        return {}
    install_state = _install_state(root)
    active_version = str(install_state.get("active_version") or "").strip()
    activation_history = [
        str(value).strip()
        for value in install_state.get("activation_history", [])
        if str(value).strip()
    ]
    if not active_version or len(activation_history) < 2 or activation_history[-1] != active_version:
        return {}
    from_version = activation_history[-2]
    to_version = activation_history[-1]
    if not from_version or not to_version or from_version == to_version:
        return {}

    payload = load_upgrade_spotlight(repo_root=root) or {}
    release_url = ""
    release_tag = ""
    release_published_at = ""
    release_body = ""
    raw_highlights: list[str] = []
    if (
        str(payload.get("from_version", "")).strip() == from_version
        and str(payload.get("to_version", "")).strip() == to_version
    ):
        release_url = str(payload.get("release_url", "")).strip()
        release_tag = str(payload.get("release_tag", "")).strip()
        release_published_at = str(payload.get("release_published_at", "")).strip()
        release_body = _clean_release_story_body(
            release_body=str(payload.get("release_body", "")).strip(),
            version=to_version,
        )
        raw_highlights = _clean_release_story_highlights(payload.get("highlights"), version=to_version)

    authored_notes = release_notes.load_release_notes_source(repo_root=root, version=to_version)
    if authored_notes is not None:
        release_body = authored_notes.body or release_body
    highlights = raw_highlights
    if authored_notes is not None and authored_notes.highlights:
        highlights = [str(item).strip() for item in authored_notes.highlights if str(item).strip()][:3]
    summary, detail = _release_spotlight_copy(
        from_version=from_version,
        to_version=to_version,
        release_body=release_body,
        highlights=highlights,
    )
    if authored_notes is not None and authored_notes.summary:
        summary = authored_notes.summary
    if not summary and highlights:
        summary = highlights[0]
    if not detail:
        detail = next((item for item in highlights if item != summary), "")
    highlights = [
        item
        for item in highlights
        if item not in {summary, detail}
    ][:3]
    title = _release_story_title(
        authored_notes=authored_notes,
        release_tag=release_tag,
        to_version=to_version,
    )
    return {
        "show": True,
        "from_version": from_version,
        "to_version": to_version,
        "title": title,
        "release_tag": release_tag,
        "release_url": release_url,
        "release_published_at": (
            authored_notes.published_at
            if authored_notes is not None and authored_notes.published_at
            else release_published_at
        ),
        "release_body": release_body,
        "highlights": highlights,
        "summary": summary,
        "detail": detail,
        "headline": title,
        "notes_url": _release_story_notes_url(
            authored_notes=authored_notes,
            release_tag=release_tag,
            to_version=to_version,
        ),
        "cta_label": _release_story_note_link_label(
            authored_notes=authored_notes,
            title=title,
            release_tag=release_tag,
            to_version=to_version,
        ),
        "external_label": _release_story_external_link_label(
            authored_notes=authored_notes,
            release_url=release_url,
            release_tag=release_tag,
            to_version=to_version,
        ),
        "reopen_label": _release_story_reopen_label(
            authored_notes=authored_notes,
            title=title,
            release_tag=release_tag,
            to_version=to_version,
        ),
    }


def _release_spotlight_expires_utc(payload: dict[str, object]) -> str:
    recorded_at = _parse_iso_utc(payload.get("recorded_utc")) or _parse_iso_utc(payload.get("release_published_at"))
    if recorded_at is None:
        return ""
    return (recorded_at + _UPGRADE_SPOTLIGHT_MAX_AGE).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _release_spotlight_copy(
    *,
    from_version: str,
    to_version: str,
    release_body: str,
    highlights: list[str],
) -> tuple[str, str]:
    paragraphs = _release_note_paragraphs(release_body, limit=2)
    summary = paragraphs[0] if paragraphs else ""
    detail = paragraphs[1] if len(paragraphs) > 1 else ""
    if not summary and highlights:
        summary = highlights[0]
    if not detail:
        detail = next((item for item in highlights if item != summary), "")
    return summary, detail


def _release_note_paragraphs(body: str, *, limit: int) -> list[str]:
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
            normalized = _normalize_release_note_text(line, limit=260)
            if normalized:
                lines.append(normalized)
        paragraph = _normalize_release_note_text(" ".join(lines), limit=260)
        if paragraph and paragraph not in paragraphs:
            paragraphs.append(paragraph)
        if len(paragraphs) >= limit:
            break
    return paragraphs[:limit]
def _has_backlog_ideas(repo_root: Path) -> bool:
    ideas_root = repo_root / "odylith" / "radar" / "source" / "ideas"
    if not ideas_root.is_dir():
        return False
    return any(path.is_file() and path.suffix.lower() == ".md" for path in ideas_root.rglob("*.md"))


def _has_component_specs(repo_root: Path) -> bool:
    components_root = repo_root / "odylith" / "registry" / "source" / "components"
    if not components_root.is_dir():
        return False
    return any(path.is_file() and path.name == "CURRENT_SPEC.md" for path in components_root.rglob("CURRENT_SPEC.md"))


def _has_atlas_diagrams(repo_root: Path) -> bool:
    atlas_root = repo_root / "odylith" / "atlas" / "source"
    if not atlas_root.is_dir():
        return False
    return any(path.is_file() and path.suffix.lower() == ".mmd" for path in atlas_root.rglob("*.mmd"))


def _detect_repo_focus(repo_root: Path) -> _RepoFocus:
    visible_roots = tuple(_visible_top_level_entries(repo_root))
    focus_parts = _choose_focus_parts(repo_root)
    focus_path = "/".join(focus_parts)
    component_seed = next((part for part in reversed(focus_parts) if part.lower() not in _GENERIC_FOCUS_TOKENS), "")
    if not component_seed:
        component_seed = repo_root.name
    component_id = _slugify(component_seed)
    if not component_id:
        component_id = "core"
    return _RepoFocus(
        focus_path=focus_path,
        component_id=component_id,
        component_label=_humanize(component_seed) or _humanize(repo_root.name),
        stack_labels=tuple(label for marker, label in _STACK_MARKERS if (repo_root / marker).exists()),
        visible_roots=visible_roots,
    )


def _visible_top_level_entries(repo_root: Path) -> list[str]:
    entries: list[str] = []
    try:
        for entry in sorted(repo_root.iterdir(), key=lambda path: path.name.lower()):
            name = entry.name.strip()
            if not name or name.startswith(".") or name in _IGNORED_TOP_LEVEL_DIRS:
                continue
            entries.append(f"{name}/" if entry.is_dir() else name)
    except OSError:
        return []
    return entries[:6]


def _choose_focus_parts(repo_root: Path) -> tuple[str, ...]:
    for name in _PRIORITY_DIRS:
        root = repo_root / name
        if not root.is_dir():
            continue
        child = _first_visible_child_dir(root)
        if child and child.name.lower() not in _GENERIC_FOCUS_TOKENS:
            return (name, child.name)
        return (name,)

    try:
        for entry in sorted(repo_root.iterdir(), key=lambda path: path.name.lower()):
            name = entry.name.strip()
            if (
                not entry.is_dir()
                or not name
                or name.startswith(".")
                or name in _IGNORED_TOP_LEVEL_DIRS
            ):
                continue
            child = _first_visible_child_dir(entry)
            if child and child.name.lower() not in _GENERIC_FOCUS_TOKENS:
                return (name, child.name)
            return (name,)
    except OSError:
        return ()
    return ()


def _first_visible_child_dir(root: Path) -> Path | None:
    visible_children = _visible_child_dirs(root)
    return visible_children[0] if visible_children else None


def _visible_child_dirs(root: Path) -> list[Path]:
    children: list[Path] = []
    try:
        for entry in sorted(root.iterdir(), key=lambda path: path.name.lower()):
            name = entry.name.strip()
            if not entry.is_dir() or not name or name.startswith(".") or name in _IGNORED_TOP_LEVEL_DIRS:
                continue
            children.append(entry)
    except OSError:
        return []
    return children[:4]


def _repo_fact_lines(
    *,
    root: Path,
    focus: _RepoFocus,
    grounded_focus: bool,
    missing_backlog: bool,
    missing_component: bool,
    missing_atlas: bool,
) -> list[str]:
    facts: list[str] = []
    if focus.stack_labels:
        facts.append(f"Detected stack markers: {', '.join(focus.stack_labels[:3])}.")
    if grounded_focus and focus.focus_path:
        facts.append(f"Likely first delivery surface: `{focus.focus_path}`.")
    else:
        facts.append("Odylith has not inferred one grounded slice yet; pick the real code path you want to govern first.")
    if focus.visible_roots:
        facts.append(f"Visible repo roots: {', '.join(focus.visible_roots)}.")
    if (root / ".git").exists():
        facts.append("This install is anchored to a Git-backed repository root.")
    if missing_backlog and missing_component and missing_atlas:
        facts.append("Odylith does not have repo-local backlog items, component specs, or Atlas diagrams yet.")
    elif missing_backlog and missing_component:
        facts.append("Odylith does not have any repo-local backlog items or component specs yet.")
    elif missing_backlog:
        facts.append("Odylith still needs its first backlog item in this repo.")
    elif missing_component:
        facts.append("Odylith still needs its first Registry component in this repo.")
    elif missing_atlas:
        facts.append("Odylith still needs its first Atlas diagram set in this repo.")
    return facts[:4]


def _is_grounded_focus(*, root: Path, focus: _RepoFocus) -> bool:
    focus_path = str(focus.focus_path or "").strip()
    if not focus_path:
        return False
    parts = tuple(part for part in focus_path.split("/") if part)
    if not parts:
        return False
    if len(parts) == 1:
        token = parts[0].strip().lower()
        if not token or token == root.name.lower() or token in _GENERIC_FOCUS_TOKENS:
            return False
    return True


def _welcome_notices(*, root: Path) -> list[dict[str, str]]:
    notices: list[dict[str, str]] = []
    if not (root / ".git").exists():
        notices.append(
            {
                "tone": "warning",
                "title": "Git missing",
                "body": (
                    "Odylith installed here, but repo intelligence stays reduced until this folder is backed by Git."
                ),
            }
        )
    legacy_notice = _legacy_consumer_upgrade_notice(root=root)
    if legacy_notice:
        notices.append(legacy_notice)
    return notices


def _legacy_consumer_upgrade_notice(*, root: Path) -> dict[str, str] | None:
    if _looks_like_product_repo(root):
        return None
    active_version = _active_installed_version(root)
    if active_version not in _LEGACY_CONSUMER_UPGRADE_VERSIONS:
        return None
    if _launcher_supports_bootstrap_upgrade(root):
        return None
    pinned_version = _pinned_version(root)
    version_label = active_version
    if pinned_version and pinned_version != active_version:
        version_label = f"{active_version} with repo pin {pinned_version}"
    return {
        "tone": "warning",
        "title": "Legacy upgrade path detected",
        "body": (
            f"This repo is still on the legacy {version_label} launcher path. Rerun the hosted installer once to "
            "rename any remaining legacy `odyssey/` and `.odyssey/` roots into the Odylith layout, then use `./.odylith/bin/odylith upgrade` normally."
        ),
        "code": LATEST_INSTALL_COMMAND,
        "copy_label": "Copy rescue install",
        "copy_status": "Rescue install command copied. Run it from the repo root.",
        "copy_text": LATEST_INSTALL_COMMAND,
    }


def _looks_like_product_repo(root: Path) -> bool:
    return (root / "src" / "odylith").is_dir() and (root / "odylith").is_dir() and (root / "pyproject.toml").is_file()


def _install_state(root: Path) -> dict[str, Any]:
    try:
        state = load_install_state(repo_root=root)
    except Exception:
        return {}
    return state if isinstance(state, dict) else {}


def _active_installed_version(root: Path) -> str:
    return str(_install_state(root).get("active_version") or "").strip()


def _pinned_version(root: Path) -> str:
    pin_path = version_pin_path(repo_root=root)
    if not pin_path.is_file():
        return ""
    try:
        pin = load_version_pin(repo_root=root, fallback_version="")
    except Exception:
        return ""
    return str(pin.odylith_version if pin else "").strip()


def _launcher_supports_bootstrap_upgrade(root: Path) -> bool:
    launcher_path = root / ".odylith" / "bin" / "odylith"
    if not launcher_path.is_file():
        return False
    try:
        launcher_text = launcher_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return _LAUNCHER_BOOTSTRAP_MARKER in launcher_text


def _first_use_suggestions(
    *,
    focus: _RepoFocus,
    missing_backlog: bool,
    missing_component: bool,
    missing_atlas: bool,
) -> list[str]:
    focus_path = focus.focus_path or "the main product surface"
    component_id = focus.component_id or "core"
    suggestions = [
        f"Ask the agent to map `{focus_path}` and explain which Odylith surfaces matter first in this repository.",
        (
            f"Ask the agent to draft the first Radar backlog item around `{focus_path}` so Odylith starts from one real code path here."
            if missing_backlog
            else f"Ask the agent to review the current backlog and sharpen the next high-leverage path around `{focus_path}`."
        ),
        (
            f"Ask the agent to draft the first Registry components around `{focus_path}` starting with `{component_id}` so code ownership becomes explicit early."
            if missing_component
            else f"Ask the agent to expand component coverage around `{focus_path}` and tighten the next boundary that should be tracked."
        ),
        (
            f"Ask the agent to suggest the first Atlas diagrams for `{focus_path}` and show how Radar, Registry, Atlas, Casebook, and Compass should work together here."
            if missing_atlas
            else "Ask the agent to review the current diagrams and show how to move cleanly across all five Odylith surfaces."
        ),
    ]
    return suggestions


def _component_suggestions(*, component_targets: list[tuple[str, str, str]]) -> list[str]:
    suggestions: list[str] = []
    for component_id, label, focus_path in component_targets[:3]:
        owned_path = focus_path or "the highest-leverage code path in this repo"
        suggestions.append(
            f"Create component `{component_id}` in `odylith/registry/source/components/{component_id}/CURRENT_SPEC.md` to own `{owned_path}` as a named boundary for {label}."
        )
    return suggestions


def _atlas_diagram_suggestions(
    *,
    root: Path,
    focus: _RepoFocus,
    component_targets: list[tuple[str, str, str]],
) -> list[str]:
    focus_path = focus.focus_path or "the main product surface"
    primary_component_id, primary_label, _ = (
        component_targets[0]
        if component_targets
        else (focus.component_id or "core", focus.component_label or "Core", focus_path)
    )
    repo_slug = _slugify(root.name) or "repo"
    candidate_labels = [label for _, label, _ in component_targets[:3]]
    suggestions = [
        f"Add `odylith/atlas/source/{primary_component_id}-boundary-map.mmd` to map the `{focus_path}` boundary, neighbors, and ownership edges around {primary_label}.",
        f"Add `odylith/atlas/source/{primary_component_id}-execution-flow.mmd` to show how execution moves through `{focus_path}` from entrypoint to side effects.",
    ]
    if len(candidate_labels) >= 2:
        suggestions.append(
            f"Add `odylith/atlas/source/{repo_slug}-component-interaction-map.mmd` to connect {', '.join(candidate_labels[:3])} and keep Atlas aligned with Registry."
        )
    else:
        suggestions.append(
            f"Add `odylith/atlas/source/{repo_slug}-governance-loop.mmd` to show how the first backlog item, first components, first defects, and Compass history should reinforce each other."
        )
    return suggestions[:3]


def _surface_flow(*, focus: _RepoFocus) -> list[str]:
    focus_path = focus.focus_path or "the main product surface"
    component_id = focus.component_id or "core"
    return [
        f"Radar: create one backlog item for `{focus_path}` so the repo starts from one clear outcome instead of a broad repo map.",
        f"Registry: define components such as `{component_id}` before implementation spreads so ownership stays explicit in the code paths that matter.",
        f"Atlas: diagram the boundaries and runtime flow for `{focus_path}` so the agent can see topology instead of re-deriving it from scratch.",
        "Casebook: capture real bugs or regressions there as they appear so defects become durable repo truth instead of disappearing into chat scrollback.",
        "Compass: review what the agent actually executed, then feed the learnings back into Radar, Registry, Atlas, and Casebook to tighten the next loop.",
    ]


def _surface_explainers(*, focus_path: str, component_label: str) -> list[dict[str, str]]:
    return [
        {
            "surface": "Radar",
            "sentence": "Radar keeps a clear backlog so the repo always has one governed next step.",
        },
        {
            "surface": "Registry",
            "sentence": "Registry is the component ledger for boundaries, ownership, and contracts.",
        },
        {
            "surface": "Atlas",
            "sentence": "Atlas keeps architecture visible with diagrams of topology and flow.",
        },
        {
            "surface": "Compass",
            "sentence": "Compass keeps briefs and timelines so the next move stays clear.",
        },
    ]


def _quick_steps(
    *,
    focus_path: str,
    component_label: str,
    missing_backlog: bool,
    missing_component: bool,
    missing_atlas: bool,
) -> list[str]:
    surfaces: list[str] = []
    if missing_backlog:
        surfaces.append("Radar")
    if missing_component:
        surfaces.append("Registry")
    if missing_atlas:
        surfaces.append("Atlas")
    if not focus_path and not component_label:
        return [
            "Copy the starter prompt.",
            "Paste it into Codex or Claude Code.",
            "Try commands in the cheatsheet.",
        ]
    if not surfaces:
        surface_list = "Odylith"
    elif len(surfaces) == 1:
        surface_list = surfaces[0]
    elif len(surfaces) == 2:
        surface_list = f"{surfaces[0]} and {surfaces[1]}"
    else:
        surface_list = f"{surfaces[0]}, {surfaces[1]}, and {surfaces[2]}"
    return [
        "Copy the starter prompt.",
        "Paste it into Codex or Claude Code.",
        f"Let Odylith set up {surface_list}.",
    ]


def _surface_handoff(*, focus_path: str, component_label: str) -> list[str]:
    slice_label = focus_path or "the first code path you choose"
    boundary_label = component_label or "the first named boundary you define"
    return [
        f"Radar starts with `{slice_label}`.",
        f"Registry names the boundary around {boundary_label}.",
        f"Atlas makes `{slice_label}` visible before the repo gets busy.",
    ]


def _chosen_slice(
    *,
    root: Path,
    focus: _RepoFocus,
    focus_path: str,
    component_id: str,
    component_label: str,
) -> dict[str, Any]:
    if not focus_path:
        return {
            "title": "No starting path yet",
            "reason": (
                "Odylith cannot recommend a code path yet because this repo does not expose one real code area."
            ),
            "guidance": [
                "Create one real code folder first for the app, service, or package you actually plan to build.",
                "Then reopen setup and Odylith will recommend a grounded starting area automatically.",
            ],
        }
    return {
        "title": "Example starting path",
        "path": focus_path,
        "reason": (
            f"Use `{focus_path}` as the example. Odylith can already ground it from the current repo structure."
            if focus_path
            else "Odylith can ground one concrete code path immediately instead of spreading across the whole repo."
        ),
        "guidance": [
            "Start small with one real path instead of trying to map the whole repo.",
            "Odylith will use this same example to seed Radar, Registry, and Atlas.",
        ],
    }


def _guard_seam_label(*, root: Path, focus: _RepoFocus) -> str:
    focus_parts = tuple(part for part in str(focus.focus_path or "").split("/") if part)
    if len(focus_parts) >= 2:
        parent = root.joinpath(*focus_parts[:-1])
        current_name = focus_parts[-1]
        siblings = [child.name for child in _visible_child_dirs(parent) if child.name != current_name]
        if siblings:
            sibling_path = "/".join((*focus_parts[:-1], siblings[0]))
            return f"`{focus.focus_path}` <-> `{sibling_path}`"
    if focus_parts:
        current_root = focus_parts[0]
        sibling_root = next(
            (token.rstrip("/") for token in focus.visible_roots if token.rstrip("/") != current_root),
            "",
        )
        if sibling_root:
            return f"`{focus.focus_path}` <-> `{sibling_root}`"
        return f"`{focus.focus_path}` entrypoints <-> side effects"
    return "entrypoints <-> side effects"


def _first_tasks(
    *,
    focus_path: str,
    component_id: str,
    component_label: str,
) -> list[dict[str, Any]]:
    return [
        {
            "id": "backlog",
            "title": "Backlog",
            "summary": f"Open the first Radar item for `{focus_path}`.",
            "prompts": [
                {"label": "Create", "text": f"Open the Radar item for `{focus_path}`."},
                {"label": "Edit", "text": f"Tighten the Radar item for `{focus_path}`."},
                {"label": "Delete", "text": f"Drop the Radar item if `{focus_path}` is the wrong starting area."},
            ],
            "actions": [{"label": "Open Radar", "tab": "radar"}],
        },
        {
            "id": "components",
            "title": "Components",
            "summary": f"Define the first Registry boundary for `{component_label}`.",
            "prompts": [
                {"label": "Create", "text": f"Define the Registry component for `{component_label}`."},
                {"label": "Edit", "text": f"Tighten the Registry boundary for `{component_label}`."},
                {"label": "Delete", "text": f"Drop the Registry component if `{component_label}` is the wrong starting boundary."},
            ],
            "actions": [{"label": "Open Registry", "tab": "registry"}],
        },
        {
            "id": "diagrams",
            "title": "Diagrams",
            "summary": f"Draw the first Atlas view for `{focus_path}`.",
            "prompts": [
                {"label": "Create", "text": f"Draw the Atlas diagram for `{focus_path}`."},
                {"label": "Edit", "text": f"Update the Atlas diagram for `{focus_path}`."},
                {"label": "Delete", "text": f"Drop the Atlas diagram if `{focus_path}` is no longer the right starting area."},
            ],
            "actions": [{"label": "Open Atlas", "tab": "atlas"}],
        },
    ]


def _candidate_component_targets(*, root: Path, focus: _RepoFocus) -> list[tuple[str, str, str]]:
    candidates: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    def add_candidate(*, source_path: str, seed: str, label: str) -> None:
        component_id = _slugify(seed)
        if not component_id or component_id in seen:
            return
        seen.add(component_id)
        candidates.append((component_id, label or _humanize(component_id), source_path))

    if focus.component_id:
        add_candidate(source_path=focus.focus_path, seed=focus.component_id, label=focus.component_label)

    for path_parts in _candidate_focus_paths(root):
        source_path = "/".join(path_parts)
        seed = next((part for part in reversed(path_parts) if part.lower() not in _GENERIC_FOCUS_TOKENS), path_parts[-1])
        add_candidate(source_path=source_path, seed=seed, label=_humanize(seed))
        if len(candidates) >= 3:
            break

    if not candidates:
        repo_component = _slugify(root.name) or "core"
        add_candidate(source_path=root.name, seed=repo_component, label=_humanize(repo_component))
    return candidates[:3]


def _candidate_focus_paths(repo_root: Path) -> list[tuple[str, ...]]:
    candidates: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()

    def add_path(parts: tuple[str, ...]) -> None:
        normalized = tuple(str(part).strip() for part in parts if str(part).strip())
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        candidates.append(normalized)

    for name in _PRIORITY_DIRS:
        root = repo_root / name
        if not root.is_dir():
            continue
        visible_children = _visible_child_dirs(root)
        if visible_children:
            for child in visible_children[:2]:
                if child.name.lower() in _GENERIC_FOCUS_TOKENS:
                    continue
                add_path((name, child.name))
        else:
            add_path((name,))
        if len(candidates) >= 4:
            return candidates[:4]

    try:
        for entry in sorted(repo_root.iterdir(), key=lambda path: path.name.lower()):
            name = entry.name.strip()
            if not entry.is_dir() or not name or name.startswith(".") or name in _IGNORED_TOP_LEVEL_DIRS:
                continue
            visible_children = _visible_child_dirs(entry)
            if visible_children:
                for child in visible_children[:2]:
                    if child.name.lower() in _GENERIC_FOCUS_TOKENS:
                        continue
                    add_path((name, child.name))
            else:
                add_path((name,))
            if len(candidates) >= 4:
                break
    except OSError:
        return candidates[:4]
    return candidates[:4]


def _slugify(value: str) -> str:
    lowered = "".join(char.lower() if char.isalnum() else "-" for char in str(value or "").strip())
    while "--" in lowered:
        lowered = lowered.replace("--", "-")
    return lowered.strip("-")


def _humanize(value: str) -> str:
    token = str(value or "").strip().replace("-", " ").replace("_", " ")
    words = [word for word in token.split() if word]
    return " ".join(word[:1].upper() + word[1:] for word in words)
