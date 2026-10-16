- Bug ID: CB-344

- Status: Open

- Created: 2026-09-26

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The real file and HTTP publication-recovery browser proof copied roughly 171.8 MB of generated dashboard and governance assets, then repeatedly base64-encoded and JSON-serialized the full write set and recovery journal. The second case reached roughly 5.2 GB RSS and did not finish, blocking exact release qualification even though the Greenfield product mechanism itself had not regressed.

- Impact: Release qualification could not complete and could exhaust a maintainer host while proving Greenfield dashboard publication and recovery.

- Components Affected: dashboard

- Environment(s): Odylith product-repo source-local Greenfield release proof on macOS

- Detected By: Full headless browser validation with process RSS observation

- Failure Signature: First browser recovery case passed; the next entered repeated JSON/base64 serialization, exceeded 5.2 GB RSS, and remained incomplete after 207 seconds.

- Trigger Path: .venv/bin/python -m pytest -q tests/integration/runtime/test_greenfield_dashboard_publication_browser.py

- Ownership: Dashboard publication browser proof and Greenfield recovery evidence fixture

- Timeline: Observed at about 5.2 GB RSS and 207.52 seconds; isolated reproduction reached about 1.68 GB in 30.6 seconds. The bounded fixture then passed both protocols in 80.52 seconds with maximum RSS about 1.70 GB.

- Blast Radius: File and HTTP publication proof across Project, Atlas, Radar, Registry, Casebook, and Compass; no committed consumer data affected.

- SLO/SLA Impact: Blocked the Greenfield release gate and made proof latency and memory non-deterministic.

- Data Risk: No product data loss; test-only temporary repositories and evidence were affected.

- Security/Compliance: Policy, privacy, accessibility, and safety assessment: no trust-boundary bypass and no customer data exposure; oversized retained evidence unnecessarily increased local resource pressure.

- Invariant Violated: Release proof must preserve all six rendered surfaces and crash-recovery laws within a bounded, reproducible operating envelope.

- Workaround: Run only after limiting the fixture to the real browser-request closure and retaining compact journal hashes instead of raw recovery write sets.

- Root Cause: The harness copied a broad generated frontend tree, sealed the same large payload multiple times, reparsed the complete recovery journal, and embedded raw base64 write content in evidence although the browser used only a 33.8-50.0 MB dependency closure.

- Solution: Derive and cap the real per-protocol browser asset closure, stream file hashes, isolate large compile/materialize phases in child processes, and retain compact journal and write-set identities while preserving the six-surface and three-SIGKILL proof.

- Rollback/Forward Fix: Forward-fix the test harness only; do not weaken product recovery assertions or add a product fallback.

- Verification: Both file and HTTP cases pass in one 80.52-second run; eight observations per protocol cover six surfaces and all three kill points; maximum RSS is about 1.70 GB with no runaway growth.

- Prevention: Browser release proofs must enforce an explicit asset-closure byte cap and must never retain raw base64 recovery write sets when hashes and sizes prove identity.

- Agent Guardrails: Do not solve proof-resource failures by dropping surfaces, kill phases, or browser protocols. Bound the evidence carrier while preserving the product invariant.

- Preflight Checks: Measure requested asset closure for file and HTTP; verify all six readiness probes; verify each SIGKILL phase before accepting a harness optimization.

- Regression Tests Added: tests/integration/runtime/test_greenfield_dashboard_publication_browser.py now proves bounded closure, file/HTTP rendering, six-surface readiness, journal immutability during browsing, and abort/commit recovery.

- Monitoring Updates: The fixture records asset count and closure bytes; the release validation records wall time and maximum RSS.

- Version/Build: 2026/freedom/v0.1.15 pre-release checkpoint after 0423928a

- Config/Flags: MAX_ASSET_CLOSURE_BYTES=67108864; protocols=file,http

- Customer Comms: Internal pre-release defect; no customer communication required.

- Related Incidents/Bugs: CB-329

- Code References: - tests/integration/runtime/test_greenfield_dashboard_publication_browser.py
