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

related_diagram_ids: D-019,D-020,D-036,D-042

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
- `migration-observer:0.1.12:operator-cli-contracts:8bd155b023a8`
- `migration-observer:0.1.12:public-docs-and-release-guidance:3d374298bec4`
- `migration-observer:0.1.12:browser-surfaces:742e1bb597ab`
- `migration-observer:0.1.12:install-managed-assets:9431818775c2`
- `migration-observer:0.1.12:install-managed-assets:d14d06cf271a`
- `migration-observer:0.1.12:guidance-and-skills:45ea19466ac3`
- `migration-observer:0.1.12:public-docs-and-release-guidance:5580fec19c37`
- `migration-observer:0.1.12:browser-surfaces:0e52f13dc5d1`
- `migration-observer:0.1.12:install-managed-assets:f38b248c4afc`
- `migration-observer:0.1.12:guidance-and-skills:9fb623126d5e`
- `migration-observer:0.1.12:operator-cli-contracts:e07ba033e117`
- `migration-observer:0.1.12:public-docs-and-release-guidance:0f9d169af4a3`
- `migration-observer:0.1.12:browser-surfaces:5a9b0129e994`
- `migration-observer:0.1.12:install-managed-assets:06b85aa9c5bf`
- `migration-observer:0.1.12:public-docs-and-release-guidance:05ba809e75b3`
- `migration-observer:0.1.12:browser-surfaces:7810e993e4e8`
- `migration-observer:0.1.12:install-managed-assets:1ab8cfc9a993`
- `migration-observer:0.1.12:guidance-and-skills:1e990eefbbfb`
- `migration-observer:0.1.12:operator-cli-contracts:731222452f92`
- `migration-observer:0.1.12:public-docs-and-release-guidance:4264bcadc26d`
- `migration-observer:0.1.12:browser-surfaces:74123c981071`
- `migration-observer:0.1.12:install-managed-assets:2b43ee19c828`
- `migration-observer:0.1.12:public-docs-and-release-guidance:fa3785ca8bb9`
- `migration-observer:0.1.12:public-docs-and-release-guidance:619e13200222`
- `migration-observer:0.1.12:operator-cli-contracts:95bdafb2d9c3`
- `migration-observer:0.1.12:operator-cli-contracts:b19ea13035eb`
- `migration-observer:0.1.12:operator-cli-contracts:5623e2b7a652`
- `migration-observer:0.1.12:operator-cli-contracts:ea9a447849da`
- `migration-observer:0.1.12:browser-surfaces:12abab7ee27b`
- `migration-observer:0.1.12:install-managed-assets:d0f5ae9b528d`
- `migration-observer:0.1.12:browser-surfaces:be89e7d8c73b`
- `migration-observer:0.1.12:browser-surfaces:3b985886b081`
- `migration-observer:0.1.12:guidance-and-skills:8bd324eee5c9`
- `migration-observer:0.1.12:operator-cli-contracts:543527c37b46`
- `migration-observer:0.1.12:browser-surfaces:78830ddaafa7`
- `migration-observer:0.1.12:install-managed-assets:fb5694fe0011`
- `migration-observer:0.1.12:guidance-and-skills:1210067e00a9`
- `migration-observer:0.1.12:operator-cli-contracts:f9cbe70854c0`
- `migration-observer:0.1.12:public-docs-and-release-guidance:e94df79bf12e`
- `migration-observer:0.1.12:browser-surfaces:d199eea3c898`
- `migration-observer:0.1.12:install-managed-assets:e8fc20ba7fea`
- `migration-observer:0.1.12:browser-surfaces:ef4035484a1f`
- `migration-observer:0.1.12:guidance-and-skills:29f7fa1bb934`
- `migration-observer:0.1.12:operator-cli-contracts:b6b723e0ade6`
- `migration-observer:0.1.12:browser-surfaces:72c852fe7cc9`
- `migration-observer:0.1.12:install-managed-assets:5918fe8926c0`
- `migration-observer:0.1.12:browser-surfaces:3f96348508b6`
- `migration-observer:0.1.12:browser-surfaces:98854e6093b8`
- `migration-observer:0.1.12:public-docs-and-release-guidance:84223e1b9464`
- `migration-observer:0.1.12:browser-surfaces:f8c8cc1cb827`
- `migration-observer:0.1.12:browser-surfaces:6dfeaacb6c70`
- `migration-observer:0.1.12:public-docs-and-release-guidance:e54b8d215fa7`
- `migration-observer:0.1.12:browser-surfaces:de68c95d0f21`
- `migration-observer:0.1.12:public-docs-and-release-guidance:ce8f131e3fb2`
- `migration-observer:0.1.12:browser-surfaces:e49d83468c2b`
- `migration-observer:0.1.12:install-managed-assets:3dfe999afb21`
- `migration-observer:0.1.12:install-managed-assets:365942f272bd`
- `migration-observer:0.1.12:install-managed-assets:0a6693568dcf`
- `migration-observer:0.1.12:install-managed-assets:b4e1e9bc8f82`
- `migration-observer:0.1.12:operator-cli-contracts:c6e13f7283c5`
- `migration-observer:0.1.12:operator-cli-contracts:40e56321befd`
- `migration-observer:0.1.12:operator-cli-contracts:0be705679685`
- `migration-observer:0.1.12:guidance-and-skills:2d48e421d4a4`
- `migration-observer:0.1.12:browser-surfaces:d6d3e6d10f84`
- `migration-observer:0.1.12:install-managed-assets:1d47c001ac50`

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
- Uninstall recovery: `odylith uninstall` now preserves the repo-local
  `odylith/` governed truth tree, detaches root guidance, removes `.odylith/`
  local runtime state, and removes Odylith-owned Claude/Codex hook entries
  from host project settings before deleting the launcher. The removal path
  tolerates late hook writes under `.odylith/`, and the host launcher now
  silently no-ops when an already-open host fires after a clean uninstall.
  Symlink proof confirms uninstall preserves linked `odylith/` targets and
  unlinks linked `.odylith/` state roots without following them.
- Uninstall request routing: Claude and Codex managed bash guards now allow the
  supported `./.odylith/bin/odylith uninstall --repo-root .` lifecycle command
  while blocking raw shell or Python removal of Odylith-managed paths with a
  message that points back to uninstall and says host directories such as
  `.claude/`, `.codex/`, and `.agents/` stay in place. Existing consumer repos
  need an upgrade to receive the patched managed host assets; until then,
  operators should type the uninstall command explicitly and reject `rm -rf`,
  `shutil.rmtree`, hook-bypass guidance, commit/snapshot preflights, second
  confirmation detours, or offers to remove host config directories.
- Hosted install same-version repair: 0.1.12 hosted install now treats an
  already-current repo as a compact install repair path instead of invoking the
  upgrade planner, so stale but valid migration ledgers that point at missing
  Odylith-owned value-engine corpus files are repaired without dumping an
  upgrade plan. Malformed migration ledgers still block as corruption, but the
  compact install path reports the problem without a Python traceback.
- Technical-plan help routing: `odylith plan --help` is now a read-only command
  guide that points to `odylith governance ...` and `odylith validate plan-* ...`
  instead of failing as an invalid top-level command. Managed Codex and Claude
  guidance now says help discovery should run one authoritative help command
  before exploratory filesystem probes, and it names the real
  `odylith/technical-plans/{in-progress,done,parked}/` layout instead of the
  nonexistent `odylith/technical-plans/source/` path. Existing consumer repos
  only need the 0.1.12 runtime/assets upgrade; no repo truth migration is
  required.
- Capability and engine inventory route: 0.1.12 adds the read-only
  `odylith capabilities` product inventory so prompts such as "list all
  Odylith capabilities and engines" return the host-model-agnostic product
  taxonomy instead of a thin `odylith --help` command list or Claude/Codex
  host capability prose. The inventory explicitly covers Analysis Engine,
  Governance Engine, Delivery Intelligence, Tribunal, Reasoning Engine, Proof
  State, Memory Substrate, Subagent Router/Orchestrator, lifecycle, trust,
  governed surfaces, and host adapters. Existing consumer repos need no
  source-truth migration; upgrading the managed runtime and bundled
  Claude/Codex guidance is sufficient. Migration observer markers:
  `migration-observer:0.1.12:guidance-and-skills:04a9b592880f`,
  `migration-observer:0.1.12:operator-cli-contracts:aa6affcce29e`,
  `migration-observer:0.1.12:public-docs-and-release-guidance:02ffa6495e36`,
  `migration-observer:0.1.12:browser-surfaces:af51fa1e4800`,
  `migration-observer:0.1.12:install-managed-assets:6915afe65bb3`.
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
- First-run install transcript hygiene: the hosted installer now marks the
  just-unpacked managed runtime as bootstrap-owned before calling the install
  lifecycle, so fresh installs no longer report thousands of runtime files as
  dirty user work. The first-run surface sync remains fail-open for diagnostic
  output, but successful bootstrap sync emits a compact success line instead
  of the full 23-step governance plan, managed-asset overlap preview, and
  benign empty-repo warnings. Existing installed repos do not need migration;
  the change affects new installs and future hosted refresh/upgrade handoff
  transcript shape.
- First-run install compact mode: hosted fresh installs now use short progress
  labels for the active work (`fetch`, `check`, `setup`, `write`, `draw`,
  `done`, `ready`, `open`, `start`) and keep lifecycle plans, overlap lists,
  path-heavy guidance, and long onboarding copy out of the default first-time
  transcript. Explicit CLI `--dry-run` and `--verbose` remain the detailed
  safety/debug lanes, so maintainers keep observability without making the
  default installer feel like an internal migration trace.
- Final 2026-04-30 release hardening sweep: the remaining changed
  public-doc/release-note, browser-surface, and install-managed-asset
  fingerprints are covered by the same upgrade posture. Existing consumer
  repos do not need a repo-truth migration; upgrade/repair brings the compact
  hosted install route, stale-residue repair, enterprise fetch diagnostics,
  refreshed dashboards, and bundled host/guidance assets. The release gate
  remains the proof boundary: if these fingerprints change again, the
  observer must produce new markers and this assessment must be revisited.
- Uninstall scope preview: 0.1.12 adds `odylith uninstall --dry-run` as the
  non-mutating answer to "what would uninstall touch?" The actual uninstall
  command stays a single lifecycle command, removes `.odylith/` runtime state
  and launcher files, detaches root guidance blocks, removes Odylith-owned
  hook entries from Claude/Codex project settings, and preserves the repo-owned
  `odylith/` governed truth plus host config directories. Claude and Codex
  managed guard text now routes raw deletion attempts back to the lifecycle
  command and names the dry-run preview only for scope questions.
- Shared runtime store deferral: v0.1.12 remains repo-local at runtime. It does
  not introduce `attach`, machine-global store paths, `odylith repos list`,
  shared runtime materialization, hardlink/reflink reuse, or other user-facing
  shared-store behavior. The only migration-prep change is read-only evidence:
  installs keep version/platform/release digest, feature-pack, trust-receipt,
  active-runtime-root, and activation-history data that a later dedicated
  immutable content-addressed store migration can verify. Existing consumer
  repos need no migration for this deferral; normal upgrade brings the helper
  and release-note language with the managed runtime and bundled assets.
- Upgrade transcript hygiene: normal 0.1.12 upgrade/migration output now keeps
  the operator path compact: verified release prep, activation result,
  dashboard refresh, report path, and rollback command. The full lifecycle
  plan, migration ledger, asset digests, destructive-write matrix, and Compass
  stage timings remain available through `--verbose`, `--dry-run`, `--json`,
  and the written upgrade report. Existing consumer repos need no data
  migration; this changes only CLI transcript shape and keeps automation JSON
  stable.
- Browser auto-open opt-out clarity: compact install output now makes inherited
  `ODYLITH_NO_BROWSER` visible as the reason auto-open was skipped, prints the
  exact local `odylith/index.html` path, and tells operators to unset the
  variable for the next install. Existing consumer repos need no migration; the
  change only improves the default transcript for shells where the opt-out
  leaked from earlier local testing.
- Host latency and Casebook token contract hardening: v0.1.13 host assets
  prefer the bootstrap doctor path when repair is needed, so Claude, Codex,
  and future host adapters do not keep re-entering the stale launcher during
  bootstrap repair. Casebook `Status` and `Type` are now compact token fields
  in source validation, bug capture, projections, and bundled dashboards;
  existing records are normalized in repo-owned Casebook truth. Existing
  consumer repos need no data migration. Upgrading installs the fixed host
  launcher, refreshed bundle assets, and compact Casebook renderer behavior.
  Migration observer markers:
  `migration-observer:0.1.12:guidance-and-skills:048a2f4ecf97`,
  `migration-observer:0.1.12:operator-cli-contracts:70c8b2cf9689`,
  `migration-observer:0.1.12:browser-surfaces:bc447ebffb0c`,
  `migration-observer:0.1.12:install-managed-assets:0576ffce86df`.
