# External Audit Brief — `Plan/` as a buildable single source of truth

**Engagement type:** independent, adversarial documentation & specification audit.
**Object:** the directory `/opt/to_liora_school/liora-project-ml-engineering/Plan/` (this folder), audited
**in isolation** — as if it is the only material an engineering team will receive.
**Language of all deliverables:** English.

---

## 1. Purpose & required outcome

Certify that `Plan/` is a **single source of truth (SOT)** that is:

1. **Consistent** — no fact contradicts another fact, within a file or across files.
2. **Logically sound** — every claim follows from its stated inputs; no orphan, circular, or unsupported claims.
3. **Strictly mathematically correct** — every formula is well-defined (all symbols resolve), dimensionally
   sound, and numerically self-consistent; every number agrees everywhere it appears.
4. **Buildable** — a competent engineer can implement the described project **from `Plan/` alone**, with no
   access to the upstream source repos, and reproduce the described behaviour.
5. **Self-describing** — the documents and the visualizations tell **one coherent story** under one set of
   conventions.

The auditor must issue a **PASS / CONDITIONAL-PASS / FAIL** verdict per §6, with evidence.

---

## 2. Object of audit — inventory

`Plan/` documents **two distinct pipelines** that share an `L#` prefix and **must never be conflated**:

- **Pipeline A — S&P 500 ML strategy, layers `L1–L10`** (Alpaca → LEAN ZIP → DuckDB → snapshot/parquet →
  time split → trend-line detector → features+triple-barrier → quality gate → Optuna/XGBoost → OOS test).
- **Pipeline B — OHLCV → L5 feature engineering, layers `L0–L5`** (raw OHLCV → atomic → rolling/temporal →
  MTF/regime → classical indicators → research representations); scoped to the **1h** store (native bar = 1h;
  resample **1h → 1d** only).

| File | Role | Pipeline | Format |
|---|---|---|---|
| `ENG/glossary_eng.md` | **Canonical terminology + conventions reference** | A (+ §"Pipeline B" for B) | Markdown |
| `ENG/summary_rules_eng.md` | The writing standard the summaries must obey (1:1 with source) | A | Markdown |
| `ENG/readme_eng.md` | Index of the `L1–L10` summaries | A | Markdown |
| `ENG/L1_…_eng.md … L10_…_eng.md` | Per-layer 1:1 summaries | A | Markdown |
| `README.md` | Package overview, two-pipeline framing, "Open the visualizations" | A + B | Markdown |
| `viz/main_data_flow.html` | Interactive 3D pipeline visualization | A | **Plaintext** HTML (directly editable) |
| `viz/feature_dag.html` | Interactive OHLCV→L5 feature-DAG wireframe | B | **Bundled** HTML — see §5.4 |

`glossary_eng.md` is the **canonical reference**: where any artifact disagrees with it on terminology,
naming, or a documented fact, the glossary wins (unless the auditor finds the glossary itself is wrong).

---

## 3. Acceptance criteria (what "PASS" means)

The auditor must verify each, independently:

- **AC-1 Naming conventions hold.** File names follow `L{n}_{slug}_eng.md` (n = 1..10) plus
  `readme_eng.md`, `summary_rules_eng.md`, `glossary_eng.md`; all lowercase, `_eng` suffix; viz names
  descriptive. The Pipeline-B feature-id grammar stated in the glossary matches **every** id in the viz.
- **AC-2 Canonical forms hold verbatim** across all artifacts (see §4.B list).
- **AC-3 Every formula is well-defined and correct** (see §4.C). No undefined symbols; guards (ε, σ=0)
  stated where division can be zero; standard indicators match their textbook definitions.
- **AC-4 Every number is consistent** everywhere it appears, and derivations check out (see §4.C).
- **AC-5 SOT 1:1.** The Pipeline-A glossary, the `L1–L10` summaries, and `main_data_flow.html` agree on
  the same facts (layer names, contracts, numbers). `summary_rules_eng.md` mandates this 1:1 rule.
- **AC-6 Two-pipeline integrity.** A's `L1–L10` and B's `L0–L5` are clearly separated and never mixed;
  any shared vocabulary is accurately marked as shared vs. intentionally divergent.
- **AC-7 Buildability.** From `Plan/` alone an engineer can implement both pipelines: every input contract,
  output contract, parameter, gate, formula, and artifact format needed to build is present or
  unambiguously referenced. The auditor must list any **buildability gap** (a fact required to build that is
  missing, ambiguous, or only referenced to an unavailable external doc).
- **AC-8 English-only**, links resolve, no dead references (e.g. no `index.html` ghost), both viz render.

---

## 4. Audit dimensions & checklist

