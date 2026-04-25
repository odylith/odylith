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
| Lane role | primary candidate | odylith_off / raw host CLI honest baseline | full Odylith vs raw agent | Keeps the internal diagnostic benchmark honest: full Odylith packet and prompt construction versus the raw host CLI prompt bundle on the same task. |
| Scenario count | 82 | 82 | +0 | Both lanes run the exact same corpus, so the comparison stays apples-to-apples. |
| Median packet time | 24.255 ms | 0.010 ms | <span style="color:#c5221f;">+24.245 ms</span> | Shows the packet construction time on the internal diagnostic benchmark before any live Codex session begins. |
| Mean packet time | 24.565 ms | 0.011 ms | <span style="color:#c5221f;">+24.554 ms</span> | Shows the mean packet time so slow prompt-build cases stay visible. |
| P95 packet time | 51.265 ms | 0.024 ms | <span style="color:#c5221f;">+51.241 ms</span> | Shows the long-tail packet time instead of hiding it behind the median. |
| Median prompt-bundle build time | 24.022 ms | 0.000 ms | <span style="color:#c5221f;">+24.022 ms</span> | Shows time spent inside Odylith packet construction and prompt shaping on the internal diagnostic benchmark. |
| Median grounding validation overhead | 0.652 ms | 0.010 ms | <span style="color:#c5221f;">+0.642 ms</span> | Shows post-build grounding harness overhead such as validation and accounting. |
| Median prompt-bundle input tokens | 935.0 | 101.0 | <span style="color:#c5221f;">+834.0</span> | Shows the model-facing prompt-bundle input size on the internal diagnostic benchmark. |
| Median total prompt-bundle payload tokens | 1177.5 | 101.0 | <span style="color:#c5221f;">+1076.5</span> | Shows the full grounding payload size across prompt, runtime contract, and operator diagnostics. |
| Required-path recall rate | 0.926 | 0.601 | <strong style="color:#137333;">+0.325</strong> | Higher means Odylith finds more of the repo surfaces the task truly depends on. |
| Required-path precision rate | 1.000 | 0.951 | <strong style="color:#137333;">+0.049</strong> | Higher means Odylith keeps the evidence cone tighter and more relevant. |
| Hallucinated-surface rate | 0.000 | 0.000 | +0.000 | Lower means less made-up or unnecessary surface spread. |
| Validation-success proxy rate | 0.689 | 0.000 | <strong style="color:#137333;">+0.689</strong> | Higher means the internal diagnostic benchmark more often satisfies the benchmark validator proxy before any live Codex session begins. |
| Critical required-path recall rate | 0.889 | 0.611 | <strong style="color:#137333;">+0.278</strong> | Protects high-stakes cases from missing critical repo truth. |
| Critical validation-success proxy rate | 0.613 | 0.000 | <strong style="color:#137333;">+0.613</strong> | Protects critical grounding cases from missing packet-level validator proxy truth. |
| Expectation-success proxy rate | 0.963 | 0.000 | <strong style="color:#137333;">+0.963</strong> | Higher means more scenarios satisfy the stated task contract on the internal diagnostic benchmark before model execution begins. |

> [!NOTE]
> Current diagnostic status: `provisional_pass`.
> Fairness contract passed: `True`.
> Corpus seriousness floor passed: `True`.

## Live Signal Table

| Signal | odylith_on | odylith_off | Delta | Why It Matters |
| --- | --- | --- | --- | --- |
| Lane role | primary candidate | odylith_off / raw host CLI honest baseline | full Odylith vs raw agent | Keeps the public claim honest: full Odylith scaffold versus raw host CLI on the same task. |
| Scenario count | 82 | 82 | +0 | Both lanes run the exact same corpus, so the comparison stays apples-to-apples. |
| Median time to valid outcome | 5.15s | 1m 17s | <strong style="color:#137333;">-1m 12s</strong> | Shows matched-pair benchmark time to valid outcome for the live run plus the harness validator, not interactive product latency. |
| Mean time to valid outcome | 25s | 1m 35s | <strong style="color:#137333;">-1m 10s</strong> | Shows the mean matched-pair benchmark time to valid outcome so long-tail slow cases stay visible. |
| P95 time to valid outcome | 1m 35s | 4m 00s | <strong style="color:#137333;">-2m 25s</strong> | Shows the tail completion time for the slowest benchmark cases instead of letting the median hide them. |
| Median live agent runtime | 0.000 ms | 1m 10s | <strong style="color:#137333;">-1m 10s</strong> | Shows time spent inside the live host CLI session itself. |
| Median validator overhead | 3.29s | 3.06s | <span style="color:#c5221f;">+232 ms</span> | Shows harness validator overhead added after the live host session completes. |
| Median live session input tokens | 0 | 101,009.5 | <strong style="color:#137333;">-101,009.5</strong> | Shows full live host session input across the multi-turn run, not just the first prompt. |
| Median total model tokens | 0 | 103,238.5 | <strong style="color:#137333;">-103,238.5</strong> | Shows total live model-token spend across the multi-turn session. |
| Required-path recall rate | 1.000 | 0.748 | <strong style="color:#137333;">+0.252</strong> | Higher means Odylith finds more of the repo surfaces the task truly depends on. |
| Required-path precision rate | 0.979 | 0.719 | <strong style="color:#137333;">+0.260</strong> | Higher means Odylith keeps the evidence cone tighter and more relevant. |
| Hallucinated-surface rate | 0.021 | 0.281 | <strong style="color:#137333;">-0.260</strong> | Lower means less made-up or unnecessary surface spread. |
| Validation success rate | 0.973 | 0.905 | <strong style="color:#137333;">+0.068</strong> | Higher means the lane more often reaches a validator-backed correct outcome. |
| Critical required-path recall rate | 1.000 | 0.763 | <strong style="color:#137333;">+0.237</strong> | Protects high-stakes cases from missing critical repo truth. |
| Critical validation success rate | 1.000 | 0.968 | <strong style="color:#137333;">+0.032</strong> | Protects critical changes from silent regressions. |
| Expectation success rate | 0.939 | 0.247 | <strong style="color:#137333;">+0.692</strong> | Higher means more scenarios finish the stated task contract on the live run. |

> [!NOTE]
> Current live-proof status: `hold`.
> Comparison contract: `full_product_assistance_vs_raw_agent`.
> Fairness contract passed: `True`.
> Full tracked-corpus coverage rate: `1.000`.
> `benchmark_compare` remains release-warn until a shipped release baseline is recorded in `docs/benchmarks/release-baselines.v1.json`.
