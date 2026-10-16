- Bug ID: CB-180

- Status: FixedPendingRelease

- Created: 2026-05-07

- Severity: P3

- Reproducibility: High

- Type: OperatorUX

- Description: Installer progress bar glued child output to elapsed seconds

- Impact: First-run install output could print progress text and the next renderer line on the same terminal row, for example '19smermaid catalog render passed', making the release look unpolished.

- Components Affected: installer

- Environment(s): macOS Apple Silicon local release install v0.1.15 from localhost release server.

- Detected By: Operator transcript from the 2026-05-07 end-to-end local release run.

- Failure Signature: The install progress bar rendered elapsed seconds without leaving a clean terminal boundary before child renderer stdout.

- Trigger Path: Run install.sh for a local release and let the setup progress bar overlap Mermaid/traceability renderer output.

- Ownership: Installer progress renderer and local release install transcript polish.

- Timeline: Captured 2026-05-07 through `odylith bug capture`.

- Blast Radius: First-run operator trust, release smoke transcript readability, and support debugging from install logs.

- SLO/SLA Impact: No functional outage; harms perceived release quality and makes logs harder to parse.

- Data Risk: No data risk.

- Security/Compliance: Policy and accessibility posture: terminal progress must remain readable for assistive tooling and support logs; no credential, privacy, or safety exposure.

- Invariant Violated: Installer progress output must not collide with subsequent child process output.

- Root Cause: The progress renderer updated the line without forcing a carriage-return/newline-safe boundary before child output could print.

- Solution: Render progress updates with a carriage-return boundary so subsequent child process output starts cleanly instead of gluing to elapsed text.

- Verification: PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py::test_install_progress_bar_does_not_glue_child_output_to_elapsed_seconds

- Prevention: Keep a unit transcript test for progress output followed by Mermaid renderer text.

- Regression Tests Added: tests/unit/test_cli.py::test_install_progress_bar_does_not_glue_child_output_to_elapsed_seconds

- Code References: - src/odylith/cli.py
- tests/unit/test_cli.py
