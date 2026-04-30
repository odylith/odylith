status: finished

idea_id: B-140

title: Consumer Surface Migration Observer And Release Gate

date: 2026-04-29

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: migration-runtime, release-gate, guidance, skills, dashboard surfaces, install-managed assets

sizing: M

complexity: High

ordering_score: 100

ordering_rationale: Consumer migration misses directly damage upgrade trust and early-adopter branding; this should be a 0.1.12 release gate.

confidence: High

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-29-consumer-surface-migration-observer-and-release-gate.md

execution_model: standard

workstream_type: standalone

workstream_parent: 

workstream_children: 

workstream_depends_on: 

workstream_blocks: 

related_diagram_ids: 

workstream_reopens: 

workstream_reopened_by: 

workstream_split_from: 

workstream_split_into: 

workstream_merged_into: 

workstream_merged_from: 

supersedes: 

superseded_by: 

## Problem
Odylith can change dashboards, managed guidance, skills, install-managed assets, or host-facing surfaces in the product repo without explicitly assessing how already-installed consumer repositories will experience that change. That leaves migration needs to human memory after the code lands.

## Customer
Odylith maintainers preparing 0.1.12 and future releases, plus downstream consumer-repo operators who upgrade from earlier installed versions and expect dashboards, guidance, skills, hooks, and managed assets to migrate intentionally.

## Opportunity
Make consumer-lane migration assessment automatic whenever product surfaces move, so every release can prove that changed surfaces were either migration-safe, planned as release-note guidance, or backed by a real migration/repair task before publish.

## Proposed Solution
Add a surface migration observer to the migration runtime and wire it into `odylith release migration-gate`. The observer classifies changed consumer-visible surfaces, emits exact Radar markers for migration-assessment obligations, and blocks release gating until each observed need has a completed workstream record for the target version.

## Scope
- Add the shared observer runtime under `src/odylith/install/`.
- Wire observer output into release migration-gate JSON and human stdout.
- Update maintainer guidance and skills so every surface change considers installed consumer repos.
- Mirror changed guidance and skills into shipped bundle assets.
- Add focused tests for path classification, target-specific markers, release-gate blocking, CLI JSON, and mirror drift.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- False positives can slow release work if the observed surface classes are too broad. The first classifier set is intentionally limited to consumer-visible surfaces: guidance, skills, host assets, browser governance surfaces, install-managed assets, public docs, release guidance, and operator CLI contracts.

## Dependencies
- Migration runtime release gate.

## Success Metrics
release migration-gate reports observed surface migration needs; consumer-visible surface changes cannot pass without a tracked migration observer workstream or explicit resolved record; agent guidance and skills require migration impact assessment for any surface change; tests cover guidance, dashboard, skill, bundle, and install-managed surface path classes.

## Validation
- `python -m py_compile` for touched runtime, CLI, and tests.
- Focused migration runtime and CLI unit tests.
- Source/bundle mirror tests for changed guidance and skills.
- `odylith release migration-gate --repo-root . --target-version 0.1.12 --json`.
- `git diff --check`.

## Rollout
- Land in 0.1.12 as a release-gate hardening slice. Future surface changes reuse the same observer markers instead of relying on maintainer memory.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Add a migration observer to the migration-runtime release gate. It scans changed consumer-visible surface paths, classifies the migration risk, emits exact governance prompts, and fails the release gate until each observed need is linked to tracked Radar migration work or intentionally waived with evidence.

## Impacted Components
- `odylith`

## Interface Changes
- None decided yet; record interface changes once implementation is scoped.

## Migration/Compatibility
- No automatic consumer migration is required for this observer itself. It changes release-gate behavior in the product repo and installed guidance text in future bundles.
- Existing consumer installs are protected by the new pre-release observer because future changed surfaces cannot close without a completed migration assessment.

## Migration Observer Needs
- `migration-observer:0.1.12:guidance-and-skills:5edfb8f61a7a`
- `migration-observer:0.1.12:operator-cli-contracts:5048d0eb61c4`
- `migration-observer:0.1.12:public-docs-and-release-guidance:3d374298bec4`
- `migration-observer:0.1.12:browser-surfaces:742e1bb597ab`
- `migration-observer:0.1.12:install-managed-assets:9431818775c2`

## 0.1.12 Upgrade Assessment
- First-run install and sync overlap: existing 0.1.11 consumer repos can safely
  upgrade through the fixed installer/runtime because first-run shell rendering
  now acknowledges the freshly materialized managed-asset overlap instead of
  leaving the dashboard incomplete.
- Registry component registration drift: existing 0.1.11 repos that already
  ran `odylith component register` are repaired through `odylith doctor
  --repair`, which normalizes invalid `detected` category/qualification values
  and backfills missing `Feature History` sections before later Registry
  validation or dashboard refresh. This is not a hand-edit path; operators
  should upgrade and repair instead of editing
  `odylith/registry/source/component_registry.v1.json` directly.
- Atlas-first onboarding: 0.1.12 permits draft Atlas diagrams without forcing
  pre-existing Radar, technical-plan, and doc links, so the `odylith show`
  Atlas prompt is no longer a dead-end for new installs.
- Show-me scanner pollution: 0.1.12 ignores Odylith-managed install and
  governance files as app-source evidence, so repos that already installed
  Odylith are not prompted to govern Odylith's own generated dashboard tree as
  if it were the customer application.
- Host lint pollution: generated Python host hook and launcher assets now carry
  a file-level Ruff suppression so strict consumer commands such as
  `ruff check .` do not fail on Odylith-managed integration shims.
