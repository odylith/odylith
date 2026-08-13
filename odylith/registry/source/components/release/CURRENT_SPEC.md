# Release
Last updated: 2026-08-13


## Purpose
Release is Odylith's release subsystem. It owns the canonical maintainer
publication lane and the additive repo-local release-planning contract that
lets backlog work target explicit ship lanes such as `current`, `next`, or a
named release record. Publication proof, release planning, release-note
alignment, and launch-readiness still stay separate concerns inside one
governed subsystem.

## Scope And Non-Goals
### Release owns
- Sticky local release-session state under `.odylith/locks/`.
- Repo-local release-planning truth under `odylith/radar/source/releases/`.
- Stable semver discovery anchored to published canonical releases and
  reusable unpublished tag reservations for the canonical lane.
- Canonical release preflight and dispatch orchestration.
- Process-isolated full-suite execution for the canonical maintainer validation
  lane, with deterministic collection order and an aggregate verdict across
  every shard.
- Release-planning selector resolution, alias ownership, append-only
  workstream assignment history, and the `odylith release ...` command group.
- The generic maintainer GTM-and-release checklist plus the release-readiness
  contract for benchmark-backed launch assets.
- GitHub Actions publication of wheel, signed manifest, provenance, SBOM, and
  supported managed base runtime bundles plus managed context-engine feature
  packs.
- The maintained `THIRD_PARTY_ATTRIBUTION.md` ledger plus the fail-closed
  runtime license audit used by the maintainer lane.
  Canonical releases also publish the checked-in attribution ledger as a
  signed release asset.
- The hosted installer contract for selecting a supported platform runtime
  bundle before runtime activation.
- Maintainer runbook and release-lane operator targets.
- Canonical release-note and launch-asset alignment across the built-in popup,
  permanent release-note page, GitHub release body, and README benchmark
  snapshot.

### Release does not own
- Consumer install and upgrade semantics themselves. The install/runtime layer
  owns those contracts.
- Generic workstream topology or umbrella execution-wave programs. Release
  planning is additive and does not replace backlog lineage or execution waves.
- Consumer project toolchains and application runtime selection.
- The public support or disclosure policy.
- Ongoing channel execution, community management, or non-product campaign
  operations outside the release-owned launch assets.
- Ordinary developer validation outside the canonical maintainer lane.

## Developer Mental Model
- Release is a product subsystem, not just a make target bundle.
- Release planning is additive:
  - backlog topology and execution waves remain the planning/execution shape
  - repo-local release planning records one active target ship lane per
    workstream
  - the canonical maintainer publication lane still proves and ships one
    semver release at a time
- The runbook drives command order; the GTM-and-release checklist drives claim,
  asset, and announcement readiness.
- The maintainer lane resolves one version per release attempt and keeps it
  sticky across retries.
- Unpublished release tags are reusable reservations until a real GitHub
  release exists for that tag.
- The release session is local operational state, not tracked repo truth.
- Benchmark-proof waivers are not local shell folklore. When a release needs
  a maintainer-only exception, it must be recorded in
  `odylith/runtime/source/release-maintainer-overrides.v1.json` with an exact
  version, reason, and owner so PR gating, lane status, and the final release
  story can agree on why benchmark proof was advisory instead of blocking.
- The current `v0.1.10` release uses that exact exception path because the
  pinned-dogfood proof benchmark wedged mid-corpus on report
  `0047192366d8bf1c`. This release must not be narrated as benchmark
  re-proved; the override is exact-version only and the runner fix moves to the
  next release.
- The current `v0.1.12` release uses the same tracked-exception contract for a
  narrower recovery-release decision: candidate proof passed the full test/build
  lane and built the wheel, but benchmark compare correctly failed closed under
  `CB-116` because there is no current-tree authoritative proof report. The
  release story must say benchmark proof is advisory for `v0.1.12`, not current
  proof, and the default benchmark gate remains active for releases without an
  exact-version override.
- The current `v0.1.14` release uses that exact tracked-exception contract
  because the maintainer explicitly waived full benchmark runs for GA. The
  release story must say benchmark proof is advisory for `v0.1.14`; product
  Turn Gate formal-model truth, migrations, browser surfaces, install/runtime
  tests, topology/guidance/discipline validation, and release-candidate proof
  carry the GA lane without claiming fresh benchmark proof.
- Preflight is the session initializer. Dispatch reuses the active session
  rather than recomputing a version.
- The canonical release lane is authoritative only when it runs from the
  canonical repo, on the canonical `origin/main` commit, as the canonical
  maintainer identity.
- Local maintainer wrappers may materialize an isolated clean checkout of that
  canonical commit when the active workspace is dirty or off-main, but they
  must not weaken the commit-binding or workflow authority rules.
- The hosted installer activates an Odylith-managed runtime on supported
  platforms instead of depending on a consumer-machine Python interpreter.
- The hosted installer must remain one-command and non-interactive: it detects
  the platform, selects the correct managed assets, verifies release evidence,
  and finishes activation without asking the developer to choose install-time
  options.
  The canonical public bootstrap command is
  `curl -fsSL https://odylith.ai/install.sh | bash`.
- Release prep for the next version must land an authored note under
  `odylith/runtime/source/release-notes/vX.Y.Z.md` before the lane is treated
  as launch-ready. That note is the source of truth for the consumer upgrade
  spotlight copy, so release-facing popup claims must be proved from the same
  authored markdown rather than one-off shell text.
- Release `name` is explicit planning truth. Matching authored release notes
  may exist for the same `version`, but they must not rename or override the
  release-planning record unless a maintainer explicitly changes `name`.
- In practice, release names only change through an explicit
  `odylith release create ... --name` or `odylith release update ... --name`
  operation.
- Governed read surfaces may fall back from blank `name` to `version`, `tag`,
  or `release_id`, but they must never treat release-note titles as implicit
  release names.
- `current` and `next` are explicit source aliases, not inferred from semver,
  dates, or release-history ordering.
- The active target release owned by the `current` alias stays surfaced in
  governed read models until maintainers explicitly update it to `shipped` or
  `closed`; zero targeted workstreams is an empty state, not implicit GA.
- Governed read models may also surface finished work completed in that active
  release as historical completed members while keeping active-target
  membership at zero.
- Release-target member badges must follow shared workstream-progress truth
  rather than raw plan checkbox math:
  - active implementation members with checked execution work show tracked
    execution percent
  - active implementation members with zero checked execution tasks show
    checklist-only or unknown state, never fake `0% progress`
  - planning or queued members may still truthfully show `0% progress`
- `odylith release add` may attach an already `finished` workstream to an
  active release as historical completed membership. The command must record
  that membership without restoring an active target for the finished
  workstream.
- `shipped` and `closed` release records are terminal for active planning.
  Alias ownership and carried work must move to non-terminal follow-on records
  before lifecycle closure.
- Release notes and maintainer overrides are necessary but not sufficient
  version truth. Before canonical preflight for `vX.Y.Z`, the tracked product
  version must already be advanced in `pyproject.toml` and synchronized into
  `src/odylith/__init__.py` plus
  `odylith/runtime/source/product-version.v1.json`; the `VERSION=` argument to
  preflight does not substitute for that tracked source bump.
- Generated hosted installer commands must remain compatible with the last
  shipped runtime shape used in release smoke. When the template needs
  different first-install versus existing-install behavior, branch on repo
  state using stable commands such as `install --version` and
  `upgrade --to ... --write-pin` instead of assuming a newly introduced hidden
  flag exists in older shipped CLIs.
- Generated hosted installer shell helpers must stay strict-mode safe. Under
  `set -euo pipefail`, repo-root detection and other optional shell locals must
  be initialized before guard checks, and local release smoke must continue to
  prove the nested first-install shape before ancestor repo markers are
  discovered.
- When the hosted installer upgrades an already-installed consumer repo, it
  must leave one truthful closeout posture: the verified runtime is active, the
  tracked repo pin matches that runtime, and any stale-retention cleanup that
  still cannot finish is reported as exact remediation instead of a false
  activation failure.
- Supported public install and normal pinned upgrade remain full-stack by
  default, but release transport is split into a smaller base runtime plus a
  separately versioned managed context-engine pack so uploads, downloads, and
  incremental updates stay lighter.
- Hatch is the canonical build frontend for publishable Odylith wheels in
  maintainer preflight, the repo test workflow, and the GitHub release
  workflow.
- Managed runtime bundle assembly is rooted in pinned upstream Python archive
  digests; release publication must fail closed if those upstream inputs do not
  match the pinned checksums.
- The context-engine pack is a release-owned managed asset with its own signed
  manifest entry, provenance digest, and platform matrix.
- Odylith runtime ownership and consumer project runtime ownership are
  intentionally separate concerns.
- There is no shell-level interpreter switching: `./.odylith/bin/odylith`
  always routes into Odylith's managed runtime, while consumer repo project
  commands stay on the consumer toolchain.
- Interpreter choice does not limit file-edit authority. An Odylith-managed
  runtime may still edit in-scope repo files; the separate question is which
  toolchain validates the target repo's own code.
- Consumer repos stay on one supported posture: installed pinned runtime only.
- The Odylith product repo's maintainer mode has two postures:
  - pinned dogfood for shipped-runtime proof
  - detached `source-local` for live unreleased source execution

## Supported Platform Contract
- Supported install/upgrade platforms for this slice are:
  - macOS (Apple Silicon)
  - Linux (`x86_64`)
  - Linux (`ARM64`)
- Intel macOS and Windows are intentionally unsupported in the current GA
  contract.
- Canonical releases must publish the full supported base-runtime matrix and
  the matching required full-stack context-engine-pack matrix for this slice,
  not a partial subset.
