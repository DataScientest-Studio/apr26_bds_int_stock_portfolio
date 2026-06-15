// OHLCV → L5 pipeline data
// Naming: l{layer}_{metric}[_{params}][_{timeframe}]; family is a separate attribute (the family: field), not an id segment
//
// Families: price, returns, range, candle, volume, meta (synthesis/regime/embedding)
//
// Each node: { id, layer, family, name, formula?, note? }
// Each edge: { from, to }  (lineage: data flows from -> to, i.e. "to" is computed FROM "from")

(function () {
  const NODES = [
    // ───────────────────────────── L0: Raw OHLCV ─────────────────────────────
    { id: "O",  layer: 0, family: "price",   name: "O",  note: "open"   },
    { id: "H",  layer: 0, family: "range",   name: "H",  note: "high"   },
    { id: "L",  layer: 0, family: "range",   name: "L",  note: "low"    },
    { id: "C",  layer: 0, family: "price",   name: "C",  note: "close"  },
    { id: "V",  layer: 0, family: "volume",  name: "V",  note: "volume" },

    // ───────────────────────────── L1: Atomic transforms ─────────────────────
    // Price coordinates
    { id: "l1_tp",                   layer: 1, family: "price",   name: "l1_tp",                   formula: "(H + L + C) / 3" },
    { id: "l1_mp",                   layer: 1, family: "price",   name: "l1_mp",                   formula: "(H + L) / 2" },
    { id: "l1_ohlc4",                layer: 1, family: "price",   name: "l1_ohlc4",                formula: "(O + H + L + C) / 4" },

    // Returns / gaps
    { id: "l1_r_cc",                 layer: 1, family: "returns", name: "l1_r_cc",                 formula: "ln( C_t / C_{t-1} )" },
    { id: "l1_r_co",                 layer: 1, family: "returns", name: "l1_r_co",                 formula: "ln( C / O )" },
    { id: "l1_gap_oc",               layer: 1, family: "returns", name: "l1_gap_oc",               formula: "ln( O_t / C_{t-1} )" },

    // Range / vol proxy
    { id: "l1_range_pct",            layer: 1, family: "range",   name: "l1_range_pct",            formula: "(H - L) / C" },
    { id: "l1_hl_log",               layer: 1, family: "range",   name: "l1_hl_log",               formula: "ln( H / L )" },

    // Candle geometry
    { id: "l1_body_pct",             layer: 1, family: "candle",  name: "l1_body_pct",             formula: "|C - O| / C" },
    { id: "l1_signed_body_pct",      layer: 1, family: "candle",  name: "l1_signed_body_pct",      formula: "(C - O) / O" },
    { id: "l1_clv",                  layer: 1, family: "candle",  name: "l1_clv",                  formula: "(2C - H - L) / (H - L)" },
    { id: "l1_wick_imb",             layer: 1, family: "candle",  name: "l1_wick_imb",             formula: "(lw - uw) / (H - L),  uw = H - max(O,C),  lw = min(O,C) - L" },

    // Volume activity
    { id: "l1_log_volume",           layer: 1, family: "volume",  name: "l1_log_volume",           formula: "ln(1 + V)" },
    { id: "l1_log_dollar_volume",    layer: 1, family: "volume",  name: "l1_log_dollar_volume",    formula: "ln(1 + C·V)" },

    // ───────────────────────────── L2: Rolling / temporal ────────────────────
    // Lags
    { id: "l2_r_cc_lag_k",           layer: 2, family: "returns", name: "l2_r_cc_lag_k",           formula: "r_cc_{t-k},  k ∈ {1,2,…}" },
    // Rolling on returns
    { id: "l2_mom_n",                layer: 2, family: "returns", name: "l2_mom_n",                formula: "Σ_{i=0..n-1} r_cc_{t-i}" },
    { id: "l2_rv_n",                 layer: 2, family: "returns", name: "l2_rv_n",                 formula: "Σ_{i=0..n-1} r_cc²_{t-i}" },
    { id: "l2_absret_n",             layer: 2, family: "returns", name: "l2_absret_n",             formula: "mean_n( |r_cc| )" },
    // Rolling on range
    { id: "l2_range_mean_n",         layer: 2, family: "range",   name: "l2_range_mean_n",         formula: "mean_n( range_pct )" },
    { id: "l2_range_z_n",            layer: 2, family: "range",   name: "l2_range_z_n",            formula: "(range_pct − μ_n) / σ_n  (σ_n=0 → 0)" },
    // Rolling on candle
    { id: "l2_press_n",              layer: 2, family: "candle",  name: "l2_press_n",              formula: "mean_n( clv )" },
    { id: "l2_wick_imb_mean_n",      layer: 2, family: "candle",  name: "l2_wick_imb_mean_n",      formula: "mean_n( wick_imb )" },
    // Rolling on volume
    { id: "l2_vol_z_n",              layer: 2, family: "volume",  name: "l2_vol_z_n",              formula: "(log_V − μ_n) / σ_n  (σ_n=0 → 0)" },
    { id: "l2_dvol_z_n",             layer: 2, family: "volume",  name: "l2_dvol_z_n",             formula: "(log_$V − μ_n) / σ_n  (σ_n=0 → 0)" },
    // Ratios across windows
    { id: "l2_vol_ratio",            layer: 2, family: "returns", name: "l2_vol_ratio",            formula: "rv_short / rv_long" },
    { id: "l2_mom_ratio",            layer: 2, family: "returns", name: "l2_mom_ratio",            formula: "mom_short / mom_long" },

    // ───────────────────────────── L3: MTF / regime ──────────────────────────
    // Resample → recompute L1/L2 per TF (we model the *resulting* MTF aggregates)
    { id: "l3_mom_mtf",              layer: 3, family: "returns", name: "l3_mom_{tf}",             formula: "mom_n on resampled OHLCV,  tf ∈ {1h,1d}" },
    { id: "l3_rv_mtf",               layer: 3, family: "returns", name: "l3_rv_{tf}",              formula: "rv_n on resampled OHLCV" },
    { id: "l3_vol_z_mtf",            layer: 3, family: "volume",  name: "l3_vol_z_{tf}",           formula: "vol_z_n on resampled OHLCV" },

    { id: "l3_trend_align",          layer: 3, family: "meta",    name: "l3_trend_align",          formula: "Σ_tf sign( mom_tf )" },
    { id: "l3_vol_regime",           layer: 3, family: "meta",    name: "l3_vol_regime",           formula: "bucket( rv_tf )  →  low | normal | high" },
    { id: "l3_liq_regime",           layer: 3, family: "meta",    name: "l3_liq_regime",           formula: "bucket( vol_z_tf )  →  normal | abnormal" },

    { id: "l3_regime",               layer: 3, family: "meta",    name: "l3_regime",               formula: "(trend_align, vol_regime, liq_regime)" },

    // ───────────────────────────── L4: Classical indicators ──────────────────
    // From Close / r_cc
    { id: "l4_sma_ema",              layer: 4, family: "price",   name: "l4_sma_n / l4_ema_n",     formula: "SMA: mean_n(C);  EMA: α·C + (1−α)·EMA_{t−1}" },
    { id: "l4_rsi",                  layer: 4, family: "returns", name: "l4_rsi_n",                formula: "100 − 100 / (1 + RS),  RS = avg_gain / avg_loss" },
    { id: "l4_macd",                 layer: 4, family: "returns", name: "l4_macd",                 formula: "EMA_12(C) − EMA_26(C),  signal = EMA_9(MACD)" },
    { id: "l4_boll_z",               layer: 4, family: "price",   name: "l4_boll_z_n",             formula: "(C − SMA_n) / σ_n(C)  (σ_n=0 → 0)" },
    // From range / true range
    { id: "l4_atr",                  layer: 4, family: "range",   name: "l4_atr_n",                formula: "mean_n( TR ),  TR = max(H−L, |H−C_{−1}|, |L−C_{−1}|)" },
    { id: "l4_stoch",                layer: 4, family: "range",   name: "l4_stoch_n",              formula: "(C − min_n L) / (max_n H − min_n L)" },
    { id: "l4_adx",                  layer: 4, family: "range",   name: "l4_adx_n",                formula: "smoothed |+DI − −DI| / (+DI + −DI)" },
    // From volume / TP
    { id: "l4_obv",                  layer: 4, family: "volume",  name: "l4_obv",                  formula: "OBV_t = OBV_{t−1} + sign(ΔC) · V" },
    { id: "l4_adl",                  layer: 4, family: "volume",  name: "l4_adl",                  formula: "ADL_t = ADL_{t−1} + clv · V" },
    { id: "l4_mfi",                  layer: 4, family: "volume",  name: "l4_mfi_n",                formula: "100 − 100 / (1 + MR),  MR on TP·V flows" },
    { id: "l4_vwap",                 layer: 4, family: "price",   name: "l4_vwap",                 formula: "Σ TP·V / Σ V" },

    // ───────────────────────────── L5: Research representations ──────────────
    { id: "l5_stack",                layer: 5, family: "meta",    name: "X_raw  =  stack & standardize( L1..L4 )", formula: "z = (x − μ) / σ per column  (σ=0 → 0)" },
    { id: "l5_pca",                  layer: 5, family: "meta",    name: "l5_pca",                  formula: "pc_1, pc_2, pc_3  (eigenvectors of cov(X_raw))" },
    { id: "l5_wave",                 layer: 5, family: "meta",    name: "l5_wave",                 formula: "approx + detail coefficients (DWT)" },
    { id: "l5_ae",                   layer: 5, family: "meta",    name: "l5_ae",                   formula: "z_1 … z_k  =  Encoder( X_raw )" },
    { id: "l5_seq",                  layer: 5, family: "meta",    name: "l5_seq",                  formula: "h_t  =  LSTM / Transformer( X_{1..t} )" },
    { id: "l5_x_final",              layer: 5, family: "meta",    name: "X_final",                 formula: "concat( pca, wave, ae, seq )  →  model input" },
  ];

  const EDGES = [
    // ── L0 → L1 ──
    ["H","l1_tp"],["L","l1_tp"],["C","l1_tp"],
    ["H","l1_mp"],["L","l1_mp"],
    ["O","l1_ohlc4"],["H","l1_ohlc4"],["L","l1_ohlc4"],["C","l1_ohlc4"],

    ["C","l1_r_cc"],
    ["C","l1_r_co"],["O","l1_r_co"],
    ["O","l1_gap_oc"],["C","l1_gap_oc"],

    ["H","l1_range_pct"],["L","l1_range_pct"],["C","l1_range_pct"],
    ["H","l1_hl_log"],["L","l1_hl_log"],

    ["C","l1_body_pct"],["O","l1_body_pct"],
    ["C","l1_signed_body_pct"],["O","l1_signed_body_pct"],
    ["C","l1_clv"],["H","l1_clv"],["L","l1_clv"],
    ["O","l1_wick_imb"],["H","l1_wick_imb"],["L","l1_wick_imb"],["C","l1_wick_imb"],

    ["V","l1_log_volume"],
    ["V","l1_log_dollar_volume"],["C","l1_log_dollar_volume"],

    // ── L1 → L2 ──
    ["l1_r_cc","l2_r_cc_lag_k"],
    ["l1_r_cc","l2_mom_n"],
    ["l1_r_cc","l2_rv_n"],
    ["l1_r_cc","l2_absret_n"],

    ["l1_range_pct","l2_range_mean_n"],
    ["l1_range_pct","l2_range_z_n"],
    ["l1_hl_log","l2_range_z_n"],

    ["l1_clv","l2_press_n"],
    ["l1_wick_imb","l2_wick_imb_mean_n"],

    ["l1_log_volume","l2_vol_z_n"],
    ["l1_log_dollar_volume","l2_dvol_z_n"],

    ["l2_rv_n","l2_vol_ratio"],
    ["l2_mom_n","l2_mom_ratio"],

    // ── L2 → L3 (MTF = recompute on resampled OHLCV; we draw lineage from the analogous L2 nodes)
    ["l2_mom_n","l3_mom_mtf"],
    ["l2_rv_n","l3_rv_mtf"],
    ["l2_vol_z_n","l3_vol_z_mtf"],

    ["l3_mom_mtf","l3_trend_align"],
    ["l3_rv_mtf","l3_vol_regime"],
    ["l3_vol_z_mtf","l3_liq_regime"],

    ["l3_trend_align","l3_regime"],
    ["l3_vol_regime","l3_regime"],
    ["l3_liq_regime","l3_regime"],

    // ── L1/L2/L3 → L4 (classical indicators are compressed functions of earlier layers) ──
    // SMA/EMA: from C  (we route via l1_tp/price-ish? actually from raw C)
    ["C","l4_sma_ema"],
    ["l1_r_cc","l4_rsi"],
    ["C","l4_macd"],
    ["C","l4_boll_z"],
    ["l2_rv_n","l4_boll_z"],         // σ_n from L2 realized vol
    ["l2_rv_n","l4_atr"],            // ATR conceptually tied to rolling vol
    ["H","l4_atr"],["L","l4_atr"],["C","l4_atr"],
    ["H","l4_stoch"],["L","l4_stoch"],["C","l4_stoch"],
    ["H","l4_adx"],["L","l4_adx"],["C","l4_adx"],
    ["V","l4_obv"],["C","l4_obv"],
    ["V","l4_adl"],["l1_clv","l4_adl"],
    ["l1_tp","l4_mfi"],["V","l4_mfi"],
    ["l1_tp","l4_vwap"],["V","l4_vwap"],

    // Regime conditioning (dashed in render)
    ["l3_regime","l4_rsi",  "ctx"],
    ["l3_regime","l4_macd", "ctx"],
    ["l3_regime","l4_vwap", "ctx"],

    // ── L1..L4 → L5 stack ──
    ["l1_tp","l5_stack"],
    ["l1_r_cc","l5_stack"],
    ["l1_range_pct","l5_stack"],
    ["l1_clv","l5_stack"],
    ["l1_log_volume","l5_stack"],
    ["l2_mom_n","l5_stack"],
    ["l2_rv_n","l5_stack"],
    ["l2_vol_z_n","l5_stack"],
    ["l3_regime","l5_stack"],
    ["l4_rsi","l5_stack"],
    ["l4_macd","l5_stack"],
    ["l4_atr","l5_stack"],
    ["l4_obv","l5_stack"],
    ["l4_vwap","l5_stack"],

    ["l5_stack","l5_pca"],
    ["l5_stack","l5_wave"],
    ["l5_stack","l5_ae"],
    ["l5_stack","l5_seq"],

    ["l5_pca","l5_x_final"],
    ["l5_wave","l5_x_final"],
    ["l5_ae","l5_x_final"],
    ["l5_seq","l5_x_final"],
  ].map((e) => ({ from: e[0], to: e[1], kind: e[2] || "data" }));

  window.PIPELINE = { NODES, EDGES };
})();
