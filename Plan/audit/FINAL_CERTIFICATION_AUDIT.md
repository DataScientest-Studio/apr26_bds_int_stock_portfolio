# Final Certification Audit — Plan/

Date: 2026-06-15  
Object: `/opt/to_liora_school/liora-project-ml-engineering/Plan/`  
Verdict: **PASS — certified as a buildable single source of truth.**

## Why It Passes

`Plan/` is now self-contained. A competent engineer can build the described Pipeline A and Pipeline B
from this folder alone.

The previous audit blockers are closed:

- Pipeline A dates and row counts are consistent.
- Pipeline A TP math is direction-aware.
- Pipeline B canonical `l4_atr` is `mean_n(TR)` everywhere.
- ADX may use internal Wilder smoothing, but that is not canonical `l4_atr`.
- Pipeline B z-scores use `std=0 -> 0`, not an epsilon-floor.
- There is one canonical `reports/quality/summary.json` schema.
- `config/params.json` is the single configuration site and includes core, split, detector, L8, Pipeline B L4, and Pipeline B L5 values.
- Pipeline B is certified through `L0-L5`.
- English-only, links, decoded DAG, and rendering checks pass.

## Checklist

| Check | Result |
|---|---:|
| Naming and local links | PASS |
| `config/params.json` valid and complete | PASS |
| `config/universe.txt` = 503 unique tickers | PASS |
| Pipeline A formulas and numbers | PASS |
| Pipeline B formulas and guards | PASS |
| `summary.json` schema consistency | PASS |
| Pipeline A / Pipeline B separation | PASS |
| No stale FAIL-era strings | PASS |
| English-only scan | PASS |
| Decoded `feature_dag.html` ids and edges | PASS |
| Both visualizations render with no real console errors | PASS |

## Final Cleanup Order

Keep:

- `Plan/audit/FINAL_CERTIFICATION_AUDIT.md`
- `Plan/AUDIT_BRIEF.md`

Optional remove:

- `Plan/audit/rerun_*/`
- old generated evidence files in `Plan/audit/`
- old non-final audit reports in `Plan/audit/`

Do not remove:

- `Plan/config/`
- `Plan/ENG/`
- `Plan/viz/`
- `Plan/README.md`