- Host hook fast-path dispatch: v0.1.13 keeps the public
  `./.odylith/bin/odylith claude|codex ...` command surface while the generated
  trusted launcher dispatches baked host hook commands directly to their
  runtime modules after trust selection. The low-signal prompt gate now uses a
  shared lightweight classifier before importing the full intervention renderer
  stack, and the Claude/Codex host contracts document that hot hooks must not
  pay for full CLI import when they can return empty. Existing consumer repos
  do not need repo-truth migration; upgrading installs the regenerated launcher,
  bundled host assets, refreshed guidance, and refreshed Casebook/Radar browser
  surfaces. Migration observer markers:
  `migration-observer:0.1.12:guidance-and-skills:2d48e421d4a4`,
  `migration-observer:0.1.12:browser-surfaces:d6d3e6d10f84`,
  `migration-observer:0.1.12:install-managed-assets:1d47c001ac50`.
- Upgrade-residue dashboard recovery: v0.1.13 makes post-upgrade dashboard
  refresh resilient when a consumer repo is midway through surface generation.
  The top-level shell now treats missing child dashboard HTML as a warning,
  Compass refresh creates the Casebook index and Radar traceability graph before
  render, shell refresh waits until owned child surfaces have settled, and
  registry validation ignores host-visibility chatter while preserving failures
  for meaningful unmapped implementation events. Existing consumer repos do not
  need repo-truth migration; upgrades from 0.1.10+ receive the fixed runtime and
  can repair stale 0.1.11/0.1.12 dashboard residue in place. Migration observer
  markers:
  `migration-observer:0.1.12:guidance-and-skills:20383b041e00`,
  `migration-observer:0.1.12:operator-cli-contracts:3f7f46e3c07b`,
  `migration-observer:0.1.12:browser-surfaces:48a6b76069b3`,
  `migration-observer:0.1.12:install-managed-assets:81225e1e602e`.
- Cross-host prompt-first and Compass settlement hardening: v0.1.13 preserves
  the Context Engine, memory substrate, execution handshake, Tribunal-backed
  proof posture, and Intervention/Assist hidden context while reducing hot
  hook latency through direct host dispatch and compact startup substrate
  packets. Maintainer-only narration guidance remains confined to the
  dev-maintainer subtree and is guarded from consumer-safe guidance, bundled
  host contracts, install-generated guidance, and shared skills. Compass
  dashboard refresh now settles provider-backed global standup briefs before
  reporting success and can repair upgrade-residue inputs in place. Existing
  consumer repos do not need repo-truth or data migration; upgrading installs
  the regenerated host launcher, host prompt/session assets, refreshed
  dashboards, and fixed Compass refresh runtime. Migration observer markers:
  `migration-observer:0.1.13:guidance-and-skills:20383b041e00`,
  `migration-observer:0.1.13:operator-cli-contracts:9d82eb895c46`,
  `migration-observer:0.1.13:browser-surfaces:7cf0ebcb5035`,
  `migration-observer:0.1.13:install-managed-assets:73dadb319858`.
- Mixed-version launcher compatibility: v0.1.13 generated launchers preserve
  direct host-hook dispatch for the warm path while remaining readable by the
  shipped v0.1.12 launcher health parser. Claude `prompt-bundle` launchers
  detect whether the active runtime or source `PYTHONPATH` contains the new
  bundle module; if not, they merge the shipped `prompt-context` and
  `prompt-teaser` commands so fresh installs keep prompt context and visible
  teaser behavior before the v0.1.13 runtime ships. Existing consumer repos do
  not need data migration; upgrading installs regenerated launchers and
  refreshed browser assets. Migration observer markers:
  `migration-observer:0.1.12:operator-cli-contracts:4eb40da3c1d9`,
  `migration-observer:0.1.12:browser-surfaces:ab0df3cd03b7`,
  `migration-observer:0.1.12:install-managed-assets:7b6ed784455c`,
  `migration-observer:0.1.13:operator-cli-contracts:4eb40da3c1d9`,
  `migration-observer:0.1.13:browser-surfaces:ab0df3cd03b7`,
  `migration-observer:0.1.13:install-managed-assets:7b6ed784455c`.
- Historical upgrade matrix proof: v0.1.13 adds explicit lifecycle coverage
  for consumer upgrades from 0.1.10, 0.1.11, and 0.1.12 into the 0.1.13
  target. The 0.1.10 fixture proves the value-engine migration still applies
  from legacy signal-ranker state; 0.1.11 and 0.1.12 prove the same migration
  skips cleanly while activation, pin adoption, and runtime pointer convergence
  still complete. Existing consumer repos do not need manual data migration;
  this adds release proof and refreshed Radar/Compass render artifacts only.
  Migration observer markers:
  `migration-observer:0.1.13:browser-surfaces:f7b7e4cdba20`,
  `migration-observer:0.1.13:browser-surfaces:02ebed1744ff`,
  `migration-observer:0.1.13:install-managed-assets:20e8ce49c04a`.
- Dev-maintainer source-local visibility proof: v0.1.13 restores the Codex
  post-bash live Observation/Proposal payload while keeping governed refresh
  work deferred to the dirty-event settlement lane. The source-local maintainer
  switch regenerated the tooling shell, Radar, Compass, and bundle mirror
  surfaces so the dashboard now reflects detached source-local posture instead
  of pinned dogfood. Existing consumer repos do not need repo-truth migration;
  upgrading installs the fixed Codex hook runtime and refreshed managed browser
  assets, while release proof must still return to pinned dogfood before
  shipping. Migration observer markers:
  `migration-observer:0.1.13:public-docs-and-release-guidance:c8276a3cb8e8`,
  `migration-observer:0.1.13:browser-surfaces:cc8a7f297f08`,
  `migration-observer:0.1.13:install-managed-assets:d2de2ef4649d`.
- Dev-maintainer Release Targets alias filtering: v0.1.13 keeps release
  registry history intact while making the default Compass release-target view
  follow explicit current/next aliases when those aliases exist. Older active
  release lanes remain in source truth and scoped drill-in paths, but they no
  longer make the live default view look pinned to 0.1.12 after B-141 moves to
  0.1.13. Existing consumer repos do not need data migration; upgrading
  installs refreshed browser and bundle assets. Migration observer markers:
  `migration-observer:0.1.13:browser-surfaces:a33e8d0e6dab`,
  `migration-observer:0.1.13:browser-surfaces:adfbbaeec25e`,
  `migration-observer:0.1.13:install-managed-assets:583b3a29cb60`.
- Casebook compact metadata detail hardening: v0.1.13 keeps legacy consumer
  Casebook records readable without allowing prose Status, Fixed, or Type
  values to leak into detail-card labels. Existing consumer records now flow
  through the registered v0.1.13 Casebook compact-metadata migration, which
  normalizes source labels, rebuilds the Casebook index, rerenders Casebook
  browser payloads, and writes a migration ledger for 0.1.10, 0.1.11, and
  0.1.12 upgrades. The release-path cleanup keeps the same behavior while
  using content fingerprints instead of whole-file snapshots for changed-path
  reporting. Migration observer markers:
  `migration-observer:0.1.13:operator-cli-contracts:b870d25c57e8`,
  `migration-observer:0.1.13:browser-surfaces:f2c4d30f468f`,
  `migration-observer:0.1.13:browser-surfaces:f56cbbad5b96`,
  `migration-observer:0.1.13:browser-surfaces:5c6e158288a8`,
  `migration-observer:0.1.13:install-managed-assets:b85c3e788eab`,
  `migration-observer:0.1.13:install-managed-assets:d5ce300448b1`,
  `migration-observer:0.1.13:operator-cli-contracts:1c7ce3ac7fe4`,
  `migration-observer:0.1.13:browser-surfaces:e0801e363df8`,
  `migration-observer:0.1.13:install-managed-assets:b62c9c457cb1`,
  `migration-observer:0.1.13:install-managed-assets:2c261b3fa6e6`,
  `migration-observer:0.1.13:browser-surfaces:ef3937feff8b`,
  `migration-observer:0.1.13:install-managed-assets:e021b3887dda`,
  `migration-observer:0.1.13:install-managed-assets:c0dc04317b0c`.
- Casebook detail gutter hardening: v0.1.13 tightens the selected-bug detail
  gutter in live and bundled Casebook HTML, repairs the media-block brace shape
  so padding no longer depends on CSS parser recovery, and keeps existing
  consumer Casebook data compatible because only rendered layout changes.
  Migration observer markers:
  `migration-observer:0.1.13:browser-surfaces:1c8a6979a09c`,
  `migration-observer:0.1.13:browser-surfaces:83f738bbae83`,
  `migration-observer:0.1.13:browser-surfaces:262b63ed190c`,
  `migration-observer:0.1.13:browser-surfaces:c72b1df630d2`,
  `migration-observer:0.1.13:install-managed-assets:8afd5be2970e`,
  `migration-observer:0.1.13:install-managed-assets:6aad0d78490e`,
  `migration-observer:0.1.13:install-managed-assets:352b7f58e4df`.
- Compass skipped-narration status routing: v0.1.13 keeps the last validated
  Standup Brief visible when fresh narration is skipped for non-material fact
  churn, and routes the provider-spend warning to the existing Compass header
  status banner. Existing consumer repos do not need data migration; upgrading
  installs refreshed Compass and Casebook browser assets plus the bundled
  Compass dashboard runtime assets.
  Migration observer markers:
  `migration-observer:0.1.12:browser-surfaces:154862df3418`,
  `migration-observer:0.1.12:install-managed-assets:07f37c277434`,
  `migration-observer:0.1.13:browser-surfaces:154862df3418`,
  `migration-observer:0.1.13:install-managed-assets:07f37c277434`.
- Governed sync performance proof surfaces: v0.1.13 adds end-to-end latency
  and no-provider credit-burn tests for full sync dry-run, all-surface
  dashboard refresh, Compass status, owned Radar/Atlas/Registry/Casebook
  refresh commands, and multi-surface dashboard parallelism. The source change
  adds tests and B-141 governance notes; refreshed Radar and Compass browser
  surfaces plus bundle mirrors are install-managed output updates only.
  Existing consumer repos do not need data migration; upgrading installs the
  refreshed browser assets. Migration observer markers:
  `migration-observer:0.1.13:browser-surfaces:fcd4ad300aac`,
  `migration-observer:0.1.13:browser-surfaces:3822d2354e1c`,
  `migration-observer:0.1.13:install-managed-assets:b45cab51875d`.
- Startup grounding order and index-only Casebook migration guard: v0.1.13
  makes `odylith start` the serial first gate before follow-on `context`,
  `query`, `git status`, or broad repo inspection across Codex, Claude, and
  installed guidance/skill mirrors. The same pass fixes Casebook compact-label
  migration so guidance-only `AGENTS.md` files under `odylith/casebook/bugs/`
  do not count as bug records and do not trigger empty index/dashboard rewrites
  over customer truth. Existing consumer repos do not need manual migration;
  upgrades refresh managed guidance, host command assets, skills, and rendered
  browser assets while preserving repo-owned Casebook source truth when no bug
  records exist. Migration observer markers:
  `migration-observer:0.1.13:guidance-and-skills:633944f92664`,
  `migration-observer:0.1.13:operator-cli-contracts:b0183d029a95`,
  `migration-observer:0.1.13:browser-surfaces:de6df3fb3057`,
  `migration-observer:0.1.13:install-managed-assets:d0e3fe35c626`,
  `migration-observer:0.1.13:browser-surfaces:8e66cd173155`,
  `migration-observer:0.1.13:install-managed-assets:2f2e3b612696`,
  `migration-observer:0.1.13:browser-surfaces:b065a42fa247`,
  `migration-observer:0.1.13:browser-surfaces:36a9b304f8a5`.
