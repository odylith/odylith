# Mirror Registry Concurrency Test Deadlock (Barrier Miscount)

- Bug ID: CB-001

- Status: Closed

- Created: 2026-02-15

- Fixed: 2026-02-15

- Severity: P2

- Reproducibility: Intermittent

- Type: Tooling

- Description:

  `tests/core/metrics/test_mirror_registry_concurrency.py::test_registry_hot_swap` (and the similar churn test)
  could hang indefinitely during local pre-commit `unit-tests` because the test's `threading.Barrier`
  was configured for `n_threads`, but both `n_threads` worker threads and the main thread called
  `barrier.wait()`. Depending on thread scheduling, the barrier could trip without the main thread,
  leaving the main thread stuck in the next barrier cycle forever.

- Impact:

  Local commits could hang for 10+ minutes (or indefinitely) due to the pre-commit `unit-tests` hook.
  This can also waste CI minutes if the same hang occurs under load.

- Components Affected:

  Tooling/tests only (mirror registry concurrency tests).

- Environment(s):

  Local developer machines (observed on macOS); potentially CI depending on scheduling.

- Root Cause:

  The barrier party count was incorrect: `threading.Barrier(n_threads)` was used while `n_threads + 1`
  threads (workers + main) waited on it. If all workers arrived first, the main thread would block on
  the next barrier generation and never proceed.

- Solution:

  Updated `tests/core/metrics/test_mirror_registry_concurrency.py` to:

  - Use `threading.Barrier(n_threads + 1)` in the affected tests.
  - Add a timeout and explicit failure on main-thread `barrier.wait()` to prevent indefinite hangs.

- Verification:

  - Re-ran the unit-test suite via the pre-commit `unit-tests` hook and confirmed it progressed past
    the hot-swap test without hanging.

- Prevention:

  - Use `Barrier(n_threads + 1)` whenever the main thread participates.
  - Always add timeouts to coordination primitives in tests (barriers/events/queues) so failures are
    bounded and observable rather than hanging indefinitely.

