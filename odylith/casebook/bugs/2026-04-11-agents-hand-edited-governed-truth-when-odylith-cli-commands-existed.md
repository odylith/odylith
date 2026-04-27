- Bug ID: CB-104

- Status: In progress

- Created: 2026-04-11

- Severity: P1

- Reproducibility: High

- Type: Agent-Governance-Policy

- Description: During the B-084 and B-085 closeout slice, the agent hit a
  blocked `odylith sync --check-only` run that complained about two missing
  pieces of governance truth: the reciprocal `workstream_children: B-084`
  field on B-083's Radar idea, and the `odylith/technical-plans/INDEX.md`
  rows for B-084 and B-085. Instead of using the dedicated CLI commands
  that own those surfaces, the agent hand-edited the Radar idea frontmatter
  directly and hand-authored the two new INDEX.md rows. The same slice
  then hand-edited the governance INDEX.md "Last updated" header. All of
  these surfaces have dedicated Odylith CLI owners:
  `odylith governance backfill-workstream-traceability` reconciles Radar
  reciprocal links, and
  `odylith governance reconcile-plan-workstream-binding` reconciles
  technical-plan INDEX.md rows from live evidence. The user caught the
  miss with a direct callout ("Dude, why are you not using odylith cli
  commands?") and escalated it to a non-negotiable policy: when an
  Odylith CLI command exists for an operation, the agent must use the
  CLI and must not hand-edit the governed file the CLI owns. Post-hoc
  verification by running the CLI commands idempotently on the
  already-landed state returned `files_modified: 0` and `decisions: 0`,
  confirming the CLI shape was exactly right; only the workflow was
  wrong.

- Impact: Hand-editing governed truth silently races the Odylith writer,
  produces partial states that fail `odylith sync --check-only`, and
  bypasses the authoritative event stream that Radar, Compass, Atlas,
  Registry, and Casebook derive from. Even when the hand-edit looks
  cosmetically correct, it skips execution-governance receipts, drifts
  generated surfaces, wastes operator attention on a redundant refresh,
  and normalizes a Codex/Claude failure mode Odylith exists to prevent.
  Over repeated incidents, the CLI-first contract silently weakens into
  "hand-edit when it feels faster", which is exactly the governance
  regression B-084/B-085 work was supposed to harden against.

- Components Affected: `agent-governance policy` (cross-cutting guidance
  contract), `odylith/agents-guidelines/CLI_FIRST_POLICY.md`,
  `odylith/agents-guidelines/*.md` (9 canonical guidance files),
  `odylith/skills/*/SKILL.md` (16 shared skills),
  `odylith/AGENTS.md`, `odylith/CLAUDE.md`, `AGENTS.md`, `CLAUDE.md`,
  and the shared Odylith CLI surface anchored at `./.odylith/bin/odylith`.

- Environment(s): Odylith product repo maintainer mode under Claude Code
  and Codex. The policy also travels through consumer repos and every
  routed native-spawn leaf on both hosts.

- Root Cause: The previous CLI-first guidance was diffuse. The agent
  guidelines covered grounding, validation, and delegation strongly, but
  they did not name a non-negotiable contract that said "when an Odylith
  CLI command exists for an operation, use the CLI and do not hand-edit
  the governed file". The skill shims did not echo the rule either.
  Faced with two specific blockers and under time pressure, the agent
  defaulted to direct Edit calls against the most obviously broken
  fields instead of re-reading `odylith governance --help` to find the
  exact helper that owned the surface. The policy gap made the
  fast-but-wrong path feel indistinguishable from the correct path.

- Solution: Publish a dedicated non-negotiable policy document at
  `odylith/agents-guidelines/CLI_FIRST_POLICY.md` with an explicit
  enumeration of the authoritative CLI surface, the narrow allowed
  hand-edit surfaces, failure-mode handling, and host coverage for both
  Codex and Claude Code. Install a short `## CLI-First Non-Negotiable`
  stanza at the top of every canonical guidance file under
  `odylith/agents-guidelines/` and every shared skill shim under
  `odylith/skills/*/SKILL.md`, pointing back to the canonical policy and
  anchored by this Casebook learning id (`CB-104`). Mirror the rule into
  the repo-root `AGENTS.md` and `CLAUDE.md` bridge files, and into the
  Odylith-scoped `odylith/AGENTS.md` and `odylith/CLAUDE.md` companions,
  so substantive turns inherit the rule before the first grounded
  action. Treat the rule as host-portable: Codex primary sessions and
  routed `spawn_agent` leaves inherit it, and Claude Code primary
  sessions and Task-tool subagent spawns inherit it through the same
  contract.

- Verification: After the rollout, every canonical guidance file under
  `odylith/agents-guidelines/` must contain the stanza; every skill
  under `odylith/skills/*/SKILL.md` must contain the stanza; both root
  and scoped `AGENTS.md`/`CLAUDE.md` files must reference the policy;
  `odylith/agents-guidelines/CLI_FIRST_POLICY.md` must exist as the
  canonical source with the CLI surface enumeration; and
  `odylith sync --repo-root .` followed by
  `odylith sync --repo-root . --check-only` must pass on the rolled-out
  tree. Run
  `./.odylith/bin/odylith governance backfill-workstream-traceability --repo-root .`
  and
  `./.odylith/bin/odylith governance reconcile-plan-workstream-binding --repo-root .`
  idempotently on the already-landed state and confirm they return
  `files_modified: 0` / `decisions: 0`, which locks in the principle
  that the hand-edited state and the CLI-regenerated state are bit-
  identical when both workflows target the same truth.

- Prevention: CLI-first must be treated as a first-class invariant the
  agent checks before any edit against a governed surface. The
  canonical guidance file enumerates the CLI surface so the agent can
  match the operation to a command without guessing. Every guidance doc
  and skill carries the same short stanza so the rule is impossible to
  miss regardless of which file the agent lands on first. The policy
  explicitly covers both Codex and Claude Code, and it travels through
  routed `spawn_agent` and Task-tool subagent leaves so delegated work
  inherits the same contract. Future host-capability promotions and new
  CLI subcommands must update the enumeration in the same slice.

- Detected By: Operator call-out during the B-084/B-085 closeout slice
  ("Dude, why are you not using odylith cli commands?").

- Failure Signature: `odylith sync --repo-root . --check-only` reports
  missing `workstream_children` reciprocal links or missing
  technical-plan INDEX rows, and the agent's first repair move is a
  direct Edit tool call against the underlying markdown file instead of
  `odylith governance backfill-workstream-traceability` or
  `odylith governance reconcile-plan-workstream-binding`.

- Trigger Path: Any sync-gate blocker that points at a surface owned by
  an Odylith CLI helper. Specifically observed on B-083's Radar idea
  frontmatter and the `odylith/technical-plans/INDEX.md` active-plans
  table.

- Ownership: Cross-cutting agent-governance policy. Primary owners are
  the authors of `odylith/agents-guidelines/` and `odylith/skills/`;
  secondary owners are the Radar and Technical Plans governance
  surfaces that already expose CLI repair paths. The canonical document
  is `odylith/agents-guidelines/CLI_FIRST_POLICY.md`.

- Timeline: Observed on 2026-04-11 during the B-084 parent-plan closeout
  and B-085 Claude host Python surface bake work on branch
  `2026/freedom/v0.1.11`. The operator escalated the miss to a
  non-negotiable policy in the same turn, and the canonical policy
  document plus the guidance/skill stanzas were authored immediately
  afterward.

- Blast Radius: Every Codex and Claude Code session that touches
  governed truth under `odylith/` across every repo that installs
  Odylith. Left unchecked, the drift compounds because rendered surfaces
  and append-only event streams diverge from the hand-edited file
  states.

- SLO/SLA Impact: No outage. The regression is on the agent-governance
  contract, not on runtime correctness, but the cost shows up in
  repeated sync-check failures, redundant refresh passes, and
  execution-governance receipts that go missing.

- Data Risk: Low. The hand-edits themselves happened to be cosmetically
  correct for this specific slice, but the general failure mode opens
  the door to partial drift between source truth and the event stream.

- Security/Compliance: Low.

- Invariant Violated: When an Odylith CLI command exists for an
  operation, the agent must use the CLI command and must not hand-edit
  the governed file the CLI owns. This invariant is now non-negotiable
  across both Codex and Claude Code, and it travels through every
  routed or Task-tool delegated leaf.

- Workaround: If a CLI has already been bypassed on the current slice,
  rerun the matching CLI command idempotently to re-assert governed
  truth, then record the miss in Casebook (this record) and the
  surrounding Compass timeline so later turns inherit the learning.

- Rollback/Forward Fix: Forward fix. Rollback is not meaningful for a
  policy-contract update; the rollback equivalent is weakening the
  canonical rule, which is explicitly forbidden.

- Agent Guardrails: Before any Edit, Write, or equivalent call against a
  path under `odylith/radar/source/`, `odylith/technical-plans/`,
  `odylith/registry/source/`, `odylith/atlas/source/`, or
  `odylith/compass/`, check whether an Odylith CLI command owns that
  operation. Consult `./.odylith/bin/odylith --help`,
  `./.odylith/bin/odylith governance --help`, and the skill-owned
  canonical command sections before falling back to hand-edit.

- Preflight Checks: Re-read `odylith/agents-guidelines/CLI_FIRST_POLICY.md`
  and the matching skill shim before touching any governed surface.
  When `odylith sync --check-only` complains about a governed field,
  pattern-match the failure message onto the CLI enumeration in the
  canonical policy instead of reaching straight for the Edit tool.

- Regression Tests Added: None executable yet; this is a policy-contract
  learning, not a runtime regression. The Casebook record itself plus
  the canonical CLI_FIRST_POLICY.md enumeration and the stanza
  rollout are the durable repo memory. Future work should consider a
  linter or pre-commit hook that greps agent diffs for direct edits
  against CLI-owned surfaces without a matching CLI invocation in the
  same turn.

- Monitoring Updates: Watch for future `odylith sync --check-only`
  failures whose repair diff targets governance surfaces listed in
  `CLI_FIRST_POLICY.md` without a paired CLI invocation upstream.

- Residual Risk: Agents may still hit novel governed surfaces whose CLI
  owner is not yet enumerated in the policy. The mitigation is to treat
  any missing enumeration as maintainer feedback, extend the policy
  document in the same slice, and prefer the CLI once it exists rather
  than hand-editing as a workaround.

- Related Incidents/Bugs:
  [2026-04-11-claude-host-profile-blanks-execution-model-via-supports-explicit-model-selection-flag.md](2026-04-11-claude-host-profile-blanks-execution-model-via-supports-explicit-model-selection-flag.md)

- Version/Build: Odylith product repo working tree on 2026-04-11, branch
  `2026/freedom/v0.1.11`.

- Config/Flags: None. The policy applies unconditionally to both Codex
  and Claude Code primary sessions and every routed delegation leaf.

- Customer Comms: The Odylith CLI is now the mandatory path for every
  governance operation that has a dedicated helper. Hand-editing
  governed surfaces (Radar ideas, technical-plan indexes, Registry
  FORENSICS sidecars, Atlas catalog projections, release-planning
  truth, and so on) is a policy violation when a CLI exists. The
  canonical policy and the authoritative CLI enumeration live in
  `odylith/agents-guidelines/CLI_FIRST_POLICY.md`.

- Code References: `odylith/agents-guidelines/CLI_FIRST_POLICY.md`,
  `odylith/agents-guidelines/CODING_STANDARDS.md`,
  `odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md`,
  `odylith/agents-guidelines/GROUNDING_AND_NARROWING.md`,
  `odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md`,
  `odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md`,
  `odylith/agents-guidelines/SECURITY_AND_TRUST.md`,
  `odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md`,
  `odylith/agents-guidelines/UPGRADE_AND_RECOVERY.md`,
  `odylith/agents-guidelines/VALIDATION_AND_TESTING.md`,
  `odylith/skills/*/SKILL.md`, `AGENTS.md`, `CLAUDE.md`,
  `odylith/AGENTS.md`, `odylith/CLAUDE.md`.

- Runbook References: `odylith/agents-guidelines/CLI_FIRST_POLICY.md`,
  `odylith/AGENTS.md`, `odylith/agents-guidelines/GROUNDING_AND_NARROWING.md`.

- Fix Commit/PR: Landing on branch `2026/freedom/v0.1.11` alongside the
  B-084/B-085 Claude-parity rollout.