- Cross-host host-surface diet and prompt receipt fast path: v0.1.13 removes
  duplicated Claude guidance bytes, removes no-op Claude prompt marker shell
  hooks, makes Claude SessionStart quiet while preserving auto-memory writes,
  skips full prompt receipts only for generic low-signal prompts, keeps
  Odylith-directed prompt receipts and live Observation/Proposal eligibility,
  and lets exact non-governed Claude Bash commands bypass heavy checkpoint
  grounding. Codex receives the same generic low-signal prompt fast path while
  preserving Odylith-directed receipt behavior. Existing consumer repos do not
  need data migration; upgrading refreshes managed host guidance, hook
  settings, bundle assets, and runtime surfaces while preserving user-owned
  host settings through the additive install merge. Migration observer markers:
  `migration-observer:0.1.13:guidance-and-skills:355461e98fe5`,
  `migration-observer:0.1.13:operator-cli-contracts:e167a3c7d9d7`,
  `migration-observer:0.1.13:browser-surfaces:2870c7b4909c`,
  `migration-observer:0.1.13:install-managed-assets:e825f6f123e1`,
  `migration-observer:0.1.13:operator-cli-contracts:8480b8f26127`,
  `migration-observer:0.1.13:browser-surfaces:8b10e3560e2d`,
  `migration-observer:0.1.13:install-managed-assets:f87bf182fdad`.
- Consumer guidance and Claude skill invocation surface diet: v0.1.13 trims
  installed consumer guidance and model-visible Claude workflow skills without
  removing Odylith startup, Context Engine, Execution Engine, memory,
  Tribunal, Intervention Engine, observers, governance, Surface DAGs,
  delivery, analysis, or migration-breakage observation. Existing consumer
  repos do not need data migration; upgrading refreshes managed guidance,
  host skill shims, rendered browser assets, and generated bundle assets
  through the normal additive install/upgrade path. Maintainer-only
  release-gate and migration-observer rules remain confined to the product
  repo maintainer lane. Migration observer markers:
  `migration-observer:0.1.13:guidance-and-skills:87630690d87a`,
  `migration-observer:0.1.13:guidance-and-skills:59639ab45ae1`,
  `migration-observer:0.1.13:guidance-and-skills:89d6d904843f`,
  `migration-observer:0.1.13:operator-cli-contracts:b09578c9b18f`,
  `migration-observer:0.1.13:browser-surfaces:e3adbd2d8288`,
  `migration-observer:0.1.13:install-managed-assets:d7d268bdf746`,
  `migration-observer:0.1.13:install-managed-assets:6b654b4be78e`,
  `migration-observer:0.1.13:install-managed-assets:e3b4249862a5`.
- B-141 topology and Casebook sidepanel card display: v0.1.13 refreshes
  Radar traceability so B-141 advertises the runtime/topology diagrams that
  actually bound the cross-host latency work, and refreshes Casebook browser
  assets so sidepanel bug-card body text is clamped to two preview lines.
  Existing consumer installs need no data migration; upgrade/dashboard
  refresh replaces the generated browser assets and Radar traceability graph.
  Migration observer markers:
  `migration-observer:0.1.13:browser-surfaces:3951dfb049aa`,
  `migration-observer:0.1.13:operator-cli-contracts:f64f4820aa8e`,
  `migration-observer:0.1.13:operator-cli-contracts:3e98e8bddd13`,
  `migration-observer:0.1.13:browser-surfaces:4c75930a07c1`.
- Casebook release closeout automation: v0.1.13 adds the
  `odylith release casebook-closeout` command and wires shipped release
  updates to close eligible `FixedPendingRelease` records automatically after
  validation evidence is present. Existing consumer installs need no data
  migration; upgrade installs receive the managed CLI, Casebook guidance, and
  refreshed browser surfaces, while local bug source stays repo-owned.
  Migration observer markers:
  `migration-observer:0.1.13:operator-cli-contracts:dbdb5bb92f21`,
  `migration-observer:0.1.13:browser-surfaces:af4b4c0ff738`,
  `migration-observer:0.1.13:install-managed-assets:92cac291c52f`.
- Root guidance routing and topology validator decomposition: v0.1.13 keeps
  root guidance as a compact contract, routes detailed anti-slop examples to
  the playbook and skill, removes duplicate Casebook Claude companion wording,
  and moves Radar topology validation out of the oversized backlog validator
  into a focused runtime module. Existing consumer installs need no data
  migration; upgrade installs receive refreshed guidance, command/runtime
  code, rendered governance surfaces, and bundle mirrors through the normal
  additive managed-asset refresh. Migration observer markers:
  `migration-observer:0.1.13:guidance-and-skills:361e66bc060e`,
  `migration-observer:0.1.13:operator-cli-contracts:114d91bc9afa`,
  `migration-observer:0.1.13:public-docs-and-release-guidance:c8276a3cb8e8`,
  `migration-observer:0.1.13:browser-surfaces:7aa82e9853a8`,
  `migration-observer:0.1.13:browser-surfaces:8138268c6173`,
  `migration-observer:0.1.13:browser-surfaces:0ce09f5edbc9`,
  `migration-observer:0.1.13:install-managed-assets:db520dee14e4`.
- Odylith-tree guidance de-dup: v0.1.13 trims duplicated consumer-lane
  `odylith/AGENTS.md` working rules while preserving explicit startup, context,
  execution, memory, Tribunal, Intervention Engine, observer, governance,
  subagent, Surface DAG, delivery, analysis, migration-observer, CLI-first,
  visibility-proof, consumer-boundary, and host-specific capability contracts.
  Existing consumer installs need no data migration; upgrade refreshes managed
  guidance and bundle mirrors through the additive managed-asset path, while
  Compass browser/runtime artifacts refresh through the usual governed surface
  render lane. Migration observer markers:
  `migration-observer:0.1.13:guidance-and-skills:15c190e29627`,
  `migration-observer:0.1.13:browser-surfaces:7bef9ce648f9`,
  `migration-observer:0.1.13:install-managed-assets:3b63012c3b68`,
  `migration-observer:0.1.13:browser-surfaces:533f5e4374a6`,
  `migration-observer:0.1.13:install-managed-assets:06c877ec7676`.
- Source-local memory activation and Assist visibility recovery: v0.1.13
  keeps consumer pinned runtimes isolated on the managed feature pack while
  dev-maintainer `source-local` launchers prefer the source checkout `.venv`
  so full LanceDB/PyArrow/Tantivy memory stays active. The same pass maps
  exact Assist-visibility complaints to the shared visible recovery line
  without changing ordinary low-signal prompt silence, and makes forced
  Compass daemon refresh autospawn the local Context Engine daemon instead of
  failing when it idles out. Existing consumer installs need no data migration;
  upgrade refreshes managed runtime code, browser governance surfaces, and
  bundle mirrors through the additive install-managed asset path. Migration
  observer markers:
  `migration-observer:0.1.13:browser-surfaces:b9d0ec78e453`,
  `migration-observer:0.1.13:browser-surfaces:2bbecacc6d56`,
  `migration-observer:0.1.13:install-managed-assets:82e3cd8ed4c1`.
- Greenfield domain-intelligence governance: v0.1.13 adds a provider-free
  `odylith greenfield propose/apply` path for empty and thin consumer repos,
  installs the managed guidance/skill shims, records Domain Intelligence as a
  Registry component, adds Atlas topology, and filters zero-file prompt
  intervention chatter out of Compass timeline transactions. Existing
  consumer installs need no data migration; upgrade refreshes managed
  guidance, command/runtime code, generated browser surfaces, and bundle
  mirrors while local source-backed governance remains repo-owned. Migration
  observer markers:
  `migration-observer:0.1.13:guidance-and-skills:d8c8ff0d951d`,
  `migration-observer:0.1.13:operator-cli-contracts:2d60d08c285d`,
  `migration-observer:0.1.13:operator-cli-contracts:26bfb61a6298`,
  `migration-observer:0.1.13:browser-surfaces:695cf1a55b3d`,
  `migration-observer:0.1.13:browser-surfaces:c279a5da21f4`,
  `migration-observer:0.1.13:install-managed-assets:4444145d768a`,
  `migration-observer:0.1.13:guidance-and-skills:b6ccbcebbd7c`,
  `migration-observer:0.1.13:browser-surfaces:fcbd8d2ec808`,
  `migration-observer:0.1.13:install-managed-assets:0b654205854a`.
- Engine inventory and Compass settlement hardening: v0.1.13 makes Context
  Engine and Domain Intelligence explicit in the host-agnostic capability
  inventory, rejects markup snippets as project identity prose during
  greenfield repo analysis, and treats non-forced Compass brief settlement
  gaps as visible warnings instead of release-blocking failures after the
  runtime payload has refreshed. Existing consumer installs need no data
  migration; upgrade refreshes managed runtime code, browser governance
  surfaces, and the Compass bundle mirror while preserving repo-owned
  governance truth. The same assessment covers the consumer launcher hygiene
  fix that keeps maintainer-only `source-local` routing out of repaired
  consumer launchers while retaining explicit source-local support for
  product-repo maintainer posture. Migration observer markers:
  `migration-observer:0.1.13:browser-surfaces:d00ba488e699`,
  `migration-observer:0.1.13:install-managed-assets:13d6f64a015b`,
  `migration-observer:0.1.13:install-managed-assets:6a1d8f00879f`,
  `migration-observer:0.1.13:browser-surfaces:cafacdb848c3`,
  `migration-observer:0.1.13:install-managed-assets:9a4f23dde703`,
  `migration-observer:0.1.13:install-managed-assets:8137f3c657dd`.
- Deepened Domain Intelligence science/math catalog: v0.1.13 expands the
  provider-free greenfield proposal path with first-class formal-proof,
  computational-notebook, numerical-simulation, scientific-pipeline,
  geospatial/environmental, ML-experiment, and math-education lenses, and
  splits program/release/UX planning into a smaller reusable runtime module.
  Existing consumer installs need no data migration; upgrade refreshes managed
  greenfield skill guidance, refreshed product browser surfaces, and bundled
  install-managed dashboard copies while keeping all proposal writes
  confirmation-gated and user-intent-labeled until source evidence exists.
  Migration observer markers:
  `migration-observer:0.1.13:guidance-and-skills:b5799cbf748f`,
  `migration-observer:0.1.13:browser-surfaces:bb2be774790f`,
  `migration-observer:0.1.13:install-managed-assets:f400668668ca`,
  `migration-observer:0.1.13:guidance-and-skills:38e6768904a3`,
  `migration-observer:0.1.13:browser-surfaces:da46e2ca9dea`,
  `migration-observer:0.1.13:browser-surfaces:44b8f03ad08b`,
  `migration-observer:0.1.13:install-managed-assets:20dacaa00761`,
  `migration-observer:0.1.13:browser-surfaces:7a832cdde5ae`,
  `migration-observer:0.1.13:browser-surfaces:e7074b845e26`,
  `migration-observer:0.1.13:browser-surfaces:64c67de45d32`.
- Domain Intelligence fit and program-formation hardening: v0.1.13 adds
  host-reasoned fit assessment, acronym-safe titles, domain-aware first-slice
  validation wording, a dedicated proposal renderer, explicit parent/child
  program-formation policy, and accepted-proposal Compass memory records. The
  release-version truth and security posture docs now also
  target v0.1.13 so local release bundles carry a v0.1.13 wheel instead of a
  mismatched v0.1.12 package. Existing consumer installs need no data
  migration; upgrade refreshes managed greenfield skill guidance, regenerated
  governance browser surfaces, public release guidance, and bundled
  install-managed assets while keeping all proposal writes confirmation-gated.
  Migration observer markers:
  `migration-observer:0.1.13:guidance-and-skills:9075101e3a40`,
  `migration-observer:0.1.13:browser-surfaces:2f376881da04`,
  `migration-observer:0.1.13:install-managed-assets:75cf4de5d713`,
  `migration-observer:0.1.13:browser-surfaces:3d9a853aa730`,
  `migration-observer:0.1.13:install-managed-assets:3b31898b633e`,
  `migration-observer:0.1.13:browser-surfaces:1ec38a98f26b`,
  `migration-observer:0.1.13:browser-surfaces:fb44f0624d3e`,
  `migration-observer:0.1.13:operator-cli-contracts:993ddc4af587`,
  `migration-observer:0.1.13:browser-surfaces:6d15ce4c0b44`,
  `migration-observer:0.1.13:install-managed-assets:e2a8129f2ea6`,
  `migration-observer:0.1.13:public-docs-and-release-guidance:1cfdbc5a7431`,
  `migration-observer:0.1.13:browser-surfaces:189eeef17a7f`,
  `migration-observer:0.1.13:install-managed-assets:df982c278aaa`,
  `migration-observer:0.1.13:public-docs-and-release-guidance:66717a535044`,
  `migration-observer:0.1.13:install-managed-assets:545aea26da90`,
  `migration-observer:0.1.13:browser-surfaces:8a26320aa5c6`.
