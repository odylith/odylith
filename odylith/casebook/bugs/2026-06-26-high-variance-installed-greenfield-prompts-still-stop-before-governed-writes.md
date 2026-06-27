- Bug ID: CB-209

- Status: FixedPendingRelease

- Created: 2026-06-26

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: High-variance installed greenfield prompts still stop before governed writes

- Impact: Harder real-world greenfield prompts can pass proposal generation but fail post-confirm create before Radar, Registry, Atlas, release, traceability, and quality-manifest records are committed, leaving only partial runtime/source artifacts.

- Components Affected: domain-intelligence

- Environment(s): v0.1.15 local release dists installed into fresh consumer repos under /Users/freedom/mock, including /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-17e8a6f6, /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-cedafc79, and /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-b0713a0a

- Detected By: Custom high-variance installed greenfield matrix after release smoke and standard installed matrix passed

- Failure Signature: autonomous warehouse safety state and federated agent incident command returned create_returncode=2 in the earlier installed matrix; post-confirm quality manifest missing; Radar workstreams 1, Registry specs 0, Atlas sources 0, release records 0, trace nodes 0. A later installed matrix on cedafc79 fixed those two cases but exposed two additional platform failures: indigenous data sovereignty review returned create_returncode=2 before governed writes, and spacecraft anomaly triage committed records but failed rendered package quality because multiple Radar titles ended with a clipped article phrase `a`.

- Trigger Path: scripts/release/greenfield_post_confirm_matrix.py custom cases using greenfield propose followed by greenfield create --confirm --release 0.0.1 --json

- Ownership: Domain Intelligence greenfield post-confirm semantic compiler and final quality gate

- Timeline: 2026-06-26: standard installed five-domain matrix passed at 17.404-18.353s with zero quality issues; custom high-variance installed matrix then failed autonomous warehouse safety state at 17.855s and federated agent incident command at 10.728s before governed writes. After semantic-custody and typed Tribunal-lens fixes, the cedafc79 standard installed matrix passed five cases at 17.074-18.574s with zero issues and all expert lenses passing. A harder cedafc79 custom installed matrix then passed autonomous warehouse safety state, federated agent incident command, deepfake provenance escrow, and fusion plasma shot readiness at 16.851-17.347s, but indigenous data sovereignty review failed before governed writes in 8.999s and spacecraft anomaly triage failed the package/domain-expert gate after writing records in 18.454s due clipped Radar article phrases. After the second semantic-custody fix, the b0713a0a dist passed release smoke, the standard installed matrix, and the harder six-case installed matrix with every create under 19s and every PM, architect, engineer, and domain-expert lens passing.

- Blast Radius: Any consumer greenfield prompt with overloaded safety/state/agent/model/release language that deterministic completion cannot safely normalize before final writes

- SLO/SLA Impact: Fixed in the b0713a0a local release dist: post-confirm create stayed under the 60s standard budget in the standard and high-variance installed matrices.

- Data Risk: Low: governed records are not written after failed create; product intent can remain in runtime files

- Security/Compliance: No direct security exposure; governance trust and release-readiness claim risk

- Invariant Violated: Confirmed greenfield create must either write a complete governed project package within the standard/rescue budget or return exact recoverable blockers after exhausting bounded semantic repair

- Workaround: None acceptable; do not hand-edit generated project repos or weaken quality gates

- Root Cause: Retained repros showed multiple semantic-custody misses. First, system-generated outcome text such as product monitors reporting evidence was projected into user capability prose as modal drift (`can reports`). Second, passive review-state clauses such as `operator override records and release readiness must be reviewable` were misread as actor rows, promoting result nouns like `Release Readiness` into people. A separate modal normalizer misread `decide what can be released` as an actor plus verb, producing `what bes released`. The artifact-plan PatchSet executor also had a repair-custody risk: an untargeted row patch could mutate the only row instead of requiring an explicit row selector. The cedafc79 installed repros exposed two further owner defects: the semantic compiler treated every phrase beginning with `release readiness` as proof-control text, rejecting a valid first-path result event and falling back to proof-boundary prose; and first-path/actor recovery treated hyphenated noun compounds and passive object-state tails as action or actor facts, turning `research-use limits` into a fake `use limits` action and `recovery state before a corrective procedure is released` into a human actor. The rescue-path proof then exposed provider-path failed mechanisms: with `--ignore-user-config`, a blank Codex model inherited an account-incompatible CLI default, the automatic ladder still contained unsupported `gpt-5.3-codex`, and the Tribunal patch-plan schema had open-ended or untyped fields that strict structured output rejected. The architectural learning is that actor, action, object, passive state predicate, system-generated result, proof-control text, review target, provider model selection, and schema-constrained repair facts must be separated before rendering governed artifacts; row-level and provider-authored repair must be fail-closed without explicit custody.

