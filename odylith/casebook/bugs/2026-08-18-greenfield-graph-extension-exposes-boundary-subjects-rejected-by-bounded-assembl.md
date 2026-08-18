- Bug ID: CB-348

- Status: FixedPendingRelease

- Created: 2026-08-18

- Severity: P2

- Reproducibility: Consistent

- Type: Product

- Description: Greenfield graph extension exposes boundary subjects rejected by bounded assembly

- Impact: A fresh one-shot semantic author run reaches deterministic assembly and fails before evidence persistence, consuming the assignment and blocking attributable convergence evidence.

- Components Affected: domain-intelligence

- Environment(s): Detached source-local Greenfield development cohort at 030c2d5390b212aa46e999bf7b9f7644d597de1f

- Detected By: Fresh revision-bound 24-case development cohort at gfhi-005

- Failure Signature: ValueError: Semantic graph extension boundary relation lacks a bounded subject

- Trigger Path: greenfield_semantic_host_execution.author_development_case -> assemble_semantic_intent_from_extension -> _require_bounded_extension

- Ownership: Semantic graph extension author schema and bounded relation assembly contract

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: Any host-authored architecture relation whose free-form subject id resolves outside the bounded extension fact set

- SLO/SLA Impact: Release-blocking development evidence failure after four clean cases

- Data Risk: No customer write and no persisted failed segment; deterministic assembly failed closed

- Security/Compliance: Safety custody held, but the provider contract admitted output the deterministic boundary could not accept

- Invariant Violated: Every provider-expressible architecture relation must be admissible under the same typed bounded-extension contract that assembles it

- Root Cause: The provider schema exposed one free-form top-level relation list with authored subject ids, relation kinds, and custody, while deterministic assembly admitted only subjects already present in the bounded extension fact set. The public authoring contract and the assembler therefore described different languages.

- Solution: Replaced the free-form relation list with `odylith.greenfield.semantic-graph-extension.v2`. Each bounded internal-system node owns typed outgoing endpoint groups, each bounded state node may own typed incoming changes, and deterministic assembly projects subject, relation kind, and custody. The old top-level relation path was deleted rather than retained as a fallback.

- Rejected Approaches: No verifier weakening, prompt-only correction, validation-error retry, regex/token parser, or compatibility adapter was added. Those approaches would preserve split authority or make failed author output non-attributable.

- Verification: Focused protocol and custody matrix passed 154 tests. Full frozen-tree validation passed 4,405 tests with 1 expected skip; its sole initial failure was the unregistered release migration fingerprint. B-146 recorded the consumer-install assessment, the v0.1.15 migration gate then passed with zero blockers, and the exact previously failing CLI test passed 1/1.
