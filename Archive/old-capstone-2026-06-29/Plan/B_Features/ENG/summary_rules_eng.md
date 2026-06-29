# SOT writing rules (Plan B)

Goal: each SOT file in [`Stages_Short_SOT/`](Stages_Short_SOT/) reads like a precise account of *what a
feature is and how it is computed* — formula, family, inputs — no narrative, no guesswork. Short, fact-only
files that **own** the canonical facts.

**Division of roles.** The **canonical, authoritative source** is the short `Stages_Short_SOT/` files — they
own every feature-id, formula, family, guard, window and the selection/calibration methodology. The companion
docs (`feature_formulas_eng.md`, `selection_calibration_spec_eng.md`, `glossary_eng.md`, and the root
`feature_explanation_plan_b_eng.md`) are **subordinate**: derivations, worked examples, rationale, definitions.

## Rules

1. **One fact per line.** Do not glue two facts together with conjunctions.
2. **Formulas are canonical and explicit** — give the exact short form (`f2_r_cc = safe_log_ratio(close, prev_close)`); the *derivation* and worked examples live in `feature_formulas_eng.md`.
3. **Every feature row carries its `family`** (one of the 6, see `00_families_eng.md`) and its Stage.
4. **Guards by reference** — divisions/logs use the guard functions owned by `00_guards_and_windows_eng.md`; do not redefine `ε` or `safe_div` per file.
5. **Causality is stated where relevant** — backward-only windows, Train-only fits (see `00_leakage_contract_eng.md`); never restate the full leakage contract in a Stage file.
6. **Each fact has exactly one home (DRY)** — defined in its owner file (the fact-ownership map in [`Stages_Short_SOT/README.md`](Stages_Short_SOT/README.md)) and **referenced** everywhere else.
7. **The companions follow the SOT.** They state the same facts as the SOT, never different ones; on any divergence, the **SOT wins** — fix the companion (or the viz) to match, never the reverse.

## Pattern

```text
| f2_close_position | candle | safe_div(close − low, safe_max(f2_candle_range, ε)) |
| f3_mom_n          | returns| rolling sum of f2_r_cc over the last n bars |
```

## Anti-pattern

Verbose prose with abstractions and no formula ("F1 derives a rich set of atomic descriptors of price
action") — that belongs in the companions, not the SOT. The SOT is exclusively feature ids, families,
formulas and the short methodology facts.
