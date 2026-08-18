- Bug ID: CB-344

- Status: Open

- Created: 2026-08-18

- Severity: P1

- Reproducibility: Always

- Type: API

- Description: The semantic graph authority cut added --semantic-intent-file but retained --intent-file and --confirmed-intent-file as equivalent public proposal and compiler aliases. Help therefore advertises obsolete prose-era authority and violates the graph-only public entry contract.

- Impact: Operators can invoke retired intent-file vocabulary as if it were equivalent to the typed source-cited Semantic Intent packet, preserving an obsolete authority seam during the graph cutover.

- Components Affected: domain-intelligence

- Environment(s): Odylith product-repo detached source-local canonical dev validation

- Detected By: Canonical pytest shard 21, test_greenfield_propose_help_forwards_backend_flags

- Failure Signature: Greenfield propose help contains --intent-file and --confirmed-intent-file; assertion that --intent-file is absent fails.

- Trigger Path: python -m pytest -q -x tests/unit/test_cli.py::test_greenfield_propose_help_forwards_backend_flags

- Ownership: Greenfield public CLI parser and semantic packet entry contract

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: Greenfield propose and controlled compile-transaction callers, installed help, and host guidance

- SLO/SLA Impact: Blocks canonical dev validation and release completion.

- Data Risk: No governed writes occurred; risk is semantic authority confusion if obsolete aliases are used.

- Security/Compliance: No direct security impact; fail-closed authority separation is weakened.

- Invariant Violated: The graph-native public route must accept only the canonical typed Semantic Intent packet flag and must not preserve prose-era intent aliases.

- Root Cause: Commit 555f72917 inserted --semantic-intent-file into an existing argparse alias declaration without deleting --intent-file and --confirmed-intent-file.

- Solution: Remove the two retired aliases from propose and compile-transaction, retain only --semantic-intent-file, and migrate the obsolete negative CLI characterization to assert parser rejection.

- Verification: Exact help and public-entry tests, structural source scan for retired aliases, then replay canonical shard 21.

- Prevention: Treat public entry cutovers as symbol-level authority deletion and require structural inventories for superseded flags.

- Agent Guardrails: Do not hide or tolerate old aliases as compatibility when the underlying authority contract is intentionally severed.

- Preflight Checks: Inspect all live source and test usages of the retired flags before changing the parser; preserve the unrelated discipline --intent-file contract.

- Regression Tests Added: tests/unit/test_cli.py::test_greenfield_propose_help_forwards_backend_flags and tests/unit/runtime/test_greenfield_public_entry_contract.py::test_public_greenfield_help_exposes_semantic_packet_entrypoints

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_proposals_cli.py
- tests/unit/test_cli.py
