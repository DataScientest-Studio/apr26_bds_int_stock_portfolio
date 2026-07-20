# Consistency and correctness report on the research into a trade-decision algorithm for exchange markets communicating through OHLCV values, based on machine and deep learning

**Subject of the audit:** the `liora-project-ml-engineering` repository, epoch `2026-07-golden-v5`.
The audit was performed on the research branch `to_give_up_and_show`; in this copy of the document
the file references have been rewritten to the layout of the presentation branch
`Stable_Presentable_Version`, and references to the orchestration layer, which is not part of
this branch, are marked "(research branch)".
**Research status:** `research_status = FROZEN_FINAL_RESEARCH_SNAPSHOT`, presentation freeze
`presentation-v1/2026-07-golden-v5`.
**Audit date:** 2026-07-19.

Every number in this document was **measured** — by querying `data/results.db`, by parsing the
OOS read ledgers (research branch; their cumulative counters are summed in the
`oos_read_summary` table inside `data/results.db` — inspectable offline, not surfaced by the
console), or by reading the indicated place in the code. None was copied from the prose of
another document. Wherever a number comes from a file, `file:line` is given.

---

## 1. Verdict

**The research can be presented as methodologically sound — under the declared limitations of
section 4, which are part of the result, not a footnote to it.**

The core is healthy in a way that can be checked, not merely declared: the out-of-sample window
feeds no decision on the Train side, every read of it is counted in an append-only ledger, the
operating point is selected by one shared criterion instead of the best per fold, and the
interpretation layer also records unfavourable segments instead of showing only those that
confirm the thesis.

The most important property of this project from the audit's perspective is that **the headline
result is negative and is reported as such**. The median strategy loses to simply holding the
asset in both model families. The project does not try to mask this by choosing a metric or a
scope — and that is a stronger argument for the soundness of the workmanship than any positive
result would be.

What this document does **not** claim: that the described system has a market edge, that it is
fit for live use, or that the result generalizes beyond the examined window.

---

## 2. Research identity

| Field | Value | Source |
|---|---|---|
| Epoch | `2026-07-golden-v5` | `research_run` |
| Recipe hash XGB | `447745d1059e560f` | `research_run` |
| Recipe hash LSTM | `a4cc8f4a78ad8574` | `research_run`, recomputable from the OOS ledger module (research branch) |
| Train / OOS window — XGB | `2016-10-17 → 2023-12-29` / `2024-01-02 → 2026-05-29` | `research_run` |
| Train / OOS window — LSTM | `2017-01-01 → 2023-12-31` / `2024-01-01 → 2026-04-30` | `research_run` |
| Sealed rows | 498 XGB + 495 LSTM | `asset_results` |
| Artifacts | 993 folders, 5 files each | `artifacts/{xgb,lstm}/`, manifest `_meta.counts` |
| Integrity checks | **16 / 16 PASS** | `integrity_checks` |

A note on identity on this branch: the `research_run` identity fields in `data/results.db` are
anonymized (`epoch = 'sealed'`, `run_id = 'sealed-final'`,
`presentation_freeze = 'public/stable-2'`, `git_sha = NULL`). The epoch and freeze values in the
table above come from the audit performed on the research branch; the recipe hashes and time
windows are identical in both places.

`recipe_hash` covers the **configuration of the method**, not the input data. This is not an
oversight but a deliberate separation: the identity of the bars is recorded separately (the
corporate-action policy and `events_sha256` in `oos_read_summary.reason`), so that a data
correction can be repeated and compared against the **same** method hash. Folding both into one
digest would make every data fix look like a method change. The separation is declared
explicitly in `src/xgb/feature_search.py` in the documentation of the `recipe_hash` function
(`:93`).

---

## 3. What was checked and found solid

### 3.1 Isolation of the out-of-sample window

The check addressed the question: does **any** path exist through which a value from OOS
influences training, feature selection, HPO, or the operating point.

- The trimming of the Train set is a hard assertion, not a best-intentions filter:
  `src/xgb/pipeline.py:322-323` keeps only events satisfying
  `t0 + H + embargo <= oos_start`, and then **asserts** that no label window reaches into OOS.
- The same boundary is enforced inside cross-validation (`src/xgb/pipeline.py:848`,
  `:933`) — every engine window in every fold must end before the start of OOS.
