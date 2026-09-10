"""Admit explicit authored selective-sync inputs, never unexplained dirty truth.

The invocation authorizes the selected current bytes, not a historical edit
provenance claim. The ordinary repository write-set owner proves that every
other managed byte still matches the immutable publication.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import stat
from typing import Any, Mapping, Sequence

from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_sets
from odylith.runtime.governance import sync_argument_contract
from odylith.runtime.governance import sync_casebook_bug_index as casebook


_CASEBOOK_METADATA = frozenset(name.casefold() for name in (
    "Bug ID", "Created", "Title", "Status", "Severity", "Type", "Fixed",
    "Reproducibility", "Components Affected", "Ownership", "GitHub Issue(s)",
    "GitHub Status", "Fixed In", "Public Response",
))
_REGISTRY = "odylith/registry/source/component_registry.v1.json"
_ATLAS = "odylith/atlas/source/catalog/diagrams.v1.json"


def _refuse(reason: str) -> generations.GreenfieldWorkingGenerationDriftError:
    return generations.GreenfieldWorkingGenerationDriftError(
        "RECOVERY_REQUIRED: authored selective sync refused: " + reason
        + "; this admission did not publish a successor"
    )


@dataclass(frozen=True)
class AuthoredSyncAdmission:
    """Exact invocation intent bound to an already validated published base."""

    pinned: generations.PinnedGreenfieldGeneration
    active: Mapping[str, str]
    selected: Mapping[str, tuple[bytes, int]]

    def require_unchanged_intent(self, root: Path) -> None:
        if publication.active_generation_identity(root) != self.active:
            raise _refuse("the published base changed during sync")
        for token, expected in self.selected.items():
            if _regular_file(root, token) != expected:
                raise _refuse(f"selected authored bytes or mode changed during sync: {token}")

    def require_compiled_intent(self, write_set: Mapping[str, Any]) -> None:
        if (write_set["before_fingerprints"] != self.pinned.manifest["after_fingerprints"]
                or write_set["active_generation_precondition"] != self.active):
            raise _refuse("the successor is not bound to the admitted published base")
        files = {row["path"]: row for row in write_set["after_image"]["files"]}
        for token, (data, mode) in self.selected.items():
            row = files.get(token)
            if row is None or (row["sha256"], row["mode"]) != (hashlib.sha256(data).hexdigest(), mode):
                raise _refuse(f"the successor changed selected authored intent: {token}")


def _explicit_paths(command_tokens: Sequence[str], *, repo_root: Path) -> tuple[str, ...]:
    if not command_tokens or command_tokens[0] != "sync":
        raise _refuse("only explicit selective sync can admit authored edits")
    parser = sync_argument_contract.configure_sync_parser(
        argparse.ArgumentParser(add_help=False, exit_on_error=False),
    )
    parser.set_defaults(repo_root=None)
    try:
        args, unknown = parser.parse_known_args(list(command_tokens[1:]))
    except (argparse.ArgumentError, SystemExit) as exc:
        raise _refuse("invalid sync arguments") from exc
    if (unknown or args.impact_mode != "selective" or args.force or args.check_only
            or args.dry_run or not args.changed_paths):
        raise _refuse("explicit write-mode selective paths are required, without force")
    if args.repo_root is not None and Path(args.repo_root).expanduser().resolve() != repo_root:
        raise _refuse("the sync target differs from the locked repository")
    paths: list[str] = []
    for raw in args.changed_paths:
        token = raw[2:] if raw.startswith("./") else raw
        path = Path(token)
        if (not token or path.is_absolute() or "\\" in token
                or any(part in {".", ".."} or part.startswith(".") for part in path.parts)
                or path.as_posix() != token):
            raise _refuse(f"an exact repository-relative file is required: {raw}")
        if token not in paths:
            paths.append(token)
    return tuple(paths)


def _regular_file(root: Path, token: str) -> tuple[bytes, int]:
    path = root
    for part in Path(token).parts:
        path = path / part
        if path.is_symlink():
            raise _refuse(f"selected authored path contains a symlink: {token}")
    try:
        mode = path.stat().st_mode
        if not stat.S_ISREG(mode):
            raise _refuse(f"selected authored path is not a regular file: {token}")
        return path.read_bytes(), stat.S_IMODE(mode)
    except OSError as exc:
        raise _refuse(f"selected authored file is unavailable: {token}") from exc


def _casebook_metadata(text: str) -> dict[str, str]:
    fixed: dict[str, str] = {}
    for key, value, raw in casebook.parse_bug_field_blocks(text):
        key = key.casefold()
        if key not in _CASEBOOK_METADATA:
            continue
        if key in fixed:
            raise _refuse(f"ambiguous duplicate Casebook metadata: {key}")
        if key == "bug id" and not casebook._EXPLICIT_CASEBOOK_BUG_ID_RE.fullmatch(
            casebook.normalize_casebook_bug_id(value),
        ):
            raise _refuse("Casebook admission requires a valid existing explicit Bug ID")
        fixed[key] = raw
    if "bug id" not in fixed:
        raise _refuse("Casebook admission requires an existing explicit Bug ID")
    return fixed


def _require_casebook(root: Path, token: str, before: str, after: str) -> None:
    from odylith.runtime.governance import casebook_source_validation

    if _casebook_metadata(before) != _casebook_metadata(after):
        raise _refuse(f"CLI-owned Casebook metadata changed: {token}")
    if casebook._render_bug_text_with_compact_metadata_defaults(text=after) != after:
        raise _refuse(f"selected Casebook source requires metadata normalization: {token}")
    issues = casebook_source_validation._validate_casebook_bug_file(root / token)
    if issues:
        raise _refuse(f"selected Casebook source is invalid: {token}: {issues[0].message}")


def _require_plan(token: str, before: str, after: str) -> None:
    from odylith.runtime.governance import normalize_plan_risk_mitigation as risks
    from odylith.runtime.governance import reconcile_plan_workstream_binding as plans

    if plans.plan_metadata_preamble(before) != plans.plan_metadata_preamble(after):
        raise _refuse(f"CLI-owned plan preamble changed: {token}")
    if risks.normalize_risk_mitigation_markdown(after) != after:
        raise _refuse(f"selected plan body requires risk/mitigation normalization: {token}")


def _require_mapping(root: Path, manifest: str, collection: str, field: str, token: str) -> None:
    try:
        rows = json.loads((root / manifest).read_text(encoding="utf-8"))[collection]
        matches = [row for row in rows if row.get(field) == token]
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise _refuse(f"published authoring ownership is unavailable: {manifest}") from exc
    if len(matches) != 1:
        raise _refuse(f"selected source lacks one exact published ownership mapping: {token}")


def _requirements_region(text: str) -> str:
    from odylith.runtime.governance import sync_component_spec_requirements as requirements

    lines = text.splitlines(keepends=True)
    bounds = requirements._find_h2_section(lines, requirements._SECTION_TITLE)
    starts = [i for i, line in enumerate(lines) if line.strip() == requirements._START_MARKER]
    ends = [i for i, line in enumerate(lines) if line.strip() == requirements._END_MARKER]
    if bounds is None:
        if starts or ends:
            raise _refuse("requirements markers have no owning section")
        return ""
    start, end = bounds
    if requirements._find_h2_section(lines[end:], requirements._SECTION_TITLE) is not None:
        raise _refuse("ambiguous duplicate Requirements Trace section")
    if not starts and not ends:
        # The normalizer owns the whole pre-marker section when no block exists.
        return "".join(lines[start - 1:end])
    if len(starts) != 1 or len(ends) != 1 or not start <= starts[0] < ends[0] < end:
        raise _refuse("ambiguous generated requirements markers")
    # Surrounding manual spec content, including Last updated and the manual
    # tail after the generated block, remains authored under CLI_FIRST_POLICY.
    return "".join(lines[start - 1:ends[0] + 1])


def _require_authored_surface(root: Path, published: Path, token: str, before: bytes, after: bytes) -> None:
    try:
        old_text, new_text = before.decode("utf-8"), after.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _refuse(f"selected authored source is not UTF-8: {token}") from exc
    path = Path(token)
    if path.name in {"INDEX.md", "AGENTS.md", "CLAUDE.md"}:
        raise _refuse(f"selected path is not an admitted authored record: {token}")
    if token.startswith("odylith/casebook/bugs/") and path.suffix == ".md":
        _require_casebook(root, token, old_text, new_text)
    elif (any(token.startswith(f"odylith/technical-plans/{folder}/") for folder in ("in-progress", "done", "parked"))
            and path.suffix == ".md"):
        _require_plan(token, old_text, new_text)
    elif token.startswith("odylith/registry/source/components/") and path.name == "CURRENT_SPEC.md":
        _require_mapping(published, _REGISTRY, "components", "spec_ref", token)
        if _requirements_region(old_text) != _requirements_region(new_text):
            raise _refuse(f"generated Registry requirements changed: {token}")
    elif token.startswith("odylith/atlas/source/") and path.suffix == ".mmd":
        _require_mapping(published, _ATLAS, "diagrams", "source_mmd", token)
    else:
        raise _refuse(f"selected path has no authored admission owner: {token}")


def require_authored_sync_admission(*, repo_root: Path, command_tokens: Sequence[str]) -> AuthoredSyncAdmission:
    """Called under the publication lock, after ordinary clean admission failed."""
    selected_paths = _explicit_paths(command_tokens, repo_root=repo_root)
    pinned = generations.pin_active_greenfield_generation(repo_root)
    active = publication.active_generation_identity(repo_root)
    if (active["write_set_hash"], active["generation_manifest_sha256"]) != (
        pinned.write_set_hash, pinned.manifest_sha256,
    ):
        raise _refuse("pinned generation differs from the active publication")
    selected = {}
    for token in selected_paths:
        previous, previous_mode = _regular_file(pinned.repository_root, token)
        current, current_mode = _regular_file(repo_root, token)
        if current_mode != previous_mode:
            raise _refuse(f"selected authored mode differs from publication: {token}")
        _require_authored_surface(repo_root, pinned.repository_root, token, previous, current)
        selected[token] = (current, current_mode)
    delta = write_sets.compile_greenfield_repository_write_set(
        source_root=pinned.repository_root, staged_root=repo_root, publication_precondition=active,
    )
    if (delta["directories"] or delta["directory_deletes"] or delta["deletes"]
            or any(row["path"] not in selected for row in delta["writes"])):
        raise _refuse("unselected managed files or directory inventory differ from publication")
    admission = AuthoredSyncAdmission(pinned=pinned, active=active, selected=selected)
    admission.require_compiled_intent(delta)
    write_sets.require_greenfield_repository_after_state(repo_root=repo_root, write_set=delta)
    admission.require_unchanged_intent(repo_root)
    return admission
