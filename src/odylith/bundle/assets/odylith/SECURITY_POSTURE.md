# Security Posture
Last updated: 2026-05-05

## Purpose

Odylith treats runtime trust, release provenance, and process lifetime as
first-class product boundaries. It hardens `.odylith/` against runtime drift,
fails closed on insecure consumer-lane overrides, and keeps Odylith-owned
Python helpers on a tight leash.

This posture is authored for the `v0.1.15` release line prepared by this
branch.

## Threat Model

Odylith actively hardens against:

- unsigned or redirected release assets
- local tamper inside `.odylith/runtime/versions/<version>/`
- poisoned launcher fallback authority and recursive wrappers
- insecure localhost or Sigstore-bypass release overrides in consumer repos
- stuck or orphaned Odylith-owned Python helpers after failure or timeout
- benchmark-only runtime branches that would make release measurements diverge
  from the product policy shipped to users

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

### Greenfield governance safety

- Greenfield Domain Intelligence proposals separate observed source, user
  intent, and Odylith assumptions; missing source cannot become a source-backed
  governance claim.
- `odylith greenfield semantic-intent-request` gives the active host a
  schema-constrained authoring request. The host uses the simplest
  evidence-supported reasoning mechanism, assembles one source-cited Semantic
  Intent graph, and independently challenges it for
  contradictions before submission. A matching citation proves custody, not
  entailment; the host remains responsible for semantic support. Outcome and
  proof laws are fixed; the authoring mechanism remains provisional.
- `odylith greenfield propose` deterministically verifies graph shape, typed
  relation endpoints, source custody, canonical meaning, and the complete
  ProductCreateTransaction before it renders the sole confirmation rail.
  Prompt and EDIT prose never become parser-derived product authority.
- `odylith greenfield create` only verifies the compiler receipt, transaction
  hash, compiler identity, and unchanged repo preconditions; applies the sealed
  write set under rollback guard; validates exact readback; and reports success.
- Legacy proposal `apply` is not a confirmed write path. EDIT produces a new
  authoring request bound to the exact superseded transaction and compiles a
  new transaction; it never repairs or mutates confirmed meaning in place.
- The greenfield proposal Tribunal rejects disconnected child topology, shallow
  component ownership, and invisible release/program structures before durable
  source truth changes.
- Supported host routes own semantic judgment but not validation or writes; the
  Odylith runtime owns deterministic validation, confirmation, topology
  hygiene, and durable memory boundaries without becoming a second semantic
  authority.

### Product Governed Harness safety

- Turn Gate decisions are product policy. The same classifier, evidence gate,
  execution capsule, tool gate, receipt, and stop-check contracts must be used
  by consumer prompts, managed harnesses, hooks, and benchmark wrappers.
- Benchmark wrappers may sandbox, time, log, and score Turn Gate outcomes, but
  they must not decide closure independently or install benchmark-only fast
  paths.
- Early-exit proof requires grounded evidence, matching repo state, validator
  sufficiency, no workspace writes, and a receipt sourced from the product Turn
  Gate.
- Execution capsules constrain owned paths, denied paths, allowed commands,
  dirty-worktree safety, validation obligations, route/delegation boundaries,
  and completion-claim limits before side effects.
- Enforce mode is security-relevant only for host integrations that can block
  prompt, tool, or stop flow. Other integrations must label advisory behavior
  honestly.

### Host and migration safety

- Managed Codex and Claude assets merge additively with user-owned host
  settings; Odylith must not replace a user's host config with an
  Odylith-only template.
- Consumer-visible docs, browser-rendered governance surfaces, and
  install-managed assets are release-observed. `odylith release
  migration-gate --target-version 0.1.15` must pass before release prep can
  treat those surfaces as migration-safe.
- Historical benchmark proof waivers, including the exact-version `v0.1.14`
  waiver, stay tracked release truth and do not create a standing bypass for
  later releases.

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
