# Benchmark Tables

This note holds the detailed benchmark tables linked from the root
[README](../../README.md).

Benchmark metric order:
[Odylith Benchmark Metrics And Priorities](METRICS_AND_PRIORITIES.md)

Methodology and reviewer protocol:
[How To Read Odylith's Codex Benchmarks](README.md) and
[Reviewer Guide And Prompt](REVIEWER_GUIDE.md)

Family-by-family corpus map:
[Benchmark Families And Eval Catalog](FAMILIES_AND_EVALS.md)

## Grounding Signal Table

| Signal | odylith_on | odylith_off | Delta | Why It Matters |
| --- | --- | --- | --- | --- |
| Lane role | primary candidate | odylith_off / raw Codex CLI honest baseline | full Odylith vs raw agent | Keeps the Grounding Benchmark honest: full Odylith packet and prompt construction versus the raw Codex CLI prompt bundle on the same task. |
| Scenario count | 37 | 37 | +0 | Both lanes run the exact same corpus, so the comparison stays apples-to-apples. |
| Median packet time | 7.048 ms | 0.003 ms | <span style="color:#c5221f;">+7.045 ms</span> | Shows the packet construction time on the Grounding Benchmark before any live Codex session begins. |
| Mean packet time | 6.871 ms | 0.003 ms | <span style="color:#c5221f;">+6.868 ms</span> | Shows the mean packet time so slow prompt-build cases stay visible. |
| P95 packet time | 9.881 ms | 0.008 ms | <span style="color:#c5221f;">+9.873 ms</span> | Shows the long-tail packet time instead of hiding it behind the median. |
| Median prompt-bundle build time | 6.702 ms | 0.000 ms | <span style="color:#c5221f;">+6.702 ms</span> | Shows time spent inside Odylith packet construction and prompt shaping on the Grounding Benchmark. |
| Median grounding validation overhead | 0.515 ms | 0.003 ms | <span style="color:#c5221f;">+0.512 ms</span> | Shows post-build grounding harness overhead such as validation and accounting. |
| Median prompt-bundle input tokens | 139.0 | 92.0 | <span style="color:#c5221f;">+47.0</span> | Shows the model-facing prompt-bundle input size on the Grounding Benchmark. |
| Median total prompt-bundle payload tokens | 149.0 | 92.0 | <span style="color:#c5221f;">+57.0</span> | Shows the full grounding payload size across prompt, runtime contract, and operator diagnostics. |
| Required-path recall rate | 0.916 | 0.596 | <strong style="color:#137333;">+0.320</strong> | Higher means Odylith finds more of the repo surfaces the task truly depends on. |
| Required-path precision rate | 0.976 | 0.892 | <strong style="color:#137333;">+0.084</strong> | Higher means Odylith keeps the evidence cone tighter and more relevant. |
| Hallucinated-surface rate | 0.024 | 0.000 | <span style="color:#c5221f;">+0.024</span> | Lower means less made-up or unnecessary surface spread. |
| Validation-success proxy rate | 0.690 | 0.000 | <strong style="color:#137333;">+0.690</strong> | Higher means the Grounding Benchmark more often satisfies the benchmark validator proxy before any live Codex session begins. |
| Critical required-path recall rate | 0.930 | 0.646 | <strong style="color:#137333;">+0.284</strong> | Protects high-stakes cases from missing critical repo truth. |
| Critical validation-success proxy rate | 0.667 | 0.000 | <strong style="color:#137333;">+0.667</strong> | Protects critical grounding cases from missing packet-level validator proxy truth. |
| Expectation-success proxy rate | 1.000 | 0.000 | <strong style="color:#137333;">+1.000</strong> | Higher means more scenarios satisfy the stated task contract on the Grounding Benchmark before model execution begins. |

## Grounding Family Order

Developer-first family order used below in the family tables and heatmaps:

| Archetype | Evals | Families | Why This Comes Early |
| --- | ---: | --- | --- |
| Bug Fixes | 5 | `validation_heavy_fix`, `browser_surface_reliability`, `cli_contract_regression` | Closest to the classic SWE-bench shape: localize a concrete defect, change code, clear a validator. |
| Multi-File Features | 2 | `cross_file_feature`, `merge_heavy_change` | Measures bounded multi-file implementation instead of single-file toy edits. |
| Runtime / Install / Security | 6 | `install_upgrade_runtime`, `agent_activation`, `daemon_security`, `consumer_profile_compatibility`, `runtime_state_integrity` | Represents real developer pain around install, activation, config compatibility, state integrity, and security-sensitive repair. |
| Surface / UI Reliability | 2 | `dashboard_surface`, `compass_brief_freshness` | Covers browser-backed product behavior and stateful UI regressions. |
| Docs + Code Closeout | 5 | `docs_code_closeout`, `governed_surface_sync`, `cross_surface_governance_sync` | Keeps code, docs, specs, and mirrors aligned after implementation. |
| Governance / Release Integrity | 4 | `component_governance`, `release_publication` | Retains Odylith's product-repo truth and release-proof integrity cases. |
| Architecture Review | 4 | `architecture` | Keeps grounded design-review quality visible, but after direct coding work. |
| Grounding / Orchestration Control | 9 | `broad_shared_scope`, `exact_path_ambiguity`, `exact_anchor_recall`, `explicit_workstream`, `retrieval_miss_recovery`, `orchestration_feedback`, `orchestration_intelligence` | Shows how Odylith stays bounded and grounded, but does not lead the public developer story. |

## Live Signal Table

| Signal | odylith_on | odylith_off | Delta | Why It Matters |
| --- | --- | --- | --- | --- |
| Lane role | primary candidate | odylith_off / raw Codex CLI honest baseline | full Odylith vs raw agent | Keeps the public claim honest: full Odylith scaffold versus raw Codex CLI on the same task. |
| Scenario count | 37 | 37 | +0 | Both lanes run the exact same corpus, so the comparison stays apples-to-apples. |
| Median time to valid outcome | 57s | 1m 28s | <strong style="color:#137333;">-30s</strong> | Shows matched-pair benchmark time to valid outcome for the live run plus the harness validator, not interactive product latency. |
| Mean time to valid outcome | 1m 51s | 1m 47s | <span style="color:#c5221f;">+4.73s</span> | Shows the mean matched-pair benchmark time to valid outcome so long-tail slow cases stay visible. |
| P95 time to valid outcome | 4m 24s | 4m 05s | <span style="color:#c5221f;">+19s</span> | Shows the tail completion time for the slowest benchmark cases instead of letting the median hide them. |
| Median live agent runtime | 53s | 1m 19s | <strong style="color:#137333;">-26s</strong> | Shows time spent inside the live Codex CLI session itself. |
| Median validator overhead | 3.77s | 3.48s | <span style="color:#c5221f;">+292 ms</span> | Shows harness validator overhead added after the live Codex session completes. |
| Median live session input tokens | 168,786 | 335,454 | <strong style="color:#137333;">-166,668</strong> | Shows full live Codex session input across the multi-turn run, not just the first prompt. |
| Median total model tokens | 170,631 | 338,270 | <strong style="color:#137333;">-167,639</strong> | Shows total live model-token spend across the multi-turn session. |
| Required-path recall rate | 0.997 | 0.811 | <strong style="color:#137333;">+0.186</strong> | Higher means Odylith finds more of the repo surfaces the task truly depends on. |
| Required-path precision rate | 0.809 | 0.539 | <strong style="color:#137333;">+0.270</strong> | Higher means Odylith keeps the evidence cone tighter and more relevant. |
| Hallucinated-surface rate | 0.191 | 0.434 | <strong style="color:#137333;">-0.243</strong> | Lower means less made-up or unnecessary surface spread. |
| Validation success rate | 0.897 | 0.828 | <strong style="color:#137333;">+0.069</strong> | Higher means the lane more often reaches a validator-backed correct outcome. |
| Critical required-path recall rate | 0.979 | 0.649 | <strong style="color:#137333;">+0.330</strong> | Protects high-stakes cases from missing critical repo truth. |
| Critical validation success rate | 1.000 | 1.000 | +0.000 | Protects critical changes from silent regressions. |
| Expectation success rate | 0.757 | 0.364 | <strong style="color:#137333;">+0.393</strong> | Higher means more scenarios finish the stated task contract on the live run. |

## Live Notes

> [!NOTE]
> `odylith_off` means `raw_agent_baseline`. The headline comparison is
> `odylith_on` versus that baseline.
>
> For honest inner-loop tuning, targeted `--profile proof --case-id ...`
> slices are useful and often much faster, but they do not replace the full
> warm-plus-cold proof run that drives the public benchmark snapshot.
>
> This latest pass is the current source-tree benchmark posture. Product-repo
> `benchmark_compare` still reports `warn` until the first shipped release
> baseline is recorded in `docs/benchmarks/release-baselines.v1.json`.
