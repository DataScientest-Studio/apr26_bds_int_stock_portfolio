# WO-FS-LSTM-v1 — Pętla selekcji cech dla modułu LSTM (Projekt/folde/moduł 2)

WO-FS-XGB-v1 = /opt/to_liora_school/10000-xgb-lstm-liora/docs/XGB-ZLECENIE-LOOP.md

| Pole | Wartość |
|---|---|
| ID / Status | WO-FS-LSTM-v1 / DRAFT do akceptacji |
| Cel | **Mały** (≤ 8 cech), stabilny, nieprzeuczony zbiór cech-kanałów maksymalizujący **macro-F1 OOS** dla LSTM na etykietach Triple Barrier; uniwersalny dla 498 tickerów |
| Zależność wejściowa | **WO-FS-XGB-v1**: te same etykiety (Study 1) + ranking cech XGB jako punkt startowy |
| Dane | jak WO-FS-XGB-v1 §1 (DuckDB, 498 tickerów, 1h/1d/1w) |
| Stack | jak Projekt 1 + PyTorch + **wyjątek dep-policy: pakiet `shap`** (uzasadnienie §5) |
| Poza zakresem | zmiana architektury (CNN/TCN/attention), produkcja sygnałów, model kosztów |

---

## 1. Kontrakt danych: sekwencje i skalowanie

**Wejście modelu:** tensor `(L, F)` — okno L barów **1h** × F kanałów-cech. Kanały 1d/1w: forward-fill wartości z ostatniej **ZAMKNIĘTEJ** świecy wyższego TF (reguły alignmentu i test anty-lookahead identyczne jak WO-FS-XGB-v1 §1 — bramka obowiązkowa).

**Kontrakt skalowania (twardy — najczęstsze źródło wycieku):**
1. Wyłącznie cechy stacjonarne: zwroty / z-score / wartości bounded z puli WO-1; surowe ceny zakazane.
2. Scaler (**z-score**) fitowany **WYŁĄCZNIE na oknie treningowym danego foldu**, transform na val/test; parametry scalera zapisywane per fold (artefakt audytu).
3. Zakaz jakiejkolwiek statystyki liczonej na pełnym szeregu przed splitem.

## 2. Etykieta Y, wagi, walidacja

- **Identyczne etykiety** jak Projekt 1: parametry Triple Barrier z **jednego wspólnego Study 1** (uczciwe porównanie XGB vs LSTM; jedna prawda etykiet). Wagi = average uniqueness → wagi próbek w loss.
- Walidacja: wspólny moduł (Purged K-Fold k=5 + embargo, CPCV, holdout ×1), z jedną korektą: **purge = L + H** (okno sekwencji wydłuża nakładanie informacji) — nie samo H.

## 3. Architektura bazowa (stała w pętli — minimalizm)

| Element | Wartość |
|---|---|
| Sieć | 1–2 warstwy LSTM, 16–64 jednostek, dropout 0.2–0.5 |
| Głowa | softmax 3 klasy; loss = weighted cross-entropy (wagi §2) |
| Trening | early stopping po val macro-F1 (patience 5), weight decay, ≥ 3 seedy → uśrednienie |
| Okno L | parametr Study 2 (np. 32–128 barów 1h) |

## 4. Algorytm pętli selekcji (na sekwencjach)

1. **START:** kandydaci = **top-k rankingu z WO-FS-XGB-v1** (k = 12–15; tani pre-ranking) + obowiązkowo przedstawiciel cross-TF mean-reversion, nawet jeśli poza top-k (rdzeń tezy projektu — do zweryfikowania, nie założenia).
2. **Trening bazowy** (§3) w trybie oszczędnym: mniej epok / podpróba tickerów — pełna weryfikacja dopiero dla finalisty.
3. **Ranking kanałów:** *channel permutation importance* — tasowanie wartości JEDNEGO kanału w całym oknie na OOF (×10 powtórzeń, uśrednione po seedach) + **ablacja** (retrening bez kanału) dla top-kandydatów do usunięcia. Uzasadnienie: zależności temporalne i interakcje między krokami sprawiają, że pojedyncza permutacja nie izoluje czysto wkładu — stąd para permutacja+ablacja zamiast wag pierwszej warstwy (nieaudytowalne).
4. **Eliminacja wsteczna:** usuń najsłabszy kanał → wróć do 2.
5. **STOP:** spadek macro-F1 CV > 1 SE LUB brak poprawy 3 rundy LUB osiągnięto ≤ 8 kanałów. Wybór: najmniejszy zbiór w 1 SE.
6. **Stabilność:** ≥ 10 powtórzeń (foldy × seedy × podpróby tickerów); champion = kanały z π ≥ 0.7.
7. **Finalista:** pełny trening (pełne epoki, wszystkie tickery) → Study 2 → CPCV → holdout ×1.

