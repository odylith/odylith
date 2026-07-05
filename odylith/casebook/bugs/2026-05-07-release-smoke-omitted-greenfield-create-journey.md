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

- 2026-05-14 Failure Signature: v0.1.15 shipped with smoke coverage that ran `show`, two `greenfield propose` commands, and dashboard refresh, but did not run the confirmed write path. A downstream greenfield run therefore passed release proof while the real host still spent 32m hand-authoring and repairing hidden proposal JSON after confirmation.

- 2026-07-05 Escaped Release-Smoke Failure: Post-commit local release smoke against dist `odylith-local-release-0.1.15-9842e85d` failed the fresh-install guidance guard with `AGENTS.md: proposal JSON`. The engine and strict greenfield proof had passed, but the installable package still shipped a managed root guidance block whose no-JSON wording was too vague for the current confirmed-create contract.

- 2026-07-05 Second Release-Smoke Failure: A rebuilt proof dist `odylith-local-release-0.1.15-guidance-smoke-20260705T0448` passed the previous proposal-JSON wording but failed the next fresh-install confirmation-format guard with `AGENTS.md: Product story`. The managed root guidance mentioned sectioned Markdown but did not list the minimum Product Intent Confirmation sections or the no-wall-of-prose guard that local release smoke requires.

- Trigger Path: Run scripts/release/local_release_smoke.py against a fresh local release bundle.

- Ownership: Release smoke harness and greenfield release-readiness proof.

- Timeline: Captured 2026-05-07 through `odylith bug capture`.

- Blast Radius: Release validation, greenfield onboarding, and confidence that packaged installs own the full proposal/apply path.

- SLO/SLA Impact: Could allow release candidates to ship with multi-minute first-run schema repair loops.

- Data Risk: No application data risk; release validation can miss governance-source write failures.

- Security/Compliance: Policy posture: release proof must cover confirmation-gated governance writes and fail closed on schema repair loops before public release; no credential or privacy exposure.

- Invariant Violated: A release smoke for greenfield-ready releases must exercise the confirmed propose/apply path end to end and reject visible host-side schema repair loops; the one-command create shortcut is additional proof, not a substitute for the transcript journey.

- Root Cause: The smoke harness stopped after install/dashboard validation and did not encode the operator's fresh-repo greenfield journey as a regression lane.

- 2026-07-05 Root Cause: The release smoke correctly required installed guidance to contain the explicit `proposal JSON` and `parser/schema retries` guards, while broader asset tests also require the `Do not inspect Odylith source`, `hand-author`, final-summary-only, and second-confirmation sentinels. `src/odylith/install/agents.py` and the generated root `AGENTS.md` scope block still said `source/repair JSON`, `narrate retries`, and `seek JSON review`, so a fresh install could pass most guidance wording while still drifting from the current confirmed-create contract. Bootstrap and bundled greenfield guidance already had the stricter wording, so the defect was a managed-AGENTS custody mismatch rather than a semantic-engine failure.

- Solution: Add an exact greenfield propose/apply smoke: run show, emit canonical proposal JSON with `odylith greenfield propose --format json`, apply that file with `odylith greenfield apply --confirm --release 0.0.1`, require Tribunal/pass/start-coding closeout, run dashboard refresh, reject schema-loop strings, and assert Compass/Radar/Registry/Atlas surfaces exist. Keep the create shortcut covered in a separate fresh installed repo, and treat wrapped release-metadata 404s as missing previous releases so the focused smoke can skip unrelated upgrade rehearsals deterministically.

- Follow-up Solution: Extend local release smoke to inspect installed `AGENTS.md`, `odylith/AGENTS.md`, `odylith/README.md`, `odylith-greenfield-governance`, and `odylith-show-me`; require `greenfield create`, require an explicit no hand-authored JSON guard, and reject stale host-drafts-proposal instructions.

- 2026-05-14 Solution: Make the release smoke prove the current confirmed path instead of the obsolete host-authored file path: show, no-write propose JSON, `propose --confirm-intent --format json` returning an apply-ready proposal with backlog/components/diagrams, `greenfield create --confirm --release 0.0.1 --json`, dashboard/surface proof, accepted-project, delivery-intelligence, traceability artifacts, and explicit rejection of schema-loop strings such as `greenfield proposal validation failed`, `host_instruction`, `reasoning_contract`, and `active-proposal.v1.json`.

