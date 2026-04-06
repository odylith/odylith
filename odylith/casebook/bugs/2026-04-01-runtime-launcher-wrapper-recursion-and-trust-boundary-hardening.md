- Bug ID: CB-026

- Status: Closed

- Created: 2026-04-01

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: Odylith's repo-local launcher and wrapped-runtime repair path
  could recurse through `.odylith/runtime/current`, trust mutable launcher
  fallback text too early, and execute unverified runtime roots before the
  Python-side trust checks had a chance to intervene. In detached
  `source-local` or degraded repair states, `odylith start` and `odylith
  version` could therefore hang, retries could stack multiple blocked
  terminals, and repair could preserve the wrong interpreter authority.

- Impact: All three supported lanes were exposed to the same class of failure,
  just with different symptoms. Detached maintainer-dev could self-loop on
  `source-local`, pinned dogfood and repaired product-repo wrappers could keep
  stale host-Python fallback authority, and bootstrap or degraded consumer
  launchers could select runtime candidates by weak metadata alone. The result
  was slow or stuck startup, broken trust in launcher repair, and a realistic
  risk of leaving extra Python processes alive while operators retried.

- Components Affected: `src/odylith/install/runtime.py`,
  `src/odylith/install/manager.py`, repo launcher and bootstrap launcher shell
  contract, wrapped-runtime fallback normalization, product-repo detached
  `source-local` repair path, consumer and dogfood runtime trust boundary.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, pinned dogfood, degraded repo-local launcher/repair states,
  and any repo with a mutable `.odylith` runtime tree that had drifted into a
  self-referential or unverified runtime candidate.

- Root Cause: The first wrapper fix stopped one self-reference, but the deeper
  authority model was still inconsistent. Wrapper creation could still reason
  from `runtime/current`, the shell launcher still executed `current_python`
  whenever it existed even if the runtime was unverified or malformed, the
  bootstrap launcher still treated `runtime-metadata.json` as sufficient trust
  for candidate discovery, and repair still read fallback interpreter or
  source-root hints from mutable launcher text without revalidating them.

- Solution: Harden the runtime layer itself instead of only the wrapper writer.
  Wrapped-runtime fallback selection now normalizes away self-referential
  `runtime/current` pointers, validates source roots, and prefers verified
  managed runtimes or explicit maintainer wrappers over mutable launcher text.
  Modern managed runtimes now write repo-root trust anchors outside
  `.odylith/`, the launcher verifies hot-path integrity before `odylith.cli`
  import, `odylith doctor` and same-version runtime reuse verify the deeper
  runtime tree, and feature packs only attach to already trusted managed
  runtimes. The shell launcher and bootstrap launcher fail closed on
  unverified managed runtimes, self-referential wrappers, and untrusted
  fallback targets; repair ignores poisoned launcher fallback paths and
  recreates wrappers only from validated authority. Consumer posture also now
  rejects insecure localhost or Sigstore-bypass release overrides, and the
  release-critical GitHub workflows are pinned to immutable first-party action
  SHAs plus a pinned runner image and Hatch version. Legacy `0.1.0` and
  `0.1.1` installs keep only the narrow compatibility path needed to upgrade
  off pre-trust releases.

- Verification: Focused runtime and manager regression coverage now passes for
  wrapper normalization, non-hanging fallback execution, bootstrap candidate
  trust, repair-time fallback sanitization, and consumer-lane release-override
  rejection. Live repo checks also returned to normal launcher behavior:
  `./.odylith/bin/odylith version --repo-root .`,
  `./.odylith/bin/odylith start --repo-root .`, and
  `./.odylith/bin/odylith context-engine status --repo-root .` complete in the
  current checkout again instead of blocking on a recursive launcher path. A
  focused process sweep after validation found no lingering Odylith
  launcher-related or context-engine-related Python processes.

- Prevention: Treat the repo launcher as part of the trust boundary, not just
  as a thin shell hop. Shell entrypoints must only execute verified managed
  runtimes or validated maintainer wrappers, bootstrap discovery must never use
  weak metadata alone as trust, and repair must never inherit fallback
  interpreters or source roots from mutable launcher text without
  revalidation. Bad runtime state should fail closed into repair guidance
  instead of hanging.

- Detected By: User report on 2026-04-01 after `odylith start` appeared to
  create two running terminals and took nearly three minutes to reach a usable
  result.

