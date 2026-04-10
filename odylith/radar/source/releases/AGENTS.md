# Release Planning Source AGENTS

Scope: applies to all files under `odylith/radar/source/releases/`.

## Purpose
- Maintain the canonical repo-local release-planning registry and append-only workstream assignment history for Odylith Radar.

## Contract
- `releases.v1.json` is the canonical release registry and alias-ownership document.
- `release-assignment-events.v1.jsonl` is the append-only assignment history for add/remove/move release targeting.
- Release planning is additive to workstream topology and execution waves; do not copy active release targeting into backlog idea metadata or program files.

## Ownership
- Release planning truth is repo-local Odylith governance data.
- Keep release aliases explicit in the registry instead of inferring `current` or `next` from dates or semver order.
- Treat release `name` as explicit operator-owned source truth. Never infer,
  inherit, or rewrite it from release notes, versions, tags, or rendered
  surfaces without explicit maintainer authorization.
- Keep assignment history append-only so carry-forward and move decisions stay auditable.
- Treat current-release visibility as lifecycle-driven: an active `current`
  release remains live planning truth until maintainers explicitly mark it
  `shipped` or `closed`, even when no active workstreams remain.
- Keep completed-member visibility separate from active targeting: a current
  active release may still surface finished workstreams completed in that
  release while keeping active-target membership at zero.
