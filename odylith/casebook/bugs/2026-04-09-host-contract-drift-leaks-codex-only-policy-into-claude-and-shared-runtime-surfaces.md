- Bug ID: CB-084

- Status: Closed

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Odylith's shared runtime, governance, and UX surfaces still
  leak Codex-only policy into contracts that should be host-neutral. Host
  detection still doubles as policy in several layers, canonical routed
  profile ids and Compass runtime artifacts still use Codex-branded names, and
  shared docs plus benchmark scaffolding still present Codex assumptions as if
  they were the whole product contract. Claude Code therefore inherits
  misleading copy, degraded defaults, or unnecessary compatibility shims even
  where the underlying grounding and reasoning path already works.

- Impact: Claude Code users do not get a truthful first-class Odylith contract,
  maintainers cannot cleanly distinguish transport limits from product limits,
  and shared source truth keeps reintroducing Codex-only language into runtime
  payloads, Compass, install/help UX, and benchmark reporting.

- Components Affected: `src/odylith/contracts/host_adapter.py`,
  `src/odylith/runtime/common/host_runtime.py`,
  `src/odylith/runtime/orchestration/subagent_router.py`,
  `src/odylith/runtime/orchestration/subagent_orchestrator.py`,
  `src/odylith/runtime/context_engine/tooling_context_routing.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine_store.py`,
  `src/odylith/runtime/memory/tooling_memory_contracts.py`,
  `src/odylith/runtime/common/log_compass_timeline_event.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine_projection_search_runtime.py`,
  shared reasoning defaults, Compass runtime artifacts, CLI/install guidance,
  Registry specs, Atlas diagrams, benchmark reports, and bundled mirrors.

- Environment(s): Odylith product repo maintainer mode in both Codex and
  Claude Code, shared CLI/help/install surfaces, Compass runtime rendering,
  Context Engine packets, benchmark proof generation, and bundled consumer
  artifacts.

- Root Cause: Early product slices encoded Codex-specific names and defaults as
  the canonical shared contract because Codex had the first working native
  delegation path. Later Claude support and shared reasoning/runtime work
  layered on top of that canon instead of separating host capability,
  model-family policy, and proof publication scope into explicit contracts.

- Solution: Establish one host capability contract with explicit transport and
  model-family fields, move Codex-specific behavior behind
  `model_family=codex` or explicit capabilities, rename canonical runtime
  artifacts to host-neutral terms with compatibility aliases, rewrite shared
  governance/docs/specs around an explicit host matrix, and split the
  remaining benchmark-only schema tail into `B-070` / `CB-089` instead of
  leaving it hidden inside the broader contract bug.

- Verification: On 2026-04-09 the completed non-benchmark host-contract slice
  passed `104` runtime/contract tests, `153` reasoning and surface/browser
  tests, `102` CLI/install tests, `62` Registry and renderer tests,
  `git diff --check`, and `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`.

- Prevention: Shared product contracts must express host capability and
  host-scoped proof separately. Do not let the first supported host become the
  canonical name for shared runtime ids, stream artifacts, docs, or benchmark
  fields.

- Detected By: Cross-host repo scan while hardening Odylith for equivalent
  Codex and Claude Code operation under strict time and cost budgets.

- Failure Signature: `codex-*` stream or hot-path names appear in shared
  runtime canon, routed payloads emit Codex-branded canonical profile ids,
  host-neutral docs still default to Codex-only language, or shared proof
  fields imply Codex is the whole product rather than one scoped host lane.

- Trigger Path: Any new runtime, guidance, or proof slice that copies existing
  Codex-first canon instead of deriving behavior from explicit host capability
  and model-family contracts.

- Ownership: Host adapter/runtime contracts, subagent routing/orchestration,
  Context Engine packet/memory output, Compass runtime canon, benchmark schema,
  and shared governance surfaces.

- Timeline: `B-012`, `B-015`, `B-016`, and `B-031` each improved part of the
  early Codex-first product contract, but none fully separated Codex-only
  transport behavior from the shared cross-host product contract. The drift
  became more visible after Claude support and broader governance hardening
  landed across 2026-03-29 through 2026-04-09.

- Blast Radius: Shared runtime payloads, Compass readouts, install and help
  UX, Registry and Atlas truth, benchmark reporting, and any future host work
  that extends the current Codex-first canon by default.

- SLO/SLA Impact: No outage, but a first-class product-contract and operator
  trust regression across multiple maintained surfaces.

- Data Risk: Low.

- Security/Compliance: Low direct security risk, but weak contract separation
  increases the chance of misleading proof or behavior claims across hosts.

- Invariant Violated: Odylith should expose one host-neutral product contract
  with explicit host-scoped capabilities and proof, not a Codex-branded canon
  with Claude compatibility layered on top.

- Workaround: Manual maintainer interpretation of which Codex-branded terms are
  merely historical or compatibility aliases. That workaround does not scale
  and should not remain the product contract.

- Rollback/Forward Fix: Forward fix with compatibility aliases.

- Agent Guardrails: Before editing routing, Compass, install/help, or benchmark
  copy, inspect whether the behavior belongs to host capability, model-family
  policy, or proof publication scope. Do not add new Codex-branded canonical
  ids to shared contracts.

- Preflight Checks: Inspect `host_adapter.py`, `host_runtime.py`, the router
  and orchestrator, the Context Engine packet and memory outputs, the Compass
  runtime stream contract, and current host-facing docs/specs before editing.

- Regression Tests Added: Host-capability matrix proof in
  `tests/unit/runtime/test_host_runtime_contract.py`; Compass/runtime/context
  hardening in `tests/unit/runtime/test_context_grounding_hardening.py`; plus
  the broader runtime, surface/browser, CLI/install, and Registry validation
  bundles recorded under `B-069` closeout.

- Monitoring Updates: Watch new runtime payloads, synced bundle mirrors, and
  proof outputs for reintroduced `codex-*` canonical ids outside explicit
  compatibility or measured proof scopes.

- Residual Risk: Claude-native transport parity remains intentionally out of
  scope until proven, and the benchmark live-runner/report schema still has an
  explicit follow-up under `B-070` / `CB-089`.

- Related Incidents/Bugs:
  [2026-04-08-release-proof-tests-assume-local-codex-host-and-break-in-github-actions.md](2026-04-08-release-proof-tests-assume-local-codex-host-and-break-in-github-actions.md)
  [2026-04-09-benchmark-live-proof-reports-still-emit-codex-branded-canonical-fields.md](2026-04-09-benchmark-live-proof-reports-still-emit-codex-branded-canonical-fields.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Standard shared runtime and product-governance paths; no
  special flags required to reproduce the drift.

- Customer Comms: Odylith should work the same way conceptually in Codex and
  Claude Code. The fix is to make the contract say that truth explicitly while
  keeping honest host-specific transport limits.

- Code References: `src/odylith/contracts/host_adapter.py`,
  `src/odylith/runtime/common/host_runtime.py`,
  `src/odylith/runtime/orchestration/subagent_router.py`,
  `src/odylith/runtime/orchestration/subagent_orchestrator.py`,
  `src/odylith/runtime/common/log_compass_timeline_event.py`,
  `src/odylith/runtime/reasoning/odylith_reasoning.py`

- Runbook References: `odylith/AGENTS.md`,
  `odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md`,
  `odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md`,
  `odylith/registry/source/components/subagent-router/CURRENT_SPEC.md`,
  `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`

- Fix Commit/PR: Non-benchmark cross-host contract fix landed locally under
  `B-069`; benchmark-schema follow-up remains pending under `B-070`.
