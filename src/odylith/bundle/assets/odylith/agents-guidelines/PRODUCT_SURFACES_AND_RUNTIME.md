# Product Surfaces And Runtime

## CLI Contract
- The supported operator contract is the `odylith` CLI.
- Use `odylith sync`, `odylith context-engine`, `odylith benchmark`, `odylith compass ...`, and `odylith atlas ...` as the public workflow.
- Do not default back to removed local wrapper modules when the CLI already owns the surface.

## Installed Consumer Lane
- `./.odylith/bin/odylith` runs Odylith on Odylith's managed runtime.
- Consumer repo code still validates on the consumer repo's own toolchain.
- The shipped bundle covers the installed consumer contract only.

## Coding Standards
- Follow [CODING_STANDARDS.md](./CODING_STANDARDS.md) for the canonical Odylith coding standards, including file-size discipline, refactor-first posture, documentation, reuse, robustness, and focused validation expectations.

## Runtime, Write, And Validation Boundaries
- Runtime boundary: the invoked Odylith executable decides which interpreter runs Odylith itself.
- Write boundary: interpreter choice does not decide which repo files the agent may edit.
- Validation boundary: the target repo's own toolchain proves target-repo application behavior; Odylith CLI proves Odylith-owned runtime, governance, and surface contracts.
- Do not collapse those three boundaries into one generic "which Python am I using" question.
- In consumer repos, diagnosing an Odylith product issue does not authorize local writes under `odylith/` or `.odylith/`; hand off upstream evidence unless the operator explicitly authorizes mutation.

## Surface Ownership And Generated UI Contract
- Odylith governance surfaces are product-owned and should be refreshed through the CLI, not hand-run local renderer modules.
- Consumer agents may inspect Odylith governance surfaces to diagnose product issues, but refresh, repair, and sync flows stay write actions rather than neutral diagnostics when the target issue is Odylith itself.
- Keep one canonical HTML entrypoint per surface and externalize payload/bootstrap control into adjacent generated assets instead of reintroducing per-route HTML forks.
- The shared framework for that contract is `odylith.runtime.surfaces.dashboard_surface_bundle`.
- The contract stays intentionally narrow:
  - renderers keep their own DOM, CSS, and JS behavior
  - shared bootstrap only externalizes adjacent `*-payload.v1.js` and `*-app.v1.js` assets plus common UI/runtime primitives
  - visually identical cross-surface behavior should move into shared runtime helpers instead of being recopied per renderer
  - local `file:` opening must keep working without a web server
- Radar, Atlas, Compass, Registry, and Odylith are shell-owned child surfaces: direct opens should canonicalize back into `odylith/index.html` with the relevant tab/scope state preserved.
- Prefer diagram-pinned Atlas routes when available so cross-surface links land on reviewed Mermaid context instead of a generic workstream view.
- Canonical generated roots are:
  - `odylith/radar/`
  - `odylith/atlas/`
  - `odylith/compass/`
  - `odylith/registry/`
  - `odylith/runtime/`
  - `odylith/` for the shell
- Retired child-surface aliases are legacy outputs only and must never become active product architecture again.

