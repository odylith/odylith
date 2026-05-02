- Bug ID: CB-153

- Status: FixedPendingRelease

- Created: 2026-05-02

- Fixed: Pending

- Severity: P2

- Reproducibility: Consistent

- Type: UX

- Description: Casebook detail view leaves excessive left gutter

- Impact: Casebook detail pages waste horizontal space before the bug summary and action chips, making the selected bug detail feel misaligned and harder to scan.

- Components Affected: casebook

- Environment(s): Casebook browser dashboard during v0.1.13 UI proof.

- Detected By: Operator screenshot from 2026-05-02 showing excess left whitespace in the Casebook selected bug detail area.

- Failure Signature: The detail summary and Source markdown action start too far from the left edge of the detail panel.

- Trigger Path: Open the Casebook dashboard, select a bug, and inspect the selected bug detail pane.

- Ownership: Casebook browser renderer layout.

- Timeline: Captured and fixed during the 2026-05-02 v0.1.13 Casebook UI hardening pass.

- Blast Radius: Operators using the Casebook dashboard in installed or product-repo views.

- SLO/SLA Impact: Low direct SLO impact; dashboard scan efficiency and trust regression.

- Data Risk: None.

- Security/Compliance: No direct security or compliance impact.

- Invariant Violated: Casebook detail content should use a compact, intentional gutter and should not depend on CSS parser error recovery for its effective padding.

- Root Cause: The Casebook shell and detail pane used a loose horizontal gutter, and the mobile detail padding rule was outside its intended media block because of a stray brace.

- Solution: Tighten the Casebook shell and detail-pane horizontal padding, repair the media block, regenerate live and bundled Casebook HTML, and add headless browser assertions for the detail gutter.

- Rollback/Forward Fix: Forward-fix in v0.1.13; do not restore the wider Casebook gutter or the broken media-block shape.

- Verification: PYTHONPATH=src .venv/bin/python -m pytest -q tests/integration/runtime/test_casebook_list_layout_browser.py tests/integration/runtime/test_casebook_sort_browser.py; git diff --check.

- Prevention: Keep browser layout tests measuring the Casebook detail left gutter on desktop and compact view.

- Agent Guardrails: Do not change dashboard spacing by screenshot guesswork alone; measure the rendered panel and content offsets in headless browser tests.

- Preflight Checks: Inspect the Casebook renderer and browser layout tests before changing Casebook detail spacing again.

- Regression Tests Added: tests/integration/runtime/test_casebook_list_layout_browser.py::test_casebook_detail_uses_compact_left_gutter_on_desktop; tests/integration/runtime/test_casebook_list_layout_browser.py::test_casebook_detail_uses_compact_left_gutter_in_compact_view

- Monitoring Updates: Watch Casebook screenshots and browser layout audits for oversized gutters or CSS parser recovery around media blocks.

- Version/Build: 0.1.13 target release

- Config/Flags: Default Casebook browser dashboard rendering.

- Customer Comms: No separate customer communication needed beyond v0.1.13 dashboard polish notes.

- Related Incidents/Bugs: CB-150

- Fixed In: v0.1.13

- Code References: - src/odylith/runtime/surfaces/render_casebook_dashboard.py
- tests/integration/runtime/test_casebook_list_layout_browser.py
