Status: In progress

Created: 2026-04-11

Updated: 2026-04-11 (release-0-1-11 binding recorded; `subagent_router.py` decomposition workstream still outstanding)

Backlog: B-084

Goal: Close the second-pass Claude delegation runtime gaps that `B-083`
did not cover. Flip the `supports_explicit_model_selection` flag for the
Claude host, add a Claude column to the execution-profile ladder so every
canonical profile resolves to a real haiku/sonnet/opus model, differentiate
Claude project subagent frontmatter, rewrite the stale "Codex is the
validated host today" language, expand the `.claude/` project surface with
the documented Claude-native primitives we were missing (output style,
statusline, PreCompact hook, slash-command parameterization, subagent
triggers), and open a bounded decomposition workstream for
`subagent_router.py` so future Claude tuning does not continue to inflate a
red-zone shared file. Keep Codex byte-identical throughout.

Assumptions:
- Claude Code supports explicit model selection via subagent frontmatter
  and Task-tool spawns, so the defensive `supports_explicit_model_selection
  =False` flag on the Claude host profile is wrong, not cautious.
- The canonical execution-profile ladder is semantic (analysis, write,
  frontier, fast worker) and the Codex column is one concrete host mapping,
  not the ladder itself.
- Every existing Codex profile tuple must remain byte-identical; the
  Claude column is additive.
- `.claude/` surface expansion is scoped to the Claude host and has zero
  runtime impact on Codex.
- This slice is contract hardening and surface expansion, not measured
  benchmark proof.

Constraints:
- Do not regress Codex. Every touched file must keep the Codex branch
  byte-identical to the pre-change behavior.
- Do not land the host-capability flag flip without the matching Claude
  profile-ladder column in the same commit. Landing them out of order
  silently returns empty model strings for every Claude spawn.
- Do not attempt to decompose `subagent_router.py` inside this slice;
  stand up the bounded decomposition workstream only.
- MCP server surfaces are explicitly out of scope per operator direction;
  this plan does not land `.claude/mcp/`.
- Must-Ship items must be complete before closeout; the characterization
  test is the gate that catches future regressions of the same shape.

Reversibility: The host-capability flip, the profile ladder growth, and the
`.claude/` surface expansion are all reversible. If the Claude model ladder
produces surprising behavior, rollback is to re-pin every subagent to
`sonnet` and fall back to returning the Codex column for both host
families. The characterization test makes the rollback legible because it
pins the expected model name per host family per profile.

Boundary Conditions:
- Scope includes the host-capability contract in
  `src/odylith/runtime/execution_engine/contract.py` and
  `src/odylith/runtime/common/host_runtime.py`, the host-neutral execution
  profile helpers in `src/odylith/runtime/common/agent_runtime_contract.py`,
  the Claude project surface under `.claude/`, the guidance doc under
  `odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md`, and the
  matching Registry/Atlas/Casebook/Compass governance trail.
- Scope excludes the actual decomposition of `subagent_router.py`,
  `.claude/mcp/`, and any benchmark re-proof against the new Claude ladder.

Related Bugs:
- CB-103 (new this slice): Claude host profile blanks execution model via
  `supports_explicit_model_selection` flag
- CB-084 (closed, referenced): host-contract drift leaks Codex-only policy
  into Claude and shared runtime surfaces

## Learnings
- [x] A host-capability flag that was set defensively to `False` during
      the "Claude is not yet validated" era silently becomes a correctness
      bug the moment Claude becomes a real delegation host, because
      downstream consumers treat it as a veto.
- [x] Growing a semantic profile ladder without a host-family axis forces
      the first host's names to become the shared canon, which is the same
      invariant `CB-084` closed for Codex-branded runtime ids.
- [x] Every `.claude/` surface primitive Claude Code documents is a
      first-class place for Odylith to express its contract; leaving any of
      them unused is opportunity cost, not neutral.

## Must-Ship
- [x] Bind this plan to `B-084` and document it as a child of `B-083`.
- [x] Open `CB-103` for the silent model-selection flag bug and link it
      back to this plan.
- [x] Flip `supports_explicit_model_selection` to `True` for the Claude
      host in `contract.py` and `host_runtime.py`.
- [x] Extend `_EXECUTION_PROFILE_RUNTIME_FIELDS` with a `(host_family,
      profile) -> (model, reasoning_effort)` map that keeps Codex tuples
      byte-identical and adds a Claude column
      (haiku/sonnet/opus per profile). Landed as
      `_EXECUTION_PROFILE_RUNTIME_FIELDS_BY_HOST` in
      `src/odylith/runtime/common/agent_runtime_contract.py:76`, codex
      column byte-identical, claude column differentiated per profile.
