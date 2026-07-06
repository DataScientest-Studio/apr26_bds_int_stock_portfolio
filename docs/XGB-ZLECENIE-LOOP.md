# WO-FS-XGB-v1 — Pętla selekcji cech dla modułu XGBoost (Projekt 1)

| Pole | Wartość |
|---|---|
| ID / Status | WO-FS-XGB-v1 / DRAFT do akceptacji |
| Cel | Minimalny, stabilny, nieprzeuczony zbiór cech maksymalizujący **macro-F1 OOS** dla XGBoost na etykietach Triple Barrier; **uniwersalny** dla 498 tickerów S&P 500 |
| Dane | DuckDB, 498 tickerów, OHLCV 1h / 1d / 1w |
| Stack (zamknięty) | Python + DuckDB + pandas/pyarrow + scikit-learn + XGBoost + Optuna — **zero nowych zależności** (SHAP liczony natywnie: `Booster.predict(pred_contribs=True)`) |
| Poza zakresem | Produkcyjny sygnał/egzekucja, model kosztów, corporate actions, HPO finalne poza Study 2 |

---

## 1. Kontrakt danych i cech

**Hierarchia TF (walidacja):** 1w → 1d → 1h; proporcje 1d/1h ≈ 7× (RTH), 1w/1d = 5× — obie ≥ 3×, hierarchia poprawna. Wskaźniki liczone z **natywnych barów** każdego TF (zakaz resamplingu 1h→1d).

**Pula cech startowych (limit: ≤ 4 wskaźniki / TF, po 1 na kategorię obserwacyjną):**

| Kategoria | 1w (kontekst/reżim) | 1d (setup) | 1h (timing) |
|---|---|---|---|
| Trend | znak+siła nachylenia MA (znormalizowane) | ADX + znak trendu | — |
| Momentum | — | RSI (0–1) | ROC / RSI (0–1) |
| Zmienność | reżim vol: ekspansja/kontrakcja (±1/0) | ATR% (bounded) | vol-z-score |
| Struktura | dystans do swing H/L (w ATR) | dystans do pivota (w ATR) | pozycja w range dnia (0–1) |

**Cechy cross-TF (mean-reversion, rdzeń projektu):** z-score ceny 1h względem MA(1d) i MA(1w) skalowany vol; spread RSI(1h)−RSI(1d); ratio vol(1h)/vol(1d); `alignment_score` = zgodność znaku trendu 1w/1d/1h ∈ {0,⅓,⅔,1}; flaga dywergencji między poziomami (0/1). Encoding: wartości znakowane/znormalizowane/ograniczone — bez surowych cen (stacjonarność).

**Alignment bez lookahead (reguły twarde):**
1. W chwili t (bar 1h) cechy 1d/1w pochodzą wyłącznie z **ostatniej ZAMKNIĘTEJ** świecy danego TF (`merge_asof backward` + jawny lag 1 bara TF).
2. **Test anty-lookahead (bramka):** opóźnij wszystkie cechy o 1 bar → jeśli metryka walidacyjna ROŚNIE, jest wyciek → STOP pipeline'u.
3. Panel long: `(ticker, ts_utc, X…, y, sample_weight, t1)`.

## 2. Etykieta Y i wagi

| Element | Definicja | Kalibracja |
|---|---|---|
| Zdarzenia | filtr CUSUM na 1h, próg h = f(vol) | Study 1 |
| Target vol | EWMA std zwrotów, span (default 100) | Study 1 |
| Bariery | TP = pt·vol, SL = sl·vol, pionowa = H barów 1h | Study 1 (pt, sl ∈ [0.5, 3]; H) |
| Klasy | y ∈ {−1, 0, +1} (pierwsza dotknięta bariera) | — |
| Wagi | average uniqueness (nakładanie etykiet) → `sample_weight` | — |

Baza zdarzeń = **1h** (decyzja stała v1, nie wymiar przeszukiwania); 1d/1w wyłącznie jako kontekst top-down.

## 3. Walidacja (moduł wspólny z WO-FS-LSTM-v1)

- **Purged K-Fold (k=5) + embargo**: purge = max lookback cech + H; embargo ≈ 1% obserwacji za każdym foldem testowym.
- **CPCV** (N=6 grup, k=2 test → 15 splitów, 5 ścieżek) do finalnej oceny → **rozkład** OOS, nie punkt.
- **Holdout OOS** (najświeższy okres): użyty **dokładnie raz**, po zamknięciu selekcji i HPO. Selekcja cech NIGDY na holdoucie.

## 4. Algorytm pętli selekcji

1. **START:** pełna pula (§1) + wagi (§2), etykiety zamrożone po Study 1.
2. **Klastrowanie korelacji:** odległość 1−|ρ| (Spearman), klastry hierarchiczne/ONC → grupy substytutów.
3. **Trening bazowy XGB** (regularyzowany, stały w pętli: max_depth 3–5, eta 0.05, subsample/colsample 0.8, λ/α > 0, `sample_weight`) na Purged K-Fold.
4. **Ranking:** clustered MDA (permutacja CAŁEGO klastra na OOF) — decyzyjny; SHAP (`pred_contribs`) — kontrola zgodności rankingu.
5. **Eliminacja wsteczna:** usuń najsłabszy klaster/cechę → wróć do 3.
6. **STOP gdy:** spadek macro-F1 CV > 1 SE od maksimum LUB brak poprawy przez 3 rundy LUB osiągnięto ≤ 15 cech. **Wybór: najmniejszy zbiór w obrębie 1 SE od najlepszego.**
7. **Stabilność:** powtórz pętlę na ≥ 20 bootstrapach (foldy × podpróby tickerów); do champion setu wchodzą cechy o częstości wyboru π ≥ 0.7.

