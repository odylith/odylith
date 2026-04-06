- Bug ID: CB-012

- Status: Open

- Created: 2026-03-28

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The hosted installer's localhost allowlist accepted
  `http://127.0.0.1/...` and similar URLs without a port, but the local
  maintainer release-smoke server publishes assets from
  `http://127.0.0.1:<port>/...`. The installer therefore treated the local
  rehearsal URL as a normal insecure HTTP endpoint and handed it to curl with
  HTTPS-only protocol constraints.

- Impact: The local hosted-asset smoke failed before the first install could
  fetch the bootstrap runtime, which weakened the new pre-dispatch proof gate.

- Components Affected: hosted installer allowlist logic, local maintainer
  release smoke, release preflight proof lane.

- Environment(s): local maintainer hosted-asset rehearsal using the generated
  install script and a localhost HTTP server.

- Root Cause: The install script's shell pattern for allowed localhost URLs did
  not include `host:port` forms.

- Solution: Expand the localhost allowlist to accept `127.0.0.1`,
  `localhost`, and `[::1]` with or without an explicit port before falling
  back to the HTTPS-only curl path.

- Verification: The generated installer script now includes port-aware
  localhost patterns. The local hosted-asset smoke remains the final
  operational close condition for this bug.

- Prevention: Keep install-script localhost allowlist tests aligned with the
  real URL shape produced by the local release-smoke server.

- Detected By: Local hosted-asset smoke during maintainer relaunch proof.

- Failure Signature: `curl: (1) Protocol "http" disabled` while fetching
  localhost-hosted release assets during local installer rehearsal.

- Trigger Path: local hosted-asset smoke against generated release assets.

- Ownership: Hosted installer contract and maintainer release proof lane.

- Timeline: The new local hosted-asset proof gate surfaced that the installer
  still treated localhost-with-port rehearsal URLs as if they were ordinary
  remote HTTP endpoints.

- Blast Radius: Maintainer local hosted-asset proof only. Canonical GitHub
  release assets remain HTTPS-hosted.

- SLO/SLA Impact: Maintainer release proof loses determinism until localhost
  rehearsal URLs are accepted.

- Data Risk: None.

- Security/Compliance: The change is limited to localhost rehearsal URLs and
  does not relax the HTTPS requirement for normal hosted release assets.

- Invariant Violated: Local hosted-asset rehearsal should exercise the
  installer contract without being blocked by the rehearsal server's port.

- Workaround: none beyond manually editing the generated installer.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not broaden the HTTP allowlist beyond localhost
  rehearsal endpoints.

- Preflight Checks: Review this bug and the Release component spec before
  widening installer URL allowlists again.

- Regression Tests Added: `tests/unit/install/test_release_bootstrap.py`

- Monitoring Updates: none.

- Related Incidents/Bugs: `2026-03-28-local-macos-release-build-fails-when-linux-runtime-archive-is-expanded-on-case-insensitive-fs.md`

- Version/Build: Relaunch source line targeting restarted preview `v0.1.0`.

- Config/Flags: `ODYLITH_RELEASE_BASE_URL`,
  `ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST`

- Customer Comms: none. This is a maintainer-only rehearsal bug.

- Code References: hosted installer generator, local release smoke helper

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`

- Fix Commit/PR: Pending.