- Domain Intelligence host-reasoning correction: v0.1.13 removes the in-code
  greenfield project taxonomy from the active proposal-authoring path and keeps
  consumer installs on the host-reasoned contract instead. Existing installs
  need no repo data migration; upgrade refreshes managed guidance, skills,
  bundled browser assets, and runtime validation. Confirmed greenfield writes
  remain explicit through `odylith greenfield apply --confirm`, and Atlas
  drafts now require host-authored Mermaid source before any governed write.
  This supersedes the earlier seed-catalog implementation as an inactive
  design exploration; the release path is host reasoning plus Odylith
  validation/apply, not a checked-in domain taxonomy.
  Migration observer markers:
  `migration-observer:0.1.13:guidance-and-skills:d307d1dee98b`,
  `migration-observer:0.1.13:browser-surfaces:de07c1596960`,
  `migration-observer:0.1.13:install-managed-assets:10f2fe027321`,
  `migration-observer:0.1.13:guidance-and-skills:43e7a7e7b66a`,
  `migration-observer:0.1.13:install-managed-assets:cc92d0a4ee9d`,
  `migration-observer:0.1.13:browser-surfaces:af1a8c005565`,
  `migration-observer:0.1.13:install-managed-assets:0b0c0d1ffef8`,
  `migration-observer:0.1.13:browser-surfaces:c977b656d5a8`,
  `migration-observer:0.1.13:browser-surfaces:ec2ce938e93c`,
  `migration-observer:0.1.13:install-managed-assets:253ccfb23e93`,
  `migration-observer:0.1.13:guidance-and-skills:e854d7e0d9b5`,
  `migration-observer:0.1.13:install-managed-assets:8dc77c50aa92`.
- Public documentation and bundled release-guidance refresh: v0.1.13 updates
  README, operator instructions, status disclosures, outcome framing,
  release notes, and the bundled consumer README/release-note copies so the
  shipped docs describe host-reasoned greenfield proposals, confirmation-gated
  apply, compact release proof, and source-truth boundaries consistently.
  Existing consumer installs need no data migration; upgrade installs receive
  refreshed managed docs and release guidance, and already-owned governance
  truth stays untouched.
  Migration observer markers:
  `migration-observer:0.1.13:public-docs-and-release-guidance:67252caffe8e`,
  `migration-observer:0.1.13:browser-surfaces:8d03362b49b6`,
  `migration-observer:0.1.13:install-managed-assets:84b480bd2eaf`,
  `migration-observer:0.1.13:browser-surfaces:7ca3752b114d`,
  `migration-observer:0.1.13:install-managed-assets:877351c7e794`,
  `migration-observer:0.1.13:install-managed-assets:378a6ed807cc`.

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

## 0.1.14 Upgrade Assessment
- Casebook status is a controlled seven-state FSM in v0.1.14. Existing consumer Casebook records from unknown/legacy install state and every historical 0.1.0 through 0.1.13 release upgrade through the registered `v0.1.14-casebook-status-fsm` migration, which normalizes source records, rerenders Casebook, and writes `.odylith/state/migrations/v0.1.14-casebook-status-fsm.v1.json`.
- `FixedPendingRelease` remains an active pre-release state and is not treated as terminal; only `Closed` exits the open Casebook lane. Release closeout remains the owner that turns shipped fixed-pending records into `Closed`.
- Casebook Type is now a controlled but broad host-agnostic taxonomy instead of arbitrary compact acceptance. Legacy consumer labels such as `PrivateJobsRunnerManifes`, `TestHarnessInfraRegressi`, and `ForwardFixUpdatedLocallyPendingPlatformReleaseDeploy` normalize to allowed category tokens during migration, while unknown arbitrary tokens fall back to `Product` instead of passing source validation.
- Existing consumer installs do not need manual source edits. Upgrade/repair paths use the migration runtime and normal managed-asset refresh to update browser assets, bundled Casebook guidance, and rendered Casebook payloads without overwriting repo-owned governance truth.
- Browser-surface churn in the current v0.1.14 branch is intentionally covered by browser proof for the Casebook status filter, humanized status labels, detail summary card layout, and generated Casebook payload. Atlas browser churn now has a first-class generated-surface migration instead of relying on a manual refresh.
- The final Casebook detail polish keeps the narrative in a full-width `Summary` card rather than a capped `Casebook` card. Existing consumer installs receive this through generated Casebook browser-surface refresh, and the v0.1.14 Casebook migration verifier treats the old card contract as stale generated surface drift.
- Casebook generated-surface reuse now fingerprints both the product renderer/metadata code and the outer surface-refresh DAG inputs. A consumer upgrade cannot reuse an old Casebook browser app merely because the source bug files are unchanged; generator behavior changes force a fresh rendered surface.
- Atlas diagram rendering is migrated by the registered `v0.1.14-atlas-render-surface-polish` migration. It rerenders stale SVG/PNG assets when Mermaid render fingerprints, legacy palette tokens, or unmanaged rendered node/cluster colors are present, rerenders `odylith/atlas/atlas.html` with a pure-white viewer stage, and writes `.odylith/state/migrations/v0.1.14-atlas-render-surface-polish.v1.json`.
- Atlas visual semantics now have a two-level contract: lane/container color means grouping, ownership, or phase; inner node color means semantic role such as input/source, reasoning/component, decision/gate, apply/write, memory/proof, or neutral. Atlas now owns rendered color for consistency across all existing diagrams: authored Mermaid remains topology truth, but the shared Mermaid render worker applies the darker managed palette over old `classDef`/`style` color tokens without changing the pure-white viewer background.
- Atlas `--all-stale` now selects render-style fingerprint drift as stale, not only old review dates or watched-path drift. This closes the consumer-upgrade gap where a shared renderer polish change could leave older SVG/PNG assets visually inconsistent even though the diagram source had not changed.
- The shared topology spine is now regenerated as part of the Atlas v0.1.14 migration. The migration rebuilds `odylith/radar/traceability-graph.v1.json`, adds Registry component, Atlas diagram, execution-program, wave, release, and Radar workstream edges, and records a `multipartite-spine-v1` topology integrity score in the migration ledger. Existing consumer installs therefore receive the new traceability graph contract during upgrade instead of carrying a stale graph until a later manual refresh.
- Compass/Radar/Registry generated asset churn remains generated-surface refresh, not a separate repo data migration, because this slice changed Casebook and Atlas runtime contracts only.
- Install-managed asset churn is covered by normal bundle update semantics plus registered migration definitions: shipped Casebook guidance mirrors the source guidance, the Casebook FSM migration makes behavioral status conversion automatic during upgrades, and Atlas render-style changes are repaired by the Atlas migration from the consumer repo's own diagram source truth. The node-palette renderer change is covered by the same render fingerprint path, so 0.1.10/0.1.11/0.1.12/0.1.13 installs rerender stale Atlas assets during upgrade instead of requiring hand refresh.
- Operator CLI contract changes are additive: the migration registry now includes `v0.1.14-casebook-status-fsm` and `v0.1.14-atlas-render-surface-polish`, and release migration-gate reports the historical 0.1.x -> 0.1.14 path as covered migration ranges.
- Greenfield proposal contract changes are additive and source-compatible: new proposals default the first target release selector to `0.0.1`, accepted proposals now create an umbrella execution-wave program document when child workstreams exist, and release assignment targets the first wave plus umbrella instead of blanket-tagging every child. Existing proposal JSON that already names a release selector remains respected, and consumer-owned backlog, Registry, Atlas, Compass, and release truth are still written only after `odylith greenfield apply --confirm`.
- Customer core-detail validation is relaxed from the old six-word minimum to a one-token minimum for `## Customer` only. The stricter anti-placeholder checks and six-word minimums remain on Problem, Opportunity, Product View, and Success Metrics, so old one-word customer fields migrate by validation compatibility rather than source rewriting.
- Public release guidance impact is limited to generated delivery-intelligence/readout state in this branch; no consumer-owned source truth requires a manual migration.

## 2026-05-03 Reviewability Addendum
- Upgrade report reviewability now separates required migration writes, generated refresh churn, install-managed assets, runtime/report state, and manual-review paths. This keeps broad upgrade output reviewable instead of mixing Casebook source-truth normalization with ordinary generated shell refresh.
- Consumer upgrade sequencing now lets registered release migrations own Casebook source-truth normalization. The upgrade path no longer normalizes Casebook bug metadata through the consumer index sync before the migration runner, so dirty pre-existing bug files touched by migration appear in the upgrade report.
- The change-review classifier treats `odylith/runtime/source/` as install-managed consumer runtime asset churn, not manual-review application work. Local consumer files outside Odylith remain surfaced as manual review.
- The migration observer path normalizer now strips only leading `./`, not leading dot characters. Dot-prefixed consumer assets such as `.odylith` or `.codex` are no longer collapsed into misleading non-hidden paths during release assessment.
- Browser-surface proof now includes a dirty consumer repo upgraded from 0.1.13 to 0.1.14 with legacy bad Casebook metadata, a stale URL status filter, generated shell refresh, and a browser assertion that rows still render with humanized status/type detail.
- Casebook detail text now uses the full width of the `Summary` card, and the empty/fallback browser state is explicit when search or filters produce zero visible rows.
- Engine-integrity hardening in the v0.1.14 branch changed Benchmark, Context
  Engine, Registry, Casebook, Atlas, and shell generated outputs. The browser
  surface churn is covered by the registered Casebook and Atlas generated
  refresh migrations; install-managed asset churn is covered by normal bundle
  update semantics plus those same registered migration verifiers.
- Atlas compact-viewer fit was tightened after browser proof found D-030 could
  first-paint below the readability threshold on compact screens. The change is
  generated-renderer owned, keeps the viewer stage pure white, and is covered by
  the Atlas render-surface migration rather than a hand repair.
- Host-model agnostic review found no new renderer or migration branch on any
  host, provider, model, or agent identity. The Atlas polish path keys off
  Mermaid source/style truth and rendered SVG style evidence only; diagrams
  whose subject names a host remain ordinary Atlas topology records.
- Lane-discipline review kept the proof split explicit: source-local commands
  prove unreleased maintainer code, pinned-release lane status proves the current
  product-repo runtime posture, and consumer installs receive the Casebook/Atlas
  changes through registered release migrations plus normal bundle refresh
  semantics. No consumer path is allowed to activate source-local maintainer
  code.
- Atlas migration latency review collapsed rendered SVG style inspection to one
  read/parse per diagram for cluster and node polish checks. Fresh Atlas render
  proof for 43 diagrams completed with 43 fresh, 0 stale, and 0.59s wall time.
- The latest generated browser and install-managed asset fingerprints are still
  migration-safe for consumers: browser surfaces are regenerated from governed
  renderer/source truth, and install-managed bundle mirrors are refreshed through
  the existing install/upgrade asset synchronization contract.
- The decision-color follow-up only changes the Atlas renderer/config palette,
  regenerated browser surfaces, and bundled generated Atlas/Casebook/Radar/
  Registry shell assets. Existing consumer source truth remains preserved; the
  v0.1.14 Atlas render-style migration intentionally detects old SVG/PNG style
  fingerprints and rerenders them through the same managed upgrade path.
- Historical-range migration proof is now a required fixture class for every
  registered release migration. The gate no longer accepts a migration
  definition with only dry-run/apply/rerun/stale-ledger/skipped-version proof;
  it also requires explicit evidence that unknown legacy state and every
  historical 0.1.x release before the current release plan cleanly into the
  target migration path.
- The semantic Atlas palette follow-up keeps color deterministic and generated:
  source Mermaid topology remains the truth, while the renderer owns visual
  color. Cluster color now keys off the same visible label plus Mermaid
  subgraph identifier used by the renderer; migration detection rejects old
  order-based lane colors, accepts current cluster-inherited node fills, and
  reports zero stale render paths after the full catalog refresh.
- The latest browser and install-managed asset fingerprints are covered by the
  same v0.1.14 Atlas render-surface migration and normal bundle synchronization
  contract. Consumer-owned diagram source, backlog, Registry, Casebook, and
  Compass truth are not rewritten during install; existing 0.1.10 through
  0.1.13 installs rerender stale generated Atlas assets from local source truth
  during upgrade.
- Operator CLI and public-doc/reporting churn in this branch is additive release
  proof and benchmark documentation state, not a new destructive consumer data
  migration. The release migration gate remains fail-closed until these
  fingerprints are bound to this completed migration assessment.
