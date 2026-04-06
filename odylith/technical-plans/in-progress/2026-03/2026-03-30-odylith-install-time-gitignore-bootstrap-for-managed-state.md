Status: In progress

Created: 2026-03-30

Updated: 2026-03-30

Backlog: B-029

Goal: Make Odylith install create or update the root `.gitignore` with
`/.odylith/` even before `.git` exists, so managed runtime state stays
pre-ignored from the first consumer bootstrap.

Assumptions:
- A root `.gitignore` is a valid preparatory artifact even before `git init`.
- The user intent is to ignore Odylith-managed state whenever Odylith installs,
  not only after Git metadata already exists.
- The existing duplicate-detection logic is the right idempotency contract.

Constraints:
- Preserve the current `git_repo_present` summary flag semantics.
- Do not add unrelated ignore entries in this slice.
- Keep install, upgrade, and repair behavior deterministic and idempotent.

Reversibility: Reverting this slice returns install behavior to the older
Git-only guard without affecting existing consumer truth or runtime state.

Boundary Conditions:
- Scope includes the install helper, install/upgrade/repair call paths, and
  focused manager/CLI tests.
- Scope excludes Git repository initialization and broader install UX changes.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] The current helper exits early when `.git` is missing.
- [x] That guard prevents install from preparing the root `.gitignore` in
      freshly bootstrapped consumer folders.
- [x] The CLI already has a `gitignore_updated` summary path that can report
      this change cleanly.

## Success Criteria
- [x] Install writes `/.odylith/` into `.gitignore` whether or not `.git`
      exists.
- [x] Existing `.gitignore` files stay stable and do not duplicate the Odylith
      entry.
- [x] Focused manager and CLI tests prove the new behavior.

## Non-Goals
- [ ] Adding non-Odylith ignore entries.
- [ ] Removing the Git-missing operator caveat.
- [ ] Changing how install decides whether Git-aware features are available.

## Impacted Areas
- [x] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)

## Risks & Mitigations

- [ ] Risk: creating `.gitignore` before Git exists could feel unexpected.
  - [ ] Mitigation: keep the entry minimal and preserve the existing Git-missing
    caveat in CLI output.
- [ ] Risk: helper changes could regress idempotency and duplicate the ignore
    rule.
  - [ ] Mitigation: retain exact-pattern duplicate detection and cover it with
    focused integration tests.

## Validation/Test Plan
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/install/test_manager.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py`
- [x] `git diff --check`

## Rollout/Communication
- [x] Keep the change bounded to install hygiene.
- [x] Call out that the prepared `.gitignore` no longer depends on `.git`
      already existing.

## Current Outcome
- [x] Bound to `B-029`; install, upgrade, and repair now prepare the root
      `.gitignore` for `/.odylith/` even before `.git` exists, and focused
      manager/CLI coverage passed.