- The OOS read has a single **choke point** with a gate in the research runner (research branch;
  the runner is not part of this branch, cf. `docs/ARCHITECTURE.md`): it refuses to read when
  the ledger has no open epoch. Instead of a warning there is an abort.

**Conclusion:** no leakage path from OOS into training decisions was found.

### 3.2 Read discipline — counted, not assumed

This is the place where the project says an uncomfortable thing about itself, and does so
correctly.

| Pipeline | Epoch cycles | Reads | Tickers | Read more than once |
|---|---|---|---|---|
| XGB | 3 | **588** | 498 | **89** |
| LSTM | 2 | **495** | 495 | **0** |

Breaking the XGB reads down into open/close cycles: cycle 2 is an **interrupted attempt** (89
reads / 89 tickers, zero repeats within the cycle), cycle 3 is the actual sealing pass (499
reads / 498 tickers, only AAPL repeated). The cumulative per-ticker read counter is 4–9
(mean 5.18) for XGB and 4–6 (mean 4.00) for LSTM.

The claim "every asset was read exactly once" would therefore be **untrue**, and it has been
removed from the project. The wording that matches the data is: *the OOS window is not an input
to any decision on the Train side, and every read of it is recorded in an append-only ledger;
the number of reads in an epoch can exceed the number of assets and is reported outright.*

The rationale for this construction is recorded in the ledger itself (the OOS ledger module,
research branch): re-sealing is allowed, whereas an **unrecorded** repeat read would be
indistinguishable from cherry-picking results.

### 3.3 The label and execution contract

The label does **not** mean "TP reached before SL". It means a positive net outcome after
passing through the entire execution contract — `src/lstm/pipeline.py:354`:

```
y = 1 if sim["local_per_unit_net_return"] > 0 else 0
```

That outcome is composed of: barrier triggering **at the close** (`BARRIER_MODE: close`), entry
at the next bar's open (`ENTRY_FILL: next_bar_open`), exit at the open of the bar following the
trigger (`EXIT_FILL: trigger_next_open`), the time-based exit at the close
(`SCHEDULED_EXIT_FILL: scheduled_moc_close`), a 1 bp commission and 2 bp slippage on both
sides, and the time barrier `H`. Events with an invalidating gap or invalid barrier geometry
are rejected (`GAP_INVALIDATED_SKIP`, `INVALID_BARRIER_SKIP`).

Barriers are tested **exclusively against the close price** (`BARRIER_MODE: close`;
`target_hit = s*(c[t]-tp) >= 0`). Bar highs and lows are not read, even though they are in the
data. A close-only scan will miss intraday touches — and since the stop lies closer (1×ATR)
than the target (2×ATR), it misses stops more often. The effect is therefore **conservative
with respect to win-rate**, not optimistic, but it is a real simplification of the contract and
that is what we call it here.

A consequence the project now names outright: **the nominal 2:1 geometry is not the realized
payoff.** The measured ratio of the average win to the average loss (computed from
`profit_factor` and the counts of wins and losses, over `ML_MULTI_TRADE` rows holding at least
one win and one loss) is:

| Model | Median | p25 | p75 | Share of assets ≥ 2.0 |
|---|---|---|---|---|
| XGB | **1.447** (n = 328) | 1.340 | 1.535 | **1.2%** |
| LSTM | **1.241** (n = 435) | 1.033 | 1.500 | **7.6%** |

For XGB that set coincides with every row carrying a computable profit factor (n = 328); for
LSTM it is 435 of the 445 rows with a profit factor — nine of the ten excluded rows have no
winning trade to average, and the tenth is the single non-promoted row that traded (LSTM CEG,
section 3.4).

The sentence "one win covers two losses" would therefore be true only for an idealized,
cost-free `+2R/−1R` payoff. It has been removed from the project.

### 3.4 The operating point and the notion of a promoted strategy

`src/shared/op_select.py` accumulates results **across all folds** and selects **one shared**
operating point for the whole Train window. A best theta per fold is explicitly forbidden as a
"fold oracle" — the rationale is in the module's documentation: no deployable strategy can
switch the threshold between folds. Criteria order: the trade floor (`min_oof_trades`), then
the spread across folds.

When nothing clears the floor, the point is flagged `trade_floor_met = False`, and the module
states outright that **the caller must not promote such a result**.

The distribution of selected thetas shows that the calibration genuinely works rather than
returning a constant:

- XGB (grid 0.40–0.60): `0.40 → 199`, `0.44 → 79`, `0.60 → 140`, the rest scattered;
- LSTM (grid 0.50–0.60): `0.50 → 178`, `0.52 → 100`, `0.54 → 98`, `0.56 → 63`, `0.58 → 35`, `0.60 → 21`.

**A distinction that had to be sharpened.** The `TRAIN_OOF_FLOOR_NOT_MET` state is not
identical to model idleness. In the whole universe there is **exactly one** row where the model
traded but the configuration was not promoted: **LSTM CEG, 40 model trades**, a result of
`+136.09%` against a benchmark of `+168.91%`. All 136 XGB rows with the floor not met have zero
trades — there, "idle" is an accurate description.

That is why the aggregate called the strategy result is computed via `trade_floor_met = 1 AND
model_trades > 0`, while the comparison diagram qualifies an asset by the sealed label
`result_mode = 'ML_MULTI_TRADE'`. It was verified that this label is **exactly equivalent** to
the condition `trade_floor_met = 1 AND model_trades >= 2` — zero discrepancies across 993 rows.

### 3.4b How the LSTM hyperparameters were actually chosen

The audit revealed a discrepancy between description and execution. The app told the reader
that both models are tuned by Optuna. **For the LSTM in this epoch, per-asset Optuna did not
run.** When a committed backbone exists (research branch: `lstm/data/universal_backbone.json`),
the research runner takes the architecture from `warm["arch"]` **instead of** calling
`M.hpo(...)`. The backbone carries one architecture (`hidden 32`, `num_layers 1`,
`dropout 0.3`, `lr 0.001`, `weight_decay 1e-4`), shared by all 495 assets; what remains
per-asset is the operating-point calibration (θ, direction) and feature selection.

The description in the app was corrected to say this outright, together with the fold-purity
caveat. A cold-start path with per-asset Optuna exists and is triggered by the
`LSTM_COLD_START=1` variable, but it was not used to seal this epoch.

### 3.5 Input data and corporate-action events

The split correction is applied on **hourly** bars, **before any aggregation**. The reason is
arithmetic and stated in the code: scaling commutes with `first/max/min/last`, but **not** with
the total volume sum — correcting after aggregation would corrupt the volume.

The detector table contains 88 events on 73 tickers; after 28 overriding entries (removals of
false positives, additions of events undetectable from bars) the effective state is **83 events
on 69 tickers**, `events_sha256 = 5989535b02f384f8`, recorded in `oos_read_summary.reason` of
both pipelines.

### 3.6 The interpretation layer

The layer reads the sealed artifact and Train rows — **never the OOS window**. Coverage: 16,601
feature-statistics rows, 16,601 contribution rows, 45,021 ENTRY-range segments.

The strongest evidence against selection toward a thesis: of the 45,021 segments only
**12,472** are marked with the `candidate_entry_region` flag, and the remaining **32,549 were
recorded despite carrying no highlight**. The flag is thus a presentational highlight, not a
storage filter — unfavourable segments are in the data.

Every payload carries three mandatory labels inside itself, so they cannot be lost in
processing: `TRAIN-DERIVED INTERPRETATION`, `NOT AN OOS RESULT`, `NOT A LIVE TRADING SIGNAL`.

### 3.7 The result — reported without smoothing

| | XGB (1h) | LSTM (daily) | population |
|---|---|---|---|
| Assets | 498 | 495 | whole universe |
| Median return | **−1.78%** | **+2.25%** | all rows |
| Median buy & hold (same window) | **+22.16%** | **+23.09%** | all rows |
| Median model trades | 86.5 | 28 | all rows |
| Median profit factor | **0.935** (n = 328) | **1.013** (n = 445) | rows with a computable PF |
| Beats its own benchmark | **72 / 498 (14.5%)** | **129 / 495 (26.1%)** | whole universe |
| Median return — promoted only | **−7.58%** (n = 328) | **+0.75%** (n = 446) | `ML_MULTI_TRADE` |
| Median trades — promoted only | 160.5 | 30 | `ML_MULTI_TRADE` |

