Status: In progress

Created: 2026-04-11

Updated: 2026-04-11

Backlog: B-086

Goal: Harden the `odylith start` changed-path pipeline so it no longer
corrupts dotfile directories (`.claude/…`, `.codex/…`, `.github/…`) into
broken non-dotfile aliases and so accidental nested git worktrees (for
example `.claude/worktrees/<slug>` or a bundled copy of one under
`src/odylith/bundle/assets/project-root/.claude/worktrees/<slug>`) cannot
pollute the changed-path set and fan out into multiple bogus variants
that push the start bootstrap into `lane: fallback` with
`selection_state: none`. The slice is the concrete forward fix for
CB-102 whose original framing pointed at a missing secondary signal when
the real root cause is two latent bugs in the path-normalization
pipeline plus a missing nested-worktree guard.

Assumptions:
- The `.lstrip("./")` idiom is broken for dotfile directories because
  `str.lstrip` strips every leading `.` or `/` character, not just a
  literal `./` prefix. Any repo with real dotfile directories (`.claude`,
  `.codex`, `.github`, `.vscode`, `.tmp`) is silently one typo-equivalent
  away from the same fan-out pathology as funny-leavitt.
- Nested git worktrees are the right filesystem signal to skip. A
  directory carrying a `.git` marker (either a directory for full clones
  or a text file starting with `gitdir:` for registered worktrees) is
  opaque to the parent repo and must never contribute changed-path
  candidates, regardless of whether git status actually recurses into it
  (git status does not, but untracked bundle copies of a worktree do).
- CB-102 is the exact casebook match for the observable failure. The
  original framing attributed the fallback to missing secondary signals;
  the real root cause is upstream path corruption and missing nested-
  worktree filtering. The right move is to extend CB-102 with the
  corrected root cause and mark it Resolved rather than open CB-105.
- The fix must be host-agnostic. Codex and Claude Code both go through
  the same `build_session_bootstrap` → `_resolve_changed_path_scope_context`
  → `collect_meaningful_changed_paths` → `collect_git_changed_paths`
  pipeline. One upstream fix covers both hosts and does not add any
  host-family branching.

Constraints:
- Do not widen the fix beyond the governance path-normalization surface
  and the nested-worktree guard. The other twelve `.lstrip("./")`
  callsites scattered across `component_registry_intelligence.py`,
  `build_traceability_graph.py`, `odylith_chatter_runtime.py`,
  `subagent_orchestrator.py`, and friends are latent bugs in adjacent
  pipelines; leave them for their own bounded slices.
- Do not change `workstream_inference.normalize_repo_token` beyond what
  is already there. That helper already peels `./` correctly via an
  explicit `startswith("./")` check; the corruption happens downstream
  in `_legacy_product_token_alias` and in `normalize_changed_paths`.
- Do not add host-family branching. A nested-worktree guard or a
  dotfile-preserving normalizer must behave identically under the Codex
  and Claude Code execution profiles.
- Do not cascade the bundle-mirror rendered assets on this commit. The
  fix edits source-of-truth Python modules and tests only; derived
  surfaces do not change shape.

Reversibility: The fix is fully reversible. Reverting the two source
files and the three new characterization tests restores the exact prior
behavior. The new `_strip_current_dir_prefix` helper and
`_is_nested_git_worktree_path` helper are private module-level functions
with no external caller.

Boundary Conditions:
- Scope includes
  `src/odylith/runtime/governance/agent_governance_intelligence.py`
  (new `_strip_current_dir_prefix` helper, fixed `_changed_path_aliases`,
  fixed `normalize_changed_paths`, new `_is_nested_git_worktree_path`
  helper, updated `collect_git_changed_paths`),
  `src/odylith/runtime/common/consumer_profile.py`
  (fixed `_legacy_product_token_alias`),
  `tests/unit/runtime/test_agent_governance_intelligence.py`
  (three new characterization tests), cleanup of the funny-leavitt
  worktree accident (`git worktree remove` plus removal of the bundled
  copy under
  `src/odylith/bundle/assets/project-root/.claude/worktrees/`), and the
  CB-102 bug-record update marking Resolved with the corrected root
  cause and the new fix commit reference.
