- Bug ID: CB-167

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-05-04

- Severity: P0

- Reproducibility: Always

- Type: Tooling

- Description: Fresh consumer greenfield flow exposed three trust failures: generated refresh guards could reuse stale payloads after source truth changed, greenfield apply could silently omit proposed waves that resolved to no children, and wave assignment/adoption required governed front-matter hand edits despite CLI-first policy.

- Impact: Operators can receive confident green refresh or apply success while Radar, Registry, Compass, or program wave truth is stale, incomplete, or unreachable through supported CLI verbs.

- Components Affected: domain-intelligence

- Environment(s): Odylith v0.1.14 post-release maintainer branch after consumer-lane fresh empty repo dogfood.

- Detected By: Operator brutal feedback from a fresh empty consumer repo greenfield propose/apply/render/wave authoring session.

- Failure Signature: dashboard refresh and registry refresh report fingerprint reuse while rendered payloads are stale; greenfield apply reports fewer waves than proposed; wave assign help hides required args; wave assign denial leaks internal Tribunal scope language when workstream_parent is missing.

- Trigger Path: Run odylith greenfield propose/apply in an empty repo, mutate workstream wave assignments, then run dashboard/registry refresh and wave assign/create help.

- Ownership: Generated surface refresh guards, greenfield program formation, and execution-wave CLI authoring.

- Timeline: Captured 2026-05-04 through `odylith bug capture`.

- Blast Radius: Fresh consumer repos, greenfield proposal-first projects, and operators relying on CLI-first governance instead of hand-editing Radar front matter.

- SLO/SLA Impact: First-run governance trust is damaged because operators must debug stale generated surfaces and hidden topology authoring gaps before minute thirty.

- Data Risk: Governance-memory data risk: source truth may be valid while generated UI remains stale, or proposed program waves may be omitted from durable program truth.

- Security/Compliance: No direct security exposure; high compliance-of-process risk for governed memory and release review.

- Invariant Violated: Governance authoring commands must not report passed while serving stale surfaces, must not silently drop proposed structural program waves, and must provide CLI verbs for reciprocal workstream topology required by validators.

- Root Cause: Generated refresh guards keyed on file size and mtime instead of content bytes; greenfield wave assignment skipped empty member waves; wrapper CLI help consumed backend wave/program arguments; wave authoring had no adopt verb to set reciprocal parent/child links.

- Solution: Hash generated refresh watched inputs by content with a new guard version, add dashboard refresh --force, preserve all greenfield waves with deterministic child assignment, forward wave/program backend help, add program adopt plus wave assign --adopt, and add backlog create --parent/--umbrella for CLI-first child creation.

- Rollback/Forward Fix: Forward fix in v0.1.14 post-release branch; no rollback because existing source records stay readable and new refresh guard version invalidates stale guard caches.

- Verification: Focused tests cover generated refresh content fingerprints, greenfield wave preservation, program/wave adoption, backlog create parent adoption, CLI help forwarding, and dashboard refresh force bypass.

- Prevention: Keep same-size content-change fingerprint tests, greenfield multi-wave tests, and CLI help/adoption tests in release gates before shipping consumer greenfield changes.

- Agent Guardrails: Do not accept greenfield or wave authoring complete unless source truth, generated surfaces, CLI help, reciprocal topology, and migration/refresh behavior are proven together.

- Preflight Checks: Search existing Casebook greenfield/refresh records; reproduce through source CLI help and focused tests before mutating governance records.

- Regression Tests Added: tests/unit/runtime/test_generated_refresh_guard.py; tests/unit/runtime/test_greenfield_proposals.py; tests/unit/runtime/test_program_wave_authoring.py; tests/unit/runtime/test_backlog_authoring.py; tests/unit/test_cli.py; tests/unit/runtime/test_sync_cli_compat.py

- Monitoring Updates: Watch consumer fresh-repo dogfood for fingerprint reuse on changed source truth, missing program waves, and any wave assignment path that still requires hand-edited front matter.

- Version/Build: 0.1.14 post-release fixes

- Config/Flags: dashboard refresh --force; greenfield default release selector remains 0.0.1; wave assign --adopt; backlog create --parent/--umbrella

- Customer Comms: Release notes should state that refresh reuse now fingerprints source bytes and greenfield wave/topology authoring is reachable through supported CLI verbs.

- Related Incidents/Bugs: CB-156, CB-160, CB-166

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.14

- Public Response: pending

- Code References: - src/odylith/runtime/common/generated_refresh_guard.py
- src/odylith/runtime/domain_intelligence/greenfield_programs.py
- src/odylith/runtime/governance/program_wave_authoring.py
- src/odylith/runtime/governance/backlog_authoring.py
- src/odylith/runtime/governance/sync_workstream_artifacts.py