- The Product Governed Harness / Turn Gate benchmark formalization changes add
  product runtime decisions, benchmark report fields, Registry component truth,
  release-target wording, and generated browser surface refreshes. The consumer
  migration posture is additive: existing source truth is not rewritten, rendered
  Registry/Radar/Atlas/Compass assets are regenerated from governed local truth,
  and old benchmark reports remain readable through derived compatibility fields.
  Fresh headless Chromium coverage exercised the shell default route; Radar
  `B-118` deep link; Registry `governed-harness`; Atlas `D-024`; Casebook;
  Compass; desktop and mobile viewports; impossible-search empty states; and
  degraded payload fixtures. The only surfaced UI regression was Compass attempting
  a `file://` JSON fetch despite already loading the embedded runtime JS; the
  template and bundle mirror now skip that fetch on file-backed surfaces.

Migration observer markers for this assessment:
- `migration-observer:0.1.14:operator-cli-contracts:dce35485ba07`
- `migration-observer:0.1.14:public-docs-and-release-guidance:c8276a3cb8e8`
- `migration-observer:0.1.14:browser-surfaces:fa89cb5fd7d2`
- `migration-observer:0.1.14:install-managed-assets:5c2bbc2978da`
- `migration-observer:0.1.14:operator-cli-contracts:402136e0398d`
- `migration-observer:0.1.14:browser-surfaces:cd53cbdf5da4`
- `migration-observer:0.1.14:install-managed-assets:87cd517d3fd5`
- `migration-observer:0.1.14:browser-surfaces:e453ed10928f`
- `migration-observer:0.1.14:install-managed-assets:6f32b94b5363`
- `migration-observer:0.1.14:browser-surfaces:a9356669fb28`
- `migration-observer:0.1.14:install-managed-assets:0b4307f3dce4`
- `migration-observer:0.1.14:guidance-and-skills:5db32f2987ff`
- `migration-observer:0.1.14:operator-cli-contracts:e1abf985ede6`
- `migration-observer:0.1.14:install-managed-assets:1d4f10095f9b`
- `migration-observer:0.1.14:operator-cli-contracts:2d3701102456`
- `migration-observer:0.1.14:operator-cli-contracts:0a8c3f9b2b7a`
- `migration-observer:0.1.14:browser-surfaces:7f7bd69a8dc0`
- `migration-observer:0.1.14:operator-cli-contracts:6c8f21465bf7`
- `migration-observer:0.1.14:browser-surfaces:fd975b633b46`
- `migration-observer:0.1.14:install-managed-assets:a7e30bf7b29c`
- `migration-observer:0.1.14:operator-cli-contracts:78bd88e6dc7f`
- `migration-observer:0.1.14:browser-surfaces:cdddb847ee9c`
- `migration-observer:0.1.14:install-managed-assets:fd10220c45e7`
- `migration-observer:0.1.14:install-managed-assets:93adce4724db`
- `migration-observer:0.1.14:browser-surfaces:ccace5dd3597`
- `migration-observer:0.1.14:install-managed-assets:a1affeb6cf6a`
- `migration-observer:0.1.14:browser-surfaces:492f9b7c0771`
- `migration-observer:0.1.14:browser-surfaces:b31f63954a7a`
- `migration-observer:0.1.14:install-managed-assets:e6fe806b6b2c`
- `migration-observer:0.1.14:browser-surfaces:2a84febff00a`
- `migration-observer:0.1.14:install-managed-assets:1cfbc9a3d55c`
- `migration-observer:0.1.14:browser-surfaces:153451a01209`
- `migration-observer:0.1.14:install-managed-assets:0e8582122c9e`
- `migration-observer:0.1.14:browser-surfaces:eb0df9d94382`
- `migration-observer:0.1.14:install-managed-assets:1399dd8df581`
- `migration-observer:0.1.14:browser-surfaces:676bc95aa23f`
- `migration-observer:0.1.14:install-managed-assets:8aef028d8b71`
- `migration-observer:0.1.14:browser-surfaces:1f6c0bfb0d82`
- `migration-observer:0.1.14:browser-surfaces:ea1639f2f7ab`
- `migration-observer:0.1.14:install-managed-assets:e23c645938ac`
- `migration-observer:0.1.14:browser-surfaces:b837e43d920f`
- `migration-observer:0.1.14:install-managed-assets:7e630a9ec669`
- `migration-observer:0.1.14:operator-cli-contracts:a2f8783ca40e`
- `migration-observer:0.1.14:browser-surfaces:31cad59063eb`
- `migration-observer:0.1.14:browser-surfaces:7638a63401c0`
- `migration-observer:0.1.14:install-managed-assets:6cdc35a7067e`
- `migration-observer:0.1.14:browser-surfaces:534bf25aaff7`
- `migration-observer:0.1.14:install-managed-assets:9d0a7bcdd9ff`
- `migration-observer:0.1.14:browser-surfaces:9a28712a1b8f`
- `migration-observer:0.1.14:install-managed-assets:b8cd0958ad5a`
- `migration-observer:0.1.14:browser-surfaces:2148442b7f83`
- `migration-observer:0.1.14:install-managed-assets:1b037b621ef9`
- `migration-observer:0.1.14:browser-surfaces:ae770b4d8cc7`
- `migration-observer:0.1.14:install-managed-assets:0ac7ccb1c77d`
- `migration-observer:0.1.14:operator-cli-contracts:bf744bbab40d`
- `migration-observer:0.1.14:browser-surfaces:a371bff537ac`
- `migration-observer:0.1.14:install-managed-assets:fe7abb4cf478`
- `migration-observer:0.1.14:browser-surfaces:8d99ed8ed8e2`
- `migration-observer:0.1.14:install-managed-assets:608e1152e253`
- `migration-observer:0.1.14:operator-cli-contracts:0942471fe516`
- `migration-observer:0.1.14:public-docs-and-release-guidance:987530a55111`
- `migration-observer:0.1.14:browser-surfaces:c4397cface1d`
- `migration-observer:0.1.14:install-managed-assets:b75b7d53959d`
- `migration-observer:0.1.14:browser-surfaces:d883f0423a24`
- `migration-observer:0.1.14:install-managed-assets:115989511d7d`
- `migration-observer:0.1.14:browser-surfaces:1c29f285545e`
- `migration-observer:0.1.14:install-managed-assets:bd0bed9814dd`
- `migration-observer:0.1.14:browser-surfaces:51ba5efbb798`
- `migration-observer:0.1.14:install-managed-assets:24025292a0dd`
- `migration-observer:0.1.14:browser-surfaces:597e50554af1`
- `migration-observer:0.1.14:install-managed-assets:121a792a1657`
- `migration-observer:0.1.14:public-docs-and-release-guidance:2dea6c816224`
- `migration-observer:0.1.14:public-docs-and-release-guidance:7ae5ea00d66a`
- `migration-observer:0.1.14:browser-surfaces:a34583a76e66`
- `migration-observer:0.1.14:install-managed-assets:38450e754d08`
- `migration-observer:0.1.14:public-docs-and-release-guidance:b434849a9cbc`
- `migration-observer:0.1.14:browser-surfaces:210b4d5b31c0`
- `migration-observer:0.1.14:install-managed-assets:94f47e9c8cac`
- `migration-observer:0.1.14:public-docs-and-release-guidance:ce303c4cd30f`
- `migration-observer:0.1.14:install-managed-assets:13f15f932050`
- `migration-observer:0.1.14:browser-surfaces:3dc864525c0a`
- `migration-observer:0.1.14:browser-surfaces:2bc16e52e857`
- `migration-observer:0.1.14:install-managed-assets:b6f3e45c2bb6`
- `migration-observer:0.1.14:browser-surfaces:3a0922f20803`
- `migration-observer:0.1.14:install-managed-assets:d7ee76b62591`
- `migration-observer:0.1.14:operator-cli-contracts:672d8e71e5fb`
- `migration-observer:0.1.14:browser-surfaces:a0f2462f7333`
- `migration-observer:0.1.14:install-managed-assets:026e981d2397`
- `migration-observer:0.1.14:operator-cli-contracts:d1546b46cab4`
- `migration-observer:0.1.14:browser-surfaces:082d686c209c`
- `migration-observer:0.1.14:install-managed-assets:13f26f2bb451`
- `migration-observer:0.1.14:operator-cli-contracts:6ab68b8ca8b4`
- `migration-observer:0.1.14:operator-cli-contracts:dcac88f4e4a7`
- `migration-observer:0.1.14:browser-surfaces:6584e43cc8d1`
- `migration-observer:0.1.14:install-managed-assets:8afd5be2970e`
- `migration-observer:0.1.14:operator-cli-contracts:430cbf2c16a3`
- `migration-observer:0.1.14:browser-surfaces:c27f8838b3c7`
- `migration-observer:0.1.14:install-managed-assets:017a0c8f19fa`
- `migration-observer:0.1.14:browser-surfaces:2d323cc9b2f3`
- `migration-observer:0.1.14:browser-surfaces:0dbe8cc13855`
- `migration-observer:0.1.14:install-managed-assets:50b82d75fe4f`
- `migration-observer:0.1.14:operator-cli-contracts:9871cf63f2ba`
- `migration-observer:0.1.14:browser-surfaces:537ae469ce88`
- `migration-observer:0.1.14:browser-surfaces:2ee6238bab31`
- `migration-observer:0.1.14:install-managed-assets:6aad0d78490e`

