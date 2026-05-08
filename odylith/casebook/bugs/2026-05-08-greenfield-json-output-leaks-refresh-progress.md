- Bug ID: CB-185

- Status: FixedPendingRelease

- Created: 2026-05-08

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: The greenfield apply/create JSON contract was not release-safe: real refresh subprocess output could write before the serialized result, so the command looked successful to a human but failed machine parsing. This directly affects the greenfield release smoke and any host workflow that consumes canonical apply output.

- Impact: Delivery risk: release smoke and host agents cannot safely parse greenfield create/apply JSON output; a successful create can still fail automation and hide whether Tribunal, Radar, Registry, Atlas, and Compass actually landed.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo dev lane, PYTHONPATH=src, seeded consumer repo copied from bundle assets.

- Detected By: Aggressive greenfield CLI smoke during CB-184 hardening.

- Failure Signature: json.tool fails because stdout begins with refresh progress such as 'wrote delivery intelligence artifact' before the JSON object.

- Trigger Path: Run greenfield create --json against a seeded consumer repo with real surface refresh enabled.

- Ownership: Domain Intelligence owns greenfield apply/create CLI output; owned-surface refresh and render helpers may emit progress internally.

- Timeline: 2026-05-08: real CLI smoke found refresh progress before JSON; fd-level stdout capture added for JSON apply/create.

- Blast Radius: Machine consumers of greenfield apply/create --json, release smoke, Claude/Codex host workflows, and future CI that pipes canonical apply output.

- SLO/SLA Impact: Automation correctness regression: parseable-output success rate for greenfield --json drops to zero when refresh emits progress; no data loss.

- Data Risk: Low data risk: the leaked output is local governance/render progress, but it can expose local temp paths and makes audit payload capture unreliable.

- Security/Compliance: Security posture: no secret exposure observed, but machine-readable audit output is part of the release validation boundary; stdout must be deterministic, parseable, and free of mixed human progress text so downstream validators cannot misread a partial apply as trusted evidence.

- Invariant Violated: --json commands must emit exactly one parseable JSON document on stdout; human progress belongs in captured operator_output or stderr, not before the JSON document.

- Root Cause: JSON mode captured Python print output in unit tests but did not redirect process fd 1, so subprocess/render progress could bypass the JSON serializer.

- Solution: Wrap greenfield apply/create JSON execution in fd-level stdout capture; expose captured progress as operator_output and emit one JSON document or JSON error.

- Rollback/Forward Fix: Forward fix only; reverting would restore unparsable --json output.

- Verification: PYTHONPATH=src pytest -q tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_json_output_is_machine_clean tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_json_error_is_machine_clean; real CLI create --json parses with json.tool.

- Prevention: Keep fd-level noisy-output regression coverage for greenfield JSON mode.

- Agent Guardrails: Do not claim --json is machine-readable unless a real-refresh smoke parses stdout as JSON.

- Preflight Checks: Seed consumer repo, run greenfield create --json with real refresh enabled, parse stdout with json.tool.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py covers Python print and fd-level stdout noise during greenfield JSON apply.

- Monitoring Updates: None; this is a CLI contract regression pinned by tests.

- Version/Build: v0.1.15 dev

- Config/Flags: PYTHONPATH=src

- Customer Comms: Internal release hardening before next local dist.

- Related Incidents/Bugs: CB-184

- GitHub Status: not filed

- Public Response: No public response until release notes.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_proposals.py

- Runbook References: - odylith/registry/source/components/domain-intelligence/CURRENT_SPEC.md
