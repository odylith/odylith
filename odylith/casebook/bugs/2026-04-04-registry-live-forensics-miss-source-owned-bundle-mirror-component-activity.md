- Bug ID: CB-052

- Status: Open

- Created: 2026-04-04

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Registry live forensic coverage could leave a component marked
  `baseline_forensic_only` even while its source-owned bundled mirror files
  were actively changing. The component still had historical spec coverage, but
  its live evidence channels remained empty because workspace-activity mapping
  only matched canonical source `path_prefixes`.

- Impact: Maintainers can misread Registry and conclude that a tracked
  component is currently quiet when the governed product mirror is actively
  changing. That weakens operator trust in Registry's component evidence model
  and makes low-signal manual reconstruction necessary.

- Components Affected: `src/odylith/runtime/governance/component_registry_intelligence.py`,
  Registry forensic coverage, `tribunal`, `remediator`, source-owned bundled
  runtime docs, Registry detail rendering.

- Environment(s): Odylith product repo maintainer mode with local edits under
  `src/odylith/bundle/assets/odylith/...` that mirror component-owned source
  docs or runtime assets.

- Root Cause: The workspace-activity evidence path only matched the manifest's
  canonical component `path_prefixes`. Source-owned mirror locations in the
  bundled product tree were not normalized back to the same owning component,
  so live synthetic evidence could stay empty even when the mirrored product
  artifact was the real file under active edit.

- Solution: Teach Registry's workspace-activity mapper to recognize the
  product repo's source-owned mirror layout and map those mirrored paths back
  to the owning component's canonical source path prefixes. Keep the rule
  narrow so unrelated generated or benchmark paths still stay excluded.

- Verification: Focused Registry rendering and forensic sidecar tests should
  prove that a component becomes live when only the mirrored path changes, and
  benchmark-facing regression tests should stay green.

- Prevention: If Odylith maintains governed source-to-bundle mirrors, the
  component forensic layer needs the same ownership model. Otherwise Registry
  quietly undercounts live activity on product-owned components.

- Detected By: Manual inspection of live Registry forensic coverage on
  2026-04-04 after `tribunal` and `remediator` remained baseline-only despite
  active bundle-side source edits elsewhere in the repo.

- Failure Signature: `FORENSICS.v1.json` for an affected component reports
  `status: baseline_forensic_only`, `recent_path_match_count: 0`, and an empty
  live `timeline` even though the source-owned bundled mirror for that
  component is currently dirty.

- Trigger Path: Registry component report building through
  `build_workspace_activity_events(...)` and
  `build_component_forensic_coverage(...)`.

- Ownership: Registry component-evidence mapping and Odylith product
  source-to-bundle mirror handling.

- Timeline: The stricter forensic model correctly separated explicit Compass
  evidence from synthetic workspace activity, but the bundle mirror ownership
  rule lagged behind that separation and left some components looking quieter
  than they really were.

- Blast Radius: Registry evidence accuracy for product-owned components,
  operator trust in component activity, and any workflow that depends on live
  forensic coverage to decide whether a component is stale or recently touched.

- SLO/SLA Impact: Low direct runtime risk, medium operator-trust and
  governance-signal risk.

- Data Risk: Low.

- Security/Compliance: No direct security impact.

- Invariant Violated: A source-owned mirror edit for a tracked component should
  count as live component activity when Odylith itself treats that mirror as a
  governed product artifact.

- Workaround: Manually inspect dirty paths and infer source ownership outside
  Registry, but that defeats the point of the forensic surface.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Do not fix this by treating all generated or mirrored files
  as evidence. Keep the rule deterministic, component-owned, and benchmark-safe.

- Preflight Checks: Inspect Registry forensic coverage policy, the affected
  component manifest entries, and benchmark-facing dirty-path tests before
  widening any shared path helper.

- Regression Tests Added: Pending.

- Monitoring Updates: Watch whether components with only source-mirror edits
  still surface as `baseline_forensic_only` after Registry refresh.

- Residual Risk: If Odylith later adds new mirror layouts outside the current
  product bundle tree, the rule may need explicit metadata rather than the
  current narrow path normalization.

- Related Incidents/Bugs: No related bug found before this capture.

- Version/Build: `v0.1.7` worktree on 2026-04-04.

- Config/Flags: Default Registry forensic workspace-activity window.

- Customer Comms: Registry undercounted live component activity in a narrow
  but visible source-mirror case; the fix tightens evidence accuracy without
  broadening benchmark behavior.

- Code References: `src/odylith/runtime/governance/component_registry_intelligence.py`,
  `src/odylith/runtime/surfaces/render_registry_dashboard.py`,
  `tests/unit/runtime/test_render_registry_dashboard.py`,
  `tests/unit/runtime/test_sync_component_spec_requirements.py`

- Runbook References: `odylith/registry/source/components/registry/CURRENT_SPEC.md`,
  `src/odylith/bundle/assets/odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md`

- Fix Commit/PR: Pending.
