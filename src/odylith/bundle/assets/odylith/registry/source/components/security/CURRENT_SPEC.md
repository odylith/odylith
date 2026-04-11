# Security
Last updated: 2026-04-02


Last updated (UTC): 2026-04-01

## Purpose
Security is Odylith's cross-cutting trust-boundary component for managed
runtime integrity, release-asset provenance, workflow supply-chain posture,
and process-lifetime discipline across consumer, pinned-dogfood, and detached
`source-local` lanes.

## Scope And Non-Goals
### Security owns
- The repo-local launcher and bootstrap-launcher trust boundary.
- Managed-runtime integrity evidence, trust-anchor placement, and compatibility
  posture for pre-trust consumer upgrades.
- Consumer-lane rejection of insecure maintainer-only release overrides.
- Workflow supply-chain pinning expectations for release-critical GitHub
  Actions and maintainer tooling.
- Security posture documentation, guidance, and skills that describe the above
  contract honestly.
- Verification that Odylith-owned Python helpers exit when validated command or
  timeout paths complete.

### Security does not own
- Full same-user local compromise resistance from inside one writable repo.
- Hosted disclosure policy or enterprise security-process operations.
- Consumer application security outside Odylith's own launcher, runtime, and
  release boundary.

## Developer Mental Model
- Odylith's security posture is local-first and fail-closed, not invisible.
- The trust boundary is shared across launcher shell, managed runtime bytes,
  repo-root trust anchors, signed release assets, and bounded maintainer
  rehearsal controls.
- Managed-runtime trust for modern installs must survive `.odylith/` tamper by
  keeping the trust anchor outside `.odylith/`.
- Legacy `0.1.0` and `0.1.1` compatibility exists only to bootstrap old
  installs onto the modern trust contract.
- Same-user repo compromise remains a residual risk and must be documented as
  such instead of hand-waved away.

## Owning Interfaces And Artifacts
- `src/odylith/install/runtime.py`
- `src/odylith/install/runtime_integrity.py`
- `src/odylith/install/release_assets.py`
- `.github/workflows/release.yml`
- `.github/workflows/release-candidate.yml`
- `.github/workflows/test.yml`
- `odylith/SECURITY_POSTURE.md`
- `odylith/agents-guidelines/SECURITY_AND_TRUST.md`
- `odylith/skills/security-hardening/SKILL.md`

## Lane Contract
### Consumer lane
- Only verified managed runtimes are trusted.
- Insecure localhost or Sigstore-bypass release overrides are rejected.
- Managed-runtime trust anchors live under the gitignored local path
  `.odylith/trust/managed-runtime-trust/`.

### Pinned dogfood
- Uses the same runtime-trust and release-verification contract as consumer
  lane.
- Proves the shipped runtime rather than live unreleased source.

### Detached `source-local`
- Maintainer-only live-source posture.
- Wrapper and source-root validation still fail closed.
- This posture is not release-eligible and is not described as immutable.

### Legacy bootstrap compatibility
- Applies only to `0.1.0` and `0.1.1`.
- Exists only to preserve a safe upgrade path onto the stronger trust model.

## Control Flow
### 1. Trust staging
1. Verified release assets are downloaded from trusted hosts, checked against
   signed manifest and provenance evidence, and staged atomically.
2. Modern managed runtimes write repo-root trust anchors outside `.odylith/`
   once release verification succeeds.

### 2. Trust execution
1. The launcher hashes the managed runtime Python binary before execution.
2. A Python preflight verifies hot-path managed-runtime files before
   `odylith.cli` import.
3. `odylith doctor`, repair, and same-version reuse verify the deeper runtime
   tree before reusing installed bytes.

### 3. Trust recovery
1. Trust drift fails closed into repair guidance.
2. Legacy compatibility stays narrow enough to upgrade stranded old installs
   without weakening the modern runtime contract.
3. Process-lifetime validation verifies Odylith-owned Python helpers do not
   leak after the validated path finishes.

## Validation
- `tests/unit/install/test_runtime.py`
- `tests/unit/install/test_release_assets.py`
- `tests/integration/install/test_manager.py`
- `tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py`
- `tests/unit/runtime/test_auto_update_mermaid_diagrams.py`
- `tests/unit/runtime/test_sync_cli_compat.py`

## Residual Risk
- An attacker who can rewrite both the launcher and the repo-root trust anchor
  can still subvert local trust from inside the same compromised repo.
- Detached `source-local` is intentionally less immutable than pinned managed
  runtime posture.

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-04-01: Registered Security as a first-class Odylith component for runtime integrity, release provenance, workflow supply-chain hardening, and process-lifetime validation so the product trust boundary stops living only in scattered code and release notes. (Plan: [B-040](odylith/radar/radar.html?view=plan&workstream=B-040))