- The hosted installer must fail clearly on unsupported platforms before it
  mutates repo truth.
- Installer and CLI runtime staging must only reuse an already-staged local
  version when that runtime's local verification marker still matches the
  verified release evidence for the requested version.
- Modern managed runtimes must also carry repo-root trust anchors under
  `odylith/runtime/source/managed-runtime-trust/`; consumer and dogfood launch
  paths must fail closed when the hot-path integrity check does not match that
  trust anchor.
- Fresh consumer install must not make a runtime live until the full-stack
  managed runtime and managed context-engine pack pass activation smoke.
- Hosted-installer retention cleanup for stale non-active runtime and release
  cache trees is best-effort only after healthy activation. Read-only leftovers
  must surface exact remediation and must not overturn the active runtime.
- Verified release downloads must stream into repo-local cache files
  atomically and retry bounded transient network failures instead of leaving
  half-written assets in place.
- When an already named local runtime version must be restaged, Odylith must
  build the replacement beside the current tree and only then swap it into the
  canonical version path.
- Same-version upgrade must not restage the already live runtime in place; the
  repair path for same-version drift is `odylith doctor --repo-root . --repair`.
- Installer and CLI upgrade may reuse a previously installed context-engine pack
  only when its recorded asset name and SHA-256 still match the target verified
  release manifest.
- Odylith owns the managed runtime it installs under
  `.odylith/runtime/versions/<version>`.
- `./.odylith/bin/odylith` must always run inside that managed runtime and
  must not source or mutate the consumer repo's own Python environment.
- Consumer launchers and runtime repair paths must fail closed if the active
  runtime pointer or fallback target leaves `.odylith/runtime/versions/`.
- Consumer repos must not activate the detached `source-local` lane. That lane
  is reserved for the Odylith product repo self-host dev posture.
- Product-repo maintainers must return from detached `source-local` to pinned
  dogfood before release-proof, dogfood, or consumer-rehearsal claims.

## Runtime And Operator Contract
### Repo-local release-planning truth
- `odylith/radar/source/releases/releases.v1.json`
  Release registry with immutable `release_id`, lifecycle state, optional
  `version`, `tag`, `name`, notes, and explicit alias ownership.
- `odylith/radar/source/releases/release-assignment-events.v1.jsonl`
  Append-only add, remove, and move history for workstream targeting.

### Local mutable state
- `.odylith/locks/release-session.json`
  Sticky local session for `version`, `tag`, `head_sha`, and retry metadata.

### Maintainer command surface
- `odylith release create|update|list|show|add|remove|move`
  Maintain repo-local release-planning truth for backlog targeting.
- `make release-version-preview`
  Show the next auto patch version with no mutation.
- `make release-version-show`
  Show session state, highest stable semver tag, and the next auto version.
- `make dev-validate`
  Run the detached `source-local` maintainer validation lane against current
  unreleased workspace changes. Pytest runs in bounded fresh-process shards so
  one order-contaminated or crashed interpreter cannot erase prior evidence;
  every shard still runs and the command fails on any nonzero shard result.
  This is maintainer-only and release-ineligible.
- `make license-audit`
  Refresh and audit the checked-in third-party attribution ledger.
- `make release-session-show`
  Show the raw sticky session payload.
- `make release-preflight [VERSION=X.Y.Z]`
  Initialize or reuse the sticky release session, reserve the tag, and run the
  canonical release preflight.
- `make release-dispatch`
  Reuse the active session and dispatch the canonical GitHub release workflow.
- `make dogfood-activate`
  Return the Odylith product repo from detached `source-local` to the pinned
  installed runtime after the release exists.
- `make consumer-rehearsal [VERSION=X.Y.Z] [PREVIOUS_VERSION=Y.Y.Y]`
  Rehearse first install, upgrade, rollback, doctor, and Compass behavior in a
  disposable consumer repo from hosted assets.
- `make ga-gate [VERSION=X.Y.Z] [PREVIOUS_VERSION=Y.Y.Y]`
  Run the post-publish dog-food and consumer proof gate.
- `make release-session-clear`
  Intentionally clear the local session after success or abort.

### Owning interfaces and control points
- `Makefile` plus `bin/release-*`, `bin/dogfood-activate`,
  `bin/consumer-rehearsal`, and `bin/ga-gate`
  Thin maintainer entrypoints over the release subsystem.
- `odylith/MAINTAINER_RELEASE_RUNBOOK.md` and
  `odylith/maintainer/GTM_AND_RELEASE_CHECKLIST.md`
  Canonical release-order and launch-readiness operator guidance.
- `odylith/runtime/source/release-notes/vX.Y.Z.md`
  Authored release-note source that drives the consumer upgrade spotlight and
  the tagged GitHub note URL for the released version.
- `bin/_odylith.sh`
  Shared maintainer release-lane authority checks, local session-file
  location, and wrapper plumbing.
- `bin/validate` and `scripts/run_pytest_shards.py`
  Canonical maintainer validation entrypoint and deterministic process-
  isolation boundary for the complete pytest corpus.
- `.github/workflows/release.yml`
  Canonical release workflow with authority, commit-binding, and self-host
  validation gates.
- `src/odylith/runtime/governance/validate_self_host_posture.py`
  Source-level self-host release validation used by the canonical release
  workflow and preflight checks.
- Internal semver/session/publication helpers remain implementation details
  behind these maintainer interfaces and are not part of the public release
  operator contract.

## Release Session Contract
- The release session is keyed by:
  `version`, `tag`, `head_sha`, `source`, and target metadata.
- A live session can only be reused on the same commit. If `HEAD` drifts, the
  session becomes invalid and must be cleared intentionally.
- An explicit `VERSION=X.Y.Z` must be stable semver and cannot be lower than
  the highest published canonical `vX.Y.Z` release.
- If `VERSION` is unset, preflight auto-tags the next patch version from the
  highest published canonical release, floored by the current product source
  version so the first release does not regress below the codebase version.
- The initializer must either create and push the tag at the current `HEAD`,
  prove the tag already exists on that same commit, or safely rebind an
  unpublished reserved tag to the current `HEAD`.
- Dispatch never initializes a session. It reuses the existing session only.

## Authority And Safety Model
- Canonical releases are restricted to:
  `odylith/odylith` on `main` as GitHub actor `freedom-research`.
- Local release wrappers must fail closed unless:
  - the origin remote is canonical
  - GitHub auth resolves to the canonical actor
  - `HEAD` matches `origin/main`
  - the proof checkout itself is clean
- Local wrappers may satisfy the clean-checkout requirement by materializing an
  isolated clean worktree at the canonical `origin/main` commit when the active
  maintainer workspace is dirty or off-main. They must not publish from a
  commit that is merely local-only or ahead of `origin/main`.
- The GitHub release workflow must fail closed unless:
  - the workflow runs in the canonical repo
  - the workflow actor is canonical
  - the workflow ref is `refs/heads/main`
  - the requested `tag` resolves to the session `expected_sha`
  - `GITHUB_SHA` equals that same `expected_sha`
- Release identity validation now pins canonical maintainer authorship for
  commit-history proof and no longer depends on a GitHub-generated committer
  exception in canonical `main` ancestry.
- Local maintainer config still remains strict on both author and committer
  identity. The history gate is intentionally narrower: it validates the
  canonical authored identity that must survive platform merge machinery while
  tolerating the immutable historical maintainer author alias already present
  in older canonical commits.
- The concrete `v0.1.10` follow-up record is
  [B-060](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-07-odylith-v0-1-10-release-feedback-closure-benchmark-reproof-and-ga-lane-hardening.md).
- Release, release-candidate, and test workflows now pin
  `actions/checkout v5.0.1` and `actions/setup-python v6.1.0` to immutable
  SHAs, keep the runner image pinned, and keep the build frontend version
  pinned instead of relying on floating CI inputs.
- Those first-party Action pins must also stay on a currently supported
  GitHub-hosted runtime major. A release-lane Node-runtime deprecation warning
  from pinned first-party Actions is a release blocker, not benign CI noise.
- Release-proof tests must not depend on ambient maintainer workstation
  capabilities. If a unit or candidate-proof assertion needs Codex host-native
  spawn semantics or a discovered `codex` binary, the test must force or mock
  that contract explicitly so GitHub-hosted runners prove the same truth.
- Successful verification output must stay calm across every shipped release
  lane, not only the hosted installer shell. Hosted install, reinstall, upgrade,
  pinned dogfood, consumer rehearsal, and GA gates must not print allowlisted
  trust-warning noise such as `unsupported key type: 7`, `trust.py:177`, or
  `Failed to load a trusted root key` during successful install or upgrade.
  Bootstrap shell and managed-runtime verification must capture both stdout and
  stderr, strip ANSI/Rich styling before benign-warning matching, and fold
  wrapped continuations so `Failed to load a trusted root key: unsupported ...`
  followed by `key type: 7` stays quiet. Suppressed warning details belong in
  structured verification metadata and explicit diagnostics, not install
  success-path output.
- Release assets are authoritative only when the signed manifest, provenance,
  and SBOM all verify for the canonical signer identity.
- Maintainer-local release assets are not closure proof unless
  `build-provenance.v1.json` binds the package to the local git `HEAD` and
  records the local source-tree posture, including branch, dirty flag, and
  dirty-file count. A local dist with an empty provenance commit can be useful
  for debugging, but it cannot support a release-readiness or local-install
  handoff claim.
- Maintainer-local `*.sigstore.json` files are not production attestation proof
  when they are placeholder `{}` payloads. Local install instructions may use
  an explicit localhost skip-verify posture, but release-readiness narration
  must distinguish checksum/provenance proof from canonical signed-attestation
  proof.