### A. File & naming conventions
- `readme_eng.md` index ⇄ actual `ENG/` files: exact 1:1, no missing/extra `L`, all relative links resolve.
- `README.md` Contents/Open/Provenance links resolve to real files (`main_data_flow.html`, `feature_dag.html`).
- Pipeline-B feature ids: confirm they follow the glossary's stated grammar
  `l{layer}_{metric}[_{params}][_{timeframe}]`, with **family as a separate node attribute, not an id token**.
  Flag any id or any glossary example that violates the grammar.

### B. Terminology / canonical forms (glossary §"Canonical forms" is the reference)
Verify these hold verbatim across summaries + `main_data_flow.html` + `feature_dag.html`:
`DuckDB` (never "duck"/"kaczka"); `VIEW ohlcv_1h`; OOS metric order **PF · Sharpe · MDD · TIM · WR**;
`QC-01…QC-11`; **Pipeline A** `ATR = Wilder` vs **Pipeline B** `l4_atr` = plain rolling mean of TR
(intentional divergence — confirm it is labelled as such, not silently contradictory); `warm-up`/`warmup`;
`triple barrier` / `TB_v1.1`; `raw_usd_view`; timestamps **naive ET** until the F1 reader (UTC only at F1).

### C. Strict mathematical & numerical correctness
- **Pipeline B formulas** (`feature_dag.html` data): re-derive each (typical price, CLV, log-returns,
  ATR=mean(TR) with `TR=max(H−L,|H−C₋₁|,|L−C₋₁|)`, RSI, MACD, OBV, ADL, stochastic, MFI, VWAP, wick
  imbalance with `uw=H−max(O,C)`, `lw=min(O,C)−L`, z-scores/Bollinger with `σ=0→0` guard). Flag any
  undefined symbol, missing guard, or incorrect standard form.
- **Pipeline A formulas** (glossary L7 + `L7` summary + detector contract): `R0 = |close[t0] − L_opp(t0)|`
  (unsigned magnitude); `take_profit_level = close[t0] + direction·R0` (**direction factor required** — must
  be correct for shorts, not only longs); SL = moving `L_opp(t)`; time barrier `H=24`;
  `distance_to_trend_line = sign·(c−L_trend)/ATR`; `risk_if_entered_pct = |c−L_opp|/c·100`;
  `body_to_range_ratio = |c−o|/max(ε, h−l)`; `volume_z_score = (v−mean_20)/std_20, std=0→0`;
  `label_uniqueness_weight = mean(1/c_t)`. Confirm glossary and the `L7` summary **agree**.
- **Numbers** (must agree everywhere + derivations check): `503` universe · `510` zip (503 + extras) ·
  `8 841 820` rows · `~7` candles/day from `09:00–16:00 ET` · candles/day `∈ [5,9]` · `H=24` ·
  warm-up lookback `max(W_ATR=14, W_VOL=20)=20` candles · embargo `≈5 sessions (~35 candles)` ·
  `503` parquet files · `THRESHOLD_ENTRY=0.60` · `N_TRIALS=200` · prices `×10000`.

### D. Logical / SOT cross-file coherence
- Internal: each file self-consistent (no self-contradiction).
- Cross-file (Pipeline A): glossary ⇄ `L1–L10` summaries ⇄ `main_data_flow.html` state the **same** facts;
  any divergence is an SOT violation (the `summary_rules` 1:1 rule).
- Two-pipeline relationship: coherent and honestly described — Pipeline A's `L7` is a small hand-crafted
  8-feature / 7-X detector set; Pipeline B is a general feature library. Confirm the docs do **not** imply
  one *is* the other; confirm the shared-vocabulary claims are accurate.

### E. Buildability (the decisive criterion)
For **each** pipeline, attempt a paper build from `Plan/` only and record gaps:
- Are all **input/output contracts** per layer present and unambiguous?
- Are all **parameters** (the glossary `config/params.json` set) and **gates** (QC-01…11, the L8 dashboard
  FAIL→block) specified well enough to implement?
- Are all **artifact formats** (LEAN zip CSV layout, DuckDB schema + view, parquet schema, `strategy_<TICKER>.py`
  contract: `MODEL_B64`/`FEATURE_MANIFEST`/`LABEL_CONTRACT`/`THRESHOLD_ENTRY`/`selfcheck()`) specified?
- Is anything **only** obtainable from an external doc not in `Plan/` (e.g. "spec §N", "register C-xx",
  `FLOW/L*.md`)? List each such reference as a buildability dependency and state whether the needed fact is
  *also* stated in `Plan/` (OK) or *only* external (gap).

### F. Language & rendering
- No non-English text anywhere (including viz code comments and bundle payloads).
- Both viz render with no console errors; `feature_dag.html`'s bundle decodes; all `L#` labels present.

---

