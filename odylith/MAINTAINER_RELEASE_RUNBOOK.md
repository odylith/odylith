# Odylith Maintainer Release Runbook

Last updated: 2026-04-03

## Purpose
Use this runbook for the canonical Odylith release lane only.

Use the generic
[GTM and Release Checklist](/Users/freedom/code/odylith/odylith/maintainer/GTM_AND_RELEASE_CHECKLIST.md)
as the reusable launch-readiness overlay for narrative, proof, asset, and
announcement review. The runbook remains the canonical command order.

The release lane is authoritative only when all of these are true:
- repo: `odylith/odylith`
- GitHub actor: `freedom-research`
- release commit: matches `origin/main`
- local proof checkout: clean

The active maintainer workspace does not need to be the clean proof checkout.
When the current workspace is off-main or dirty but its `HEAD` still matches
`origin/main`, the local release wrappers may materialize an isolated clean
checkout of that exact canonical commit for preflight, dispatch, and GA proof.
That isolated checkout is a local maintainer proof aid only; the actual GitHub
release workflow still publishes from `refs/heads/main`.

## Retrieval Posture
- During release, benchmark, and dogfood verification, use Odylith CLI and
  maintained Odylith surfaces first to inspect runtime state, self-host
  posture, benchmark proof, and routing context.
- Keep maintainer mode explicit:
  - pinned dogfood is the release-proof posture
  - detached `source-local` is the dev posture for current unreleased
    `src/odylith/*` execution
- Use `make dev-validate` for detached `source-local` validation of current
  unreleased workspace changes. That dev lane is maintainer-only, release
  ineligible, and separate from canonical release proof.
- Source-tree-only maintainer helpers that do not have a supported Odylith CLI
  surface yet may still use the product repo toolchain with `PYTHONPATH=src ...`.
  That is a maintainer dev detail, not a consumer contract, and it does not
  change the rule that shipped-runtime proof must return to pinned dogfood.
- For substantive release-adjacent changes, recover the existing workstream,
  bound plan, related bugs, related components, related diagrams, and recent
  Compass/session context first; extend or reopen that truth before creating
  new records.
- If the release-adjacent slice is genuinely new, create the missing
  workstream and bound plan before non-trivial implementation; if the work
  spans multiple release tracks, split it with child workstreams or execution
  waves.
- Keep Casebook, Registry, Atlas, and Compass current in-band whenever release
  or benchmark work exposes a named failure mode, boundary change, or stale
  public benchmark story.
- Widen to direct `rg`, source reads, generator inspection, or targeted tests
  only when Odylith reports ambiguity, fallback, or repair conditions, or when
  you are verifying tracked source truth behind a runtime-generated claim.
- This matches the benchmark contract: recall, accuracy, precision, and
  validation are the hard floor before latency or token wins count as product
  progress.

## Release Order
Run the targets in this order.

1. `make release-version-preview`
   See the next auto patch version without mutating anything.

2. `make release-version-show`
   Inspect the active session, the highest existing `vX.Y.Z` tag, and the next
   auto version before you start the lane.

3. Refresh the public Codex benchmark snapshot.
   Run `./.odylith/bin/odylith benchmark --repo-root . --profile proof`, regenerate
   `docs/benchmarks/*.svg` from
   `.odylith/runtime/odylith-benchmarks/latest.v1.json`, and update the
   repo-root `README.md` benchmark section from that same report before the
   release lane continues. The default `quick` lane is not release proof. This
   must stay on the warm-plus-cold `proof` Codex lane for the live
   `odylith_on` versus `odylith_off` pair, and the README must publish the
   conservative benchmark view from that report rather than a warm-only or
   primary-profile-only snapshot. If maintainers need isolated packet or
   prompt tuning, use `--profile diagnostic` separately and keep it out of the
   public benchmark claim. Label published latency as paired benchmark
   task-cycle time and published token cost as full-session spend, not as
   solo-user latency or initial prompt size.
   A version-scoped maintainer override may waive this step only when it is
   recorded in `odylith/runtime/source/release-maintainer-overrides.v1.json`;
   that path is exceptional, must name the exact release version, and must
   carry the reason in tracked repo truth instead of living only in shell
   history.

