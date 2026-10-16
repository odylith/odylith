"""Authoritative active-generation state for Greenfield publication."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

from odylith.install.fs import atomic_write_text
from odylith.install.fs import fsync_directory


ACTIVE = "active"
NONE = "none"
PUBLICATION_ENTRY_VERSION = "odylith.greenfield.publication-entry.v1"
_ENTRY_PREFIX = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Odylith project</title>
<style>body{margin:0;padding:8vh 24px;background:#f3f9fc;color:#152c42;font:17px/1.6 system-ui,sans-serif}main{max-width:42rem;margin:auto;padding:32px;border:1px solid #cfdeea;border-radius:16px;background:white}h1{font-size:1.8rem;line-height:1.3}p{overflow-wrap:anywhere}button{font:inherit;padding:8px 18px;border:1px solid #a7bdd0;border-radius:8px;background:#f3f9fc;color:inherit;cursor:pointer}</style>
</head><body><main><small>ODYLITH</small><h1 id="heading">Opening your project</h1>
<p id="status" role="status">Loading the complete published view.</p>
<button type="button" onclick="location.reload()">Reload</button>
<noscript><p>Enable JavaScript to open the published dashboard. No partial project is shown.</p></noscript>
</main><script id="odylith-publication" type="application/json">'''
_ENTRY_SUFFIX = '''</script><script>
(async () => {
  try {
    let source = document;
    if (location.protocol === 'http:' || location.protocol === 'https:') {
      const response = await fetch(location.href, {cache: 'no-store', redirect: 'error'});
      if (!response.ok) throw new Error('Publication unavailable');
      source = new DOMParser().parseFromString(await response.text(), 'text/html');
    } else if (location.protocol !== 'file:') {
      throw new Error('Unsupported project location');
    }
    const records = source.querySelectorAll('script#odylith-publication[type="application/json"]');
    if (records.length !== 1) throw new Error('Publication unavailable');
    const raw = records[0].textContent;
    const record = JSON.parse(raw);
    const digest = value => typeof value === 'string' && value.length === 64 &&
      [...value].every(character => '0123456789abcdef'.includes(character));
    if (record.version !== 'odylith.greenfield.publication-entry.v1' ||
        !digest(record.write_set_hash) || !digest(record.generation_manifest_sha256) ||
        raw !== JSON.stringify({generation_manifest_sha256: record.generation_manifest_sha256,
          version: record.version, write_set_hash: record.write_set_hash})) {
      throw new Error('Publication unavailable');
    }
    const target = new URL('../.odylith/runtime/greenfield/generations/' +
      record.write_set_hash + '/repository/odylith/index.html', location.href);
    target.search = location.search;
    target.hash = location.hash;
    location.replace(target.href);
  } catch (error) {
    document.getElementById('heading').textContent = 'Project unavailable';
    document.getElementById('status').textContent =
      'The published view could not be opened. No partial project is shown. Reload after recovery.';
  }
})();
</script></body></html>
'''


def compile_greenfield_publication_entry(*, write_set_hash: str, generation_manifest_sha256: str) -> str:
    """Compile the browser entry after W and M, before the enclosing transaction T."""

    record = {
        "version": PUBLICATION_ENTRY_VERSION,
        "write_set_hash": _require_digest(write_set_hash, label="write-set hash"),
        "generation_manifest_sha256": _require_digest(generation_manifest_sha256, label="manifest hash"),
    }
    return _ENTRY_PREFIX + json.dumps(record, sort_keys=True, separators=(",", ":")) + _ENTRY_SUFFIX


def require_sealed_greenfield_publication_entry(
    text: str, *, write_set_hash: str, generation_manifest_sha256: str,
) -> dict[str, str]:
    """Validate exact sealed entry bytes without rendering or compiling an entry."""

    if not isinstance(text, str) or not text.startswith(_ENTRY_PREFIX) or not text.endswith(_ENTRY_SUFFIX):
        raise ValueError("Greenfield sealed publication entry has an invalid envelope")
    raw = text[len(_ENTRY_PREFIX):-len(_ENTRY_SUFFIX)]
    try:
        record = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Greenfield sealed publication entry is unreadable") from exc
    expected = {
        "version": PUBLICATION_ENTRY_VERSION,
        "write_set_hash": _require_digest(write_set_hash, label="publication write-set hash"),
        "generation_manifest_sha256": _require_digest(generation_manifest_sha256, label="publication manifest hash"),
    }
    if record != expected or raw != json.dumps(expected, sort_keys=True, separators=(",", ":")):
        raise ValueError("Greenfield sealed publication entry differs from its reviewed identity")
    return {
        "write_set_hash": expected["write_set_hash"],
        "generation_manifest_sha256": expected["generation_manifest_sha256"],
        "publication_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def read_active_publication(repo_root: Path) -> dict[str, str] | None:
    """Read the sole browser entry, never the working shell or a JSON pointer.

    Ordinary shells are unactivated repositories, not atomic current views.
    A retained working shell makes a missing or replaced entry an error.
    """

    root = Path(repo_root).expanduser().resolve()
    path = root / "odylith/index.html"
    legacy = root / ".odylith/runtime/greenfield/active-generation.v1.json"
    if legacy.exists() or legacy.is_symlink():
        raise RuntimeError("Greenfield JSON publication state requires explicit migration; existing evidence is preserved")
    for candidate in (path, path.parent):
        if candidate.is_symlink():
            raise RuntimeError("Greenfield publication entry crosses an unsafe symlink")
    working = root / "odylith/tooling-shell.html"
    protected = working.exists() or working.is_symlink()
    if not path.exists():
        if protected:
            raise RuntimeError("Greenfield publication entry is missing; recovery is required")
        return None
    if not path.is_file():
        raise RuntimeError("Greenfield publication entry is not a file")
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError("Greenfield publication entry is unreadable") from exc
    if "odylith-publication" not in text:
        if protected:
            raise RuntimeError("Greenfield publication entry was replaced; recovery is required")
        return None
    return _publication_identity_from_text(text)


def _publication_identity_from_text(text: str) -> dict[str, str]:
    if not isinstance(text, str) or not text.startswith(_ENTRY_PREFIX) or not text.endswith(_ENTRY_SUFFIX):
        raise ValueError("Greenfield publication entry has an invalid envelope")
    try:
        record = json.loads(text[len(_ENTRY_PREFIX):-len(_ENTRY_SUFFIX)])
    except json.JSONDecodeError as exc:
        raise ValueError("Greenfield publication entry is unreadable") from exc
    if not isinstance(record, Mapping):
        raise ValueError("Greenfield publication entry must be an object")
    return require_sealed_greenfield_publication_entry(
        text,
        write_set_hash=record.get("write_set_hash"),
        generation_manifest_sha256=record.get("generation_manifest_sha256"),
    )


def no_active_generation_identity() -> dict[str, str]:
    return {
        "status": NONE,
        "write_set_hash": "",
        "generation_manifest_sha256": "",
        "publication_sha256": "",
    }


def active_generation_identity(repo_root: Path) -> dict[str, str]:
    state = read_active_publication(repo_root)
    return {"status": ACTIVE, **state} if state is not None else no_active_generation_identity()


def active_publication_matches(
    *, repo_root: Path, expected_publication: Mapping[str, str],
) -> bool:
    """Compare artifacts only; the admitted transaction journal owns approval."""

    expected = require_active_generation_identity({"status": ACTIVE, **expected_publication})
    return active_generation_identity(repo_root) == expected


def publish_sealed_publication(
    *,
    repo_root: Path,
    expected_identity: Mapping[str, Any],
    sealed_entry_text: str,
) -> dict[str, str]:
    root = Path(repo_root).expanduser().resolve()
    expected = require_active_generation_identity(expected_identity)
    actual = active_generation_identity(root)
    if actual != expected:
        raise ValueError("Greenfield active generation changed after pre-confirm compilation")
    state = _publication_identity_from_text(sealed_entry_text)
    if {"status": ACTIVE, **state} == actual:
        raise ValueError("Greenfield publication must be a fresh predecessor-bound transition")
    path = root / "odylith/index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    fsync_directory(path.parent)
    atomic_write_text(path, sealed_entry_text)
    fsync_directory(path.parent)
    return state


def require_active_generation_identity(value: Mapping[str, Any] | object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("ProductCreateTransaction active-generation precondition is missing")
    if set(value) != set(no_active_generation_identity()):
        raise ValueError("ProductCreateTransaction publication precondition fields are invalid")
    identity = dict(value)
    if identity["status"] == NONE:
        if identity != no_active_generation_identity():
            raise ValueError("ProductCreateTransaction empty active-generation precondition is invalid")
        return identity
    if identity["status"] != ACTIVE:
        raise ValueError("ProductCreateTransaction active-generation precondition has an invalid status")
    for key in ("publication_sha256", "write_set_hash", "generation_manifest_sha256"):
        _require_digest(identity[key], label=key.replace("_", " "))
    return identity


def _require_digest(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"Greenfield {label} must be a SHA-256 value")
    return value


__all__ = [
    "ACTIVE",
    "NONE",
    "active_generation_identity",
    "active_publication_matches",
    "compile_greenfield_publication_entry",
    "no_active_generation_identity",
    "publish_sealed_publication",
    "read_active_publication",
    "require_active_generation_identity",
    "require_sealed_greenfield_publication_entry",
]