- Scope excludes fixing the twelve other `.lstrip("./")` callsites in
  adjacent runtime modules, decomposing `agent_governance_intelligence.py`,
  adding new CLI commands for casebook bug or technical-plan creation,
  and any change to the bundle-mirror render or refresh pipeline.

Related Bugs:
- CB-102 (extended with corrected root cause and marked Resolved in the
  same commit as the code fix).

## Learnings
- [x] `str.lstrip("./")` is not the right way to peel a `./` prefix.
      `lstrip` takes a character set and strips every leading `.` or `/`
      character, so `.claude/worktrees/funny-leavitt`.lstrip("./") is
      `claude/worktrees/funny-leavitt`. The correct idiom is an explicit
      `if token.startswith("./"): token = token[2:]`, or a thin helper
      like the new `_strip_current_dir_prefix` that makes the intent
      local and searchable. The broken idiom is pervasive across the
      runtime tree (fourteen non-mirror callsites before this fix);
      this slice fixes the two that actually corrupt the start pipeline
      and leaves the rest as a latent-bug cleanup slice.
- [x] The path-alias fan-out in `_changed_path_aliases` multiplies
      whatever corruption happens upstream. A single git-status row for a
      nested-worktree copy expanded into three separate changed-path
      entries: the original bundle-mirror path, a correctly-stripped
      bundle-mirror alias, and a dot-stripped variant. None of the three
      matched any workstream anchor, so the start bootstrap fell to
      `selection_state: none` and `lane: fallback` even though no real
      workstream evidence was in flight.
- [x] Nested git worktrees are an absolute filesystem signal. Any
      directory containing a `.git` marker (directory or `gitdir:` file)
      is opaque to the parent repo and must be excluded before changed-
      path normalization runs. Walking ancestors up to the repo root and
      checking for that marker gives a host-agnostic guard that works
      for both registered worktrees (`git worktree add`) and accidental
      bundle copies that carry the marker into the parent repo's
      filesystem.
