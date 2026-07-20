# Independent methodological-integrity review of the ML system

> **Verification status (2026-07-18):** all file:line references and mechanism claims of this report were independently checked directly in the code — on the research branch `to_give_up_and_show` (commit `d8f920f`) and in the `src/` tree of the `Stable_Presentable_Version` branch. Result: **all mechanisms confirmed in the code**; relative to the original text four clarifications were applied: (1) lines `848/933` in XGB are fail-closed asserts, and the replay up to `hi` is performed by `op_grid_scores` (`pipeline.py:802–803`); (2) the OOS-read choke points live in the `run_asset.py` entrypoints, and the actual universe `read_count` is XGB = 4 / LSTM = 3 (historical values from before the v5 re-seal; the current figures — 588/495 reads, means 5.18/4.00 — are in §5.2); (3) the proposal DSL validator is a mechanism of the LSTM subsystem (XGB selects from a closed feature registry); (4) each cited document is annotated with the branch on which it exists.
>
> **Code-reference map:** the line references in the tables refer to the layout of the research branch (`xgb/src/pipeline.py`, `lstm/pipeline.py`, `lstm/model.py`, `lstm/feature_search.py`, `lstm/pretrain_universal.py`, `iterators/…`). Their counterparts on the `Stable_Presentable_Version` branch: `src/xgb/pipeline.py` (identical lines), `src/lstm/pipeline.py` (offset +1 for the pipeline construction), `src/lstm/model.py` and `src/lstm/feature_search.py` (identical lines), `src/shared/op_select.py` (formerly `iterators/op_select.py`), `src/xgb/artifact.py` (formerly `xgb/src/asset_writers.py`), `docs/METHODOLOGY.md` (counterpart of `docs/FEATURE_SEARCH_METHODOLOGY.md`). The orchestration layer (`run_asset.py`, the execution notebook, `iterators/`, the `oos_read_ledger.jsonl` ledgers, `pretrain_universal.py`) exists exclusively on the research branch.

## 1. Verdict

**Verdict: YES — the core of the ML system shows no look-ahead bias and no data leakage.**

The independent verification was carried out according to the mathematical, validation and engineering procedures applied as the industry standard when building machine-learning systems for time series and quantitative strategies.

The verification was adversarial in nature and was performed by three independent control agents. Approximately 30 protective mechanisms, constraints and fail-closed conditions were verified.

### Verification result

* number of detected `CRITICAL`-class problems: **0**,
* no access of OOS data to the process of creating features, labels, models or decision parameters,
* no mixing of the Train, Validation and OOS sets,
* protective mechanisms confirmed directly in the code of the current `HEAD` version,
* four known deviations from an ideal one-shot experiment were counted, documented and explicitly separated from the ML results.

The conclusion covers the entire core chain:

> **features → labels → CV → HPO → calibration → artifact → OOS execution**

---

## 2. Scope and method of the verification

The verification did not rely on declarations contained in comments, documentation or architecture descriptions.

Every guarantee was verified directly in the executable code of the system, with references to specific files and lines.

The audit covered in particular:

* label construction,
* the Train, Validation and OOS time boundaries,
* purge and embargo,
* cross-validation mechanisms,
* feature generation,
* data normalization,
* HPO and feature search,
* the LSTM model warm start,
* calibration of decision thresholds,
* strategy selection,
* the moment of artifact freezing,
* OOS data reads,
* read counters and ledgers,
* the fallback mode,
* historical experiments and methodological limitations.

---

## 3. Hard guarantees verified in the code

