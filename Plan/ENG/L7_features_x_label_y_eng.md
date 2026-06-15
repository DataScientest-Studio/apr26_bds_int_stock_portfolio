# L7 · Features X + label Y (summary)

- Input: setup objects from the detector ([L6](L6_setup_detector_eng.md)) in the Train window.
- At `t0` the transformer computes exactly 8 columns.
  - columns: `distance_to_trend_line · distance_to_opposing_line · risk_if_entered_pct · bar_return_pct · body_to_range_ratio · volume_z_score · touch_count · closed_through_line`
  - ATR in the denominators = Wilder(14), window up to and including `t`
- The model's X takes 7 columns.
  - `closed_through_line` is an audit column (at `t0` always = 1)
- Label Y = triple barrier (close-based, first-touch).
  - TP: close reaches `close[t0] + direction·R0` → Y=1
  - SL: close breaks through the moving `L_opp(t)` → Y=0
  - time: no resolution by `t0+24` → Y=0
- Every row gets a `label_uniqueness_weight` weight (formula in `build_contract_eng.md` §Outputs).
- Output: Output B — one row per setup.
  - data partition: `{asset × direction}`
  - the column schema is frozen (a change = hard fail)
