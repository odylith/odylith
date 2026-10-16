- Bug ID: CB-199

- Status: FixedPendingRelease

- Created: 2026-05-11

- Severity: P1

- Reproducibility: Always

- Type: OperatorUX

- Description: After applying a greenfield proposal, accepted-project.v1.json, Radar workstreams, Registry components, and Atlas diagrams existed, but the Project tab could still render the blank repository projection, a templated Product Story with source-map/topology blocks, or a broken first-path scenario layout instead of a human product narrative. Operational risk: operators could miss the actual product story and start implementation from stale or generic project state. Delivery risk: project truth, workstreams, components, diagrams, and release proof could appear disconnected. Compliance/privacy risk: money-movement proposals could hide unresolved lender, custody, privacy, and policy boundaries behind generic UI.

- Impact: Greenfield users could apply proposal records and still see a blank or machinery-first Project page instead of the accepted product story.

- Components Affected: dashboard

- Environment(s): Odylith v0.1.15 source-local maintainer posture and an installed empty consumer repo after greenfield create --confirm.

- Detected By: User screenshots and source-local browser proof against a consumer dashboard Project tab.

- Failure Signature: Project tab showed placeholder-repo blank state, orienting work, templated Product Story/source-map layout, first-path scenario prose squeezed into a narrow label column, or a component-inventory dump labeled Product Story. The 2026-05-14 downstream-domain repro rendered a broken service-component sentence as the hero and story opener, repeated artifact mapping before explaining the product, and added native browser tooltips on top of Odylith's black ID tooltip.

- Trigger Path: Install local Odylith, run odylith greenfield propose for a new product, run odylith greenfield create --confirm --release 0.0.1, then open odylith/index.html?tab=project.

- Ownership: Dashboard Project tab renderer, Project Intelligence greenfield projection, Domain Intelligence greenfield apply refresh handoff, and tooling shell refresh guard.

- Timeline: Captured 2026-05-11 through `odylith bug capture`.

- Blast Radius: Greenfield consumer repos, Project tab, Radar/Registry/Atlas traceability perception, and first-build operator review.

- SLO/SLA Impact: Blocks project-first comprehension and can delay or misdirect the first implementation lane after greenfield apply.

- Data Risk: No secret or production data exposure; source-truth risk is stale or generic project claims being shown after accepted proposal records exist.

- Security/Compliance: Security/access posture unchanged; compliance risk increases when regulated business, privacy, or policy boundaries are hidden by stale or generic Project UI.

- Invariant Violated: Confirmed greenfield apply must make the Project tab start from the accepted project story, with dynamic source-derived prose and links, not blank fallback or templated governance machinery.

- Root Cause: Greenfield apply did not refresh the tooling shell Project surface; the shell refresh guard did not watch accepted-project source or Project Intelligence renderer code; Product Story rendered artifact topology as a visible template instead of prose; scenario fallback prose reused the two-column label/value row layout; source-backed fallback could choose the first Registry component as the project identity when accepted-project source was absent; component authoring stored imperative responsibility text inside "responsible for ..." prose; Project deeplinks set both Odylith's custom tooltip metadata and the native `title` attribute.

- Solution: Refresh tooling_shell after greenfield apply, route apply handoff to the Project tab, include accepted-project and Project Intelligence code/CSS in the shell refresh fingerprint, move Product Story generation into the Project Intelligence story generator, render story prose as a human narrative informed by Radar, Registry, Atlas, and release proof, give first-path scenario prose its own full-width copy treatment, recover accepted-greenfield product identity from Compass/Radar before falling back to component identity, make Product Story paragraphs answer product/user/problem/workflow/proof before artifact mapping, normalize component responsibility prose into finite clauses, and remove native browser `title` attributes from ID deeplinks.

- Verification: python -m pytest tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_project_intelligence.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_owned_surface_refresh_authoring.py -q; python -m pytest tests/unit/runtime/test_project_intelligence.py tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_owned_surface_refresh_authoring.py tests/integration/runtime/test_project_tab_browser.py -q; source-local render of a consumer fixture; Playwright screenshot /tmp/odylith-project-story-scenario-v2.png with Product Story present, blank fallback absent, source-map/topology block absent, and first-path scenario prose using full-width layout.

- Prevention: Keep tests asserting accepted greenfield projects feed Project tab from accepted-project plus Tribunal evidence, source-backed greenfield fallbacks recover the product identity before component identity, Product Story stays prose-first, artifact mapping follows product narration, component responsibility text is grammatically finite, shell refresh invalidates on accepted-project and renderer changes, and ID deeplinks do not set native browser tooltip attributes.

- Agent Guardrails: Do not call greenfield UX fixed until the installed repo Project tab is visually checked after apply. Do not present governance topology widgets as the Product Story.

- Regression Tests Added: Updated greenfield apply Project tab regression, Project Intelligence greenfield rendering regression, Product Story source-backed rendering regression, source-backed accepted-greenfield product identity regression, deeplink custom-tooltip regression, component responsibility grammar regression, scenario prose layout regression, tooling dashboard accepted-project refresh regression, and owned-surface tooling_shell refresh regression.

- Code References: - src/odylith/runtime/project_intelligence/product_story.py
- src/odylith/runtime/project_intelligence/greenfield.py
- src/odylith/runtime/project_intelligence/builder.py
- src/odylith/runtime/project_intelligence/deeplinks.py
- src/odylith/runtime/project_intelligence/presenter.py
- src/odylith/runtime/project_intelligence/project_tab.css
- src/odylith/runtime/surfaces/render_tooling_dashboard.py
- src/odylith/runtime/domain_intelligence/greenfield_proposals.py
- src/odylith/runtime/governance/component_authoring.py