- Consumer posture must reject maintainer-only localhost asset overrides and
  Sigstore-bypass toggles; those controls are rehearsal-only and valid only in
  the product-repo maintainer lane.

## Cross-Component Control Flow
### 1. Resolve one version
1. Maintainer previews and inspects release state with `make release-version-preview`
   and `make release-version-show`.
2. When the active slice is still detached `source-local`, maintainers may run
   `make dev-validate` first to validate current unreleased workspace changes
   without claiming canonical release proof.
3. `make release-preflight` initializes or reuses `.odylith/locks/release-session.json`.
4. The session binds the release version and tag to the current `HEAD`.

### 2. Validate and publish
1. Preflight runs the local validation, self-host release gate, split-asset
   packaging, Hatch-based wheel build, and hosted-style local installer proof.
   When the active maintainer workspace is dirty or off-main but already
   matches `origin/main`, preflight may run inside an isolated clean checkout
   of that same commit instead of mutating the active workspace. That proof
   checkout intentionally excludes detached `source-local` workspace changes.
2. `make release-dispatch` reuses the active session and dispatches the GitHub
   release workflow with `tag` and `expected_sha`.
3. The workflow validates authority and commit binding, then publishes the
   wheel, install script, managed base runtime bundles, managed context-engine
   feature packs, signed manifest, provenance, and SBOM.

### 3. Prove the release
1. `make dogfood-activate` returns the product repo to the pinned installed runtime.
2. `make consumer-rehearsal` validates the hosted asset path against a
   disposable consumer repo.
3. `make ga-gate` combines those proofs for the stable public-release lane.

## Failure And Recovery Posture
- A stale or conflicting session must fail closed rather than silently drifting
  to a new version.
- If the requested tag already exists on a different commit and has already
  been published as a GitHub release, the release lane must fail closed rather
  than moving it.
- If the requested tag already exists on a different commit but has not been
  published yet, the release lane should reuse that same version by rebinding
  the unpublished reserved tag instead of burning a new patch version.
- If `HEAD` differs from `origin/main`, the canonical release lane must stop
  before publication.
- If local preflight validation mutates tracked files in the clean proof
  checkout, the lane must fail closed instead of silently publishing from
  temp-only changes.
- A failed or partial release attempt should remain recoverable by reusing the
  same local session after the maintainer fixes the blocking issue.
- Full-suite test validation must collect one stable node order, run bounded
  contiguous shards in fresh Python processes, continue after a failed or
  signaled shard, and return one aggregate failure after all shards finish.
  Replaying a failed node in isolation is diagnostic evidence, not a substitute
  for a complete canonical verdict.
- Session cleanup is explicit so retry evidence is not silently discarded.
- Managed runtime bundles must preserve runtime isolation so a consumer repo's
  active `VIRTUAL_ENV`, Conda env, `PYTHONHOME`, `PYTHONPATH`,
  `PYTHONEXECUTABLE`, `PYENV_VERSION`, `UV_*`, Poetry/Pipenv/PDM selectors,
  or user-site configuration does not bleed into Odylith.
- The release manifest must expose exactly one Odylith wheel plus the expected
  base-runtime and feature-pack assets; preflight must fail closed on sidecar
  wheels, missing wheel metadata, or missing feature-pack asset metadata.
- The release manifest must carry `repo_schema_version` from checked-in
  product-version truth and derive `migration_required` from the registered
  migration registry for the published version. Migration-marked releases must
  be accepted by the hosted installer and routed to the install runtime's
  registered migration planner instead of being rejected by bootstrap shell
  validation.
- Local release smoke should prove the installer from a nested repo directory
  as well as the repo root so the zero-friction repo-root detection contract
  does not silently regress.
- Local release smoke must also exercise both fresh greenfield journeys:
  install into an empty repo, run `odylith show`, run
  `odylith greenfield propose --format json`, apply that exact proposal file
  with confirmation, require a passed Tribunal and first coding handoff, assert
  Radar/Registry/Atlas/Compass surfaces exist, and reject host-side schema
  repair loop strings. A second fresh repo must run confirmed
  `odylith greenfield create` so the one-command shortcut cannot drift from the
  explicit propose/apply path.
- The shared release proof lane must run the installed greenfield release matrix
  after local release smoke and persist the matrix payload as
  `greenfield-post-confirm-matrix.v1.json` in the dist directory. The standard
  leg must cover at least ten high-variance domains, including retained escaped
  regressions from prior installed audits, stay under the 60 second
  standard budget for every create, write complete governed records, pass all
  expert lenses, satisfy strict case-required domain-anchor coverage, and score
  10/10 across the release matrix dimensions. The matrix must also run
  persisted-artifact custody checks: Project implementation prompts must be
  scored from generated `odylith/tooling-payload.v1.js` readback, persisted
  project-brief Markdown must be structurally checked, and generated-domain
  terms actually present in readback artifacts must be rescanned against
  protected platform source and dist custody. Required domain-coverage anchors
  that are already native to platform custody must be resolved through one
  selected-vocabulary baseline scan and reused during per-case readback; the
  matrix must not rescan source or runtime archives once per generated term or
  once per case when a single generated-readback vocabulary scan can preserve
  case attribution.
  The matrix must parse persisted governed readback, not count arbitrary
  nonempty files. Release proof requires valid release catalogs/events, program
  wave records with generated workstream coverage, Compass source/runtime
  records with meaningful payload, generated surface payload globals, and
  persisted source-launch readback. Missing readback blocks the owning quality
  dimension before any 10/10 claim.
  The matrix must also run per-case headless generated browser state proof for
  the Project shell pane, Radar, Registry, Atlas, Compass, Casebook, and
  tooling-shell surfaces. That browser lane must cover normal shell routes,
  Project prompt-card readback,
  invalid-query recovery, and Casebook empty/filter fallback, must provision
  Playwright Chromium through the maintained proof wrapper, and must fail
  closed if Playwright or Chromium remains unavailable in the proof environment.
  The exact matrix interpreter must import Playwright and launch Chromium before
  a one-shot semantic holdout ledger is claimed. Campaign interruption must set
  the shared shard stop signal, terminate the active process group, remove its
  temporary project root, and terminalize a claimed holdout as `interrupted`;
  no child process or reusable `claimed` ledger may survive cancellation.
  The matrix must include rescue smoke by default when post-confirm repair behavior
  changes. That smoke must
  run the packaged CLI in `--repair-tier auto`, inject one exact-token internal
  typed final-gate finding, prove auto-escalation from standard to the 90 second
  rescue budget, write the expected governed records, return a passed final
  manifest, and record the repaired semantic issue code. The release harness
  must keep standard matrix creates free of the internal probe token and must
  apply that token only to the rescue-smoke create subprocess. Source-local
  rescue tests, opt-in-only smoke, synthetic installed-engine probes, local
  release smoke alone, a standalone matrix target that the release lane does not
  invoke, and probe-env leakage into the wrong matrix leg do not substitute for
  this installed release proof. The rescue-smoke result is wiring proof only.
  Release proof must also include a separate host-planned structured rescue leg
  when natural rescue quality is claimed: the leg must emit a typed semantic or
  artifact-plan PatchSet with no deterministic replacement fact, call an
  explicit reasoning provider, preserve the patch-plan or provider-failure
  summary in the final clean manifest as `last_repair_patchset_request`, avoid the
  deterministic rescue-probe issue code, finish under the 90 second rescue
  budget, and write the same governed record floor as the standard matrix.
  Provider-planned operations are the preferred proof. If the provider times
  out, natural rescue quality may still pass only when the PatchSet operation
  names a schema-owned semantic or artifact-plan target, the accepted proposal
  already carries an exact source-owned value for that target, the manifest
  records `structured_patch_fallback.status=applied` with provider-failure
  metadata, the semantic-patch ledger records the applied or idempotent fact,
  and the final post-confirm quality gate passes before governed writes.
  Empty replacement facts without an executable provider plan or source-anchored
  fallback, missing `last_repair_patchset_request`, missing semantic-patch
  ledger evidence, or a clean standard matrix plus synthetic rescue smoke is
  not enough to claim natural rescue quality.
  Explicit empty-list replacement facts are valid only when the PatchSet target
  is a list-valued semantic field and the structured plan records a provider
  decision ledger; a blank, absent, or prose-only replacement fact remains a
  release blocker.
- The local release asset builder, standalone greenfield matrix target, and
  shared release proof lane must run the platform domain-leakage guard against
  current runtime/source guidance, release tooling, and built release assets
  before accepting a release proof. The guard must detect phrase leakage across
  line boundaries plus identifier-shaped leaks such as camelCase or compacted
  multi-word terms. Distinctive fixture vocabulary belongs in tests, explicit
  release fixture catalogs, governed evidence, top-level matrix or rescue proof
  JSON, evaluation corpora, and release
  notes; it must not leak into runtime code, shipped agent guidance, release
  tooling behavior, or bundled default behavior.
- The greenfield release matrix must not rely on hand-curated leakage
  sentinels alone. Preflight and generated-readback leakage proof must include
  explicit case sentinels, required anchors, and conservative distinctive
  source-text phrases from the case prompt or accepted intent while filtering
  generic confirmation/governance wording. If a declared sentinel is already
  platform-native, the harness must choose a source-grounded distinctive
  fallback before failing a case; it may fail preflight only when no
  platform-distinctive candidate remains. Domain-anchor coverage scoring must
  use token-aware matching rather than raw substring containment.
