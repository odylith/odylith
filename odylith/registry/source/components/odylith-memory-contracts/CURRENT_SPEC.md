# Odylith Memory Contracts

## Adaptive Agent Operating Character Contract
- Memory Contracts own the Learning facet. Character learning events use
  `odylith_agent_operating_character_learning.v1` and retain compact practice
  signals only: pressure features, stance vector, hard-law result, decision,
  recovery action, proof obligation/status, benchmark/case ids, related
  Casebook ids, source refs, fingerprint, and retention class.
- Durable learning is gated by validation, benchmark evidence, or Tribunal and
  governance promotion. Raw transcripts, secrets, broad context, and full
  corpus payloads do not enter durable memory.
- Practice events also carry `durable_update_allowed`, `promotion_gate`, and
  evidence-shaped intervention visibility so recurrence can become a Tribunal
  candidate without silently converting session noise into durable doctrine.
- Practice-event source refs must suppress transcript/secret markers and
  ephemeral local execution paths such as `/tmp`, `/var/folders`,
  `/private/var`, and `/dev/fd`. Temporary intent files and shell descriptors
  are not durable learning anchors.
Last updated: 2026-04-18


Last updated (UTC): 2026-04-18

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
- compact Guidance Behavior summary retention for context packets and evidence
  packs

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
- compact guidance-behavior summaries
- packet budget and optimization posture
- execution signals
- routing handoff summaries

The contract should keep user-facing and benchmark-facing packets dense without
destroying provenance.

Guidance Behavior summaries are retained only in compact form:
status, validation status, case counts, selected case ids, failed check ids,
source fingerprints, validator command, hot-path contract, runtime-layer
contract, and Tribunal-ready signal. Memory Contracts must not expand the full
corpus or run validation while shaping context packets or evidence packs.

## Trust And Safety Posture
- Repo truth remains read-only. This layer is about representation, not
  mutation.
- Sensitive tokens, secrets, DSNs, private-key material, and non-allowlisted
  paths must be excluded from portable packets.
- Transcript-shaped source refs and ephemeral host paths must be suppressed
  from Character practice events even when they appear in local decision
  receipts. Durable practice memory keeps governed source refs and compact
  fingerprints, not temp files.
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
- [Governance Intervention Engine](../governance-intervention-engine/CURRENT_SPEC.md)
  consumes the compact Guidance Behavior summary as bounded evidence, not as
  an excuse to reopen the corpus or scan repo truth during live selection.

## Validation Playbook
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_tooling_memory_contracts.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py -k 'remote_retrieval or compact_report_summary or odylith_adoption'`
- `odylith validate guidance-behavior --repo-root .`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-04-07: Promoted the packet-safe memory contract layer into a first-class Registry component so allowlisting, redaction, execution-profile encoding, and compact evidence shaping stop hiding inside one helper module. (Plan: [B-058](odylith/radar/radar.html?view=plan&workstream=B-058))
- 2026-04-17: Preserved compact Guidance Behavior summaries in `context_packet.v1` and `evidence_pack.v1` so Context Engine, Execution Engine, and Governance Intervention Engine share one low-latency contract without expanding the corpus or running validation on the hot path. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
- 2026-04-17: Retained the Guidance Behavior platform-contract summary inside compact memory/evidence packets so benchmark/eval, host mirror, bundle, and install-proof availability survives packet handoff without widening stored context. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096); Bug: `CB-123`)
- 2026-04-18: Hardened Adaptive Agent Operating Character learning events so recurrence can retain `tribunal_doctrine_candidate`, intervention visibility is stored as evidence state rather than generated prose, and durable updates remain gated by benchmark, validator, Tribunal, or governance proof. (Plan: [B-110](odylith/radar/radar.html?view=plan&workstream=B-110))
- 2026-04-18: Hardened Character practice-event compaction against transcript-shaped source refs and malformed credit counters: transcript-like refs are suppressed like secrets, non-integer counters become validation issues, and budget checks fail closed instead of throwing or silently greenlighting bad payloads. (Plan: [B-110](odylith/radar/radar.html?view=plan&workstream=B-110))
