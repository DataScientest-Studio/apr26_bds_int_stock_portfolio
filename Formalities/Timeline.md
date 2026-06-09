# Project Timeline & Formalities — Liora "Stocks Recommender Based on User Profile"

**Training course:** Data Scientist · **Difficulty:** 8/10 · **Mentor:** Paul Grolier
Framing meeting: **2026-05-13** (Zoom). Original kickoff: Slack thread (Paul Grolier).

## Deadlines

| Step | Deliverable | Deadline |
| ---- | ----------- | -------- |
| 0 | Framing meeting | Week of 2026-05-11 |
| 1 | Data mining + DataViz | **2026-05-27** |
| 2 | Pre-processing + feature engineering → **Rendering 1** | **2026-06-03** |
| 3.1 | Modeling — baseline models, first iterations | **2026-06-10** |
| 3.2 | Modeling — ML metrics, optimization, model comparison | **2026-06-24** |
| 3.3 | Modeling — bagging/boosting, Deep Learning, interpretability → **Rendering 2** | **2026-07-01** |
| 4 | Final report + clean commented code on GitHub | **2026-07-08** |
| 5 | Streamlit application + oral defense | **2026-07-21 → 2026-07-23** |

## Step requirements

- **Step 1 — Data mining + DataViz** _(2026-05-27)_: define context/scope, near-exhaustive dataset analysis (structure, difficulties, biases) using the _TEMPLATE - Data Audit_; ≥ 5 relevant visualizations, each with a business comment validated by data manipulation or a statistical test.
- **Step 2 — Pre-processing + feature engineering** _(2026-06-03)_: cleaning, transformations, feature engineering, dataset enrichment → dataset ready for ML/DL.
- **Step 3 — Modeling** _(2026-06-10 → 2026-07-01)_: baseline → optimization → advanced (bagging/boosting + Deep Learning) → interpretability + scientific & business conclusions.
- **Step 4 — Final report** _(2026-07-08)_: merges Renderings 1 & 2, adds conclusion + opening, plus clean commented code on GitHub.
- **Step 5 — Defense** _(2026-07-21 → 2026-07-23)_: 20 min presentation + 10 min jury Q&A. Streamlit app must be multi-tab, carefully coded (**no re-training at runtime**), bug-free.

> Reports must include illustrations, proper layout, no spelling mistakes. **Reports not up to standard or late will not validate the project.** Mentor confirmed (2026-05-28): deliverable format is **PDF**, template flexible (Markdown/Overleaf/…). Written feedback on Renderings 1 & 2 feeds the final report.

## Deliverables

- Exploration, data visualization & pre-processing **report** (Rendering 1) — ✅ delivered 2026-06-03 (`Rendering1/report_v1_June_03_2026.pdf`).
- Modeling **report** (Rendering 2) — due 2026-07-01.
- Final **report** + associated **code** — due 2026-07-08.
- **Streamlit** application + oral **defense** — 2026-07-21 → 2026-07-23.

## Actions

- [x] Decide data source — Alpaca free IEX feed for S&P 500 daily OHLCV (mentor-approved 2026-05-22); yfinance kept as cross-check (later moved to `Archive/experiments/yfinance/`). DAX 40 deferred.
- [x] Migrate `fetch_data.py` from yfinance to Alpaca (2026-05-24).
- [x] Streamlit skeleton + 6 EDA visualizations + Data Audit (mentor-reviewed 2026-05-28).
- [x] Rendering 1 PDF delivered 2026-06-03.
- [ ] Per-ticker history-length column in EDA (flag short-history entrants, e.g. SNDK).
- [ ] With-vs-without outliers modeling comparison (mentor 2026-05-28).
- [ ] XGBoost vs Random Forest comparison across data preparations.
- [ ] Attend Paul's "Introduction to Deep Learning" masterclass (2026-06-11).

## Reference documents (provided by Liora)

- Stock Portfolio Recommender — project brief (Google Drive).
- Projects_methodology_reports — report-writing guide.
- TEMPLATE - Data Audit — Step 1 dataset analysis template.
- Defense_Methodology — defense organization document.
- Teaching Assistants — Calendly booking page.

## Bibliography

- Aroussi, R. — _yfinance documentation_.
- López de Prado, M. (2018). _Advances in Financial Machine Learning_. Wiley.
