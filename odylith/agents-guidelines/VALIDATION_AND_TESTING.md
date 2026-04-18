# Validation And Testing

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

## Core Rule
- Prefer targeted validation, but when the change is Odylith-product-owned, test the public product boundary and the repo-integrated boundary instead of relying on removed local duplicates.
- Keep runtime boundary and validation boundary separate. The interpreter that runs Odylith is not automatically the interpreter that should validate the target repo's own code.

## Odylith-First Validation Loop
- Start open-ended or non-trivial validation work by grounding through Odylith `status`, `doctor`, `bootstrap-session`, `session-brief`, or `query`.
- Once the slice is explicit, use `status`, `impact`, `architecture`, `governance-slice`, `bootstrap-session`, and `context` as the grounded runtime lanes.
- Keep `query` inside the Odylith runtime as the lexical recall lane; do not replace first-pass validation discovery with host-native repo search.
- Check `status` or `doctor` before an explicit `serve`.
- Use focused `rg`, targeted pytest, and direct source reads only when Odylith cannot bound the invariant from the prompt or worktree, or explicitly recommended widening.

## Canonical Validation Bundles
- Risk-mitigation, traceability, component-registry, strict refresh, strict check, and Atlas render belong to the canonical Odylith proof lane.
- Use standalone strict-check paths for parity, pre-commit, and CI truth; warm daemons are acceleration only.
- If strict sync is blocked only by Mermaid freshness, repair that with `odylith atlas auto-update ...`, rerender Atlas, then rerun the strict gate.
- When governed surfaces change, review the rendered output after refresh rather than trusting raw payloads alone.

## Product Validation Expectations
- When changing backlog or plan lifecycle semantics, test all three truth-bearing states: active, parked, and done.
- When changing generated surfaces, validate the full generated bundle contract, not only the HTML shell.
- Child-surface regressions must preserve the shell-owned redirect/access contract for Radar, Atlas, Compass, Registry, and Odylith.
- Visual dashboard changes still need rendered review after regeneration; static HTML assertions do not replace looking at the generated surface.
- Provider-backed reasoning changes need the owning fail-closed contract checked in the same pass.
- Compass brief work follows [Briefs Voice Contract](../registry/source/components/briefs-voice-contract/CURRENT_SPEC.md): validate deterministic substrate building, exact substrate-cache reuse, provider-worthiness gating, fresh `provider`, exact `cache`, explicit `unavailable`, subset repair, bounded diagnostics, daemon hot reuse, and voice-truth rejection together.
- Commentary or closeout-contract changes need source, bundle, install, and benchmark-story regressions so ambient mid-task signals stay task-first, labeled `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` beats stay rare and earned, and any final `Odylith Assist:` note remains evidence-backed. Prefer `**Odylith Assist:**` when Markdown is available. Lead with the user win, keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual, link updated governance IDs inline only when they actually changed, name affected governance-contract IDs from bounded request or packet truth when no governed file moved, and tie concrete observed counts, measured deltas, or validation outcomes back to `odylith_off` or the broader unguided path. Silence is better than filler.
- Intervention visibility changes need delivery-ledger regressions too:
  `intervention-status` must prove static host readiness without a slow host
  probe, recent Compass events must preserve `delivery_channel` and
  `delivery_status`, and `visible-intervention` must still render plain
  Markdown that can be shown directly in chat.
- Guidance Behavior changes need both deterministic validator proof and
  benchmark-family proof. Use
  `odylith validate guidance-behavior --repo-root .` for corpus, guidance,
  host/lane, runtime-layer, platform end-to-end, bundle, and high-risk
  instruction checks, including live/source-bundle byte-parity for shipped
  consumer assets and the `hot_path_efficiency` domain that guards against
  avoidable session widening, projection-store opens, delivery-ledger reads,
  and host probes. Use
  `odylith benchmark --profile quick --family guidance_behavior` to prove the
  existing benchmark path selects only the `guidance_behavior` family without
  creating a separate public proof lane.
- Adaptive Agent Operating Character changes need credit-safe deterministic
  proof and benchmark-family proof. Use
  `odylith validate agent-operating-character --repo-root .` for hard laws,
  open-world pressure observations, stance vectors, ranked affordances,
  learning signals, host/lane parity, bundle mirrors, external-reference
  guards, and hot-path zero-credit counters. Use
  `odylith benchmark --profile quick --family agent_operating_character --no-write-report --json`
  for quick family proof. Full public or release claims still require proof
  profile benchmark evidence, matched `odylith_on` versus
  `raw_agent_baseline`, fairness intact, warm and cold profiles, and pinned
  dogfood runtime health.