- Solution: Fix Odylith generally in semantic/projection ownership rather than domain-specific terms or rendered-string repair. Confirmed-intent recovery now localizes role-only actors to the project, keeps object modifiers out of actor labels, treats state-review predicates as review targets, rejects passive object-state subjects as human actors, and uses article-safe actor references. Outcome-action projection now converts system-generated results into modal-safe `review` or `see` actions before `user can` prose is composed. The role-can normalizer now preserves interrogative/modal clauses such as `what can be released`. First-path visible-result extraction now respects token boundaries inside hyphenated noun compounds, and semantic proof-control detection no longer rejects first-path `release readiness for ...` noun results while still rejecting control claims such as `release readiness requires ...`. Artifact-plan PatchSet row repair now refuses untargeted row mutations. A shared Tribunal lens contract now lets PM, architect, engineer, and domain-expert checks emit source-map target paths, semantic-node IDs, projection IDs, repairability, and repair owner at judgment time instead of reconstructing repair custody from check-name prose. The structured reasoning adapter now supplies an explicit live-proven Codex model for general structured repair when config is blank, maps the legacy Spark alias to the live CLI model, avoids the unsupported Codex ladder rung, and keeps user-config bypass reproducible. Tribunal patch planning now uses strict structured-output schemas for decision ledger, proof deltas, and replacement facts, then materializes the typed fact envelope back into caller-owned semantic or artifact-plan replacements after custody validation.

- Rollback/Forward Fix: Forward fix only

- Verification: Run source-local and installed high-variance matrices including autonomous warehouse safety state, federated agent incident command, indigenous data sovereignty review, and spacecraft anomaly triage; require create_returncode 0, committed quality manifest, complete Radar/Registry/Atlas/release/trace records, zero package quality issues, all expert lenses passing, and create latency under 60s unless documented rescue path is active. Source-local proof on 2026-06-26 is green: focused Tribunal/greenfield proof passed 53 tests in 85.82s; the broad greenfield runtime pack passed 299 tests in 474.86s; six source-local CLI confirmed-create simulations passed with temp cleanup after every case. Timings were autonomous warehouse safety state 15.501s, federated agent incident command 14.685s, deepfake provenance escrow 15.143s, fusion plasma shot readiness 13.934s, indigenous data sovereignty review 15.344s, and spacecraft anomaly triage 15.333s. Every source-local run wrote four Radar workstreams, three Registry specs, six Atlas diagrams, five rendered surfaces, release/program records, 18 trace nodes, at least three required domain-term hits, zero issues, and all PM/architect/engineer/domain-expert lenses passed. Installed cedafc79 standard matrix passed five cases, but custom installed proof still failed two cases. Current source-local proof after the second fix: focused regressions passed 4 tests in 17.61s; indigenous data sovereignty review and spacecraft anomaly triage source CLI simulations both wrote governed records, produced complete Radar/Registry/Atlas/release/trace artifacts, reported zero quality issues, passed all expert lenses, and finished in 12.708s and 12.328s; the widened greenfield suite passed 162 tests in 148.37s. Final installed proof from b0713a0a is green: local release smoke exited 0; the standard installed five-domain matrix passed at 16.523-18.483s; the harder six-case installed matrix passed autonomous warehouse safety state 17.356s, federated agent incident command 17.020s, deepfake provenance escrow 16.602s, fusion plasma shot readiness 17.302s, indigenous data sovereignty review 17.649s, and spacecraft anomaly triage 17.107s. Every installed case wrote five Radar workstreams, three Registry specs, six Atlas diagrams, five rendered surfaces, release/program records, 18 trace nodes, zero package-quality issues, and passed PM, architect, engineer, and domain-expert lenses. Current rescue-provider proof: focused reasoning and Tribunal patch-planner tests passed 57 tests in 0.36s, compile proof passed, and a live Codex CLI `gpt-5.4` structured patch-plan call returned one validated `project_outcome` operation in 24.895s with no provider failure or custody rejection. Controlled source-local rescue-write proof passed in 39.768s against the 90s budget: a valid accepted-intent proposal had unique first-pass Radar semantic-coverage misses injected at prewrite, auto tier activated rescue, the real Codex CLI structured planner repaired typed semantic findings, the second pass passed, the normal write transaction committed four workstreams, three Registry specs, and six Atlas sources, final issue count was zero, and the temp repo was deleted after the run.

- Prevention: Keep high-variance installed simulations in release proof; require failure stderr/blocker retention for any matrix failure before cleanup; do not rely on standard-domain passes alone. Expert-lens failures must carry typed Tribunal lens evidence at the point of judgment: source-map target, semantic node, projection, repairability, and owner. Failed mechanisms recorded here must not be repeated: broad proof-control rejection of product-result noun phrases, action extraction inside hyphenated noun compounds, passive object-state tails promoted to actors, rendered-string cleanup after Radar files are already written, blank Codex structured model inheritance under ignored user config, unsupported automatic model ladder rungs, or model-facing patch-plan schema holes.

- Agent Guardrails: Before claiming release readiness, run hard prompts with overloaded terms such as state, agent, model, case, claim, release, record, and verify governed writes plus expert lenses. Capture failures in Casebook before fixing.

- Preflight Checks: Search CB-208 and this bug before changing greenfield completion, final quality gates, repair routing, or release matrix proof.

- Version/Build: 0.1.15 local release dist built from commit b0713a0a

- Related Incidents/Bugs: CB-208

- Code References: - src/odylith/runtime/domain_intelligence
- src/odylith/runtime/reasoning/tribunal_lens.py
- src/odylith/runtime/artifact_quality/greenfield_quality_lenses.py
- scripts/release/greenfield_post_confirm_matrix.py
