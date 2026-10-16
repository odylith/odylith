- Bug ID: CB-282

- Status: Open

- Created: 2026-07-18

- Severity: P2

- Reproducibility: High

- Type: Tooling

- Description: A live v2 source-corpus recapture hit GitHub HTTP 403 rate limiting. The capture cleaned its staging output, but the command surfaced a Python traceback and did not use the locally available GitHub credential unless a token was manually supplied.

- Impact: Maintainers cannot reliably acquire release evidence and receive an implementation traceback instead of an actionable pre-confirm environment failure.

- Components Affected: odylith

- Environment(s): Odylith product repo, maintainer source-local live GitHub capture

- Detected By: Live source-corpus recapture

- Failure Signature: urllib.error.HTTPError: HTTP Error 403: rate limit exceeded

- Trigger Path: python3 scripts/release/greenfield_release_corpus.py capture --output-root tests/fixtures/greenfield-release-corpus

- Ownership: Greenfield release source capture boundary

- Timeline: Captured 2026-07-18 through `odylith bug capture`.

- Blast Radius: Operational release-evidence acquisition for all unauthenticated GitHub-backed source captures

- SLO/SLA Impact: Delivery is blocked until rate limit resets or authenticated access is used

- Data Risk: No production data impact; temporary capture output is cleaned

- Security/Compliance: Privacy and safety posture: the optional GitHub token is only an in-memory request header and must never appear in output or retained artifacts

- Invariant Violated: Source acquisition must fail with an actionable environment message and leave no partial corpus.

- Workaround: Use a locally authenticated GitHub token through GITHUB_TOKEN for the read-only capture.

- Root Cause: The fetcher omitted optional token authentication and let HTTPError escape without domain-level handling.

- Solution: Read GITHUB_TOKEN only into the request Authorization header and translate rate-limit responses into a bounded RuntimeError.

- Rollback/Forward Fix: Do not use partially captured output; retry a clean capture after the preflight environment condition is resolved.

- Verification: Focused regression proves token header use, clear rate-limit message, and clean staging behavior.

- Prevention: Keep capture failures at the evidence-acquisition boundary; never expose raw implementation tracebacks to operators.

- Agent Guardrails: Do not claim source acquisition succeeded after a rate-limit response or retain partial capture state.

- Preflight Checks: Check authenticated GitHub API availability before a live release-corpus capture.

- Regression Tests Added: test_fetch_reports_rate_limits_and_uses_an_available_github_token

- Related Incidents/Bugs: CB-280, CB-281
