# GitHub Issue Pipeline

## Overview

GitHub Issue Pipeline is the governed intake and closeout lane for public
GitHub issues that need Odylith maintainer action. It turns a raw issue URL
into a draft-first plan that fetches evidence, classifies severity and type,
links Casebook truth, drafts labels and public comments, and later gates
release closeout without closing issues before artifacts are public.

## Boundary

- **Logical boundary**: Own GitHub issue fetch/normalization, issue-reference
  parsing, severity/type/component classification, Casebook matching, internal
  governance mutation planning, public GitHub mutation planning, issue sweep,
  and release closeout. The boundary is split into explicit phase owners:
  models (`github_issue_models.py`), reference parsing
  (`github_issue_references.py`), GitHub transport (`github_issue_transport.py`),
  Casebook/release truth (`github_issue_casebook.py`), classification and
  public-response policy (`github_issue_policy.py`), orchestration
  (`github_issue_pipeline.py`), and CLI adaptation (`github_issue_cli.py`).
- **Evidence anchors**:
  `src/odylith/runtime/governance/github_issue_casebook.py`,
  `src/odylith/runtime/governance/github_issue_pipeline.py`,
  `src/odylith/runtime/governance/github_issue_policy.py`,
  `src/odylith/runtime/governance/github_issue_models.py`,
  `src/odylith/runtime/governance/github_issue_references.py`,
  `src/odylith/runtime/governance/github_issue_cli.py`,
  `src/odylith/runtime/governance/github_issue_transport.py`,
  and `tests/unit/runtime/test_github_issue_pipeline.py`.
- **Kind**: governance_engine
- **Status**: active

## Contract

- Public GitHub writes are draft-first. `triage`, `sweep`, and
  `release-closeout` may fetch public issue/release state, but labels,
  comments, and closures require `--apply-github`.
- `--apply-github` must fail closed when the intake plan has no linked
  Casebook record. The pipeline may draft `status:needs-repro`, but it must
  not post a confirmed/fixed public response before internal truth exists.
- Casebook is the primary internal truth. Confirmed bugs link public issues
  through `GitHub Issue(s)`, `GitHub Status`, `Fixed In`, and
  `Public Response` fields.
- `IssueIntakePlan` must include issue metadata, evidence summary, suspected
  component, severity, issue types, confidence, duplicate Casebook candidates,
  recommended governance mutations, and recommended GitHub mutations.
- `GitHubMutationPlan` must list missing labels to create, labels to add,
  comment body, closure decision, and any blocked reason.
- `ReleaseIssueCloseoutPlan` must distinguish pending, closable, and blocked
  linked issues. P0/P1 issues require validation evidence in Casebook before
  release closeout can pass.
- Before public release availability, closeout can only draft or post a fixed
  pending release comment. After public artifacts exist, closeout can draft or
  apply the released-version comment and closure.
- After public release availability, closeout may close only when the issue
  state is confirmed open. Unknown issue state is blocked, not assumed safe.
- The pipeline may update Registry or Radar only when an issue changes
  ownership or scope. Routine confirmed bugs link to Casebook first.

## CLI Surface

- `odylith github issue triage <issue-url-or-number> --repo odylith/odylith --json`
- `odylith github issue triage ... --apply-governance`
- `odylith github issue triage ... --apply-github`
- `odylith github issue sweep --repo odylith/odylith --state open --json`
- `odylith github issue release-closeout --release current --json`

## Dependencies

- Upstream: GitHub REST API through `GITHUB_TOKEN` or `GH_TOKEN` for writes;
  unauthenticated reads may work for public issues.
- Upstream: Casebook markdown source validation and bug-index sync.
- Downstream: maintainer release gates, Casebook records, public GitHub labels,
  comments, and issue closure.
- Governance: CB-136 and the active 0.1.12 release lane.

## Test Coverage

- Unit: `tests/unit/runtime/test_github_issue_pipeline.py` covers issue
  URL/number parsing, issue #21 classification, Casebook matching, governance
  application, GitHub write gating, explicit fake-transport GitHub apply,
  deterministic sweep ordering, release pending/closable/blocked closeout,
  no-Casebook fail-closed apply, missing label creation, unknown issue-state
  closeout blocking, cross-repo closeout filtering, structural boundary
  ownership, and Casebook capture linkage fields.
- CLI: `tests/unit/runtime/test_github_issue_pipeline.py` calls
  `odylith github issue triage` through the top-level CLI with fake GitHub
  transport so CI never writes to public GitHub.

## Feature History

- 2026-04-29: Registered the GitHub Issue Pipeline for 0.1.12 so maintainers can point Odylith at issue #21, link CB-136, draft labels/comments, and keep release closeout blocked until v0.1.12 is public. (Plan: [B-127](odylith/radar/radar.html?view=plan&workstream=B-127); Casebook: CB-136)
- 2026-04-29: Split the pipeline into explicit models, references, Casebook, policy, transport, orchestration, and CLI owners; added fail-closed no-Casebook public-write behavior and unknown issue-state release-closeout blocking. (Plan: [B-127](odylith/radar/radar.html?view=plan&workstream=B-127); Casebook: CB-136)
