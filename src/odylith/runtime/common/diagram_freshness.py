"""Content-fingerprint helpers for Atlas diagram freshness and render invalidation."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Callable, Sequence

_READ_CHUNK_SIZE = 64 * 1024
_IGNORED_DIRECTORY_FINGERPRINT_PARTS = frozenset({"__pycache__"})
_IGNORED_DIRECTORY_FINGERPRINT_SUFFIXES = frozenset({".pyc", ".pyo"})
_MERMAID_RENDER_STYLE_VERSION = "atlas-semantic-color-v4"
_MERMAID_RENDER_CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "surfaces" / "assets" / "mermaid_render_config.json"
)
_MERMAID_RENDER_WORKER_PATH = (
    Path(__file__).resolve().parents[1] / "surfaces" / "assets" / "mermaid_cli_worker.mjs"
)


def normalize_mermaid_render_source(definition: str) -> str:
    """Return a render-semantic Mermaid source string.

    Mermaid review comments (`%% ...`) and trailing whitespace should not force
    a full SVG/PNG rebuild when the rendered topology is otherwise unchanged.
    """

    lines: list[str] = []
    for raw_line in str(definition or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = raw_line.lstrip()
        if stripped.startswith("%%"):
            continue
        lines.append(raw_line.rstrip())
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


class ContentFingerprintCache:
    """In-process cache for repeat content fingerprints during one Atlas run."""

    __slots__ = ("_mermaid_cache", "_path_cache")

    def __init__(self) -> None:
        self._path_cache: dict[str, str] = {}
        self._mermaid_cache: dict[str, str] = {}

    def path_fingerprint(self, path: Path) -> str:
        target = Path(path).resolve()
        cache_key = str(target)
        cached = self._path_cache.get(cache_key)
        if cached is not None:
            return cached
        digest = self._compute_path_fingerprint(target)
        self._path_cache[cache_key] = digest
        return digest

    def mermaid_render_fingerprint(self, path: Path) -> str:
        target = Path(path).resolve()
        cache_key = str(target)
        cached = self._mermaid_cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            definition = target.read_text(encoding="utf-8")
        except OSError:
            digest = hashlib.sha256(f"missing-mermaid\0{target}".encode("utf-8")).hexdigest()
        else:
            normalized = normalize_mermaid_render_source(definition)
            digest = hashlib.sha256(
                (
                    f"source\0{normalized}"
                    f"\0render-style\0{_MERMAID_RENDER_STYLE_VERSION}"
                    f"\0render-config\0{mermaid_render_style_fingerprint()}"
                ).encode("utf-8")
            ).hexdigest()
        self._mermaid_cache[cache_key] = digest
        return digest

    def _compute_path_fingerprint(self, target: Path) -> str:
        hasher = hashlib.sha256()
        if not target.exists():
            hasher.update(f"missing\0{target}".encode("utf-8"))
            return hasher.hexdigest()
        if target.is_file():
            hasher.update(b"file\0")
            hasher.update(target.name.encode("utf-8"))
            hasher.update(b"\0")
            self._update_file_bytes(hasher, target)
            return hasher.hexdigest()
        if not target.is_dir():
            hasher.update(f"other\0{target}".encode("utf-8"))
            return hasher.hexdigest()

        hasher.update(b"dir\0")
        hasher.update(target.name.encode("utf-8"))
        hasher.update(b"\0")
        try:
            nodes = sorted(target.rglob("*"))
        except OSError:
            hasher.update(f"unreadable\0{target}".encode("utf-8"))
            return hasher.hexdigest()
        for node in nodes:
            try:
                rel = node.relative_to(target).as_posix()
            except ValueError:
                rel = str(node)
            if _path_ignored_for_directory_fingerprint(node=node, relative_path=rel):
                continue
            if node.is_dir():
                hasher.update(f"dir\0{rel}\0".encode("utf-8"))
                continue
            if node.is_file():
                hasher.update(f"file\0{rel}\0".encode("utf-8"))
                self._update_file_bytes(hasher, node)
                continue
            hasher.update(f"other\0{rel}\0".encode("utf-8"))
        return hasher.hexdigest()

    @staticmethod
    def _update_file_bytes(hasher: hashlib._Hash, target: Path) -> None:
        try:
            with target.open("rb") as handle:
                while True:
                    chunk = handle.read(_READ_CHUNK_SIZE)
                    if not chunk:
                        break
                    hasher.update(chunk)
        except OSError:
            hasher.update(f"unreadable\0{target}".encode("utf-8"))


def _path_ignored_for_directory_fingerprint(*, node: Path, relative_path: str) -> bool:
    rel = PurePosixPath(relative_path)
    if any(part in _IGNORED_DIRECTORY_FINGERPRINT_PARTS for part in rel.parts):
        return True
    if node.is_file() and rel.suffix in _IGNORED_DIRECTORY_FINGERPRINT_SUFFIXES:
        return True
    return False


def mermaid_render_style_fingerprint() -> str:
    hasher = hashlib.sha256()
    hasher.update(_MERMAID_RENDER_STYLE_VERSION.encode("utf-8"))
    for path in (_MERMAID_RENDER_CONFIG_PATH, _MERMAID_RENDER_WORKER_PATH):
        hasher.update(b"\0")
        hasher.update(path.name.encode("utf-8"))
        hasher.update(b"\0")
        try:
            hasher.update(path.read_bytes())
        except OSError:
            hasher.update(f"missing\0{path}".encode("utf-8"))
    return hasher.hexdigest()


def watched_path_fingerprints(
    *,
    repo_root: Path,
    watched_paths: Sequence[str],
    resolve_path: Callable[[str], Path] | None = None,
    cache: ContentFingerprintCache | None = None,
) -> dict[str, str]:
    helper = cache or ContentFingerprintCache()
    fingerprints: dict[str, str] = {}
    for raw in watched_paths:
        token = PurePosixPath(str(raw or "").strip()).as_posix()
        if not token or token in fingerprints:
            continue
        target = resolve_path(token) if resolve_path is not None else (Path(repo_root).resolve() / token).resolve()
        fingerprints[token] = helper.path_fingerprint(target)
    return fingerprints


__all__ = [
    "ContentFingerprintCache",
    "mermaid_render_style_fingerprint",
    "normalize_mermaid_render_source",
    "watched_path_fingerprints",
]
