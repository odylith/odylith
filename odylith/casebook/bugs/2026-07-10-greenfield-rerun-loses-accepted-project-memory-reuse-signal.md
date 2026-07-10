- Bug ID: CB-228

- Status: Open

- Created: 2026-07-10

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A second identical source-local greenfield create reused stable backlog and diagram identities but reported memory.reused_existing=false even though accepted-project memory had already been recorded.

- Impact: Consumers and release proof cannot distinguish a safe idempotent rerun from a fresh memory write, weakening confidence that repeated confirmation preserves accepted project continuity.

- Components Affected: odylith-memory-backend

- Environment(s): Product-repo detached source-local posture on branch 2026/freedom/v0.1.15; multi-actor greenfield create integration case.

- Detected By: Recommended greenfield create performance integration gate; second identical run stayed under 30 seconds but failed the reuse assertion.

- Failure Signature: Second create kept the same backlog IDs and identical diagram IDs, memory.recorded=true, but memory.reused_existing=false.

- Trigger Path: PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_greenfield_create_performance.py::test_multi_actor_greenfield_create_rerun_is_idempotent_under_thirty_seconds

- Ownership: Accepted-project memory prewrite preview, compiled commit result, and memory backend idempotent readback contract.

- Timeline: Captured 2026-07-10 through `odylith bug capture`.

- Blast Radius: Repeated greenfield create or confirm flows against an already accepted identical project transaction.

- SLO/SLA Impact: Both runs remain within 30 seconds, but idempotency and continuity proof fail, blocking release readiness.

- Data Risk: No observed duplicate backlog or diagram identities and no application-data loss; the risk is incorrect memory-state reporting and possible hidden duplicate memory writes.

- Security/Compliance: No direct security or compliance exposure observed; inaccurate provenance/reuse reporting weakens auditability.

- Invariant Violated: An identical accepted-project rerun must reuse the existing memory record or report the exact replacement contract truthfully; compiled result previews and readback must agree.

- Root Cause: Investigation pending at the boundary between precompiled accepted-project memory writes and the memory backend reuse detector.

- Solution: Trace the second-run sealed write and readback, preserve idempotent memory identity in the pre-confirm transaction result, and add exact repeat-confirm regression proof without post-confirm generation.

- Rollback/Forward Fix: Forward fix in a bounded memory/greenfield execution wave; keep current idempotency assertion fail-closed.

- Verification: Exact two-run integration case reproduces deterministically: stable backlog IDs, stable diagrams, recorded memory, false reuse signal.

- Prevention: Include repeated identical transaction compile/confirm in installed release proof and compare memory identity, reuse status, and sealed write set across runs.

- Agent Guardrails: Do not force reused_existing=true in rendering or hide a replacement write. Fix the memory ownership/readback contract and prove exact bytes plus identity.

- Preflight Checks: Inspect existing B-010 memory contracts and compiled accepted-project memory tests before changing code; replay exact two-run test first.

- Monitoring Updates: Track exact idempotency replay and installed repeated-confirm proof before release readiness.

- Version/Build: 0.1.15 source-local branch 2026/freedom/v0.1.15 after commit 1b2072f0f

- Config/Flags: Default source-local greenfield create path; no feature flag.

- Customer Comms: None before release; defect was caught in maintainer QA.

- Related Incidents/Bugs: CB-226

- Code References: - tests/integration/runtime/test_greenfield_create_performance.py
- src/odylith/runtime/domain_intelligence/proposal_memory.py
- src/odylith/runtime/memory