- The standalone `make greenfield-post-confirm-matrix` maintainer target must
  write `greenfield-post-confirm-matrix.v1.json` by default, with
  `GREENFIELD_MATRIX_OUTPUT_JSON` as the explicit override. A stdout-only
  matrix pass is not durable release evidence. The target must also accept an
  explicit fresh-variance case file through `GREENFIELD_MATRIX_CASE_FILE` so
  maintainers can run external high-variance simulations without adding domain
  vocabulary to the platform source catalog. Persisted matrix JSON must include
  per-case post-confirm manifest summaries, natural structured-rescue proof
  when requested by the maintained wrapper, and temp-cleanup proof; leftover
  Odylith simulation roots are release-proof failures, not chat-side cleanup
  chores.
- The tiered `make greenfield-matrix-campaign` discovery harness must keep
  discovery proof and release proof separate. Discovery tiers may use seeded
  installs and controlled concurrency, but they must stream per-case JSONL,
  flush incremental shard result JSON, merge live progress into campaign JSONL
  and snapshot files, cluster failures from typed manifest ownership before
  score buckets, stop on configured failure-cluster thresholds, and emit a
  failure-response packet with failed-result JSON paths, stable case IDs,
  content fingerprints, Casebook-capture requirement, exact failed-subset
  replay instruction, materialized failed-subset replay shards when exact
  source identity exists, and resume order. If stable identity is missing,
  unreadable, or ambiguous, the packet must mark replay materialization
  unavailable and preserve source-shard replay guidance instead of pretending an
  exact subset exists. Case breadth must be evaluated through the shared
  stressor taxonomy and 10-point variance score rather than raw case count
  alone. Campaign summaries must also report failure outcomes by
  stressor class, and failure clusters must carry stressor tags so maintainers
  can identify which ambiguity shapes are failing. Case-generator and shard
  summaries must also persist source-file, tag, stressor, and stressor-by-tag
  stratification evidence so high-volume discovery proves varied
  ambiguity-shape coverage before expensive execution. Pre-result
  child-process failures must write a replayable synthetic shard payload with
  source case identity and prompt fingerprints; interrupted sibling shards
  without failure evidence must not be advertised as failed-subset replay
  inputs. Release readiness remains strict full-install proof with browser,
  rescue, and natural-rescue legs, and a release-tier preflight abort is not a
  completed release proof. Temp cleanup proof must fail on matching stale
  directories, files, or symlinks.
- The optional `make greenfield-matrix-generate-cases` source-pool step must
  consume external case files, not embedded platform domains, and must report
  stressor coverage, variance score, density warnings, and hard missing-stressor
  failures before shards are built. Matrix preflight must flush structured
  failed-case telemetry and incremental result JSON before project execution
  when source metadata is invalid. Live-stop failure response must prefer exact
  failed case identity from running shard telemetry before falling back to
  broader shard replay.
- Local release smoke must inspect installed greenfield guidance files as part of
  the same journey. Installed AGENTS, README, and skill guidance must mention the
  `greenfield create` confirmation path, must forbid hand-authored proposal JSON,
  must explicitly guard against proposal JSON review and parser/schema retry
  narration, must name the minimum Product Intent Confirmation sections, and
  must fail on stale host-drafts-proposal instructions that would send agents
  back into schema-repair loops.
- Local release smoke must treat unavailable previous-release metadata as a
  skipped upgrade rehearsal when the release lookup reports a 404, whether the
  fetch layer exposes the 404 directly or wraps it in operator-facing context.
- Installer progress output is part of release polish. Progress bars must leave
  a clean terminal boundary before child renderer output so transcript lines
  such as Mermaid render results never glue onto elapsed seconds.

## Validation Playbook
### Release
- `make release-version-preview`
- `make release-version-show`
- `make license-audit`
- `PYTHONPATH=src python -m pytest -q tests/unit/test_pytest_shards.py`
- `make release-preflight [VERSION=X.Y.Z]`
- `make release-session-show`
- `odylith validate self-host-posture --repo-root . --mode release --expected-tag vX.Y.Z`
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_release_version_session.py tests/unit/install/test_release_assets.py tests/unit/install/test_release_bootstrap.py tests/unit/runtime/test_validate_self_host_posture.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-08-05 · Implementation:** Implementation evidence linked this component to governed work with workstream scope preserved; 3 verifiable artifact references.
  - Scope: B-142
  - Evidence: `odylith/registry/source/components/release/CURRENT_SPEC.md`, `src/odylith/runtime/domain_intelligence/greenfield_prompt_evidence_interpretation.py`, `tests/fixtures/greenfield-release-corpus/retired-ba25-final-holdout-regressions.v1.json`
- **2026-08-04 · Implementation:** Implementation evidence linked this component to governed work with workstream scope preserved; 3 verifiable artifact references.
  - Scope: B-142
  - Evidence: `odylith/casebook/bugs/2026-08-04-final-holdout-ledger-revision-is-not-bound-to-distribution-provenance.md`, `odylith/casebook/bugs/2026-08-04-semantic-release-recovery-selection-requires-source-audit-binding.md`, `odylith/registry/source/components/release/CURRENT_SPEC.md`
- **2026-08-04 · Implementation:** Implementation evidence linked this component to governed work with workstream scope preserved; 3 verifiable artifact references.
  - Scope: B-142
  - Evidence: `odylith/casebook/bugs/2026-08-04-semantic-holdout-release-preflight-requires-unrelated-source-audit.md`, `odylith/registry/source/components/release/CURRENT_SPEC.md`, `tests/unit/install/test_greenfield_matrix_campaign_release_scope.py`
- **2026-08-02 · Implementation:** Implementation evidence linked this component to governed work with workstream scope preserved; 4 verifiable artifact references.
  - Scope: B-142
  - Evidence: `odylith/registry/source/components/release/CURRENT_SPEC.md`, `src/odylith/runtime/domain_intelligence/greenfield_canonical_meaning.py`, `src/odylith/runtime/domain_intelligence/greenfield_confirmed_components.py`, `src/odylith/runtime/domain_intelligence/greenfield_confirmed_title_completion.py`
- **2026-08-02 · Implementation:** Implementation evidence linked this component to governed work with 2 verifiable artifact references.
  - Evidence: `odylith/casebook/bugs/2026-08-02-greenfield-model-profile-claimed-unobserved-provider-failure.md`, `odylith/registry/source/components/release/CURRENT_SPEC.md`
- **2026-08-01 · Implementation:** Implementation evidence linked this component to governed work with 4 verifiable artifact references.
  - Evidence: `odylith/registry/source/components/release/CURRENT_SPEC.md`, `src/odylith/runtime/domain_intelligence/greenfield_generated_prose_shape.py`, `tests/unit/install/test_greenfield_preconfirm_matrix.py`, `tests/unit/runtime/test_greenfield_generated_prose_shape.py`
<!-- registry-requirements:end -->

