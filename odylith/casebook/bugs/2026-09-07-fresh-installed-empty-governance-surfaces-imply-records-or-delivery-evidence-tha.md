- Bug ID: CB-330

- Status: FixedPendingRelease

- Fixed In: 0.1.15

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

- Root Cause: Atlas cleared metadata without hiding selection-only sections, the source-less image or unavailable navigation. Compass substituted a generic priority, estimated an empty mapping, treated no workstream or timestamp as stale execution and labelled deferred narration as underway. Casebook checked only visible rows, confusing absent source with filtered results. Radar and Registry cleared detail without source-empty guidance; selected-ID-only async guards permitted older same-ID responses to overwrite newer detail.

- Solution: Give each surface's existing selection or presentation phase one owner for absent versus filtered state. Preserve selected Atlas diagrams during filtering, remove unsupported Compass facts before narration, distinguish Casebook source count from visible count and cancel superseded Radar/Registry detail loads. Provide source-empty next steps without inventing records. Keep the frozen header, mobile KPI layout, sealed semantics and 60/90/120 budgets unchanged.

- Verification: Fresh final source-local empty consumer passes 28 desktop/mobile route-state cells, six Open Project recoveries and independent review of all seven surfaces, with 40 screenshots, 151 unchanged source/asset hashes and 18 unchanged governed-source records. A separate final generated package passes all 32 normal/empty/degraded/error browser cells and exact sealed/readback checks for 113 files; browser reads leave every published byte unchanged. Real delayed-fetch controls fail on all four prior-renderer cases and pass on current source. Atlas 81, Radar/Registry 76, Casebook 25 and final Compass 212 focused checks pass; these overlap broader suites and are not additive unique counts. Evidence: /private/tmp/odylith-empty-state-proof.kJuowo. Exact updated-distribution installation and release remain pending; the retained 4ce8cd2f installed screenshots are baseline, not current-runtime proof.

- Prevention: Treat screenshot adjudication as independent evidence; a route-heading and no-overflow pass is not a UX pass. The first isolated run passed 28 automated cells but failed visual review on fabricated freshness; keep that attempt explicitly rejected. In-process provider guards do not cover spawned maintenance, so synthetic no-model proof also uses the existing background-disable test setting. The earlier contaminated fixture cannot claim zero model calls. Extracted presentation owners must be included in existing worker-epoch inputs; an actual-file invalidation regression covers the new Compass status owner. Mobile KPI density and full accessibility remain separate open obligations.

- Related Incidents/Bugs: CB-181, CB-303; workstream B-142

- Code References: - src/odylith/runtime/surfaces/render_mermaid_catalog.py
- scripts/release/greenfield_browser_surface_proof.py