| Control mechanism                                       | Technical evidence                                                                                                                                                                                                                                                                                                                                                  |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Labels do not reach into the OOS period**             | The condition `t0 + H + embargo ≤ oos_start` applies, protected by asserts. XGB: `pipeline.py:320–324`. LSTM: `pipeline.py:178–182`. Barrier-simulation exits are additionally clipped to the last bar of the Train set in `simulate_trade`.                                                                                                                  |
| **CV folds do not cross the OOS boundary**              | Every scorer operating on the Train side carries fail-closed conditions. The assert boundary matches the engine's actual processing window. XGB: fail-closed asserts in HPO (`pipeline.py:848`) and in the operating-point calibration (`pipeline.py:933`); the engine replay up to `hi` is performed by `op_grid_scores` (`pipeline.py:802–803`). The LSTM uses the range up to `hi + H`, and the assert controls exactly that boundary: `model.py:201, 298`; `feature_search.py:288`. |
| **Features are causal**                                 | All time windows are trailing. Only `rolling`, `EWM` and `shift ≥ 1` operations are used. The proposal DSL validator (a mechanism of the LSTM subsystem: `lstm/features.py:276–341`) carries a whitelist of historical operators and rejects `shift < 1`; XGB has no DSL — the search selects exclusively from a closed registry of implemented features. The `1d` and `1w` context is attached via `merge_asof(direction="backward")` keyed on the close time of an already completed bar: `pipeline.py:536–548`. |
| **Normalization uses no future data**                   | In the LSTM pipeline the statistics of each fold are computed exclusively on data earlier than `val_lo − embargo`: `pipeline.py:224–239`. Whole-Train statistics are used only when building the final artifact destined for OOS.                                                                                                                        |
| **The warm-start backbone uses Train data only**        | The pooled panel is built exclusively from rows belonging to the Train masks. The data passes through purge, and the labels are restricted to the valid horizon: `pretrain_universal.py:74–99`. OOS data is never used to create the checkpoint.                                                                                                                     |
| **No OOS feedback into model decisions**                | The model artifact, the `θ` threshold and the feature set are frozen before the `D9/L9` read. Calibration and the floor are determined exclusively on Train-OOF. `op_select` is a pure function and has no access to result files. No `oos_metrics` reader influences the selection of the model or its parameters. The only branch dependent on the OOS result is the explicitly separated fallback. |
| **OOS reads are controlled and counted**                | Both `run_asset` entrypoints carry choke points blocking a read without an open experimental epoch (XGB `run_asset.py:43–46`, LSTM `run_asset.py:44–47`; backstop in `iterators/oos_ledger.py:136–154`). Every OOS read is recorded in a committed ledger (`{xgb,lstm}/data/oos_read_ledger.jsonl`) together with a `read_count` counter.                      |
| **Parameter selection happens before OOS**              | HPO, feature selection, threshold calibration, artifact selection and the execution configuration use exclusively Train or Train-OOF data. OOS participates in neither optimization nor candidate ranking.                                                                                                                                                              |
| **ML results are separated from execution benchmarks**  | The proper model result and the fallback mode carry distinct `result_mode` fields. The fallback has `trades=0` and `PF=None`, so it cannot be presented as the result of the ML strategy.                                                                                                                                                                          |

---

## 4. No look-ahead bias or data leakage in the pipeline core

Based on the audits performed, it can be stated that future data does not influence:

1. feature generation,
2. label construction,
3. fold partitioning,
4. candidate evaluation in CV,
5. the feature search,
6. HPO,
7. normalization,
8. threshold calibration,
9. model selection,
10. the construction of the final artifact,
11. decisions executed in the OOS period.

It is also significant that the safeguards are not limited to logical assumptions of the architecture. The system carries active asserts and fail-closed mechanisms which halt the process if the time boundaries are violated.

This means that the pipeline's correctness is enforced executably, not merely described declaratively.

---

## 5. Four explicit methodological limitations

The elements below do not constitute leakage in the core ML pipeline. They do not, however, correspond to an ideal strict one-shot experiment, and must therefore be disclosed whenever the results are presented.

> The broader consistency report (`Research_Consistency_Report.md` §4) declares **eight** limitations of the study; the **four** below are a procedural subset of the same set — the numberings of the two lists are independent.

### 5.1. The HODL fallback is selected after observing the number of trades

The switch to the mode:

> "buy on the first OOS day and hold until the end of the period"

occurs only after establishing that the model executed no trade over the entire OOS window.

Such a fallback is not executable ex ante, because the decision to activate it uses the information that `0 trades` occurred over the entire period.

For that reason the sealed epoch stores the fallback as a separate mode:

* a separate `result_mode`,
* `trades = 0`,
* `PF = None`,
* the fallback is never qualified as an ML result.

The fallback is exclusively an execution-mode benchmark. It must never be merged with the ML strategy's result nor presented as its outcome.

The presentation interface preserves this separation.

---

### 5.2. One-shot holds at the level of an epoch, not the whole project

