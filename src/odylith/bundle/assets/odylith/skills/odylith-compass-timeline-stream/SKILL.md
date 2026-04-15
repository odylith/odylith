# odylith-compass-timeline-stream

## CLI-First Non-Negotiable
- CLI-first is non-negotiable for both Codex and Claude Code. Remove all hand-authoring for places where Odylith CLI should be doing the heavy-lifting. When an Odylith CLI command exists for an operation, you must call the CLI command and you must not hand-edit governed files the CLI owns. Hand-authoring governed truth where a CLI exists is a hard policy violation, not a stylistic preference. The authoritative policy, CLI surface enumeration, allowed hand-edit surfaces, and failure-mode handling live in `odylith/agents-guidelines/CLI_FIRST_POLICY.md`, anchored by Casebook learning `CB-104`. The rule travels through routed `spawn_agent` leaves on Codex and Task-tool subagents on Claude Code, so delegated work inherits the same contract.

Use when logging bounded Compass timeline events for decisions, implementation updates, or execution statements.

## Canonical Commands

```bash
odylith compass log --repo-root . --kind decision --summary "<decision>"
odylith compass log --repo-root . --kind implementation --summary "<implementation update>"
odylith compass update --repo-root . --statement "<current execution state>"
odylith compass refresh --repo-root .
odylith compass deep-refresh --repo-root .
```

## Rules

- Keep summaries crisp, engineering-meaningful, and concrete enough that later Compass briefs can sound human without inventing connective tissue.
- Write timeline memory in ordinary words. It should sound like one maintainer carrying context forward for another, not like a polished dashboard caption.
- Avoid stock framing or dashboard-slogan wording in logged statements; Compass memory should retain real operator meaning, not repeated window leads, canned next/why/timing wrappers, benchmark-challenge slogans, or stagey phrases like `pressure point`, `muddy`, or `top lane` that later leak back into briefs.
- Do not encode `Executive/Product` or `Operator/Technical` labels into timeline memory. Compass briefs no longer carry a voice split, so memory should not seed one back into the surface later.
- Keep timeline memory deterministic and cheap to consume. Compass should reuse this stream for hot-path audits and brief context instead of spending model calls to reconstruct what the timeline already says.
- Include workstream, component, and artifact links whenever they are known.
- Treat timeline events as additive runtime evidence, not source-of-truth records.
