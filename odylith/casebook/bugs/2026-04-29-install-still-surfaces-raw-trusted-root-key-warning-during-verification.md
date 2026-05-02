- Bug ID: CB-137

- Type: Product



- Status: Closed

- Created: 2026-04-29

- Severity: P1

- Reproducibility: High


- Description: Install still surfaces raw trusted-root key warning during verification

- Impact: Successful install or upgrade can still show raw Sigstore/Rich warning text for unsupported trusted-root key type 7, making a verified install look broken at the exact supply-chain trust moment.

- Components Affected: release

- Environment(s): 0.1.12 hosted install bootstrap shell and managed runtime install/upgrade verification path after B-056/CB-076 closure; consumer install output that invokes release asset verification through Sigstore.

- Detected By: Operator report on 2026-04-29 quoting WARNING Failed to load a trusted root key: unsupported trust.py:177 key type: 7 during install.

- Failure Signature: Terminal output includes raw warning text: WARNING Failed to load a trusted root key: unsupported trust.py:177 key type: 7.

- Trigger Path: hosted `install.sh`, `odylith install`, `odylith reinstall`, or `odylith upgrade` path that downloads and verifies release assets with Sigstore.

- Ownership: Release asset verifier output boundary, install lifecycle operator messaging, and trust warning telemetry.

- Timeline: Captured 2026-04-29 through `odylith bug capture`.

- Blast Radius: New enterprise and consumer adopters during first install or upgrade; maintainer release proof also loses credibility if raw verifier warnings leak.

- SLO/SLA Impact: P1 adoption and trust regression; no verification bypass or runtime outage, but install confidence is materially damaged.

- Data Risk: Low direct data risk; high operator trust risk.

- Security/Compliance: Security communication regression: strict verification still passes, but raw warning text implies a trust failure and can confuse enterprise operators.

- Invariant Violated: Successful install verification must never print raw trusted-root key warnings; benign verifier chatter must be captured as structured telemetry and reserved for doctor/version/reporting, while real failures still print full fatal details.

- Fix: Hardened both hosted install bootstrap shell verification and managed runtime release asset verification so the known Sigstore trusted-root key type 7 warning is folded across Rich/logging line wraps, including `WARNING ... trust.py:177` and unindented `key type: 7` continuations. Removed the managed install-path trust notice that reintroduced the same warning as friendly stdout; suppressed non-fatal verifier chatter is now metadata-only through `sigstore_warning_*` verification fields after managed runtime takeover.

- Hardening Follow-Up: A second QA pass expanded the invariant from stderr-only to the full install output boundary. Hosted bootstrap now captures and filters both Sigstore stdout and stderr, strips ANSI control styling before matching, suppresses the trusted-root warning even when Rich emits colored `WARNING`/`trust.py:177` fragments, and still preserves non-benign success stdout such as `OK: asset verified`. Managed runtime verification now strips ANSI control styling and classifies benign trusted-root warnings from either captured stream without replaying them during install.

- Third Hardening Follow-Up: A 2026-04-29 challenge exposed two remaining
  leak paths. First, managed Python verification could replay stderr when a
  benign trusted-root warning appeared alongside non-benign success stdout.
  Second, the hosted bootstrap failure branch still raw-catted Sigstore stdout
  and stderr before exiting. Both paths now filter benign trusted-root warning
  fragments per stream before any success or failure output is emitted, and
  split Rich labels such as `WARNING` on one line followed by the trusted-root
  message on the next line are folded and suppressed.

- Workaround: None acceptable for 0.1.12. Operators should not have to set Sigstore bypass flags or mentally ignore warning text during install.

- Rollback/Forward Fix: Forward-fix in 0.1.12; 0.1.11 stays GA and immutable.

- Agent Guardrails: Do not print normalized trusted-root warning summaries during install, upgrade, reinstall, or hosted bootstrap success paths. Reserve suppressed warning details for structured verification metadata and explicit diagnostic surfaces.

- Preflight Checks: Inspect both `scripts/release/publish_release_assets.py` and `src/odylith/install/release_assets.py` before claiming trusted-root warning suppression is fixed; the bootstrap shell and managed Python verifier are separate output boundaries.

- Regression Tests Added: `tests/unit/install/test_release_bootstrap.py` covers hosted install shell suppression for classic wrapped, Rich wrapped, ANSI-styled Rich output, stdout-emitted warnings, success stdout plus warning stderr, split `WARNING` labels, filtered failure output, and unindented trusted-root continuations while preserving non-benign success stdout and unexpected verifier warnings. `tests/unit/install/test_release_assets.py` covers managed verifier suppression for the same classes plus ANSI stripping, stdout-emitted trusted-root warnings, success stdout plus warning stderr, split `WARNING` labels, failure-detail filtering, and release download metadata-only reporting with clean stdout/stderr.

- Monitoring Updates: Watch install, reinstall, upgrade, and bootstrap failure reports for `trusted root key`, `trust.py:177`, `key type: 7`, and `Trust notice:` appearing in success-path output.

- Version/Build: Fix target 0.1.12.

- Config/Flags: Default Sigstore verification path; no bypass flags required.

- Customer Comms: Successful installs should no longer show the raw Sigstore trusted-root key warning. Real verification failures still fail closed and print actionable fatal details.

- Code References: - scripts/release/publish_release_assets.py
- src/odylith/install/release_assets.py
- tests/unit/install/test_release_bootstrap.py
- tests/unit/install/test_release_assets.py

- Related Incidents/Bugs: CB-076, B-056, CB-136.