## Coverage And Harness Rules
- Use the public Odylith repo when collecting Odylith-product coverage; the authoritative product package is `src/odylith`.
- Pre-commit and pytest harnesses must stay hermetic to maintainer-local Odylith reasoning overrides.
- Registry/component-spec fixtures must satisfy the same fail-closed feature-history plan-link contract as production specs.
- In consumer repos, validate consumer application code with the consumer repo's own `python`, `uv`, Poetry, Conda, or equivalent project toolchain even when Odylith commands ran through `./.odylith/bin/odylith`.
- In the Odylith product repo's maintainer mode, never make current-workspace code or tracked-file edits directly on `main`; if the current branch is `main`, create and switch to a new branch before the first edit, and if work is already on a non-`main` branch, keep using that branch.
- In the Odylith product repo's maintainer mode, use pinned dogfood validation to prove shipped-runtime behavior and detached `source-local` validation only when the slice intentionally exercises live unreleased `src/odylith/*`.
- In the Odylith product repo, `make dev-validate` is the explicit detached `source-local` validation lane for current unreleased workspace changes; `make release-preflight` remains the canonical clean-checkout release-proof lane.
- Guidance Behavior must stay lane-correct: consumer validation uses the
  installed repo-local launcher and diagnosis-first product-fix posture;
  pinned dogfood proves the shipped runtime in the product repo; detached
  source-local proof is maintainer-only for current unreleased source changes.
  Do not treat a source-local pass as consumer or shipped-runtime proof.

## Odylith-Specific Regression Families
- Odylith/Tribunal changes need explicit truthfulness regressions: provider validation, deterministic fallback, no fake ownership or semantic claims, and separation of reasoning from execution mode.
- Registry forensic-coverage changes need builder plus renderer regressions so evidence-channel states survive into generated payloads and UI.
- Odylith Context Engine changes need projection plus operator-surface regressions: impact, query, context, session packets, daemon lifecycle, ambiguity handling, and `full_scan_recommended` fail-closed behavior.
- Governed sync/projection reuse changes need provenance regressions too:
  generation mismatch, code-version mismatch, compiler/backend-manifest
  mismatch, surface runtime provenance, and cache-explain debug-manifest output
  should all be checked deliberately instead of assumed from profiler wins.
- Mermaid acceleration or Atlas refresh changes need both worker-path and fallback regressions.

## Useful Validation Bundles
- When changing Compass brief architecture or refresh reuse, run:
  - `PYTHONPATH=src pytest tests/unit/runtime/test_compass_standup_brief_substrate.py tests/unit/runtime/test_compass_standup_brief_batch.py tests/unit/runtime/test_compass_standup_brief_maintenance.py tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/runtime/test_render_compass_dashboard.py -q`
  - `PYTHONPATH=src pytest tests/integration/runtime/test_surface_browser_deep.py -k 'compass and brief' -q`
  - `PYTHONPATH=src pytest tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_sync_cli_compat.py -q`
- When changing Odylith Context Engine or local-runtime behavior, run:
  - `./.odylith/bin/odylith context-engine --repo-root . status`
  - `./.odylith/bin/odylith context-engine --repo-root . impact --working-tree`
  - `./.odylith/bin/odylith compass watch-transactions --repo-root . --once --runtime-mode standalone`
  - `./.odylith/bin/odylith sync --repo-root . --debug-cache --check-only --runtime-mode standalone`
  - `./.odylith/bin/odylith sync --repo-root . --check-only --check-clean --runtime-mode standalone --registry-policy-mode enforce-critical --enforce-deep-skills`
  - `./.odylith/bin/odylith validate component-registry --repo-root .`
- When the target repo's own application code changes, add the target repo's own test/build/lint command on its native toolchain after Odylith validation narrows the slice.
- When changing generated governance surfaces or lifecycle semantics, run a strict refresh path and review the rendered output, not only the raw payloads.
- When changing lifecycle closeout or rendered surface truth, add `./.odylith/bin/odylith validate plan-risk-mitigation --repo-root .`, `./.odylith/bin/odylith validate plan-traceability --repo-root .`, `./.odylith/bin/odylith sync --repo-root . --force --odylith-mode refresh --check-clean`, and `./.odylith/bin/odylith atlas render --repo-root . --fail-on-stale`.
- When changing Guidance Behavior, add:
  - `./.odylith/bin/odylith validate guidance-behavior --repo-root .`
  - `./.odylith/bin/odylith benchmark --profile quick --family guidance_behavior --no-write-report --json`
- If the strict sync gate is blocked only by Mermaid freshness, repair that with `./.odylith/bin/odylith atlas auto-update --repo-root . --from-git-working-tree --fail-on-stale` plus Atlas rerender, then rerun the gate.

## Useful Validation Commands
- `./.odylith/bin/odylith context-engine --repo-root . status`
- `./.odylith/bin/odylith context-engine --repo-root . impact --working-tree`
- `./.odylith/bin/odylith compass watch-transactions --repo-root . --once --runtime-mode standalone`
- `./.odylith/bin/odylith validate plan-risk-mitigation --repo-root .`
- `./.odylith/bin/odylith validate plan-traceability --repo-root .`
- `./.odylith/bin/odylith validate component-registry --repo-root .`
- `./.odylith/bin/odylith validate guidance-behavior --repo-root .`
- `./.odylith/bin/odylith benchmark --profile quick --family guidance_behavior --no-write-report --json`
- `./.odylith/bin/odylith sync --repo-root . --force --odylith-mode refresh --check-clean`
- `./.odylith/bin/odylith sync --repo-root . --check-only --check-clean --runtime-mode standalone --registry-policy-mode enforce-critical --enforce-deep-skills`
- `./.odylith/bin/odylith atlas render --repo-root . --fail-on-stale`
