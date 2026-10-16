- Bug ID: CB-283

- Status: Open

- Created: 2026-07-18

- Severity: P2

- Reproducibility: Always

- Type: UX

- Description: A live source-provenanced case build rendered the user-visible phrase 'Create a accessibility product'. The generator used a fixed article for source-family prompt templates.

- Impact: Generated Greenfield prompts and confirmation views can contain ungrammatical copy, reducing user trust and violating the clarity floor.

- Components Affected: odylith

- Environment(s): Odylith product repo, maintainer source-local source-corpus build

- Detected By: Live rebuilt discovery corpus review

- Failure Signature: release-accessibility-001-description rendered 'Create a accessibility product'

- Trigger Path: python3 scripts/release/greenfield_release_corpus.py build --source-manifest tests/fixtures/greenfield-release-corpus/source-manifest.v2.json

- Ownership: Greenfield release corpus prompt generator

- Timeline: Captured 2026-07-18 through `odylith bug capture`.

- Blast Radius: Operational delivery and user-trust risk across all vowel-leading source-family prompt templates

- SLO/SLA Impact: Release qualification delivery is blocked until generated copy passes the clarity floor

- Data Risk: No production data impact; generated evaluation copy is affected

- Security/Compliance: Accessibility and usability posture: malformed generated copy makes the product harder to understand

- Invariant Violated: Human-visible generated content must be grammatical and clear.

- Workaround: Do not use the malformed case file; rebuild after correcting the generator.

- Root Cause: Prompt templates hard-coded the article 'a' regardless of the source-family label.

- Solution: Derive the indefinite article deterministically from the source-family label and cover vowel-leading families.

- Rollback/Forward Fix: Discard the malformed generated case file and rebuild from retained v2 source evidence.

- Verification: Focused regression checks accessibility and open-data prompt styles; rebuilt corpus contains no 'a accessibility' or 'a open-data' prompt.

- Prevention: Keep grammar assertions for generated templates that interpolate user-visible domain labels.

- Agent Guardrails: Treat malformed user-visible copy as a release blocker, not a cosmetic note.

- Preflight Checks: Inspect generated corpus copy before audit qualification.

- Regression Tests Added: test_prompt_styles_use_correct_indefinite_articles

- Related Incidents/Bugs: CB-280, CB-281
