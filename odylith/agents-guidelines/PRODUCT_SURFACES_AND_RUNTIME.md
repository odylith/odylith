# Product Surfaces And Runtime

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

## CLI Contract
- The supported operator contract is the `odylith` CLI.
- Use `odylith sync`, `odylith context-engine`, `odylith benchmark`, `odylith compass ...`, and `odylith atlas ...` as the public workflow.
- Do not default back to removed local wrapper modules when the CLI already owns the surface.

## Project-Root Host Assets
- Odylith's managed project-root host assets are now split by host family:
  `.claude/` for Claude Code, `.codex/` for Codex CLI project config, hooks,
  and custom agents, and `.agents/skills/` for Codex repo-scoped skill shims.
- The installer refreshes those assets through one shared project-root bundle
  sync path; do not invent a second host-specific install pipeline for Codex.
- Codex only activates the checked-in `.codex/` layer for trusted projects, so
  the Codex project-asset contract is partly install-time and partly host trust
  posture.
- Keep `AGENTS.md` canonical across hosts. Checked-in host assets reinforce the
  shared repo contract; they do not replace it.
- The current routed `spawn_agent` host-tool contract and the checked-in Codex
  CLI project assets are separate layers. Project agents in `.codex/agents/`
  are not yet router-selectable `agent_type` values through this integration.

## Lane Matrix
- Consumer lane:
  - `./.odylith/bin/odylith` runs Odylith on Odylith's managed runtime
  - consumer repo code still validates on the consumer repo's own toolchain
  - `source-local` is unsupported
- Product-repo maintainer mode:
  - pinned dogfood posture:
    - default self-host posture
    - proves the shipped pinned runtime
    - not the lane for executing unreleased live `src/odylith/*` changes
  - detached `source-local` posture:
    - explicit maintainer-only override
    - allowed to execute live unreleased `src/odylith/*` changes
    - intentionally release-ineligible
  - dashboard header freeze:
    - the dashboard shell header is a non-negotiable frozen contract in both
      maintainer postures
    - do not add, remove, rename, reorder, restyle, repurpose, or otherwise
      tamper with header labels, text, buttons, controls, badges, tabs,
      version readouts, or any other UI artifact there
    - keep onboarding, release-note, maintainer-note, and adjacent shell UX
      affordances out of the header
  - branch safety posture:
    - the Git `main` branch is read-only for authoring in this maintainer lane
    - never work directly on `main`; this rule is non-negotiable
    - if the current branch is `main`, create and switch to a new branch before any code or tracked-file edit
    - if work is already on a non-`main` branch, keep using that branch
  - source-file discipline posture:
    - follow [CODING_STANDARDS.md](./CODING_STANDARDS.md) for the canonical Odylith coding standards, including file-size discipline, refactor-first posture, documentation, reuse, robustness, and focused validation expectations

## Observation And Proposal Contract
- `**Odylith Observation**` and `Odylith Proposal` are shipped product
  surfaces, not host-local flourishes. The same shared core must power them on
  Codex and Claude.
- The live mid-turn hot path for teaser, Observation, and Proposal belongs to
  the intervention engine. `Odylith Chatter` owns the broader narration
  posture and the final `Odylith Assist:` closeout instead of recomputing the
  hook-time surface.
- The lane may change what evidence is available or whether apply is allowed,
  but it must not fork the labels, confirmation phrase, or overall markdown UX
  across detached `source-local`, pinned dogfood, and consumer pinned-runtime
  posture.
- The shipped confirmation phrase is fixed:
  `apply this proposal`
- Render that phrase as a quiet trailing sentence such as
  `To apply, say "apply this proposal".`
  rather than as the loudest visual element in the block.
- The shipped default voice is also fixed for this release: friendly,
  delightful, soulful, insightful, simple, clear, accurate, precise, and
  above all human. Future voice packs may tune the voice later, but current
  runtime and guidance must not drift into templated or mechanical copy.
- The shipped markdown shape matters too: Observation should look like
  `Odylith Assist` and stay to one short labeled line. Proposal should look
  like a short ruled block with one calm lead line beginning `Odylith Proposal:`,
  a few bullets, and one quiet confirmation line.
- The same intervention moment must keep one stable session-local identity
  across prompt, stop, and edit/bash checkpoints. Do not let a later hook
  make the same moment feel like a fresh branded interruption just because it
  added changed-path or assistant-summary evidence.
