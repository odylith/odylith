# GitHub Issue Pipeline

## Purpose

Use this maintainer-only pipeline when an Odylith maintainer points at a
GitHub issue, asks for issue triage, or needs release closeout for linked
public bugs. The pipeline keeps public issue handling tied to Casebook truth
and release evidence instead of letting GitHub comments, labels, and local
governance drift independently.

Do not mirror this guideline into consumer-safe `odylith/agents-guidelines/`,
shared `odylith/skills/`, `.agents/skills`, `.claude/skills`, or bundled
install assets.

## Default Posture

- Draft first. A plain triage command may fetch public issue metadata and
  produce a plan, but it must not write labels, comments, or closures.
- Public writes require `--apply-github`.
- Internal governance writes require `--apply-governance`.
- Casebook is the primary truth for confirmed bugs.
- Radar, Registry, and Atlas change only when issue scope changes ownership,
  product direction, or component boundaries.

## Intake Flow

1. Fetch and classify:

   ```bash
   ./.odylith/bin/odylith github issue triage <issue-url-or-number> \
     --repo odylith/odylith --json
   ```

2. Inspect the plan:
   - issue metadata and evidence summary
   - severity, type, suspected component, and confidence
   - duplicate or matching Casebook candidates
   - proposed Casebook fields
   - proposed GitHub labels, comment, and close decision

3. Apply internal governance only when the Casebook match is correct:

   ```bash
   ./.odylith/bin/odylith github issue triage <issue-url-or-number> \
     --repo odylith/odylith --apply-governance --json
   ```

4. Apply GitHub writes only after the maintainer approves the exact public
   comment and labels:

   ```bash
   ./.odylith/bin/odylith github issue triage <issue-url-or-number> \
     --repo odylith/odylith --apply-github --json
   ```

## Release Closeout Flow

Before publish:

```bash
./.odylith/bin/odylith github issue release-closeout \
  --repo odylith/odylith --release current --json
```

- Linked fixed issues should remain pending.
- P0/P1 issues without Casebook validation evidence must block.
- No issue may close before the release is public.

After publish and maintainer approval:

```bash
./.odylith/bin/odylith github issue release-closeout \
  --repo odylith/odylith --release current --apply-github --json
```

- The command posts the released-version comment and closes only eligible
  linked issues.
- Already closed issues should stay deterministic and not receive duplicate
  closure intent in future hardening.

## Label Contract

The pipeline owns these label families:

- `severity:P0`, `severity:P1`, `severity:P2`
- `type:data-loss`, `type:install`, `type:upgrade`, `type:trust`, `type:ux`
- `component:migration-runtime`, `component:install`
- `release:0.1.12`
- `status:confirmed`, `status:needs-repro`,
  `status:fixed-pending-release`, `status:fixed-released`

If a label is absent, dry-run reports label creation. Only `--apply-github`
creates it.

## Casebook Linkage

Confirmed linked bugs may use:

- `GitHub Issue(s): odylith/odylith#21`
- `GitHub Status: confirmed | fixed_pending_release | fixed_released | closed | needs_info`
- `Fixed In: 0.1.12`
- `Public Response: pending | posted | close_pending | closed`

These fields are additive and optional for older records. P0/P1 linked issues
must also carry concrete validation evidence before release closeout passes.

## Guardrails

- Do not summarize a GitHub issue by memory when a fetch is possible.
- Do not create a duplicate Casebook bug when the plan finds a high-confidence
  existing match.
- Do not close issues from branch-local proof. Public release availability is
  required.
- Do not use GitHub labels as internal truth. Labels reflect the Casebook and
  release plan; they do not replace them.
- Do not post defensive or vague public comments. The drafted response should
  name the confirmed status, linked Casebook id, fixed version, release status,
  and validation summary.
