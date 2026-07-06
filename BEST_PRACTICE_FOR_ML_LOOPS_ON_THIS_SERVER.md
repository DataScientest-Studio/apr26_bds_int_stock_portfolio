# Best practices for ML loops on this server

**Scope.** How to run feature-selection / hyper-parameter / cross-validation loops for OHLC-based ML
(XGBoost, LSTM, and similar) on **this box** without wasting time or hardware. It is written to be
**reused across projects** — it is not about any one repo. The `10000-xgb-lstm-liora/fs/` loop is used
only as a *worked example*: the concrete mistakes made there, and the configuration that fixed them.

**The one value everything below serves.** *Time is the scarce resource.* The goal of a run is the
**minimum wall-clock to a correct result** — not maximum CPU%, not "all cores pinned". CPU cycles and
RAM bytes are only useful when they are shortening the path to the numbers you need. Two failures are
equally bad and equally common:

- **Idle waste** — 14 of 16 cores sitting at 0% while one training crawls for an hour.
- **Thrash waste** — 16 cores oversubscribed with 75 threads, so everything runs *slower* than serial.

Both look busy on a dashboard. Only wall-clock tells the truth. **Match the parallelism to where the
heavy work actually is**, and let the rest stay deliberately idle.

---

## 1. This server (the numbers you're budgeting against)

| Resource | Value | Consequence for how you configure |
|---|---|---|
| CPU | **16 physical cores**, AMD EPYC-Genoa, **1 thread/core (no hyper-threading)** | 16 = your real parallel width. Budget **total concurrent threads ≈ 15** (leave one for the OS/IO). |
| RAM | **30 GiB, NO swap** | RAM overcommit does **not** slow down — it **OOM-kills** the process. Memory is a hard wall, not a soft one. |
| Disk cache | OS **page cache** (seen as `buff/cache`, often 10–15 GiB) | Reading a store once keeps it **hot in RAM for free**. Exploit this instead of re-reading from disk. |

Check them on any box before you size a run:

```bash
nproc                       # logical CPUs
lscpu | grep -E 'Core|Thread|Model name'
free -h                     # total / available / swap ; watch "available" during a run
```

Everything else in this document is derived from these three facts. On a different machine, re-read
them first and rescale (see §9).

---

## 2. The two knobs, and the one rule that governs both

Parallelism has exactly two independent knobs. Almost every performance bug is getting their **product**
wrong.

1. **Process-level** — how many worker *processes* you fan out (`multiprocessing`,
   `ProcessPoolExecutor`).
2. **Thread-level** — how many threads *each process* spawns inside its math libraries:
   - XGBoost → **OpenMP** (`nthread`)
   - NumPy/scikit / BLAS → `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`
   - PyTorch → `torch.set_num_threads()`

> ### The golden rule
> **`workers × threads_per_worker ≈ physical_cores`.**
>
> - Overshoot → oversubscription: threads fight for cores, context-switch storms, cache eviction. It
>   gets *slower*, sometimes catastrophically (see §3).
> - Undershoot → idle cores doing nothing while work waits (see §4).

Two corollaries that resolve almost every case:

- **When you fan out W workers, pin each worker to 1 thread.** `W × 1 = W ≈ cores`. Set the BLAS/OMP
  env caps to `1` *inside* the worker (before importing NumPy).
- **When you run ONE heavy job, give it all the threads.** `1 × (cores−1)`. Anything less leaves the
  box idle.

---

## 3. XGBoost loops — small models want *serial* folds

XGBoost trees for a 3-class OHLC label are **tiny**: one fold trains in ~0.4–2 s. For work that cheap,
the overhead of parallelising *dwarfs* the work.

> **Worked mistake (this project).** The 5-fold OOF was process-parallelised, each fold training with
> `nthread=15`. That is `5 workers × 15 OpenMP threads = 75 threads on 16 cores`. Measured on the same
> panel:
>
> | | wall-clock |
> |---|---|
> | serial fold `fit_predict` loop | **2.0 s** |
> | process-parallel folds (`nthread=15` each) | **248.3 s** |
>
> **124× slower.** Root cause: OpenMP oversubscription + per-fold spawn/IPC overhead, each ~100× the
> 0.4 s of actual training. After reverting to serial folds, the stability stage went from **93 min →
> 79 s**. (The code now carries this lesson inline — see `fs/xgb_loop.py:198`.)