- Failure Signature: `./.odylith/bin/odylith start --repo-root .` or `version`
  hangs in detached `source-local` posture; launcher text points at
  `.odylith/runtime/current/bin/python`; retrying from Codex leaves multiple
  blocked launcher terminals alive; bootstrap or repair paths can choose a
  runtime by weak metadata instead of verified authority.

- Trigger Path: Product-repo maintainer work that activated `source-local`
  through a wrapper built from `runtime/current`, degraded repair or doctor
  paths that reused launcher-embedded fallback values, and bootstrap launcher
  discovery when multiple repo-local runtime roots were present.

- Ownership: Odylith install/runtime launcher trust boundary.

- Timeline: The user escalated the startup stall on 2026-04-01; the first fix
  normalized the obvious self-reference; the second hardening pass broadened
  the repair and shell trust model the same day so the bug could not reappear
  through dogfood, detached `source-local`, or consumer bootstrap variants.

- Blast Radius: Maintainers dogfooding Odylith in the product repo, consumers
  relying on repo-local repair after launcher drift, and any agent workflow
  that treats `odylith start` or `odylith version` as safe first-turn status.

- SLO/SLA Impact: Local startup reliability and repair trust degrade sharply;
  the operator can lose minutes on false hangs and lose trust in whether the
  active runtime is real.

- Data Risk: Low direct data risk, but high trust-boundary risk because the
  launcher could execute a runtime candidate before verification.

- Security/Compliance: This was a real local trust-boundary gap. Before the
  hardening, the shell launcher could execute an unverified managed runtime or
  a mutable fallback path before the Python-side checks could reject it.
  Maintainer wrappers also derived too much authority from mutable launcher
  text.

- Invariant Violated: Repo-local launchers must never execute unverified or
  self-referential runtime state, and failed startup paths must not leave
  blocked or lingering Python processes behind.

- Workaround: Bypass the broken launcher with a known-good pinned runtime, then
  run `./.odylith/bin/odylith doctor --repo-root . --repair`. This was useful
  for diagnosis but not acceptable as the steady-state contract.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not exec `runtime/current/bin/python` blindly. Do not
  treat `runtime-metadata.json` alone as bootstrap trust. Do not preserve
  launcher-embedded fallback interpreters or source roots unless they validate
  as current Odylith authority. If runtime state is ambiguous, fail closed into
  repair instead of widening execution.

- Preflight Checks: Inspect this bug, the active B-033 release-hardening plan,
  `src/odylith/install/runtime.py`, `src/odylith/install/manager.py`,
  `tests/unit/install/test_runtime.py`, and
  `tests/integration/install/test_manager.py` before changing launcher or
  repair trust again.

- Regression Tests Added: `test_bootstrap_launcher_skips_unverified_managed_runtime_candidates`,
  `test_repo_launcher_falls_back_from_self_referential_current_wrapper_without_hanging`,
  `test_doctor_runtime_repair_ignores_untrusted_launcher_fallback`,
  `test_source_repo_upgrade_normalizes_current_runtime_symlink_fallback`,
  plus the earlier wrapper-recursion regressions in
  `tests/unit/install/test_runtime.py`.

- Monitoring Updates: None beyond the live process sweep and launcher-runtime
  health checks exercised by `doctor_runtime(...)`.

- Residual Risk: Odylith still cannot fully protect against an attacker who
  can rewrite both the repo-root trust anchor and the launcher from inside the
  same compromised repo. Detached `source-local` also remains a development
  posture, not an immutable trusted runtime.

- Related Incidents/Bugs:
  `2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md`,
  `2026-03-28-public-consumer-install-depends-on-machine-python.md`,
  `2026-03-28-public-consumer-rollback-to-legacy-preview-runtime-fails.md`

- Version/Build: `v0.1.7` launcher/runtime hardening wave completed on
  2026-04-01.

- Config/Flags: `odylith start --repo-root .`, `odylith version --repo-root .`,
  `odylith doctor --repo-root . --repair`, detached `source-local`,
  repo-local bootstrap launcher.

- Customer Comms: Captured directly in the authored `v0.1.7` release note and
  popup-facing highlights as stronger runtime trust, supply-chain proof, and
  fail-closed recovery without local Python process leaks.

- Code References: `src/odylith/install/runtime.py`,
  `src/odylith/install/manager.py`, `tests/unit/install/test_runtime.py`,
  `tests/integration/install/test_manager.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