Validation evidence for the Casebook status-FSM slice:
- `python -m py_compile src/odylith/runtime/common/casebook_metadata.py src/odylith/runtime/governance/casebook_source_validation.py src/odylith/runtime/surfaces/render_casebook_dashboard.py src/odylith/install/casebook_metadata_migration.py src/odylith/install/migration_runtime.py src/odylith/install/migration_definitions.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_casebook_source_validation.py tests/unit/runtime/test_casebook_bug_index.py tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/install/test_casebook_metadata_migration.py tests/unit/install/test_migration_runtime.py tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_14` (`104 passed`)
- `PYTHONPATH=src python -m pytest -q tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_13 tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_14` (`2 passed`)
- `odylith casebook validate --repo-root .` (`161 records`)
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_context_engine_turn_cli.py tests/unit/runtime/test_odylith_benchmark_runner.py::test_diagnostic_profile_keeps_public_pair_packet_only` (`5 passed`; diagnostic cold default and Context Engine closed-pipe guard)
- `odylith context-engine --repo-root . benchmark --profile diagnostic --limit 5 --no-write-report` (`provisional_pass`; diagnostic default uses cold cache)
- `set -o pipefail; odylith context-engine --repo-root . benchmark --profile diagnostic --limit 1 --no-write-report --json | head -n 1 >/dev/null` (`exit 0`; downstream pipe closure stays quiet)
- `PYTHONPATH=src python -m odylith.runtime.surfaces.render_casebook_dashboard --repo-root . --output odylith/casebook/casebook.html --runtime-mode standalone` (`total_cases: 161`, `open_total: 69`)
- `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_casebook_sort_browser.py tests/integration/runtime/test_casebook_list_layout_browser.py` (`8 passed`)
- `PYTHONPATH=src python -m py_compile src/odylith/install/atlas_surface_migration.py src/odylith/install/migration_runtime.py src/odylith/install/migration_definitions.py src/odylith/install/casebook_metadata_migration.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_atlas_surface_migration.py tests/unit/install/test_casebook_metadata_migration.py tests/unit/install/test_migration_runtime.py` (`67 passed`)
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_diagram_freshness.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/runtime/test_casebook_source_validation.py` (`78 passed`)
- `PYTHONPATH=src python -m pytest -q tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_13 tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_14` (`2 passed`)
- `PYTHONPATH=src python -m py_compile src/odylith/runtime/surfaces/render_casebook_dashboard.py src/odylith/install/casebook_metadata_migration.py`
- `PYTHONPATH=src python -m odylith.runtime.surfaces.render_casebook_dashboard --repo-root . --output odylith/casebook/casebook.html --runtime-mode standalone` (`total_cases: 161`, `open_total: 69`)
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/install/test_casebook_metadata_migration.py tests/integration/runtime/test_casebook_list_layout_browser.py tests/integration/runtime/test_surface_browser_layout_audit.py` (`61 passed`)
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_diagram_freshness.py tests/unit/install/test_atlas_surface_migration.py` (`51 passed`)
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_atlas_surface_migration.py tests/unit/runtime/test_build_traceability_graph.py tests/unit/test_cli.py::test_validate_topology_integrity_dispatch_accepts_forwarded_flags` (`15 passed`)
- `odylith validate topology-integrity --repo-root .` (`score: 100/100`, `spine: 244 nodes, 1562 structural edges`)
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_backlog_authoring.py tests/unit/runtime/test_program_wave_authoring.py tests/unit/runtime/test_execution_wave_contract.py tests/unit/runtime/test_release_planning.py tests/unit/install/test_codex_project_assets.py` (`118 passed`)
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_migration_runtime.py` (`51 passed`)
- `PYTHONPATH=src python -m pytest -q tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_14` (`1 passed`)
- `odylith release migration-gate --repo-root . --target-version 0.1.14 --json` (`blocked_manual_migrations: []`)
- `PYTHONPATH=src ODYLITH_BROWSER_FAILURE_SCREENSHOTS=.odylith/browser-failures python -m pytest -q tests/integration/runtime/test_atlas_sort_browser.py tests/integration/runtime/test_surface_browser_layout_audit.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_context_execution_alignment_browser.py tests/integration/runtime/test_intervention_visibility_browser.py tests/integration/runtime/test_surface_browser_filter_audit.py tests/integration/runtime/test_casebook_sort_browser.py tests/integration/runtime/test_casebook_list_layout_browser.py tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_compass_browser_regression_matrix.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py` (`188 passed, 1 skipped`)
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_context_engine_proof_packet_runtime.py tests/unit/runtime/test_context_engine_topology_contract.py tests/unit/runtime/test_execution_engine.py tests/unit/runtime/test_execution_engine_handshake.py tests/unit/runtime/test_intervention_engine.py tests/unit/runtime/test_intervention_engine_apply.py tests/unit/runtime/test_intervention_engine_hygiene.py tests/unit/runtime/test_intervention_engine_package_layout.py tests/unit/runtime/test_intervention_engine_performance.py tests/unit/runtime/test_tribunal_engine.py tests/unit/runtime/test_greenfield_host_routing.py tests/unit/runtime/test_greenfield_proposals.py tests/unit/test_cli.py` (`324 passed`)
- `PYTHONPATH=src python -m pytest -q tests/integration/install/test_lifecycle_simulator.py tests/unit/install/test_atlas_surface_migration.py tests/unit/install/test_casebook_metadata_migration.py tests/unit/install/test_migration_runtime.py` (`75 passed`)
- `odylith casebook validate --repo-root .` (`162 records`)
- `odylith validate topology-integrity --repo-root .` (`score: 100/100`, `spine: 245 nodes, 1566 structural edges`)
- `odylith validate guidance-behavior --repo-root .` (`6 cases`, `11 checks`)
- `odylith validate discipline --repo-root . --json` (`status: passed`, `26 cases`, hot-path pass rate `1.0`, host/provider calls `0`)
- `odylith release migration-gate --repo-root . --target-version 0.1.14 --json` (`blocked_manual_migrations: []`, `ungated_lifecycle_paths: []`, ranges cover legacy, v0.1.11, v0.1.13, and v0.1.14 migrations)
- `odylith greenfield propose --repo-root . --prompt 'Draft a greenfield Odylith proposal for a small research project with backlog, planned Registry components, Atlas topology, program waves, and release targets. Do not write until I confirm.' --format json` (`host_reasoned_proposal_request`, confirmation-gated, contains `0.0.1`, program, and wave release language)
- `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_atlas_sort_browser.py tests/integration/runtime/test_surface_browser_filter_audit.py::test_atlas_filter_audit_accepts_compact_diagram_ids_and_normalized_titles` (`4 passed`)
- `PYTHONPATH=src python -m odylith.runtime.surfaces.auto_update_mermaid_diagrams --repo-root . --all-stale --runtime-mode standalone` (`40 render-needed diagrams`, then fresh)
- `PYTHONPATH=src python -m odylith.runtime.surfaces.auto_update_mermaid_diagrams --repo-root . --all-stale --runtime-mode standalone --dry-run` (`no stale diagrams found`)
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_upgrade_reporting.py tests/unit/runtime/test_render_casebook_dashboard.py tests/integration/runtime/test_casebook_sort_browser.py tests/integration/runtime/test_casebook_list_layout_browser.py tests/integration/runtime/test_casebook_consumer_upgrade_browser.py` (`24 passed`)
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_casebook_source_validation.py tests/unit/runtime/test_generated_refresh_guard.py tests/unit/runtime/test_casebook_bug_index.py tests/unit/install/test_casebook_metadata_migration.py tests/unit/install/test_migration_runtime.py tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_13 tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_14` (`107 passed`)
- `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py::test_install_existing_complete_repo_routes_through_upgrade_lifecycle tests/unit/test_cli.py::test_install_dry_run_existing_complete_repo_previews_upgrade_lifecycle tests/unit/test_cli.py::test_install_product_repo_shape_does_not_route_through_consumer_upgrade tests/unit/install/test_release_bootstrap.py::test_generated_install_script_routes_complete_already_current_install_through_upgrade_lifecycle` (`4 passed`; hosted installer and direct CLI install both route complete existing consumer installs through upgrade while product-repo maintainer shape stays out of the consumer route)
- `odylith casebook validate --repo-root .` (`161 records`)
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_migration_runtime.py::test_every_registered_upgrade_migration_has_full_lifecycle_fixture_coverage tests/unit/install/test_migration_runtime.py::test_release_migrations_cover_any_historical_0_1_release_to_v014 tests/integration/install/test_lifecycle_simulator.py::test_lifecycle_simulator_proves_historical_upgrades_to_0_1_14` (`3 passed`; unit proof covers unknown legacy state plus every 0.1.0-0.1.13 release, lifecycle proof exercises 0.1.0-0.1.13 install/upgrade activation)
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/install/test_casebook_metadata_migration.py tests/integration/runtime/test_casebook_list_layout_browser.py` (`22 passed`; proves stale URL cleanup, display-label normalization, and full-width Casebook summary card after source-local render)
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_migration_runtime.py tests/integration/install/test_lifecycle_simulator.py` (`61 passed`; historical upgrade matrix covers unknown legacy state plus every 0.1.0-0.1.13 release into 0.1.14)
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_diagram_freshness.py tests/unit/install/test_atlas_surface_migration.py` (`52 passed`; Atlas render-surface migration and color/freshness contracts)
- `odylith sync --repo-root . --check-only --runtime-mode standalone` (`passed`; source-local sync check, no runtime fallback)
- `odylith release migration-gate --repo-root . --target-version 0.1.14 --json` (`blocked_manual_migrations: []`, `ungated_lifecycle_paths: []`)
- `make dev-validate` (`3733 passed, 1 skipped in 963.19s`; source-local maintainer lane validation, with release eligibility still requiring pinned dogfood proof)

Validation evidence for the Product Governed Harness Turn Gate browser-surface slice:
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_turn_gate.py tests/unit/test_cli.py::test_turn_gate_decide_cli_emits_product_receipt tests/unit/runtime/test_odylith_benchmark_live_execution.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_publication.py tests/unit/runtime/test_odylith_benchmark_shard_merge.py tests/unit/runtime/test_odylith_benchmark_graphs.py tests/unit/runtime/test_odylith_benchmark_corpus.py` (`399 passed`)
- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_turn_gate.py tests/unit/test_cli.py::test_turn_gate_decide_cli_emits_product_receipt tests/unit/runtime/test_odylith_benchmark_live_execution.py::test_run_live_scenario_uses_turn_gate_early_exit_proof` (`10 passed`)
- Headless Chromium shell matrix over default, Radar `B-118`, Registry `governed-harness`, Atlas `D-024`, Casebook, and Compass at desktop and mobile viewports (`16 checked`, `failures: []`)
- Headless Chromium degraded payload matrix over Registry, Radar, Atlas, Casebook, and Compass (`5 checked`, `failures: []`)
- The generated Radar install-managed asset change for marker `migration-observer:0.1.14:install-managed-assets:121a792a1657` is a bundle mirror of this refreshed B-140 assessment and requires no custom consumer data migration beyond the normal v0.1.14 bundle/dashboard refresh path.
- The Benchmark Formal Model public-docs change for marker `migration-observer:0.1.14:public-docs-and-release-guidance:2dea6c816224` is interpretation-only documentation for the v0.1.14 Turn Gate benchmark model. Existing consumer installs do not require data migration; the release requirement is accurate docs publication with the normal bundle/docs refresh.
- The governed sync repair for markers `migration-observer:0.1.14:public-docs-and-release-guidance:7ae5ea00d66a`, `migration-observer:0.1.14:browser-surfaces:a34583a76e66`, and `migration-observer:0.1.14:install-managed-assets:38450e754d08` refreshed component spec forensics, Atlas/Radar/Registry/Casebook/Compass browser surfaces, and bundle mirrors from source truth. Existing consumer installs do not require a custom data migration beyond the normal v0.1.14 managed surface refresh path.
- The v0.1.14 GA release metadata and security refresh for markers `migration-observer:0.1.14:public-docs-and-release-guidance:b434849a9cbc`, `migration-observer:0.1.14:browser-surfaces:210b4d5b31c0`, and `migration-observer:0.1.14:install-managed-assets:94f47e9c8cac` bumps tracked version truth to 0.1.14, adds the v0.1.14 release note, updates root and bundled security posture, records the exact benchmark-proof override, and regenerates governed browser surfaces plus install bundle mirrors. Existing consumer installs do not require a custom data migration beyond normal v0.1.14 version adoption, release-note sync, security-doc refresh, dashboard refresh, and the registered 0.1.14 migration set already covered by the release migration gate.
- The release-note YAML-safety repair for markers `migration-observer:0.1.14:public-docs-and-release-guidance:ce303c4cd30f` and `migration-observer:0.1.14:install-managed-assets:13f15f932050` is a front-matter wording correction in the source and bundled v0.1.14 release note. Existing consumer installs do not require a custom data migration; the normal v0.1.14 release-note sync is sufficient.
- The final governed-sync browser refresh for marker `migration-observer:0.1.14:browser-surfaces:3dc864525c0a` updates Radar, Registry, Casebook, Compass, Atlas, and shell render outputs after the v0.1.14 release/security/governance truth changed. Existing consumer installs do not require a custom data migration beyond the normal v0.1.14 dashboard refresh and registered migration set.
- The release-candidate shell auto-refresh hardening for markers `migration-observer:0.1.14:browser-surfaces:2bc16e52e857` and `migration-observer:0.1.14:install-managed-assets:b6f3e45c2bb6` replaces same-URL shell reload with a cache-busted state-preserving reload after the checked-in payload fingerprint changes, then refreshes the generated shell and bundle mirror. Existing consumer installs do not require a custom data migration beyond normal v0.1.14 managed asset adoption and dashboard refresh; focused proof passed the Turn Gate CLI audit matrix and the upgrade spotlight auto-refresh browser cases.
- The post-sync release-candidate marker settlement for `migration-observer:0.1.14:browser-surfaces:3a0922f20803` and `migration-observer:0.1.14:install-managed-assets:d7ee76b62591` records the final content-addressed browser and bundle fingerprints after the shell auto-refresh hardening was rendered. Existing consumer installs still require no bespoke data migration beyond normal v0.1.14 managed asset adoption, dashboard refresh, and the registered 0.1.14 migration set.
- The post-release dashboard-version drift repair for CB-168, covered by
  markers `migration-observer:0.1.14:operator-cli-contracts:dcac88f4e4a7`,
  `migration-observer:0.1.14:browser-surfaces:6584e43cc8d1`, and
  `migration-observer:0.1.14:install-managed-assets:8afd5be2970e`, adds a mutable
  `.odylith/runtime/odylith-version-state.v1.{json,js}` sidecar, forces the
  default shell-facing dashboard refresh after upgrade, and moves sync
  dirty-overlap blocking before tracked Radar normalization. Marker
  `migration-observer:0.1.14:operator-cli-contracts:430cbf2c16a3` covers the
  final execution-step wiring that preserves the dirty-overlap pre-mutation
  gate while keeping the Radar normalization blocker summary. Existing
  consumers need no source-truth migration; normal v0.1.14 upgrade/dashboard
  refresh writes the sidecar and rerenders shell assets, while dirty worktrees
  get a narrow `odylith dashboard refresh --repo-root . --force` recovery path.