- 2026-07-05 Solution: Align the managed AGENTS generator and root product guidance with the current confirmed-create wording: do not inspect Odylith source, do not hand-author or repair proposal JSON, do not narrate parser/schema retries, do not stop after repairable issues, do not ask the operator to inspect proposal JSON or for a second confirmation, and surface only the final summary or blockers. Add a focused regression assertion on the managed product-repo block. Do not weaken the smoke guard or broaden the stale-guidance allowlist.

- 2026-07-05 Confirmation-Format Solution: Extend the same managed AGENTS source line to name the minimum Product Intent Confirmation sections: Product story, State object, First complete path, and Proof boundary, and to reject a wall of prose. Compress unrelated Assist closeout guidance so the managed block stays under its byte ceiling while preserving the required visible-behavior sentinels.

- Verification: PYTHONPATH=src python -m pytest -q tests/unit/install/test_local_release_smoke.py; PYTHONPATH=src python scripts/release/local_release_smoke.py --version 0.1.15 --dist-dir /tmp/odylith-local-smoke-current-0.1.15 --previous-version 0.0.0

- Follow-up Verification: `PYTHONPATH=src python -m pytest -q tests/unit/install/test_local_release_smoke.py::test_release_smoke_requires_installed_greenfield_guidance_uses_create tests/unit/install/test_codex_project_assets.py::test_greenfield_guidance_uses_canonical_create_path_not_host_json_authoring`

- 2026-05-14 Verification: `PYTHONPATH=src pytest tests/unit/install/test_local_release_smoke.py::test_greenfield_propose_apply_smoke_runs_exact_release_journey tests/unit/install/test_local_release_smoke.py::test_release_smoke_requires_installed_greenfield_guidance_uses_confirmed_create tests/unit/install/test_codex_project_assets.py::test_greenfield_guidance_uses_product_intent_then_host_authored_apply_path tests/unit/install/test_codex_project_assets.py::test_greenfield_guidance_keeps_post_confirmation_contract_internal -q` passed.

- 2026-07-05 Pre-Rebuild Verification: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_agents.py tests/unit/install/test_local_release_smoke.py::test_release_smoke_requires_installed_greenfield_guidance_uses_confirmed_create` passed with 10 tests. Final release posture still requires a rebuilt dist from the fixed tree and a fresh local release smoke against that dist.

- 2026-07-05 Confirmation-Format Verification: `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_agents.py tests/unit/install/test_local_release_smoke.py::test_release_smoke_requires_installed_greenfield_guidance_uses_confirmed_create tests/unit/install/test_codex_project_assets.py::test_greenfield_guidance_keeps_post_confirmation_contract_internal tests/unit/install/test_codex_project_assets.py::test_greenfield_guidance_uses_product_intent_then_cli_owned_create_path` passed with 12 tests. Managed block sizes are now `consumer_repo=11098` and `product_repo=11321`, below the 11600-byte guard.

- Prevention: Keep the release smoke tied to the exact install -> show -> propose JSON -> confirmed apply -> surface proof journey for future greenfield releases, while separately testing the one-command create shortcut in its own fresh installed repo.

- Prevention Update: For the current contract, the exact journey is install -> show -> no-write Product Intent JSON -> confirmed apply-ready proposal JSON -> `greenfield create --confirm` -> surface and artifact proof. The optional file apply path is a review/export fallback, not the primary release proof.

- Regression Tests Added: tests/unit/install/test_local_release_smoke.py::test_greenfield_propose_apply_smoke_runs_exact_release_journey, tests/unit/install/test_local_release_smoke.py::test_greenfield_create_smoke_runs_show_create_and_checks_surfaces, tests/unit/install/test_local_release_smoke.py::test_install_and_create_smoke_installs_then_runs_one_command_path, tests/unit/install/test_local_release_smoke.py::test_release_smoke_requires_installed_greenfield_guidance_uses_create, tests/unit/install/test_codex_project_assets.py::test_greenfield_guidance_uses_canonical_create_path_not_host_json_authoring, and tests/unit/install/test_local_release_smoke.py::test_previous_release_is_published_treats_wrapped_404_as_missing

- Related Incidents/Bugs: CB-173, CB-176

- Code References: - scripts/release/local_release_smoke.py
- tests/unit/install/test_local_release_smoke.py
