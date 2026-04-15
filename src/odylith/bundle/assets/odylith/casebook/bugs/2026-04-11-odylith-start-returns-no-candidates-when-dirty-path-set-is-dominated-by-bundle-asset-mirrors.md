- Bug ID: CB-102

- Status: Resolved

- Created: 2026-04-11

- Updated: 2026-04-11

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: `odylith start --repo-root .` returns exit code 1 with
  `selection_state: none`, `selection_reason: "No workstream evidence
  matched the current changed-path set."`, `lane: fallback`, and
  `ambiguity_class: no_candidates` when the dirty path set contains a
  nested git worktree tree (for example `.claude/worktrees/<slug>` or a
  bundled copy of one under
  `src/odylith/bundle/assets/project-root/.claude/worktrees/<slug>`) or
  dotfile directories such as `.claude/…` or `.codex/…`. The underlying
  cause is two latent bugs in the path-normalization pipeline plus a
  missing nested-worktree filter, not a missing secondary signal as the
  original framing of this bug assumed.

- Impact: Agents following the AGENTS.md startup contract receive a
  degraded bootstrap packet and a fallback lane instead of the active
  workstream context. The `narrowing_required: true` guidance forces additional
  manual context lookup steps that should not be needed when a clear in-progress
  workstream is already active.

- Components Affected:
  `src/odylith/runtime/governance/agent_governance_intelligence.py`
  (`_changed_path_aliases`, `normalize_changed_paths`,
  `collect_git_changed_paths`),
  `src/odylith/runtime/common/consumer_profile.py`
  (`_legacy_product_token_alias`),
  `./.odylith/bin/odylith start` command, and every downstream consumer
  of `normalize_repo_token` and the changed-path fan-out pipeline.

- Environment(s): Odylith product repo maintainer mode, branch
  `2026/freedom/v0.1.11`, repo state with a registered nested git worktree
  under `.claude/worktrees/funny-leavitt` and an accidental bundled copy
  of that worktree under
  `src/odylith/bundle/assets/project-root/.claude/worktrees/funny-leavitt`
  carrying a `gitdir:` marker. The bug reproduces on any repo that
  carries a real dotfile directory in its changed-path set (`.claude`,
  `.codex`, `.github`, `.vscode`) even without a nested worktree.

- Root Cause: Two latent bugs in the path-normalization pipeline plus a
  missing nested-worktree guard.
  1. `str.lstrip("./")` is a broken idiom. `lstrip` takes a character
     set, not a prefix, so `.claude/worktrees/funny-leavitt`.lstrip("./")
     returns `claude/worktrees/funny-leavitt`. The broken call site in
     `_legacy_product_token_alias` (in `consumer_profile.py`) sits
     upstream of every `normalize_repo_token` call, so it silently
     mangles every dotfile directory before the token ever reaches the
     changed-path pipeline. Two more broken call sites in
     `agent_governance_intelligence.py` (`_changed_path_aliases` and
     `normalize_changed_paths`) re-mangle the token on each subsequent
     normalization pass, so the same dotfile path can fan out into
     multiple non-dotfile variants.
  2. `collect_git_changed_paths` had no nested-worktree guard. When an
     accidental bundled copy of a git worktree was committed (or left
     untracked) inside the repo, git-status emitted the top-level
     directory as a single untracked entry, and the path-alias fan-out
     in `_changed_path_aliases` multiplied that into a source mirror
     alias plus a project-root mirror alias, all of which then got
     dot-stripped on the next normalization pass.
  3. The combined effect: a single filesystem mistake (one nested
     worktree copy under the bundle tree) produced three unrelated
     changed-path entries — `src/odylith/bundle/assets/project-root/.claude/worktrees/funny-leavitt`,
     `.claude/worktrees/funny-leavitt`, and the dot-stripped
     `claude/worktrees/funny-leavitt` — zero of which matched any
     workstream anchor. The start bootstrap correctly returned
     `selection_state: none` because no real workstream evidence was
     in the dirty set; the symptom looked like a missing secondary
     signal but the underlying pathology was upstream path corruption
     and missing nested-worktree filtering.

- Solution (Shipped): Land the forward fix as B-086 Governance Path
  Normalization Hardening And Nested Worktree Guard.
  1. Add a private `_strip_current_dir_prefix(token)` helper in
     `agent_governance_intelligence.py` that only peels a literal `./`
     prefix, with an inline docstring warning about the broken
     `lstrip("./")` idiom. Use it in `_changed_path_aliases` and in
     `normalize_changed_paths` in place of the broken idiom.
  2. Fix `_legacy_product_token_alias` in `consumer_profile.py` to use
     an explicit `startswith("./")` prefix check with the same warning
     comment.
  3. Add a private `_is_nested_git_worktree_path` helper that walks the
     candidate path and each of its ancestors up to (but excluding)
     the repo root and returns True when any of them carry a `.git`
     marker (directory or `gitdir:` text file). Call it in
     `collect_git_changed_paths` so paths under a nested worktree are
     skipped before normalization.
  4. Clean up the funny-leavitt worktree accident:
     `git worktree remove --force .claude/worktrees/funny-leavitt`,
     `git worktree prune`, `rmdir .claude/worktrees`, and
     `git clean -fd src/odylith/bundle/assets/project-root/.claude/worktrees/`.
  5. Add three characterization tests in
     `tests/unit/runtime/test_agent_governance_intelligence.py`
     covering dotfile-preserving normalization, bundle-mirror alias
     fan-out without the broken variant, and nested-worktree
     filtering.

