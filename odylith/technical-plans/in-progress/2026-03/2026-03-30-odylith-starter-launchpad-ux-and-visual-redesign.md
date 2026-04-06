Status: In progress

Created: 2026-03-30

Updated: 2026-03-30

Backlog: B-028

Goal: Make Odylith's first-run launchpad feel sharp, readable, and obviously
actionable by redesigning the starter-screen layout, hierarchy, responsive
presentation, and close/reopen flow around the prompt handoff and chosen-slice
context.

Assumptions:
- The onboarding logic already exposes the right underlying truth; the main
  gap is presentation and hierarchy.
- The first-run screen should optimize for one decisive next step, not equal
  weight across every support card.
- A product-quality first impression matters more now that the release is at
  GA.
- Closing the welcome state should feel temporary and recoverable, not like
  the user just lost the setup path.

Constraints:
- Keep the starter prompt contract and existing onboarding data truthful.
- Do not redesign unrelated shell surfaces in this slice.
- Keep the screen usable at common laptop widths without horizontal crowding.
- Do not let stale browser dismissal state suppress materially new onboarding
  guidance.

Reversibility: Reverting this slice restores the prior first-run layout and
styling without changing onboarding data, runtime state, or install behavior.

Boundary Conditions:
- Scope includes welcome-state HTML structure, launchpad styling, focused copy
  hierarchy, close/reopen affordances, rendered shell output, and browser
  evidence.
- Scope excludes broader shell redesign, dark-mode strategy, and non-onboarding
  runtime logic changes.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] The starter prompt does not dominate the screen strongly enough.
- [x] The current layout wastes space and feels visually muddy on laptop
      screens.
- [x] Supporting cards compete with the primary action instead of reinforcing
      it.
- [x] The first-run shell does not yet feel as polished as the underlying
      product contract.

## Success Criteria
- [x] The launchpad has one obvious primary action with a stronger visual
      hierarchy.
- [x] Chosen-slice context and support guidance remain visible but subordinate
      to the prompt handoff.
- [x] The screen feels intentional at both laptop and desktop widths.
- [x] The welcome state closes in a way that is explicit, reversible, and
      resilient to onboarding-shape changes.
- [x] Headless-browser screenshots show a materially improved first-run shell.

## Non-Goals
- [ ] Broad shell-wide visual redesign.
- [ ] Changing the governed-slice inference logic.
- [ ] Rewriting the starter prompt semantics.

## Impacted Areas
- [x] [shell_onboarding.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/shell_onboarding.py)
- [x] [tooling_dashboard_shell_presenter.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py)
- [x] [style.css](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/tooling_dashboard/style.css)
- [x] [page.html.j2](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/tooling_dashboard/page.html.j2)
- [x] [control.js](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js)
- [x] [test_shell_onboarding.py](/Users/freedom/code/odylith/tests/unit/runtime/test_shell_onboarding.py)
- [x] [test_render_tooling_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_tooling_dashboard.py)
- [x] [test_tooling_dashboard_onboarding_browser.py](/Users/freedom/code/odylith/tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py)

## Risks & Mitigations

- [ ] Risk: the new hero styling becomes louder but less legible.
  - [ ] Mitigation: keep typography and spacing crisp, and make the prompt
    card serve the action instead of ornament.
- [ ] Risk: responsive layout breaks at the exact narrow desktop widths users
    actually hit.
  - [ ] Mitigation: prove the rendered shell in a headless browser at realistic
    viewport sizes.
- [ ] Risk: layout changes accidentally regress copy-to-agent affordances.
  - [ ] Mitigation: preserve the existing copy button semantics and status
    feedback.
- [ ] Risk: persisted dismissal makes the welcome state feel stuck or lost.
  - [x] Mitigation: use a keyed dismissal token that changes when the
    onboarding shape changes, and keep a visible `Resume setup` recovery
    affordance in the shell header.
- [ ] Risk: stricter browser storage rules make dismissal persistence feel
    flaky.
  - [x] Mitigation: fall back from `localStorage` to `sessionStorage`, and
    still hide the welcome state immediately even if browser storage is
    unavailable.

## Validation/Test Plan
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_shell_onboarding.py tests/unit/runtime/test_render_tooling_dashboard.py`
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_tooling_dashboard --repo-root <temp-rehearsal-repo> --output odylith/index.html`
- [x] headless browser screenshot proof of the first-run launchpad
- [x] headless browser audit of dismiss, reload, reopen, Escape, CTA, truth,
      and keyed-reset paths
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
- [x] `git diff --check`

## Rollout/Communication
- [x] Keep the slice source-owned and bounded to the starter launchpad.
- [x] Capture browser evidence so the visual improvement is concrete, not just
      described.

## Current Outcome
- [x] Bound to `B-028`; the welcome state now renders as a centered launchpad
      hero with a prompt-dominant primary card, a chosen-slice/notice sidebar,
      and a cleaner action grid for backlog, Registry, and Atlas.
- [x] Low-confidence consumer repos no longer render fake repo-name-derived
      starter-slice details; they now fall back to honest generic guidance
      until a real repo path can be inferred.
- [x] The welcome state now closes via `Hide for now`, reopens from
      `Show starter guide` in the shell viewport, persists per onboarding
      shape, and resets
      automatically when the underlying onboarding state changes enough that
      Odylith should show setup again.
- [x] Focused onboarding/dashboard tests passed, and headless Chromium proof
      captured the refreshed first-run shell in a fresh consumer-style
      `rehearsal-repo`.
- [x] A deeper browser audit passed for dismiss, reopen, reload persistence,
      Escape handling, tab CTA navigation, truth completion, and stricter
      storage fallback behavior.
- [x] Browser proof now covers two hard failure modes explicitly: localStorage
      blocked with sessionStorage fallback, and total browser-storage denial
      where `Hide for now` still exits immediately but correctly returns on
      reload because persistence is impossible.
- [x] Browser proof now also covers the actual `odylith install` CLI path by
      rendering a real first-run launchpad after the install flow, not only a
      directly seeded renderer path.
- [x] The launchpad now uses explicit `Open <surface> view` actions plus short
      notes so first-time users understand that empty Radar, Registry, and
      Atlas views are live product surfaces, not broken placeholders.