- Checkpoint hooks carry two surfaces on purpose:
  - hidden developer context with the full Observation/Proposal/Assist bundle
    for continuity into the next model turn
  - a visible checkpoint beat for the user when Observation or Proposal is
    actually earned
- The primary visible intervention moment is the edit/bash checkpoint, not the
  stop fallback. Stop may still recover a late Observation or a closeout
  Assist line, but the product should not make users wait until stop to feel a
  live intervention.
- Success-only governance refresh receipts must not drown out an earned
  Observation or Proposal. Keep routine success quiet when a stronger live beat
  exists; surface refresh status only when it failed, skipped, or when no live
  intervention was earned.
- Rich reasoning signature and continuity identity are intentionally distinct.
  Odylith may reason from more evidence as the moment matures, but the visible
  thread should still feel like one evolving thought.
- A later hook may suppress a duplicate Observation and still surface the
  first eligible Proposal for that same moment. Do not require Proposal to
  re-announce the already-earned Observation just to appear.
- Missing launcher-backed anchor resolution is not permission to silence a
  real prompt-submit teaser. Degraded context narrowing may remove the anchor
  summary, but the earned intervention beat should still survive.
- If the user cannot tell in a breath why Odylith stepped in, or if the
  Proposal turns into a mini report, the UX has failed.
- Multiline Observation and Proposal markdown is part of the shipped product
  contract. Do not flatten those blocks into one-line summaries in stream
  events, Compass payloads, host surfaces, or regression fixtures.
- When showing those surfaces to humans in guidance, demos, or regression
  discussion, prefer rendered Markdown or plain prose. Do not wrap the product
  moment in fenced raw Markdown unless you are debugging the raw source text.
- Demo copy must carry real governed meaning. Decorative filler lines are not
  harmless polish; they blur the interjection and make the product feel fake.
- Preview-only proposals stay unappliable until every action in the bundle has
  a safe CLI-backed apply lane. Do not partially apply the supported subset of
  a richer proposal and call the contract satisfied.
- Preserve prompt memory across intervention lifecycle events and pending
  proposal state. Later host hooks must reason from the original human prompt
  when it exists, not from Odylith's own pending/applied summary strings.
- Empty or missing hook session ids must fall back to a stable host-local
  synthetic session token. Intervention runtime must never widen an empty
  session id into cross-session prompt or changed-path bleed.
- Observation and proposal reasoning must stay on the hot-path evidence cone:
  prompt excerpts, assistant summaries, changed paths, packet summaries,
  delivery snapshots, active governed refs, and existing local runtime or
  governance state. No wide repo search is allowed just to make the output
  sound smarter.

