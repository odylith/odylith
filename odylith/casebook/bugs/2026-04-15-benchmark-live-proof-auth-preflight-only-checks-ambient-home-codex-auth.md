- Bug ID: CB-118

- Status: Open

- Created: 2026-04-15

- Severity: P1

- Reproducibility: Medium

- Type: Product

- Description: Benchmark live proof auth preflight only checks ambient home codex auth

- Impact: One proof shard can fail before live execution even though Codex Desktop auth exists, blocking shard merge and forcing operator forensics.

- Components Affected: benchmark

- Environment(s): Odylith product repo maintainer source-local proof lane on branch 2026/freedom/v0.1.11, Codex Desktop host with /Users/freedom/.codex/auth.json present.

- Detected By: Deep resume inspection of proof shard report 8b4a7efd1beeb118 and local filesystem auth state.

- Failure Signature: Shard 8b4a7efd1beeb118 failed with RuntimeError: Codex CLI auth is unavailable at ~/.codex/auth.json; cannot run live benchmark scenarios, while /Users/freedom/.codex/auth.json exists.

- Trigger Path: Run a live proof shard whose process environment does not resolve the operator Codex home through HOME/.codex, then enter _temporary_codex_home before launching codex exec.

- Ownership: benchmark live execution Codex auth discovery and isolated host-home setup

- Timeline: Captured 2026-04-15 through `odylith bug capture`.

- Blast Radius: Live proof shards, full-product benchmark comparison, current-head proof publication, and maintainer release gating.

- SLO/SLA Impact: Release benchmark proof can fail before scenario execution due to auth discovery drift instead of real benchmark quality.

- Data Risk: Low product-data risk; medium local credential-handling risk because auth discovery must be explicit and bounded.

- Security/Compliance: Credential copy remains local to stripped benchmark temp homes and must not broaden beyond declared Codex auth candidates.

- Invariant Violated: Live benchmark auth preflight must discover the same Codex auth source the host actually uses, without inventing hidden credentials or depending on one ambient HOME value.

- Root Cause: _temporary_codex_home resolved auth only from _user_codex_home(environ)/auth.json, which effectively assumes HOME/.codex is the only valid Codex auth root.

- Solution: Resolve Codex auth from an ordered, explicit candidate set including CODEX_HOME and Path.home()/.codex, copy only the selected local auth.json into the isolated benchmark home, and report the checked candidates when unavailable.

- Verification: Add unit coverage for CODEX_HOME fallback, Path.home fallback when HOME points at a stripped temp directory, and no hidden credential broadening.

- Prevention: Benchmark live execution must keep auth source selection explicit, local, and reportable in failure messages.

- Agent Guardrails: Do not treat a single ~/.codex lookup failure as proof that Codex auth is unavailable until CODEX_HOME and Path.home candidates are checked.

- Regression Tests Added: Benchmark live execution tests for Codex auth candidate resolution and isolated temp-home copy.

- Code References: - src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py
