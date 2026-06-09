- Bug ID: CB-198

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-05-11

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Greenfield child artifacts failed product manager comprehension

- Impact: Confirmed greenfield child workstreams, Registry component IDs, and Atlas diagram slugs could read like governance preparation instead of the business/product work a project owner asked Odylith to create.

- Components Affected: domain-intelligence

- Environment(s): Odylith greenfield create/apply against an empty consumer repo with an external-domain prompt.

- Detected By: Operator screenshot review and source audit of a consumer Radar B-002, Registry specs, Atlas slugs, and accepted-project state.

- Failure Signature: Radar B-002 used generic Decision Basis lines such as created as a new queued workstream and deeper scope decomposition waits; Registry and Atlas inherited the full prompt slug instead of a compact domain artifact identity.

- Trigger Path: odylith greenfield create --repo-root . --prompt <greenfield project intent> --release 0.0.1 --confirm, then open Radar B-002 and related Registry/Atlas artifacts.

- Ownership: Domain Intelligence greenfield projection, Radar backlog authoring, Registry component scaffolding, Atlas diagram scaffolding.

- Timeline: Captured 2026-05-11 through `odylith bug capture`.

- Blast Radius: Greenfield child workstreams, Radar INDEX rationale, component directories/specs, Atlas diagram slugs, accepted-project topology links, and Project tab source graph.

- SLO/SLA Impact: Breaks the first-read product-manager test before implementation planning starts.

- Data Risk: No production data loss; affected consumer repos may retain low-quality generated governance records until regenerated or repaired.

- Security/Compliance: In regulated domains, vague prep language and prompt-shaped IDs can obscure ownership, compliance, proof, and release-boundary responsibilities.

- Invariant Violated: A confirmed greenfield proposal must produce product-relevant artifacts shaped by project intelligence, not raw prompt repetition or generic governance preparation text.

- Root Cause: Greenfield rows carried product-specific content, but Radar authoring discarded product-specific rationale when rationale_lines crossed through the generic backlog create namespace; component and diagram slugs also inherited the raw project prompt.

- Solution: Preserve product-derived rationale through backlog authoring and use compact domain artifact slugs for generated Registry and Atlas artifacts.

- Follow-Up Evidence (2026-06-09 / Dignity-shaped confirmed create): A v0.1.15 local install transcript for a dignity-and-agency app exposed a broader comprehension failure: child workstreams could inherit parent setup actions, action-shaped outcomes rendered as object phrases such as `shows open`, component labels repeated conjunctions, `Grown-up` casing flattened, and repetitive implementation-slice template text appeared across Radar surfaces even when the post-confirm gate passed.

- Follow-Up Root Cause (2026-06-09): Confirmed-create used the same first-path action string across program and child rows without preserving actor ownership, downstream completion/enrichment layers treated action-shaped outcomes as visible objects, generated-copy gates did not reject presentational/action splices or repeated implementation templates, and component/title normalization did not distinguish setup actions, terminal outcomes, weak reflection artifacts, hyphenated role terms, or repeated conjunction chains.

- Follow-Up Solution (2026-06-09): Preserve actor-owned workflow actions for child titles and copy, prefer terminal outcome titles only for strong outcome nouns, render action-shaped outcomes as user capabilities instead of objects, gate presentational/action splices and repeated implementation-slice templates, normalize repeated component conjunction chains, preserve hyphenated terms such as `Grown-up`, and repair gerund/base-form conversion for action chains such as accepting or dismissing a suggestion.

- Rollback/Forward Fix: Forward fix in Domain Intelligence and Radar authoring; existing generated consumer repos should be regenerated or repaired from their accepted project source.

- Verification: pytest tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_project_intelligence.py -q. Follow-up proof: `PYTHONPATH=src ./.venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_confirmed_backlog_terms.py tests/unit/runtime/test_greenfield_artifact_language_quality.py tests/unit/runtime/test_greenfield_prewrite_transaction.py tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py` passed (`72 passed`); `PYTHONPATH=src ./.venv/bin/python -m pytest -q tests/integration/runtime/test_greenfield_create_performance.py` passed (`7 passed`). A fresh Dignity-shaped confirmed-create replay completed in 12.296s and produced zero hits for `visible outcome from`, `uses the product to`, `understand The`, `Start with this implementation slice`, `representative user can`, `Let Child Learner Create An Account`, `shows open`, `Grown Up Recap`, and the old `Scenario Library and Authoring and Curation` label.

- Prevention: Regression tests assert compact domain artifact IDs, no raw prompt slug in project payload, no generic queued-workstream rationale in greenfield Radar output, and Project tab projection from accepted-project and Tribunal state.

- Agent Guardrails: Before declaring a greenfield fix, inspect Radar child rows, Registry component IDs/specs, Atlas diagram IDs, accepted-project topology, and the Project tab story for product-owner readability.

- Preflight Checks: Run a product-manager comprehension audit on at least one greenfield fixture before local release packaging.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_feeds_project_tab_from_accepted_project_and_tribunal; tests/unit/runtime/test_project_intelligence.py::test_greenfield_workstream_body_does_not_repeat_full_project_title

- Code References: - src/odylith/runtime/domain_intelligence/proposal_scaffold.py
- src/odylith/runtime/domain_intelligence/greenfield_workstream_rows.py
- src/odylith/runtime/governance/backlog_authoring.py
