- Bug ID: CB-152

- Type: Product




- Status: FixedPendingRelease

- Created: 2026-05-02

- Severity: P1

- Reproducibility: High


- Description: Current-source install generated launchers and Claude settings with newer host-hook helper routes, while the shipped v0.1.12 runtime only knows the older launcher health parser, pre-bundle Claude prompt hook commands, and legacy intervention-status readiness checks.

- Impact: Fresh consumer installs or repairs produced by newer installer code can appear unhealthy to the pinned shipped runtime even when launcher files and managed runtime are present; Claude `prompt-bundle` hooks can also fail if the launcher routes directly to a module that the active shipped runtime has not received yet, and readiness status can incorrectly report degraded even when the prompt-bundle fallback is working.

- Components Affected: odylith

- Environment(s): Fresh consumer repo installed from current v0.1.13 source while active managed runtime remains v0.1.12 pinned_release.

- Detected By: Fresh-host proof for B-141 after release target and migration governance refresh.

- Failure Signature: doctor reported repo launcher fallback missing and bootstrap launcher fallback missing; start entered repair lane for the same reason; a clean fresh host also failed `claude prompt-bundle --help` with `No module named odylith.runtime.surfaces.claude_host_prompt_bundle` against the pinned v0.1.12 runtime; after prompt-bundle fallback worked, shipped `claude intervention-status` still reported degraded because it looked only for legacy prompt-context and prompt-teaser hooks.

- Trigger Path: Install from current source into a new repo, then run ./.odylith/bin/odylith doctor --repo-root ., ./.odylith/bin/odylith start --repo-root ., ./.odylith/bin/odylith claude prompt-bundle, or ./.odylith/bin/odylith claude intervention-status through the pinned v0.1.12 managed runtime.

- Ownership: Managed runtime launcher generation and cross-version repair health parsing.

- Timeline: Captured 2026-05-02 during v0.1.13 fresh-host proof; fix added a legacy health-check anchor while preserving direct host-hook dispatch.

- Blast Radius: Consumer repos installed or repaired with newer launcher templates while the active managed runtime still uses the older fallback parser.

- SLO/SLA Impact: Fresh-host and migration proof can fail even though runtime artifacts are present, blocking operator trust in repair and start guidance.

- Data Risk: Low direct data risk; install health and migration confidence risk.

- Security/Compliance: Trust boundary communication risk: a healthy managed runtime can be reported as missing fallback evidence, making supply-chain health look worse than it is.

- Invariant Violated: Generated launchers must stay parseable by the latest shipped health checker until the shipped runtime advances past that parser.

- Root Cause: The launcher generator switched the fallback execution line to odylith_exec_odylith for direct host-hook module dispatch, but older shipped health checks parse launcher text for the exact legacy CLI fallback form. The same launcher optimization also assumed every generated host-hook module route exists in the active managed runtime, which is false during mixed-version installs where current source generates launchers before v0.1.13 ships.

- Solution: Emit an explicit legacy health-check fallback anchor in generated repo and bootstrap launchers while keeping the active odylith_exec_odylith dispatch path for host-hook fast paths. For Claude `prompt-bundle`, detect whether the runtime or source `PYTHONPATH` actually contains the new module; when it does not, merge the shipped `prompt-context` and `prompt-teaser` commands in-process so hidden context and visible teaser behavior survive on v0.1.12. Generated Claude settings now also include no-op compatibility marker hooks for the legacy prompt-context and prompt-teaser names so shipped v0.1.12 readiness status recognizes the prompt-submit lane without reintroducing duplicate Python hook work.

- Rollback/Forward Fix: Forward-fix in v0.1.13; do not weaken runtime trust checks or remove direct host-hook dispatch.

- Verification: PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_runtime.py tests/unit/install/test_runtime_host_hook_launcher.py tests/unit/install/test_claude_effective_settings.py tests/unit/runtime/test_intervention_delivery_status.py; PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/install/test_runtime.py tests/integration/install/test_manager.py -k "launcher or fallback or start_preflight"; mixed-version fresh-host proof in /private/tmp/odylith-fresh-host-final-aezgVP reports version and doctor healthy through the generated launcher, keeps `claude prompt-bundle` plus `claude intervention-status` compatible with the shipped v0.1.12 runtime, proves Codex and Claude visible-intervention output, and reaches `odylith start` Context/Execution Engine narrowing with only expected empty-repo fallback.

- Prevention: Keep regression tests that mimic the v0.1.12 fallback parser against generated launchers and assert mixed-version Claude prompt-bundle fallback, direct-dispatch, and source-local dispatch behavior.

- Regression Tests Added: tests/unit/install/test_runtime.py::test_generated_launchers_stay_parseable_by_0_1_12_health_checks; tests/unit/install/test_runtime_host_hook_launcher.py

- Monitoring Updates: Fresh-host proof should include install, version, doctor, and start failure classification so repair-lane launcher failures do not hide as normal context narrowing.

- Version/Build: Observed during v0.1.13 source work against shipped v0.1.12 pinned runtime; fixed for v0.1.13.

- Config/Flags: Default managed runtime launcher generation; no opt-in flags.

- Customer Comms: Affected fresh or repair installs can be healthy after repair even if the older runtime reports fallback missing; v0.1.13 keeps newer launchers readable by that health checker.

- Related Incidents/Bugs: B-141; CB-147; CB-149

- Fixed In: v0.1.13

- Code References: - src/odylith/install/runtime.py
- src/odylith/runtime/common/claude_cli_capabilities.py
- src/odylith/runtime/surfaces/host_intervention_status.py
- tests/unit/install/test_runtime.py
- tests/unit/install/test_runtime_host_hook_launcher.py
- tests/unit/install/test_claude_effective_settings.py