## 5. Methodology (required)

1. **Read everything in `Plan/` first**, treating `glossary_eng.md` as canonical.
2. **Independent re-derivation** of every formula and number — do not trust the text; recompute.
3. **Cross-file diffing**: for each Pipeline-A fact, compare the value in glossary vs summary vs viz; record
   any mismatch with all three quotes.
4. **Adversarial verification**: for every candidate finding, attempt to refute it before reporting; report
   only findings that survive (default to "not a defect" when a difference is intended and labelled, e.g.
   the two L-schemes, or A-Wilder vs B-mean ATR).
5. **Buildability dry-run**: write (do not execute) the build steps for each pipeline from `Plan/` only;
   every step that cannot be specified is a gap.
6. **Decode the Pipeline-B bundle** to read its real content. `viz/feature_dag.html` is a self-contained
   artifact bundle: its JS/JSX assets are **gzip+base64** inside `<script type="__bundler/manifest">`,
   referenced by uuid from `<script type="__bundler/template">`, decoded at runtime (`atob` +
   `DecompressionStream('gzip')`). To inspect: parse the manifest JSON, base64-decode each asset, gunzip,
   read. To *propose* a fix, describe the decoded-asset edit (the team re-packs: edit → gzip → base64 →
   replace the manifest entry, preserving uuid/mime/`compressed`). `viz/main_data_flow.html` is plaintext.
7. **Render check** both viz headlessly; capture a screenshot and the console log.

---

## 6. Deliverables

A single English report containing:

1. **Verdict:** PASS / CONDITIONAL-PASS / FAIL, with a one-paragraph justification.
2. **Per-criterion table** (AC-1 … AC-8): pass/fail + one-line evidence each.
3. **Findings register** — for every defect: `id · severity · file:location · issue · exact-quote evidence ·
   why it is wrong (re-derivation or contradicting quote) · precise repair (the exact edit)`.
4. **Buildability gap list** — facts required to build that are missing/ambiguous/external-only, each with
   the minimal addition needed to close the gap.
5. **Repair plan** — deduplicated, prioritized (must/should/optional), each a concrete edit to a named file.
6. **Sign-off statement**: "From `Plan/` alone, a competent team can build Pipelines A and B as described,
   and every formula/number/claim is internally consistent and mathematically correct" — or the explicit
   list of conditions that must be met before this statement can be made.

---

## 7. Severity definitions
- **critical** — blocks building, or a mathematically/logically wrong fact a reader would act on.
- **major** — a real contradiction or undefined/incorrect formula in a canonical place; misleads implementers.
- **minor** — local inconsistency, missing guard/qualifier, or stylistic divergence with no build impact.

## 8. Ground rules & constraints
- Treat `Plan/` as the deliverable; **do not** assume access to the upstream repos. Where the text references
  an external doc, that is a **buildability dependency** to flag, not an excuse to fetch it.
- `glossary_eng.md` is canonical for terminology/naming; if you believe the glossary itself is wrong, say so
  explicitly with proof.
- Preserve the existing **designs** of both visualizations; propose content/text/formula fixes, not redesigns.
- Different `L#` schemes for the two pipelines are **by design** (labelled) — not a defect.
- `Plan/` is a snapshot copy; if a fix should also propagate to the upstream source to avoid silent reversion
  on re-copy, note it (informational).

## 9. Out of scope
- Executing or back-testing the strategy; validating live data; performance/UX of the viz beyond rendering.
- Re-authoring the visualizations' visual design.

---

## Appendix — known baseline (for the auditor's starting context, to be re-verified independently)
An internal adversarial audit (4 dimensions → per-finding refutation → synthesis) was run and its confirmed
findings repaired prior to this engagement:
- Pipeline-B feature-id grammar corrected to `l{layer}_{metric}[_{params}][_{timeframe}]` (family is a
  separate `family:` attribute) — fixed in `glossary_eng.md` and the `feature_dag.html` title card.
- `feature_dag.html`: `l1_wick_imb` wicks defined inline (`uw=H−max(O,C)`, `lw=min(O,C)−L`); `σ=0→0` guards
  added to Pipeline-B z-score/Bollinger/standardization nodes.
- `main_data_flow.html`: L1 output corrected to **naive ET** (UTC only at the F1 reader); `volume_z_score`
  `std=0→0` guard restored.
- `L7_…_eng.md`: TP barrier made direction-aware (`close[t0] + direction·R0`).
- `glossary_eng.md`: shared-vocabulary ATR claim softened (A = Wilder, B = plain mean of TR — labelled).
- Package made English-only; `index.html` references removed (3D viz is now `main_data_flow.html`).

The external auditor must **re-verify all of the above independently** and must not treat this appendix as
evidence of correctness — only as the starting state.
