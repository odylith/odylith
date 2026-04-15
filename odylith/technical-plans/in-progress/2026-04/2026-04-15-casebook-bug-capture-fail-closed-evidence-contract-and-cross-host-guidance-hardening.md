Status: In progress

Created: 2026-04-15

Updated: 2026-04-15

Backlog: B-097

Goal: Make `odylith bug capture` fail closed when the caller cannot provide
enough grounded evidence to publish a real Casebook record, remove placeholder
`TBD` bug emission from the shared backend, and align the shared Codex/Claude
guidance plus automated call sites so bug capture only runs after minimum bug
evidence is present.

Assumptions:
- The Casebook markdown file remains the authoritative bug record and should not
  carry placeholder claims as if they were governed truth.
- Root cause, fix, and prevention are often discovered later, so the capture
  contract should require strong intake evidence without pretending the full
  investigation is already complete.
- The shared `odylith/skills/odylith-casebook-bug-capture/` skill is the
  cross-host guidance surface because Claude reuses it through
  `.claude/skills/odylith-casebook-bug-capture/SKILL.md`.

Constraints:
- Do not keep the old placeholder-writing path behind a silent fallback.
- Do not weaken bug capture into a title-only fast path for automation or
  intervention proposals.
- Do not invent fake evidence fields just to satisfy the minimum contract.
- Keep the fix shared across Codex and Claude surfaces instead of forking host
  behavior.

Reversibility: The fail-closed capture contract is additive. If the first
minimum-evidence threshold proves too strict, the fallback is to adjust the
required field set and keep the no-placeholder invariant rather than reviving
`TBD` record emission.

Boundary Conditions:
- Scope includes the bug-authoring backend, the public `odylith bug capture`
  CLI flags and validation, the intervention-engine casebook create path, the
  shared bug-capture skill and preflight guidance, and the touched Casebook
  component/governance records.
- Scope excludes Casebook renderer redesign, broad bug-schema expansion beyond
  the fields needed for fail-closed capture, and unrelated benchmark quality
  fixes outside the active benchmark recovery slice.

Related Bugs:
- [CB-114](../../../casebook/bugs/2026-04-15-bug-capture-can-publish-placeholder-tbd-records-before-the-maintainer-has-enough.md)
  tracks the product failure where `odylith bug capture` can publish placeholder
  `TBD` records as authoritative bug truth.

## Learnings
- [ ] A governed bug record is not trustworthy just because it has a stable
      `CB-###` id; the intake evidence has to be real and explicit.
- [ ] Shared cross-host guidance has to carry the bug-capture minimum-evidence
      contract or the backend will keep receiving title-only calls.
- [ ] Automated casebook-create paths must fail closed when they cannot satisfy
      the same capture evidence contract that human operators use.

## Must-Ship
- [ ] Replace placeholder bug markdown generation in
      `src/odylith/runtime/governance/bug_authoring.py` with a minimum-evidence
      contract and optional grounded field emission.
- [ ] Extend `odylith bug capture --help` and the backend parser so callers can
      provide structured intake evidence instead of only title/component.
- [ ] Make `capture_bug(...)` reject incomplete bug captures with a precise
      error listing the missing minimum fields.
- [ ] Remove the fake default detector path and any other misleading synthetic
      bug-intake defaults.
- [ ] Harden the intervention-engine casebook-create path so it only auto-applies
      when the proposal payload carries valid capture evidence.
- [ ] Update the shared bug-capture skill and bug-preflight guidance so Codex
      and Claude gather minimum evidence before invoking `odylith bug capture`.
- [ ] Enrich `CB-114` with the real failure signature, trigger path, impact,
      and prevention details once the capture contract is understood.

## Should-Ship
- [ ] Bind the new bug-capture workstream to the active `0.1.11` release lane.
- [ ] Add one focused Casebook component-spec history note for the fail-closed
      capture contract.
- [ ] Make the bug-capture JSON output report whether the capture satisfied the
      fail-closed intake contract.

## Defer
- [ ] Broader Casebook schema redesign or renderer-side intake workflows.
- [ ] Hosted multi-step bug-investigation assistants beyond the minimum shared
      CLI-backed capture contract.

## Success Criteria
- [ ] `odylith bug capture` no longer writes `TBD` placeholders into new bug
      markdown.
- [ ] A title-only capture attempt fails with a clear missing-evidence error.
- [ ] Shared Codex/Claude guidance tells the operator to gather the same
      minimum evidence the backend requires.
- [ ] Automated casebook-create paths cannot silently create low-evidence bug
      records.
- [ ] Focused validation is green on the backend, intervention, and guidance
      surfaces touched by this slice.

## Impacted Areas
- [ ] [2026-04-15-casebook-bug-capture-fail-closed-evidence-contract-and-cross-host-guidance-hardening.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-15-casebook-bug-capture-fail-closed-evidence-contract-and-cross-host-guidance-hardening.md)
- [ ] [2026-04-15-casebook-bug-capture-fail-closed-evidence-contract-and-cross-host-guidance-hardening.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-15-casebook-bug-capture-fail-closed-evidence-contract-and-cross-host-guidance-hardening.md)
- [ ] [src/odylith/runtime/governance/bug_authoring.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/bug_authoring.py)
- [ ] [src/odylith/runtime/intervention_engine/apply.py](/Users/freedom/code/odylith/src/odylith/runtime/intervention_engine/apply.py)
- [ ] [odylith/skills/odylith-casebook-bug-capture/SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-casebook-bug-capture/SKILL.md)
- [ ] [odylith/skills/odylith-casebook-bug-preflight/SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-casebook-bug-preflight/SKILL.md)
- [ ] [odylith/registry/source/components/casebook/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/casebook/CURRENT_SPEC.md)
- [ ] [tests/unit/test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [ ] [tests/unit/runtime/test_intervention_engine_apply.py](/Users/freedom/code/odylith/tests/unit/runtime/test_intervention_engine_apply.py)

## Validation
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py -k bug_capture`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_engine_apply.py`
- [ ] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_render_casebook_dashboard.py`
- [ ] `./.odylith/bin/odylith validate backlog-contract --repo-root .`
- [ ] `./.odylith/bin/odylith validate component-registry --repo-root .`
- [ ] `git diff --check`