**The populations must be read literally, because they differ between rows.** The medians of
return, benchmark and trades are computed over **all** rows — including non-promoted assets and
those that fell to the fallback, i.e. including results the model did not produce. Profit
factor exists only where the model traded, so its median has its own `n`: 328 for XGB (there
the set coincides exactly with the promoted ones) and 445 for LSTM (443 promoted + 1 with the
floor not met + 1 with a single trade; three `ML_MULTI_TRADE` rows have an empty PF). The two
rows added at the bottom show the same result **on promoted strategies only** — there it is
markedly worse for XGB (−7.58% versus −1.78%), because the whole-universe median is pulled up
by benchmark paths. The stricter version is the more honest one, and we give both.

The `result_mode` breakdown: XGB — 328 promoted, 136 with the floor not met, 33 fallback to
benchmark, 1 single trade; LSTM — 446 / 1 / 37 / 11.

---

## 4. Declared limitations

The following are not defects. They are conditions without which the result would be read more
broadly than it permits.

1. **Survivorship.** The universe is today's index constituents applied backwards. Aggregate
   results are therefore optimistic.
2. **A bull-market OOS window.** The years 2024–2026 make buy & hold an exceptionally hard
   benchmark; the result does not say how the method would behave in a different regime.
3. **Dividends not adjusted.** Only splits are corrected. The benchmark is therefore
   **price-only** — and that is exactly what keeps it on the same plane as the strategy.
4. **The split detector.** Ratios below 3:2 are not detectable from bars, because they fall
   within the range of ordinary post-earnings moves. The table passed a human review, but not
   an external verification against an independent source of corporate-action events.
5. **Fold purity under the LSTM warm start.** The backbone initializing the LSTM models was
   trained on the whole Train region, so a single fold's initialization saw Train rows from
   outside that fold. **This is not a leak from OOS**, but LSTM validation is not fully
   fold-causal. The methodology is OOS-isolating; it is not unconditionally "leak-free".
6. **Accumulation of OOS reads.** Described in 3.2. The sealed result is conditioned on
   knowledge from earlier reads of the same period.
7. **Verifier scope.** The `make verify-*` verifiers run on the research branch and reproduce
   a **sample** of rows: XGB compares 5 fields on a committed store of 15 tickers, LSTM 4
   fields on a sample of 10 tickers, both with a `1e-6` tolerance. This is a deterministic
   reproduction of selected rows, **not** byte identity and **not** the whole universe — the
   full XGB hourly store is not part of the repository. On this branch the artifact tree is
   verified with per-folder SHA-256 digests (`artifacts/manifest.json`), and the two executed
   notebooks in `examples/` show reproduced XGB **and LSTM** rows (the same ticker, one
   notebook per model).
8. **The interpretation is in-sample.** It describes the model's behaviour on the Train
   window. It is not an OOS result nor a trading signal.

---

## 5. Remediation path

The audit did not find the project in its final state — it was preceded by a series of fixes
(research-branch commits), which we record because it is part of the audit trail.

| Commit | What it addressed |
|---|---|
| `dcde5b97` | a single data-access layer; separation of the model result, the executed path and the benchmark; the Integrity page (page later removed in the four-page console refactor) |
| `e4f0c8d7` | previous-epoch numbers in the README; two false comments describing a mechanism |
| `cac93edf` | 12 consistency fixes: the promoted-strategy predicate, the payoff, "leak-free", the reproducibility scope, the README thesis |
| `8f61e288` | repair of the LSTM verifier; scoping of a clause that an earlier fix had made false |
| `fd403caa` | the last claims about a single read and set notation |

Two observations from this pass are worth recording, because they concern workmanship, not the
result:

**The presentation notebooks were one epoch behind — and claimed to be current.** Four
committed notebooks (two of them rendered by a Jupyter Notebook console page, itself removed
in the four-page refactor) came from the epoch before the split
correction and printed the NVDA result `436.32 USD / −56.37% / 1 trade`, accompanied by the
sentence "REPRODUCED the sealed row within 1e-6". The sealed v5 row says `3,390.08 USD /
+239.01% / 288 trades`. The reproduction claim was therefore **false against the current
store**, and it was visible in the presented app.