## Refresh And Runtime Posture
- Odylith refresh defaults to `on-demand`, not a mandatory background daemon and not part of the normal hot path for every local coding loop.
- In consumer repos, the shell may show passive runtime-freshness warnings before commit time by reading existing local runtime state only; that notice must never start sync, never start background work, and never silently rewrite tracked `odylith/` truth.
- In consumer repos, autonomous Odylith fixes must not run `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, or `odylith dashboard refresh`; those mutate `odylith/` or `.odylith/` and belong to operator-authorized recovery flows.
- Plain `odylith sync --repo-root .` is the fast selective upkeep path.
- Use `odylith dashboard refresh --repo-root .` for the low-friction shell-facing refresh path, `odylith sync --repo-root . --force --impact-mode full` for a full write-mode refresh, `odylith sync --repo-root . --check-only` for a strict non-mutating gate, and `odylith compass watch-transactions` only when an explicitly continuous local loop is useful.
- Default local reasoning should auto-select the active Codex or Claude Code host when one is available; do not require separate endpoint keys or a hardcoded host-model override for the normal local path.
- Persist repeated local reasoning-provider choices in gitignored `.odylith/reasoning.config.v1.json`; environment variables remain per-process overrides on top of that local config.
- Treat Tribunal provider adapters as bounded tooling, not as ambient reuse of the current interactive desktop chat session.
- `odylith sync` and dashboard refresh must stay deterministic when the persisted Tribunal reasoning artifact is missing; do not block shell or delivery-intelligence refresh on opportunistic provider calls.
- When explicit Tribunal provider enrichment times out or loses transport during a run, disable provider enrichment for the remaining cases in that run and keep the queue deterministic rather than repeating the same stall case by case.

## Operator-Intelligence Split
- Odylith owns signal intake, posture, queue ranking, approval, and clearance.
- Tribunal owns deep reasoning and editorial engineering briefs.
- Remediator owns bounded packet compilation plus execution/delegation metadata.
- `reasoning_state` is a reasoning-depth/status signal; `packet_mode` is an execution-lane signal.
- `proof_routes` are the only deep-linkable proof contract. `evidence_refs` remain contextual evidence and must not become proof chips.
- The shell owns the top-level `Operator Inbox`; Odylith owns full queue/control-plane detail; Radar, Registry, Atlas, and Compass stay native to their own evidence instead of embedding shared intervention cards.

## Runtime Layers And Artifacts
- Odylith is the observer/control-plane surface: it owns signal intake, cheap correlation, queue ranking, approval state, clearance state, and the final operator-facing shell/CLI surface.
- Tribunal is the reasoning engine beneath Odylith: it turns ranked scopes into dossiers, runs actors, adjudicates disagreement, and emits one engineering brief plus systemic context.
- Remediator compiles an adjudicated prescription into a bounded correction packet when the action is reviewable, allowlisted, validated, and reversible.
- Canonical Odylith runtime artifacts are:
  - `odylith/runtime/posture.v4.json`
  - `odylith/runtime/reasoning.v4.json`
  - `odylith/runtime/delivery_intelligence.v4.json`
  - `odylith/runtime/decisions.v1.jsonl`
- Product-facing lifecycle terms are fixed:
  - `approval` means an operator authorized a packet
  - `clearance` means post-action success conditions were rechecked and passed
- Packet modes remain `deterministic`, `ai_engine`, `hybrid`, and `manual`.
- Case, outcome, and correction-packet contracts stay public and schema-backed; renderers and operators should rely on those runtime contracts instead of inventing local summary heuristics.

## Contract Evolution
- Odylith runtime and operator-intelligence contracts stay versioned and schema-backed under the product.
- When product semantics change materially, update the whole product boundary in the same change:
  - builders and writers
  - renderers and consumers
  - sync or autosync orchestration
  - tests
  - product docs and packaged guidance
- Preserve fail-closed behavior during contract migration:
  - deterministic fallback must still work
  - generated artifacts must still validate in strict check modes
  - duplicate or unsupported model-backed findings must be rejected before render
- Schema files remain versioned artifacts; authoring guidance should not fork their semantics into repo-local docs.

## Queue And Operator Readout Contract
- `case_queue[]` is the primary Odylith/Tribunal case lane and the shell preview lane.
- Queue visibility is advisory, not an execution grant. Unless the operator explicitly asks to work a queued backlog item or case, Odylith and agents must not start implementing it automatically just because it appears in `case_queue[]`, Radar, Compass, or shell queue previews.
- `systemic_brief` summarizes latent causes shared across current cases.
- Every scoped snapshot exposes a validated `operator_readout` payload containing:
  - `primary_scenario`
  - `secondary_scenarios`
  - `severity`
  - `issue`
  - `why_hidden`
  - `action`
  - `action_kind`
  - `proof_refs`
  - `requires_approval`
  - `source`
- Queue items also expose operator-facing `why_now`, `success_check`, `proof_highlights`, `live_reason`, and `next_surface`.
- Case queue rows expose identity, decision, brief, reasoning/execution state, proof routes, confidence, and selection rationale.
- Queue proof semantics are strict:
  - `proof_routes` are the canonical deep-linkable proof contract
  - generic `evidence_refs` must not be merged into `proof_routes`
  - missing proof routes fail closed rather than routing back to Odylith
- Queue selection semantics are explicit and auditable:
  - `selection_slot` distinguishes `scenario_coverage` from `priority_fill`
  - `selection_reason` explains why a case survived truncation
  - `selection_metrics` expose the scenario / severity / decision-debt inputs used for selection
  - `selection_score_band_size` makes large tie bands visible when `scope_id` order becomes the final stable tie-break
- Shared scenario taxonomy is fixed:
  - `unsafe_closeout`
  - `cross_surface_conflict`
  - `orphan_activity`
  - `stale_authority`
  - `false_priority`
  - `clear_path`
- Queue visibility and provider-focus semantics remain distinct:
  - `selection_summary.shown_scope_count` is the number of eligible cases rendered in Odylith
  - `selection_summary.provider_focus_count` and `selection_summary.outside_focus_count` describe the provider-focus subset versus the rest of the shown queue
- `selection_summary.truncated_count` is reserved for truly hidden or paginated queue entries
- `case_queue[*].provider_focus` records whether a case sat inside the provider-focus subset
- deterministic fallback rows explain themselves through `deterministic_reason` and `deterministic_reason_detail`

## Compass Brief Runtime
- Compass standup briefs should read like a concise engineering standup, not like a generic dashboard summary.
- The default live refresh should warm the primary 24h global standup brief first; secondary global windows may reuse cache or stay deterministic until they are warmed, so normal sync does not block on every window.
- The local brief cache is an acceleration layer only; cache fingerprints must rotate when narration semantics change, and stale warmed briefs must not imply current traction without freshness evidence.
- Exact cache hits may reuse directly, and bounded same-scope fallback is acceptable only when live refresh fails or is intentionally deferred.
- If the provider returns no valid brief after bounded retry and repair, the standup panel must stay fail-closed.
- Provider-output transport quirks such as missing sidecar files or transient stdout/file disagreements should degrade gracefully when the same schema-valid payload is still recoverable.

## Shared Surface Primitives
- Dashboard detail-pane buttons and linked chips must use the shared dense detail-action primitives instead of renderer-local button shells.
- Dashboard list/detail workspaces must use the shared split-pane layout primitives; treat the `330px-420px` left selector rail as the canonical sibling-surface width contract.
- Dashboard detail disclosures must use one shared triangle/caret affordance instead of renderer-local `Show`, `Expand`, or `Collapse` button copy.
- Dashboard disclosure headings must use shared typography tiers instead of mixing card-title, utility-heading, and button-label scales in one detail pane.
- Tooling-shell navigation tabs must use the shared shell-tab primitive instead of renderer-local active/inactive tab contracts.
- Keep shared tooltip, date/time, chip/button, and operator-readout behavior in the Odylith runtime surface primitives instead of renderer-local copies.
- Keep displayed dates and the related day-bucket arithmetic on the shared dashboard time helpers instead of mixing local UTC slicing with Pacific-normalized display.
- Do not reintroduce renderer-local compact chip/button styling, tooltip runtimes, or proof-link shells that fork the shared surface contract.
- For alignment, spacing, overflow, symmetry, and similar visual UX refinements on Odylith surfaces, verify the rendered result in headless Chromium before closeout; CSS or DOM inspection alone is not enough.
- When a visual bug is fixed, prefer adding or extending a Playwright/browser assertion in the surface browser suites so the layout contract stays proved at the rendered page level.

## Runtime Cadence And Overhead
- Cheap observer polling stays adaptive and fingerprint-based.
- The default active observer cadence is `30s`, with idle backoff up to `300s`.
- Tribunal reasoning runs only when a case dossier fingerprint changes or leverage/uncertainty thresholds justify it.
- Missing Tribunal cache during sync or shell refresh is not a license to start an implicit provider-backed reasoning pass; use deterministic Tribunal fallback there and keep explicit provider use on dedicated reasoning flows.
- Systemic synthesis runs more selectively still, and remediation only proceeds after explicit approval.
- The default local loop is `sync + on-demand`; continuous watchers are optional local accelerators, not required background truth.
