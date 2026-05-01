- Bug ID: CB-148

- Type: Product


- Status: Open

- Created: 2026-05-01

- Severity: P1

- Reproducibility: High


- Description: Bootstrap doctor repair still surfaces trusted-root warning noise

- Impact: During bootstrap doctor repair, operators still see raw Sigstore trusted-root warning text interleaved with OK lines, making a successful repair look partially untrusted.

- Components Affected: release

- Environment(s): Consumer repo on v0.1.12 pinned_release during Claude Code migration repair; ./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair verifies cached release assets.

- Detected By: Operator transcript from 2026-05-01 migration feedback showing repeated WARNING Failed to load a trusted root key: unsupported trust.py:177 key type: 7 around OK release asset lines.

- Failure Signature: [10:18:47] WARNING Failed to load a trusted root key: unsupported trust.py:177 followed by key type: 7 while Sigstore also prints OK: /path/to/release-manifest.json and related release assets.

- Trigger Path: ./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair in a consumer repo with cached v0.1.12 release artifacts.

- Ownership: Release asset verification output boundary shared by hosted bootstrap, managed verifier, and bootstrap doctor repair UX.

- Timeline: Captured 2026-05-01 through `odylith bug capture`.

- Blast Radius: Consumer repair and migration sessions that verify release artifacts through Sigstore while the local Sigstore/TUF trusted-root loader emits unsupported key type 7 warnings.

- SLO/SLA Impact: Migration confidence and supportability regression; repair can complete but the transcript suggests a trust failure at the supply-chain verification step.

- Data Risk: Low direct data risk; the observed issue is verifier-output hygiene, not evidence of data exposure.

- Security/Compliance: Security communication risk: benign verifier chatter appears as raw warning text during a successful trust path, obscuring the distinction between non-fatal trusted-root loader noise and real verification failure.

- Invariant Violated: Successful install, upgrade, reinstall, and bootstrap doctor repair paths must not print raw trusted-root key warnings; benign verifier chatter must be suppressed or recorded as structured metadata while fatal verification failures stay visible.

- Root Cause: The v0.1.12 repair transcript shows a timestamped Rich/Sigstore warning plus OK stdout shape that was not explicitly covered by the released verification-output regression matrix.

- Solution: Carry exact regression coverage for timestamped trusted-root warning lines with Sigstore OK stdout in both the managed Python verifier and generated hosted bootstrap verifier; keep existing suppression behavior in v0.1.13.

- Rollback/Forward Fix: Forward-fix in v0.1.13; do not bypass Sigstore verification or silence fatal verifier output.

- Verification: pytest -q tests/unit/install/test_release_assets.py::test_verify_sigstore_asset_suppresses_timestamped_trusted_root_warning_with_sigstore_ok_stdout tests/unit/install/test_release_bootstrap.py::test_generated_install_script_verify_sigstore_identity_suppresses_timestamped_warning_with_ok_stdout

- Prevention: Keep exact transcript-shaped tests for timestamped WARNING plus trusted-root continuation and Sigstore OK stdout in both verifier output boundaries.

- Regression Tests Added: Added timestamped trusted-root warning plus OK stdout coverage in tests/unit/install/test_release_assets.py and tests/unit/install/test_release_bootstrap.py.

- Monitoring Updates: Watch install, reinstall, upgrade, and bootstrap doctor repair transcripts for trusted root key, trust.py:177, key type: 7, and raw Sigstore OK/warning interleaving.

- Version/Build: Observed on v0.1.12; fix target v0.1.13.

- Config/Flags: Default Sigstore verification path; no bypass flags.

- Customer Comms: A successful repair may have completed despite the v0.1.12 warning noise, but v0.1.13 should keep that benign trusted-root warning out of repair transcripts.

- Related Incidents/Bugs: CB-137 is the original trusted-root warning noise bug; this record captures the later bootstrap doctor repair transcript shape.

- Fixed In: v0.1.13

- Code References: - tests/unit/install/test_release_assets.py
- tests/unit/install/test_release_bootstrap.py
- src/odylith/install/release_assets.py
- scripts/release/publish_release_assets.py
