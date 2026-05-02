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