The OOS window covering the `2024–2026` period (XGB: `2024-01-02` – `2026-05-29`; LSTM: `2024-01-01` – `2026-04-30`) was read multiple times across successive epochs. **State after the `2026-07-golden-v5` epoch (2026-07-19), straight from the ledgers:** in this epoch 588 reads were executed for the XGB universe (498 tickers) and 495 for the LSTM (495 tickers); the cumulative per-ticker `read_count` is **4–9 (mean 5.18) for XGB** and **4–6 (mean 4.00) for LSTM**.

A consequence that must be named outright: the sealed result is **not** a single, virgin read of the OOS window — it is a read conditioned on knowledge from earlier reads of the same period. The discipline here lies not in the read having been single, but in the fact that **every read is counted and recorded**: an unrecorded re-read would be indistinguishable from cherry-picking OOS results. The exact number of reads of each ticker is recorded in the ledgers as `read_count` and summed in the `oos_read_summary` table inside the sealed `data/results.db` (inspectable offline; not surfaced by the console).

Between individual epochs the methodology was improved. The changes covered primarily:

* removing detected sources of bias,
* strengthening purge and embargo,
* tightening the gates,
* adding asserts,
* eliminating the possibility of loosening the validation conditions.

This does not mean leakage inside the currently frozen epoch. It does mean, however, that the sealed result is conditioned on knowledge obtained during earlier reads of the same OOS period.

The project therefore does not pretend to be a laboratory-clean, first and only read. The experimental discipline here consists of:

* counting every read,
* separating the epochs,
* freezing the configuration before the next read,
* recording the history of the methodology,
* disclosing the dependence on earlier iterations.

---

### 5.3. LSTM initialization bias and gain inflation in the XGB search

During the warm-start process, the LSTM backbone saw rows belonging to the Train set originating from across different fold boundaries.

This does not grant access to OOS, but it may affect the absolute level of the results achieved in individual folds.

The practical interpretation is as follows:

* candidate rankings may be used,
* relative comparisons remain informative,
* absolute metric values should be interpreted with more caution.

In the case of XGB, a search conducted on a larger configuration superset may cause inflation of the gains reported in the search phase.

Both limitations are described in `docs/FEATURE_SEARCH_METHODOLOGY.md` (research branch `to_give_up_and_show`; warm-start bias: lines 79–88, gain inflation: 89–99). On the `Stable_Presentable_Version` branch the counterpart is `docs/METHODOLOGY.md` (§5 and the limitations table).

Configurations burdened with these mechanisms are not deployed directly into the production artifact without re-validation.

---

### 5.4. Universe survivorship bias and the historical pilot exception

The historical universe is built from the present-day composition of the S&P 500 index.

This causes classic survivorship bias, because the historical analysis does not contain all the companies that:

* previously belonged to the index,
* were removed from it,
* were acquired,
* went bankrupt,
* lost the required capitalization or liquidity criteria.

Additionally, in the historical pilot one feature candidate was evaluated after observing OOS. This concerned feature `906` (`xtf_zscore_1h_vs_1d`).

The case was documented in the pilot report `docs/FEATURE_PILOT_REPORT.md` (research branch only — no counterpart on this branch).

The current steer contract forbids such conduct. Today, evidence admitting a feature into the further process may come exclusively from Train-CV.

---

## 6. MINOR-class findings

The verification also revealed several `MINOR`-class problems. They do not affect the frozen results of the sealed epoch, but they constitute a technical-hardening list for future versions.

| Problem                                                                                    | Significance                                                                                                                                                                                                    |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **The scratch exemption checks for the presence of an environment variable instead of the validity of the path** | The mechanism should validate the specific path and its scope, not merely the fact that the variable is set.                                                                                                         |
| **The ledger is updated after the result row is written**                                  | A process failure between writing the result and writing the ledger may leave an incomplete audit trail. In the future the write should be transactional, or performed in the reverse order with a recovery mechanism. |
| **The DSL validator reads bars from the OOS period during the finiteness test**            | The data is used exclusively for structural checks, e.g. detecting `NaN` or `inf`, not for evaluating results or for selection. Despite the lack of decision impact, it is better to restrict validation to Train only.      |
| **Early stopping may observe validation inside a fold on the cold HPO path**               | This is local peeking within the tuning procedure of a given fold. It does not violate the OOS boundary, but it may slightly optimistically affect a configuration's score in the search.                                           |

The current epoch has `FROZEN` status, therefore the fixes are not applied retroactively.

