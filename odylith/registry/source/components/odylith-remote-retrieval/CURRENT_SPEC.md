# Odylith Remote Retrieval
Last updated: 2026-04-07


Last updated (UTC): 2026-04-07

## Purpose
Odylith Remote Retrieval is the optional Vespa-backed retrieval and sync
contract that can augment or replace local lookup when explicitly configured.

## Scope And Non-Goals
### Odylith Remote Retrieval owns
- environment-driven Vespa configuration parsing
- readiness, disabled, and misconfigured posture reporting
- remote query execution for allowed document kinds
- sync manifests and state under `.odylith/runtime/`
- document dedupe, embedding derivation, and network cleanup for the remote
  sync path

### Odylith Remote Retrieval does not own
- the default local-memory proof posture
- the compiler bundle or snapshot contracts
- the local LanceDB and Tantivy backend
- authority over tracked repo truth

## Developer Mental Model
- `src/odylith/runtime/memory/odylith_remote_retrieval.py` is an opt-in lane.
  It should feel obviously separate from the default local memory path.
- Remote retrieval stays dormant unless a base URL exists and the mode is
  explicitly `augment` or `remote_only`.
- Misconfiguration is a first-class state. This component should tell the
  operator what is missing instead of quietly half-enabling a networked path.
- Even when enabled, remote retrieval is downstream of compiled local truth.
  It is an augmentation or alternate query lane, not the author of repo truth.

## Runtime Contract
### Environment inputs
- `ODYLITH_VESPA_URL`
- `ODYLITH_VESPA_SCHEMA`
- `ODYLITH_VESPA_NAMESPACE`
- `ODYLITH_VESPA_MODE`
- `ODYLITH_VESPA_RANK_PROFILE`
- `ODYLITH_VESPA_TIMEOUT_SECONDS`
- `ODYLITH_VESPA_TOKEN`
- `ODYLITH_VESPA_CLIENT_CERT`
- `ODYLITH_VESPA_CLIENT_KEY`
- `ODYLITH_VESPA_PRUNE_MISSING`

### Persistent runtime files
- `.odylith/runtime/odylith-vespa-sync.v1.json`
- `.odylith/runtime/odylith-vespa-sync-manifest.v1.json`

### Modes
- `disabled`
  Explicitly off.
- `augment`
  Local retrieval remains primary and Vespa can augment recall.
- `remote_only`
  Vespa is allowed to stand in for local retrieval when explicitly requested.

### State contract
`remote_config(...)` must expose:
- `enabled`
- `configured`
- `status`
- `mode`
- `issues`
- `blocking_issues`
- `action`
- auth posture
- timeout posture
- current persisted state payload

`sync_remote(...)` must return an explicit status payload even when no network
request is made, for example `disabled`, `misconfigured`, `partial_error`, or
`synced`.

## Safety And Failure Posture
- Active remote modes without `ODYLITH_VESPA_URL` must fail into
  `misconfigured`, not into speculative network behavior.
- Invalid timeout input must recover to the default timeout instead of
  disabling a ready remote lane.
- Incomplete client-certificate configuration must be surfaced explicitly.
- HTTP clients must close even after partial failure so the remote lane cannot
  leak resources while trying to be helpful.
- Benchmark and default product proof remain local-memory-first unless the run
  explicitly declares otherwise.

## Composition
- [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md)
  decides whether remote retrieval participates in a given read path.
- [Odylith Memory Backend](../odylith-memory-backend/CURRENT_SPEC.md)
  remains the default local substrate.
- [Odylith Projection Bundle](../odylith-projection-bundle/CURRENT_SPEC.md)
  provides the document payloads that remote sync dedupes and uploads.

## Validation Playbook
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_remote_retrieval.py`
- `odylith context-engine --repo-root . memory-snapshot`
- `odylith context-engine --repo-root . odylith-remote-sync --help`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-04-05: Kept the published benchmark posture local-memory-first and explicitly left Vespa in the opt-in experiment lane until it can show no-regression gains. (Plan: [B-021](odylith/radar/radar.html?view=plan&workstream=B-021))
- 2026-04-07: Promoted the optional Vespa sync and retrieval contract into a first-class Registry component so networked memory behavior is explicit, governed, and visibly distinct from the local backend. (Plan: [B-058](odylith/radar/radar.html?view=plan&workstream=B-058))