4. `make release-preflight [VERSION=X.Y.Z]`
   Initialize or reuse the sticky release session, reserve the release tag,
   validate the canonical release contract, build the wheel plus split managed
   runtime assets, and prove the generated installer locally before dispatch.
   If your active maintainer workspace is dirty or off-main but already points
   at `origin/main`, this target may run from an isolated clean checkout of the
   same commit instead of forcing you to discard the active workspace. That
   clean-checkout proof intentionally excludes unreleased workspace changes;
   use `make dev-validate` first when you want to validate detached
   `source-local` changes before they land on the canonical release commit.
   The canonical wheel build frontend is Hatch.

5. `make release-session-show`
   Confirm the sticky session fields, especially `version`, `tag`, and
   `head_sha`, before dispatch.

6. `make release-dispatch`
   Reuse the existing session and dispatch the canonical GitHub release
   workflow with the reserved `tag` and `expected_sha`.

7. Wait for the GitHub release workflow to finish successfully.

8. `make dogfood-activate`
   Return the Odylith product repo from detached `source-local` to the pinned
   installed runtime for the published version, then run
   `./.odylith/bin/odylith validate self-host-posture --repo-root . --mode local-runtime`
   to prove the live dogfood checkout is back on the tracked runtime.

9. `make consumer-rehearsal [PREVIOUS_VERSION=X.Y.Z]`
   Prove first install, upgrade, rollback, doctor, and Compass retention
   behavior against real hosted release assets in a disposable consumer repo.
   This rehearsal must prove the supported-platform runtime contract:
   macOS (Apple Silicon) plus Linux only, Intel macOS and Windows unsupported,
   no dependence on the consumer machine's Python installation or active
   Python environment, and a full-stack Odylith runtime outcome assembled from
   split managed assets.

10. `make ga-gate [PREVIOUS_VERSION=X.Y.Z]`
   Re-run the post-publish dog-food and consumer proof lane for the candidate
   version.

11. `make release-session-clear`
    Clear the local sticky session after the lane is complete or intentionally
    abandoned.

## Target Reference
- `make validate`
  Baseline maintainer validation suite. This includes `make license-audit`.
- `make dev-validate`
  Detached `source-local` maintainer validation lane for current unreleased
  workspace changes. This is not release proof and does not make the repo
  release-eligible.
- `make license-audit`
  Refresh and audit `THIRD_PARTY_ATTRIBUTION.md` against the current runtime
  dependency closure and bundled managed-runtime suppliers.
- `make release-version-preview`
  Print the next auto patch version only.
- `make release-version-show`
  Show session, highest tag, next tag, and effective version state.
- `make release-session-show`
  Show the raw sticky release-session payload under `.odylith/locks/`.
- `make release-preflight [VERSION=X.Y.Z]`
  Session initializer and canonical preflight gate.
- `make release-dispatch`
  Canonical GitHub release workflow dispatch using the active session only.
- `make dogfood-activate`
  Switch the product repo back onto the pinned installed runtime.
- `./.odylith/bin/odylith validate self-host-posture --repo-root . --mode local-runtime`
  Prove the live product-repo checkout is back on the tracked installed
  runtime after dogfood activation.
- `./.odylith/bin/odylith validate self-host-posture --repo-root . --mode release --expected-tag vX.Y.Z`
  Prove source-only release invariants for CI or release workflow gating.
- `make consumer-rehearsal [VERSION=X.Y.Z] [PREVIOUS_VERSION=Y.Y.Y]`
  Disposable downstream proof against hosted assets. `VERSION` defaults to the
  active release session.
- `make ga-gate [VERSION=X.Y.Z] [PREVIOUS_VERSION=Y.Y.Y]`
  Combined dog-food plus consumer proof gate. `VERSION` defaults to the active
  release session.
- `make release-session-clear`
  Clear the sticky release session intentionally.
