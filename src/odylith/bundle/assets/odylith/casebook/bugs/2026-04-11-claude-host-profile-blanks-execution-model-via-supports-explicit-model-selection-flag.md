- Bug ID: CB-103

- Status: In progress

- Created: 2026-04-11

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: Odylith's shared host capability contract declares
  `supports_explicit_model_selection=False` for the Claude host family,
  and `execution_profile_runtime_fields` treats that flag as a veto that
  silently blanks out the resolved model. Every Claude-routed spawn
  therefore comes back with an empty model name even though Claude Code
  supports explicit model selection through subagent frontmatter and
  Task-tool spawns. The downstream effect is that the canonical execution
  profile ladder (`analysis_medium`, `analysis_high`, `fast_worker`,
  `write_medium`, `write_high`, `frontier_high`, `frontier_xhigh`) has no
  effect on Claude: a `frontier_high` routing decision and a `fast_worker`
  routing decision both resolve to the same empty-string model. Combined
  with the fact that `_EXECUTION_PROFILE_RUNTIME_FIELDS` only carries Codex
  tuples (`gpt-5.4-mini`, `gpt-5.3-codex-spark`, `gpt-5.3-codex`, `gpt-5.4`)
  and has no Claude-side column, the profile ladder is effectively a no-op
  on Claude even after `B-083` landed guidance-surface parity and flipped
  `supports_native_spawn=True` for the Claude host family.

- Impact: Claude delegation loses the reasoning-tier discipline the
  profile ladder is designed to enforce. Review leaves, retrieval leaves,
  and frontier leaves all pay the same middle-tier cost and accuracy
  posture, regardless of how the router assessed the slice. Claude project
  subagents compound the regression by hard-coding `model: sonnet`
  uniformly in `.claude/agents/`, so the contract silently degrades to a
  single model tier across the entire Claude delegation surface.

- Components Affected: `src/odylith/runtime/execution_engine/contract.py`,
  `src/odylith/runtime/common/host_runtime.py`,
  `src/odylith/runtime/common/agent_runtime_contract.py`,
  `src/odylith/runtime/orchestration/subagent_router.py`,
  `src/odylith/runtime/orchestration/subagent_orchestrator.py`,
  `src/odylith/runtime/context_engine/tooling_context_routing.py`,
  `.claude/agents/*.md`, and the `execution-governance` Registry component.

- Environment(s): Odylith product repo maintainer mode under Claude Code,
  any Claude-hosted delegation surface that consumes the host-neutral
  execution profile ladder, and shared runtime payloads that read the
  host-capability contract.

- Root Cause: Early Claude support work set
  `supports_explicit_model_selection=False` defensively because Claude was
  not yet validated as a delegation host. `B-083` later promoted Claude to
  a first-class delegation host and flipped `supports_native_spawn=True`,
  but the model-selection flag kept its conservative default. Separately,
  `_EXECUTION_PROFILE_RUNTIME_FIELDS` was built around a single profile -
  tuple mapping instead of a per-host-family axis, so even with the flag
  flipped the ladder has no Claude column to resolve to.

- Solution: Flip `supports_explicit_model_selection` to `True` for the
  Claude host in `contract.py` and `host_runtime.py`. Restructure
  `_EXECUTION_PROFILE_RUNTIME_FIELDS` as a `(host_family, profile) ->
  (model, reasoning_effort)` map that keeps the existing Codex column
  byte-identical and adds a Claude column mapping each semantic profile
  onto haiku, sonnet, or opus. Update `execution_profile_runtime_fields`
  to resolve through the host-family axis and return the real Claude model
  instead of an empty string. Update the eight Claude project subagents in
  `.claude/agents/` to declare per-profile models instead of a uniform
  `sonnet`. Land the flag flip and the ladder column in the same commit to
  avoid landing one without the other.

- Verification: Add a characterization test in
  `tests/unit/runtime/test_agent_runtime_contract.py` that asserts, for
  every canonical profile, `execution_profile_runtime_fields(profile,
  host_runtime="codex_cli")` and `execution_profile_runtime_fields(profile,
  host_runtime="claude_cli")` both return a non-empty model; and assert
  every Codex tuple is byte-identical to its pre-change value. Then run
  `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_host_runtime_contract.py tests/unit/runtime/test_agent_runtime_contract.py tests/unit/runtime/test_execution_governance.py tests/unit/test_claude_project_hooks.py`,
  `./.odylith/bin/odylith sync --repo-root . --check-only`,
  and `git diff --check`.

- Prevention: Shared host-neutral runtime contracts must grow a host-family
  axis from the start whenever they resolve names, tiers, or other host-
  specific detail. Defensive host-capability flags must be revisited the
  moment a host is promoted to a first-class delegation lane; the
  promotion review should fail if any capability flag still reads as "not
  yet validated" for the host being promoted.

