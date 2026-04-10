#!/usr/bin/env bash
set -euo pipefail

odylith_script_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
odylith_repo_root="${ODYLITH_REPO_ROOT_OVERRIDE:-$odylith_script_repo_root}"
cd "$odylith_repo_root"

odylith_host_repo_root="${ODYLITH_HOST_REPO_ROOT:-$odylith_script_repo_root}"
if [[ -n "${ODYLITH_PYTHON:-}" ]]; then
  odylith_python="$ODYLITH_PYTHON"
elif [[ -x "$odylith_host_repo_root/.venv/bin/python" ]]; then
  odylith_python="$odylith_host_repo_root/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  odylith_python="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  odylith_python="$(command -v python)"
else
  odylith_python="$odylith_host_repo_root/.venv/bin/python"
fi
odylith_launcher="$odylith_repo_root/.odylith/bin/odylith"
odylith_release_repo="odylith/odylith"
odylith_release_actor="freedom-research"
odylith_release_ref="main"
odylith_release_session_file="${ODYLITH_RELEASE_SESSION_FILE:-$odylith_host_repo_root/.odylith/locks/release-session.json}"
odylith_release_worktree_helper="$odylith_host_repo_root/scripts/release_worktree.py"

die() {
  echo "error: $*" >&2
  exit 1
}

require_file() {
  local path="$1"
  [[ -e "$path" ]] || die "missing required file: $path"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

require_tag() {
  local tag="${1:-}"
  [[ -n "$tag" ]] || die "release tag is required (example: v0.1.0)"
  [[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([+-][0-9A-Za-z.-]+)?$ ]] || die "release tag must look like vX.Y.Z"
}

require_version() {
  local version="${1:-}"
  [[ -n "$version" ]] || die "version is required (example: make consumer-rehearsal VERSION=0.1.0)"
  [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([+-][0-9A-Za-z.-]+)?$ ]] || die "version must look like X.Y.Z"
}

require_origin_release_repo() {
  local origin_url="${1:-}"
  if [[ -z "$origin_url" ]]; then
    origin_url="$(git remote get-url origin 2>/dev/null || true)"
  fi
  [[ -n "$origin_url" ]] || die "release dispatch requires an origin remote for $odylith_release_repo"
  case "$origin_url" in
    "https://github.com/$odylith_release_repo"|\
    "https://github.com/$odylith_release_repo.git"|\
    "git@github.com:$odylith_release_repo.git"|\
    "ssh://git@github.com/$odylith_release_repo.git")
      ;;
    *)
      die "release dispatch is only allowed from the canonical repo $odylith_release_repo (origin: $origin_url)"
      ;;
  esac
}

require_release_actor_auth() {
  require_cmd gh
  local login
  login="$(gh api user --jq .login 2>/dev/null || true)"
  [[ "$login" == "$odylith_release_actor" ]] || die "release dispatch requires GitHub auth as $odylith_release_actor (current: ${login:-<unknown>})"
}

require_release_ref() {
  local ref="${1:-}"
  [[ "$ref" == "$odylith_release_ref" ]] || die "release dispatch is only allowed from ref $odylith_release_ref"
}

current_branch_name() {
  git branch --show-current 2>/dev/null || true
}

current_head_sha() {
  git rev-parse HEAD 2>/dev/null || true
}

current_source_version() {
  require_file "$odylith_python"
  "$odylith_python" - <<'PY'
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

path = Path("pyproject.toml")
if not path.is_file():
    raise SystemExit("missing pyproject.toml")
payload = tomllib.loads(path.read_text(encoding="utf-8"))
project = payload.get("project")
if not isinstance(project, dict):
    raise SystemExit("missing [project] table in pyproject.toml")
version = str(project.get("version") or "").strip()
if not version:
    raise SystemExit("missing [project].version in pyproject.toml")
print(version)
PY
}

require_current_release_branch() {
  local branch
  branch="$(current_branch_name)"
  [[ "$branch" == "$odylith_release_ref" ]] || die "release lane requires current branch $odylith_release_ref (current: ${branch:-<detached>})"
}

current_worktree_is_clean() {
  git diff --quiet --ignore-submodules HEAD -- && git diff --quiet --ignore-submodules --cached --
}

require_clean_worktree() {
  current_worktree_is_clean || die "release lane requires a clean worktree"
}

require_head_matches_origin_release_ref() {
  git fetch origin "$odylith_release_ref" --quiet
  local head_sha
  local origin_sha
  head_sha="$(current_head_sha)"
  origin_sha="$(git rev-parse "origin/$odylith_release_ref" 2>/dev/null || true)"
  [[ -n "$head_sha" && -n "$origin_sha" ]] || die "unable to resolve HEAD and origin/$odylith_release_ref for release validation"
  [[ "$head_sha" == "$origin_sha" ]] || die "release lane requires HEAD to match origin/$odylith_release_ref (HEAD=$head_sha origin/$odylith_release_ref=$origin_sha)"
}

require_canonical_release_lane() {
  require_origin_release_repo
  require_release_actor_auth
  require_current_release_branch
  require_clean_worktree
  require_head_matches_origin_release_ref
}

require_canonical_release_checkout() {
  require_origin_release_repo
  require_release_actor_auth
  require_clean_worktree
  require_head_matches_origin_release_ref
}

prepare_canonical_release_checkout() {
  require_file "$odylith_python"
  require_file "$odylith_release_worktree_helper"
  "$odylith_python" "$odylith_release_worktree_helper" prepare \
    --repo-root "$odylith_repo_root" \
    --remote origin \
    --ref "$odylith_release_ref"
}

