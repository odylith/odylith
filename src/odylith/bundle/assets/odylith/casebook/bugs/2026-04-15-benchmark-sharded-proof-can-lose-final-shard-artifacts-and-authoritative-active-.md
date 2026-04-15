- Bug ID: CB-113

- Status: Open

- Created: 2026-04-15

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The sharded `proof` benchmark lane can finish or abandon shard work
  without leaving the authoritative final shard artifact. During the 12-way
  `0.1.11` benchmark proof run, shards `1/12`, `7/12`, and `12/12` exited
  after real live work with no remaining parent process, no active-run ledger,
  no shard progress payload, and no final shard history report. That leaves the
  benchmark lane with partial shard truth and no safe way to merge or publish a
  canonical proof result.

- Impact: Maintainers cannot trust sharded proof execution as a release-safe
  benchmark path when a shard can disappear after doing real work without
  leaving a final report or a recoverable progress artifact. That blocks
  publication, blocks release proof closeout, and turns benchmark progress into
  an operator-forensics problem instead of a fail-closed product lane.

- Components Affected:
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  benchmark shard progress lifecycle, active-run ledger maintenance, shard
  teardown/finalization, benchmark publication proof.

- Environment(s): Odylith product repo maintainer mode, detached `source-local`,
  branch `2026/freedom/v0.1.11`, macOS Apple Silicon, sharded proof benchmark
  execution for `0.1.11`.

- Root Cause: The benchmark runner had two coupled lifecycle weaknesses. First,
  the shared active-run ledger used an unsafe read-modify-write path under
  concurrent shard updates, so live shard authority could be clobbered even
  while shard progress files were still fresh. Second, shard teardown could
  remove the only remaining progress artifact before a matching history report
  was guaranteed to exist. When a shard exited during that window, there was no
  authoritative active-run entry, no progress checkpoint, and no final shard
  report left behind.

- Solution: Treat shard progress as the durable recovery journal until a
  matching history report is present. Keep the active-run ledger under an
  explicit lock, rebuild live authority from per-shard progress files when the
  ledger is missing, persist shard history reports before any alias/latest
  publication work, and synthesize failed shard reports from orphaned progress
  or stale ledger rows when a process exits before final report persistence.

- Verification:
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py`
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_live_execution.py tests/unit/runtime/test_odylith_benchmark_prompt_payloads.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_shard_merge.py tests/unit/runtime/test_odylith_benchmark_publication.py tests/unit/runtime/test_odylith_benchmark_context_engine.py`
  - rerun benchmark diagnostic and a real sharded proof slice on the live
    source tree and confirm that every shard finishes with either a final shard
    report or a synthesized failed artifact, never silence.

- Prevention: A shard may only discard its progress checkpoint after a matching
  history report exists. Any stale running shard state with a dead owning
  process must synthesize a failed history report before cleanup. The
  active-run ledger is advisory convenience only; per-shard progress files are
  the durable recovery source until final report persistence succeeds.

- Detected By: Maintainer investigation while recovering the `B-093` benchmark
  proof lane after a 12-way sharded `proof` run stalled at `9/12` final shard
  reports.

- Failure Signature: The last live shard parents disappear, `active-runs.v1.json`
  vanishes or empties, no final history report exists for the affected shard
  report ids, and no `progress-*.json` file remains to explain what the shard
  was doing when it exited.

- Trigger Path:
  `odylith benchmark --repo-root . --profile proof --shard-count 12 --shard-index <n>`

- Ownership: benchmark runner lifecycle and proof publication truth.

- Timeline: Captured 2026-04-15 through `odylith bug capture`.

- Blast Radius: Benchmark proof truth, release-safe benchmark publication,
  sharded proof operational feasibility, and maintainer trust in benchmark
  status surfaces.

- SLO/SLA Impact: No external customer outage, but a direct P0 maintainer
  release-proof blocker.

- Data Risk: Low product-data risk, high benchmark-truth risk because
  authoritative proof state can disappear after real work.

- Security/Compliance: None directly.

- Invariant Violated: Every benchmark shard must leave one authoritative
  terminal artifact: either a final shard report or a failed shard report.
  Shard teardown must not erase the only remaining evidence of an unfinished
  or failed proof slice.

- Related Incidents/Bugs:
  [2026-04-08-pinned-dogfood-proof-benchmark-can-wedge-mid-corpus-and-block-release-proof.md](2026-04-08-pinned-dogfood-proof-benchmark-can-wedge-mid-corpus-and-block-release-proof.md)
  [2026-04-12-benchmark-live-preflight-evidence-is-only-injected-for-odylith-on-without-a-declared-comparison-contract.md](2026-04-12-benchmark-live-preflight-evidence-is-only-injected-for-odylith-on-without-a-declared-comparison-contract.md)
  [2026-04-12-benchmark-live-observed-path-scoring-credits-odylith-prompt-surfaces-but-not-equivalent-raw-prompt-anchors.md](2026-04-12-benchmark-live-observed-path-scoring-credits-odylith-prompt-surfaces-but-not-equivalent-raw-prompt-anchors.md)