- Detected By: Second-pass Claude-optimization repo scan against the
  post-`B-083` tree, while validating the delegation style consumer sites
  in `subagent_router.py` and the profile resolver in
  `agent_runtime_contract.py`.

- Failure Signature: `execution_profile_runtime_fields(profile,
  host_runtime="claude_cli")` returns `("", reasoning_effort)` for every
  canonical profile; Claude delegation payloads emit empty `model` fields;
  Claude project subagents all resolve to the same uniform `sonnet` model
  regardless of profile.

- Trigger Path: Any Claude-hosted delegation call that reads the execution
  profile ladder, including routed subagent spawns, orchestrator fanout,
  and hot-path packet runtime resolution under
  `src/odylith/runtime/context_engine/odylith_context_engine_hot_path_packet_core_runtime.py`.

- Ownership: Execution Governance (host capability contract and profile
  helpers) in partnership with Subagent Router and Subagent Orchestrator
  for consumer-site callers. The `.claude/` project surface fix is
  co-owned with the Claude host lane within the broader Odylith product
  repo.

- Timeline: `B-083` landed the guidance-surface parity push on 2026-04-10,
  which included flipping `supports_native_spawn=True` for the Claude
  host family. The second-pass repo scan on 2026-04-11 found that the
  model-selection flag had not been revisited in the same review, and that
  the profile ladder still had no Claude column. `B-084` extends
  `B-083` to close that gap.

- Blast Radius: Every Claude-hosted delegation call that consumes the
  execution profile ladder. Codex callers are unaffected because the Codex
  branch of the host-capability contract already returns `True`.

- SLO/SLA Impact: No outage, but a product-contract regression: the Odylith
  execution profile ladder silently has no effect on Claude, which is a
  first-class capability claim after `B-083`.

- Data Risk: Low.

- Security/Compliance: Low.

- Invariant Violated: Every canonical execution profile must resolve to a
  non-empty model for every validated host family; Odylith's shared
  host-neutral runtime contract must not silently degrade to empty fields
  on any supported host.

- Workaround: None short of the forward fix, because the empty-string
  model silently bypasses the profile ladder instead of raising a visible
  error.

- Rollback/Forward Fix: Forward fix with characterization-test coverage.
  Rollback path is to revert the host-capability flag flip and the Claude
  profile-ladder column together.

- Agent Guardrails: Before editing host-capability flags, model-family
  policy, or the execution profile ladder, verify the resolver returns a
  non-empty model for every canonical profile on every validated host
  family; do not land a flag flip without the matching ladder column in
  the same commit.

- Preflight Checks: Inspect `contract.py`, `host_runtime.py`, and
  `agent_runtime_contract.py` together before editing any of them; confirm
  the Codex branch is byte-identical before and after; inspect every
  caller of `execution_profile_runtime_fields` to confirm none of them
  depend on empty-string as a sentinel.

- Regression Tests Added: New characterization test in
  `tests/unit/runtime/test_agent_runtime_contract.py` pinning the
  host-family model ladder for every canonical profile for both Codex and
  Claude; existing `tests/unit/test_claude_project_hooks.py` keeps the
  `.claude/` surface coverage in place.

- Monitoring Updates: Watch routed Claude spawn payloads in the agent
  stream for empty `model` fields; any future occurrence is a regression.

- Residual Risk: Actual `subagent_router.py` decomposition remains a
  separate workstream; until that lands, every Claude-specific runtime
  tuning deepens a red-zone shared file and increases the Codex-regression
  blast radius.

- Related Incidents/Bugs:
  [2026-04-09-host-contract-drift-leaks-codex-only-policy-into-claude-and-shared-runtime-surfaces.md](2026-04-09-host-contract-drift-leaks-codex-only-policy-into-claude-and-shared-runtime-surfaces.md)

- Version/Build: Odylith product repo working tree on 2026-04-11, branch
  `2026/freedom/v0.1.11`.

- Config/Flags: Standard shared runtime and host-capability paths; no
  special flags required to reproduce the regression.

- Customer Comms: Odylith's execution profile ladder now resolves to a
  real model on both Codex and Claude Code. Previous Claude-hosted
  delegation effectively ignored the profile ladder because the host-
  capability contract declared the host could not select an explicit
  model; that defensive default has been corrected.

- Code References: `src/odylith/runtime/execution_engine/contract.py:82`,
  `src/odylith/runtime/common/host_runtime.py:101`,
  `src/odylith/runtime/common/agent_runtime_contract.py:70`,
  `src/odylith/runtime/common/agent_runtime_contract.py:101`.

- Runbook References: `odylith/AGENTS.md`,
  `odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md`,
  `odylith/registry/source/components/execution-governance/CURRENT_SPEC.md`.

- Fix Commit/PR: Landing under `B-084` on branch
  `2026/freedom/v0.1.11`.
