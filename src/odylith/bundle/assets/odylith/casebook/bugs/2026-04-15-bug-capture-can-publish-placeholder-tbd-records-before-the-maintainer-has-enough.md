- Bug ID: CB-114

- Status: Open

- Created: 2026-04-15

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: `odylith bug capture` could publish a new Casebook bug record
  with placeholder `TBD` intake fields even when the caller had not yet
  provided enough grounded failure evidence to make the record trustworthy.

- Impact: Casebook could immediately render authoritative-looking bug truth that
  was visibly incomplete, which poisoned governed product memory, misled
  maintainers about the actual state of an incident, and taught Codex/Claude
  fast paths to capture bugs before they had the facts.

- Components Affected: `src/odylith/runtime/governance/bug_authoring.py`,
  `src/odylith/runtime/intervention_engine/apply.py`,
  `src/odylith/runtime/intervention_engine/engine.py`,
  `src/odylith/runtime/analysis_engine/show_capabilities.py`,
  `odylith/skills/odylith-casebook-bug-capture/SKILL.md`,
  `odylith/skills/odylith-casebook-bug-preflight/SKILL.md`,
  and the shared Casebook bug-authoring contract.

- Environment(s): Odylith product-repo maintainer mode, detached
  `source-local`, branch `2026/freedom/v0.1.11`, plus any Codex or Claude lane
  that invoked `odylith bug capture` through the shared CLI contract.

- Detected By: Maintainer review of the rendered Casebook detail for `CB-114`
  immediately after capture on 2026-04-15.

- Failure Signature: A freshly captured bug rendered literal placeholder values
  such as `Reproducibility: TBD`, `Impact: TBD — describe the user-facing
  consequences.`, `Failure Signature: TBD`, and `Trigger Path: TBD` instead of
  failing the capture or waiting for grounded evidence.

- Trigger Path: `./.odylith/bin/odylith bug capture --repo-root . --title ...`
  with only the old legacy fields (`title`, `component`, `severity`) or any
  automated path that called the same backend without richer evidence.

- Ownership: Casebook bug-authoring contract, shared Codex/Claude bug-capture
  guidance, and automated casebook-create apply logic.

- Timeline: Captured 2026-04-15 through `odylith bug capture`; root cause and
  contract hardening identified in the same maintainer recovery pass.

- Blast Radius: New Casebook bug truth, intervention-engine casebook-create
  proposals, show-surface bug suggestions, and any operator or agent relying on
  Casebook as durable engineering memory.

- SLO/SLA Impact: Direct P0 product-trust hit for governed memory because a
  visible first-hop authoring command could publish ungrounded records into an
  authoritative surface.

- Data Risk: Low product-data loss risk, high governed-memory integrity risk.

- Security/Compliance: No direct security issue; the main failure is false
  authority in bug-memory capture.

- Invariant Violated: New Casebook bug capture must either record grounded
  intake evidence or fail closed. It must not emit placeholder stand-ins as if
  they were real bug facts.

- Workaround: Do not run `odylith bug capture` until the minimum intake fields
  are known; enrich or reopen an existing bug manually if the record already
  exists.

- Root Cause: The bug-authoring backend hardcoded a placeholder markdown
  template with `TBD` values and accepted title-only captures as valid writes.
  Shared guidance and automated call sites reused that weak contract, so the
  product kept teaching the same low-evidence capture path.

- Solution: Replace the placeholder template with a fail-closed minimum-evidence
  contract, require structured intake fields on the CLI, make automated
  casebook-create paths validate the same fields before apply, and update the
  shared bug-capture/preflight guidance used by both Codex and Claude.

- Verification: `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py -k bug_capture`
  and `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_engine_apply.py tests/unit/runtime/test_intervention_engine.py`
  passed after the fail-closed bug-capture contract landed.

- Prevention: Keep `odylith bug capture` fail closed, reject placeholder-like
  values, require the same minimum evidence across manual and automated entry
  points, and keep the shared Codex/Claude bug-capture guidance aligned with
  the backend contract.

- Agent Guardrails: Do not call `odylith bug capture` from a title alone. Gather
  the minimum evidence first: reproducibility, impact, environment, detected
  by, failure signature, trigger path, ownership, blast radius, SLO/SLA impact,
  data risk, security/compliance, and invariant violated.

- Preflight Checks: Search for an existing Casebook bug first, confirm the
  affected component boundary, and ensure the minimum evidence set is grounded
  before capture.

- Regression Tests Added: Focused CLI bug-capture tests for missing-evidence and
  placeholder rejection, plus intervention-engine tests that keep casebook
  create preview-only until the same evidence contract is satisfied.

- Monitoring Updates: The Casebook capture path now surfaces missing-evidence
  failures immediately at CLI/apply time instead of silently creating low-signal
  bug truth.

- Related Incidents/Bugs: [2026-04-14-forwarded-cli-help-hides-backend-flags-and-selective-sync-stays-too-wide-for-gov.md](2026-04-14-forwarded-cli-help-hides-backend-flags-and-selective-sync-stays-too-wide-for-gov.md)
  and [2026-04-15-benchmark-sharded-proof-can-lose-final-shard-artifacts-and-authoritative-active-.md](2026-04-15-benchmark-sharded-proof-can-lose-final-shard-artifacts-and-authoritative-active-.md)

- Code References: `src/odylith/runtime/governance/bug_authoring.py`
  `src/odylith/runtime/intervention_engine/apply.py`
  `src/odylith/runtime/intervention_engine/engine.py`
  `odylith/skills/odylith-casebook-bug-capture/SKILL.md`
