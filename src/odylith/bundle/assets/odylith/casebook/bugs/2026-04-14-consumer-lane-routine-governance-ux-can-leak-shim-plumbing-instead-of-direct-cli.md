- Bug ID: CB-111

- Status: Closed

- Created: 2026-04-14

- Severity: P2

- Reproducibility: High

- Type: Product

- Description: Consumer-lane routine governance UX could still leak backend
  plumbing because forwarded Atlas help surfaced `cli.py` / `__main__.py`
  usage strings and an internal refresh-wrapper description instead of the
  public `odylith atlas ...` contract.

- Impact: The first obvious consumer-lane path still felt broken after the
  broader simplification work landed. Operators reaching for `odylith atlas
  render --help` or related Atlas help surfaces saw backend filenames and
  wrapper-specific copy instead of a crisp top-level command contract, which
  made the lane feel internal, brittle, and slower to trust.

- Components Affected: `src/odylith/runtime/surfaces/scaffold_mermaid_diagram.py`,
  `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`,
  `src/odylith/runtime/surfaces/render_mermaid_catalog.py`,
  `src/odylith/runtime/surfaces/render_mermaid_catalog_refresh.py`,
  `src/odylith/runtime/surfaces/install_mermaid_autosync_hook.py`,
  `tests/unit/test_cli.py`, and consumer-lane CLI help UX under `B-088`.

- Environment(s): Product-repo maintainer mode and consumer repos invoking the
  Atlas command family through top-level `odylith ... --help`.

- Root Cause: The forwarded-help fix from `CB-110` covered the right command
  families, but several Atlas backend parsers still relied on argparse
  defaults for `prog`, so the top-level help surface inherited `cli.py` or
  `__main__.py`. `odylith atlas render` also routes through the lightweight
  `render_mermaid_catalog_refresh` proxy, and that proxy still described the
  internal skip-wrapper behavior instead of the public render contract.

- Solution: Set explicit public `prog` values on the Atlas backend parsers,
  align the `render_mermaid_catalog_refresh` help description and option help
  text with the public `odylith atlas render` contract, add regression tests
  that assert the real top-level usage strings and forbid the internal
  refresh-wrapper copy from leaking back into `--help`, and tighten the host
  guidance so Codex and Claude share one default lane while Codex-only advice
  is limited to capability-gated optimizations like
  `odylith codex compatibility`.

- Verification: `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py -k
  'bug_capture_help_forwards_backend_flags or compass_log_help_forwards_backend_flags or backlog_create_help_forwards_backend_flags or component_register_help_forwards_backend_flags or atlas_scaffold_help_forwards_backend_flags or atlas_render_help_forwards_backend_flags or atlas_auto_update_help_forwards_backend_flags or atlas_install_autosync_hook_help_forwards_backend_flags'`
  plus live smoke checks for `PYTHONPATH=src python3 -m odylith.cli atlas
  scaffold --help`, `atlas render --help`, `atlas auto-update --help`, and
  `atlas install-autosync-hook --help` all passed on 2026-04-14.

- Prevention: Any forwarded subcommand or lazy proxy that owns public help must
  pin the public command name and user-facing description explicitly. Tests
  should assert the rendered `usage:` line for common consumer-lane commands,
  not just the presence of backend flags. Host guidance should stay shared by
  default across Codex and Claude Code, and only surface Codex-specific tips
  when a proven native capability materially reduces hops.

- Detected By: `odylith show`

- Failure Signature: `odylith atlas render --help` showing `usage: cli.py` or
  `usage: __main__.py`, and the description `Skip current Atlas rerenders
  before importing the full renderer.` leaking into the public help surface.

- Trigger Path: `odylith atlas render --help`, `odylith atlas scaffold
  --help`, `odylith atlas auto-update --help`, and
  `odylith atlas install-autosync-hook --help`.

- Ownership: product

- Timeline: Captured 2026-04-14 through `odylith bug capture`.

- Blast Radius: Consumer-lane Atlas discoverability, operator trust in the
  truthful-help contract, and the “one direct CLI hop” UX for routine governed
  work.

- SLO/SLA Impact: Low-to-medium operator-latency and confidence impact on a
  common entrypoint.

- Data Risk: Low.

- Security/Compliance: No direct security impact.

- Invariant Violated: Public forwarded help must look like the public command,
  not a backend filename or an internal wrapper implementation detail.
