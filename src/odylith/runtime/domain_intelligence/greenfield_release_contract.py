"""Parser-free constants shared by Greenfield release paths."""

from collections.abc import Mapping


DEFAULT_GREENFIELD_RELEASE_SELECTOR = "0.0.1"
_MAX_RELEASE_TARGET_LABEL_CHARS = 18


def release_assignment_note(*, selector: str) -> str:
    """Return the stable operator note shared by pre-confirm release paths."""

    return f"Target confirmed first-release greenfield workstream(s) for release `{selector}`."


def semantic_release_metadata(
    *, selector: str, release_plan: Mapping[str, object]
) -> tuple[str, str]:
    """Return exact v7 version metadata without searching arbitrary prose."""

    selector_token = _semver_token(selector)
    version_token = _semver_token(str(release_plan.get("version") or ""))
    version = version_token or selector_token
    tag = str(release_plan.get("tag") or "").strip()
    return version, tag or (f"v{version}" if version else "")


def semantic_release_label(value: str) -> str:
    """Return a bounded release label from an already typed selector."""

    token = str(value or "").strip()
    version = _semver_token(token)
    if version:
        return version
    label = token or DEFAULT_GREENFIELD_RELEASE_SELECTOR
    return label if len(label) <= _MAX_RELEASE_TARGET_LABEL_CHARS else label[:15].rstrip() + "..."


def _semver_token(value: str) -> str:
    token = str(value or "").strip()
    candidate = token[1:] if token.startswith("v") else token
    core = candidate.split("+", 1)[0].split("-", 1)[0]
    parts = core.split(".")
    if len(parts) != 3 or any(not part.isdecimal() for part in parts):
        return ""
    suffix = candidate[len(core):]
    if suffix and any(not (char.isalnum() or char in ".+-") for char in suffix):
        return ""
    return candidate


__all__ = [
    "DEFAULT_GREENFIELD_RELEASE_SELECTOR",
    "release_assignment_note",
    "semantic_release_label",
    "semantic_release_metadata",
]
