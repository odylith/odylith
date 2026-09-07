- Bug ID: CB-330

- Status: Open

- Created: 2026-09-07

- Severity: P2

- Reproducibility: High

- Type: UX

- Description: Exact clean 4ce8cd2f local 0.1.15 installation has zero project records. Independent desktop and 430px mobile screenshot review finds an Atlas broken-image preview with blank metadata, Compass delivery projected heuristically at roughly 6 days beside zero active workstreams, and Casebook filter-recovery instructions despite zero cases. Radar and Registry also leave unexplained blank panels. Sixteen route/layout cells pass after correcting test assumptions, but those checks do not qualify this human-visible experience.

- Impact: First-time consumers see a broken architecture preview, unsupported delivery guidance and unhelpful next steps before defining a project.

- Components Affected: dashboard

- Environment(s): Fresh installed local distribution from clean 4ce8cd2f, authoring disabled, Chromium desktop1440 and mobile430; evidence /private/tmp/odylith-installed-checkpoint.tefox7/installed-empty-browser-final

- Detected By: Independent screenshot review during B-142 installed governance UX checks; root visually corroborated Atlas, Compass and Casebook.

- Failure Signature: Atlas zero total with broken image; Compass zero active workstreams with roughly 6 days forecast; Casebook zero cases with change-filter advice.

- Trigger Path: Install into a fresh nested Git repo, leave project undefined, serve odylith/index.html, and inspect tabs atlas, compass, casebook, radar and registry at desktop and mobile widths.

- Ownership: Dashboard surface owners: Atlas selection/empty renderer, Compass no-scope narration substrate and Casebook/Radar/Registry empty-state presenters.

- Timeline: Captured 2026-09-07 through `odylith bug capture`.

- Blast Radius: Fresh installed consumers before first accepted Greenfield project; existing populated and degraded/error states need separate preservation proof.

- SLO/SLA Impact: First-run utility and trust regression; observed install time is not consumer 60/90/120 creation SLA proof.

- Data Risk: No governed-byte mutation observed during browser inspection; no data loss observed.

- Security/Compliance: No security incident observed. Source-grounded presentation must not imply unobserved delivery evidence.

- Invariant Violated: Absent source records must produce explicit useful empty states, not broken previews, invented forecasts or instructions that assume hidden records.

- Root Cause: Visible no-record paths are insufficiently distinguished from populated or filter-empty states; precise source ownership remains to be diagnosed before patching.

- Solution: Add minimal empty-state handling at each existing owner with source-empty versus filtered-empty controls; do not build another framework or change the frozen dashboard header.

- Verification: Preserve the original screenshots and add failing empty-state assertions before implementation. Recheck normal, empty/fallback, degraded/error and invalid-recovery paths across all seven surfaces at both widths.

- Prevention: Treat screenshot adjudication as independent evidence; a route-heading and no-overflow pass is not a consumer UX pass.

- Related Incidents/Bugs: CB-181, CB-303; workstream B-142

- Code References: - src/odylith/runtime/surfaces/render_mermaid_catalog.py
- scripts/release/greenfield_browser_surface_proof.py
