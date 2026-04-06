# Odylith Repo Integration Contract

Odylith installs into an existing repository as a product, not as copied
source. A consumer repo's `odylith/` tree is that repo's local bootstrap and
truth tree. The Odylith product repo's own `odylith/` tree is the product's
governance tree.

## What Gets Installed

Odylith keeps its boundary separate from the host repo's own toolchain.

| Path | What It Holds |
| --- | --- |
| `odylith/` | consumer-owned bootstrap metadata and local repo truth that remains after `odylith uninstall` |
| `odylith/runtime/source/product-version.v1.json` | tracked repo pin for the intended Odylith version |
| `odylith/runtime/source/tooling_shell.v1.json` | tracked tooling-shell starter metadata |
| `odylith/surfaces/brand/` | starter assets for local Odylith HTML surfaces |
| `odylith/agents-guidelines/` | the Odylith-managed guidance subtree |
| `.odylith/` | launcher, staged runtimes, caches, ledgers, trust evidence, and mutable runtime integration |

`odylith/` is never a copied mirror of the Odylith product repo's own
`odylith/` tree.

## Root Guidance Handoff

- The repo-root `AGENTS.md` stays repository-owned.
- Odylith adds one managed Odylith pointer block after install.
- That block points agents to Odylith first and makes governed workflow the
  default for substantive repo work.
- `odylith/AGENTS.md` carries the consumer bootstrap guidance.
- `odylith on` and `odylith off` toggle the Odylith block without removing the
  installed runtime.

## Ownership

- Repository code and repository source-of-truth artifacts stay owned by the
  host repository.
- Odylith-owned product code, docs, guidance, skills, brand assets, and
  runtime sources live in the Odylith source repo and ship through the
  installed runtime package.
- Consumer starter assets such as `odylith/surfaces/brand/` may be seeded on
  first install and restored by explicit repair, but they are not part of
  normal upgrade mutation.
- The only consumer-side subtree Odylith may refresh during normal upgrade is
  `odylith/agents-guidelines/`.
- Installed Odylith reads local plans, bugs, specs, diagrams, and other repo
  truth in place instead of packaging that context into the product itself.

## What Lives In This Repository

| Path | Purpose |
| --- | --- |
| `src/odylith/` | the Odylith product package |
| `src/odylith/install/` | install, upgrade, doctor, AGENTS injection, runtime switching, and release fetch logic |
| `src/odylith/contracts/` | stable public execution contracts |
| `src/odylith/bundle/` | the installed bundle that materializes under `odylith/` |
| `src/odylith/runtime/` | context engine, memory, orchestration, governance, evaluation, and surface code |
| `tests/` | unit, integration, and end-to-end coverage grouped by concern |
| `docs/` | Odylith product docs and runbooks |

The public repo is one product package, not separate peer packages for the
CLI and the installed bundle.

## Versioning And Activation

- Every installed version lives under `.odylith/runtime/versions/<version>`.
- `.odylith/runtime/current` is the active-version switch and is updated
  atomically.
- `odylith/runtime/source/product-version.v1.json` is the tracked repo pin for
  the intended version.
- `odylith upgrade` realizes the pinned version locally and must not rewrite
  tracked repo truth during normal upgrades.
- `odylith upgrade --source-repo /path/to/odylith` is a development-only
  detached override. It activates `source-local`, does not rewrite the repo
  pin, and cannot be combined with `--to` or `--write-pin`.
- `odylith upgrade` may refresh `odylith/agents-guidelines/`, but should not
  create or repair other starter-tree files in an existing repo.
- `odylith doctor --repair` may restore missing starter-tree assets.
- `odylith rollback --previous` switches back to a previously verified local
  version without rewriting repo files.

## Product Repo Self-Hosting

- The public Odylith repo is a `product_repo` and should dogfood the pinned
  release lane by default.
- In that posture, maintainers and coding agents should start with
  `./.odylith/bin/odylith` status, context, validation, and benchmark surfaces
  before falling back to ad-hoc repo search.
- The product repo never permits tracked edits directly on `main`.
- `odylith upgrade --source-repo /path/to/odylith` is valid for explicit
  detached development, but that posture is release-ineligible until the
  active runtime returns to the tracked pin.
- `odylith validate self-host-posture --mode local-runtime` validates the live
  checkout against the active runtime pointer.
- `odylith validate self-host-posture --mode release --expected-tag vX.Y.Z`
  validates source-only release invariants for CI and release gating.
