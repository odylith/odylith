- Bug ID: CB-209

- Status: InProgress

- Created: 2026-06-26

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: High-variance installed greenfield prompts still stop before governed writes

- Impact: Harder real-world greenfield prompts can pass proposal generation but fail post-confirm create before Radar, Registry, Atlas, release, traceability, and quality-manifest records are committed, leaving only partial runtime/source artifacts.

- Components Affected: domain-intelligence

- Environment(s): v0.1.15 local release dist /Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-17e8a6f6 installed into fresh consumer repos under /Users/freedom/mock

- Detected By: Custom high-variance installed greenfield matrix after release smoke and standard installed matrix passed

- Failure Signature: autonomous warehouse safety state and federated agent incident command returned create_returncode=2; post-confirm quality manifest missing; Radar workstreams 1, Registry specs 0, Atlas sources 0, release records 0, trace nodes 0

- Trigger Path: scripts/release/greenfield_post_confirm_matrix.py custom cases using greenfield propose followed by greenfield create --confirm --release 0.0.1 --json

- Ownership: Domain Intelligence greenfield post-confirm semantic compiler and final quality gate

- Timeline: 2026-06-26: standard installed five-domain matrix passed at 17.404-18.353s with zero quality issues; custom high-variance installed matrix then failed autonomous warehouse safety state at 17.855s and federated agent incident command at 10.728s before governed writes

- Blast Radius: Any consumer greenfield prompt with overloaded safety/state/agent/model/release language that deterministic completion cannot safely normalize before final writes

- SLO/SLA Impact: Post-confirm create remains under 60s but fails closed instead of recovering; release-quality objective not met

- Data Risk: Low: governed records are not written after failed create; product intent can remain in runtime files

- Security/Compliance: No direct security exposure; governance trust and release-readiness claim risk

- Invariant Violated: Confirmed greenfield create must either write a complete governed project package within the standard/rescue budget or return exact recoverable blockers after exhausting bounded semantic repair

- Workaround: None acceptable; do not hand-edit generated project repos or weaken quality gates

- Root Cause: Retained repros showed two semantic-custody misses. First, system-generated outcome text such as product monitors reporting evidence was projected into user capability prose as modal drift (`can reports`). Second, passive review-state clauses such as `operator override records and release readiness must be reviewable` were misread as actor rows, promoting result nouns like `Release Readiness` into people. A separate modal normalizer misread `decide what can be released` as an actor plus verb, producing `what bes released`. The artifact-plan PatchSet executor also had a repair-custody risk: an untargeted row patch could mutate the only row instead of requiring an explicit row selector. The architectural learning is that actor, action, object, passive state predicate, system-generated result, and review target must be separated before rendering governed artifacts; row-level repair must be fail-closed without explicit custody.

- Solution: Fix Odylith generally in semantic/projection ownership rather than domain-specific terms or regex towers. Confirmed-intent recovery now localizes role-only actors to the project, keeps object modifiers out of actor labels, treats state-review predicates as review targets, and uses article-safe actor references. Outcome-action projection now converts system-generated results into modal-safe `review` or `see` actions before `user can` prose is composed. The role-can normalizer now preserves interrogative/modal clauses such as `what can be released`. Artifact-plan PatchSet row repair now refuses untargeted row mutations. A shared Tribunal lens contract now lets PM, architect, engineer, and domain-expert checks emit source-map target paths, semantic-node IDs, projection IDs, repairability, and repair owner at judgment time instead of reconstructing repair custody from check-name prose.

- Rollback/Forward Fix: Forward fix only

- Verification: Run source-local and installed high-variance matrices including autonomous warehouse safety state and federated agent incident command; require create_returncode 0, committed quality manifest, complete Radar/Registry/Atlas/release/trace records, zero package quality issues, all expert lenses passing, and create latency under 60s unless documented rescue path is active. Source-local proof on 2026-06-26 is green: focused Tribunal/greenfield proof passed 53 tests in 85.82s; the broad greenfield runtime pack passed 299 tests in 474.86s; six source-local CLI confirmed-create simulations passed with temp cleanup after every case. Timings were autonomous warehouse safety state 15.501s, federated agent incident command 14.685s, deepfake provenance escrow 15.143s, fusion plasma shot readiness 13.934s, indigenous data sovereignty review 15.344s, and spacecraft anomaly triage 15.333s. Every source-local run wrote four Radar workstreams, three Registry specs, six Atlas diagrams, five rendered surfaces, release/program records, 18 trace nodes, at least three required domain-term hits, zero issues, and all PM/architect/engineer/domain-expert lenses passed. Fresh installed-dist proof remains required before closing.

- Prevention: Keep high-variance installed simulations in release proof; require failure stderr/blocker retention for any matrix failure before cleanup; do not rely on standard-domain passes alone. Expert-lens failures must carry typed Tribunal lens evidence at the point of judgment: source-map target, semantic node, projection, repairability, and owner.

- Agent Guardrails: Before claiming release readiness, run hard prompts with overloaded terms such as state, agent, model, case, claim, release, record, and verify governed writes plus expert lenses. Capture failures in Casebook before fixing.

- Preflight Checks: Search CB-208 and this bug before changing greenfield completion, final quality gates, repair routing, or release matrix proof.

- Version/Build: 0.1.15 local release dist built from commit 17e8a6f6

- Related Incidents/Bugs: CB-208

- Code References: - src/odylith/runtime/domain_intelligence
- src/odylith/runtime/reasoning/tribunal_lens.py
- src/odylith/runtime/artifact_quality/greenfield_quality_lenses.py
- scripts/release/greenfield_post_confirm_matrix.py
