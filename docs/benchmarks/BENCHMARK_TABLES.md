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
| Lane role | primary candidate | odylith_off / raw host CLI honest baseline | Odylith policy vs raw host | Keeps the internal diagnostic benchmark honest: full Odylith packet and prompt construction versus the raw host CLI prompt bundle on the same task. |
| Scenario count | 82 | 82 | +0 | Both lanes run the exact same corpus, so the comparison stays apples-to-apples. |
| Median packet time | 58.529 ms | 0.012 ms | <span style="color:#c5221f;">+58.517 ms</span> | Shows the packet construction time on the internal diagnostic benchmark before any live Codex session begins. |
| Mean packet time | 81.359 ms | 0.014 ms | <span style="color:#c5221f;">+81.345 ms</span> | Shows the mean packet time so slow prompt-build cases stay visible. |
| P95 packet time | 211.377 ms | 0.035 ms | <span style="color:#c5221f;">+211.342 ms</span> | Shows the long-tail packet time instead of hiding it behind the median. |
| Median prompt-bundle build time | 60.518 ms | 0.000 ms | <span style="color:#c5221f;">+60.518 ms</span> | Shows time spent inside Odylith packet construction and prompt shaping on the internal diagnostic benchmark. |
| Median grounding validation overhead | 0.649 ms | 0.012 ms | <span style="color:#c5221f;">+0.637 ms</span> | Shows post-build grounding harness overhead such as validation and accounting. |
| Median prompt-bundle input tokens | 972.0 | 101.0 | <span style="color:#c5221f;">+871.0</span> | Shows the model-facing prompt-bundle input size on the internal diagnostic benchmark. |
| Median total prompt-bundle payload tokens | 1225.0 | 101.0 | <span style="color:#c5221f;">+1124.0</span> | Shows the full grounding payload size across prompt, runtime contract, and operator diagnostics. |
| Required-path recall rate | 0.916 | 0.600 | <strong style="color:#137333;">+0.316</strong> | Higher means Odylith finds more of the repo surfaces the task truly depends on. |
| Required-path precision rate | 0.998 | 0.951 | <strong style="color:#137333;">+0.047</strong> | Higher means Odylith keeps the evidence cone tighter and more relevant. |
| Hallucinated-surface rate | 0.002 | 0.000 | <span style="color:#c5221f;">+0.002</span> | Lower means less made-up or unnecessary surface spread. |
| Validation-success proxy rate | 0.662 | 0.014 | <strong style="color:#137333;">+0.648</strong> | Higher means the internal diagnostic benchmark more often satisfies the benchmark validator proxy before any live Codex session begins. |
| Critical required-path recall rate | 0.867 | 0.611 | <strong style="color:#137333;">+0.256</strong> | Protects high-stakes cases from missing critical repo truth. |
| Critical validation-success proxy rate | 0.548 | 0.000 | <strong style="color:#137333;">+0.548</strong> | Protects critical grounding cases from missing packet-level validator proxy truth. |
| Expectation-success proxy rate | 0.927 | 0.104 | <strong style="color:#137333;">+0.823</strong> | Higher means more scenarios satisfy the stated task contract on the internal diagnostic benchmark before model execution begins. |

> [!NOTE]
> Current diagnostic status: `hold`.
> Fairness contract passed: `True`.
> Corpus seriousness floor passed: `True`.

## Live Signal Table

| Signal | odylith_on | odylith_off | Delta | Why It Matters |
| --- | --- | --- | --- | --- |
| Lane role | primary candidate | odylith_off / raw host CLI honest baseline | Odylith policy vs raw host | Keeps the public comparison honest: report-visible Odylith grounding, validation, and write-admission policy versus raw host CLI on the same measured contract. |
| Scenario count | 82 | 82 | +0 | Both lanes run the exact same corpus, so the comparison stays apples-to-apples. |
| Median time to valid outcome | 4.51s | 53s | <strong style="color:#137333;">-48s</strong> | Shows matched-pair benchmark time to valid outcome for the live run plus the harness validator, not interactive product latency. |
| Mean time to valid outcome | 19s | 59s | <strong style="color:#137333;">-40s</strong> | Shows the mean matched-pair benchmark time to valid outcome so long-tail slow cases stay visible. |
| P95 time to valid outcome | 1m 06s | 1m 43s | <strong style="color:#137333;">-37s</strong> | Shows the tail completion time for the slowest benchmark cases instead of letting the median hide them. |
| Median live agent runtime | 0.000 ms | 45s | <strong style="color:#137333;">-45s</strong> | Shows time spent inside the live host CLI session itself; zero-heavy Odylith rows are valid only as report-visible validator-backed closure stops. |
| Median validator overhead | 3.25s | 3.24s | <span style="color:#c5221f;">+4 ms</span> | Shows harness validator overhead added after the live host session completes. |
| Median live session input tokens | 0 | 245,205.5 | <strong style="color:#137333;">-245,205.5</strong> | Shows full live host session input across the multi-turn run, not just the first prompt. |
| Median total model tokens | 0 | 246,379.5 | <strong style="color:#137333;">-246,379.5</strong> | Shows total live model-token spend across the multi-turn session. |
| Required-path recall rate | 0.992 | 0.765 | <strong style="color:#137333;">+0.227</strong> | Higher means Odylith finds more of the repo surfaces the task truly depends on. |
| Required-path precision rate | 0.983 | 0.481 | <strong style="color:#137333;">+0.502</strong> | Higher means Odylith keeps the evidence cone tighter and more relevant. |
| Hallucinated-surface rate | 0.017 | 0.519 | <strong style="color:#137333;">-0.502</strong> | Lower means less made-up or unnecessary surface spread. |
| Validation success rate | 0.986 | 0.973 | <strong style="color:#137333;">+0.013</strong> | Higher means the lane more often reaches a validator-backed correct outcome. |
| Critical required-path recall rate | 0.979 | 0.774 | <strong style="color:#137333;">+0.205</strong> | Protects high-stakes cases from missing critical repo truth. |
| Critical validation success rate | 1.000 | 1.000 | +0.000 | Protects critical changes from silent regressions. |
| Expectation success rate | 0.951 | 0.299 | <strong style="color:#137333;">+0.652</strong> | Higher means more scenarios finish the stated task contract on the live run. |

> [!NOTE]
> Current live-proof status: `provisional_pass`.
> Comparison contract: `full_product_assistance_vs_raw_agent`.
> Fairness contract passed: `True`.
> Full tracked-corpus coverage rate: `1.000`.