- [x] Update `execution_profile_runtime_fields` to resolve through the
      host-family axis and return a real model for Claude. Resolver at
      `agent_runtime_contract.py:133` routes through the `host_family`
      capability key returned by `host_runtime.resolve_host_capabilities`.
- [x] Update the Claude project subagent frontmatters in
      `.claude/agents/` to declare per-profile models. All 9 shipped
      project subagents now carry an explicit `model:` field (haiku for
      compass-narrator, opus for reviewer, sonnet for the remaining
      task/retrieval/governance leaves).
- [x] Rewrite the "Codex is the validated host today" bullet in
      `odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md:46`.
      Both the routing-defaults and profile-ladder bullets now name Codex
      and Claude as first-class delegation hosts and surface the per-host
      ladder tuples.
- [x] Add a characterization test that pins the host-family model ladder.
      `tests/unit/runtime/test_agent_runtime_contract.py` now asserts the
      Codex ladder byte-identical, the Claude ladder per profile, every
      validated host returning non-empty model/reasoning for every
      canonical profile, cross-host column differentiation, and
      fail-closed unknown-host handling.
- [x] Add `.claude/output-styles/odylith-grounded.md` for the voice contract.
- [x] Statusline and PreCompact snapshot moved to child slice B-085, which
      bakes both surfaces into `src/odylith/runtime/surfaces/` as
      first-class Python modules behind a new `odylith claude` CLI
      subcommand group instead of external shell + standalone-Python
      adapters under `.claude/`. See
      `odylith/technical-plans/in-progress/2026-04/2026-04-11-claude-host-python-surface-bake-statusline-and-precompact-snapshot.md`.
- [x] Parameterize the ref-taking slash commands with `$ARGUMENTS`. The
      `/odylith-context`, `/odylith-query`, `/odylith-workstream-new`,
      `/odylith-worktree`, `/odylith-handoff`, `/odylith-plan`,
      `/odylith-case`, `/odylith-compass-log`, and
      `/odylith-sync-governance` shims now declare
      `argument-hint:` frontmatter and pipe `$ARGUMENTS` through the
      command body. Bundle mirrors under
      `src/odylith/bundle/assets/project-root/.claude/commands/` carry
      the same contract.
- [x] Add "Use PROACTIVELY when ..." clauses to every subagent
      `description:` field. All 9 project subagents declare a
      `PROACTIVELY when ...` trigger so the Task tool surfaces the
      right leaf without a host-side prompt rewrite.
- [x] Drop `Bash` from `odylith-context-engine.md`'s declared tool list.
      The retrieval leaf now declares `tools: Read, Grep, Glob` only.
- [ ] Stand up a bounded decomposition workstream record for
      `src/odylith/runtime/orchestration/subagent_router.py` (3,418 LOC,
      red zone) without attempting the refactor in this slice.
- [x] Update `execution-governance` `CURRENT_SPEC.md` to describe the
      host-family axis on the runtime profile ladder. The spec now
      documents `host_family` as a per-host axis and traces the
      `(host_family, profile) -> (model, reasoning_effort)` resolution
      path, with a dated lifecycle entry referencing `B-084`/`CB-103`.
- [x] Update the `odylith-execution-governance-engine-stack` Atlas diagram
      so the Host → Policy edge reflects per-host-family model resolution.
      The diagram reviewed-on comment now cites `B-084` and the Ladder
      node labels both the Codex and Claude columns explicitly.
- [ ] Log the slice to Compass so the next standup brief surfaces the new
      posture.

## Should-Ship
- [x] Sweep existing Radar and technical-plan markdown for stale
      "until proven" Claude parity language and update the bullets that the
      new contract has already proved. Post-sweep search shows no
      residual "until proven" Claude qualifier in active Radar or
      technical-plan bullets; the only remaining hits are unrelated
      `SECURITY_AND_TRUST.md` Python-helper phrasing and generated
      casebook-payload bundle shards.

## Defer
- [ ] Actual `subagent_router.py` decomposition (separate workstream).
- [ ] `.claude/mcp/` Odylith surface exposure (out of scope per operator
      direction).
- [ ] Fresh Claude-host benchmark proof (out of scope; contract hardening
      only).

## Success Criteria
- [x] Every canonical profile resolves to a non-empty model for both
      `codex_cli` and `claude_cli` host runtimes. Pinned by
      `test_every_validated_host_resolves_to_non_empty_model_for_every_profile`.
- [x] Every Codex profile tuple is byte-identical to its pre-change value.
      Pinned by `test_codex_execution_profile_ladder_is_byte_identical`
      against the `_CODEX_CANONICAL_PROFILE_LADDER` snapshot.
