# odylith-github-release-closeout

Use this maintainer-only skill when the operator needs to prepare or apply
public GitHub issue updates for issues fixed in a release.

Do not mirror this skill into consumer-safe shared skills, `.agents/skills`,
`.claude/skills`, or bundled install assets.

## Rules

- Run closeout in draft mode before any public GitHub write.
- Run local Casebook release closeout before public GitHub closeout; do not
  hand-edit `FixedPendingRelease` records to `Closed`.
- Do not close issues before the release is marked shipped locally and the
  public GitHub release artifact is available.
- P0/P1 linked issues must have validation evidence in Casebook before closeout
  passes.
- Only `--apply-github` may post release comments, add closeout labels, or close
  issues.
- Keep Casebook status and public response fields aligned after public writes.

## Canonical Commands

```bash
./.odylith/bin/odylith github issue release-closeout \
  --repo odylith/odylith --release current --json
./.odylith/bin/odylith github issue release-closeout \
  --repo odylith/odylith --release current --apply-github --json
```

Local Casebook status closeout:

```bash
./.odylith/bin/odylith release casebook-closeout \
  --release current --json
./.odylith/bin/odylith release casebook-closeout \
  --release current --apply --json
```

## Closeout Checklist

- `pending` means fixed but not publicly released; it may draft a pending
  release comment but must not close.
- `closable` means local release state and public GitHub release availability
  both prove the fix is released.
- `blocked` means governance evidence is missing, the release is unknown, or
  the Casebook linkage is not safe enough to drive public closure.
- `already_closed` means GitHub is already closed; the pipeline should no-op
  instead of posting duplicate closure comments.
- Released-version comments should name the exact release tag.
- Closure must be idempotent in future passes; do not add ad hoc comments
  outside the pipeline.