## Feature History
- 2026-08-03: Moved canonical full-suite pytest execution behind deterministic fresh-process shards after a long-lived Python 3.13 process emitted order-dependent failures and terminated with `SIGBUS`. The runner preserves collected order, reports every failed or signaled shard, continues the remaining corpus, and returns one fail-closed aggregate verdict. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-308`)
- 2026-07-05: Proved the retained final local-installable dist through strict installed release proof. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`)
  Release proof for
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-final-20260705T200258Z`
  passed with campaign
  `/private/tmp/odylith-final-release-proof-20260705T201226Z/campaign.json`
  reporting `status=release-ready`, `execution_status=passed`,
  `release_proof_status=passed`, `release_readiness_status=proven`, and zero
  failure clusters. The release shard passed 12/12 scientific/deep-tech cases
  at hard `10/10`, browser proof passed, platform generated-readback leakage
  proof passed, temp cleanup passed, and natural rescue committed governed
  records under the 90s rescue budget. Standard create timing stayed below 60s
  with max `47.719s`. Exact installed `grn-sim` replay against the same dist
  returned `0` in `38.349s`, wrote governed records, and had zero scanned
  repeated-copy blockers. Obsolete local release dists were removed so the
  retained package is the only `odylith-local-release-*` directory under the
  research-code root.

- 2026-07-04: Materialized exact failed-subset replay shards from failed campaign output. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The tiered campaign runner now writes `failure_response.failed_subset_replay`
  in the final campaign JSON. When failed result JSON and source case files
  carry exact stable identity, the runner invokes the existing shard builder to
  emit ready-to-run failed-subset shard files; when identity is missing,
  unreadable, ambiguous, or source files are unavailable, it reports an
  explicit unavailable reason and leaves the original shard replay guidance
  intact. The wrapper exposes `GREENFIELD_MATRIX_FAILED_SUBSET_REPLAY_DIR` for
  maintainer-controlled output placement. Focused proof passed the harness
  campaign/sharder/failure-response/generator suite (`69 passed in 1.61s`) and
  shell syntax checks. This is stop-fix-replay custody, not release readiness.

- 2026-07-04: Added stratification evidence to Greenfield matrix case generation and shard summaries. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The high-volume campaign harness now records tag, source-file, stressor, and
  stressor-by-tag distribution in generated case files and tier shard
  summaries. This keeps the discovery lane honest by proving source-grounded
  ambiguity-shape breadth before execution instead of relying on raw case
  counts. Focused proof passed the campaign/generator/sharder harness suite
  (`63 passed in 1.53s`). This is discovery-harness proof, not release
  readiness.

- 2026-07-05: Hardened high-variance leakage-sentinel preflight with corpus-aware fallback candidates. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  External matrix cases can declare source-grounded sentinels that are already
  native to platform custody. The harness now scans declared plus source-derived
  candidates once, excludes platform-native candidates, and fails preflight only
  when no distinctive sentinel remains. Generated-readback leakage proof keeps
  declared sentinels authoritative when usable and otherwise falls back to
  source-derived candidates without adding domain vocabulary to release code.
  Focused proof passed the leakage-preflight and generated-readback regression
  pack (`39 passed in 7.45s`).

- 2026-07-05: Preserved full platform-leakage proof breadth while narrowing external fallback candidates. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  A case-aware source/dist scan showed that raw source-derived fallback
  candidates could misclassify generic quality-obligation wording as project
  domain leakage. The harness now derives fallback candidate sentinels from
  product/title/vocabulary context and confirmed-intent source sections, while
  the official default release proof keeps the full historical 224-term
  platform-leakage corpus. Focused proof passed 38 leakage/preflight tests;
  default source/dist platform leakage passed 224 fixture terms; and exact
  failed-subset case-aware source/dist leakage passed 69 terms with zero
  findings. This is proof-custody filtering, not a domain exception and not a
  weakening of the release leakage guard.

- 2026-07-04: Completed the incremental Greenfield campaign runner architecture slice without promoting discovery to release proof. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The campaign harness now attributes live stop decisions to the shard that
  emitted failed case telemetry, propagates required stressor classes into child
  matrix commands, permits discovery shards to report partial shard-local
  stressor coverage while the tier owns aggregate coverage, writes replayable
  synthetic payloads for launch and cleanup failures, and reports
  `discovery-passed`, `release-ready`, `failed`, or `skipped` as distinct
  campaign statuses. `execution_status` remains the CLI exit contract, while
  release readiness still requires the strict full-install release tier with
  browser, rescue, natural rescue, platform-leakage, temp-cleanup, and artifact
  quality proof. Focused proof passed the synthetic/replayability pack, focused
  harness/preflight checks, Compass visible-copy checks, and the full
  install/matrix harness suite (`135 passed in 15.98s`).

- 2026-07-04: Added source-grounded Greenfield case generation and structured preflight telemetry to the campaign harness. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The release harness now includes `bin/greenfield-matrix-generate-cases` and
  `scripts/release/greenfield_matrix_case_generator.py` for selecting external
  case pools by stressor coverage, source/tag balance, and density without
  adding domain vocabulary to Odylith source. Matrix preflight now emits
  structured `preflight_failed` case results, incremental result JSON, and
  run-stop telemetry before expensive project execution when required terms,
  leakage terms, stressor coverage, or platform-domain custody are invalid.
  Campaign progress records running cases and per-shard failed identity so
  live-stop failure-response packets can replay the exact failed subset, and
  explicit `required_stressors` now apply even when high-variance defaults are
  disabled. Tooling readback moved to an anchored payload reader that resolves
  the real `__ODYLITH_TOOLING_DATA__` assignment instead of first-brace parsing.
  Focused proof passed compile, shell syntax, an external source-case generator
  smoke, and the focused install/matrix regression pack (`58 passed in 8.45s`).
  This is discovery-harness proof, not release readiness.

- 2026-07-04: Hardened Greenfield campaign replayability, stressor outcomes, and release-proof status boundaries after reviewer audit. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The campaign runner now writes replayable synthetic matrix payloads when a
  child shard dies before normal result JSON emission, preserving source case
  IDs, stressor tags, and prompt fingerprints for exact failed-subset replay.
  Failure-response aggregation moved into `greenfield_matrix_failure_response.py`
  so interrupted sibling shards without failed-case evidence are excluded from
  replay inputs. Campaign summaries now include stressor-class outcomes and
  stressor-tagged clusters, release-proof preflight aborts report
  `release_proof_completed=false`, and temp cleanup proof fails on stale
  files and symlinks as well as directories. Focused proof passed 53
  reviewer-boundary tests, the widened 134-test install/greenfield harness
  suite, compile, shell syntax, scoped diff hygiene, and a disposable campaign
  smoke that proved intentional failure still flushes progress and a
  failure-response packet without claiming release readiness.

- 2026-07-04: Promoted Greenfield campaign stressor taxonomy and failure-response custody. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The campaign harness now has a shared stressor taxonomy owner and 10-point
  variance score used by campaign summaries and shard selection, and the
  maintained default matrix cases carry explicit stressor metadata so breadth
  is measured by ambiguity shape rather than only project count. Failed
  campaigns now persist a failure-response packet that requires Casebook
  capture, points at failed shard result JSON, preserves stable case IDs and
  fingerprints for exact replay, and states the stop-fix-replay sequence before
  volume discovery can resume. Focused proof passed 47 tiered harness tests,
  77 installed matrix/proof-scope tests, compile, scoped `git diff --check`,
  Atlas D-047 render at 47 fresh / 0 stale, and a disposable campaign smoke
  that proved telemetry and failure-response behavior on a controlled fake
  install failure. This is discovery-harness proof, not release readiness.

- 2026-07-04: Hardened Greenfield campaign replay identity and local-temp portability after reviewer audit. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  Failed-subset replay now distinguishes strong case identity
  (`case_id`, prompt hash, confirmed-intent hash) from weak display-name
  evidence, and uses weak names only when a failure cluster carries no stronger
  identity. This keeps duplicate display names from collapsing unrelated cases
  while still replaying cluster-only failures from older or partial result
  payloads. Matrix wrappers and the source default no longer assume
  `/Users/freedom/mock`; disposable project roots default to the host temp
  directory unless `TEMP_PARENT` explicitly overrides it. Focused proof passed
  the sharder, campaign, bootstrap, and matrix wrapper regressions plus a
  two-case tiered shard smoke where failed-subset, 60-case regression,
  240-case discovery, release-proof, and volume-discovery tiers all reported
  passed. This remains harness/discovery custody and does not convert a
  no-browser or no-natural-rescue run into release readiness.

- 2026-07-04: Hardened tiered Greenfield campaign telemetry, release-proof variance, and failed-subset identity. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The release discovery harness now emits a failed case result when clone or
  case execution raises after `case_started`, then flushes incremental payload,
  `case_completed`, and `run_stopped` telemetry instead of leaving the shard
  opaque. The merged campaign snapshot backfills shard-level failed case and
  cluster counts only for cases not already observed from child telemetry, so
  stop decisions remain live without double-counting. Release-proof tiers now
  enforce requested stressor coverage instead of relying on discovery-tier
  variance, and the sharder dedupes/replays no-id cases by prompt fingerprint
  so duplicate names cannot corrupt exact failed-subset replay.

- 2026-07-04: Added source-case required-term provenance to the Greenfield matrix harness. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  External case files now fail at ingestion when `required_terms` cannot be
  grounded as source tokens or phrases in the case prompt or confirmed intent.
  The sharder therefore rejects invalid evaluator metadata before writing tier
  files or launching installed campaigns, rather than burning successful
  project creates before discovering an impossible domain-term obligation inside
  one shard. The same pass gives pre-result child-process failures a stable
  `campaign.shard-process-failed` cluster with tail-preserved stderr, so final
  campaign JSON remains actionable even when no child matrix result payload was
  written. The gate is intentionally token-provenance based: prefixed words do
  not ground shorter required terms, while exact source terms remain valid.

- 2026-07-03: Isolated concurrent Greenfield matrix shard temp cleanup scope. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The tiered campaign runner no longer lets concurrent discovery shards share
  one cleanup-proof parent. Each shard now receives a campaign-owned isolated
  temp parent, stale copies of that shard scope are removed before launch, the
  shard temp parent is recorded in progress/result payloads, and the campaign
  removes that shard temp parent after completion or interruption. This keeps
  strict temp-cleanup proof intact while preventing a finished shard from
  falsely failing because an in-flight sibling still has an active simulation
  root. The fix is harness-scoped and does not weaken artifact quality gates or
  convert discovery evidence into release readiness.

- 2026-07-03: Completed tiered Greenfield campaign progress and replay custody. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The release harness now treats high-volume Greenfield discovery as a tiered
  campaign rather than final-only shard execution. Matrix runs flush their
  result payload incrementally while cases complete; the campaign runner tails
  per-shard telemetry into merged JSONL and live snapshot files; and live
  cluster evidence can stop scheduling and interrupt sibling shards before a
  known-bad class burns the rest of the run. Failed-subset replay is keyed by
  stable case identity, slug, prompt hash, and confirmed-intent hash instead of
  display names alone. The sharder now emits failed-subset, 60-case regression,
  120-case discovery, 240-case discovery, and strict release-proof tiers, with
  per-tier worker limits and final output that keeps discovery status separate
  from browser/natural-rescue release readiness. This is harness custody only:
  it does not relax artifact-quality gates and does not convert discovery
  evidence into release proof.

- 2026-07-03: Tightened Greenfield matrix leakage-sentinel distinctiveness. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The platform domain-leakage preflight now rejects short declared case
  sentinels made only from platform-native or common governance terms before
  scanning Odylith source and built package surfaces. This keeps release
  leakage proof strict while preventing legitimate platform custody prose from
  blocking discovery shards before any project create occurs. Project-specific
  declared phrases remain authoritative, and source-derived fallback terms
  still preserve coverage for cases without explicit sentinels. Focused proof
  covered the false-positive sentinel class and retained valid multi-token
  project phrases; the affected installed discovery shards reran cleanly after
  the selector fix. This is leakage-proof vocabulary custody only: it does not
  suppress platform findings, weaken generated-artifact readback checks, or
  convert no-browser discovery evidence into release readiness.

- 2026-07-03: Proved fresh tiered-replay package on selected installed cases. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  Fresh local-release dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-working-tiered-replay2-20260703`
  passed build-time platform leakage, checksum, installer syntax, and archive
  readability checks. The selected installed package matrix passed the exact
  actor-led product-view replay plus the leakage-sentinel tranche with 7/7
  governed post-confirm writes, hard 10/10 scored quality, zero issues, all
  expert lenses green, max standard create time of 37.229s, generated-readback
  leakage proof passing, and temp cleanup passing. This remains discovery and
  package proof only because browser proof and natural rescue proof were not
  requested; release proof remains browser-strict and natural-rescue-strict.

