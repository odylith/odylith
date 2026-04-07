# Odylith Install And Upgrade

## Do Not Clone Odylith For Install

Most people should never clone this repository.

Cloning this repository is for people developing Odylith itself. The supported
install path for a consumer repo is the hosted installer:

```bash
curl -fsSL https://odylith.ai/install.sh | bash
```

## Happy Path

- Run the hosted installer from the repo you want to augment, ideally from the
  repo root.
- Supported public install platforms today are macOS (Apple Silicon) and
  Linux (`x86_64`, `ARM64`). Intel macOS and Windows are out of scope for the
  current public contract.
- First install does not depend on preinstalled machine Python on supported
  platforms. Odylith stages its own verified managed runtime under
  `.odylith/runtime/versions/<version>` and creates `./.odylith/bin/odylith`.
- The installer verifies the signed release manifest, managed runtime bundle,
  managed context-engine pack, provenance, and SBOM before activation.
- The installer also creates a minimal consumer-owned `odylith/` tree for
  local repo truth and bootstrap metadata. It does not copy the product repo's
  `odylith/` tree into the consumer repository.
- Odylith is meant to be used through an AI coding agent such as Codex or
  Claude Code. The agent is the execution interface. `odylith/index.html` is
  the operating surface.
- On successful local interactive install, Odylith tries to open
  `odylith/index.html` automatically. Use `ODYLITH_NO_BROWSER=1` for the
  hosted bootstrap or `odylith install --no-open` for direct CLI installs if
  you want to suppress that.

First commands to know:

- Default first turn:
  `./.odylith/bin/odylith start --repo-root .`
- Update to the latest verified release:
  `./.odylith/bin/odylith upgrade --repo-root .`
- Restage and align runtime plus repo pin:
  `./.odylith/bin/odylith reinstall --repo-root . --latest`
- Inspect local version and posture:
  `./.odylith/bin/odylith version --repo-root .`
- Repair drift:
  `./.odylith/bin/odylith doctor --repo-root . --repair`

If a consumer repo is still on the legacy `0.1.0` or `0.1.1` launcher, rerun
the hosted installer once from that repo root before using plain
`odylith upgrade`.

Other useful lifecycle commands:

- Refresh shell-facing surfaces:
  `./.odylith/bin/odylith dashboard refresh --repo-root .`
- Roll back to the last verified local version:
  `./.odylith/bin/odylith rollback --repo-root . --previous`
- Turn Odylith guidance off or on without removing the runtime:
  `./.odylith/bin/odylith off --repo-root .`
  `./.odylith/bin/odylith on --repo-root .`
- Detach runtime integration while preserving `odylith/`:
  `./.odylith/bin/odylith uninstall --repo-root .`

## Repo Integration Contract

- `odylith/` in a consumer repo is consumer-owned bootstrap and local repo
  truth. It is not a copied product bundle.
- The bootstrap seeds `odylith/runtime/source/product-version.v1.json`,
  `odylith/runtime/source/tooling_shell.v1.json`, `odylith/agents-guidelines/`,
  and starter brand assets under `odylith/surfaces/brand/`.
- Product runtime code, staged versions, ledgers, trust evidence, and caches
  live under `.odylith/`.
- `./.odylith/bin/odylith` always runs with Odylith's own runtime and does not
  source or mutate the consumer repo's active Python environment.
- Keep three boundaries separate:
  - runtime boundary: `./.odylith/bin/odylith` chooses how Odylith runs
  - write boundary: interpreter choice does not limit which repo files the
    agent may edit
  - validation boundary: consumer repo code must still be proved with the
    consumer repo's own toolchain
- Consumer launchers fail closed if the active runtime pointer leaves
  `.odylith/runtime/versions/`; they do not silently fall back into
  consumer-machine Python.
- The root `AGENTS.md` gets one Odylith pointer block.

## Isolation Guarantees

- Odylith runtime ownership and consumer project runtime ownership are
  separate concerns.
- `./.odylith/bin/odylith` always runs inside Odylith's managed runtime under
  `.odylith/`; the consumer repo's own `python`, `uv`, Poetry, Pipenv, or
  Conda commands stay on the consumer toolchain.
- Normal install and upgrade do not rewrite the consumer repo's own runtime
  manifest files such as `pyproject.toml`, `requirements.txt`, `uv.lock`,
  `poetry.lock`, or Conda environment files.
- Odylith does not require shell activation, global PATH mutation, or a repo
  shell bootstrap step to switch between runtimes.
- If Odylith cannot trust its own runtime pointer or staged runtime evidence,
  it fails closed into repair instead of borrowing the consumer machine's
  Python.

## Secure Runtime Guarantees

- Hosted install and CLI upgrade verify the signed release manifest, managed
  runtime bundle, managed context-engine pack, provenance, and SBOM before
  activation.
- Managed runtime bundles are built from pinned upstream Python archive
  digests, and installer/runtime checks fail closed if those digests or local
  verification markers drift.
- Launchers scrub ambient Python and environment-manager variables before
  starting Odylith so shell state from the consumer repo cannot bleed into the
  Odylith runtime.
- Runtime staging is side-by-side under `.odylith/runtime/versions/` and
  activation is an atomic switch of `.odylith/runtime/current`.

## Upgrade Contract

- In consumer repos, `odylith upgrade` treats the latest verified release as
  the normal control plane and advances
  `odylith/runtime/source/product-version.v1.json` to the version it activates.
- `odylith upgrade` verifies signed assets, stages the managed runtime
  side-by-side, installs or reuses the matching managed context-engine pack,
  health-checks the result, and atomically switches `.odylith/runtime/current`.
- `odylith upgrade` reports whether it moved to a new version, was already
  current, or only advanced the repo pin.
- When the requested release already matches the active verified full-stack
  runtime, `odylith upgrade` treats that as already current and does not
  restage the live same-version runtime in place.
- Normal upgrades must not rewrite tracked repo truth under `odylith/`; the
  only allowed consumer-tree refresh is `odylith/agents-guidelines/`.
- `odylith rollback --previous` only targets previously verified local
  versions and may temporarily diverge from the repo pin.

## Product Repo Self-Host Posture

- The public Odylith repo should normally dogfood the pinned release lane.
- Detached `source-local` is an explicit development override and remains
  release-ineligible until the active runtime returns to the tracked pin.
- Pinned dogfood and detached `source-local` are not interchangeable:
  - pinned dogfood proves the shipped runtime
  - detached `source-local` is the explicit posture for unreleased live
    `src/odylith/*` execution
- `odylith validate self-host-posture --mode release --expected-tag vX.Y.Z`
  validates release invariants before asset publication.

## Recovery

- Preferred repair path:
  `./.odylith/bin/odylith doctor --repo-root . --repair`
- Missing-launcher bootstrap path:
  `./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair`
- Poisoned local state:
  `./.odylith/bin/odylith doctor --repo-root . --repair --reset-local-state`
- If Odylith is not installed yet and there is no repo-local bootstrap
  launcher, rerun the hosted installer from the repo root instead of cloning a
  second Odylith checkout.
- In consumer repos, repair must restage the pinned verified runtime or fail
  closed. It must not recreate Odylith through host-Python wrapper fallback.
- Uninstall preserves consumer-owned `odylith/` truth and only removes the
  Odylith block in the root `AGENTS.md`.