- [x] The original CB-102 framing ("missing secondary signal when dirty
      tree is dominated by bundle mirrors") was a reasonable hypothesis
      from observable symptoms but wrong about the root cause. The
      actual pathology is upstream path corruption in
      `_legacy_product_token_alias` plus missing nested-worktree
      filtering in `collect_git_changed_paths`. Diagnosis discipline:
      reproduce → trace the exact string through every hop in the
      normalization pipeline → do not trust intuition about where the
      corruption enters.

## Must-Ship
- [x] File B-086 in Radar via `odylith backlog create` (not hand-edited).
- [x] Hand-author this technical plan under
      `odylith/technical-plans/in-progress/2026-04/` and bind it to
      B-086.
- [x] Add `_strip_current_dir_prefix` to
      `agent_governance_intelligence.py` with a docstring that calls out
      the broken `lstrip("./")` idiom and why the explicit prefix check
      is safer.
- [x] Replace both broken `lstrip("./")` sites in
      `agent_governance_intelligence.py` (`_changed_path_aliases` and
      `normalize_changed_paths`) with the new helper.
- [x] Fix `_legacy_product_token_alias` in `consumer_profile.py` to use
      an explicit `startswith("./")` prefix check with an inline comment
      calling out the broken idiom.
- [x] Add `_is_nested_git_worktree_path` to
      `agent_governance_intelligence.py` that walks the candidate path
      and each of its ancestors up to (but excluding) the repo root and
      returns True if any of them carry a `.git` marker (directory or
      `gitdir:` text file).
- [x] Call `_is_nested_git_worktree_path` in `collect_git_changed_paths`
      so paths under a nested worktree are skipped before normalization.
- [x] Add
      `tests/unit/runtime/test_agent_governance_intelligence.py::test_normalize_changed_paths_preserves_leading_dot_directories`
      covering `.claude/…`, `.codex/…`, `.github/…`, and `./odylith/…`
      inputs and asserting no `claude/…`, `codex/…`, or `github/…`
      variant is minted.
- [x] Add
      `tests/unit/runtime/test_agent_governance_intelligence.py::test_normalize_changed_paths_fans_out_bundle_mirror_aliases`
      covering the legitimate bundle-mirror alias fan-out without the
      broken dot-stripped variant.
- [x] Add
      `tests/unit/runtime/test_agent_governance_intelligence.py::test_collect_git_changed_paths_skips_nested_worktree_copies`
      covering the synthesized bundled-worktree-copy tree with a
      `gitdir:` marker.
- [x] Run the governance-intelligence, consumer-profile, and
      workstream-inference test suites clean.
- [x] Clean up the funny-leavitt worktree accident:
      `git worktree remove --force .claude/worktrees/funny-leavitt`,
      `git worktree prune`, `rmdir .claude/worktrees`, and
      `git clean -fd src/odylith/bundle/assets/project-root/.claude/worktrees/`.
- [x] Verify `./.odylith/bin/odylith start --repo-root .` resolves to a
      real lane with `selection_state: inferred_confident` or better.
- [x] Extend CB-102 with the corrected root cause, the fix commit, and
      mark Status: Resolved.

## Should-Ship
- [x] Inline comment in `_strip_current_dir_prefix` explaining why
      `lstrip("./")` is broken so the next maintainer finds the right
      pattern without re-deriving it.
- [x] Characterization test docstrings that quote the broken idiom and
      the failing input so regression review is one grep away.

## Defer
- [ ] Fix the other twelve `.lstrip("./")` callsites in
      `component_registry_intelligence.py`,
      `sync_component_spec_requirements.py`,
      `build_traceability_graph.py`,
      `validate_plan_traceability_contract.py`,
      `execution_wave_contract.py`,
      `odylith_chatter_runtime.py`,
      `subagent_orchestrator.py`,
      `subagent_router_assessment_runtime.py`,
      `component_registry_path_aliases.py`,
      `product_assets.py`,
      `odylith_benchmark_runner.py`, and the remaining adjacent modules.
      Each of those is a separate bounded latent-bug slice.
- [ ] Decomposing `agent_governance_intelligence.py` toward the 800 LOC
      soft limit; the file is at 820 LOC after this slice. The file-size
      discipline policy flags this as a refactor candidate but the
      slice itself does not grow the file, so the decomposition work
      belongs to a separate refactor-first wave.
- [ ] Adding a CLI for casebook bug and technical-plan creation. The
      absence of those CLIs is why this slice still hand-authors the
      plan and extends CB-102 via direct markdown edit.

## Success Criteria
- [x] All three new characterization tests pass locally.
- [x] The existing `test_agent_governance_intelligence.py`,
      `test_consumer_profile.py`, and `test_workstream_inference.py`
      suites remain green.
- [x] `./.odylith/bin/odylith start --repo-root .` on the current branch
      returns `lane: bootstrap` (or better), `selection_state:
      inferred_confident`, `precision_score >= 60`, and a changed-path
      set that contains only the real source edits in this slice. No
      phantom `claude/…`, `codex/…`, or `github/…` variants. No
      worktree-copy paths.

## Validation Handoff
- Run `PYTHONPATH=src .venv/bin/python -m pytest
  tests/unit/runtime/test_agent_governance_intelligence.py
  tests/unit/runtime/test_consumer_profile.py
  tests/unit/runtime/test_workstream_inference.py -q` and report the
  summary in the Compass log entry that accompanies the commit.
- Run `./.odylith/bin/odylith start --repo-root .` and capture the
  resulting `lane`, `selection_state`, `selection_confidence`, and
  `changed_paths` in the Compass log entry.
- Do not trigger a selective governance sync on this commit; the fix
  does not touch rendered surface files.
