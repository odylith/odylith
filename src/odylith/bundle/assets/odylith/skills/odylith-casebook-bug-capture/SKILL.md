# odylith-casebook-bug-capture

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

Use when capturing a new Casebook bug record or updating an open bug with fresh evidence, especially when a named failure mode or repeated-debug loop needs durable repo memory in the same turn.

## Rules

- Search for an existing bug first; update, reopen, or consolidate the existing record before creating a parallel duplicate.
- Give every new bug record a stable `Bug ID` in the `CB-###` sequence and keep that ID unchanged when the title, status, or file location evolves.
- Do not call `odylith bug capture` until you have the minimum grounded intake evidence in hand:
  `component`, `reproducibility`, `impact`, `environment`, `detected by`,
  `failure signature`, `trigger path`, `ownership`, `blast radius`,
  `SLO/SLA impact`, `data risk`, `security/compliance`, and the
  `invariant violated`.
- Pass `reproducibility` as one compact token such as `High`, `Medium`, `Low`,
  `Always`, `Intermittent`, or `Consistent`; never put commands, screenshots,
  proof shard ids, or prose in that field.
- If those fields are not yet grounded, keep investigating or update an
  existing bug later. Do not publish a low-evidence placeholder bug record.
- If Casebook source truth has been hand-edited or looks suspect, run
  `odylith casebook validate --repo-root .`; Casebook refresh must fail closed
  on invalid bug markdown before publishing generated surfaces.
- Keep the bug narrative factual and reproduction-oriented.
- Link the affected workstream, components, tests, and artifacts explicitly.
- Link the affected diagrams, validation obligations, and next guardrails or preflight checks whenever they are known.
- Refresh governed Odylith surfaces after meaningful bug truth changes.

## Canonical Commands

```bash
./.odylith/bin/odylith bug capture --repo-root . \
  --title "<bug title>" \
  --component "<component>" \
  --reproducibility "High" \
  --impact "<user or operator impact>" \
  --environment "<lane or environment>" \
  --detected-by "<how it was detected>" \
  --failure-signature "<concrete failure signature>" \
  --trigger-path "<command or workflow path>" \
  --ownership "<owning boundary>" \
  --blast-radius "<affected surfaces or operators>" \
  --slo-impact "<delivery or SLA impact>" \
  --data-risk "<data risk posture>" \
  --security-compliance "<security/compliance posture>" \
  --invariant-violated "<broken invariant>"
./.odylith/bin/odylith casebook validate --repo-root .
./.odylith/bin/odylith compass log --repo-root . --kind implementation --summary "<bug capture update>"
./.odylith/bin/odylith sync --repo-root . --force
```