## Runtime, Write, And Validation Boundaries
- Runtime boundary: the invoked Odylith executable decides which interpreter runs Odylith itself.
- Write boundary: interpreter choice does not decide which repo files the agent may edit.
- Validation boundary: the target repo's own toolchain proves target-repo application behavior; Odylith CLI proves Odylith-owned runtime, governance, and surface contracts.
- Do not collapse those three boundaries into one generic "which Python am I using" question.
- In consumer repos, diagnosing an Odylith product issue does not authorize local writes under `odylith/` or `.odylith/`; hand off maintainer-ready evidence unless the operator explicitly authorizes mutation.

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
- In consumer repos, autonomous Odylith fixes must not run `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, or `odylith dashboard refresh`; those mutate `odylith/` or `.odylith/` and belong to operator- or maintainer-authorized recovery flows.
- In the Odylith product repo, keep the shell frozen for benchmark and proof posture: no passive live-refresh probe, no hidden dashboard heating, and no benchmark-lane-only convenience behavior.
- Plain `odylith sync --repo-root .` is the fast selective upkeep path.
- Use `--odylith-mode refresh` for a full refresh, `--odylith-mode check` for a strict non-mutating gate, and `odylith compass watch-transactions` only when an explicitly continuous local loop is useful.
- Default local reasoning should auto-select the active Codex or Claude Code host when one is available; do not require separate endpoint keys or a hardcoded host-model override for the normal local path.
- Persist repeated local reasoning-provider choices in gitignored `.odylith/reasoning.config.v1.json`; environment variables remain per-process overrides on top of that local config.
- Treat Tribunal provider adapters as bounded tooling, not as ambient reuse of the current interactive desktop chat session.
- `odylith sync` and dashboard refresh must stay deterministic when the persisted Tribunal reasoning artifact is missing; do not block shell or delivery-intelligence refresh on opportunistic provider calls.
- When explicit Tribunal provider enrichment times out or loses transport during a run, disable provider enrichment for the remaining cases in that run and keep the queue deterministic rather than repeating the same stall case by case.
- In the product repo, pinned dogfood stays the default operator posture even when maintainers are editing source; switch to detached `source-local` only when the task actually needs live-source execution rather than shipped-runtime proof.

## Operator-Intelligence Split
- Odylith owns signal intake, posture, queue ranking, approval, and clearance.
- Tribunal owns deep reasoning and editorial maintainer briefs.
- Remediator owns bounded packet compilation plus execution/delegation metadata.
- `reasoning_state` is a reasoning-depth/status signal; `packet_mode` is an execution-lane signal.
- `proof_routes` are the only deep-linkable proof contract. `evidence_refs` remain contextual evidence and must not become proof chips.
- The shell owns the top-level `Operator Inbox`; Odylith owns full queue/control-plane detail; Radar, Registry, Atlas, and Compass stay native to their own evidence instead of embedding shared intervention cards.

## Runtime Layers And Artifacts
- Odylith is the observer/control-plane surface: it owns signal intake, cheap correlation, queue ranking, approval state, clearance state, and the final operator-facing shell/CLI surface.
- Tribunal is the reasoning engine beneath Odylith: it turns ranked scopes into dossiers, runs actors, adjudicates disagreement, and emits one maintainer brief plus systemic context.
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
- The canonical brief contract lives in [Briefs Voice Contract](../registry/source/components/briefs-voice-contract/CURRENT_SPEC.md).
- `LLM writes, local code thinks` is the governing implementation rule for
  Compass briefs.
- Compass standup briefs should read like a thoughtful maintainer talking to a teammate, not like a dashboard summary or executive memo.
- The only truthful brief source states are fresh `provider`, exact `cache`, or explicit `unavailable`.
- Deterministic fallback narration is retired. If the provider does not yield a valid brief and there is no exact same-packet validated cache entry, the standup panel must stay fail-closed.
- The local brief cache is an acceleration layer only. Cache fingerprints must rotate when narration semantics change, and stale warmed briefs must never imply current traction.
- Exact cache hits may reuse directly, but exact now means exact narration-substrate identity rather than raw packet identity. Non-exact cache replay is not allowed.
- Build a deterministic narration substrate locally before the provider call:
  top winner facts, hard section budgets, compact storyline/self-host fields,
  and prior accepted brief snapshot only.
- Prefer delta narration over full regeneration. The provider should update
  from changed winner facts and the prior accepted brief, not reread a giant
  packet.
- Call the provider only when the winner story moved materially. Freshness-only
  drift, non-winner summary churn, and exact substrate matches must stay local.
- Partial salvage is required. Keep valid global or scoped entries from a mixed
  bundle response and repair only the missing subset once.
- Record narration spend telemetry locally: input/output size, latency, repair
  count, salvage count, skip reason, failure kind, and provider code/detail.
- Global and scoped Compass narration should warm as one packet-level bundle.
  Do not reintroduce a second scoped provider queue or scope-by-scope provider
  fanout after refresh.
- Non-ready Compass brief states must stay explicit and clearly labeled; they
  must not silently impersonate a ready narrated brief for the selected scope
  or packet.
- `Copy Brief` should only appear when a real narrated brief is on screen.
- Whole-window coverage facts stay upstream evidence; Compass must not synthesize stock coverage bullets to fill the panel.
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
- Compass refresh should be push-first and daemon-first whenever possible:
  changed projection fingerprint first, daemon-held hot payload second, local
  rebuild only when the fingerprint actually moved.
- Tribunal reasoning runs only when a case dossier fingerprint changes or leverage/uncertainty thresholds justify it.
- Missing Tribunal cache during sync or shell refresh is not a license to start an implicit provider-backed reasoning pass; use deterministic Tribunal fallback there and keep explicit provider use on dedicated reasoning flows.
- Systemic synthesis runs more selectively still, and remediation only proceeds after explicit approval.
- The default maintainer loop is `sync + on-demand`; continuous watchers are optional local accelerators, not required background truth.
- For Compass specifically:
  - hot unchanged refresh should come from daemon-held in-memory state
  - shell-safe blocking refresh spends `0` foreground provider calls
  - live narration spend belongs to the background bundle lane only
