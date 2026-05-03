- Bug ID: CB-142

- Type: Product








- Status: FixedPendingRelease

- Created: 2026-04-30

- Severity: P1

- Reproducibility: High


- Description: Generated Python host assets break consumer Ruff lint

- Impact: Consumer repos that run strict `ruff check .` after Odylith install fail on Odylith-managed `.agents/bin/*.py` and `.claude/hooks/*.py` files before reaching their own application lint signal.

- Components Affected: migration-runtime

- Environment(s): Odylith 0.1.11 consumer install in /Users/freedom/code/dentoai-isb with Python 3.13 and Ruff configured for E,F,I,B,C4,S,UP,T100,TYP,D.

- Detected By: Direct consumer-repo audit after operator reported first-run install failures

- Failure Signature: `ruff check .` reports 86 errors under `.agents/bin/odylith-host-launcher.py` and `.claude/hooks/*.py`, including I001, D103, E501, S603, S607, S105, and UP035, before app lint failures.

- Trigger Path: Install Odylith into a Python consumer repo, then run `ruff check .` or the repo lint script over the repository root.

- Ownership: Install-managed project-root host assets

- Timeline: 2026-04-29: dentoai-isb 0.1.11 consumer repo audit ran `.venv/bin/python -m ruff check .`; generated Odylith Python host assets produced the first 86 lint errors. 2026-04-30: v0.1.12 branch added file-level Ruff suppression to generated Python host assets and bundle mirrors.

- Blast Radius: Consumer repos with repo-wide Python lint commands that include hidden project-root assets after Odylith install.

- SLO/SLA Impact: P1 onboarding and CI hygiene regression: Odylith install can make an otherwise targeted lint command fail on managed integration shims.

- Data Risk: Low

- Security/Compliance: No direct security exposure; security-lint rules can still produce false-positive noise on managed hook dispatchers.

- Invariant Violated: Odylith-managed host integration files must not pollute or fail the consumer repo's own application lint surface.

- Workaround: Run Ruff only on application paths, e.g. `ruff check dentoai_isb pyproject.toml`, until upgrading to 0.1.12.

- Root Cause: Generated project-root Python shims were copied into `.agents/` and `.claude/hooks/` without a file-level Ruff suppression, so consumer repo lint configs treated Odylith-managed integration code as application-owned Python.

- Solution: Add `# ruff: noqa` immediately after the shebang in every generated Python host hook and launcher template, and keep live product-repo mirrors byte-for-byte aligned with the bundled project-root assets.

- Rollback/Forward Fix: Forward-fix in 0.1.12; do not mutate consumer app Ruff config or exclude Odylith paths in user projects.

- Verification: `/Users/freedom/code/dentoai-isb/.venv/bin/python -m ruff check /Users/freedom/code/odylith/src/odylith/bundle/assets/project-root/.agents /Users/freedom/code/odylith/src/odylith/bundle/assets/project-root/.claude/hooks --config /Users/freedom/code/dentoai-isb/pyproject.toml` reports `All checks passed!`.

- Prevention: Keep generated project-root Python host assets marked as managed shims, and test that both bundled assets and live product mirrors start with shebang plus `# ruff: noqa`.

- Regression Tests Added: tests/unit/install/test_codex_project_assets.py::test_generated_python_project_assets_do_not_pollute_host_ruff_lint

- Monitoring Updates: Watch first-run consumer audits for repo-wide lint failures under `.agents/` or `.claude/hooks/`.

- Version/Build: Observed in Odylith 0.1.11 consumer install; fixed pending 0.1.12.

- Customer Comms: Tell affected operators this is managed Odylith hook lint noise, not their app code; upgrade to 0.1.12 instead of editing app Ruff config.

- Related Incidents/Bugs: Related to CB-139, CB-140, and CB-141 as first-run 0.1.11 trust failures.

- Code References: - src/odylith/bundle/assets/project-root/.agents/bin/odylith-host-launcher.py
- src/odylith/bundle/assets/project-root/.claude/hooks/odylith_claude_support.py
- tests/unit/install/test_codex_project_assets.py
