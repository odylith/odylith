- Bug ID: CB-280

- Status: Open

- Created: 2026-07-18

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: A live GitHub source capture admitted a repository into the climate family solely because it carried the climate topic, although its retained description did not establish climate product evidence. The rejected candidate was removed; topic membership alone is insufficient source-family grounding.

- Impact: A release candidate can derive product prompts from evidence unrelated to its declared source family, making relevance claims unsound.

- Components Affected: odylith

- Environment(s): Odylith product repo, maintainer source-local release-corpus capture

- Detected By: Live GitHub source capture review

- Failure Signature: topic:climate admitted warifp/FacebookToolkit without description-level climate evidence

- Trigger Path: python3 scripts/release/greenfield_release_corpus.py capture --output-root tests/fixtures/greenfield-release-corpus

- Ownership: Greenfield release corpus capture and provenance boundary

- Timeline: Captured 2026-07-18 through `odylith bug capture`.

- Blast Radius: All source-family candidates using topic-only filtering

- SLO/SLA Impact: Blocks credible Greenfield release qualification

- Data Risk: No production data impact; test evidence integrity at risk

- Security/Compliance: No security boundary impact

- Invariant Violated: A source-family label must be grounded in retained description evidence, not topic membership alone.

- Workaround: Reject the capture and remove the candidate corpus.

- Root Cause: The eligibility predicate treated GitHub topic membership as sufficient semantic evidence.

- Solution: Require declared description evidence terms during capture and require independent source-family relevance approval before release.

- Rollback/Forward Fix: Do not publish or consume unaudited corpus artifacts; rebuild from a clean capture after the eligibility fix.

- Verification: Focused capture regression rejects topic-only evidence; release audit must independently approve source family relevance.

- Prevention: Keep a deterministic topic-only negative fixture and bind independent audit evidence to each approved case.

- Agent Guardrails: Do not infer product-domain relevance from repository topics alone.

- Preflight Checks: Evaluate every capture for description-level evidence before building case seeds.

- Regression Tests Added: test_capture_requires_description_level_family_evidence

- Related Incidents/Bugs: CB-279
