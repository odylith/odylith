Status: In progress

Created: 2026-03-30

Updated: 2026-04-07

Backlog: B-030

Goal: Make consumer upgrades refresh the local shell immediately and surface a
closeable in-dashboard release spotlight that shows the version jump and the
strongest release highlights over the operator's current Odylith surface, with
a local authored release note and a safe recovery path after close, while
hardening reinstall, launcher recovery, dashboard refresh, and Mermaid failure
legibility for the release lane.

Assumptions:
- Consumer upgrade is the right place to trigger shell refresh because it owns
  the operator workflow that just activated the new runtime.
- A repo-local runtime payload under `.odylith/` is the right home for
  ephemeral release spotlight state.
- The shell should dismiss the spotlight client-side without mutating repo
  truth.
- If the operator closes the spotlight accidentally, the shell should offer a
  low-friction way to reopen it for the current upgraded version.
- First install should stay on the normal launchpad path even if stale
  spotlight state is present under `.odylith/`.
- Consumer reinstall and repair must stay on verified release assets only; no
  host-Python fallback or source-local escape hatch is acceptable in the
  public consumer lane.
- A narrow dashboard refresh command is safer than changing full `odylith sync`
  semantics right before release.
- The canonical hosted bootstrap and rescue command is
  `curl -fsSL https://odylith.ai/install.sh | bash`, and the install/upgrade
  docs plus agent guidance should all name that same entrypoint.

Constraints:
- Keep the feature consumer-lane only.
- Keep release copy crisp: versions plus at most three bullets.
- Align the popup styling with the current dashboard launchpad language.
- Do not invent a fake full-stage backdrop; keep the real Odylith surface
  visible behind the spotlight.
- Do not reintroduce same-version live-runtime restaging during plain upgrade.
- Do not make shell refresh mutate Registry forensic truth unless the operator
  explicitly asked for that broader surface work.

Reversibility: Reverting this slice removes the spotlight, reinstall command,
and narrow dashboard refresh path and returns release upkeep to the previous
install/upgrade/sync posture without affecting verified runtime assets.

Boundary Conditions:
- Scope includes reinstall and upgrade CLI flow, launcher recovery guidance,
  narrow dashboard refresh execution, spotlight payload persistence, shell
  render and client behavior, Mermaid worker failure reporting, and browser
  proof.
- Scope excludes hosted release-note publishing and broader dashboard redesign.

Related Bugs:
- [2026-03-28-public-consumer-install-depends-on-machine-python.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-public-consumer-install-depends-on-machine-python.md)
- [2026-03-28-first-install-and-same-version-upgrade-mutate-live-runtime-before-fail-closed-proof.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-first-install-and-same-version-upgrade-mutate-live-runtime-before-fail-closed-proof.md)
- [2026-04-02-atlas-refresh-diagnostics-and-surface-selection-clarity.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-02-atlas-refresh-diagnostics-and-surface-selection-clarity.md)
- [2026-04-03-upgrade-spotlight-live-refresh-updates-version-badge-but-keeps-release-note-hidden.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-03-upgrade-spotlight-live-refresh-updates-version-badge-but-keeps-release-note-hidden.md)

## Context/Problem Statement
- [x] Consumer upgrade currently does not guarantee an immediate shell refresh.
- [x] The dashboard has no first-class post-upgrade release announcement.
- [x] The product loses a high-value “what changed” moment after activation.
- [x] Consumer reinstall semantics are surprising because `install` does not
      adopt the latest verified release and repo pin in one step.
- [x] Missing-launcher recovery still depends too much on operator intuition.
- [x] Broad `odylith sync --force --impact-mode full` is heavier than a simple
      shell-facing refresh should be.
- [x] Mermaid worker failure can read like a hang instead of a named blocking
      diagram with clear fallback progress.
- [x] Default `odylith dashboard refresh` can leave Compass stale and does not
      say plainly which surfaces were included versus excluded.
- [x] Atlas parse failures still arrive too late and with too little path or
      line context during bulk refresh.

## Success Criteria
- [x] Consumer upgrade refreshes shell surfaces automatically after success.
- [ ] Steady-state consumer freshness lands before commit through the broader
      runtime-freshness posture tracked in `B-025`; upgrade-time refresh is the
      first step, not the whole answer.
- [ ] Consumer `odylith reinstall --latest` safely adopts the latest verified
      release and repo pin in one step.