- Claude Code Stop-hook visibility: 0.1.12 no longer emits visible-intervention
  UX through Stop `systemMessage`; Stop logs/records only. Upgrade users should
  not see Odylith visibility recovery as `Stop hook error` or `Stop says`
  control transcript noise.
- Claude Code PostToolUse visibility: 0.1.12 direct-edit and Bash checkpoints
  stay silent after successful governed refresh. They emit only compact
  failure/skipped-refresh status, so successful edits no longer print Risks,
  History, Observation, Assist, product-repo workstream IDs, Casebook IDs, or
  transcript-proof copy into a consumer transcript.
- Codex post-bash and Stop visibility: 0.1.12 keeps real prompt/post-bash live
  interventions, but successful post-bash refreshes no longer print receipt
  text, and Stop summary no longer authors fresh branded closeouts or
  transcript-proof copy. Stop only logs or replays an already-earned pending
  live beat, optionally with its matching one-line Assist.
- Intervention visibility copy: 0.1.12 replaces recursive visibility-recovery
  copy such as "Show the next Odylith Observation" with a direct user-facing
  state line. The value-engine corpus and shared visibility broker now reject
  internal delivery or host-control vocabulary, product-theater phrases, and
  governance IDs that do not exist in the current repo before copy can render
  as visible intervention text. Existing consumer repos do not need data
  migration; upgrading the managed runtime and bundled assets is sufficient.
- Stale intervention stream repair: 0.1.12 `doctor --repair` removes stale
  0.1.11 Claude intervention events from consumer Compass streams when those
  events mention product-repo-only `B-096` or `CB-122` IDs absent from the
  local repo. This prevents upgraded repos from keeping old bad timeline
  evidence that later dashboard renders could re-display.
- Doctor repair for empty browser surfaces: 0.1.12 `doctor --repair` now
  detects missing first-run shell surfaces in a real installed tree and runs
  the same overlap-aware full surface bootstrap used by first install. Existing
  0.1.11 installs should not see repair say completed while the browser remains
  empty; only a failed repair should point operators at the explicit
  `sync --proceed-with-overlap` recovery.
- Normal CLI transcript shape: install, sync, and dashboard refresh write paths
  now show compact summaries and live progress by default. Operators who need
  the internal step graph, mutation classes, and path previews can still ask for
  `--dry-run` or `--verbose`, so 0.1.12 reduces terminal noise without hiding
  safety details from explicit preview/debug flows.
- Backlog topology authoring: `odylith backlog create --workstream-type
  umbrella` now creates a valid umbrella plus reciprocal child workstreams when
  multiple titles are supplied. Existing consumer repos do not need migration;
  this only makes first-run program and execution-wave setup possible without
  hand-editing Radar source truth.
- Intervention status and compatibility copy: 0.1.12 keeps raw visibility
  status enums in JSON for automation, but the human CLI/status copy now uses
  operator-facing labels such as "confirmed in this session" and
  "waiting-for-chat" instead of `chat_visible_proof`, `unproven_this_session`,
  `ledger_visible_unconfirmed`, transcript-confirmation wording, or
  `systemMessage`/`additionalContext` internals.
- Uninstall recovery: `odylith uninstall` now removes the visible repo-local
  `odylith/` tree instead of leaving stale or empty dashboard files behind.
  It keeps `.odylith/` launcher and audit state so the repo can still report
  version posture or reinstall cleanly, and symlink proof confirms it unlinks
  a linked `odylith/` path without following the target.
- Uninstall request routing: Claude and Codex managed bash guards now allow the
  supported `./.odylith/bin/odylith uninstall --repo-root .` lifecycle command
  while blocking raw shell or Python removal of Odylith-managed paths with a
  message that points back to uninstall. Existing consumer repos need an
  upgrade to receive the patched managed host assets; until then, operators
  should type the uninstall command explicitly and reject `rm -rf`,
  `shutil.rmtree`, hook-bypass guidance, commit/snapshot preflights, second
  confirmation detours, or claims that uninstall removes `.odylith/`.
- Release guidance: operators upgrading from 0.1.11 should run
  `./.odylith/bin/odylith doctor --repo-root . --repair` after upgrading when
  they have existing Registry records from `component register` or missing
  first-run shell surfaces. Run `./.odylith/bin/odylith sync --repo-root .
  --proceed-with-overlap` only if doctor repair still reports incomplete shell
  surfaces after attempting the repair.
- Remote upgrade advisory: `odylith version --check-upgrade` now performs a
  short-timeout, cached remote advisory check and stores its result under
  `.odylith/state/upgrade-check.v1.json`. Plain `odylith version` does not ping
  remote endpoints; it only displays cached advisory state. Enterprise and
  offline installs can disable checks with `ODYLITH_UPGRADE_CHECK=off`, point
  `ODYLITH_UPGRADE_CHECK_URL` at an approved mirror, tune interval/timeout with
  the documented env vars, or use `--upgrade-check-offline`. This is advisory
  only; `odylith upgrade` remains the signed verified release path.

## Test Strategy
- Unit-test surface classification without relying on Git state.
- Unit-test completed marker matching by target version.
- Unit-test release-gate blocking when a changed surface has no completed marker.
- Assert release-gate JSON carries the observer payload.
- Assert source and bundle copies preserve the migration-observer guidance.

## Open Questions
- None for this first wave. Additional surface classes can be added when a future change proves a concrete consumer-lane migration risk.

## Outcome
The observer is now part of the migration-runtime release gate. It records changed consumer-visible surface classes, provides exact governance prompts, and fails the gate until completed Radar migration-assessment markers exist for the target release and observed changed-path fingerprint.
