# Odylith Memory Contracts
Last updated: 2026-04-07


Last updated (UTC): 2026-04-07

## Purpose
Odylith Memory Contracts is the neutral packet and evidence-pack contract layer
that shapes memory-derived runtime payloads into compact, provenance-aware,
secret-safe structures.

## Scope And Non-Goals
### Odylith Memory Contracts owns
- execution-profile token encode/decode helpers
- allowlisted source-class mapping for memory-facing packet fields
- secret and non-allowlisted path suppression
- compact packet and evidence-pack shaping for retained docs, tests, commands,
  guidance, workstreams, diagrams, and components
- summary-only hot-path packet shaping

### Odylith Memory Contracts does not own
- projection compilation
- local or remote retrieval ranking
- benchmark scoring semantics
- the authoritative component registry or other tracked governance truth

## Developer Mental Model
- `src/odylith/runtime/memory/tooling_memory_contracts.py` is the contract
  membrane between rich internal memory state and the smaller packets Odylith
  actually hands to surfaces, orchestrators, or benchmark consumers.
- This component exists to preserve truth while refusing to leak sensitive or
  irrelevant paths.
- The contract is intentionally neutral. It does not decide what is true; it
  decides how already-built truth can be retained, compacted, and shared.
- The summary-only hot path is part of the product contract, not an incidental
  optimization detail.

## Core Contract Areas
### Execution-profile encoding
- `execution_profile_mapping(...)`
- `compact_execution_profile_mapping(...)`
- `encode_execution_profile_token(...)`

These helpers normalize execution-profile fields so runtime components can pass
compact tokens without losing the shared field order.

### Source-class and path policy
The contract layer classifies retained paths into allowlisted source classes
such as:
- backlog markdown
- plan markdown
- bug markdown
- component registry
- component specs
- runtime contracts
- mermaid catalog
- delivery-intelligence artifacts
- engineering guidance
- Python source
- pytest source

Sensitive or non-allowlisted paths are dropped or redacted instead of quietly
passing into packets.

### Packet compaction
`build_context_packet(...)` and `build_evidence_pack(...)` compact:
- retained components
- retained diagrams
- retained workstreams
- retained docs
- retained tests
- retained commands
- retained guidance
- packet budget and optimization posture
- execution signals
- routing handoff summaries

The contract should keep user-facing and benchmark-facing packets dense without
destroying provenance.

## Trust And Safety Posture
- Repo truth remains read-only. This layer is about representation, not
  mutation.
- Sensitive tokens, secrets, DSNs, private-key material, and non-allowlisted
  paths must be excluded from portable packets.
- Summary-only compaction is allowed to omit detail, but it must not invent
  clean certainty where the source payload was ambiguous.
- Silence is better than garbage here too: missing nested fields should degrade
  to compact empty structures instead of malformed packet shapes.

## Composition
- [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md)
  feeds this layer with compiler and retrieval outputs.
- [Odylith Projection Bundle](../odylith-projection-bundle/CURRENT_SPEC.md),
  [Odylith Projection Snapshot](../odylith-projection-snapshot/CURRENT_SPEC.md),
  [Odylith Memory Backend](../odylith-memory-backend/CURRENT_SPEC.md), and
  [Odylith Remote Retrieval](../odylith-remote-retrieval/CURRENT_SPEC.md) all
  rely on this layer indirectly when their outputs are compacted into packets
  or evidence packs.

## Validation Playbook
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_tooling_memory_contracts.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py -k 'remote_retrieval or compact_report_summary or odylith_adoption'`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-04-07: Promoted the packet-safe memory contract layer into a first-class Registry component so allowlisting, redaction, execution-profile encoding, and compact evidence shaping stop hiding inside one helper module. (Plan: [B-058](odylith/radar/radar.html?view=plan&workstream=B-058))
