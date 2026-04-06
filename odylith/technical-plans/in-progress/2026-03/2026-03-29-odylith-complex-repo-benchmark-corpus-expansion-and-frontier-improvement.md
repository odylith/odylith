Status: In progress

Created: 2026-03-29

Updated: 2026-04-05

Backlog: B-021

Goal: Reframe Odylith's benchmark around a developer-first family order,
expand the tracked corpus with more SWE-bench-like local coding slices, restore
guidance-memory-backed weak-family grounding, improve the weakest live proof
families without softening the benchmark, and keep README plus the surrounding
benchmark governance surfaces aligned to the same current proof and diagnostic
posture.

Assumptions:
- The latest diagnostic report `74cbe36427f2c375` is strong enough that the
  next leverage comes from guidance-memory recovery, better live handoff
  quality, and a better developer benchmark story, not from more packet-only
  wins.
- The latest full source-local proof `52aa3f76538cf12f` is a real product
  signal: Odylith now clears the hard quality gate and secondary guardrails,
  while the older `926bfeab4e887ade` report remains the protected proof floor
  for no-regression comparisons.
- The current public proof is local-memory-first on LanceDB plus Tantivy.
  Vespa remains intentionally disabled and must not become a hidden
  prerequisite for the first passing release.
- The current tracked corpus still reads too much like an Odylith product
  maintainer benchmark unless the developer-core families are explicit and come
  first.

Constraints:
- Do not soften the corpus to recover a prettier benchmark.
- Do not accept speed or token wins that regress recall, precision,
  validation, expectation success, or write-surface quality.
- Treat proof report `926bfeab4e887ade` as the protected floor and reject any
  change that worsens its current recall, precision, validation, expectation,
  token, or median time-to-valid-outcome wins on targeted proof reruns.
- Keep the README tied to the latest validated report ids, even while the
  tracked corpus expands ahead of the next full proof rerun.
- Keep the source corpus and bundled mirror aligned.
- Keep the heatmap order developer-first and explicit in the graph assets.
- Benchmark warm preflight must fail closed if the guidance catalog is empty or
  lacks task-family coverage.

Reversibility: Reverting this slice restores the previous benchmark taxonomy,
the smaller tracked corpus, the older graph ordering, and the prior benchmark
docs story.

Boundary Conditions:
- Scope includes README and benchmark-doc updates, Registry/Radar/Atlas/Compass
  alignment, corpus expansion, corpus-hardening tests, and prompt-handoff
  improvements for weak live families.
- Scope excludes hosted benchmark infrastructure and Claude-native benchmark
  publication.

Related Bugs:
- [CB-046](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-02-benchmark-support-doc-selector-overweights-generic-guidance-on-proof-slices.md)
- [CB-040](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-02-benchmark-warm-cold-proof-instability-flips-narrow-slice-winners.md)

## Context/Problem Statement

- [x] The root README now distinguishes the Grounding Benchmark from the Live
      Benchmark and publishes the current proof plus diagnostic report ids.
- [x] The graph renderer now understands a developer-first family taxonomy and
      can regenerate separate `diagnostic/` and `proof/` graph sets.
- [x] The live prompt handoff was under-seeding browser, install, activation,
      and release-governance slices; support-doc selection and strict-boundary
      behavior have been tightened.
- [x] The current published diagnostic report is `74cbe36427f2c375` and the
      current published live proof is `52aa3f76538cf12f`; diagnostic remains on
      `hold`, while live proof is now `provisional_pass`.
- [x] Benchmark guidance memory was effectively empty on product-repo proof
      slices until the canonical manifest path and family-aware retrieval
      plumbing were restored.
- [ ] Neighboring benchmark truth surfaces still lag the README unless Registry,
      Radar, Atlas, Compass, and benchmark docs are updated together.
- [ ] The tracked corpus still needs more developer-core local coding slices:
      CLI contract repair, config compatibility, runtime state integrity,
      managed runtime repair, and onboarding browser proof.
- [x] A new full proof rerun now exists, so the public benchmark no longer has
      to stay pinned to the older `hold` report while the tracked corpus and
      governed surfaces move forward.
- [x] Detached `source-local` proof and diagnostic reruns must use the repo
      `.venv` interpreter; system `python` can falsely miss the local
      LanceDB/Tantivy substrate and fail warm preflight before the benchmark
      logic even runs.
- [x] Selected cache profiles now clear the hard gate and tighter-budget
      behavior is back above the `0.80` floor on the current proof posture.

