# Governance authoring and recovery

Use this runbook when a governed record is missing, invalid, stale, or unexpectedly
quiet. It covers source authoring and projection upkeep, not release qualification.
Run commands from the target repository root through its installed `odylith` CLI.
Start with `odylith start --repo-root .`; resolve the exact workstream, bug, or
component using `odylith context --repo-root . <reference>` before changing truth.
Keep existing user changes and extend an existing record when it already owns the
failure. Installation problems use the [install and upgrade runbook](../../odylith/INSTALL_AND_UPGRADE_RUNBOOK.md).

## Radar titles and release-targeted intake

Use `odylith backlog create --help` to inspect the current intake contract.
Supply grounded Problem, Customer, Opportunity, Product View, Success Metrics,
Domain Risk, and Security Posture fields; a title alone is not a valid workstream.
In the Odylith product repository, name the actual slice without an `Odylith`
title prefix. This naming rule is not a license to remove a consumer's product
name or change the scope of existing work.

First submit the complete intended arguments with `--dry-run --json`. Review the
candidate's title, responsibility, scope, and any release assignment. Only then
repeat that same intake without `--dry-run` when creation is authorized. The
optional `--release` selects a release; omission leaves release targeting
unassigned. Check the selector with `odylith release --help` and the release list
before using it. Do not copy a release ID from an old plan or edit assignment
event files by hand.

If intake is rejected, correct the indicated evidence or selector before retrying;
do not create a title-only record and fill it later. For an existing title defect,
change only the authored title in the owning idea document, then run selective
sync for that path. Do not change its ID, lineage, status, or assignment to obtain
a formatting pass. Verify the Radar row and detail view refer to the same record.

## Evidence-complete Casebook capture

Search for an existing case first. Use `odylith bug capture --help` and submit a
complete `--dry-run --json` intake: failure signature, trigger, invariant, impact,
affected component, environment, detection, ownership, blast radius, data risk,
SLO impact, and security/compliance posture. Distinguish an observed root cause
from a hypothesis. State an unknown honestly; do not replace missing repro
evidence with generic filler.

After a successful dry-run and authorized capture, retain the returned bug ID
and path. Run `odylith casebook validate --repo-root .`; verify the Casebook detail
shows the actual trigger, consequence, and remaining proof. For additional
evidence on an existing case, update its authored narrative, not the derived
index or payload. Use `odylith casebook refresh --repo-root .` after the update.
A captured case is not a proven fix. Keep release closure under the existing
release closeout command and never close a case merely because capture passed.

## Registry forensic coverage

Resolve the exact component and compare its registered paths and current spec
with the changed source. A generated mirror is evidence about its source owner,
not automatically a separate component. Distinguish explicit Compass events,
tracked-path changes, and mapped workstream evidence; a synthetic workspace
event alone does not establish current implementation progress.

After correcting actual source mappings or authored specification evidence, run
`odylith governance sync-component-spec-requirements --repo-root .`, then
`odylith registry refresh --repo-root .`. These commands write derived forensic
and surface data. Never hand-edit `FORENSICS.v1.json` or add fake Compass events
to make a component look active. Verify the detail view retains its real spec,
current code links, and an honest coverage state. If it remains evidence-empty,
record the missing channel; do not reinterpret “empty” as “healthy.”

## Quiet scopes and the Scope Signal Ladder

Use the exact-reference context and existing delivery evidence to distinguish
intentional suppression from stale or missing data. The shared `scope_signal`
owns the rung and compute budget; individual surfaces must not independently
raise priority from file counts or borrow another scope's activity. The ladder
and budget meanings are defined in the
[delivery contract](../../odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md).

For an actual source correction, run selective sync for that path. Use
`odylith compass refresh --repo-root .` for quick visibility of current recorded
state; an explicitly requested narrated brief uses `odylith compass deep-refresh
--repo-root .`. A failed or missing fresh brief must remain unavailable, not be
replaced with invented narration. Check the normal view, an explicitly linked
quiet scope, and the degraded view separately. A quiet but accessible scope can
be correct; missing native chat delivery needs host-specific
`odylith codex intervention-status` or `odylith claude intervention-status` proof.

## Plan references, risk formatting, and safe settlement

Run `odylith validate plan-traceability --repo-root .` and
`odylith validate plan-risk-mitigation --repo-root .` before settlement. Active
plan discovery includes dated directories. A zero-record check is not evidence
that existing plans passed. Link current runbooks, developer docs, and source
owners in each plan's Traceability section; explain partial coverage and do not
restore retired modules or link unrelated documents to satisfy a bucket.

Risk formatting is owned by
`odylith governance normalize-plan-risk-mitigation --repo-root .`. Before adopting
a changed normalizer, compare its proposed bytes with the authored source and
rendered Markdown. Wrapping, examples, and quoting must not invent or detach
risk/mitigation records. Existing historical corruption needs source-grounded
review; a formatter cannot reconstruct missing meaning.

After authorized source updates, run `odylith sync --repo-root . --impact-mode
selective <changed-path>` and then `odylith sync --repo-root . --check-only`.
If validation fails, preserve the specific error and repair its owning source;
do not bypass the gate or overwrite unrelated changes. Compare the resulting
source diff and affected dashboard detail before committing. Recovery from an
erroneous authored update is a reviewed source correction followed by the same
canonical refresh, not a reset of the whole repository.
