# quality_gate_spec_eng.md — L8 quality gate (companion)

> **Subordinate to the SOT.** The canonical L8 facts — the counter catalogue, the parity chain P1/P2/P3, the
> `summary.json` field schema and the gate aggregation rule — are owned by
> [`Layers_Short_SOT/L8_data_quality_eng.md`](Layers_Short_SOT/L8_data_quality_eng.md); the numeric WARN/FAIL
> thresholds by [`Layers_Short_SOT/00_parameters_eng.md`](Layers_Short_SOT/00_parameters_eng.md) (`l8` block).
> This document is **narrative**: the QC defense-in-depth rationale, the dashboard layout, a worked OK-path
> example and the L8 build invariants. It restates no canonical value; on any divergence, the SOT wins.

## What L8 is

L8 sits between L7 (Output B) and L9 (Optuna → XGBoost). It **measures and reports; it fixes nothing** —
fixes belong to the source layers (L2–L7). Its single contract with L9 is binary: a **FAIL** anywhere closes
the gate and **training (L9) does not start**. L8 guards **Pipeline A** only; the feature explanation
("Plan B", feature-stages F0–F5) is out of this gate's scope. The detector is a *reference implementation*
of its output contract and L8 is Pipeline A's gate.

The canonical *set* of counters/parities and the FAIL-on-any-mismatch parity rule come from the contract and
the glossary (not invented); the numeric thresholds are **reference design (one valid realization)** pending
roadmap item F4b. Both are owned by the SOT files above — see them for the exact counters, schema and bands.

## QC defense-in-depth (why L8 re-derives QC)

L3 already enforces QC-01…QC-11 on **every load** (a load that fails QC is not published). L8 **re-derives**
the QC-relevant population counts from the published parquet / Output B, so the dashboard restates them as
gate items rather than trusting the upstream load alone (defense in depth). The QC predicates are owned by
[`Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md`](Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md); each maps to
an L8 counter or parity as follows: high/low integrity (QC-01/02) → `zero_range_bars` + internal assertions;
duplicates (QC-03/10) → `duplicates`; nulls (QC-04) → null assertion + `nan_inf_outputB` discipline; prices
(QC-05) → `prices_nonpos`; volume (QC-06) → `volume_zero_bars`; universe (QC-07) → `symbols` + parity P1;
session/sequence (QC-08/09/10) → `gaps_in_session`; range/counters (QC-11) → `inputs_hash` + parity P1.

> **Why `det09_rejected` is diagnostic, not a fail.** DET-09 rejections are the detector working as designed
> (it must reject **and count**, never silently drop). A high rate signals a weak setup population or a
> mis-tuned detector, so L8 surfaces it as **WARN-only** — it can never FAIL the gate.

## `reports/quality/dashboard.html` (the render)

`dashboard.html` is generated **from `summary.json`** and is **fully self-contained**: zero external
dependencies, no network fetch, no JS framework, all CSS inlined — it opens correctly from a file path with
no server. It is a *render*, never a source of truth (regenerating it from the same `summary.json` is
deterministic). Reference layout:

- **Header banner** showing `overall_status` as one large badge — green **OK**, amber **WARN**, red **FAIL**
  — plus `built_at_utc` and a short `inputs_hash` prefix.
- **One row per check** (the 11 items), each with its own OK / WARN / FAIL chip, the `id`, the measured
  `value`, the `threshold` string and the `desc`. Rows ordered FAIL-tier counters first, then parities, then
  the rate diagnostics.
- **Counters block** echoing every `counters.*` value, and a **parities block** showing P1/P2/P3 as
  pass/mismatch.
- **Gate verdict line** restating the decision in plain English, e.g. *"FAIL → L9 training blocked"* or
  *"OK → L9 may start"*.

The dashboard intentionally shows the **per-item** status (not just the aggregate) so an analyst sees *which*
counter failed and by how much. The aggregate badge and the per-item chips both derive from the same
`checks[]` array, so they can never disagree.

## Worked example — the OK path

For the canonical S&P 500 build with a clean upstream:

- `counters`: `rows = 8 841 820`, `symbols = 503`, `parquet_files = 503`, `gaps_in_session = 0`,
  `gaps_filled = 0`, `duplicates = 0`, `prices_nonpos = 0`, `nan_inf_outputB = 0`.
- `parities`: P1 `true`, P2 `true`, P3 `true`.
- `volume_zero_bars` and `zero_range_bars` each within the OK band of `rows` → both OK.
- `det09_rejected` rate within the OK band → OK (or WARN if higher, never FAIL).
- Aggregation: no FAIL, no WARN → `overall_status = "OK"` → dashboard **OK** → **L9 proceeds**.

If instead `gaps_in_session = 3`: that check is FAIL → `overall_status = "FAIL"` → dashboard **FAIL** →
**L9 blocked**, regardless of every other green item.

## Build invariants (DoD restated for L8)

- L8 **never mutates** upstream stores; it only reads and writes `reports/quality/summary.json` +
  `reports/quality/dashboard.html`.
- `summary.json` is written **before** `dashboard.html`; the HTML is a deterministic render of the JSON.
- Every divisor uses an explicit guard (`max(1, …)` for integer counts, `max(ε, …)` with `ε = 1e-9` for
  floats; `den = 0 → 0`) — guards owned by `00_parameters_eng.md`.
- The gate is **binary toward L9**: `overall_status` is the only field L9 reads to decide go/no-go.
- All thresholds live in `config/params.json` (`l8` block — the single configuration site); the operators
  and schema are frozen. The numbers are reference design pending F4b.