## Success Criteria

- [x] Root README benchmark tables and graphs are split into Grounding and Live
      views with the current report ids and honest status language.
- [x] The profile SVG sets under `docs/benchmarks/diagnostic/` and
      `docs/benchmarks/proof/` are regenerated with the developer-first
      archetype order and explicit `Archetype` column.
- [x] The canonical benchmark guidance manifest exists under
      `odylith/agents-guidelines/indexable-guidance-chunks.v1.json`, the
      bundle mirror is aligned, and benchmark preflight fails closed when the
      guidance catalog is empty.
- [x] Focused prompt and packet regressions cover
      `component_governance`, `compass_brief_freshness`,
      `consumer_profile_compatibility`, and narrow anchored weak families.
- [ ] Benchmark explainer docs, Registry spec, Radar workstream, Atlas proof
      lane, and Compass runtime digest all describe the same current proof and
      diagnostic posture.
- [ ] The tracked corpus includes additional developer-core benchmark families
      and scenarios, not only more governance-heavy cases.
- [ ] The public corpus and bundled mirror stay byte-for-byte aligned.
- [ ] Corpus-hardening tests enforce the new developer-core family coverage.
- [ ] Weak live-family handoff quality improves for browser reliability,
      release publication, component governance, and runtime or install slices.
- [ ] Weak live-family handoff quality improves for `component_governance`,
      `compass_brief_freshness`, `consumer_profile_compatibility`,
      `cross_file_feature`, and the remaining budget-sensitive proof slices.
- [x] Activation-family live runs prefer validator-backed no-op or a true
      failing assertion surface over speculative install-guidance rewrites.
- [x] Repair-style live scenarios that allow "already correct" closeout expose
      that contract explicitly in corpus metadata and live scoring, so no-op
      success is not punished as a write miss.
- [x] A targeted proof rerun demonstrates real movement on the weak families.
- [x] A later full proof rerun is ready to refresh the public headline and has
      now beaten the old `hold` report honestly.
- [x] The next full proof clears both cache profiles, keeps
      `within_budget_rate >= 0.80`, and does not regress the current proof
      floor.

## Non-Goals

- [ ] Hosted benchmark scheduling or analytics infrastructure.
- [ ] Replacing the Odylith product-repo benchmark with an external benchmark
      before the developer-core local slice is strong enough.
- [ ] Any benchmark-softening change that removes hard cases or weakens
      validators.

## Impacted Areas