- 2026-07-03: Proved 72-case Greenfield volume-discovery campaign on fresh package. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The fresh package passed the full available 72-case high-variance volume tier
  with two-shard concurrency, stop-on-first-failure thresholds, hard 10/10
  scored quality on every case, zero issues, zero failure clusters, and no
  standard-path create over 60s. Timing was max 39.321s, average 33.575s, and
  p95 38.143s. The tier covered every tracked stressor class and left no
  generated simulation roots under `/Users/freedom/mock`. This is discovery
  proof only; release readiness still requires browser surface proof and
  natural rescue proof.

- 2026-07-03: Strict Greenfield release proof blocked on natural host-planned rescue. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The same fresh package passed all twelve standard release-proof cases, browser
  proof, platform-domain leakage proof, temp cleanup, and synthetic rescue, but
  failed the natural structured-rescue release leg before governed writes.
  `structured_rescue_semantic_patch` remained unrepaired for
  `SemanticModelIR.domain_ontology.external_systems` because the Tribunal patch
  planner provider timed out after 45 seconds and returned no schema-bound
  operation. Release custody must keep natural rescue fail-closed: discovery
  volume proof and synthetic rescue do not prove release readiness until the
  provider-backed semantic patch path succeeds inside the 90-second rescue tier.

- 2026-07-04: Added completion-priority structured-rescue fallback custody. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  Local Codex and Claude CLI probes proved that tiny schema-bound structured
  patch requests can still miss the rescue budget. The release proof contract
  now keeps the host attempt first but allows a short provider-timeout fallback
  only for source-owned, schema-addressed semantic PatchSet operations. The
  manifest must preserve the provider failure, `structured_patch_fallback`
  metadata, semantic-patch ledger evidence, repaired issue code, final passed
  post-confirm manifest, and committed governed write. Source-local proof
  completed the natural structured-rescue create in 43.439s with governed writes
  committed after a 12.0s Codex timeout and source-anchored semantic fallback.
  Strict installed release proof from a fresh dist remains required before
  release readiness can be claimed.

- 2026-07-04: Proved strict installed release proof for the source-anchored rescue fallback. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  Fresh working-tree dist
  `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-working-tiered-rescue-fallback-20260704`
  passed build leakage, checksum, shell-syntax, wheel, and runtime-archive
  verification. The strict release campaign
  `/tmp/odylith-tiered-rescue-fallback-release-campaign.v1.json` finished with
  `release_readiness_status=proven`, no failure clusters, and a passed
  release-proof tier. The installed shard passed 12/12 full-install cases with
  browser proof, zero issue rows, complete governed evidence, and standard
  create timings of 30.674-40.448s. Synthetic rescue passed, and natural rescue
  committed governed writes in the rescue tier with `cli_create_seconds=67.639`,
  manifest elapsed 40.888s, provider timeout recorded after 12.0s, and
  `structured_patch_fallback.status=applied`. This is working-tree release proof;
  published-release closure still requires the normal stable checkpoint.

- 2026-07-04: Hardened tiered Greenfield campaign blocker extraction and live proof telemetry. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The release harness now keeps multiline final-gate blockers structurally intact
  while deriving failure-cluster keys. Plain-text and JSON-backed errors are
  scanned line by line, wrapper/remediation lines are skipped, and the first
  concrete blocker bullet becomes the replay cluster before score buckets are
  considered. This protects the failed-subset replay loop from grouping real
  post-confirm issues under generic `issue(s)` text. The same proof pass keeps
  the tiered campaign contract pinned: per-case matrix payload flushing, merged
  campaign progress JSONL/snapshot files, failed-subset/60/120/240/release
  shards, stressor-coverage checks, per-shard temp cleanup scopes, and discovery
  status separated from release readiness. Focused proof passed 29 campaign and
  sharder tests, the widened 108-test install/matrix suite, harness compile
  checks, command-help checks, and diff hygiene.

- 2026-07-04: Closed reviewer-found live telemetry and cleanup gaps in the Greenfield campaign harness. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  Per-case matrix execution now applies generated platform-domain leakage
  verdicts before telemetry, stop-threshold evaluation, and incremental result
  flushing, so leakage failures participate in live clustering instead of
  appearing only at final post-processing. The matrix also persists the partial
  result payload before deleting the generated repo, then converts cleanup
  failure into a failed proof result instead of losing the last case update. The
  standalone matrix wrapper only selects release proof when browser proof,
  installed rescue smoke, and natural rescue proof are all enabled; explicit
  debug skips downgrade the run to discovery proof. Campaign shard temp cleanup
  now fails closed with a `campaign.shard-temp-cleanup-failed` cluster rather
  than swallowing deletion errors. Focused reviewer-finding proof passed 26
  tests, the widened install/matrix suite passed 111 tests, and compile plus
  shell-syntax checks passed.

- 2026-07-03: Added merged Greenfield campaign progress and release-tier preflight. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-047)
  The tiered Greenfield matrix campaign now writes merged
  `campaign-progress.v1.jsonl` and live `campaign-progress.v1.json` snapshots
  while shards run, including per-case counts, running shard state,
  telemetry-derived stop decisions, and cross-tier failure-cluster counts. The
  campaign payload carries an aggregate failure-cluster summary, and discovery
  tiers stop scheduling pending shards after the configured failure or cluster
  threshold while signaling in-flight sibling shards to stop after actionable
  telemetry. Cluster keys now prefer typed post-confirm manifest issue ownership
  and concrete blocker text before falling back to score buckets, so repeated
  mechanisms remain diagnosable. The sharder now emits variance evaluation for
  each tier and can build failed-subset replay from top-level campaign failure
  clusters, so high-volume discovery is measured by stressor coverage and
  ambiguity-shape density, not only case count. Release-proof campaign runs now
  execute component-forensics and Chromium preflight before full-install
  browser/natural-rescue shards, and direct release-tier matrix invocations are
  rejected unless browser proof, installed rescue smoke, and natural rescue
  proof are requested. This improves discovery observability and release-proof
  custody without converting discovery passes into release readiness.

- 2026-07-03: Added tiered Greenfield matrix campaign observability and proof-tier custody. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-021)
  The installed Greenfield matrix now writes incremental JSONL telemetry,
  carries a persisted `campaign` summary, exposes failure-cluster and stressor
  coverage controls, and enforces that release tier cannot use seeded installs,
  skipped browser proof, or early-stop thresholds. The new tiered campaign
  wrapper runs failed-subset, regression, volume-discovery, and release-proof
  shards in order with controlled discovery concurrency and stop-before-next
  behavior after new failure evidence. The runner reports release proof
  completion, release proof status, and release readiness status separately
  from selected-tier pass/fail so discovery-only campaigns cannot be mistaken
  for release proof. Discovery runs remain non-release proof; release proof
  remains full install with browser and natural rescue enabled.

- 2026-07-03: Added metadata-driven Greenfield matrix shard building. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-021)
  The maintainer release harness now includes `make greenfield-matrix-shards`
  and `greenfield_matrix_shards.py` to build failed-subset, regression,
  volume-discovery, and release-proof shard files from external case JSON,
  prior result JSON, and stressor metadata. The sharder emits campaign
  environment hints, rejects missing required stressor coverage before a volume
  run starts, and keeps project-domain vocabulary in external cases rather
  than in Odylith release code. Focused proof passed the sharder/campaign test
  suite, compile and Bash syntax checks, and a disposable command-surface smoke.

- 2026-07-03: Hardened high-volume greenfield matrix leakage-term selection. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`)
  Declared case sentinels now reject low-entropy two-token artifact phrases
  such as generic `evidence` or `proof` heads while preserving project-specific
  declared phrases. This keeps platform domain-leakage proof strict without
  letting ordinary Odylith governance language block high-volume discovery
  shards as false positives. Targeted proof covered the batch-06 failure shape,
  existing explicit platform-word project phrases, and default matrix coverage.

- 2026-07-03: Separated high-volume greenfield discovery status from release browser proof. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-046)
  The installed greenfield matrix keeps browser proof required for release
  proof by default, but explicit `BROWSER_PROOF=0` high-volume discovery runs
  now pass the existing skipped-browser allowance into the matrix CLI. The
  aggregate status therefore matches the per-case scoring contract:
  no-browser volume runs can pass as
  `volume_discovery_without_browser_surface_proof`, while release-proof lanes
  still require browser state proof. Focused harness regressions passed and
  the shard-05 rerun showed 30/30 governed project creates at hard 10/10 with
  cleanup and platform leakage passing before the harness status fix.

- 2026-07-01: Bound maintainer-local release provenance to the source git head. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bugs: `CB-209`, `CB-215`; Diagram: D-023)
  Independent closure review found that the greenfield committed-head dist
  carried strong behavioral proof but weak local provenance: the generated
  `build-provenance.v1.json` retained the canonical workflow identity while
  leaving `workflow.sha` empty. The release asset builder now records the local
  `HEAD` as the provenance SHA for maintainer-local builds and adds a
  `source_tree` block with branch, dirty state, dirty-file count, and head.
  Hosted release builds keep the GitHub-provided SHA. Local install handoff now
  requires a rebuilt dist from the post-fix commit before release-readiness
  claims continue.
  The follow-up `da2643ed` local dist passed that contract with clean
  commit-bound provenance, 14/14 maintained installed matrix cases, 6/6
  scientific variance cases, exact `grn-sim` replay, and explicit notation that
  placeholder local Sigstore sidecars are not canonical attestation proof.

- 2026-07-01: Added scientific evidence-depth readback to greenfield release scoring. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-215`; Diagram: D-045)
  The installed greenfield matrix now treats scientific/evaluation semantics as
  a scored proof obligation, not a shallow domain-term hit. Package evidence
  findings derive required evidence terms from typed `EvaluationSemantics`
  fields and inspect governed readback for method/protocol,
  baseline/comparison, uncertainty/tolerance, and reproducibility obligations
  before the domain-expert lens can pass. This keeps release proof aligned with
  the premium artifact bar while preserving generic platform vocabulary;
  fixture terminology stays confined to matrix cases and evidence records.

