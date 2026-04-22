# Benchmark Tables

This note holds the detailed benchmark tables linked from the root
[README](../../README.md).

Benchmark metric order:
[Odylith Benchmark Metrics And Priorities](METRICS_AND_PRIORITIES.md)

Methodology and reviewer protocol:
[How To Read Odylith's Benchmark Proof](README.md) and
[Reviewer Guide And Prompt](REVIEWER_GUIDE.md)

Family-by-family corpus map:
[Benchmark Families And Eval Catalog](FAMILIES_AND_EVALS.md)

## Internal Diagnostic Signal Table

| Signal | odylith_on | odylith_off | Delta | Why It Matters |
| --- | --- | --- | --- | --- |
| Lane role | primary candidate | odylith_off / raw Codex CLI honest baseline | full Odylith vs raw agent | Keeps the internal diagnostic benchmark honest: full Odylith packet and prompt construction versus the raw Codex CLI prompt bundle on the same task. |
| Scenario count | 82 | 82 | +0 | Both lanes run the exact same corpus, so the comparison stays apples-to-apples. |
| Median packet time | 30.381 ms | 0.022 ms | <span style="color:#c5221f;">+30.359 ms</span> | Shows the packet construction time on the internal diagnostic benchmark before any live Codex session begins. |
| Mean packet time | 32.846 ms | 0.024 ms | <span style="color:#c5221f;">+32.822 ms</span> | Shows the mean packet time so slow prompt-build cases stay visible. |
| P95 packet time | 70.469 ms | 0.040 ms | <span style="color:#c5221f;">+70.429 ms</span> | Shows the long-tail packet time instead of hiding it behind the median. |
| Median prompt-bundle build time | 29.578 ms | 0.000 ms | <span style="color:#c5221f;">+29.578 ms</span> | Shows time spent inside Odylith packet construction and prompt shaping on the internal diagnostic benchmark. |
| Median grounding validation overhead | 0.623 ms | 0.021 ms | <span style="color:#c5221f;">+0.602 ms</span> | Shows post-build grounding harness overhead such as validation and accounting. |
| Median prompt-bundle input tokens | 935.0 | 101.0 | <span style="color:#c5221f;">+834.0</span> | Shows the model-facing prompt-bundle input size on the internal diagnostic benchmark. |
| Median total prompt-bundle payload tokens | 1177.5 | 101.0 | <span style="color:#c5221f;">+1076.5</span> | Shows the full grounding payload size across prompt, runtime contract, and operator diagnostics. |
| Required-path recall rate | 0.926 | 0.601 | <strong style="color:#137333;">+0.325</strong> | Higher means Odylith finds more of the repo surfaces the task truly depends on. |
| Required-path precision rate | 0.981 | 0.951 | <strong style="color:#137333;">+0.030</strong> | Higher means Odylith keeps the evidence cone tighter and more relevant. |
| Hallucinated-surface rate | 0.019 | 0.000 | <span style="color:#c5221f;">+0.019</span> | Lower means less made-up or unnecessary surface spread. |
| Validation-success proxy rate | 0.657 | 0.000 | <strong style="color:#137333;">+0.657</strong> | Higher means the internal diagnostic benchmark more often satisfies the benchmark validator proxy before any live Codex session begins. |
| Critical required-path recall rate | 0.889 | 0.611 | <strong style="color:#137333;">+0.278</strong> | Protects high-stakes cases from missing critical repo truth. |
| Critical validation-success proxy rate | 0.613 | 0.000 | <strong style="color:#137333;">+0.613</strong> | Protects critical grounding cases from missing packet-level validator proxy truth. |
| Expectation-success proxy rate | 0.951 | 0.000 | <strong style="color:#137333;">+0.951</strong> | Higher means more scenarios satisfy the stated task contract on the internal diagnostic benchmark before model execution begins. |

> [!NOTE]
> Current diagnostic status: `hold`.
> Fairness contract passed: `True`.
> Corpus seriousness floor passed: `True`.

## Live Signal Table

| Signal | odylith_on | odylith_off | Delta | Why It Matters |
| --- | --- | --- | --- | --- |
| Lane role | primary candidate | odylith_off / raw Codex CLI honest baseline | full Odylith vs raw agent | Keeps the public claim honest: full Odylith scaffold versus raw Codex CLI on the same task. |
| Scenario count | 82 | 82 | +0 | Both lanes run the exact same corpus, so the comparison stays apples-to-apples. |
| Median time to valid outcome | 11s | 1m 17s | <strong style="color:#137333;">-1m 07s</strong> | Shows matched-pair benchmark time to valid outcome for the live run plus the harness validator, not interactive product latency. |
| Mean time to valid outcome | 50s | 1m 38s | <strong style="color:#137333;">-47s</strong> | Shows the mean matched-pair benchmark time to valid outcome so long-tail slow cases stay visible. |
| P95 time to valid outcome | 4m 00s | 4m 00s | <strong style="color:#137333;">-129 ms</strong> | Shows the tail completion time for the slowest benchmark cases instead of letting the median hide them. |
| Median live agent runtime | 0.000 ms | 1m 12s | <strong style="color:#137333;">-1m 12s</strong> | Shows time spent inside the live Codex CLI session itself. |
| Median validator overhead | 2.87s | 2.59s | <span style="color:#c5221f;">+283 ms</span> | Shows harness validator overhead added after the live Codex session completes. |
| Median live session input tokens | 0 | 99,370 | <strong style="color:#137333;">-99,370</strong> | Shows full live Codex session input across the multi-turn run, not just the first prompt. |
| Median total model tokens | 0 | 101,205 | <strong style="color:#137333;">-101,205</strong> | Shows total live model-token spend across the multi-turn session. |
| Required-path recall rate | 0.994 | 0.756 | <strong style="color:#137333;">+0.238</strong> | Higher means Odylith finds more of the repo surfaces the task truly depends on. |
| Required-path precision rate | 0.888 | 0.661 | <strong style="color:#137333;">+0.227</strong> | Higher means Odylith keeps the evidence cone tighter and more relevant. |
| Hallucinated-surface rate | 0.112 | 0.339 | <strong style="color:#137333;">-0.227</strong> | Lower means less made-up or unnecessary surface spread. |
| Validation success rate | 0.886 | 0.829 | <strong style="color:#137333;">+0.057</strong> | Higher means the lane more often reaches a validator-backed correct outcome. |
| Critical required-path recall rate | 0.983 | 0.768 | <strong style="color:#137333;">+0.215</strong> | Protects high-stakes cases from missing critical repo truth. |
| Critical validation success rate | 1.000 | 0.935 | <strong style="color:#137333;">+0.065</strong> | Protects critical changes from silent regressions. |
| Expectation success rate | 0.841 | 0.234 | <strong style="color:#137333;">+0.607</strong> | Higher means more scenarios finish the stated task contract on the live run. |

> [!NOTE]
> Current live-proof status: `hold`.
> Comparison contract: `full_product_assistance_vs_raw_agent`.
> Fairness contract passed: `True`.
> Full tracked-corpus coverage rate: `1.000`.
> `benchmark_compare` remains release-warn until a shipped release baseline is recorded in `docs/benchmarks/release-baselines.v1.json`.
