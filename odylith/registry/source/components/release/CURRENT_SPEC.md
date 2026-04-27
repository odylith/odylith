# Release
Last updated: 2026-04-17


Last updated (UTC): 2026-04-09

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
  unreleased workspace changes. This is maintainer-only and release-ineligible.
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
  lane, not only the hosted installer shell. If pinned dogfood, consumer
  rehearsal, or GA gate still prints allowlisted trust-warning noise such as
  `unsupported key type: 7` before healthy `OK:` asset lines, the warning
  suppression slice is incomplete and stays open for the next release. Wrapped
  verifier stderr continuations must be folded before benign-warning matching
  so `Failed to load a trusted root key: unsupported ...` followed by
  `key type: 7` stays quiet on successful verification instead of scaring
  operators.
- Release assets are authoritative only when the signed manifest, provenance,
  and SBOM all verify for the canonical signer identity.
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
- Session cleanup is explicit so retry evidence is not silently discarded.
- Managed runtime bundles must preserve runtime isolation so a consumer repo's
  active `VIRTUAL_ENV`, Conda env, `PYTHONHOME`, `PYTHONPATH`,
  `PYTHONEXECUTABLE`, `PYENV_VERSION`, `UV_*`, Poetry/Pipenv/PDM selectors,
  or user-site configuration does not bleed into Odylith.
- The release manifest must expose exactly one Odylith wheel plus the expected
  base-runtime and feature-pack assets; preflight must fail closed on sidecar
  wheels, missing wheel metadata, or missing feature-pack asset metadata.
- Local release smoke should prove the installer from a nested repo directory
  as well as the repo root so the zero-friction repo-root detection contract
  does not silently regress.

## Validation Playbook
### Release
- `make release-version-preview`
- `make release-version-show`
- `make license-audit`
- `make release-preflight [VERSION=X.Y.Z]`
- `make release-session-show`
- `odylith validate self-host-posture --repo-root . --mode release --expected-tag vX.Y.Z`
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_release_version_session.py tests/unit/install/test_release_assets.py tests/unit/install/test_release_bootstrap.py tests/unit/runtime/test_validate_self_host_posture.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-04-17 · Implementation:** Implemented and hardened B-126 conditional release-targeted backlog authoring with --release selector preflight, batch release events, queued-status preservation, Radar/Compass refresh reporting, and focused QA coverage.
  - Scope: B-126
  - Evidence: odylith/technical-plans/in-progress/2026-04/2026-04-18-conditional-release-targeted-backlog-authoring.md, src/odylith/runtime/governance/backlog_authoring.py +3 more
- **2026-04-17 · Decision:** Queued B-126 Conditional Release-Targeted Backlog Authoring for v0.1.12 next release targeting; status remains queued and implementation is intentionally deferred out of the v0.1.11 lane.
  - Scope: B-126
  - Evidence: odylith/radar/source/ideas/2026-04/2026-04-18-conditional-release-targeted-backlog-authoring.md, odylith/radar/source/releases/release-assignment-events.v1.jsonl
<!-- registry-requirements:end -->

## Feature History
- 2026-03-27: Added a first-class maintainer release subsystem with sticky version sessions, stable semver auto-tagging, canonical commit-bound release dispatch, and a dedicated release runbook. (Plan: [B-005](odylith/radar/radar.html?view=plan&workstream=B-005))
- 2026-03-28: Reset the local relaunch narrative to restart preview at `v0.1.0`, made split managed assets part of the canonical release lane while keeping install full-stack by default, and blocked dispatch on local hosted-asset installer proof. (Plan: [B-005](odylith/radar/radar.html?view=plan&workstream=B-005))
- 2026-03-28: Promoted `v0.1.0` from a proved preview relaunch to the GA baseline for the supported macOS Apple Silicon and Linux platform matrix, and carried the release-reset pin-realignment hardening into the GA branch. (Plan: [B-007](odylith/radar/radar.html?view=plan&workstream=B-007))
- 2026-04-08: Added repo-local release planning with immutable `release_id`, explicit `current` and `next` aliases, append-only workstream targeting history, and authored release-note name alignment for versioned release records. (Plan: [B-063](odylith/radar/radar.html?view=plan&workstream=B-063))
- 2026-04-08: Clarified that current-release visibility is manual-close driven: governed read models keep the active current release visible until maintainers explicitly mark it `shipped` or `closed`, even when no targeted workstreams remain. (Plan: [B-065](odylith/radar/radar.html?view=plan&workstream=B-065))
- 2026-04-08: Clarified that active current releases may keep finished completed members visible from release history until explicit ship or closeout, without restoring those workstreams to active targeting. (Plan: [B-066](odylith/radar/radar.html?view=plan&workstream=B-066))
- 2026-04-09: Hardened `odylith release add` so maintainers can attach an already finished workstream to the active release as completed release history instead of reviving it as an active target. (Plan: [B-066](odylith/radar/radar.html?view=plan&workstream=B-066)) (Bug: [CB-082](odylith/casebook/casebook.html?bug=CB-082))
- 2026-04-09: Codified release-target progress semantics so release-member badges use shared execution-progress truth, show tracked partial completion honestly, and never render active implementation with unchecked execution as fake `0% progress`. (Plan: [B-068](odylith/radar/radar.html?view=plan&workstream=B-068)) (Bug: [CB-087](odylith/casebook/casebook.html?bug=CB-087))