- `./.odylith/bin/odylith benchmark --repo-root . --profile proof`
  Refresh the canonical Codex benchmark report before release. The default
  quick lane is developer signal only; the release-safe lane is the
  multi-profile `proof` run covering both `warm` and `cold` for the live
  `odylith_on` versus `odylith_off` pair.
- `make benchmark-analysis [OUT=/tmp/odylith-benchmark-...]`
  Maintainer helper that runs `diagnostic` then `proof`, copies the resulting
  JSON artifacts into a timestamped local bundle, regenerates both profile SVG
  graph sets into that bundle, and writes a markdown summary for deeper
  follow-on analysis. This is a local analysis aid, not a replacement for the
  explicit release-proof step above.
- `PYTHONPATH=src python -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir docs/benchmarks`
  Regenerate the canonical README SVGs from the current benchmark report.
  This is a source-tree maintainer helper, not a consumer-facing Odylith CLI
  contract.

## Important Notes
- `make release-preflight` is the only session initializer.
- Local release wrappers may materialize an isolated clean checkout of the
  `origin/main` commit when the active maintainer workspace is dirty or
  off-main, but only if that workspace `HEAD` already matches `origin/main`.
- `make release-preflight` must fail closed unless it can build the wheel, base
  runtime bundles, context-engine pack assets, signed release manifest inputs,
  and a local hosted-style installer proof for
  `install -> version -> doctor -> sync`.
- The canonical wheel build path is `hatch build`; do not switch the
  maintainer lane back to ad hoc `python -m build` or direct `pip` wheel
  publication flows.
- `make release-dispatch` fails closed if there is no active session.
- The session is bound to one commit. If `HEAD` changes, clear the session and
  start the lane again.
- If `VERSION` is unset, preflight auto-tags the next stable patch version from
  the highest published canonical release, but never below the current product
  source version in `pyproject.toml`.
- If `VERSION` is set explicitly, it must be stable semver and cannot be lower
  than the highest published canonical release.
- If the chosen tag already exists without a published GitHub release,
  preflight must reuse that same tag instead of burning the next patch version.
  If the tag is still unpublished and points at an older retry commit,
  preflight may rebind that unpublished tag to the current release commit
  before dispatch.
- The GitHub workflow will refuse to publish unless the requested `tag`, the
  session `expected_sha`, and `GITHUB_SHA` all match.
- Public install and upgrade must preserve strict interpreter isolation:
  `./.odylith/bin/odylith` runs Odylith inside `.odylith/`, while the consumer
  repo's own toolchain remains untouched.
- Public install and normal upgrade remain full-stack by default even though
  transport is split into a base runtime plus a managed context-engine pack.
- Incremental upgrades should stay light by reusing an unchanged
  context-engine pack when the verified asset digest still matches, then
  pruning staged runtimes and cached release payloads down to the active
  version plus one rollback target.
- The canonical maintainer lane must also keep `THIRD_PARTY_ATTRIBUTION.md`
  current and fail closed on unknown, commercial/proprietary, or otherwise
  disallowed licenses in the runtime closure or bundled managed-runtime
  suppliers.
- The canonical maintainer lane must also keep the repo-root `README.md`
  benchmark snapshot and `docs/benchmarks/*.svg` current from the latest
  Codex benchmark report before release.
- The README benchmark snapshot must publish the conservative Codex view from
  `latest.v1.json`; do not publish `primary_comparison` or a warm-only report
  when the conservative published view is weaker.
- Preserve the current benchmark graph contract across releases: the same four
  SVGs, the same filenames, and the same Codex-oriented style and tone from
  `src/odylith/runtime/evaluation/odylith_benchmark_graphs.py`, including
  red Odylith-off baseline marks and teal Odylith-on marks.
- Preserve the repo-root `README.md` benchmark graph order exactly:
  `odylith-benchmark-family-heatmap.svg`, then
  `odylith-benchmark-quality-frontier.svg`, then
  `odylith-benchmark-frontier.svg`, then
  `odylith-benchmark-operating-posture.svg`.
- The current local source reset treats the abandoned `0.1.x` drill tags as
  prelaunch rehearsal only. `v0.1.0` is the clean GA baseline for the
  canonical line; future releases should increment from that published state.