- The final source-local full dashboard refresh for markers
  `migration-observer:0.1.14:browser-surfaces:c27f8838b3c7` and
  `migration-observer:0.1.14:install-managed-assets:017a0c8f19fa` rerenders
  Radar, Compass, Atlas, Registry, Casebook, and the shell after the dashboard
  version-state sidecar and sync guard changes. Existing consumers need no
  bespoke data migration beyond normal v0.1.14 managed asset adoption and
  dashboard refresh.
- The install/upgrade dashboard-refresh settlement for marker
  `migration-observer:0.1.14:operator-cli-contracts:c691540eb853` closes the
  remaining CB-168 ambiguity: complete existing hosted installs now visibly say
  they run the upgrade lifecycle and refresh the dashboard, while install-time
  repo-state migrations that do not route through upgrade still force the
  shell-facing dashboard refresh before closeout. Existing consumers need no
  source-truth migration beyond normal v0.1.14 managed runtime adoption,
  registered repo-state migration execution, and the forced dashboard refresh.
- The matching Casebook/browser assessment for marker
  `migration-observer:0.1.14:browser-surfaces:4b2b74b01c2e` records the same
  CB-168 settlement in governed memory: the product renderer/refresh contract,
  not a local generated bundle edit, owns post-upgrade dashboard version truth.
  Existing consumers receive the behavior through upgrade/install dashboard
  refresh and do not need a bespoke Casebook source migration.
- The owned-surface refresh after that CB-168 source-truth update is covered by
  `migration-observer:0.1.14:browser-surfaces:3de239b5f3e2` and
  `migration-observer:0.1.14:install-managed-assets:81414558e1eb`. It updates
  generated Casebook, Radar, Registry, and bundled shell surface mirrors only;
  existing consumers still rely on the normal v0.1.14 dashboard refresh and
  install-managed asset adoption rather than a custom data migration.
- The source-local Registry refresh after component forensics reconciliation for
  marker `migration-observer:0.1.14:browser-surfaces:2d323cc9b2f3` updates the
  rendered Registry payload from governed Registry truth. Existing consumers need
  no custom data migration beyond normal v0.1.14 dashboard refresh.
- The post-restore generated surface settlement for markers
  `migration-observer:0.1.14:browser-surfaces:0dbe8cc13855` and
  `migration-observer:0.1.14:install-managed-assets:50b82d75fe4f` keeps the
  post-release dashboard/version repair scoped to the relevant shell, Radar,
  Atlas, Registry, and Casebook generated assets after broad Compass runtime
  history churn was removed. Existing consumers need no custom data migration
  beyond normal v0.1.14 dashboard refresh and managed asset adoption.
- The hosted install fallback release-spotlight repair for CB-169 is covered by
  `migration-observer:0.1.14:operator-cli-contracts:9871cf63f2ba` and
  `migration-observer:0.1.14:browser-surfaces:537ae469ce88`. The generated
  hosted installer now captures the previous active version before stale-state
  cleanup, passes it into compact install, and the install CLI repairs
  activation history plus writes `release-upgrade-spotlight.v1.json` before the
  shell-facing dashboard refresh. Existing consumers need no source-truth
  migration; upgrade-like install fallback paths preserve the release popup,
  while true first installs stay quiet.
- The Radar/browser settlement after recording CB-169 is covered by
  `migration-observer:0.1.14:browser-surfaces:2ee6238bab31` and
  `migration-observer:0.1.14:install-managed-assets:6aad0d78490e`. These are
  generated Radar and bundle mirror updates from the completed assessment above;
  existing consumers receive them through normal v0.1.14 dashboard refresh and
  managed asset adoption with no custom source migration.
- The sync-force recovery and latency hardening for CB-168 is covered by
  `migration-observer:0.1.14:operator-cli-contracts:241615c298f2`,
  `migration-observer:0.1.14:browser-surfaces:2de7b3690a67`, and
  `migration-observer:0.1.14:install-managed-assets:d37ada8eb939`. The CLI
  contract change makes `odylith sync --force` the explicit selected-plan dirty
  overlap acknowledgement, the browser-surface change batches Compass, Radar,
  Registry, Casebook, and shell rendering with Registry reusing the current
  Compass runtime summary, and the install-managed asset change is the generated
  bundle mirror of those settled surfaces. Existing consumers need no bespoke
  source-truth migration beyond the registered v0.1.14 migrations, normal
  managed asset adoption, and the now-functional `odylith sync --repo-root . --force`
  recovery path after upgrade/migration.
- The owned-governance refresh hardening is covered by
  `migration-observer:0.1.14:operator-cli-contracts:25d43cf0c817`,
  `migration-observer:0.1.14:operator-cli-contracts:9c3ed313cf38`,
  `migration-observer:0.1.14:public-docs-and-release-guidance:95aa48afbc77`,
  `migration-observer:0.1.14:browser-surfaces:72933f5c7e93`, and
  `migration-observer:0.1.14:install-managed-assets:f5544969ec49`. The runtime
  contract now refreshes Radar, Registry, Atlas, Casebook, and Compass immediately
  after owned governance mutations, with greenfield apply batching per-surface
  refreshes to avoid per-record render cost. The second operator-contract marker
  covers the final CLI handoff wording change from "refresh" to "reload browser
  tab" so operators do not confuse generated-surface refresh with browser reload.
  Public docs and generated bundle mirrors changed only to keep the operator copy and shipped browser assets aligned.
  Existing consumers need no bespoke source-truth migration; upgrading to v0.1.14
  or later gets the authoring/runtime behavior, and existing generated surfaces are
  refreshed through the normal dashboard/sync refresh path.
- The brutal QA hardening pass is covered by
  `migration-observer:0.1.14:public-docs-and-release-guidance:acb704a4d275`,
  `migration-observer:0.1.14:browser-surfaces:2cd63ac83fd8`, and
  `migration-observer:0.1.14:install-managed-assets:8a740f0e37f9`. The pass
  keeps Benchmark formal-model docs GitHub-safe, tightens Compass failed-brief
  fallback so provider failures retain the last ready brief while quiet scoped
  windows stay truthful, and regenerates the shipped browser/bundle assets from
  product renderers. Existing consumers need no bespoke source-truth migration;
  upgrade, managed asset adoption, and dashboard refresh apply the browser and
  documentation fixes.
- The host-neutral startup and shell-cheatsheet hardening is covered by
  `migration-observer:0.1.14:guidance-and-skills:21cdcaafabc1`,
  `migration-observer:0.1.14:operator-cli-contracts:425798d4b69d`,
  `migration-observer:0.1.14:browser-surfaces:078031117cb6`,
  `migration-observer:0.1.14:browser-surfaces:39484747861d`,
  `migration-observer:0.1.14:install-managed-assets:48e232bef174`, and
  `migration-observer:0.1.14:install-managed-assets:4782e24d1e80`. The CLI
  keeps plain `odylith start` compact while host packet consumers request
  `--json`, shared host summary logic collapses narrowing/fallback packet
  internals into a human target request, managed guidance bans chat-visible
  "Startup fell back" narration across supported coding agents, and the shell
  cheatsheet refresh adds release/program prompts to checked-in and bundled
  browser assets. Existing consumers need no bespoke source-truth migration;
  normal v0.1.14 managed guidance adoption and dashboard refresh apply the
  host-summary, CLI, shell, and bundle changes.
- The sync hot-path decomposition is covered by
  `migration-observer:0.1.14:operator-cli-contracts:da1177e62411` and
  `migration-observer:0.1.14:browser-surfaces:b4ddee9276b9`. The pass moves
  sync-only surface batching and generated-output git status helpers into
  focused runtime modules while preserving the existing `odylith sync` command
  contract, generated-output target list, and dashboard surface render order.
  Existing consumer installs need no source-truth migration; upgrade adoption
  gets the refactored runtime code and existing generated surfaces continue to
  refresh through the same sync/dashboard paths.
- The post-QA Radar and Casebook rendered-surface settlement is covered by
  `migration-observer:0.1.14:browser-surfaces:017861c55f14` and
  `migration-observer:0.1.14:install-managed-assets:e8b797046465`. The pass
  refreshes the owned browser surfaces after the source-truth assessment and
  host-neutral Casebook wording changed. Existing consumer installs need no
  bespoke source-truth migration; dashboard/sync refresh will regenerate those
  surfaces under the same installed renderer contract.
- The v0.1.15 release-integrity pass is covered by
  `migration-observer:0.1.15:operator-cli-contracts:446b97fb4045`,
  `migration-observer:0.1.15:public-docs-and-release-guidance:af873a74f56b`,
  `migration-observer:0.1.15:browser-surfaces:ae313258120f`, and
  `migration-observer:0.1.15:install-managed-assets:404087092989`. The pass
  aligns source, package, product pin, bundled pin, security docs, release
  notes, release CLI help, Compass fallback status copy, Radar/Compass release
  targeting, and generated surface mirrors under the `0.1.15` target. Existing
  consumers need no bespoke source-truth migration beyond the registered
  historical migrations, the install/upgrade dashboard refresh, and the normal
  managed asset adoption path; historical 0.1.10 through 0.1.14 installs are
  still validated through the release rehearsal matrix before publication.
- The final v0.1.15 post-sync rendered-payload settlement is covered by
  `migration-observer:0.1.15:browser-surfaces:43a7e21038d9` and
  `migration-observer:0.1.15:install-managed-assets:84934535f042`. The pass
  binds the release assessment to the exact generated Atlas, Casebook, Compass,
  Radar, Registry, and shell payloads emitted after `odylith sync --force`.
  Existing consumers need no additional source-truth migration; upgrade and
  forced sync converge installed generated surfaces to this payload contract.
- The v0.1.15 greenfield Tribunal and governed-artifact hardening pass is
  covered by `migration-observer:0.1.15:guidance-and-skills:ad47eeee311f`,
  `migration-observer:0.1.15:operator-cli-contracts:7844f71bd458`,
  `migration-observer:0.1.15:public-docs-and-release-guidance:c8276a3cb8e8`,
  `migration-observer:0.1.15:browser-surfaces:a855f8659a6c`,
  `migration-observer:0.1.15:browser-surfaces:30d9efac0b2f`, and
  `migration-observer:0.1.15:install-managed-assets:c6d00f4dc129`. The pass
  makes greenfield proposals and routine governed Radar, Registry, Atlas, and
  Casebook writes fail closed on deterministic Tribunal posture checks covering
  domain risk, security posture, compliance/policy posture, ownership, proof,
  and traceability before source truth changes. Existing consumers need no
  destructive migration: the stricter checks apply only to future CLI-owned
  writes, while existing governed records remain readable and generated
  dashboards converge through normal sync/dashboard refresh and managed asset
  adoption.
- The v0.1.15 benchmark formal-model rendering-contract documentation repair is
  covered by `migration-observer:0.1.15:public-docs-and-release-guidance:8212c7c68290`
  and `migration-observer:0.1.15:public-docs-and-release-guidance:c330d3a0402c`
  and `migration-observer:0.1.15:public-docs-and-release-guidance:084a4abb2237`.
  The pass adds reviewer-readable public interpretation text for benchmark
  report rendering and does not change installed runtime data, repo-owned
  governance truth, or managed host assets. Existing consumers need no bespoke
  migration; normal release-note/docs publication and managed asset adoption are
  sufficient.
- The v0.1.15 Radar post-refresh generated-surface settlement is covered by
  `migration-observer:0.1.15:browser-surfaces:11976f5ea60e` and
  `migration-observer:0.1.15:install-managed-assets:121a792a1657`. The pass is
  the rendered Radar browser payload plus bundled managed mirror emitted after
  the benchmark documentation and migration-observer source assessment changed.
  Existing consumers need no bespoke source-truth migration: upgrade, normal
  managed asset adoption, and `odylith sync`/dashboard refresh converge the
  installed Radar surface to the same renderer output.
- The v0.1.15 Casebook detail empty-state polish is covered by
  `migration-observer:0.1.15:browser-surfaces:99b653b0e082` and
  `migration-observer:0.1.15:install-managed-assets:fe7abb4cf478`. The pass
  makes the Odylith Agent Learnings section structurally stable even when a bug
  has no captured agent guidance yet, then refreshes the checked-in Casebook
  browser payload and bundled managed mirror from the product renderer.
  Existing consumers need no bespoke data migration: existing bug records remain
  readable, while upgrade, managed asset adoption, and dashboard refresh
  converge installed Casebook views to the same empty-state contract.
