# Release Planning

Use this skill when the operator wants to define releases, name a release,
inspect release scope, or add, remove, and move backlog workstreams between
release targets such as `current`, `next`, a version, a tag, or a named
release.

## Goal
- Keep release-planning truth explicit, auditable, and repo-local.
- Make natural phrasing like "add B-123 to current release" map to one
  deterministic CLI and source contract.
- Keep release planning separate from umbrella execution waves and separate
  from the canonical maintainer publication lane.

## Keep It Separate
- Use release planning when the question is "what release should this
  workstream ship in?"
  Example: `B-067 -> 0.1.11`.
- Do not use this skill for umbrella sequencing questions such as "what should
  happen in W1, W2, and W3?"
  That is program or execution-wave planning under the Radar umbrella
  contract, not `odylith release ...`.
- The same workstream may participate in both because release target and
  execution order are different truths.

## Canonical Source Truth
- `odylith/radar/source/releases/releases.v1.json`
  Release registry with immutable `release_id`, optional `version`, `tag`,
  `name`, notes, lifecycle state, and explicit alias ownership.
- `odylith/radar/source/releases/release-assignment-events.v1.jsonl`
  Append-only add, remove, and move history for workstream targeting.

## Canonical Commands
```bash
./.odylith/bin/odylith release list --repo-root .
./.odylith/bin/odylith release show current --repo-root .
./.odylith/bin/odylith release create release-2026-04 --repo-root . --alias current --version 0.1.11
./.odylith/bin/odylith release update current --repo-root . --name "Boringly Trustworthy"
./.odylith/bin/odylith release add B-123 current --repo-root .
./.odylith/bin/odylith release move B-123 next --repo-root .
./.odylith/bin/odylith release remove B-123 --repo-root .
./.odylith/bin/odylith validate backlog-contract --repo-root .
./.odylith/bin/odylith sync --repo-root . --check-only --runtime-mode standalone
```

## Selector Rules
- Resolve releases by exact `release_id`, alias, exact `version`, exact `tag`,
  or unique exact `name`.
- Prefer `release:<id>` when a human name or version could collide.
- Treat `current release`, `release current`, `next release`, and
  `release next` as alias phrasing, not fuzzy search.
- Ambiguous selectors must fail closed. Do not guess.

## Mapping Natural Requests
- "Add B-123 to current release"
  - `odylith release add B-123 current`
- "Move B-123 to next release"
  - `odylith release move B-123 next`
- "Remove B-123 from release 0.1.11"
  - `odylith release remove B-123 0.1.11`
- "Name the release"
  - `odylith release update <selector> --name "..."` or set `--name` during `create`

## Guardrails
- `release_id` is immutable after creation.
- `current` and `next` are explicit aliases owned by source truth, not inferred
  from semver or dates.
- The current active release remains visible in governed read surfaces until it
  is explicitly updated to `shipped` or `closed`. Zero targeted workstreams is
  an empty state, not implicit GA.
- Finished work removed during release closeout may still appear in governed
  read surfaces as completed release members; that history does not make the
  workstream an active target again.
- One workstream may have at most one active release target at a time. Use
  `move`, not a second `add`, when work carries forward.
- `finished`, `parked`, and `superseded` workstreams cannot stay in active
  releases.
- `shipped` and `closed` releases are terminal for active planning. Move alias
  ownership off them before lifecycle closure.
- Release `name` is explicit operator-owned source truth. Matching authored
  release notes may exist for the same `version`, but they must never rename
  or override the release-planning record without explicit maintainer
  authorization.
- In practice, release names only change through an explicit
  `odylith release create ... --name` or `odylith release update ... --name`
  operation.
- If `name` is blank, release-planning surfaces may fall back to `version`,
  then `tag`, then `release_id`; they must never inherit a release-note title
  as the release name.

## Working Flow
1. Inspect the current release catalog and alias ownership first.
2. Create or update the release definition if the target release does not yet
   exist or needs a new name, version, tag, or alias.
3. Add, move, or remove workstreams through the release CLI rather than by
   editing source files manually.
4. Run at least `odylith validate backlog-contract --repo-root .` after
   release mutations.
5. If the release change affects governed read surfaces, refresh or prove them
   through `odylith sync --check-only --runtime-mode standalone`.
6. When the release actually ships to GA, move aliases as needed and
   explicitly mark the record `shipped` or `closed`; until then, expect the
   current release to remain visible even if it has zero targeted workstreams.
