- Bug ID: CB-206

- Status: Open

- Created: 2026-06-26

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Agent guidance did not require failed mechanism capture before repeated fixes

- Impact: Maintainer and host-agent sessions could repeat failed post-confirm fixes or rely on chat memory instead of governed learning, slowing convergence and weakening release-quality claims.

- Components Affected: odylith-chatter

- Environment(s): Odylith product repo maintainer mode, pinned dogfood and detached source-local guidance, Codex and Claude host guidance, consumer bundle assets.

- Detected By: Operator feedback during recursive greenfield post-confirm quality work.

- Failure Signature: Durable failures, failed mechanisms, and prior failed fix attempts were not explicitly required to be searched and captured across all agent guidelines and skills before continuing.

- Trigger Path: Repeated greenfield post-confirm diagnosis, simulation, and release-readiness work across Codex and Claude guidance lanes.

- Ownership: Odylith guidance, Chatter, Casebook, Compass, Registry, Atlas, and install-managed agent assets.

- Timeline: Captured 2026-06-26 through `odylith bug capture`.

- Blast Radius: Maintainer, pinned dogfood, detached source-local, installed consumer repos, Codex, Claude Code, bundled guidance, and high-risk greenfield repair loops.

- SLO/SLA Impact: Raises recursive repair latency and release risk because failed approaches can be rediscovered instead of skipped from governed memory.

- Data Risk: No direct data loss; governance memory loss can mislead future artifact-quality and release-readiness work.

- Security/Compliance: No direct security exploit; compliance and release proof can be weakened if failed mechanisms are not preserved.

- Invariant Violated: Durable Odylith product learning must live in governed artifacts, and failed mechanisms must not remain only in chat memory.

- Root Cause: Guidance treated governance upkeep as workflow hygiene but did not make failed-mechanism capture and prior-failed-fix preflight a fail-closed default across all lanes and hosts.

- Solution: Add a shared governance-learning rule to AGENTS, Claude/Codex host contracts, install generators, bundle mirrors, and operational skills; require Casebook search, failed-mechanism capture, and no repeated failed fix paths before continuing.

- Verification: Focused mirror tests enforce the governance-learning rule across source guidance, bundle assets, and install generators.

- Prevention: Keep Casebook/Radar/Registry/Atlas/Compass freshness mandatory before commit, build, release, or completion claims; update existing governance truth before creating duplicates.

- Agent Guardrails: Before fixing a bug, search Casebook and related governance artifacts, read prior failed mechanisms and failed fix attempts, and do not repeat a fix path governance already shows failed.

- Preflight Checks: Search Casebook, Radar, technical plans, Registry, Atlas, and Compass for the failure signature and failed mechanisms before editing.

- Regression Tests Added: tests/unit/runtime/test_source_bundle_mirror.py::test_governance_learning_rule_travels_to_guidance_skills_and_install_generators

- Code References: - AGENTS.md
- odylith/AGENTS.md
- odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md
- odylith/skills/odylith-casebook-bug-capture/SKILL.md