Changing the code after seeing the results would violate the immutability principle of the frozen experiment. These elements should be fixed only in a subsequent, explicitly designated methodological epoch.

---

## 7. Rules for presenting results

In the presentation, the console and the reports, the following categories must be strictly separated:

| Category                        | Presentation                                                                     |
| ------------------------------- | -------------------------------------------------------------------------------- |
| **ML result**                   | The result of the frozen artifact, running on OOS with no post-read tuning.      |
| **HODL fallback**               | A separate execution benchmark; never as an ML result.                           |
| **Train-CV / Train-OOF**        | Results used for selection, calibration and stability assessment.                |
| **Sealed OOS**                  | The final generalization observation for a given epoch.                          |
| **Historical epochs**           | Results labeled with the epoch number and the count of earlier OOS reads.        |
| **Methodological limitations**  | Documented in `docs/METHODOLOGY.md` §6 and in these audits, never hidden or aggregated into the headline metric. |

The following identity and discipline fields must remain explicitly available to a reviewer:

* the epoch number,
* the `FROZEN` status,
* `read_count`,
* the applied purge,
* the embargo length,
* the label horizon `H`,
* the `oos_start` boundary,
* the result mode,
* the fallback information,
* the model initialization method,
* the survivorship-bias status,
* the list of known limitations,
* the list of `MINOR` findings,
* the code version or `HEAD` commit.

**Current state on the presentation branch.** The console's former `Integrity` page was
removed in the four-page refactor (July 2026); the fields above now live in the sealed
repository itself. `config/{xgb,lstm}.json` holds the frozen parameters: purge, embargo,
the label horizon `H`, `SEQ_LEN`, the warmup/Train/OOS bounds including `oos_start`, the
2×/1× ATR barrier contract, costs, fill conventions, the capital mode, the θ grid, the
trade floor and the seed. `data/results.db` holds the `research_run` identity with the
recipe hashes, `integrity_checks` (16/16 PASS), the `oos_read_summary` per-pipeline
ledger summary, and the `result_mode` matrix in `asset_results` with the fallback
contract. The model initialization method (universal warm-start LSTM vs per-asset Optuna
for XGB) is described in `docs/METHODOLOGY.md` §5, and the known-limitations list lives
in `docs/METHODOLOGY.md` §6 (eight rows, from the superset-HPO gain inflation and the
warm-start init through survivorship bias to the in-sample interpretation caveat). At
runtime the console enforces integrity fail-closed via `health()` (`app/data.py`) and
shows the `integrity_footer` caption on the Basket
Simulator page (sealed dataset · integrity N/M PASS · both OOS windows). **Deliberately
unavailable on this branch:** the epoch number and the `HEAD` commit — the identity
fields were anonymized at publication (`epoch = 'sealed'`, `git_sha = NULL`;
justification in `Research_Consistency_Report.md` §2), and the unchanged recipe hashes
act as the identifier.
The **MINOR-findings list** is section 6 of this document; the console does not
duplicate it — README and `docs/METHODOLOGY.md` §6 point to these audits instead.

---

## 8. Conclusion

The absence of look-ahead bias and data leakage in the chain:

> **features → labels → CV → HPO → calibration → artifact**

was confirmed by direct code analysis, active asserts, fail-closed conditions and an independent verification carried out according to mathematical and engineering industry standards.

OOS data does not influence the creation of features, the labels, model selection, parameter tuning, calibration or the construction of the final artifact.

At the same time, the project openly discloses the places where the procedure deviates from the laboratory ideal:

* the fallback activated after establishing the absence of trades,
* multiple epochs of reading the same OOS period,
* the LSTM warm-start initialization bias,
* the gain inflation in the XGB search,
* the universe survivorship bias,
* the historical pilot exception.

These limitations are counted, recorded in the ledgers and described in the documentation. On the presentation branch the console no longer displays them: at runtime it enforces the fail-closed integrity gate (`health()` in `app/data.py`), preserves the `result_mode` separation and renders the `integrity_footer` caption, while the ledger figures live in the sealed `data/results.db` (`oos_read_summary`) and the limitations list in `docs/METHODOLOGY.md` §6.

This is what separates a methodologically honest study from an embellished presentation: the system does not hide its deviations from the ideal, but defines their scope, impact and place in the decision process.