## 5. SHAP per asset — artefakt obowiązkowy

Ta sama tabela DuckDB `feature_importance_shap` co w Projekcie 1, z `model='LSTM'`:

| Metoda | Opis | Kolumna `method` |
|---|---|---|
| **Główna:** GradientExplainer (pakiet `shap`) | próbka ≤ 256 sekwencji OOF / ticker; \|SHAP\| sumowany po krokach okna → wartość per kanał → średnia per ticker → `mean_abs_shap`, `shap_share`, `rank_in_ticker` | `gradientshap` |
| **Fallback zero-dep:** permutacja per ticker | Δ macro-F1 po tasowaniu kanału, per ticker | `perm` |

**Wyjątek od polityki zero-dependency (wymagane uzasadnienie):** `shap` — (a) standard branżowy audytu ważności, reimplementacja = większe ryzyko niż zależność; (b) używany wyłącznie w etapie raportowania, nie w runtime treningu/produkcji; (c) dojrzały, utrzymywany, wąska powierzchnia użycia (jedna klasa). Plan utrzymania: wersja przypięta; przy braku wsparcia → fallback `perm` bez zmiany schematu tabeli.

**Kryteria uniwersalności:** identyczne jak WO-1 §5 (mediana/IQR rangi, coverage ≥ 80%, flagowanie cech asset-specific).

## 6. Metryki

Jak WO-FS-XGB-v1 §6: **macro-F1** decyzyjna; precision/recall, PR-AUC, MCC kontrolne; log-loss do pruningu; PBO + DSR na końcu. Dodatkowo dla LSTM: **odchylenie std macro-F1 między seedami** (raportowane; wysokie = niestabilny trening, nie „lepsza cecha").

## 7. Optuna

| | Study 1 — STRATEGIA | Study 2 — HPO LSTM |
|---|---|---|
| Zakres | **WSPÓLNE z Projektem 1** — bez ponownej kalibracji (jedna prawda etykiet) | L, warstwy, jednostki, dropout, lr, batch, weight decay |
| Budżet | — (przejęte) | 50–80 prób / TPE + MedianPruner (log-loss per epoka) |

Sekwencja: etykiety z Study 1 → pętla §4 → Study 2 na champion secie → p\* na CV → CPCV → holdout ×1. Anty-przeuczenie: jak WO-1 §7 (purge+embargo w objective, wąskie przestrzenie, liczba prób do DSR).

## 8. Alternatywy (odrzucone dla ścieżki głównej)

| Wariant | Zaleta | Wada (powód odrzucenia) |
|---|---|---|
| A. Embedded gating / attention na wejściach | selekcja „za darmo" w treningu | mniej audytowalne, dodatkowa pojemność = ryzyko przeuczenia |
| B. Czysty ranking XGB bez własnej pętli LSTM | najtańsze | ignoruje sekwencyjność — cecha słaba punktowo może być silna temporalnie |

## 9. Ryzyka i mitygacje

| Ryzyko | Mitygacja |
|---|---|
| Wyciek statystyk scalera | kontrakt §1 + audyt artefaktów scalerów per fold |
| Wysoka wariancja treningu LSTM | ≥ 3 seedy, uśrednianie, raport std |
| Koszt SHAP na sekwencjach | sampling ≤ 256 sekwencji/ticker; fallback `perm` |
| Przeuczenie przy > 8 kanałach | twardy limit kardynalności + dropout + early stopping |
| Nakładanie okien L w CV | purge = L + H (§2) |

## 10. Kryteria akceptacji

- [ ] Champion set ≤ 8 kanałów; macro-F1 OOS (CPCV) ≥ zestaw startowy top-k − 1 SE.
- [ ] `feature_importance_shap` (model='LSTM') kompletna, OOF, coverage ≥ 80% per cecha.
- [ ] Kontrakt skalowania zweryfikowany testem (fit-transform tylko-train) + test anty-lookahead PASS.
- [ ] std macro-F1 między seedami zaraportowane; PBO < 0.5; DSR > 95%.
- [ ] Powtarzalność: seedy, wersje, scalery i konfiguracje w repo.

## 11. Definition of Done

- [ ] Generator sekwencji (L, F) multi-TF bez lookahead + testy.
- [ ] Kontrakt skalowania per fold zaimplementowany + test jednostkowy wycieku.
- [ ] Pętla §4 zautomatyzowana (jedna komenda), tryb oszczędny + pełna weryfikacja finalisty.
- [ ] SHAP per asset (gradientshap + fallback perm) → tabela + heatmapa.
- [ ] Study 2 + p\* + raport OOS (macro-F1, PR/RC, PR-AUC, MCC, PBO, DSR, std-seed).
- [ ] Holdout użyty raz; porównanie z wynikiem Projektu 1 na tych samych etykietach.
