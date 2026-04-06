- Bug ID: CB-011

- Status: Open

- Created: 2026-03-28

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: When `ODYLITH_RELEASE_BASE_URL` was set for local hosted-asset
  rehearsal, Odylith built a synthetic release index from the manifest's
  `assets` map only. That omitted `release-manifest.json` itself and the
  `.sigstore.json` sidecars required by the verified-release download path.

- Impact: Fresh local hosted-asset rehearsal failed when the managed runtime
  attempted to download and verify the context-engine pack during first install.

- Components Affected: local release adapter, verified-release download path,
  local maintainer hosted-asset smoke.

- Environment(s): local hosted-asset rehearsal using
  `ODYLITH_RELEASE_BASE_URL`.

- Root Cause: The synthetic local release index did not include fixed manifest
  assets and per-asset sigstore bundle names.

- Solution: Have the local release adapter expose the manifest, its sigstore
  bundle, every manifest asset, and every corresponding `.sigstore.json`
  sidecar.

- Verification: Focused local-release tests now assert that the synthetic local
  release index exposes the manifest and sigstore sidecars. Hosted-asset smoke
  remains the final operational close condition.

- Prevention: Keep local-release adapter tests aligned with the same asset
  contract the real verified-release path expects.

- Detected By: Local hosted-asset smoke during maintainer relaunch proof.

- Failure Signature: `KeyError: 'release-manifest.json'` or missing local
  sigstore-bundle assets while downloading a verified release or feature pack
  from localhost.

- Trigger Path: Local hosted-asset install and feature-pack staging.

- Ownership: Release asset verification adapter and maintainer release proof
  lane.

- Timeline: After the installer reached managed-runtime activation, the local
  hosted-asset path exposed that the localhost release adapter still modeled a
  narrower asset set than the verified-release logic actually requires.

- Blast Radius: Maintainer local hosted-asset proof only. Canonical GitHub
  releases already expose the full asset list through the GitHub API.

- SLO/SLA Impact: Local release proof fails even though the generated asset set
  is complete on disk.

- Data Risk: None.

- Security/Compliance: The fix preserves strict manifest and bundle validation.

- Invariant Violated: Local hosted-asset rehearsal must present the same
  effective asset contract the verified-release path expects from canonical
  hosted releases.

- Workaround: none.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not weaken verified-release checks to accommodate an
  incomplete local release adapter.

- Preflight Checks: Review this bug and the Release component spec before
  changing local hosted-asset plumbing again.

- Regression Tests Added: `tests/unit/install/test_release_assets.py`

- Monitoring Updates: none.

- Related Incidents/Bugs: `2026-03-28-generated-installer-misses-runtime-versions-directory-before-activation.md`

- Version/Build: Relaunch source line targeting restarted preview `v0.1.0`.

- Config/Flags: `ODYLITH_RELEASE_BASE_URL`

- Customer Comms: none.

- Code References: local release adapter, verified-release download path

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`

- Fix Commit/PR: Pending.
