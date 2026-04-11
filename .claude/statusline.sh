#!/usr/bin/env bash
# Odylith Claude Code statusline shim.
#
# Claude Code invokes this script before rendering its statusline and feeds
# it session context via stdin. The shim ignores stdin and delegates to the
# ``odylith claude statusline`` subcommand baked into the Python CLI, which
# returns a single line with the active workstream, brief freshness, and
# host family. The statusline contract must never raise: if the launcher is
# missing or the subcommand errors, emit the safe fallback string and exit 0
# so Claude Code still renders a status row.
set -u

repo_root="${CLAUDE_PROJECT_DIR:-$PWD}"
launcher="$repo_root/.odylith/bin/odylith"

if [ ! -x "$launcher" ]; then
  printf 'Odylith · grounding unavailable\n'
  exit 0
fi

output="$("$launcher" claude statusline --repo-root "$repo_root" 2>/dev/null)"
rc=$?
if [ "$rc" -ne 0 ] || [ -z "$output" ]; then
  printf 'Odylith · grounding unavailable\n'
  exit 0
fi

printf '%s\n' "$output"
exit 0