**Rules for XGB loops:**

- **Fit and cross-validate serially** for small models. One process, `hist`, a modest `nthread`.
- **Parallelise only the genuinely heavy, embarrassingly-parallel parts:**
  - the **panel/feature build across tickers** (spawn pool, 1 thread each),
  - the **stability bootstraps** (each bootstrap = a full backward-elimination; 1 thread/worker).
- **Determinism:** XGBoost `hist` is deterministic at a **fixed `nthread` + fixed seed**. Reproducibility
  requires *recording the thread count* — the same code at a different `nthread` can differ in the last bits.
- **Economy without loss:** run the expensive **feature-selection** stage (MDA permutations, bootstraps)
  on a **representative ticker subsample** — it yields the same feature ranking. Then run Study-2 / CPCV
  / SHAP / holdout on **all** tickers. You pay full cost only where full coverage changes the answer.

The single final **refit/seal** is one heavy fit → give it all threads (§8). For XGB that is already
the case (`nthread = xgb_nthread`), which is exactly why the *XGB* seal was never the bottleneck.

---

## 4. LSTM loops — heavy training, so pick ONE parallelism per stage

A torch LSTM training is genuinely heavy (minutes, not milliseconds). Here parallelism *does* pay — but
you must choose, **per stage**, which knob to turn, because the two stage shapes are opposite:

| Stage shape | Example | Correct parallelism |
|---|---|---|
| **Many independent trainings** | CV/CPCV: 15 splits × 3 seeds = 45 trainings | **Fan out** over workers; **few** torch threads each. `W × t ≈ cores`. |
| **ONE big training** | finalist seal / `strategy` refit on the whole panel | **Single process, MANY torch threads** (`cores−1`). |

> **Worked mistake (this project).** `torch_threads = 2` was tuned for the *fan-out* CPCV stage (15
> workers × 2 threads = 30 ≈ throughput-optimal). But that same `2` **leaked into the single-training
> `strategy` seal**: a full-universe, 3-seed × 25-epoch refit ran at **~197% CPU (≈2 of 16 cores) for
> about an hour**, while **14 cores sat idle**. Nothing was wrong with the result — it was pure idle
> waste. Fix: single-training stages must raise the thread count to `cores−1`. (Implemented as
> `torch_threads_single` + an `apply_lstm_parallelism(single=…)` flag keyed on the stage.)

**Caveat — LSTM CPU scaling is sublinear.** A small-hidden LSTM (e.g. `hidden=32`) has small per-step
matmuls, so going 2 → 14 threads buys maybe **2–3×**, not 7×. Larger `hidden` / larger `batch` scale
better. It is still worth it: 2–3× off a one-hour stage is 30+ minutes. But size your expectations —
"more threads" is not free linear speedup.

