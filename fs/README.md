# WO-FS — pętle selekcji cech (XGBoost + LSTM)

Realizacja dwóch zleceń: [`docs/XGB-ZLECENIE-LOOP.md`](../docs/XGB-ZLECENIE-LOOP.md) (WO-FS-XGB-v1)
i [`docs/LSTM-ZLECENIE-LOOP.md`](../docs/LSTM-ZLECENIE-LOOP.md) (WO-FS-LSTM-v1). To **osobne studium
badawcze** obok zapieczętowanych pipeline'ów `xgb/` i `lstm/` — czyta ich dane w trybie *read-only*
i nigdy nie dotyka ich wyników (`make verify-xgb`/`verify-lstm` zostają zielone).

**Metodologia (inna niż sealed v2):** wspólne, **3-klasowe** etykiety Triple Barrier {−1, 0, +1} na
zdarzeniach **CUSUM** (1h), **jeden uniwersalny model** na panelu tickerów (nie per-asset), metryka
**macro-F1**, walidacja Purged K-Fold(k=5)+embargo → **CPCV(6,2)** → **holdout czytany raz**, na końcu
**PBO** i **DSR**.

## Uruchomienie (demo — 15 tickerów, gotowe tego samego dnia)

```bash
make deps            # jedno .venv (już zawiera scipy via scikit-learn)
make fs-test         # bramki poprawności (anty-lookahead, wyciek scalera, purge/embargo, CPCV, unit)
make fs-study1       # kalibracja + zamrożenie wspólnych etykiet (Optuna Study 1)
make fs-xgb          # pętla XGB: eliminacja → stabilność → Study 2 → CPCV → SHAP
make fs-lstm         # pętla LSTM: eliminacja kanałów → stabilność → Study 2 → CPCV → SHAP
make fs-holdout-xgb  # JEDEN odczyt holdoutu (strażnik flagi) — świadomie, na końcu
make fs-holdout-lstm
make app             # Streamlit → w sidebarze przełącz „Tryb” na „Studium selekcji cech (WO-FS)”
```

Pełne uniwersum (~498 tickerów): dopisz `UNIVERSE=full` do każdej komendy. Wymaga lokalnego
`xgb/data/liora.duckdb` (160 MB, gitignored; budowa w `xgb/`). Pętle mają wbudowany **tryb oszczędny**
(podpróba tickerów + mniej epok w rundach; finalista trenuje na wszystkim) — patrz `fs/config.json`.

## Kontrakt danych i interpretacje (odnotowane odstępstwa)

| Temat | Decyzja | Uzasadnienie |
|---|---|---|
| Bary 1d | **natywny** store `lstm/data/sp500_1d.duckdb` | WO-XGB §1 zakazuje resamplingu 1h→1d |
| Bary 1w | agregat ISO-tygodnia z **natywnego 1d** | jedyna dostępna ścieżka native-derived |
| Zegar decyzji | `timestamp` = OPEN interwału; decyzja = CLOSE = open+1h | konwencja sealed pipeline'ów |
| Alignment 1d/1w | `merge_asof(backward, allow_exact_matches=False)` na `available_at` | ostatnia ZAMKNIĘTA świeca + jawny lag 1 bara TF (WO §1) |
| `available_at` | close ostatniego bara 1h danej sesji / ostatniej sesji tygodnia | early-close obsłużone przez dane, nie kalendarz |
| SHAP LSTM | `method='perm'` (fallback WO §5) | `shap`→`numba` wymaga numpy<2.5, a repo jest przypięte do numpy 2.5; GradientExplainer w osobnym env (patrz `requirements.txt`) |

## Mapa: sekcja zlecenia → kod

| WO | Realizacja |
|---|---|
| §1 kontrakt danych, hierarchia TF, anty-lookahead | `data.py` (`bar_frame`, `_join_context`, `tf_hierarchy_check`), bramka w `tests.py::test_anti_lookahead_gate` |
| §1 pula cech (≤4/TF + cross-TF) | `features.py` (`POOL_1H/1D/1W/XTF`, `MR_CHANNEL`); kernele adaptowane z `xgb/src/pipeline.py` |
| §2 CUSUM + Triple Barrier 3-klasy + wagi uniqueness | `labels.py` (`cusum_events`, `triple_barrier`, `uniqueness_weights`) |
| §3/§2 Purged K-Fold + embargo + CPCV + holdout×1 | `validation.py` (`purged_kfold`, `cpcv_splits`/`cpcv_paths`, `holdout_guard`, purge=H\|L+H) |
| §4 pętla XGB (klastry ρ, clustered MDA, 1-SE, π) | `xgb_loop.py` (`corr_clusters`, `clustered_mda`, `run_elimination`, `stability`) |
| §4 pętla LSTM (sekwencje, scaler/fold, perm+ablacja) | `lstm_loop.py` (`build_X`, `fold_scaler_stats`, `channel_perm_importance`, ablacja w `run_elimination`) |
| §5 SHAP per asset → DuckDB `feature_importance_shap` | `xgb_loop.shap_stage` (treeshap), `lstm_loop.shap_stage` (gradientshap/perm), `report.py` |
| §6 macro-F1 + P/R + PR-AUC + MCC + log-loss; PBO; DSR | `metrics.py` |
| §7 Optuna Study 1 (etykiety, wspólne) + Study 2 (HPO) | `xgb_loop.study1/study2`, `lstm_loop.study2` |

## Artefakty (`fs/artifacts/<universe>/`)

`labels_frozen.json` (wspólna prawda etykiet + `run_id`) · `loop_{xgb,lstm}.json` (trajektoria ±SE) ·
`selected_{xgb,lstm}.json` (π + selected) · `xgb_feature_ranking.json` (start dla LSTM) ·
`study2_{xgb,lstm}.json` (HPO + p*) · `verdict_{xgb,lstm}.json` (holdout, PBO, DSR) ·
`optuna.db` · `fs_results.duckdb` (tabele: `feature_importance_shap`, `shap_universality`,
`loop_rounds`, `cv_scores`, `trial_slices`, `stability`, `verdict`) · `holdout_used_*.flag` (strażnik).

Małe artefakty **demo** są commitowane (aplikacja renderuje się natychmiast po klonie); cache cech,
scalery i cały run `full/` są gitignorowane.

## Dyscyplina badawcza

Wszystko wybierane jest **wyłącznie na CV** (Train). **Holdout (2024→2026) czytany dokładnie raz** —
funkcja holdoutu tworzy flagę; drugi odczyt rzuca wyjątek. Determinizm: `seed_everything` + jednowątkowy
model → powtórka daje identyczny wynik (`tests.py::test_determinism`). Wynik jest raportowany
uczciwie, nie kurowany — macro-F1 ~0.39 na 3 klasach to skromny, ale realny sygnał ponad losowym.
