- Bug ID: CB-140

- Status: Fixed Pending Release

- Created: 2026-04-30

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: A first-run consumer show report listed an Atlas candidate and gave a plain-English prompt to create the Dentoai Isb Boundary and Ownership Map Atlas diagram. Following that prompt made the agent call atlas scaffold, which failed because the scaffold CLI required at least one Radar workstream, technical plan, and doc link. The product contract was wrong: an operator must be able to start with a topology diagram, see it rendered, and link Radar/plan/doc truth later.

- Impact: New operators can follow a recommended first-run Atlas prompt and immediately hit a fail-closed scaffold error, making advisory output feel random and untrustworthy.

- Components Affected: odylith

- Environment(s): macOS Apple Silicon consumer repo after Odylith 0.1.11 first install; advisory show output in a repo with app source but no Radar workstream, technical plan, or doc-linked Atlas grounding.

- Detected By: User-provided Claude transcript from 2026-04-29.

- Failure Signature: atlas scaffold exits 2 with: FAILED radar, technical-plan, and doc links are required, after the show output recommended creating the Dentoai Isb Boundary and Ownership Map Atlas diagram.

- Trigger Path: Run show, then ask the agent to create the suggested Atlas diagram before creating Radar or technical-plan grounding.

- Ownership: Advisory show output and Atlas scaffold prompt contract.

- Timeline: 2026-04-29: show output recommended a Registry component, Radar workstream, Atlas diagram, and Casebook bug; user selected the Atlas diagram prompt; scaffold help showed required fields; scaffold failed on missing Radar, technical-plan, and doc links; agent had to ask whether to create grounding first or pivot to Registry.

- Blast Radius: Fresh consumer repos with Atlas candidates but no existing governance grounding; agent-host first-run onboarding.

- SLO/SLA Impact: P1 onboarding and governance-authoring degradation; no runtime outage, but a recommended product action dead-ends.

- Data Risk: No data loss observed; Atlas scaffold fails closed before writing an orphan diagram.

- Security/Compliance: No direct security or compliance impact observed.

- Invariant Violated: Advisory show prompts must be executable through the public CLI contract; Atlas-first creation must produce a visible draft diagram instead of requiring the rest of the governance stack first.

- Workaround: Before the forward fix, create the required Radar workstream, technical plan, and doc link before running Atlas scaffold, or start with the Registry component prompt.

- Root Cause: Atlas scaffold treated every diagram as already-governed architecture truth instead of allowing an honest Atlas-first draft state; Atlas auto-update also failed to select freshly scaffolded diagrams whose SVG/PNG artifacts did not exist yet.

- Solution: Allow `odylith atlas scaffold` to create a visible draft diagram without Radar, technical-plan, or doc links. Preserve strict validation behind `--require-links`, mark unlinked entries with `status: draft` and `link_state: atlas_first_draft`, create a starter `.mmd` by default, allow the Atlas renderer to display empty related-link lists, and select diagrams with missing SVG/PNG artifacts for auto-update rendering.

- Rollback/Forward Fix: Forward fix in Atlas scaffold, Atlas render, and Atlas auto-update. Do not hand-edit diagram catalog truth; use the CLI and later tighten the same draft entry with Registry/Radar/plan/doc links.

- Verification: `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_owned_surface_refresh_authoring.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_show_capabilities.py` passed with 66 tests; `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_intervention_engine_apply.py tests/unit/runtime/test_intervention_engine.py` passed with 38 tests.

- Prevention: Keep show output tests aligned with actual authoring behavior, and cover Atlas-first drafts through scaffold, renderer, and auto-update tests so prompt copy cannot drift from the visible diagram contract.

- Agent Guardrails: If the operator asks to start with Atlas, use `odylith atlas scaffold` and create the draft diagram first; do not force the operator to create Registry, Radar, or technical-plan records unless they asked for strict governed linkage.

- Preflight Checks: Inspect src/odylith/runtime/analysis_engine/show_capabilities.py and tests/unit/runtime/test_show_capabilities.py before changing advisory show prompts.

- Regression Tests Added: tests/unit/runtime/test_owned_surface_refresh_authoring.py covers Atlas-first draft scaffold; tests/unit/runtime/test_render_mermaid_catalog.py covers unlinked draft render loading; tests/unit/runtime/test_auto_update_mermaid_diagrams.py covers missing SVG/PNG selection; tests/unit/runtime/test_show_capabilities.py keeps the standalone Atlas prompt.

- Monitoring Updates: Watch consumer transcripts for the required Radar, technical-plan, and doc links scaffold failure immediately after following show output Atlas prompts.

- Version/Build: Odylith 0.1.11 consumer show output observed on 2026-04-29; fixed on the v0.1.12 branch.

- Config/Flags: Default show; no source-local or manual scaffold flags.

- Customer Comms: Tell affected operators the original product behavior was wrong: they should be able to start with an Atlas diagram and see it, then add Registry/Radar/plan/doc grounding later.

- Related Incidents/Bugs: Related to CB-139 as a first-run activation trust issue; distinct from install shell rendering.

- Code References: - src/odylith/runtime/surfaces/scaffold_mermaid_diagram.py
- src/odylith/runtime/surfaces/render_mermaid_catalog.py
- src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py
- src/odylith/runtime/analysis_engine/show_capabilities.py
- tests/unit/runtime/test_show_capabilities.py