- [ ] Missing-launcher recovery is first-class and does not require another
      Odylith checkout.
- [x] `odylith dashboard refresh` refreshes shell-facing surfaces without
      forcing Registry forensic churn.
- [x] `odylith dashboard refresh` includes Compass by default, prints included
      versus excluded surfaces, and shows the exact Atlas follow-up when Atlas
      is stale but excluded.
- [x] The dashboard renders a closeable release spotlight with from/to versions.
- [x] The spotlight shows up to three release bullets and dismisses persistently in-browser.
- [x] The spotlight closes via circular `X`, outside click, and Escape, then
      reopens from a version-scoped toolbar affordance.
- [x] The spotlight returns over the remembered shell surface after refresh
      instead of forcing a fallback tab.
- [x] First install and launchpad flows do not show the upgrade spotlight.
- [x] The dashboard generates a crisp repo-local release note for
      the upgraded version.
- [x] Release prep carries an authored `v0.1.9` note and the shell consumes
      that authored title and highlight copy in the upgrade moment.
- [x] Consumer upgrades keep only the current release note and remove older
      release-note artifacts from the repo.
- [x] Atlas sync fails fast on invalid Mermaid with diagram id, source path,
      and parse line before the bulk render path starts.
- [x] Focused CLI, onboarding, and dashboard tests pass.
- [x] Headless browser proof captures the new popup.

## Non-Goals
- [ ] Product-repo maintainer upgrade changes.
- [ ] Adding hosted release telemetry.
- [ ] Reworking unrelated dashboard panels.
- [ ] Rewriting the full `odylith sync` contract for every surface.
- [ ] Treating commit-time autofix as the primary consumer freshness posture.

## Impacted Areas
- [x] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [state.py](/Users/freedom/code/odylith/src/odylith/install/state.py)
- [ ] [runtime.py](/Users/freedom/code/odylith/src/odylith/install/runtime.py)
- [x] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [x] [auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py)
- [x] [shell_onboarding.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/shell_onboarding.py)
- [x] [render_tooling_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_tooling_dashboard.py)
- [x] [tooling_dashboard_shell_presenter.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py)
- [x] [control.js](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js)
- [x] [style.css](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/tooling_dashboard/style.css)
- [x] [INSTALL_AND_UPGRADE_RUNBOOK.md](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith/INSTALL_AND_UPGRADE_RUNBOOK.md)
- [ ] [FAQ.md](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith/FAQ.md)
- [ ] [README.md](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith/README.md)
- [ ] [AGENTS.md](/Users/freedom/code/odylith/odylith/AGENTS.md)
- [ ] [UPGRADE_AND_RECOVERY.md](/Users/freedom/code/odylith/odylith/agents-guidelines/UPGRADE_AND_RECOVERY.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-delivery-governance-surface-ops/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith/skills/odylith-delivery-governance-surface-ops/SKILL.md)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [ ] [test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)
- [x] [test_shell_onboarding.py](/Users/freedom/code/odylith/tests/unit/runtime/test_shell_onboarding.py)
- [x] [test_render_tooling_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_tooling_dashboard.py)
- [x] [test_tooling_dashboard_onboarding_browser.py](/Users/freedom/code/odylith/tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py)
- [x] [test_release_notes.py](/Users/freedom/code/odylith/tests/unit/runtime/test_release_notes.py)
- [x] [test_sync_cli_compat.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_cli_compat.py)
- [x] [test_auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/tests/unit/runtime/test_auto_update_mermaid_diagrams.py)

## Risks & Mitigations

- [ ] Risk: shell refresh failure could make upgrade look broken.
  - [ ] Mitigation: refresh after runtime activation, but fail soft with a clear retry command that stays on the new narrow dashboard refresh path.
- [ ] Risk: the spotlight could repeat too aggressively.
  - [ ] Mitigation: key dismissal state to repo path plus upgraded version in local storage.
- [ ] Risk: the spotlight could close cleanly but feel lost afterward, or land
      on an empty-looking tab after refresh.
  - [ ] Mitigation: remember the last active shell state across reload and show
        a version-scoped toolbar reopen affordance after dismiss.
- [ ] Risk: release highlights can be noisy or absent.
  - [ ] Mitigation: cap at three bullets and provide a clean fallback summary when release notes are sparse.