## 5. SHAP per asset — artefakt obowiązkowy

Tabela DuckDB `feature_importance_shap` (liczona na predykcjach **out-of-fold**, nigdy in-sample):

| Kolumna | Typ | Opis |
|---|---|---|
| run_id / model / method | TEXT | wersja pętli / 'XGB' / 'treeshap' |
| ticker | TEXT | 1 z 498 |
| feature | TEXT | cecha champion setu |
| mean_abs_shap | DOUBLE | średnia \|SHAP\| na OOF danego tickera |
| shap_share | DOUBLE | udział znormalizowany per ticker (Σ po cechach = 1) |
| rank_in_ticker | INT | ranga cechy w tickerze |

**Zastosowanie:** (a) audyt uniwersalności — dla każdej cechy: mediana rangi, IQR rangi, `coverage` = % tickerów z shap_share > 1%; (b) detekcja cech asset-specific (silne w < 20% tickerów) → kandydaci do usunięcia; (c) raport: heatmapa 498 × |champion|.

## 6. Metryki

| Metryka | Rola |
|---|---|
| **macro-F1** (3 klasy) | GŁÓWNA decyzyjna (pętla, Optuna) |
| precision / recall per klasa | kontrola fałszywych sygnałów |
| PR-AUC, MCC | kontrolne przy niezbalansowaniu |
| log-loss | pruning Optuna |
| hit-rate, Sharpe, **PBO, DSR** | finalna ocena na CPCV/holdout |

Próg decyzyjny p\* dobierany na CV (po Study 2), nigdy na holdoucie.

## 7. Optuna — dwa rozdzielone studia (zakaz wspólnego mega-studium)

| | Study 1 — STRATEGIA (wspólne z Projektem 2) | Study 2 — HPO XGB |
|---|---|---|
| Parametry | pt, sl, H, span vol, próg CUSUM, π, N_max | max_depth, eta, n_estimators, subsample, colsample, min_child_weight, λ, α |
| Model w objective | referencyjny XGB (tani, stały) | XGB na champion secie |
| Cel | mean macro-F1 na Purged K-Fold | mean macro-F1 na Purged K-Fold |
| Budżet / sampler | 50–100 prób / TPE + MedianPruner (log-loss) | 100–150 prób / TPE + MedianPruner |

**Sekwencja:** Study 1 → zamrożenie etykiet → pętla selekcji (§4) → Study 2 → p\* na CV → CPCV → holdout ×1.
**Anty-przeuczenie Optuny:** purge+embargo wewnątrz objective; wąskie przestrzenie; liczba prób raportowana i uwzględniona w DSR (multiple testing).

## 8. Alternatywy (odrzucone dla ścieżki głównej)

| Wariant | Zaleta | Wada (powód odrzucenia) |
|---|---|---|
| A. RFECV na `gain` | najszybszy | bias in-sample, ślepy na substytucję |
| B. Ranking czysto SHAP bez klastrów | interpretowalny | korelacje rozmywają ważność; drożej |

## 9. Ryzyka i mitygacje

| Ryzyko | Mitygacja |
|---|---|
| Substytucja skorelowanych cech | klastrowanie + clustered MDA (§4.2, §4.4) |
| Niezbalansowanie klas | wagi + macro-F1/PR-AUC |
| Przeuczenie selekcji do jednej ścieżki | 1-SE + stabilność π + CPCV + holdout ×1 |
| Wyciek MTF | reguły §1 + test anty-lookahead jako bramka CI |

## 10. Kryteria akceptacji

- [ ] Champion set ≤ 10 cech; macro-F1 OOS (CPCV) ≥ pełna pula − 1 SE.
- [ ] `feature_importance_shap` kompletna: 498 × |champion| wierszy, OOF, `coverage ≥ 80%` dla każdej cechy.
- [ ] Test anty-lookahead: PASS; brak selekcji na holdoucie (audyt logów).
- [ ] PBO < 0.5 (cel < 0.1); DSR > próg ufności 95%; liczba prób Optuny zaraportowana.
- [ ] Powtarzalność: seed, wersje bibliotek, zapytania DuckDB w repo.

## 11. Definition of Done

- [ ] Pula cech per-TF + cross-TF wg §1 wygenerowana i zaudytowana.
- [ ] Triple Barrier + CUSUM + wagi unikatowości (§2).
- [ ] Moduł walidacji (Purged K-Fold, embargo, CPCV) — wspólny, testowany.
- [ ] Pętla §4 zautomatyzowana (Python, jedna komenda), logi rund.
- [ ] Tabela SHAP per asset + heatmapa (§5).
- [ ] Raport OOS: macro-F1, precision/recall, PR-AUC, MCC, PBO, DSR.
- [ ] Holdout użyty raz; wynik wpisany do raportu końcowego.

