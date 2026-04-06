# Contributing To Odylith

Last updated: 2026-03-27

Canonical repo authorship and contributor attribution are recorded under
`freedom-research`.

## Before You Start

- Read [README.md](README.md), [SECURITY.md](SECURITY.md), and
  [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- Read the repo guidance in [AGENTS.md](AGENTS.md) before changing product,
  governance, or bundle files.
- Open or reference a GitHub issue for non-trivial changes so the problem and
  intended contract are visible before a large patch lands.

## Ground Rules

- Odylith is a product repo, not a consumer repo.
- The sole canonical contributor identity for this repo is
  `freedom-research`.
- Do not add personal-name authors, alternate handles, or additional
  contributor identities to tracked metadata, notices, docs, or generated
  surfaces unless preserving immutable third-party or historical material.
- Do not copy consumer-repo truth into this repository.
- Keep public docs generic. Do not add consumer-branded paths, screenshots, or
  prose.
- Use the `odylith` CLI in public docs and operator guidance, not internal
  module entrypoints.
- Keep bundle assets and product docs aligned when the public contract changes.

## Development Setup

Odylith currently targets Python 3.13.

```bash
python3.13 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -e .
./.venv/bin/pip install build pytest
```

## Expected Validation

Run the narrowest useful validation for your change. For lifecycle, packaging,
surface, or governance changes, the normal baseline is:

```bash
python -m pytest -q
odylith sync --repo-root . --force
odylith validate component-registry --repo-root .
```

If your change touches install, upgrade, rollback, or release packaging, also
run the relevant lifecycle simulator or install tests under
`tests/integration/install/`.

Maintainers can use the thin repo-local interface instead of remembering the
full command bundle:

```bash
make validate
make release-version-preview
make release-version-show
make release-preflight VERSION=0.1.0
```

## Generated And Governed Outputs

If you change source truth or renderers for any governed surface, regenerate the
derived outputs before opening a PR. This includes changes that touch:

- `odylith/radar/source/`
- `odylith/atlas/source/`
- `odylith/registry/source/`
- `odylith/casebook/bugs/`
- Compass, Dashboard, or Registry renderers under `src/odylith/runtime/surfaces/`

The standard regeneration path is:

```bash
odylith sync --repo-root . --force
```

## Pull Requests

A good PR for Odylith should:

- explain the user-facing contract change, if any
- call out install, upgrade, rollback, or governance-surface impact
- include test or command evidence
- keep bundle assets, docs, and generated outputs aligned with source changes
- avoid unrelated churn

## Maintainer Release Lane

The repo root `Makefile` is a thin maintainer interface over `bin/` scripts.
It is not a second product contract; the product contract remains the `odylith`
CLI and the GitHub release workflow.

- `make validate`
- `make release-version-preview`
- `make release-version-show`
- `make release-session-show`
- `make release-preflight [VERSION=X.Y.Z]`
- `make release-dispatch`
- `make dogfood-activate`
- `make consumer-rehearsal [VERSION=X.Y.Z] [PREVIOUS_VERSION=Y.Y.Y]`
- `make ga-gate [VERSION=X.Y.Z] [PREVIOUS_VERSION=Y.Y.Y]`
- `make release-session-clear`

Canonical Odylith releases are intentionally restricted. Publishing release
assets is only allowed from `freedom-research/odylith` on `main` as GitHub
actor `freedom-research`. Clones and forks fail closed for the canonical
release lane.

Use [odylith/MAINTAINER_RELEASE_RUNBOOK.md](odylith/MAINTAINER_RELEASE_RUNBOOK.md)
for the exact target order.

## Security

If you think you found a vulnerability, do not open a public issue. Follow
[SECURITY.md](SECURITY.md).
