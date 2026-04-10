# Security Posture
Last updated: 2026-04-09

## Purpose

Odylith treats runtime trust, release provenance, and process lifetime as
first-class product boundaries. It hardens `.odylith/` against runtime drift,
fails closed on insecure consumer-lane overrides, and keeps Odylith-owned
Python helpers on a tight leash.

This posture reflects shipped release `v0.1.10`, published on 2026-04-08.

## Threat Model

Odylith actively hardens against:

- unsigned or redirected release assets
- local tamper inside `.odylith/runtime/versions/<version>/`
- poisoned launcher fallback authority and recursive wrappers
- insecure localhost or Sigstore-bypass release overrides in consumer repos
- stuck or orphaned Odylith-owned Python helpers after failure or timeout

Odylith also carries one narrow compatibility exception:

- legacy pre-trust consumer installs on `0.1.0` or `0.1.1` may still execute
  through a reduced compatibility check long enough to bootstrap onto a newer
  trusted release

Odylith does not claim full protection against:

- an attacker who can rewrite both `.odylith/` and the repo-root trust anchor
- full same-user repo compromise
- OS- or host-level compromise outside Odylith's own trust boundary
- detached `source-local` as a tamper-proof posture

## Lane Contract

### Consumer lane

- Odylith runs only from a pinned verified managed runtime.
- `source-local` is unsupported.
- Release download overrides such as `ODYLITH_RELEASE_BASE_URL`,
  `ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST`, and
  `ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY` are rejected.
- Managed-runtime trust anchors live outside `.odylith/` under the gitignored
  path `.odylith/trust/managed-runtime-trust/`.

### Pinned dogfood

- Uses the same managed-runtime trust contract as the consumer lane.
- Proves the shipped runtime, not live unreleased `src/odylith/*` changes.

### Detached `source-local`

- Explicit maintainer-only development posture.
- Wrapper and source-root validation still fail closed on poisoned launch
  state.
- This posture is not release-eligible and is not treated as an immutable
  verified runtime.

### Legacy pre-trust bootstrap compatibility

- Applies only to consumer-era `0.1.0` and `0.1.1` runtime roots.
- Exists to preserve the safe-upgrade escape hatch for repos installed before
  repo-root managed-runtime trust anchors existed.
- This is compatibility, not full trust. The expected remediation is to
  upgrade onto a modern trusted runtime.

## Current Controls

### Release and supply chain

- Release assets are downloaded only from trusted hosts by default.
- Manifest, wheel, provenance, SBOM, and managed-runtime assets must verify
  against the expected Sigstore signer identity and OIDC issuer.
- Manifest SHA-256s and provenance digests are checked before activation.
- Runtime archives are validated for path safety before extraction.
- GitHub Actions in the release, release-candidate, and test workflows are
  pinned to immutable SHAs, run on a pinned runner image, and use a pinned
  Hatch version.

### Local runtime trust

- Managed-runtime trust anchors live outside `.odylith/` so runtime-only
  tamper cannot rewrite its own proof.
- The launcher hashes the trusted Python executable before using it.
- Before `odylith.cli` is imported, a Python preflight verifies the managed
  runtime's hot files against the recorded trust anchor.
- `odylith doctor` and same-version runtime reuse also verify the recorded
  deep tree manifest, so dependency drift and symlink substitution become
  trust failures instead of silent reuse.
- Feature packs only apply to already trusted managed runtimes.
- Legacy `0.1.0` and `0.1.1` installs are allowed only through the narrower
  compatibility path needed to upgrade off them.

### Process lifetime

- Context Engine daemon startup fails closed when readiness does not arrive.
- Timed-out governance child sessions kill the whole process group.
- Mermaid helper workers shut down cleanly or get killed on timeout.
- Launcher repair avoids recursive wrapper loops that previously left blocked
  Python shells behind.

## Recovery

- `./.odylith/bin/odylith version --repo-root .`
  Confirms the active lane and runtime posture.
- `./.odylith/bin/odylith doctor --repo-root . --repair`
  Repairs launcher, wrapper, and trusted-runtime drift when safe to do so.
- `./.odylith/bin/odylith reinstall --repo-root . --latest`
  Restages the current release when the runtime must be rebuilt from verified
  assets.
- `./.odylith/bin/odylith context-engine status --repo-root .`
  Checks daemon posture without starting a new background helper.

## Residual Risk

- If an attacker can rewrite both the repo-root trust anchor and the launcher,
  Odylith cannot prove local integrity from inside that same compromised repo.
- Detached `source-local` is for explicit live-source work, not for strong
  runtime immutability claims.
- Supply-chain hardening depends on the trusted canonical repo, workflow, and
  signer identity still being trustworthy.

## Operator Guidance

- Treat trust failures as a repair or reinstall signal, not something to
  bypass with consumer-lane environment variables.
- Keep the repo root Git-backed and the trust-anchor path gitignored.
- Return the product repo from detached `source-local` to pinned dogfood
  before making proof or release claims.