- The v0.1.15 Casebook spec and Registry surface alignment is covered by
  `migration-observer:0.1.15:public-docs-and-release-guidance:801216e122ce`,
  `migration-observer:0.1.15:browser-surfaces:e2a0ea479a38`, and
  `migration-observer:0.1.15:install-managed-assets:1c13fad1e9fc`. The pass
  records the agent-learning empty-state contract in the Casebook component
  spec, refreshes Registry and delivery-intelligence projections, and keeps the
  installed browser/bundle mirrors derived from source truth. Existing consumers
  need no bespoke data migration: the spec text is maintainer-facing governance
  truth, and installed Registry/Casebook surfaces converge through normal
  managed asset adoption plus dashboard refresh.
- The v0.1.15 brutal QA and greenfield-create release-path hardening pass is
  covered by `migration-observer:0.1.15:guidance-and-skills:c721d0b90037`,
  `migration-observer:0.1.15:operator-cli-contracts:259dfd9e1274`,
  `migration-observer:0.1.15:public-docs-and-release-guidance:6507977368e3`,
  `migration-observer:0.1.15:browser-surfaces:81b6e1ae22d0`, and
  `migration-observer:0.1.15:install-managed-assets:e12331350655`. The pass
  binds the final managed guidance, CLI contract, docs/release wording,
  Compass/Radar/Atlas browser surfaces, install-managed bundle assets, and
  hotfile cleanup to the exact changed source contents that shipped after the
  end-to-end fresh-repo greenfield journey was hardened. Existing consumers
  need no destructive data migration: upgrade adoption installs the managed
  guidance/asset updates, future greenfield proposals use the apply-ready
  runtime contract, and normal dashboard/sync refresh converges generated
  browser surfaces.
- The final browser-source hotfile cleanup for that same v0.1.15 QA pass is
  covered by `migration-observer:0.1.15:browser-surfaces:6fb5ceb00199`. The
  cleanup deduplicates Atlas workstream-list normalization and keeps Compass
  critical-bug timeline status handling within the pinned hotfile budget without
  changing installed data shape. Existing consumers need no migration beyond
  normal upgrade adoption and dashboard/sync refresh.
- The post-sync rendered-surface settlement for the same v0.1.15 QA pass is
  covered by `migration-observer:0.1.15:browser-surfaces:5756d08f1176`. The
  final fingerprint binds the refreshed Atlas, Casebook, Compass, Radar, and
  Registry browser payload set plus the browser-source cleanup to a completed
  consumer migration assessment. Existing consumers still need no bespoke data
  migration; normal upgrade adoption and dashboard/sync refresh converge the
  installed surfaces.
- The v0.1.15 greenfield architecture-diagram suite hardening pass is covered by
  `migration-observer:0.1.15:browser-surfaces:32f36ad50bff` and
  `migration-observer:0.1.15:browser-surfaces:1bca44045b6c` plus
  `migration-observer:0.1.15:install-managed-assets:e1ab4be0a00f`. The pass
  deepens greenfield Atlas output from a thin starter diagram set into a
  multi-view architecture suite, refreshes the governed browser surfaces and
  bundled managed dashboard mirrors, records the final proof-evidence refresh,
  and keeps proposal writes confirmation gated through the same greenfield
  Tribunal. Existing consumers need no destructive or bespoke data migration:
  existing greenfield records remain readable, while upgrade adoption and
  dashboard/sync refresh converge installed generated surfaces and managed
  assets to the richer diagram proposal contract.
- The v0.1.15 greenfield project-first UX hardening pass is covered by
  `migration-observer:0.1.15:guidance-and-skills:5ca274eb23df`,
  `migration-observer:0.1.15:public-docs-and-release-guidance:83dd374589cf`,
  `migration-observer:0.1.15:browser-surfaces:23db7fd0ca24`, and
  `migration-observer:0.1.15:install-managed-assets:5291a3c4b08e`. The pass
  adds a canonical `project_brief` with direction options and
  coding-readiness gates, updates managed guidance/docs, refreshes the browser
  surfaces and bundle mirrors, and keeps existing consumer governance truth
  readable. Existing installs need no destructive migration; normal upgrade
  adoption plus dashboard/sync refresh converges the new project-first
  proposal and handoff UX.
- The v0.1.15 greenfield component-spec bespoke hardening pass is covered by
  `migration-observer:0.1.15:operator-cli-contracts:aed74c9a51d8`,
  `migration-observer:0.1.15:browser-surfaces:7bed0ef171a8`, and
  `migration-observer:0.1.15:install-managed-assets:c46b34c03c1d`. The pass
  changes future greenfield Registry candidate-spec wording and component
  handoff selection so component dossiers carry component-owned boundaries,
  outside-boundary exclusions, collaborators, failure modes, proof, and the
  most specific child workstream instead of copied project posture. Existing
  consumer repos need no destructive migration: already-written component specs
  remain repo-owned truth, future greenfield apply runs use the sharper
  generator, and upgrade plus dashboard/sync refresh converges generated
  Registry/Radar/Compass browser surfaces and bundle mirrors.
- The v0.1.15 greenfield component-spec topology tightening pass is covered by
  `migration-observer:0.1.15:operator-cli-contracts:dc5245ee5acc` and
  `migration-observer:0.1.15:browser-surfaces:7d4664249c0d`. The pass keeps
  Registry dossiers from inheriting project-wide topology by binding future
  greenfield components to their primary child workstream, component-authored
  proof rows, component-local Tribunal posture, and non-project-level diagrams
  only. Existing consumer repos need no destructive migration: already-written
  Registry specs remain repo-owned truth, and future `odylith greenfield apply`
  plus normal Registry/Radar/Atlas/Compass refreshes converge the stricter
  component-local rendering contract.
- The v0.1.15 greenfield project-first UX deepening pass is covered by
  `migration-observer:0.1.15:browser-surfaces:1ad246b31c00`. The pass changes
  generated proposal/apply browser-facing payloads and shell-rendered HTML so
  future greenfield sessions show deeper project intelligence, design-board
  sections, customization examples, and a no-source-edits-until-plan handoff
  before implementation lanes. Existing consumer repos need no destructive
  migration: repo-owned greenfield records stay intact, upgraded runtimes emit
  the deeper UX for future proposals, and normal dashboard refresh converges
  generated Radar/Registry/Atlas/Compass surfaces.
- The v0.1.15 greenfield applied-Radar semantics hardening pass is covered by
  `migration-observer:0.1.15:browser-surfaces:0abf1a7c96b4`. The pass refreshes
  generated Radar/Registry/Atlas/Compass/Casebook surfaces after traceability
  writer changes that preserve structured risks, open questions, dependencies,
  rollout stages, and punctuation in newly applied greenfield Radar records.
  Existing consumer repos need no destructive migration: already-authored
  governance source remains repo-owned truth, while future `greenfield apply`
  runs write cleaner Radar records and normal dashboard/sync refresh converges
  generated browser surfaces.
- The v0.1.15 greenfield Atlas UX explanation pass is covered by
  `migration-observer:0.1.15:browser-surfaces:030d33c939e1`. The pass refreshes
  generated Radar/Registry/Atlas/Compass/Casebook surfaces after default
  greenfield proposals began emitting per-diagram review focus, operator
  question, proof gate, and annotated Mermaid diagram sources. Existing
  consumer repos need no destructive migration: previously applied Atlas
  source remains repo-owned truth, while future proposals and normal
  dashboard/sync refresh converge generated browser surfaces to the clearer
  architecture-review UX.
- The v0.1.15 startup target-recognition hardening pass is covered by
  `migration-observer:0.1.15:operator-cli-contracts:b196c5a54b60` and
  `migration-observer:0.1.15:browser-surfaces:c60b6a7c7415`, with the final
  focused-helper extraction covered by
  `migration-observer:0.1.15:browser-surfaces:c423443a7fa4`. The pass changes
  the `odylith start` operator transcript and startup packet intake: unquoted
  existing file paths and trusted planned new files become explicit startup
  targets, successful bootstrap output prints the compact recognized target,
  and untrusted planned suffixes remain rejected. Existing consumer repos need
  no source-truth migration; upgrade adoption supplies the sharper startup
  CLI/runtime behavior, and the generated Radar/Registry/Atlas/Compass/Casebook
  surfaces converge through normal dashboard/sync refresh.
- The v0.1.15 engine-integrity and execution-benchmark route hardening pass is
  covered by `migration-observer:0.1.15:operator-cli-contracts:a8504a4c60ea`,
  `migration-observer:0.1.15:browser-surfaces:bfc31956720b`, and
  `migration-observer:0.1.15:install-managed-assets:8afd5be2970e`. The pass
  adds the `odylith validate engine-integrity` CLI contract, expands the
  capability map for topology, taxonomies/FSMs, operator UX, and greenfield
  creation, records `CB-188` for the fixed quick execution-engine benchmark
  routing regression, records `CB-189` for the remaining quick-lane secondary
  efficiency hold, and refreshes Casebook/Radar browser payloads plus their
  managed bundle mirrors. Existing consumer repos need no bespoke data
  migration: upgrade adoption supplies the new validator/runtime route, future
  quick execution-engine benchmarks stay in the local packet lane, and normal
  dashboard/sync refresh converges generated surfaces and installed mirrors;
  efficiency claims must still cite the live benchmark status until `CB-189`
  closes.
- The v0.1.15 Atlas freshness settlement for that same engine-integrity pass is
  covered by `migration-observer:0.1.15:browser-surfaces:55e6f22469f6` and
  `migration-observer:0.1.15:install-managed-assets:4d84a40bb751`. The pass
  refreshes the final stale Atlas catalog fingerprint and rerenders the Atlas
  browser payload plus managed bundle mirror without changing Mermaid topology
  source. Existing consumers need no bespoke source-truth migration: upgrade
  adoption and normal Atlas/dashboard refresh converge installed browser assets
  to the fresh 44-diagram catalog.
- The v0.1.15 Radar deeplink reveal-filter repair is covered by
  `migration-observer:0.1.15:browser-surfaces:55c4e2e519b3`,
  `migration-observer:0.1.15:browser-surfaces:a345f81c5e3a`, and
  `migration-observer:0.1.15:install-managed-assets:fdd68873d309`. The pass
  fixes explicit Compass-to-Radar workstream deeplinks so Radar clears stale
  visibility filters when the requested workstream is outside the currently
  selected Radar view. Existing consumers need no data migration: upgrade
  adoption supplies the corrected Radar renderer, already-owned Radar workstream
  truth remains unchanged, and normal dashboard/sync refresh regenerates the
  browser and installed bundle assets.
- The v0.1.15 greenfield project-intelligence deepening pass is covered by
  `migration-observer:0.1.15:guidance-and-skills:64364569b086`,
  `migration-observer:0.1.15:browser-surfaces:f469b98318dc`, and
  `migration-observer:0.1.15:install-managed-assets:765b855989ca`, with final
  generated-surface settlement covered by
  `migration-observer:0.1.15:browser-surfaces:2d3918fcc7c7` and
  `migration-observer:0.1.15:install-managed-assets:79060c177fba`. The pass
  adds the canonical `project_intelligence` proposal object, renders it before
  the project brief and backlog, persists it into the parent Radar workstream,
  and updates managed greenfield guidance plus bundle mirrors so Codex, Claude
  Code, and direct CLI users review the same project-first control surface
  before any child workstream technical plan or source edit. Existing consumer
  repos need no destructive migration: historical greenfield records remain
  readable, while future proposal/create runs and normal dashboard/sync refresh
  converge installed surfaces to the deeper project-first UX.
- The v0.1.15 explicit invalidation and ownership pass is covered by
  `migration-observer:0.1.15:guidance-and-skills:0df65445f86d` and
  `migration-observer:0.1.15:install-managed-assets:a18d34fb8a8f`. The pass is
  additive: future greenfield proposal JSON and Radar workstream sections now
  carry explicit invalidation rules, first-class scope, and ownership maps,
  while existing consumer governance truth remains valid. Upgrade adoption only
  refreshes managed guidance/bundle assets; proposal/create remains
  confirmation-gated before new project truth is written.
- Final v0.1.15 explicit-invalidation surface settlement is covered by
  `migration-observer:0.1.15:browser-surfaces:b4d20ce668d5` and
  `migration-observer:0.1.15:install-managed-assets:dea842f8c91c`, with the
  final post-refresh fingerprints assessed under
  `migration-observer:0.1.15:browser-surfaces:77f6752a8e62` and
  `migration-observer:0.1.15:install-managed-assets:4590f557c3cd`. The pass
  only refreshes rendered governance dashboards and shipped HTML bundle copies
  from governed source truth; existing consumer Radar, Registry, Atlas,
  Casebook, and Compass source records are not rewritten by upgrade adoption.