- [x] `.claude/` surface expansion is complete: output style, statusline,
      PreCompact hook, parameterized slash commands, PROACTIVELY triggers,
      tightened context-engine tool scope. Statusline and PreCompact
      snapshot baked into `src/odylith/runtime/surfaces/claude_host/`
      under `B-085` and wired through `.claude/statusline.sh` +
      `.claude/settings.json`.
- [ ] Governance trail updated across Radar, technical plan, Casebook,
      Registry, Atlas, and Compass. Radar, plan, Casebook (`CB-103`),
      Registry (`execution-governance` spec), and Atlas (`D-030`) all
      updated; Compass slice log still pending.

## Non-Goals
- [ ] Replacing `AGENTS.md` as the canonical cross-host contract.
- [ ] Decomposing `subagent_router.py` here.
- [ ] Adding `.claude/mcp/` surfaces.
- [ ] Producing fresh benchmark proof for the Claude host.

## Impacted Areas
- [x] [2026-04-11-claude-delegation-runtime-parity-host-capability-model-ladder-and-claude-native-surface-expansion.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-11-claude-delegation-runtime-parity-host-capability-model-ladder-and-claude-native-surface-expansion.md)
- [x] [2026-04-11-claude-delegation-runtime-parity-host-capability-model-ladder-and-claude-native-surface-expansion.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-11-claude-delegation-runtime-parity-host-capability-model-ladder-and-claude-native-surface-expansion.md)
- [x] [2026-04-11-claude-host-profile-blanks-execution-model-via-supports-explicit-model-selection-flag.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-11-claude-host-profile-blanks-execution-model-via-supports-explicit-model-selection-flag.md)
- [x] [src/odylith/runtime/execution_engine/contract.py](/Users/freedom/code/odylith/src/odylith/runtime/execution_engine/contract.py)
- [x] [src/odylith/runtime/common/host_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/common/host_runtime.py)
- [x] [src/odylith/runtime/common/agent_runtime_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/common/agent_runtime_contract.py)
- [x] [odylith/registry/source/components/execution-governance/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/execution-governance/CURRENT_SPEC.md)
- [x] [odylith/atlas/source/odylith-execution-governance-engine-stack.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-execution-governance-engine-stack.mmd)
- [x] [odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md](/Users/freedom/code/odylith/odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md)
- [x] [.claude/settings.json](/Users/freedom/code/odylith/.claude/settings.json)
- [x] [.claude/agents/](/Users/freedom/code/odylith/.claude/agents/)
- [x] [.claude/commands/](/Users/freedom/code/odylith/.claude/commands/)
- [x] [.claude/hooks/](/Users/freedom/code/odylith/.claude/hooks/)
- [x] [.claude/output-styles/](/Users/freedom/code/odylith/.claude/output-styles/)
- [x] [.claude/statusline.sh](/Users/freedom/code/odylith/.claude/statusline.sh)
- [x] [tests/unit/runtime/test_agent_runtime_contract.py](/Users/freedom/code/odylith/tests/unit/runtime/test_agent_runtime_contract.py)
- [x] [odylith/radar/source/releases/release-assignment-events.v1.jsonl](/Users/freedom/code/odylith/odylith/radar/source/releases/release-assignment-events.v1.jsonl) — B-083, B-084, B-085 bound to release-0-1-11 on 2026-04-11.

## Rollout
1. Update governance trail first (Radar, plan, bug, Registry, Atlas,
   Compass log) so the next standup brief shows the second-pass posture.
2. Land the host-capability flip and the Claude profile-ladder column in
   one bounded commit together with the characterization test.
3. Differentiate Claude subagent frontmatter, rewrite the stale guidance
   doc bullet, add output style, statusline, and PreCompact hook.
4. Ship polish: parameterize ref-taking slash commands with `$ARGUMENTS`,
   add PROACTIVELY clauses to subagent descriptions, drop `Bash` from the
   context-engine subagent, sweep stale "until proven" language.
5. Stand up the bounded decomposition workstream for `subagent_router.py`.
6. Run validation and refresh governed surfaces.

## Validation
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_host_runtime_contract.py tests/unit/runtime/test_agent_runtime_contract.py tests/unit/runtime/test_execution_governance.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_claude_project_hooks.py`
- [ ] `./.odylith/bin/odylith sync --repo-root . --check-only`
- [ ] `git diff --check`

## Outcome Snapshot
- [x] Claude delegation returns a real model for every canonical profile
      instead of silently blanking it out, and the Claude project surface
      is expanded to match the documented Claude Code primitives we were
      previously leaving unused.
- [x] Codex behavior is unchanged; all Codex profile tuples are
      byte-identical and the Codex delegation style still resolves through
      the same routed-spawn path.
- [ ] The `subagent_router.py` decomposition is on the backlog as an
      explicit bounded workstream, so the next Claude-side tuning does not
      have to land in a red-zone shared file.
