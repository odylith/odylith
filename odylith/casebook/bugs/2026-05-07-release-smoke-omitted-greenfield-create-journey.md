- Bug ID: CB-181

- Status: FixedPendingRelease

- Created: 2026-05-07

- Severity: P2

- Reproducibility: High

- Type: Test

- Title: Release smoke omitted exact greenfield propose/apply journey

- Description: Release smoke omitted exact greenfield propose/apply journey

- Impact: The local release smoke could pass without proving the exact first-run path that failed in the transcript: install fresh repo, show capability, propose canonical greenfield JSON, apply the confirmed proposal, refresh surfaces, and assert no host-side schema repair loop.

- Components Affected: release

- Environment(s): Odylith v0.1.15 local release smoke harness.

- Detected By: Operator self-analysis on 2026-05-07 after the robot swarm logistics greenfield run required manual JSON repair loops before passing.

- Failure Signature: Release smoke covered install/dashboard basics and later the one-command create shortcut, but did not run odylith show followed by `greenfield propose --format json` and confirmed `greenfield apply --proposal-file`, so the original prose-to-JSON repair loop was not pinned.

- Follow-up Failure Signature: The smoke also did not inspect installed AGENTS/README/skill guidance, so a packaged release could install fixed CLI code while still teaching hosts to hand-author proposal JSON and recreate the schema-repair loop.

- Trigger Path: Run scripts/release/local_release_smoke.py against a fresh local release bundle.

- Ownership: Release smoke harness and greenfield release-readiness proof.

- Timeline: Captured 2026-05-07 through `odylith bug capture`.

- Blast Radius: Release validation, greenfield onboarding, and confidence that packaged installs own the full proposal/apply path.

- SLO/SLA Impact: Could allow release candidates to ship with multi-minute first-run schema repair loops.

- Data Risk: No application data risk; release validation can miss governance-source write failures.

- Security/Compliance: Policy posture: release proof must cover confirmation-gated governance writes and fail closed on schema repair loops before public release; no credential or privacy exposure.

- Invariant Violated: A release smoke for greenfield-ready releases must exercise the confirmed propose/apply path end to end and reject visible host-side schema repair loops; the one-command create shortcut is additional proof, not a substitute for the transcript journey.

- Root Cause: The smoke harness stopped after install/dashboard validation and did not encode the operator's fresh-repo greenfield journey as a regression lane.

- Solution: Add an exact greenfield propose/apply smoke: run show, emit canonical proposal JSON with `odylith greenfield propose --format json`, apply that file with `odylith greenfield apply --confirm --release 0.0.1`, require Tribunal/pass/start-coding closeout, run dashboard refresh, reject schema-loop strings, and assert Compass/Radar/Registry/Atlas surfaces exist. Keep the create shortcut covered in a separate fresh installed repo, and treat wrapped release-metadata 404s as missing previous releases so the focused smoke can skip unrelated upgrade rehearsals deterministically.

- Follow-up Solution: Extend local release smoke to inspect installed `AGENTS.md`, `odylith/AGENTS.md`, `odylith/README.md`, `odylith-greenfield-governance`, and `odylith-show-me`; require `greenfield create`, require an explicit no hand-authored JSON guard, and reject stale host-drafts-proposal instructions.

- Verification: PYTHONPATH=src python -m pytest -q tests/unit/install/test_local_release_smoke.py; PYTHONPATH=src python scripts/release/local_release_smoke.py --version 0.1.15 --dist-dir /tmp/odylith-local-smoke-current-0.1.15 --previous-version 0.0.0

- Follow-up Verification: `PYTHONPATH=src python -m pytest -q tests/unit/install/test_local_release_smoke.py::test_release_smoke_requires_installed_greenfield_guidance_uses_create tests/unit/install/test_codex_project_assets.py::test_greenfield_guidance_uses_canonical_create_path_not_host_json_authoring`

- Prevention: Keep the release smoke tied to the exact install -> show -> propose JSON -> confirmed apply -> surface proof journey for future greenfield releases, while separately testing the one-command create shortcut in its own fresh installed repo.

- Regression Tests Added: tests/unit/install/test_local_release_smoke.py::test_greenfield_propose_apply_smoke_runs_exact_release_journey, tests/unit/install/test_local_release_smoke.py::test_greenfield_create_smoke_runs_show_create_and_checks_surfaces, tests/unit/install/test_local_release_smoke.py::test_install_and_create_smoke_installs_then_runs_one_command_path, tests/unit/install/test_local_release_smoke.py::test_release_smoke_requires_installed_greenfield_guidance_uses_create, tests/unit/install/test_codex_project_assets.py::test_greenfield_guidance_uses_canonical_create_path_not_host_json_authoring, and tests/unit/install/test_local_release_smoke.py::test_previous_release_is_published_treats_wrapped_404_as_missing

- Related Incidents/Bugs: CB-173, CB-176

- Code References: - scripts/release/local_release_smoke.py
- tests/unit/install/test_local_release_smoke.py