- [ ] [README.md](/Users/freedom/code/odylith/README.md)
- [ ] [README.md](/Users/freedom/code/odylith/docs/benchmarks/README.md)
- [ ] [FAMILIES_AND_EVALS.md](/Users/freedom/code/odylith/docs/benchmarks/FAMILIES_AND_EVALS.md)
- [ ] [indexable-guidance-chunks.v1.json](/Users/freedom/code/odyssey/odylith/agents-guidelines/indexable-guidance-chunks.v1.json)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/benchmark/CURRENT_SPEC.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odyssey/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odyssey/odylith/registry/source/components/compass/CURRENT_SPEC.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odyssey/odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md)
- [ ] [CURRENT_SPEC.md](/Users/freedom/code/odyssey/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [ ] [2026-03-29-odylith-complex-repo-benchmark-corpus-expansion-and-frontier-improvement.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-03/2026-03-29-odylith-complex-repo-benchmark-corpus-expansion-and-frontier-improvement.md)
- [ ] [odylith-benchmark-proof-and-publication-lane.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd)
- [ ] [current.v1.json](/Users/freedom/code/odylith/odylith/compass/runtime/current.v1.json)
- [ ] [optimization-evaluation-corpus.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/optimization-evaluation-corpus.v1.json)
- [ ] [optimization-evaluation-corpus.v1.json](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith/runtime/source/optimization-evaluation-corpus.v1.json)
- [ ] [indexable-guidance-chunks.v1.json](/Users/freedom/code/odyssey/src/odylith/bundle/assets/odylith/agents-guidelines/indexable-guidance-chunks.v1.json)
- [ ] [odylith_benchmark_taxonomy.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_taxonomy.py)
- [ ] [odylith_benchmark_prompt_family_rules.py](/Users/freedom/code/odyssey/src/odylith/runtime/evaluation/odylith_benchmark_prompt_family_rules.py)
- [ ] [odylith_benchmark_prompt_payloads.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_prompt_payloads.py)
- [ ] [tooling_guidance_catalog.py](/Users/freedom/code/odyssey/src/odylith/runtime/context_engine/tooling_guidance_catalog.py)
- [ ] [tooling_context_retrieval.py](/Users/freedom/code/odyssey/src/odylith/runtime/context_engine/tooling_context_retrieval.py)
- [ ] [tooling_context_packet_builder.py](/Users/freedom/code/odyssey/src/odylith/runtime/context_engine/tooling_context_packet_builder.py)
- [ ] [odylith_context_engine_grounding_runtime.py](/Users/freedom/code/odyssey/src/odylith/runtime/context_engine/odylith_context_engine_grounding_runtime.py)
- [ ] [odylith_context_engine_session_packet_runtime.py](/Users/freedom/code/odyssey/src/odylith/runtime/context_engine/odylith_context_engine_session_packet_runtime.py)
- [ ] [odylith_context_engine_hot_path_delivery_runtime.py](/Users/freedom/code/odyssey/src/odylith/runtime/context_engine/odylith_context_engine_hot_path_delivery_runtime.py)
- [ ] [odylith_benchmark_runner.py](/Users/freedom/code/odyssey/src/odylith/runtime/evaluation/odylith_benchmark_runner.py)
- [ ] [test_tooling_guidance_catalog.py](/Users/freedom/code/odyssey/tests/unit/runtime/test_tooling_guidance_catalog.py)
- [ ] [test_tooling_context_retrieval_guidance.py](/Users/freedom/code/odyssey/tests/unit/runtime/test_tooling_context_retrieval_guidance.py)
- [ ] [test_odylith_benchmark_prompt_regressions.py](/Users/freedom/code/odyssey/tests/unit/runtime/test_odylith_benchmark_prompt_regressions.py)
- [ ] [test_odylith_benchmark_preflight.py](/Users/freedom/code/odyssey/tests/unit/runtime/test_odylith_benchmark_preflight.py)
- [ ] [test_odylith_benchmark_corpus.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_corpus.py)
- [ ] [test_odylith_benchmark_graphs.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_graphs.py)

## Risks & Mitigations

- [ ] Risk: the developer-first story outruns the actual proof.
  - [ ] Mitigation: keep README and the public graphs anchored to the current
        report ids until a stronger proof rerun exists.
- [ ] Risk: new corpus growth is still too Odylith-product-specific.
  - [ ] Mitigation: add explicit code-and-test slices with public validators
        and familiar bug-fix or feature-repair shapes.
- [ ] Risk: prompt-handoff fixes reduce latency by dropping necessary truth.
  - [ ] Mitigation: preserve required-path recall and tighten support-doc
        ranking instead of hard-pruning blindly.
- [ ] Risk: restored guidance memory improves packet quality but reintroduces
      warm/cold slice drift.
  - [ ] Mitigation: make candidate ordering deterministic and treat
        cross-profile boundedness as a hard engineering requirement before
        publication.
- [ ] Risk: Registry, Radar, Atlas, and Compass drift again.
  - [ ] Mitigation: update the benchmark source-of-truth surfaces in the same
        change and rerender the generated surfaces together.

## Validation/Test Plan

- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_prompt_payloads.py tests/unit/runtime/test_odylith_benchmark_graphs.py`
- [x] `python -m pytest -q tests/unit/runtime/test_tooling_guidance_catalog.py tests/unit/runtime/test_tooling_context_retrieval_guidance.py tests/unit/runtime/test_odylith_benchmark_prompt_regressions.py tests/unit/runtime/test_odylith_benchmark_preflight.py`
- [x] `python -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py -q`
- [x] `PYTHONPATH=src python -m odylith.runtime.evaluation.odylith_benchmark_graphs --repo-root . --out-dir docs/benchmarks --profiles diagnostic proof`
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/test_cli.py tests/unit/runtime/test_consumer_profile.py tests/unit/runtime/test_odylith_control_state.py`
- [ ] `PYTHONPATH=src python -m odylith.runtime.surfaces.auto_update_mermaid_diagrams --repo-root . --changed-path odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd`
- [ ] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_compass_dashboard --repo-root . --refresh-profile shell-safe`
- [ ] targeted proof rerun on the weak families
- [ ] `git diff --check`

## Rollout/Communication

- [x] Root README benchmark section is now current-report-first and
      developer-first in ordering.
- [x] The published profile graph sets now sort by archetype rather than by
      prompt delta.
- [ ] Benchmark docs, Registry, Radar, Atlas, and Compass will be refreshed in
      the same change so the benchmark story stays synchronized.
- [ ] The next proof headline remains frozen until the targeted weak-family
      reruns confirm no regression against `926bfeab4e887ade`.
- [ ] Corpus additions will be described as tracked-source growth until the
      next full proof refresh moves the public headline.

## Active Execution Waves

- [x] Wave 1: restore benchmark guidance memory, deterministic packet scoring,
      and fail-closed benchmark preflight so proof never runs on a zero-
      guidance posture.
- [x] Wave 2: tighten weak-family boundedness and live handoff quality so
      narrow proof slices stop widening into support-doc or validator-only
      surfaces.
- [x] Wave 3: recover validator-backed no-op scoring on already-correct repair
      slices; `daemon_security` is now cleared on warm and cold proof.
- [ ] Wave 4: finish the remaining live weak-family proof reruns with real
      time budgets for `component_governance`,
      `compass_brief_freshness`, `consumer_profile_compatibility`, and
      `cross_file_feature`.
- [ ] Wave 5: after the weak-family live blockers clear, land the next
      developer-core corpus additions and refresh the governed benchmark
      surfaces together from the stronger proof posture.

## Closeout / Cleanup Rules

- [ ] Keep `B-021` open only for the remaining corpus-growth and synchronized
      governance-refresh scope. Do not leave already-recovered weak-family
      runtime work hanging here once it is captured in `B-038` and the
      umbrella proof plan.
- [ ] Do not refresh the public benchmark headline again until the next full
      proof clears both cache profiles, keeps `within_budget_rate >= 0.80`,
      and does not regress the current proof floor.
- [ ] Close `B-021` only after:
      1. the corpus and bundle mirror gain the next developer-core scenarios,
      2. corpus-hardening tests pass,
      3. README, benchmark docs, Registry, Radar, Atlas, and Compass are
         refreshed together, and
      4. the stronger full proof report is the one actually backing the public
         story.

## Current Outcome

- [x] Bound to `B-021`; the anomaly audit and prompt-handoff fixes landed
      before the README refresh.
- [x] Browser proof handoff now pulls both required shell entrypoints into the
      support-doc candidate set when the slice truly needs them.
- [x] Install, activation, and release-governance support-doc selection now
      prefers slice-relevant runbooks and adjacent required paths over generic
      spec or skill spillover.
- [x] The live benchmark contract no longer inherits ambient
      `~/.codex/config.toml` model or reasoning defaults; repo or env contract
      now wins and the fallback reasoning effort is explicitly `medium`.
- [x] Live workspace snapshotting now captures validator companion repo files
      referenced directly by focused validation tests, so stripped truth is not
      silently reintroduced from the ambient repo during restore.
- [x] Strict bounded proof slices no longer widen simply because
      `required_paths == changed_paths` on larger multi-file publication tasks.
- [x] The benchmark renderer now regenerates profile-specific graph sets and
      the published `diagnostic` and `proof` heatmaps are categorized and
      sorted by archetype.
- [x] The benchmark docs and governance surfaces have been refreshed to the
      README-first developer taxonomy and current proof versus diagnostic split.
- [x] A canonical benchmark guidance manifest now lives at
      `odylith/agents-guidelines/indexable-guidance-chunks.v1.json`, the
      bundle mirror matches it, and benchmark warm preflight fails closed when
      guidance chunk, source-doc, or task-family coverage is empty.
- [x] Family hints now flow through benchmark packet finalization and guidance
      retrieval, so weak-family slices can pull only the guidance that matches
      the benchmark family being exercised.
- [x] Fail-closed weak-family packet ceilings now suppress miss recovery and
      unrelated support-doc spillover on `component_governance`,
      `compass_brief_freshness`, `consumer_profile_compatibility`,
      `daemon_security`, `cross_file_feature`, `exact_anchor_recall`,
      `explicit_workstream`, `orchestration_feedback`, and
      `orchestration_intelligence`.
- [x] The prompt-regression and benchmark-runner unit suites now pass with the
      restored guidance counts, deterministic compact payloads, and the new
      preflight rule.
- [x] Repair and publication live scenarios that explicitly allow "stop with
      no file changes" now carry `allow_noop_completion` in the corpus and the
      live prompt plus scorer no longer treat validator-backed no-op as an
      automatic write failure.
- [x] The activation-family warm live shard is materially recovered: the
      current targeted proof sample stays on the install activation surfaces,
      stops with validator-backed no-op, and reports full recall, full
      precision, zero hallucinated surfaces, and passing expectation.
- [x] The consumer install and managed-runtime repair warm live shards now
      have representative clean proof samples with validator-backed no-op and
      full required-path recall; consumer install is clean at full precision,
      and managed-runtime repair was tightened to the explicit `release`
      component scope before re-running to a clean representative sample.
- [x] The release-publication warm live shard now has a clean representative
      proof sample with full recall, full precision, zero hallucinated
      surfaces, passing validator-backed no-op expectation, and benchmark doc
      selection that explicitly includes `docs/benchmarks/release-baselines.v1.json`.
- [x] Benchmark-injected validator command paths are now neutralized in live
      observed-path attribution so release-proof precision is not falsely
      degraded by the benchmark's own pytest scaffolding.
- [x] Forced `ODYLITH_BENCHMARK_CODEX_TIMEOUT_SECONDS=120` is now treated as a
      failure-diagnosis tool, not the default posture for benchmark-quality
      warm proof samples, because it can manufacture schema-invalid live
      failures on otherwise passing no-op slices.
- [x] The April 5 detached diagnostic rerun now completes from the repo
      `.venv` and report `3365a99e8040d980` shows `provisional_pass` packet
      posture across the still-blocking weak families: `component_governance`,
      `compass_brief_freshness`, `consumer_profile_compatibility`,
      `daemon_security`, `architecture`, and `cross_file_feature` all now
      score `1.0` recall, `1.0` precision, and `0.0` widening against
      `odylith_off` on the current packet path.
- [x] Benchmark packet scoring now measures the same supplemented prompt
      payload that the live lane actually hands to Codex, so packet recall and
      selected-doc counts no longer under-report required guidance or support
      docs that are visible in the real proof prompt.
- [x] Detached daemon cleanup no longer throws noisy `BrokenPipeError`
      shutdown traces during focused shard teardown; the runtime now treats
      client disconnect on response write as non-fatal benchmark cleanup.
- [x] The April 5 focused `component_governance` proof rerun
      (`d776d9e3dc22bd09`) confirms the boundedness recovery on the live lane:
      recall `1.0`, precision `1.0`, hallucinated surfaces `0.0`,
      unnecessary-write widening `0.0`, and `within_budget 1.0` against
      `odylith_off`, but the slice still ends on `hold` because the local
      diagnostic timeout budget was too small to capture the validator-backed
      final result.
- [x] The April 5 focused warm `daemon_security` proof rerun
      (`f610654ed299d4f0`) is now a real live recovery, not just a packet
      cleanup: `odylith_on` finishes `provisional_pass` with full recall,
      full precision, zero hallucinated surfaces, zero widening, passing
      validator-backed no-op completion, `-228502.018 ms` latency delta, and
      `-1344532` total-token delta against the raw baseline on the bounded
      daemon slice.
- [x] The April 5 focused cold `daemon_security` proof rerun
      (`21d2c37e284693e4`) also clears the family with the same bounded no-op
      posture, so daemon security is no longer a warm-only recovery:
      `odylith_on` again posts full recall, full precision, zero hallucinated
      surfaces, zero widening, `-299735.027 ms` latency delta, and
      `-2040183` total-token delta against the raw baseline.
- [x] The daemon-security proof family now carries an honest allow-no-op
      contract plus focused-check-first prompt path because the current
      grounded daemon lifecycle and repair anchors already satisfy the narrow
      validator; this is a recovery of truthful scoring, not corpus softening.
- [x] The April 5 full proof rerun `52aa3f76538cf12f` now clears the hard
      quality gate and secondary guardrails across the full `37`-scenario
      warm-plus-cold corpus with `+0.227` recall, `+0.168` precision,
      `-0.141` hallucinated-surface rate, `+0.069` validation success,
      `+0.393` expectation success, `-52561` median live-session input
      tokens, `-53774` median total-model tokens, and `-12426.968 ms` median
      time to valid outcome against `odylith_off`.
- [x] The benchmark runner now bounds post-run adoption-proof sampling so a
      hanging read-only Codex subprocess can no longer keep a completed
      `148/148` proof report from being persisted.
- [ ] The tracked corpus still needs the new developer-core scenarios.
- [ ] The next follow-on still needs the new developer-core scenarios,
      richer family diagnostics, and a pinned-dogfood shipped baseline after
      the current source-local pass is folded into the release lane.