- 2026-06-30: Proved the structured-rescue clear-fact checkpoint through fresh installed release assets. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-211`; Diagram: D-043)
  Fresh dist `odylith-local-release-0.1.15-clear-list-fix` passed the platform
  domain-leakage build guard across 285 distinctive fixture terms. The
  installed release matrix then passed 13/13 maintained standard cases with
  hard 10/10 brutal quality scores, zero quality/browser/platform-leakage
  findings, browser proof attempted and passed for every case, complete
  governed records, max standard create time 30.563s, average standard create
  time 27.854s, generated-term leakage proof across 213 readback terms, and
  clean temp cleanup. Synthetic auto-rescue passed in 38.917s. The real
  installed natural structured-rescue leg passed in 60.926s under the 90s
  rescue budget with `structured_rescue_semantic_patch` repaired, a
  provider-backed Tribunal plan with one accepted operation and no rejections,
  committed governed writes, and natural rescue quality proven.

- 2026-06-30: Promoted governed readback parsing into the greenfield release-matrix score contract. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-209`; Diagrams: D-043, D-046)
  The release proof harness now reads persisted release catalogs/events, program
  wave records, Compass source/runtime records, generated surface payload
  globals, and persisted source-launch records through a first-class readback
  owner before scoring. Release/program freshness is tied to actual generated
  Radar workstream ids and program umbrella coverage; preview-only next-step
  output no longer satisfies operator evidence; omitted browser proof is scored
  as its own premium blocker. Matrix score construction now lives in
  `greenfield_matrix_quality_scoring.py`, keeping the installed runner focused
  on orchestration and cleanup instead of carrying score internals. Focused
  source proof passed; rebuilt installed matrix proof with browser state remains
  the release gate.
- 2026-06-30: Hardened greenfield release proof against partial sentinel and substring-coverage false positives. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-209`)
  Reviewer audit found the previous leakage proof could miss omitted case
  vocabulary when any manual `leakage_terms` were present, and the matrix
  domain-coverage score could pass on raw substrings. The release harness now
  derives conservative multi-token source-text leakage phrases from the case
  prompt or accepted intent, unions them with declared sentinels and required
  anchors for preflight/readback proof, and scores domain coverage with the
  shared token-aware matcher. The first broad extractor attempt overreached
  into generic phrases; that failed mechanism is captured in Casebook. Focused
  leakage/matrix proof passed 73 tests, the full install unit suite passed 448
  tests, and the strengthened source/dist leakage guard passed across 387
  distinctive fixture terms against the `88df22be` dist. Rebuilt installed
  matrix and fresh-variance proof from the post-fix commit remain required
  before release readiness is reclaimed.
- 2026-06-30: Fixed release-matrix generated-readback leakage baseline custody. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-209`)
  A `7cf9d2ed` release-dist proof run showed the platform leakage build gate
  can pass while the installed matrix still stalls if generated-readback
  required-anchor suppression rescans protected source and runtime tarballs
  term by term. The matrix now computes platform-native required anchors once
  for the selected case vocabulary, scans generated-readback leakage terms as
  one union while preserving case attribution, and reuses the tokenized
  source/dist custody corpus across repeated term sets. Follow-up review also
  found that release scripts were outside protected custody and that wrapped or
  identifier-shaped phrases could escape line-bounded matching. The guard now
  includes `scripts/release`, keeps intentional fixture vocabulary in the
  excluded matrix fixture catalog, tokenizes documents across line boundaries,
  splits identifier case transitions, and catches compacted multi-word phrase
  tokens. Focused install/leakage proof passed 71 tests; cold/warm source+dist
  guard timings against the `7cf9d2ed` dist were 28.228s, 0.062s, and 0.809s
  with zero findings. Rebuilt installed matrix proof remains required before
  release readiness is reclaimed.
- 2026-06-30: Proved release package `odylith-local-release-0.1.15-aebe9245` after Project proof-custody hardening. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-209`; Diagrams: D-043, D-046)
  The maintained installed matrix persisted at
  `greenfield-post-confirm-matrix-20260630-aebe9245.v1.json` passed 13/13
  standard cases with hard 10/10 scores, zero quality issues, zero browser
  issues, complete governed records, standard create timings of 22.338-28.973s,
  per-case generated browser-state proof including Project shell state,
  generated-term leakage proof across 55 readback terms with zero protected
  platform findings, synthetic typed-probe auto-rescue in 33.617s, and clean
  temp cleanup. Natural non-internal host-model rescue remains outside this
  proof scope.
- 2026-06-29: Broadened the platform domain-leakage release guard. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-209`; Diagram: D-043)
  The guard now scans root `.codex` guidance, public `docs/`, historical
  escaped-domain sentinels, and Odylith launchers/runtime/guidance inside
  runtime tarballs while excluding third-party packages, governed evidence, and
  matrix proof JSON. Line tokenization is cached per scanned line so broader
  archive custody remains bounded. Focused install proof passed 52 tests, and
  source plus local dist `odylith-local-release-0.1.15-cd6cf643` passed the
  strengthened leakage check across 49 distinctive fixture terms with zero
  protected-custody findings. Fresh local release dist
  `odylith-local-release-0.1.15-14f5102a` then rebuilt from the committed
  checkpoint and passed the same 49-term platform domain-leakage build gate.
- 2026-06-29: Proved release package `odylith-local-release-0.1.15-3fbacb91` after adding the platform domain-leakage gate. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-209`) The build gate passed across
  19 distinctive fixture terms, the maintained installed matrix passed 13/13
  standard cases with hard 10/10 scores and browser proof in 24.230-28.677s,
  synthetic typed-probe rescue smoke passed in 35.129s, the fresh ten-domain
  variance matrix passed with hard 10/10 scores and browser proof in
  25.483-29.269s, and temp cleanup was clean.
- 2026-06-29: Hardened the greenfield installed-matrix scorer. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142)) (Bug: `CB-209`; Diagrams: D-043)
  Fresh variance exposed shallow 10/10 evidence. Domain readback now uses rendered
  public artifacts rather than runtime custody JSON or accepted-project source
  launch text, operator usefulness requires real project-brief and next-step
  preview artifacts rather than custody-file counts, and the Python matrix
  entrypoint fails when browser proof is skipped unless an explicit debug flag
  allows that posture. Focused release-matrix proof passed, six source-local
  high-variance creates scored hard 10/10 under 23s, and release readiness
  remains blocked until the rebuilt installable dist reruns the installed
  matrix with browser proof.
- 2026-06-29: Proved the hardened matrix on fresh installed dist `a4ede761`. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142)) (Bug: `CB-209`; Diagrams: D-043)
  Local release dist `odylith-local-release-0.1.15-a4ede761` passed the
  maintained installed matrix with 13/13 standard cases at hard 10/10, zero
  quality issues, per-case generated browser-state proof attempted and passed,
  max create time 27.078s, clean temp cleanup, persisted matrix JSON, and
  synthetic typed-probe rescue wiring smoke passing in 33.430s. This proves the
  standard installed release matrix for this checkpoint; it does not convert
  the synthetic rescue smoke into natural host-model semantic rescue proof.
- 2026-06-29: Reopened installed release readiness after a fresh twelve-case adversarial matrix against `a4ede761`. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142)) (Bug: `CB-209`; Diagrams: D-043, D-045)
  Eleven non-reused cases passed with hard 10/10 scores and browser proof, but
  one valid proof-action list failed before governed writes on an over-broad
  gerund actor-role splice finding. Source now fixes the detector with shared
  actor-role head custody and clause-local scanning, removes mechanical
  `changes it` copy from generated state-boundary artifacts, and proves the
  exact source-local repro in 19.192s with complete records and a passed
  manifest. Release remains blocked until a rebuilt installable dist reruns the
  adversarial installed matrix and browser proof from the current commit.
- 2026-06-29: Reopened greenfield release readiness after fresh installed variance. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142)) (Bug: `CB-209`)
  Despite the earlier `13b796e9` installed matrix pass, a fresh ten-case installed variance run
  against the same dist failed three cases and cleaned its temp root: one
  domain-readback anchor miss after governed writes, one no-write semantic-slop
  blocker, and one Registry under-provisioning failure after governed writes.
  Release proof must now harden the matrix scorer so public/rendered artifacts,
  real project-brief/next-step evidence, distinct governance dimensions, and
  mandatory browser proof are required before a 10/10 claim.
- 2026-06-29: Release proof correctly failed the fresh `odylith-local-release-0.1.15-3d13f434` installed matrix. Twelve of thirteen standard greenfield cases passed with hard 10/10 scores and browser proof, and synthetic wiring-only rescue smoke passed in 33.936s, but sparse disclosure confirmation failed the release gate with score 0/10 because generated governance depth and domain-anchor coverage were insufficient. Release remains blocked until a rebuilt dist passes the maintained installed matrix from the current commit; older passing dist evidence cannot be reused as release readiness. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-209`)
- 2026-06-30: Proved rebuilt installed checkpoint `odylith-local-release-0.1.15-9a764dc7`, then reopened shipped-custody proof for a newer source-level domain-neutralization fix. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-209`)
  The maintained installed matrix at
  `odylith-local-release-0.1.15-9a764dc7/greenfield-post-confirm-matrix-20260630-9a764dc7.v1.json`
  passed 13/13 standard cases with hard 10/10 scores, zero issues, browser
  proof, complete governed records, 22.259-29.208s standard create timings,
  synthetic typed-probe rescue wiring in 33.474s, and clean temp cleanup. A
  follow-up source audit removed unconditional notification semantics from
  generic status-view Registry profiles; fresh local release dist
  `odylith-local-release-0.1.15-3c616936` passed the platform domain-leakage
  build gate across 52 distinctive fixture terms.
- 2026-06-30: Preserved standard-path release benchmark wins while reopening natural-rescue release proof for host-ledger custody. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-208`; Diagram: D-043)
  Fresh dist
  `odylith-local-release-0.1.15-31ab2559` passed 13/13 maintained standard
  greenfield cases with hard 10/10 scores, zero package/browser/platform
  leakage issues, max standard create time 27.835s, and synthetic typed-probe
  rescue at 34.084s. The real provider-backed natural structured rescue leg
  failed after 69.399s because raw host rationale entered
  `proposal.semantic_patch_ledger` and was correctly rejected by the final
  semantic-slop gate before governed writes. Release readiness remains blocked
  until a rebuilt dist proves the safe host-ledger projection fix through the
  maintained installed matrix with browser proof and natural rescue enabled.
