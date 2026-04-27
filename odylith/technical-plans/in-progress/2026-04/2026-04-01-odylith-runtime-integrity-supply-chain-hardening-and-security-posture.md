Status: In progress

Created: 2026-04-01

Updated: 2026-04-01

Backlog: B-040

Goal: Harden Odylith's runtime trust boundary, maintainer workflow
supply-chain posture, and published security contract across consumer,
pinned-dogfood, and detached `source-local` lanes without losing the narrow
legacy upgrade escape hatch for pre-trust installs.

Assumptions:
- Runtime trust, release provenance, and process lifetime are now product
  features, not hidden implementation details.
- Legacy consumer installs on `0.1.0` and `0.1.1` need a bounded compatibility
  path so they can upgrade onto the stronger trust contract.
- Same-user repo compromise remains a residual risk that Odylith cannot fully
  eliminate from inside the same repo.

Constraints:
- Modern managed runtimes must fail closed on trust drift instead of silently
  widening into host Python or mutable runtime bytes.
- Consumer posture must not honor maintainer-only localhost or Sigstore-bypass
  release overrides.
- Security docs and release-note messaging must stay honest about residual
  same-user local compromise risk.
- Process-lifetime fixes are not done until Odylith-owned Python helpers are
  verified to exit on success and timeout paths.

Reversibility: Workflow pins, runtime-integrity checks, and documentation are
forward-fix changes but remain locally reversible if a bounded compatibility
issue appears. The plan itself is additive governance truth.

Boundary Conditions:
- Scope includes launcher/runtime integrity verification, release-asset
  override gating, workflow pinning, security docs/skills, Registry/Radar and
  Casebook updates, and `v0.1.7` release messaging.
- Scope excludes hosted disclosure policy, threshold signing redesign, and any
  claim of full tamper-proof security under same-user repo compromise.

Related Bugs:
- [2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md)
- [2026-03-28-public-consumer-install-depends-on-machine-python.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-public-consumer-install-depends-on-machine-python.md)
- [2026-03-28-public-consumer-rollback-to-legacy-preview-runtime-fails.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-public-consumer-rollback-to-legacy-preview-runtime-fails.md)
- [2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md)

## Must-Ship
- [ ] Add repo-root managed-runtime trust anchors and hot-path pre-exec
      integrity verification for modern managed runtimes.
- [ ] Verify the deeper managed-runtime tree during doctor, repair, and
      same-version runtime reuse.
- [ ] Preserve the narrow `0.1.0`/`0.1.1` compatibility path needed to upgrade
      pre-trust consumer installs.
- [ ] Reject `ODYLITH_RELEASE_BASE_URL`,
      `ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST`, and
      `ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY` outside the product-repo
      maintainer lane.
- [ ] Pin first-party GitHub Actions, runner image, and Hatch version in the
      release, release-candidate, and test workflows.
- [ ] Publish the security contract in README-linked docs, guidelines, skills,
      Registry, Radar, Casebook, and `v0.1.7` release notes.
- [ ] Prove that validated Odylith command and timeout paths do not leave
      Odylith-owned Python processes behind.

## Should-Ship
- [ ] Add a dedicated `security` Registry component for the runtime and
      supply-chain trust boundary.
- [ ] Keep bundled consumer docs and skills aligned with the product tree.
- [ ] Make the `v0.1.7` popup-facing summary explain the stronger security
      posture, not only UX polish.

## Defer
- [ ] Do not claim full protection against an attacker who can rewrite both
      the repo-root trust anchor and the launcher.
- [ ] Do not broaden the legacy compatibility path beyond `0.1.0` and
      `0.1.1`.
- [ ] Do not turn this wave into a broader hosted security-program rewrite.

## Success Criteria
- [ ] Runtime trust drift blocks startup, repair reuse, or feature-pack
      application instead of being silently reused.
- [ ] Consumer posture rejects maintainer-only release override toggles.
- [ ] Workflow supply-chain mutability is reduced through immutable action pins
      and pinned maintainer tooling.
- [ ] Security docs, Registry, Radar, Casebook, and release-note story all say
      the same thing about the trust model and residual risk.
- [ ] Focused validation plus live process sweeps show no lingering
      Odylith-owned Python helpers.

## Impacted Areas
- [ ] [runtime.py](/Users/freedom/code/odylith/src/odylith/install/runtime.py)
- [ ] [runtime_integrity.py](/Users/freedom/code/odylith/src/odylith/install/runtime_integrity.py)
- [ ] [release_assets.py](/Users/freedom/code/odylith/src/odylith/install/release_assets.py)
- [ ] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [ ] [.github/workflows/release.yml](/Users/freedom/code/odylith/.github/workflows/release.yml)
- [ ] [.github/workflows/release-candidate.yml](/Users/freedom/code/odylith/.github/workflows/release-candidate.yml)
- [ ] [.github/workflows/test.yml](/Users/freedom/code/odylith/.github/workflows/test.yml)
- [ ] [odylith/SECURITY_POSTURE.md](/Users/freedom/code/odylith/odylith/SECURITY_POSTURE.md)
- [ ] [odylith/agents-guidelines/SECURITY_AND_TRUST.md](/Users/freedom/code/odylith/odylith/agents-guidelines/SECURITY_AND_TRUST.md)
- [ ] [odylith/skills/odylith-security-hardening/SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-security-hardening/SKILL.md)
- [ ] [odylith/runtime/source/release-notes/v0.1.7.md](/Users/freedom/code/odylith/odylith/runtime/source/release-notes/v0.1.7.md)
- [ ] [odylith/casebook/bugs/2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md)
- [ ] [odylith/registry/source/component_registry.v1.json](/Users/freedom/code/odylith/odylith/registry/source/component_registry.v1.json)
- [ ] [odylith/registry/source/components/security/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/security/CURRENT_SPEC.md)

## Risks & Mitigations
- [ ] Risk: startup integrity checks add too much latency.
  - [ ] Mitigation: keep the launcher on hot-file verification and reserve deep
        tree checks for doctor, repair, and reuse decisions.
- [ ] Risk: compatibility fixes reopen the modern trust boundary.
  - [ ] Mitigation: confine the compatibility exception to `0.1.0` and
        `0.1.1` and document it explicitly.
- [ ] Risk: docs overclaim local tamper resistance.
  - [ ] Mitigation: state same-user repo compromise as residual risk in
        Security Posture, Registry, and release-note messaging.

## Validation/Test Plan
- [ ] `pytest tests/unit/install/test_runtime.py -q`
- [ ] `pytest tests/unit/install/test_release_assets.py -q`
- [ ] `pytest tests/integration/install/test_manager.py -q`
- [ ] `pytest tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_sync_cli_compat.py -q`
- [ ] `./.odylith/bin/odylith version --repo-root .`
- [ ] `./.odylith/bin/odylith start --repo-root .`
- [ ] `./.odylith/bin/odylith context-engine status --repo-root .`
- [ ] final Odylith-owned `pgrep` sweep after validation

## Rollout/Communication
- [ ] Bind the security wave to `B-040` under the existing `B-033` release
      umbrella instead of flattening it into the parent record.
- [ ] Update the `v0.1.7` authored release note so the popup and release page
      tell the security story directly.
- [ ] Keep product and bundled-consumer docs aligned for the new trust model.

## Current Outcome
- [x] `B-040` is opened as the child workstream for the runtime-integrity and
      security-posture wave.
- [ ] Runtime hardening, workflow pinning, governance updates, and focused
      validation are still in progress.