On top of that, it turned out these were not only old *results* but also old *code*: a cell
called `strategy_meta(..., BEST, {}, ...)`, passing an empty calibration record where the v5
pipeline requires an operating point from `op_select`. The XGB notebooks were reproduced by
executing the **canonical per-asset template** (research branch:
`xgb/src/notebook_template.ipynb` — the same one the research runner uses); the LSTM notebooks
were regenerated faithfully from the current LSTM runner (research branch), including the
warm-start path. All four runs were executed against a **scratch store** (`OOS_METRICS_DB`), so
they were not sealing reads and the ledgers remained untouched. Result: **4 / 4 reproduce the
sealed rows** (XGB NVDA `3390.0761316752228`, XGB AAPL `941.9721600160755`, LSTM NVDA
`1363.2486792394723`, LSTM AAPL `874.7211883830511`). Committed on this branch are two
executions **on the same ticker, one per model** — `examples/Example_XGB.ipynb` (XGB NVDA) and
`examples/Example_LSTM.ipynb` (LSTM NVDA) — so that the ML↔DL comparison is apples-to-apples.
The LSTM notebook carries its own reproduction gate (a comparison with the sealed row within
1e-6); the parity of both with the database is enforced by `make verify`.

**Fixes can introduce errors.** Tightening the promoted-strategy predicate moved CEG into the
"not promoted" bucket, which made that bucket's caption — "their capital path is the benchmark
path" — false precisely for CEG (2,360.89 USD versus a benchmark of 2,689.10 USD). The error
was caught only by independent adversarial verification, not by the author of the fix.

A second example from the same family: while separating the model result from the executed
path, I used the word "promoted" for the aggregate computed as `trade_floor_met = 1 AND
model_trades > 0` (786 rows), while the diagram's caption defined "promoted" as
`ML_MULTI_TRADE`, i.e. the floor **and at least two** trades (774 rows). The predicates are
each justified on their own — win shares need at least two trades to mean anything — but one
word for two different sets is an inconsistency. The vocabulary was split: the aggregate is the
**model result**, the diagram operates on the **promoted strategy**.

**Literal gates are brittle.** A check searching for exact strings let through a variant
phrasing ("one win **can** cover two losses") and the same phrase written in different letter
casing. Further review was then carried out with case-insensitive patterns. A caveat for the
reader: this was an **audit procedure**, not a repository artifact — the repo has no committed
gate scanning text for forbidden claims, so the check does not repeat by itself and every
subsequent review must be performed deliberately.

On the same occasion an active defect was found and fixed: the default `make verify-lstm` path
(research branch) had been aborting with an exception ever since the feature-override file
changed shape in the v5 epoch — the command the documentation tells the reader to run was
verifying nothing. After the fix it was run: **10 / 10 rows reproduced**.

---

## 6. What will be attacked first

**"You claim to read OOS once, yet the ledger shows 588 reads over 498 assets."**
We do not claim that, and it is written nowhere. The guarantee is not that the read happens
once, but that **every read is counted**. The 588 reads come from an interrupted sealing pass
(89 assets) and the proper pass (499 reads, one repeat — AAPL). The cumulative counters are
recorded in the sealed store (the `oos_read_summary` table in `data/results.db`). We name the
consequence outright: the result is conditioned on earlier reads of the same period.

**"If the barriers are 2:1, one win covers two losses — so a 33% hit rate is enough."**
It is not enough, because 2:1 is the nominal geometry, not the realized payoff. The measured
median win-to-loss ratio is 1.447 (XGB) and 1.241 (LSTM); the 2.0 threshold is reached by 1.2%
and 7.6% of assets. The difference is created by close-triggered barriers, entries and exits at
the open prices of the following bars, gaps, costs on both sides, and time-based exits.

**"Is this a leak-free methodology?"**
Free of leakage from OOS — yes, and that is enforced by assertions, not by declaration. But not
unconditionally "leak-free": the LSTM universal warm start was trained on the whole Train
region, so LSTM cross-validation is not fully fold-causal. We name this a restriction to OOS isolation with a
documented fold-purity caveat, not an absence of leakage altogether.

---

## 7. Summary

A deterministic, frozen presentation of an academic experiment comparing XGBoost and LSTM in
trade selection on S&P 500 data. The out-of-sample window remains separated from decisions on
the Train side, all of its reads are explicitly recorded, and the result of the final epoch is
**negative**. Per-asset artifacts are verified by hashes, and selected result rows are
deterministically reproduced from committed fixtures within the declared tolerance.

The project is neither a live-running system nor proof that a profitable edge exists. The
product is **the method and its auditability**: a description of the conditions under which the
model makes an entry decision, when it deliberately stays idle, and what exactly was measured
and what was not measured.
