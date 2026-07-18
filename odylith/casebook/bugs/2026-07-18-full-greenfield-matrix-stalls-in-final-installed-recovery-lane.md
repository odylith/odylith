- Bug ID: CB-275

- Status: Open

- Created: 2026-07-18

- Severity: P1

- Reproducibility: Medium

- Type: Test

- Description: A 14-case installed discovery matrix completed every ordinary case with status passed, then remained in poll while the fsync rollback recovery phase waited for its installed greenfield propose child. The direct installed recovery proof passed in isolation.

- Impact: Blocks completion of the aggregate installed matrix and leaves only partial discovery evidence.

- Components Affected: domain-intelligence

- Environment(s): macOS 26.5.1, Homebrew Python 3.13.12, local release artifact 0.1.15

- Detected By: tracked installed discovery matrix and controller stack sample

- Failure Signature: greenfield_preconfirm_matrix.py waits in subprocess.communicate during _run_fsync_rollback_phase -> _compile_transaction -> installed greenfield propose after 14 ordinary cases passed

- Trigger Path: make greenfield-preconfirm-matrix VERSION=0.1.15 DIST=/tmp/odylith-local-release-0.1.15-proof-isolation

- Ownership: Greenfield installed proof orchestration

- Timeline: Captured 2026-07-18 through `odylith bug capture`.

- Blast Radius: Maintainer release and discovery proof matrix only; no customer write was attempted.

- SLO/SLA Impact: Extends release proof latency beyond bounded expectations.

- Data Risk: No governed product repository was modified by the stalled controller; its temporary evidence root was retained.

- Security/Compliance: No security or compliance impact observed.

- Invariant Violated: A complete installed matrix must finish or fail within bounded lane timeouts and emit one final proof record.

- Workaround: Run the installed recovery proof in isolation, which passed, while retaining the aggregate run for diagnosis.

- Verification: Reorder or isolate the recovery lane, then rerun the full matrix and require final aggregate recovery and cleanup records.

- Prevention: Keep recovery-lane execution independently observable and regression-test matrix ordering under retained case evidence.
