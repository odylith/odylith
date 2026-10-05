- Bug ID: CB-359

- Status: Open

- Created: 2026-10-05

- Severity: P2

- Reproducibility: Consistent

- Type: Tooling

- Description: During the B-142 dashboard clarity checkpoint, compass log appended an event and rendered successfully, then refused completion because runtime.code changed. Completion correctly stayed closed, but the existing abandonment command rejected the rendering phase even after exact published bytes and the original stream were restored. This stranded the maintainer checkpoint. The source fix extends only the existing exact-restoration archive path and excludes exact .DS_Store metadata from future runtime code identities.

- Impact: Maintainers cannot finish or safely discard an interrupted execution-history append through the supported CLI, delaying an otherwise verified release checkpoint.

- Components Affected: compass

- Environment(s): Odylith product repository; maintainer detached source-local; macOS; Python 3.13; branch 2026/freedom/v0.1.15; base 23881abd0e8bd15ddc64fb869b581060d50c3302.

- Detected By: Canonical compass log and completion command during the tested dashboard UX checkpoint; independent static review and root regression tests.

- Failure Signature: Successful render followed by runtime.code identity mismatch; receipt remains rendering with successor null; prior abandonment accepts only prepared/appended phases.

- Trigger Path: odylith compass log --repo-root .; an identity change after append/render causes fail-closed completion; restore exact published outputs and stream through reviewed CLI restoration; abandon-restored previously rejects rendering.

- Ownership: Compass log continuation owns runtime identity, unpublished append receipt, exact restoration and abandonment; dashboard publication owns immutable working-generation equality.

- Timeline: 2026-10-05: original append/render completed but post-render runtime.code check failed; --complete failed closed; eleven files backed up and restored through two exact reviewed restoration receipts; root 139 tests passed; independent review CLEAR; original receipt was then archived through abandon-restored.

- Blast Radius: Unpublished Compass event and eleven Compass-derived/stream files in this maintainer run. No consumer transaction or confirmed Greenfield project was changed.

- SLO/SLA Impact: Blocks history settlement and the release checkpoint. No measured production user SLO breach is claimed.

- Data Risk: Original receipt and event fingerprint must remain immutable. Recovery must preserve the published stream preimage and must not replay the failed event or claim completion.

- Security/Compliance: No credential or permission incident observed. Actual code/resource, mode, interpreter, installation, repository and publication identity checks remain strict.

- Invariant Violated: Every interrupted unpublished append must support a truthful exact-restoration terminal state without weakening completion identity or replaying an event.

- Workaround: Use the existing reviewed CLI restoration for exact failed derived outputs, then a separate stream-only restoration, then abandon-restored with the original receipt hash. Start a new event after recovery; do not replay the old append.

- Root Cause: Proved: rendering was absent from the abandonment phase allowlist despite a null successor and exact restored publication, and runtime identity included exact .DS_Store files. Original run changed only runtime.code; src/odylith/.DS_Store changed after rendering, but previous bytes were not retained, so Finder metadata is not certified as the sole cause.

- Solution: Within the existing continuation owner, permit rendering abandonment only with a null successor, exact original repository/publication and receipt, a closed stream-only restoration receipt, exact pre-stream fingerprints, and full published working-tree equality. Exclude only exact .DS_Store basenames from future code identities.

- Rollback/Forward Fix: Source patch is unshipped. Preserve the immutable original receipt under compass-log-abandonments. Ordinary completion remains strict and cannot reseal runtime identity.

- Verification: Root tests/unit/runtime/test_compass_log_continuation.py: 139 passed in 10.08s. Independent static review SHA 11e8b6185c99918d1f9d78638f7d9e5aa679057a68a2cfeb509ba53d2a47ac8e. Actual CLI abandonment passed; original receipt SHA 20dff7fd77f00c453a7155e588d32657192172dbf5d9f2bbd192035a52e50c9c preserved; stream matches its exact pre-append SHA; canonical working generation remains valid.

- Prevention: Cover interrupted rendering, stream-only restoration and all identity/publication rejection boundaries in the existing continuation tests. Keep source code stable while guarded history commands run.

- Agent Guardrails: Never edit receipt identities, reseal the failed event, replay an append, claim old completion, broadly ignore runtime resources, or attribute the original code delta solely to Finder without previous-byte evidence.

- Preflight Checks: Require canonical working generation, original unchanged receipt hash, closed exact stream-only restoration receipt, exact pre-append stream bytes/mode and null publication successor before abandonment.

- Regression Tests Added: Seven new bounded tests plus 132 inherited continuation cases: exact .DS_Store exclusion, real resource identity preservation, rendering abandonment and changed receipt/publication/stream/working-tree rejection.

- Version/Build: Unreleased 0.1.15 dashboard clarity checkpoint; source UI/browser proof does not confer shipped release qualification.

- Config/Flags: Maintainer detached source-local. No force, identity reseal, retry ladder or fallback archive.

- Related Incidents/Bugs: B-142 universal Greenfield domain intelligence; CB-303 dashboard clarity; original diagnosis report SHA 9235223de7145fcb74c008a3b5c92f48da735624d813eca7cc11aa5deed0bfa2.

- Code References: - src/odylith/runtime/common/compass_log_continuation.py
- tests/unit/runtime/test_compass_log_continuation.py