- 2026-05-03: Added the v0.1.14 release-planning target and made `next` point to `release-0-1-14`; B-141 and B-142 are active there, while B-140 is recorded as completed release history for migration-observer proof. Greenfield project proposals now default omitted consumer project release selectors to `0.0.1` so first-release planning does not borrow Odylith's own `next` alias. (Plans: [B-141](odylith/radar/radar.html?view=plan&workstream=B-141), [B-142](odylith/radar/radar.html?view=plan&workstream=B-142))
- 2026-03-27: Added a first-class maintainer release subsystem with sticky version sessions, stable semver auto-tagging, canonical commit-bound release dispatch, and a dedicated release runbook. (Plan: [B-005](odylith/radar/radar.html?view=plan&workstream=B-005))
- 2026-03-28: Reset the local relaunch narrative to restart preview at `v0.1.0`, made split managed assets part of the canonical release lane while keeping install full-stack by default, and blocked dispatch on local hosted-asset installer proof. (Plan: [B-005](odylith/radar/radar.html?view=plan&workstream=B-005))
- 2026-03-28: Promoted `v0.1.0` from a proved preview relaunch to the GA baseline for the supported macOS Apple Silicon and Linux platform matrix, and carried the release-reset pin-realignment hardening into the GA branch. (Plan: [B-007](odylith/radar/radar.html?view=plan&workstream=B-007))
- 2026-04-08: Added repo-local release planning with immutable `release_id`, explicit `current` and `next` aliases, append-only workstream targeting history, and authored release-note name alignment for versioned release records. (Plan: [B-063](odylith/radar/radar.html?view=plan&workstream=B-063))
- 2026-04-08: Clarified that current-release visibility is manual-close driven: governed read models keep the active current release visible until maintainers explicitly mark it `shipped` or `closed`, even when no targeted workstreams remain. (Plan: [B-065](odylith/radar/radar.html?view=plan&workstream=B-065))
- 2026-04-08: Clarified that active current releases may keep finished completed members visible from release history until explicit ship or closeout, without restoring those workstreams to active targeting. (Plan: [B-066](odylith/radar/radar.html?view=plan&workstream=B-066))
- 2026-04-09: Hardened `odylith release add` so maintainers can attach an already finished workstream to the active release as completed release history instead of reviving it as an active target. (Plan: [B-066](odylith/radar/radar.html?view=plan&workstream=B-066)) (Bug: [CB-082](odylith/casebook/casebook.html?bug=CB-082))
- 2026-04-09: Codified release-target progress semantics so release-member badges use shared execution-progress truth, show tracked partial completion honestly, and never render active implementation with unchecked execution as fake `0% progress`. (Plan: [B-068](odylith/radar/radar.html?view=plan&workstream=B-068)) (Bug: [CB-087](odylith/casebook/casebook.html?bug=CB-087))
- 2026-05-07: Added release-smoke coverage for both empty-repo greenfield paths: the explicit `show -> greenfield propose --format json -> greenfield apply --proposal-file --confirm -> surfaces` journey and the one-command `greenfield create --confirm` shortcut. The same slice tightened installer progress output so child renderer lines no longer collide with the elapsed progress row. (Plan: [B-005](odylith/radar/radar.html?view=plan&workstream=B-005); Bugs: `CB-180`, `CB-181`)
- 2026-05-07: Extended release smoke from runtime behavior into installed guidance proof: fresh installed AGENTS/README/skill guidance must point confirmation at `greenfield create --confirm`, forbid hand-authored proposal JSON, and reject stale host-drafts-proposal instructions. (Plan: [B-005](odylith/radar/radar.html?view=plan&workstream=B-005); Bugs: `CB-176`, `CB-181`)
- 2026-07-05: Tightened the managed AGENTS release contract after local release smoke caught a post-commit dist whose fresh install guidance omitted the exact `proposal JSON` guard. The release component now treats explicit proposal-JSON review and parser/schema retry wording as part of installed guidance proof, and the managed AGENTS generator carries a regression assertion for that wording. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-181`)
- 2026-07-05: Extended the same managed AGENTS contract to include the confirmation-format proof tokens (`Product story`, `State object`, `First complete path`, `Proof boundary`, and no wall of prose) after a rebuilt proof dist exposed that missing section list in fresh-install smoke. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-181`)
- 2026-06-28: Required both canonical release proof and the standalone greenfield matrix target to persist `greenfield-post-confirm-matrix.v1.json`, expanded the installed standard matrix to at least ten/currently thirteen domains, and labeled rescue smoke as wiring-only proof unless a natural repairable failure passes under the 90 second tier. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-209`)
- 2026-06-28: Promoted generated-surface browser proof from optional single-case smoke into the maintained release matrix contract. The direct matrix target enables browser proof by default unless `BROWSER_PROOF=0` is set for local debugging, shared release-candidate proof passes `--include-browser-proof`, maintained wrappers provision Playwright Chromium before the browser lane, and release proof now treats unavailable Playwright/Chromium as a fail-closed release blocker. The browser lane now covers generated normal shell routes, invalid-query recovery, Casebook empty/filter fallback, Atlas generated diagram state, and invalid Atlas diagram recovery instead of only heading-level route smoke. Persisted matrix proof now marks requested-but-unattempted browser proof as skipped and failed rather than passed. The matrix surface contract also covers Casebook and rejects stale asset-path or malformed tooling-payload wiring before claiming generated artifact quality. Rebuilt dist `odylith-local-release-0.1.15-atlas-state-proof` passed the twelve-case installed matrix with 10/10 scores, zero issues, every browser proof attempted and passed, create timings of 20.660-23.125s, clean temp cleanup, persisted matrix JSON, and synthetic wiring-only auto-rescue at 27.280s. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-209`)
- 2026-06-28: Tightened release-matrix score evidence after a fresh installed audit showed a Project prompt could be human-weak while the matrix still emitted a one-line 10/10 explanation. Perfect-score matrix results now include concrete completion counts, rendered-surface counts, traceability counts, Project prompt counts and findings, and passed expert-lens names in `score_explanation`, so release reviewers can audit why a 10/10 was awarded instead of trusting row counts alone. The default matrix now retains the escaped prompt-quality regression, and prompt quality hardening rejects bounded gerundized actor/product-subject drift without using broad suffix-count gates. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-209`)
- 2026-06-28: Proved the prompt-quality release checkpoint through fresh local installable dist `odylith-local-release-0.1.15-prompt-quality-proof`. The maintained standard matrix now covers thirteen domains, including the retained prompt-quality regression, and passed every case with 10/10 release score dimensions, zero prompt findings, zero total issues, every browser proof attempted and passed, create timings of 20.666-23.468s, clean temp cleanup, persisted matrix JSON, and synthetic wiring-only rescue smoke at 27.399s. This proves the standard installed path for this checkpoint; it does not prove natural rescue quality because `natural_rescue_quality_proven` remains false. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bugs: `CB-208`, `CB-209`)
- 2026-05-09: Release manifests now derive `migration_required` from the registered migration registry, and hosted bootstrap validation accepts migration-marked releases so v0.1.15 can route installed `0.1.10` through `0.1.14` repos into the registered Atlas box-explanation migration. (Plan: [B-127](odylith/radar/radar.html?view=plan&workstream=B-127))
- 2026-06-28: Closed the release-proof custody gap where `release-candidate` and `release-preflight` ran local release smoke but did not require the installed greenfield matrix. The shared release proof lane now runs the matrix after smoke and writes `greenfield-post-confirm-matrix.v1.json` into the dist directory. The default standard catalog expanded from eight to thirteen domains and the score contract now requires every case-declared domain anchor, not merely three keyword hits. The c6286f0a package passed the earlier twelve-case matrix in 19.834-22.057s with zero issues and 10/10 scores before this release-gate metadata change; final release proof requires a rebuilt dist from the post-fix commit. Installed CLI auto-rescue remains explicitly wiring-only unless a natural non-internal repairable failure is proven under the 90s rescue tier. `RESCUE_SMOKE=0` is debug-only and not release proof. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bugs: `CB-208`, `CB-209`)
