- Bug ID: CB-224

- Status: Open

- Created: 2026-07-07

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: Greenfield matrix leakage scan treats campaign evidence as release custody

- Impact: Broad high-variance campaign can fail after successful post-confirm creates because prior campaign result JSON in the dist directory contains project-domain case names and is scanned as protected platform custody.

- Components Affected: release

- Environment(s): local installed release matrix dist 0.1.15 9246923c, 120-case volume-discovery campaign

- Detected By: greenfield matrix volume-discovery campaign

- Failure Signature: platform.domain.leakage.after.generated.artifact.readback.dist.greenfield.matrix; dist:greenfield-matrix-campaign.v1.json leaked drought allocation

- Trigger Path: GREENFIELD_MATRIX_VOLUME_CASE_FILES=<12 volume shards> GREENFIELD_MATRIX_VOLUME_MAX_WORKERS=4 make greenfield-matrix-campaign VERSION=0.1.15 DIST=/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-9246923c

- Ownership: release matrix leakage proof and platform-domain dist scanner evidence-boundary

- Timeline: Captured 2026-07-07 through `odylith bug capture`.

- Blast Radius: Any repeated installed matrix campaign that writes campaign JSON beside release assets before a later generated-readback leakage scan

- SLO/SLA Impact: False post-confirm release-campaign failure blocks broad discovery and release-readiness proof despite governed records passing

- Data Risk: No generated project data was corrupted; risk is false failure classification and stale validation artifacts contaminating release-custody proof

- Security/Compliance: Security posture: no shipped customer data or credential exposure. Compliance and privacy posture: the release policy boundary is violated because validation evidence is misclassified as shipped platform custody.

- Invariant Violated: Release leakage proof must scan shipped platform assets, not post-build validation evidence files written beside the dist

- Root Cause: The dist text-file scanner excluded `greenfield-post-confirm-*` and `greenfield-rescue-proof-*` evidence files, but not tiered campaign outputs such as `greenfield-matrix-campaign.v1.json`. A later generated-readback leakage scan therefore read prior campaign stdout excerpts as if they were shipped release custody.

- Solution: Treat `greenfield-matrix-*` top-level dist files as validation evidence, not release assets, while continuing to scan wheels, runtime tarballs, install scripts, manifests, and other shipped platform files.

- Verification: Focused leakage proof passed `tests/unit/install/test_platform_domain_leakage_check.py` and `tests/unit/install/test_release_greenfield_matrix_bootstrap.py` (`43 passed`). Direct `scan_dist()` against `/Volumes/FREEDOM_RESEARCH/research-code/odylith-local-release-0.1.15-9246923c` with `drought allocation` now returns no findings. Required next proof: rerun the 120-case volume-discovery campaign against the same installed dist and then rebuild final dist after this source fix.

- Prevention: Regression test `test_scan_dist_allows_matrix_campaign_json_as_evidence` pins the evidence-boundary rule for `greenfield-matrix-campaign.v1.json`.

- Agent Guardrails: Do not weaken wheel or runtime tarball scanning; do not add domain-specific exceptions for water rights, drought, or other case vocabulary; keep validation artifacts out of shipped-custody decisions.

- Related Incidents/Bugs: CB-223

- Code References: - scripts/release/platform_domain_leakage_check.py
- tests/unit/install/test_platform_domain_leakage_check.py