cleanup_canonical_release_checkout() {
  local checkout_path="${1:-}"
  [[ -n "$checkout_path" ]] || return 0
  if [[ ! -e "$checkout_path" ]]; then
    return 0
  fi
  require_file "$odylith_python"
  require_file "$odylith_release_worktree_helper"
  "$odylith_python" "$odylith_release_worktree_helper" cleanup \
    --repo-root "$odylith_repo_root" \
    --path "$checkout_path" >/dev/null 2>&1 || true
}

run_in_canonical_release_checkout() {
  [[ "$#" -gt 0 ]] || die "run_in_canonical_release_checkout requires a command"
  require_origin_release_repo
  require_release_actor_auth
  local prepared mode checkout_path
  prepared="$(prepare_canonical_release_checkout)" || die "unable to prepare canonical release checkout"
  mode="${prepared%%$'\t'*}"
  checkout_path="${prepared#*$'\t'}"
  if [[ -z "$mode" || -z "$checkout_path" ]]; then
    die "release checkout helper returned an invalid payload: $prepared"
  fi
  if [[ "$mode" == "current" ]]; then
    (
      export ODYLITH_REPO_ROOT_OVERRIDE="$checkout_path"
      cd "$checkout_path"
      "$@"
    )
    return
  fi

  echo "release lane note: proving canonical origin/$odylith_release_ref in isolated clean checkout; active workspace changes are excluded. Use make dev-validate for detached source-local validation." >&2
  local status=0
  (
    export ODYLITH_HOST_REPO_ROOT="$odylith_repo_root"
    export ODYLITH_PYTHON="$odylith_python"
    export ODYLITH_RELEASE_SESSION_FILE="$odylith_release_session_file"
    export ODYLITH_REPO_ROOT_OVERRIDE="$checkout_path"
    cd "$checkout_path"
    "$@"
  ) || status=$?
  cleanup_canonical_release_checkout "$checkout_path"
  return "$status"
}

odylith_cli() {
  require_file "$odylith_python"
  PYTHONPATH=src "$odylith_python" -m odylith.cli "$@"
}

launcher_cli() {
  require_file "$odylith_launcher"
  "$odylith_launcher" "$@"
}

release_version_state_cli() {
  require_file "$odylith_python"
  "$odylith_python" "$odylith_repo_root/scripts/show_release_version_state.py" "$@"
}

release_session_cli() {
  require_file "$odylith_python"
  "$odylith_python" "$odylith_repo_root/scripts/release_version_session.py" "$@"
}

resolve_release_session_version() {
  local target="$1"
  local requested_version="${2:-}"
  local allow_session_init="${3:-true}"
  local auto_tag_if_unset="${4:-true}"
  release_session_cli resolve \
    --session-file "$odylith_release_session_file" \
    --remote origin \
    --target "$target" \
    --requested-version "$requested_version" \
    --allow-session-init "$allow_session_init" \
    --auto-tag-if-unset "$auto_tag_if_unset"
}

release_session_field() {
  local field="$1"
  require_file "$odylith_python"
  "$odylith_python" - <<'PY' "$odylith_release_session_file" "$field"
from __future__ import annotations

import json
import sys
from pathlib import Path

session_file = Path(sys.argv[1])
field = sys.argv[2]
if not session_file.is_file():
    raise SystemExit(f"missing release session: {session_file}")
payload = json.loads(session_file.read_text(encoding="utf-8"))
value = str(payload.get(field, "")).strip()
if not value:
    raise SystemExit(f"release session missing field `{field}`")
print(value)
PY
}

run_release_proof_steps() {
  local resolved_version="$1"
  local dist_dir="$2"
  local tag="v${resolved_version}"
  require_version "$resolved_version"
  [[ -n "$dist_dir" ]] || die "run_release_proof_steps requires dist_dir"

  "$odylith_python" "$odylith_host_repo_root/scripts/sync_version_truth.py" --repo-root . sync
  "$odylith_python" "$odylith_host_repo_root/scripts/sync_version_truth.py" --repo-root . release-check --expected-version "$resolved_version"
  "$odylith_host_repo_root/bin/validate"
  git diff --quiet --ignore-submodules HEAD -- || die "release proof validation mutated tracked files; commit them before release"
  git diff --quiet --ignore-submodules --cached -- || die "release proof validation staged tracked files; commit them before release"
  odylith_cli validate self-host-posture --repo-root . --mode release --expected-tag "$tag"
  "$odylith_python" -m hatch build --target wheel "$dist_dir"
  "$odylith_python" scripts/release/publish_release_assets.py --repo odylith/odylith --tag "$tag" --dist-dir "$dist_dir" --allow-local

  ODYLITH_RELEASE_PREFLIGHT_DIST_DIR="$dist_dir" "$odylith_python" - <<'PY'
from __future__ import annotations

import glob
import os
import zipfile
from pathlib import Path

dist_dir = str(os.environ.get("ODYLITH_RELEASE_PREFLIGHT_DIST_DIR") or "").strip()
if not dist_dir:
    raise SystemExit("ODYLITH_RELEASE_PREFLIGHT_DIST_DIR is required")
wheels = sorted(glob.glob(os.path.join(dist_dir, "*.whl")))
if not wheels:
    raise SystemExit(f"no wheel produced in {dist_dir}")

wheel = Path(wheels[-1])
with zipfile.ZipFile(wheel) as zf:
    names = zf.namelist()
bad = [
    name
    for name in names
    if name.startswith("tests/")
    or "/tests/" in name
    or "simulator.py" in name
    or os.path.basename(name).startswith("test_")
]
if bad:
    raise SystemExit(f"wheel contains test-only content: {bad[:10]}")

print(f"release preflight wheel ok: {wheel}")
PY

  "$odylith_python" scripts/release/local_release_smoke.py --version "$resolved_version" --dist-dir "$dist_dir"
}