**Correctness beats speed — the scaler leak.** The per-fold z-score scaler **must be fit on the training
window only**. Fitting it on holdout/warmup/test bars leaks the future into every fold and **silently
invalidates the entire run** (the metrics look fine — that's what makes it dangerous). The tempting
"compute the scaler once, globally, to save time" is exactly this leak. Bound the scaler to
`[cv_start, cv_end]` and exclude each test group's real-timestamp interval. **Never trade CV correctness
for speed.** Related: for sequence models, `purge = L + H` (the lookback window `L` extends the
contamination region past the horizon `H`).

---

## 5. RAM as a CPU-offload — compute once, then read at memory speed

The biggest speedups in a loop come not from more cores but from **not recomputing**. RAM's job is to
hold results so the CPU never redoes work.

**The warm pattern (`fs/warm.py`).** Before the loop starts, fan out over all cores and:

- **(a) build every ticker's feature frame once → a parquet cache**, keyed by
  `hash(feature_list + universe)`. Every downstream stage then *reads* features instead of recomputing
  indicators on every trial / fold / round.
- **(b) read the bars store once** (`page_cache_bars()`) so the OS keeps it hot in the page cache.
  Subsequent opens hit RAM, not disk.

**Cache the invariant; vary only what changes.** In label calibration (Study-1) the **labels** change
every trial but the **features do not** → the feature cache survives all trials, making each trial cheap.
Always separate the changing input from the fixed one and cache the fixed one.

**Per-feature column cache.** Cache each derived/proposed feature as *its own* column file. Adding one
new feature then computes only that column (in parallel, ~1 min) instead of rebuilding the whole panel.

**DuckDB / SQLite reads.** Open stores **read-only** (`duckdb.connect(..., read_only=True)`,
`sqlite3 ...?mode=ro`). Read-only handles are **shareable across processes** and **never block** a live
writer/worker; the OS page cache does the caching for you at no cost.

**Memory budget (no swap → hard wall).** Hot data in page cache + parquet caches + the current stage's
in-RAM panel all share 30 GiB. Watch `free -h` **available** during a run. If it trends toward zero,
reduce — in this order — **workers → batch → subsample**. Never let it hit the OOM-killer: with no swap
there is no warning, the process just dies. Reducing correctness (CV folds, embargo, scaler discipline)
to save RAM is never on this list.

---

## 6. `spawn` vs `fork`, and the stdin trap

- **Use `spawn`, not `fork`, for pools created after math libraries have started threads.** A `fork()`
  once OpenMP/BLAS/torch threads exist can **deadlock** the child (the child inherits locks held by
  threads that don't exist in it). Create pools with `multiprocessing.get_context("spawn")`
  (see `fs/xgb_loop.py:145`).
- **`spawn` re-imports your module in each worker → workers have no stdin.** So launching a parallel
  entry point via a heredoc (`python - <<EOF … EOF`) crashes with
  `FileNotFoundError: '<stdin>'`. **Launch parallel entry points as `python -m package.module`** (or
  from a real file), never piped stdin.
- **Set BLAS/OMP env caps *before* importing NumPy** in the worker — they are read at import time, so
  setting them afterward is silently ignored.

---

## 7. The convergence loop — stop when optimal, not when the clock runs out

A "run until it's as good as it gets, then stop and say so" loop, with **no time budget**:

- **Converged when, for `patience` consecutive rounds:** best CV metric gain `< min_gain` **AND** the
  selected feature set is unchanged **AND** no new candidate feature was accepted. A deterministic
  plateau (optimiser exhausted, no new input) is *also* convergence — without new input the loop
  **cannot** improve, so it is allowed to end. A `max_rounds` hard cap is a safety backstop, not a
  schedule.
- **Global convergence for a universal model.** When one model is trained over the whole asset panel
  (ticker is not a feature), converge **globally** on the pooled panel, then **audit per-asset coverage**
  (e.g. SHAP share ≥ threshold on ≥ X% of tickers). Do not converge per-asset.
- **Report quality honestly.** Convergence means "optimisation plateaued", **not** "the result is good".
  Always emit the honest quality flags next to the convergence flag: **PBO** (overfit probability, want
  `< 0.5`), **SHAP coverage** (want `≥ 0.8`), the **CPCV distribution**, **DSR**. A plateau reached at
  high PBO is reported as *"optimised to the limit, but overfit warning"* — never hidden behind the word
  "converged".
- **Resumable across a server change / kill.** Completed models leave a `converged_<model>.flag`; the
  optimiser state persists in `optuna.db`; all artifacts are written **atomically**. A relaunch skips
  converged models and continues the rest. This is what lets you move to a smaller box mid-run.
- **Never read the holdout inside the loop.** Guard it with a `holdout_used.flag`; a second read raises.
  The loop optimises on CV only.

---

## 8. Sealing the finalist / strategy — one heavy job, all the cores

After Study-2 + threshold selection, refit the finalist on the **whole CV panel**, **all seeds**, **full
epochs**, and seal it:

- serialise the model (base64 booster / state-dicts) + the scaler + the feature manifest + `p*`,
- add a **golden-vector selfcheck**: reload the sealed artifact and reproduce a few predictions
  **bit-for-bit** before trusting it.

This is a **single heavy training** → it gets **all cores** (§4, the `torch_threads_single` path).
Train on CV; read the holdout exactly **once**, separately. The XGB seal already does this correctly
(single fit at full `nthread`); the LSTM seal needed the single-training thread fix.

---

## 9. Configuration recipes — scale to your box and your data

**Where the knobs live.** A per-universe block plus environment overrides, every value **capped at
`os.cpu_count()-1`** so a smaller machine auto-adapts:

```jsonc
PARALLEL[universe] = {
  "xgb_nthread":          <threads for the single XGB fit/seal>,
  "torch_threads":        <threads PER WORKER in fan-out LSTM stages>,
  "torch_threads_single": <threads for a single-training LSTM stage (seal/holdout)>,
  "warm_workers":         <processes for the warm cache build>,
  "batch":                <LSTM batch size>
}
// overrides (all capped at cores-1):
//   FS_NTHREAD  FS_TORCH_THREADS  FS_PANEL_WORKERS  FS_*_SUBSAMPLE
```

| Scenario | Fan-out workers | threads/worker | single-training threads | warm_workers | selection subsample | batch | Notes |
|---|---|---|---|---|---|---|---|
| **This box** (16c / 30G) | ~15 | 1 (XGB) / 2 (LSTM) | **cores−1 = 15** | 15 | ~100 tickers | 512 | serial XGB folds; fan out only heavy stages |
| **Small box** (4c / 8G) | 3 | 1 | 3 | 3 | 40–60 | 128–256 | use **economy epochs**; RAM tight → fewer workers first |
| **Big box** (many cores) | =cores | keep `W×t≈cores` | cores−1 | =cores | can raise | 512+ | more cores ≠ faster *tiny* XGB folds; only single fits scale |
| **More DATA** (bigger universe / longer history) | unchanged | unchanged | unchanged | =cores | select on subsample, **finalist on full** | watch RAM | **RAM-first**: the warm cache is the win; if RAM-bound cut batch/workers, **not** correctness |

**Priority of levers when you are short on resources** (top = do first, bottom = never):

1. **Subsample the SELECTION stage** (feature ranking is stable under subsampling) — *not* the finalist.
2. **Economy epochs** for the selection loop; full epochs only for the sealed finalist.
3. **Fewer workers** if RAM-bound (no-swap wall).
4. **Smaller batch**.
5. **Never** cut CV rigor (folds, embargo, purge) or scaler correctness to save time.

---

## 10. Anti-pattern checklist (learn these from someone else's hour)

- ❌ Parallelising tiny XGB folds → **124× slower**. ✅ Serial folds for cheap models.
- ❌ A single big training at 2 threads while 14 cores idle (the 1-hour seal). ✅ `cores−1` threads for
  single-training stages.
- ❌ Treating **"is CPU at 1500%?"** as the success metric. ✅ Judge by **wall-clock**; high CPU on the
  wrong design is just faster waste.
- ❌ Computing the scaler "once, globally" for speed → **holdout leak**, whole run invalid. ✅ Fit per
  fold on train-only.
- ❌ `fork()` after threads exist (deadlock); heredoc into a `spawn` pool (`<stdin>` crash). ✅ `spawn`
  + `python -m module`.
- ❌ Recomputing indicators every trial. ✅ Cache the invariant (features) to parquet; vary only labels.
- ❌ `pkill` inside compound bash chains (mangled/`144` exit codes, half-killed processes). ✅ separate
  simple commands.
- ❌ Assuming linear thread speedup for small LSTMs. ✅ Expect **sublinear**; measure it.

---

## 11. Measurement discipline (the habit that prevents all of the above)

- **Time wall-clock, per stage, always.** Keep a stage-timing log (this project uses
  `supervisor_progress.json`). Without it you cannot tell "slow because heavy" from "slow because
  misconfigured".
- **Micro-benchmark SERIAL vs PARALLEL** on 2–3 tickers / 1 fold **before** committing to a parallel
  design. The 124× regression above was completely invisible until it was measured on a small slice —
  the parallel version *looked* correct and *looked* busy.
- **CPU% and RAM% are diagnostics, not targets.** The target is the result, produced in the least time,
  correctly. Everything in this document is in service of that, and nothing else.