- Verification: Reproduce pre-fix by running `./.odylith/bin/odylith start
  --repo-root .` against a repo state that contains a nested git worktree
  under `.claude/worktrees/<slug>` or a bundled copy of one under
  `src/odylith/bundle/assets/project-root/.claude/worktrees/<slug>`.
  Pre-fix behavior: exit code 1, `lane: fallback`, `selection_state:
  none`, and three phantom `changed_paths` entries (the source mirror
  path, the correctly-stripped alias, and a dot-stripped broken variant
  such as `claude/worktrees/<slug>`).

  Post-fix: `./.odylith/bin/odylith start --repo-root .` returns exit
  code 0 with `lane: bootstrap`, `selection_state: inferred_confident`,
  `selection_confidence: high`, `precision_score >= 60`, and a
  `changed_paths` set that contains only the real source edits. No
  nested-worktree entries, no dot-stripped variants. Verified locally on
  branch `2026/freedom/v0.1.11` on 2026-04-11.

- Prevention: Workstream inference must have at least one secondary signal path
  that activates when changed-path matching produces `no_candidates` on a
  known bundle-mirror or surface-output dirty tree pattern.

- Detected By: Running `odylith start --repo-root .` during B-083 Atlas diagram
  authoring on 2026-04-11, with branch `2026/freedom/v0.1.11` carrying a broad
  sync-pass dirty tree.

- Failure Signature: `odylith start` returns exit code 1, `selection_state: none`,
  `ambiguity_class: no_candidates`, and `narrowing_required: true` despite an
  active in-progress workstream and a non-empty dirty path set.

- Trigger Path: Any `odylith start` invocation after a broad surface sync or
  bundle render pass that marks managed output files dirty without touching
  the workstream-registered source files.

- Ownership: `workstream_inference.py`, `odylith_context_engine.py`, start
  bootstrap signal resolution.

- Blast Radius: Every agent turn that follows the `odylith start` startup
  contract on a repo with a broad dirty surface tree. Affected agents receive a
  fallback bootstrap instead of an active workstream packet, increasing the
  chance of ungrounded repo scan as the first action.

- SLO/SLA Impact: No data loss. Workflow degradation — agents must run a manual
  `odylith context <ref>` step to recover grounding that the start command
  should have provided automatically.

- Data Risk: Low.

- Security/Compliance: Low.

- Invariant Violated: `odylith start` should resolve to the active workstream
  when one is unambiguous from Compass, session, or plan signals, regardless of
  whether the dirty path set contains workstream-registered source files.

- Workaround: Run `./.odylith/bin/odylith context --repo-root . <workstream-id>`
  explicitly after a failed start to recover the active workstream packet.

- Rollback/Forward Fix: Forward fix — extend start bootstrap to use secondary
  signals when changed-path matching returns no_candidates.

- Agent Guardrails: If `odylith start` returns `selection_state: none`, run
  `odylith context --repo-root . <ref>` with the known active workstream id
  before proceeding to raw repo scan.

- Preflight Checks: Before diagnosing a no-candidates result as a real routing
  gap, confirm the dirty path set is dominated by bundle mirrors or managed
  output files and not by workstream-registered source files.

- Regression Tests Added:
  `tests/unit/runtime/test_agent_governance_intelligence.py::test_normalize_changed_paths_preserves_leading_dot_directories`
  asserts that `.claude/…`, `.codex/…`, and `.github/…` inputs survive
  normalization and never produce a dot-stripped variant;
  `tests/unit/runtime/test_agent_governance_intelligence.py::test_normalize_changed_paths_fans_out_bundle_mirror_aliases`
  asserts legitimate bundle-mirror alias fan-out without the broken
  dot-stripped variant; and
  `tests/unit/runtime/test_agent_governance_intelligence.py::test_collect_git_changed_paths_skips_nested_worktree_copies`
  synthesizes a bundled-worktree-copy tree with a `gitdir:` marker and
  asserts the path is excluded from `collect_git_changed_paths`.

- Monitoring Updates: Watch for `selection_state: none` in start bootstrap
  output on branches with broad surface-sync dirty trees.

- Residual Risk: Until fixed, agents on bundle-heavy dirty branches must run an
  explicit `odylith context` step to ground each session.

- Related Incidents/Bugs: None directly. Related to the broader B-083,
  B-084, and B-085 Claude host parity work whose `.claude/worktrees/`
  experimentation left the funny-leavitt worktree accident in place.
  B-086 Governance Path Normalization Hardening And Nested Worktree
  Guard is the bound forward fix and ships the corrected root cause
  plus the nested-worktree filter.

- Version/Build: Odylith product repo branch `2026/freedom/v0.1.11`,
  2026-04-11.

- Config/Flags: Reproduced with standard `odylith start --repo-root .` on the
  product repo with no special flags.

- Customer Comms: N/A — internal product repo maintainer tooling.

- Code References:
  `src/odylith/runtime/governance/agent_governance_intelligence.py`,
  `src/odylith/runtime/common/consumer_profile.py`,
  `tests/unit/runtime/test_agent_governance_intelligence.py`,
  `odylith/technical-plans/in-progress/2026-04/2026-04-11-governance-path-normalization-hardening-and-nested-worktree-guard.md`

- Runbook References: `AGENTS.md`, `odylith/AGENTS.md`,
  `odylith/agents-guidelines/VALIDATION_AND_TESTING.md`

- Fix Commit/PR: B-086 fix commit on branch `2026/freedom/v0.1.11`
  lands `_strip_current_dir_prefix`,
  `_is_nested_git_worktree_path`, the two `agent_governance_intelligence.py`
  call-site fixes, the `consumer_profile.py` `_legacy_product_token_alias`
  fix, three new `test_agent_governance_intelligence.py`
  characterization tests, the funny-leavitt cleanup, and this CB-102
  update.
