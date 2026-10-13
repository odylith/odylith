- Bug ID: CB-363

- Status: Open

- Created: 2026-10-13

- Severity: P1

- Reproducibility: Always

- Type: Tooling

- Description: Benchmark local clone fails from a linked source checkout across devices

- Impact: A full benchmark exits without a final report when a disposable clone cannot hardlink objects from the external Git store to internal temporary storage.

- Components Affected: benchmark

- Environment(s): v0.1.15 source-local checkpoint 11783fa0a; authorized linked proof checkout on internal storage, Git common object store on external storage.

- Detected By: Fresh full attempt a77808fd966dfb62 and one exact existing-owner reproduction.

- Failure Signature: Git clone returned128: fatal failed to create link to workspace/.git/objects: Cross-device link. Reproduction failed in0.024 seconds.

- Trigger Path: temporary_workspace_checkout uses git clone --local from the linked clean source checkout; terminal exception surfaced in singleton_family_latency_probes.

- Ownership: Existing benchmark isolation temporary checkout owner.

- Timeline: Captured 2026-10-13 through `odylith bug capture`.

- Blast Radius: Both benchmark lanes and latency probes when worktree and common object store occupy different filesystems.

- SLO/SLA Impact: Release benchmark aborted before final report; no timing or quality qualification from the failed attempt.

- Data Risk: No observed source or consumer data loss; preserve exact failed logs, report state and live dashboard publication.

- Security/Compliance: Use one explicit copy strategy; do not bypass Git safety checks, change source custody or copy ambient host state.

- Invariant Violated: Disposable benchmark checkouts must materialize verified source independently of whether filesystem hardlinks are available.

- Root Cause: The linked checkout is on device16777233 while the common Git object store is on device16777240; forced local clone attempts an invalid cross-device hardlink.

- Solution: Add the supported no-hardlinks clone option in the existing isolation owner, retaining the same source revision, snapshot overlay, stripping and cleanup contracts.

- Verification: A real Git fixture must prove equal source revision and bytes with independently copied objects; reproduce the original external-store/internal-workspace operation after the correction. Then run unchanged isolation and live execution controls before a fresh complete benchmark.

- Agent Guardrails: No retry cascade, fallback transport, validator or score changes, floor weakening, case selection change or benchmark waiver. Do not count traversed result slots as successful observations.

- Related Incidents/Bugs: CB-124; CB-361; CB-362; B-142

- Code References: - src/odylith/runtime/evaluation/odylith_benchmark_isolation.py

## Correction evidence (2026-10-13)

The failed full attempt `a77808fd966dfb62` has no final quality result. Its
original report and error log are retained in the durable release evidence
archive. One exact owner reproduction confirmed that Git tried to hardlink
objects from the external common object store into internal temporary storage
and exited 128 with a cross-device-link error.

The existing clone command now passes `--no-hardlinks`. The real Git regression
fails against the old implementation because it shares object inodes, then
passes after the correction. All 13 isolation tests and eight unchanged
source-custody controls pass. An actual cross-device checkout also passes:
HEAD, tree and source bytes match, object files are independent, the source
stays clean and the existing owner removes its temporary workspace. That
control took 10.59 seconds; it does not establish consumer latency. Independent
review found no actionable P0, P1 or P2 issue in the two-file patch.

The correction changes neither benchmark inputs nor scoring. Hosted CI and a
fresh full benchmark on the corrected committed source remain required. The
failed attempt is not regraded or counted as a successful run.