- [ ] Risk: reinstall or launcher recovery could widen trust toward host Python.
  - [ ] Mitigation: keep consumer reinstall on verified release assets only and reuse the repo-local bootstrap launcher for recovery guidance.
- [ ] Risk: “dashboard refresh” silently mutates governance truth.
  - [x] Mitigation: keep the command surface explicit, narrow by default, and separate from the full `sync` contract.
- [ ] Risk: operators assume upgrade-time refresh means the shell stays fresh
    indefinitely during mixed active work.
  - [ ] Mitigation: keep steady-state freshness posture explicit and route it
    through the runtime-freshness slice instead of implying an always-hot
    background sync.
- [ ] Risk: Mermaid worker fallback still feels hung on large batches.
  - [x] Mitigation: print per-diagram progress, timeout reasons, and final blocking ids when fallback also fails.
- [ ] Risk: Atlas parse failures still waste time if syntax validation only
      happens after the bulk render starts.
  - [x] Mitigation: run Mermaid syntax preflight before SVG/PNG generation and
        fail with diagram id plus source path and line context.

## Validation/Test Plan
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py tests/unit/runtime/test_shell_onboarding.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/integration/install/test_manager.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_shell_onboarding.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/test_cli.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_release_notes.py tests/unit/runtime/test_shell_onboarding.py tests/unit/runtime/test_render_tooling_dashboard.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
- [x] `pytest -q tests/unit/test_cli.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py`
- [x] `pytest -q tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py::test_cli_install_adopt_latest_renders_a_browser_valid_incremental_upgrade_note tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py::test_cli_upgrade_renders_a_browser_valid_incremental_upgrade_note`
- [x] headless browser screenshot proof of the upgrade spotlight
- [x] `git diff --check`

## Rollout/Communication
- [x] Keep spotlight payload under `.odylith/` only.
- [x] Make the dashboard refresh explicit in CLI output so operators understand why the shell changed immediately.
- [x] Keep the spotlight centered over the real Odylith surface instead of a
      fabricated stage background.
- [x] Give the operator a version-scoped `Show v<version> note` recovery path
      after dismiss.
- [x] Ship docs/help/skills atomically with the CLI contract so installed guidance does not drift.

## Current Outcome
- [x] Bound to `B-030`; upgrade spotlight and shell refresh landed.
- [x] Release spotlight now persists dismiss per version pair, reopens from the
      shell viewport, keeps the current Odylith surface in the background, and
      links to a repo-local authored release note page.
- [x] Release spotlight now drops placeholder hosted-release copy in favor of
      authored release-note source when present, falls back to a real
      version-delta explanation when hosted copy is junk, and lets the
      temporary reopen chip age out while the permanent version-story note
      remains available from the shell.
- [x] The shell now proves the split path in-browser: first install stays on
      the starter launchpad, while only real incremental upgrades show the
      release spotlight and its clean dismiss/reopen flow.
- [x] Real incremental upgrades now suppress the starter guide on first paint
      even when onboarding truth is still incomplete, so release-note UX and
      first-run UX do not stack on top of each other.
- [x] Browser proof now covers the actual `odylith upgrade` CLI path: CLI
      activation, spotlight payload write, shell refresh, and Chromium-visible
      release note are all exercised together.
- [x] Hosted install and rescue guidance now converges on the canonical
      `odylith.ai` installer entrypoint across CLI bootstrap guidance, bundled
      docs, and agent guidance instead of pointing at the raw release-download
      URL.
- [ ] Release-prep validation on 2026-04-03 exposed a remaining browser
      regression where shell auto-refresh can advance the version badge while
      leaving the upgrade spotlight hidden; tracked in
      [CB-051](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-03-upgrade-spotlight-live-refresh-updates-version-badge-but-keeps-release-note-hidden.md).
- [x] Consumer install and upgrade now prune older release-note source files
      and rendered release-note pages so only the current release note remains
      in the repo after refresh.
- [x] Release hardening extension now includes explicit dashboard surface
      selection, default Compass refresh, fast Atlas parse diagnostics, and
      doc/help alignment for that operator path.
- [x] Release prep on 2026-04-07 added the authored `v0.1.9` note and re-proved
      the welcome screen plus upgrade spotlight in headless Chromium so the
      launch moment stays anchored to real release copy.
- [ ] This plan now owns the install and upgrade moment only; the broader
      steady-state "fresh earlier than commit, benchmark-safe by default"
      posture is tracked with `B-025`.
