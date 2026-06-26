# odylith-github-issue-triage

## Governance-Learning Default
Before acting on a durable error, escaped defect, failed mechanism, failed simulation, bad generated artifact, semantic drift, quality-gate miss, latency breach, architecture decision, validation result, or release-risk learning, search Casebook and related governance truth first. Read prior failed mechanisms, failed fix attempts, rejected approaches, guardrails, and validation history; do not repeat a fix path that already failed. Capture new mechanism-level learning in Casebook or Compass, and update Radar or plans, Registry, and Atlas when the learning changes planned work, component contracts, or flows.

Use this maintainer-only skill when the operator gives a GitHub issue URL or
number and wants Odylith to fetch it, classify it, map it to
Casebook/Radar/Registry truth, and draft the public GitHub response.

Do not mirror this skill into consumer-safe shared skills, `.agents/skills`,
`.claude/skills`, or bundled install assets.

## Rules

- Run the pipeline before writing any governance record by hand.
- Default to draft mode. Do not post comments, create labels, add labels, or
  close issues unless the operator explicitly approves `--apply-github`.
- Use `--apply-governance` only after the Casebook match is clearly correct.
- Casebook is primary truth for confirmed bugs; GitHub labels and comments are
  public reflections of that truth.
- Do not create a duplicate Casebook bug when the plan finds a high-confidence
  existing record.
- If the issue changes component ownership or product scope, update Registry or
  Radar in the same governed slice after the Casebook link is correct.

## Canonical Commands

```bash
./.odylith/bin/odylith github issue triage <issue-url-or-number> \
  --repo odylith/odylith --json
./.odylith/bin/odylith github issue triage <issue-url-or-number> \
  --repo odylith/odylith --apply-governance --json
./.odylith/bin/odylith github issue triage <issue-url-or-number> \
  --repo odylith/odylith --apply-github --json
```

## Review Checklist

- The plan names the issue number, title, state, author, labels, and URL.
- Severity, type, component, and confidence are grounded in issue evidence.
- Duplicate Casebook candidates are explained and ranked.
- The Casebook mutation includes `GitHub Issue(s)`, `GitHub Status`,
  `Fixed In`, and `Public Response` when the bug is confirmed.
- The GitHub mutation plan lists labels to create, labels to add, the exact
  comment body, and the close decision.
- Public writes are empty unless `--apply-github` was explicitly passed.

## Issue #21 Expected Shape

Issue #21 should classify as `P0`, `type:data-loss`, `type:install`, and
`component:migration-runtime`; match `CB-136`; plan `Fixed In: 0.1.12`; and
draft a fixed-pending-release response without closing the issue.
