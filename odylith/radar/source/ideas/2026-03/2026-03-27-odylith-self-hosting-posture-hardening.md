status: finished

idea_id: B-004

title: Self-Hosting Posture Hardening

date: 2026-03-27

priority: P0

commercial_value: 5

product_impact: 5

market_value: 4

impacted_parts: install/runtime posture modeling, product-repo dogfood validation, release gating, shell and Compass self-host readouts, and self-host evidence visibility

sizing: M

complexity: High

ordering_score: 100

ordering_rationale: Odylith cannot credibly ship install and rollback contracts while the product repo hides detached `source-local` posture or cuts releases without a source-level gate. Self-host posture has to be explicit, validated, and visible before broader GA program work.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-27-odylith-self-hosting-posture-hardening.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on: B-001

workstream_blocks:

related_diagram_ids: D-021

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Odylith now has real install, upgrade, rollback, and release verification
mechanics, but the public product repo can still run in detached
`source-local` mode without making that posture obvious in all operator
surfaces. That weakens dogfooding credibility, obscures release risk, and
makes it too easy to reason from stale install state instead of the live
runtime pointer.

## Customer
- Primary: Odylith maintainers cutting releases from the public product repo.
- Secondary: downstream maintainers who need confidence that Odylith itself is
  operated under the same lifecycle contract it ships.

## Opportunity
By hardening self-host posture into one explicit contract, Odylith can make the
product repo behave like a disciplined consumer of its own release process
without blocking normal source development. Maintainers get loud posture
visibility, Compass gains first-class self-host risk framing, and release
cutting gets a narrow fail-closed gate.

## Proposed Solution
Keep the existing install/versioning model, but derive one authoritative
self-host posture from the live runtime pointer, repo pin, and source contract.
Use that posture everywhere: CLI, shell payloads, Compass runtime, Atlas,
Registry specs, and release validation.

### Wave 1: Shared posture model and operator visibility
- derive `repo_role`, `posture`, `runtime_source`, and `release_eligible` from
  the live runtime pointer first, then install state, then source contract
- extend `odylith version` and `odylith doctor` to report those fields directly
- keep `source-local` legal only as an explicit detached development override,
  not as a normal pinned lane

### Wave 2: Release gate
- add `odylith validate self-host-posture --mode local-runtime|release`
- make `local-runtime` fail unless the product repo is on pinned dogfood
  posture
- make `release` source-only and CI-safe: validate repo role, source version,
  repo pin, migration flag, and expected tag alignment
- gate `.github/workflows/release.yml` on the release-mode validator before
  asset build/upload

### Wave 3: Surface readouts and self-host evidence
- add a `self_host` block into the tooling shell payload and Compass runtime
  payload
- surface detached or diverged self-host posture as an explicit Compass risk
- record posture transitions and failed self-host release preflight checks in
  Compass timeline evidence so drift is visible in history

### Wave 4: Product-governance synchronization
- bind the change to a dedicated Atlas diagram instead of overloading earlier
  product-boundary views
- update Registry dossiers for Odylith, Dashboard, and Compass so the written
  contract matches the implementation
- keep the workstream separate from broader GA program policy and public
  maintainer-process work

## Scope
- product-repo self-host posture derivation
- CLI status and validator surfaces
- release workflow gating
- shell and Compass self-host readouts
- Compass posture risk and timeline evidence
- Atlas and Registry documentation for this contract

## Non-Goals
- inventing a new tracked self-host metadata file
- blocking ordinary source development when a maintainer intentionally uses a
  detached worktree
- redesigning the entire OSS release program or GA policy

## Risks
- product maintainers can still ignore local preflight and dispatch a release
  workflow from a detached workstation unless source-level release gates stay
  strict
- self-host visibility can drift if CLI, shell, and Compass compute posture
  independently
- product-repo-only rules can accidentally leak into consumer repos if repo
  role detection is too loose

## Dependencies
- `B-001` established the public product repo boundary and local governance
  roots this work now hardens
- existing install/versioning, release verification, and Compass runtime paths
  are reused instead of replaced

## Success Metrics
- `odylith version` and `odylith doctor` show `Repo role`, `Posture`,
  `Runtime source`, and `Release eligible`
- `odylith validate self-host-posture --mode local-runtime|release` is the
  supported gate for self-host posture validation
- release workflow runs the release-mode gate before building and uploading
  assets
- Compass runtime payload includes `self_host` and raises a product-runtime
  risk when the public repo is detached or diverged
- Atlas and Registry describe the same contract that the code enforces

## Validation
- `pytest -q tests/unit/runtime/test_validate_self_host_posture.py tests/unit/test_cli.py tests/integration/install/test_manager.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_compass_dashboard_runtime.py`
- `pytest -q`
- `odylith validate self-host-posture --repo-root . --mode release --expected-tag v0.1.0`
- `odylith sync --repo-root . --force`

## Rollout
Land posture derivation and release gating first, then refresh product-governed
surfaces so Compass and the shell immediately expose the new contract.

## Why Now
Odylith is about to depend on versioning, upgrade, rollback, and public release
discipline. The product repo itself has to consume those rules visibly, or the
downstream contract will stay untrustworthy.

## Product View
The default posture should be boring and safe: the main product repo runs the
pinned release lane, source-local stays explicit and loud, and releases fail
closed when the source contract does not line up.

## Impacted Components
- `odylith`
- `dashboard`
- `compass`

## Interface Changes
- `odylith validate self-host-posture --mode local-runtime|release`
- `odylith version` now reports repo role, posture, runtime source, and
  release eligibility
- `odylith doctor` now reports the same self-host posture fields alongside the
  health message
- tooling shell and Compass runtime payloads now expose `self_host`

## Migration/Compatibility
- consumer repos keep their current install/runtime behavior and only gain
  extra non-breaking readout fields
- the public product repo can remain temporarily detached during development,
  but the posture is now explicit and release-ineligible until it returns to a
  pinned lane

## Test Strategy
- validate the source-only release gate independently of local runtime state
- validate the live runtime posture against the active symlink rather than
  stale install state
- validate shell and Compass payload exposure of self-host posture
- rerun full sync so generated Compass and shell artifacts match the contract

## Open Questions
- should a future follow-on add an explicit maintainer command to restage the
  product repo onto the newest locally verified pinned release after a source
  development cycle
- should the shell later render a dedicated self-host badge in addition to the
  new payload fields and Compass risk surface
