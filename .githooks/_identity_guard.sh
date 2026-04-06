#!/bin/sh
set -eu

repo_root="$(git rev-parse --show-toplevel)"
script_path="$repo_root/scripts/validate_git_identity.py"

if [ ! -f "$script_path" ]; then
  echo "identity guard: missing $script_path" >&2
  exit 2
fi

exec python3 "$script_path" "$@" --repo-root "$repo_root"
