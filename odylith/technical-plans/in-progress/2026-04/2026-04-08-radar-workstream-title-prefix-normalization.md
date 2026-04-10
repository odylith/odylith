Status: In progress

Created: 2026-04-08

Updated: 2026-04-08

Backlog: B-064

Goal: Remove the redundant `Odylith` prefix from Radar workstream titles in the
product repo, enforce the shorter title contract for new workstreams, and keep
the change governed through Radar, validation, and guidance updates.

Assumptions:
- Radar in this repo is already the Odylith product backlog, so a leading
  `Odylith` token in every title is redundant rather than informative.
- Existing consumers of workstream titles can tolerate shorter source titles as
  long as the underlying `idea_id` and file paths stay stable.
- File-path slugs can remain unchanged for now without undermining the title
  cleanup.

Constraints:
- Keep the naming rule product-repo-specific; do not rewrite consumer backlog
  truth by accident.
- Avoid growing the oversized backlog validator with another inline special
  case when a focused title helper can own the rule.
- Do not rename historical idea or plan file paths as part of this cleanup.

Reversibility: If the shorter-title contract proves wrong, the validation rule
and authoring normalization can be removed and titles can be re-prefixed from
source truth without changing workstream ids.

Boundary Conditions:
- Scope includes the title-normalization helper, backlog authoring, backlog
  validation, Radar source title cleanup, and guidance or spec updates.
- Scope excludes path renames, technical-plan filename normalization, and
  consumer-repo backlog migrations.

Related Bugs:
- no related bug found

## Learnings
- [ ] Product-scoped backlogs should not spend title width restating the product
      boundary on every row.
- [ ] Title normalization belongs in one shared contract so authoring and
      validation cannot drift.

## Must-Ship
- [ ] Add a dedicated backlog title contract helper for product-repo title
      normalization and validation.
- [ ] Normalize new backlog titles during product-repo authoring.
- [ ] Reject newly introduced prefixed titles during product-repo backlog
      validation.
- [ ] Remove the existing leading `Odylith` prefix from product-repo Radar
      workstream titles.
- [ ] Update Radar governance guidance to describe the shorter title contract.

## Should-Ship
- [ ] Add focused tests for both authoring normalization and validation
      failure.
- [ ] Refresh Radar and Compass surfaces in the same change so the shorter
      titles are visible immediately.

## Defer
- [ ] Historical plan filename renames.
- [ ] Any broader product-language cleanup outside workstream titles.

## Success Criteria
- [ ] Radar workstream titles in the product repo no longer begin with
      `Odylith`.
- [ ] `odylith backlog create` writes prefix-free titles in the product repo.
- [ ] Product-repo backlog validation fails closed when a prefixed title is
      reintroduced.

## Non-Goals
- [ ] Renaming legacy file paths.
- [ ] Changing consumer backlog title conventions.

## Open Questions
- [ ] Whether plan-display titles should eventually follow the same shorter
      naming contract.

## Impacted Areas
- [ ] [2026-04-08-radar-workstream-title-prefix-normalization.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-08-radar-workstream-title-prefix-normalization.md)
- [ ] [2026-04-08-radar-workstream-title-prefix-normalization.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-08-radar-workstream-title-prefix-normalization.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/radar/CURRENT_SPEC.md)
- [ ] [DELIVERY_AND_GOVERNANCE_SURFACES.md](/Users/freedom/code/odylith/odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md)
- [ ] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/delivery-governance-surface-ops/SKILL.md)
- [ ] [backlog_authoring.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/backlog_authoring.py)
- [ ] [backlog_title_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/backlog_title_contract.py)
- [ ] [validate_backlog_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/validate_backlog_contract.py)

## Validation
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_backlog_authoring.py tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_render_backlog_ui.py`
- [ ] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --runtime-mode standalone --proceed-with-overlap`
- [ ] `git diff --check`
