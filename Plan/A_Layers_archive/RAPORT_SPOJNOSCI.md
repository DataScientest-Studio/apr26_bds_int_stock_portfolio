# <!DOCTYPE html>

<html lang="en">

<head>

<meta charset="utf-8">

<meta name="viewport" content="width=device-width, initial-scale=1">

<link rel="icon" href="data:,">

<title>S&amp;P 500 ML Pipeline — rotatable 3D Canvas (503 companies)</title>



<style>

:root{

--color-background-primary:#1e1e1c;

--color-background-secondary:#2b2b28;

--color-text-primary:#ece9e1;

--color-text-secondary:#a8a69d;

--color-text-tertiary:#a09d93; /* WCAG: 6.15:1 on primary bg, 5.23:1 on secondary (was #76746c = 3.57:1, fail) */

--color-border-secondary:rgba(255,255,255,0.18);

--color-border-tertiary:rgba(255,255,255,0.12);

/* text-safe accent variants: each ≥4.5:1 on both backgrounds (dark). Accents-as-TEXT

map here via txc(); saturated JS constants (RED/TEAL/…) stay for fills/strokes. */

--c-error-text:#F26B6A; /* 5.63 / 4.79 */

--c-store-text:#2BB587; /* 6.41 / 5.45 */

--c-train-text:#86B23A; /* 6.71 / 5.71 */

--c-control-text:#D89A3A; /* 6.84 / 5.82 */

--c-source-text:#ABA99F; /* 7.08 / 6.02 */

--c-gate-text:#E673A3; /* 5.84 / 4.97 */

--c-good-text:#34C96A; /* 7.72 / 6.56 */

--c-fail-text:#FF6B62; /* 5.99 / 5.09 */

--border-radius-md:8px;

--font-mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;

}

@media (prefers-color-scheme: light){

:root{

--color-background-primary:#f5f4ee;

--color-background-secondary:#e7e5dc;

--color-text-primary:#2b2b28;

--color-text-secondary:#5f5e57;

--color-text-tertiary:#67665e; /* WCAG: 5.24:1 on #f5f4ee, 4.57:1 on #e7e5dc (was #8f8e86 = fail) */

--color-border-secondary:rgba(0,0,0,0.18);

--color-border-tertiary:rgba(0,0,0,0.12);

/* text-safe accents for the light theme — darker, ≥4.5:1 on both light backgrounds */

--c-error-text:#BC3531; /* 5.16 / 4.51 */

--c-store-text:#0F6F50; /* 5.59 / 4.88 */

--c-train-text:#4E6E1C; /* 5.34 / 4.66 */

--c-control-text:#8F5410; /* 5.53 / 4.83 */

--c-source-text:#67665e; /* 5.24 / 4.57 */

--c-gate-text:#A82E68; /* 5.85 / 5.11 */

--c-good-text:#0F7035; /* 5.62 / 4.91 */

--c-fail-text:#BC3531; /* 5.16 / 4.51 */

}

}

html,body{margin:0}

html{height:100%}

/* full-screen layout: the page doesn't scroll → no scrollbar → no width changes →

overlay panels toggle without fit()/canvas reset (no more flicker) */

body{

background:var(--color-background-primary);

color:var(--color-text-primary);

font-family:"Anthropic Sans",system-ui,-apple-system,Segoe UI,sans-serif;

line-height:1.5;

height:100vh;

height:100dvh;

overflow:hidden;

display:flex;

flex-direction:column;

padding:14px 24px 0;

max-width:980px;

margin:0 auto;

box-sizing:border-box;

}

.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0}

.tlc-sub{font-size:12.5px;color:var(--color-text-secondary);margin:0 0 10px}

.tlc-sub b{color:var(--color-text-primary);font-weight:600}

.tlc-ctrls{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;margin:10px 0 2px;font-size:13px;color:var(--color-text-secondary)}

.tlc-ctrls .lbl{color:var(--color-text-primary)}

.tlc-seg{display:inline-flex;flex-wrap:wrap;border:0.5px solid var(--color-border-secondary);border-radius:var(--border-radius-md);overflow:hidden}

.tlc-seg button{border:0;background:transparent;padding:5px 10px;font-size:12.5px;color:var(--color-text-secondary);cursor:pointer}

.tlc-seg button.on{background:var(--color-background-secondary);color:var(--color-text-primary)}

.tlc-btn{border:0.5px solid var(--color-border-secondary);background:transparent;border-radius:6px;padding:5px 10px;font-size:12.5px;color:var(--color-text-secondary);cursor:pointer}

.tlc-btn:hover{color:var(--color-text-primary)}

.tlc-ctrls label{display:inline-flex;align-items:center;gap:6px;cursor:pointer;user-select:none}

.tlc-ctrls input[type=checkbox]{width:15px;height:15px;margin:0}

.tlc-ctrls select{font:inherit;background:var(--color-background-secondary);color:var(--color-text-primary);border:0.5px solid var(--color-border-secondary);border-radius:6px;padding:4px 6px}

.tlc-stage{position:relative;margin-top:4px;flex:1 1 auto;min-height:0;overflow:hidden}

#tlc{position:absolute;inset:0;display:block;width:100%;height:100%;cursor:grab}

#tip{position:absolute;display:none;pointer-events:none;z-index:3;max-width:260px;

background:var(--color-background-secondary);border:0.5px solid var(--color-border-secondary);

border-radius:8px;padding:7px 10px;font-size:12px;color:var(--color-text-primary);white-space:pre-line;line-height:1.45}

#panel{position:absolute;top:10px;right:10px;width:262px;max-height:calc(100% - 20px);overflow:auto;display:none;z-index:4;

background:var(--color-background-primary);border:0.5px solid var(--color-border-secondary);border-radius:10px}

#panelHead{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 10px;

border-bottom:1px solid var(--color-border-tertiary);font-size:13px;font-weight:600}

#panelClose{border:0;background:transparent;color:var(--color-text-secondary);cursor:pointer;font-size:15px;line-height:1}

#panelBody{padding:8px 10px;font-size:12.5px;color:var(--color-text-secondary)}

#panelBody b{color:var(--color-text-primary)}

#panelBody pre{font-family:var(--font-mono);font-size:10.5px;white-space:pre-wrap;word-break:break-all;

background:var(--color-background-secondary);border-radius:6px;padding:7px;color:var(--color-text-primary);margin:6px 0}

.tlc-leg{display:flex;flex-wrap:wrap;gap:8px 16px;margin:12px 0 2px;font-size:12.5px;color:var(--color-text-secondary)}

.tlc-leg span{display:inline-flex;align-items:center;gap:6px}

.tlc-msgs{font-size:12.5px;color:var(--color-text-secondary);margin:10px 0 0;padding-left:20px}

.tlc-msgs li{margin:2px 0}

.tlc-msgs b{color:var(--color-text-primary)}



/* buttons always in the same place (z-index above the editor, they don't disappear) */

#botTabs{position:fixed;left:14px;bottom:14px;z-index:32;display:flex;gap:8px}

#lblTab,#legTab{background:var(--color-background-secondary);

color:var(--color-text-primary);border:0.5px solid var(--color-border-secondary);

border-radius:8px;padding:9px 11px;font-size:12.5px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.25)}

#lblTab:hover,#legTab:hover{background:var(--color-background-primary)}

#legTab[aria-pressed="true"]{color:var(--color-text-tertiary)}

/* when the editor is open — push its footer aside so the floating buttons don't cover it */

body.le-open #leFoot{padding-left:210px}

/* Legend = bottom overlay (like the editor); controlled by the body.leg-open class */

#botInfo{position:fixed;left:0;right:0;bottom:0;z-index:30;max-height:min(52vh,480px);overflow:auto;

background:var(--color-background-primary);border-top:0.5px solid var(--color-border-secondary);

box-shadow:0 -6px 26px rgba(0,0,0,.4);transform:translateY(103%);transition:transform .22s ease;

will-change:transform;padding:0 24px 56px;box-sizing:border-box}

body.leg-open #botInfo{transform:translateY(0)}

#botInfo>.bi-inner{min-height:0}

/* bottom padding (56px) reserves a strip for the floating ✎/▦ buttons (left:14 bottom:14) — content doesn't hide them */

/* legend titlebar — styled like #leHead (editor header), click = collapse */

.bi-head{display:flex;align-items:center;gap:8px;padding:9px 2px 10px;margin-bottom:8px;

border-bottom:1px solid var(--color-border-tertiary);font-size:14px;font-weight:600;

color:var(--color-text-primary);cursor:pointer;user-select:none}

.bi-cue{margin-left:auto;font-size:11px;font-weight:400;color:var(--color-text-tertiary)}

.bi-head:hover .bi-cue{color:var(--color-text-secondary)}



#lblEditor{position:fixed;left:0;right:0;bottom:0;height:min(360px,44vh);z-index:31;

background:var(--color-background-primary);border-top:0.5px solid var(--color-border-secondary);

box-shadow:0 -6px 26px rgba(0,0,0,.4);transform:translateY(103%);transition:transform .22s ease;

will-change:transform;display:flex;flex-direction:column;font-size:13px}



body.le-open #lblEditor{transform:translateY(0)}

#leHead{display:flex;align-items:center;gap:8px;padding:12px 14px;cursor:pointer;user-select:none;

border-bottom:1px solid var(--color-border-tertiary);font-size:14px;font-weight:600}

#leCue{margin-left:auto;font-size:11px;font-weight:400;color:var(--color-text-tertiary)}

#leHead:hover #leCue{color:var(--color-text-secondary)}

#leClose{border:0;background:transparent;color:var(--color-text-secondary);font-size:19px;cursor:pointer;line-height:1}

#leClose:hover{color:var(--color-text-primary)}

#leSearch{margin:10px 12px 4px;padding:6px 9px;font:inherit;font-size:12.5px;background:var(--color-background-secondary);

color:var(--color-text-primary);border:0.5px solid var(--color-border-secondary);border-radius:6px}

#leHint{margin:0 14px 6px;font-size:11px;color:var(--color-text-tertiary)}

#leBody{flex:1;overflow:auto;padding:0 10px 10px;position:relative}

.le-grp{margin:8px 0 2px}

.le-gh{display:flex;align-items:center;gap:6px;cursor:pointer;font-size:12px;font-weight:600;color:var(--color-text-primary);

padding:7px 4px;border-bottom:1px solid var(--color-border-tertiary);user-select:none}

.le-gh .le-car{color:var(--color-text-secondary);width:10px;display:inline-block}

.le-gh .le-cnt{color:var(--color-text-tertiary);font-weight:400}

.le-rows{display:grid;grid-template-columns:repeat(auto-fill,minmax(252px,1fr));gap:0 18px}

.le-grp.collapsed .le-rows{display:none}

.le-row{display:flex;align-items:flex-start;gap:8px;padding:5px 4px}

.le-row input[type=checkbox]{width:15px;height:15px;margin:6px 0 0;flex:0 0 auto;cursor:pointer}

.le-fields{flex:1;min-width:0}

.le-hint{font-size:10px;color:var(--color-text-tertiary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin:0 0 1px}

.le-txt{width:100%;box-sizing:border-box;font:inherit;font-size:12px;background:var(--color-background-secondary);

color:var(--color-text-primary);border:0.5px solid var(--color-border-secondary);border-radius:6px;padding:4px 7px}

.le-txt:focus{outline:1.5px solid rgba(29,158,117,.85);border-color:#1D9E75}

.le-row.editing .le-hint{color:#1D9E75}

.le-row.off .le-txt{opacity:.45;text-decoration:line-through}

#leFoot{display:flex;flex-wrap:wrap;gap:7px;padding:10px 12px;border-top:1px solid var(--color-border-tertiary)}

#leFoot button{border:0.5px solid var(--color-border-secondary);background:transparent;border-radius:6px;

padding:6px 9px;font-size:11.5px;color:var(--color-text-secondary);cursor:pointer}

#leFoot button:hover{color:var(--color-text-primary)}

</style>

</head>

<body>

<script>try{var *p=localStorage.getItem('sp500*pipeline_panel');if(_p==null)_p='legend';

if(_p==='legend')document.body.classList.add('leg-open');

else if(_p==='editor')document.body.classList.add('le-open');}catch(e){}</script>

<h2 class="sr-only">A truly rotatable three-dimensional visualization of the ML pipeline for 503 S&amp;P 500 companies in HTML Canvas, yaw and pitch orbit by mouse drag, gentle perspective, depth-sorted painting. Ten levels from the bottom: an Alpaca SIP 1h source for a universe of 503 tickers, a LEAN ZIP store times 510 with prices times 10000, DuckDB with a raw table and an ohlcv_1h (USD) view plus a discreet row of quality-gate dots QC-01…QC-11, an atomic snapshot to parquet OHLCV per ticker, a warm-up train OOS time split with purge and embargo, a trend-line setup detector that finds L_trend, L_opp, entry_candle and R0 using only candles up to t0, trendline features X with a triple barrier label Y, quality validation of stores and transforms with a dashboard as a gate before training, Optuna tuning and XGBoost training into a strategy file with a base64-encoded model, and a wall of OOS test results for 503 assets across 5 metrics. Horizontal dashed separators between layers and editable note-cards for L-to-L transitions. View modes 1 to 9 and 0, pan, zoom, tooltips, side panel, label editor, PNG export.</h2>



<p class="tlc-sub"><b>S&amp;P 500 ML Pipeline — rotatable 3D</b> · Alpaca 1h → LEAN ZIP → DuckDB+QC → snapshot → parquet OHLCV → split → setup detector → trendline features X+Y → quality validation (dashboard) → Optuna+XGB → strategy .py (base64) → OOS test 503 assets. Drag = rotate 3D · Shift+drag / right button = pan · scroll = zoom · dblclick = reset · click = details · keys 1–9 and 0 = views.</p>



<div class="tlc-ctrls">

<span class="lbl">View:</span>

<span class="tlc-seg" id="segMode">

<button data-m="overview" class="on">1 Overview</button>

<button data-m="dataflow">2 Data (DAG)</button>

<button data-m="qc">3 QC gates</button>

<button data-m="split">4 Split</button>

<button data-m="setup">5 Setup geometry</button>

<button data-m="dq">6 Data quality</button>

<button data-m="optuna">7 Optuna</button>

<button data-m="artifact">8 Artifact</button>

<button data-m="oos">9 OOS results</button>

<button data-m="leak">0 Anti-leakage</button>

</span>

</div>



<div class="tlc-stage" id="stage">

<canvas id="tlc"></canvas>

<div id="tip"></div>

<div id="panel">

<div id="panelHead"><span id="panelTitle">Details</span><button id="panelClose" aria-label="Close">×</button></div>

<div id="panelBody"></div>

</div>

</div>



<div id="botInfo"><div class="bi-inner">

<div class="bi-head" id="legHead" title="Click to collapse the legend">▦ XGB S&amp;P500 Data Processing Pipeline<span class="bi-cue">collapse ▾</span></div>

<div class="tlc-ctrls" id="botCtrls">

<span class="lbl">Asset:</span>

<select id="selAsset"></select>

<span class="lbl">OOS metric:</span>

<span class="tlc-seg" id="segMetric">

<button data-s="pf" class="on">PF</button>

<button data-s="sharpe">Sharpe</button>

<button data-s="mdd">MDD</button>

</span>

<span class="lbl">Camera:</span>

<span class="tlc-seg" id="segCam">

<button data-c="iso" class="on">3D (iso)</button>

<button data-c="flat">front (flat)</button>

</span>

<span class="lbl">Speed:</span>

<span class="tlc-seg" id="segSpd">

<button data-v="0.5">½×</button>

<button data-v="1" class="on">1×</button>

<button data-v="2">2×</button>

</span>

<label><input type="checkbox" id="cLabels" checked> Labels</label>

<label><input type="checkbox" id="cFlow" checked> Flow</label>

<span class="lbl">Names:</span>

<span class="tlc-seg" id="segNames">

<button data-n="sample" class="on">sample</button>

<button data-n="none">none</button>

</span>

<button class="tlc-btn" id="bPause">⏸ Pause</button>

<button class="tlc-btn" id="bPng">⤓ PNG</button>

</div>



<!-- Legend by 5 families (color = role, shape = silhouette). Red reserved for errors. -->

<div class="tlc-leg">

<span><span style="display:inline-block;width:12px;height:12px;border:1.5px solid #8a8980"></span> Source / gate <span style="color:var(--color-text-tertiary)">(L1–L2)</span></span>

<span><span style="display:inline-block;width:14px;height:11px;background:rgba(29,158,117,.18);border:1.5px solid #1D9E75;border-radius:5px"></span> Store / artifact <span style="color:var(--color-text-tertiary)">(L3)</span></span>

<span><span style="display:inline-block;width:9px;height:14px;background:rgba(99,153,34,.20);border:1.5px solid #639922"></span> Transform <span style="color:var(--color-text-tertiary)">(L4·L6·L7·L9)</span></span>

<span><span style="display:inline-block;width:13px;height:11px;border:1.5px solid #BA7517;border-radius:4px"></span> Gate / control <span style="color:var(--color-text-tertiary)">(L5·L8)</span></span>

<span><span style="display:inline-block;width:12px;height:11px;background:#22C55E"></span> Result / report <span style="color:var(--color-text-tertiary)">(L10)</span></span>

<span><span style="display:inline-block;width:11px;height:11px;background:linear-gradient(90deg,var(--c-fail-text),#9a9890,#22C55E)"></span> Result scale: bad ↔ good (diverging)</span>

<span style="color:var(--c-fail-text)">✕ Red = error / block / FAIL (reserved)</span>

</div>



<ol class="tlc-msgs">

<li><b>Alpaca SIP · 1h</b> — 503 S&amp;P 500 tickers, session 09:00–16:00 ET (~7 candles/day), 2016 → today.</li>

<li><b>LEAN ZIP</b>: 510 zips (1 per ticker), CSV with prices in deci-cents <b>×10000</b>, 139 MB.</li>

<li><b>DuckDB</b>: raw table (BIGINT ×10000) + <b>VIEW ohlcv_1h</b> (USD, /10000.0); every load is gated by QC-01…QC-11.</li>

<li><b>Snapshot → parquet OHLCV</b> per ticker (×503) — features are computed only by the transformer (L7).</li>

<li><b>Time split</b>: warm-up → train → OOS; <b>purge H=24 + embargo</b>, because TB labels overlap the boundaries.</li>

<li><b>Trend-line setup</b> = 8 transformer features (7 X + closed_through_line audit) + label Y (triple barrier: TP=1 · SL=0 · time=0, close-based, SL=L_opp(t) moving, barriers from R0).</li>

<li><b>Quality validation</b> (dashboard): parities zip→DuckDB→parquet→Output B, gaps, zero-values, NaN/Inf, split assertion — <b>FAIL blocks training</b>.</li>

<li><b>Optuna tunes XGBoost on Train</b> (200 trials, purged walk-forward); champion → <b>strategy .py with a base64 model</b> + selfcheck.</li>

<li><b>OOS single run</b>: 503 assets × PF · Sharpe · MDD · TIM · WR.</li>

</ol>

</div></div>



<div id="botTabs">

<button id="lblTab" title="Edit label names">✎ Labels</button>

<button id="legTab" title="Show/hide legend" aria-pressed="false">▦ Legend</button>

</div>

<aside id="lblEditor" aria-label="Label editor" aria-hidden="true">

<div id="leHead" title="Click the bar to collapse the panel"><span>✎ Label editor</span><span id="leCue">click bar = collapse ▾</span><button id="leClose" aria-label="Close">×</button></div>

<input id="leSearch" type="text" placeholder="Filter labels…">

<div id="leHint">☑ = visible on the scene · text field = name · editing a field = teal highlight of the element on the scene (live) · L→L boundary cards are also editable by clicking on the scene · click the title bar or Esc = collapse. Changes save automatically.</div>

<div id="leBody"></div>

<div id="leFoot">

<button id="leAll">Show all</button>

<button id="leReset">Reset to defaults</button>

<button id="leExport">Export JSON</button>

</div>

</aside>



<script>

(function(){

'use strict';



var RED='#E24B4A',TEAL='#1D9E75',GREEN='#639922',AMB='#BA7517',CAN='#8a8980',PINK='#D8568E',TP='#22C55E',SL='#FF3B30';

var THEME=null;

function themeRefresh(){THEME=null;}

function vget(n,f){

if(!THEME){THEME={};try{THEME._cs=getComputedStyle(document.body);}catch(e){}}

var v=THEME[n];

if(v==null){try{v=THEME._cs?THEME._cs.getPropertyValue(n).trim():'';}catch(e){v='';}THEME[n]=v;}

return v||f;}

function rgba(hex,a){var n=parseInt(hex.slice(1),16);return 'rgba('+((n>>16)&255)+','+((n>>8)&255)+','+(n&255)+','+a+')';}

// Accent-as-TEXT → text-safe CSS variant (resolved per-theme via vget, ≥4.5:1).

// Saturated JS constants (RED/TEAL/…) stay for fills/strokes (≥3:1). txc() maps ONLY

// exact accent matches; resolved hexes (prim/sec/tert) and rgba() pass through unchanged.

var TEXT_SAFE={};

TEXT_SAFE[RED]='--c-error-text'; TEXT_SAFE[SL]='--c-fail-text';

TEXT_SAFE[TEAL]='--c-store-text'; TEXT_SAFE[GREEN]='--c-train-text';

TEXT_SAFE[AMB]='--c-control-text';TEXT_SAFE[CAN]='--c-source-text';

TEXT_SAFE[PINK]='--c-gate-text'; TEXT_SAFE[TP]='--c-good-text';

function txc(col){var v=TEXT_SAFE[col];return v?vget(v,col):col;}

function clamp(v,a,b){return v<a?a:(v>b?b:v);}

function zScale(){return clamp(CAM.z,0.8,1.45)*EXPORT_FONT;} // zoom→font-scale clamp (×EXPORT_FONT on export)

function pulse(){return 0.5+0.5*Math.sin([performance.now](http://performance.now)()/260);} // 0..1 highlight pulse

function uiFont(wt,fz){return (wt?wt+' ':'')+fz.toFixed(1)+'px "Anthropic Sans",system-ui,sans-serif';}

function lerp2(p,q,t){return {x:p.x+(q.x-p.x)*t,y:p.y+(q.y-p.y)*t};}

function rng(seed){var t=seed>>>0;return function(){t+=0x6D2B79F5;var r=Math.imul(t^t>>>15,1|t);r^=r+Math.imul(r^r>>>7,61|r);return((r^r>>>14)>>>0)/4294967296;};}



var N_ASSETS=503;

var ASSETS=['AAPL','MSFT','NVDA','AMZN','META','JPM','XOM'];



var FEATURES=[

{name:'distance_to_trend_line', family:'trendline_geometry', src:'detector + Wilder ATR(14)', unit:'×ATR', formula:'sign·(c − L_trend(t)) / ATR(t)'},

{name:'distance_to_opposing_line',family:'trendline_geometry',src:'detector + Wilder ATR(14)', unit:'×ATR', formula:'sign·(c − L_opp(t)) / ATR(t)'},

{name:'risk_if_entered_pct', family:'trendline_geometry', src:'detector', unit:'%', formula:'|c − L_opp(t)| / c · 100',

special:'feature X + Y geometry parameter (defines R0) — importance can be mechanical, interpret separately'},

{name:'bar_return_pct', family:'price_action', src:'OHLCV', unit:'%', formula:'(c − c[t−1]) / c[t−1] · 100'},

{name:'body_to_range_ratio', family:'price_action', src:'OHLCV', unit:'[0,1]', formula:'|c − o| / max(ε, h − l)'},

{name:'volume_z_score', family:'volume', src:'OHLCV · W=20', unit:'z', formula:'(v − mean_20) / std_20 (std=0 → 0)'},

{name:'touch_count', family:'trendline_geometry', src:'detector', unit:'n', formula:'count(topo_candles ≤ t)'},

{name:'closed_through_line', family:'trendline_geometry', src:'detector', unit:'{0,1}', formula:'1 if sign·(c − L_trend(t)) > 0',

special:'in Output B (t0) always =1 — break invariant; audit column, outside FEATURE_MANIFEST'}

];



var QC=[

{id:'QC-01',name:'QC-01 INTEGRITY', desc:'high ≥ low on every candle'},

{id:'QC-02',name:'QC-02 OHLC CONSISTENT', desc:'high ≥ max(o,c) · low ≤ min(o,c)'},

{id:'QC-03',name:'QC-03 DUPLICATES', desc:'no duplicates (symbol, ts)'},

{id:'QC-04',name:'QC-04 NULL', desc:'zero NULL in o/h/l/c/v'},

{id:'QC-05',name:'QC-05 PRICES > 0', desc:'all prices positive'},

{id:'QC-06',name:'QC-06 VOLUME ≥ 0', desc:'volume non-negative'},

{id:'QC-07',name:'QC-07 UNIVERSE', desc:'503/503 symbols present'},

{id:'QC-08',name:'QC-08 BARS/DAY', desc:'candles per day ∈ [5,9]'},

{id:'QC-09',name:'QC-09 SESSION', desc:'ts in 09:00–16:00 ET'},

{id:'QC-10',name:'QC-10 MONOTONIC', desc:'ts increasing per symbol'},

{id:'QC-11',name:'QC-11 MANIFEST', desc:'date range and counters match _meta'}

];

function qcStat(){return '8 841 820 rows · violations: 0 · PASS';}



var SPLIT={

bands:[

{id:'warmup',name:'WARM-UP',from:'2016-01-04',to:'2016-10-14',frac:0.075,col:CAN,

note:'roll-in for transformer windows: max(W_ATR=14, W_VOL=20) = 20 candles 1h → features without NULL; no training or detection'},

{id:'train', name:'TRAIN', from:'2016-10-17',to:'2023-12-29',frac:0.695,col:TEAL,

note:'the only window touched multiple times: setup detection, features, Optuna (purged walk-forward CV), XGB training'},

{id:'oos', name:'OOS', from:'2024-01-02',to:'2026-05-29',frac:0.230,col:AMB,

note:'frozen to the end · single strategy test run · zero tuning after seeing results'}],

purge:'purge = H = 24 candles — the triple barrier window of setups at the end of Train overlaps the boundary',

embargo:'embargo ≈ 5 sessions (~35 candles) after the boundary — rolling-feature autocorrelation; covers max feature lookback (20 candles)'

};

// L5 as a time axis: dates → fraction of the full range (warmup-start → oos-end). Clean, no [Date.now](http://Date.now) (constant strings).

function dord(s){var p=s.split('-');return Math.floor(365.25*p[0])+Math.floor(30.6*(+p[1]+1))+ +p[2];} // monotonic day counter; only differences matter

var SPLIT_T0=dord(SPLIT.bands[0].from), SPLIT_SPAN=dord(SPLIT.bands[SPLIT.bands.length-1].to)-SPLIT_T0;

function dfrac(s){return (dord(s)-SPLIT_T0)/SPLIT_SPAN;}

function aOf(f){return 0.06+0.88*f;} // a0=0.06, total=0.88 (time axis along 'a')

SPLIT.bands.forEach(function(b){b._f0=dfrac(b.from);b._f1=dfrac([b.to](http://b.to));});

SPLIT.edgeF=[]; // internal boundaries in the middle of the gap between windows → bands touch, boundary = tick anchor

for(var *i=0;*i<SPLIT.bands.length-1;_i++)SPLIT.edgeF.push((SPLIT.bands[_i]._f1+SPLIT.bands[_i+1]._f0)/2);

SPLIT.years=[];

for(var *y=+SPLIT.bands[0].from.slice(0,4);*y<=+SPLIT.bands[SPLIT.bands.length-1].to.slice(0,4);_y++)

SPLIT.years.push({y:_y,f:clamp(dfrac(_y+'-01-01'),0,1)});



var OPTUNA={n_trials:200,sampler:'TPE',pruner:'MedianPruner(n_warmup_steps=2)',

objective:'AUC-PR (mean over k=4 purged walk-forward folds on Train)',

space:{max_depth:'3–9',learning_rate:'0.01–0.3 (log)',n_estimators:'100–1200',

min_child_weight:'1–20',subsample:'0.5–1.0',colsample_bytree:'0.5–1.0',

reg_lambda:'1e-3–10 (log)',scale_pos_weight:'0.5–4'}};

function buildTrials(){var r=rng(4242),out=[],best=0.382,i;

for(i=0;i<OPTUNA.n_trials;i++){

var explore=Math.exp(-i/60), v=0.36+0.20*(1-explore)+(r()-0.5)*0.10*(0.4+explore);

var pruned=(i>15)&&(v<best-0.018)&&(r()<0.7);

v=Math.round(v*1000)/1000;

if(!pruned&&v>best)best=v;

out.push({i:i,v:v,pruned:pruned,best:Math.round(best*1000)/1000,

params:{max_depth:3+Math.floor(r()*7),learning_rate:+(0.01*Math.pow(30,r())).toFixed(3),

n_estimators:100+Math.floor(r()*1100),subsample:+(0.5+0.5*r()).toFixed(2)}});}

return out;}

var TRIALS=buildTrials();

var BEST_TRIAL=(function(){var b=0,i;for(i=0;i<TRIALS.length;i++)if(!TRIALS[i].pruned&&TRIALS[i].v>=TRIALS[b].v)b=i;return b;})();

var PARAM_IMPORTANCE=[['learning_rate',0.31],['max_depth',0.22],['min_child_weight',0.14],

['subsample',0.12],['n_estimators',0.09],['colsample_bytree',0.07],['reg_lambda',0.05]];



function setupsMock(a){var r=rng(a*131+9);return {long:Math.round(70+130*r()),short:Math.round(60+120*r())};}

function oosMock(a){var r=rng(a*7919+101),q=r();

return {pf:+(0.75+1.35*q+0.2*(r()-0.5)).toFixed(2), sharpe:+(-0.4+2.4*q+0.3*(r()-0.5)).toFixed(2),

mdd:+(32-24*q+4*r()).toFixed(1), tim:+(5+20*r()).toFixed(1),

wr:+(33+22*q+4*r()).toFixed(1), trades:Math.round(25+115*r())};}

function importanceMock(a,f){return Math.round(rng(a*31+f*131)()*0.30*100)/100;}



var METRICS=[

{id:'pf',name:'PF',hi:true,lo:0.7,hiV:2.1},

{id:'sharpe',name:'Sharpe',hi:true,lo:-0.5,hiV:2.2},

{id:'mdd',name:'MDD %',hi:false,lo:5,hiV:35},

{id:'tim',name:'TIM %',hi:true,lo:4,hiV:28},

{id:'wr',name:'WR %',hi:true,lo:32,hiV:58}];

function metricQ(val,m){var M=METRICS[m],q=clamp((val-M.lo)/([M.hiV](http://M.hiV)-M.lo),0,1);return M.hi?q:1-q;}



var DQ=[

{id:'parity',name:'PARITIES',status:'OK',

detail:'zip → DuckDB: 8 841 820 rows / 503 symbols · DuckDB → parquet: 503 files · parquet → Output B: setup count per {asset × direction} (R4)'},

{id:'gaps',name:'GAPS',status:'OK',

detail:'in-session gaps: 0 (hard fail QC-08/09/10) · overnight/weekend gaps: counted (normal for 1h) · filled gaps: 0 — we fill nothing'},

{id:'zeros',name:'ZERO-VALUES',status:'WARN',

detail:'volume=0 bars: 1 274 · high==low candles (zero-range): 312 · prices ≤ 0: 0 · WARN: zero-volume above the informational threshold'},

{id:'features',name:'FEATURES',status:'OK',

detail:'NaN/Inf in Output B: 0 · warm-up NULLs: cut off (gating) · DET-09 rejections: 1 982 (audit) · touch_count distribution: report R3'},

{id:'split',name:'SPLIT',status:'OK',

detail:'boundary assertion: no window [t0, t0+24] crosses a window boundary · embargo 5 sessions ≥ lookback 20 candles'},

{id:'alarms',name:'ALARMS',status:'OK',

detail:'FAIL: 0 · WARN: 1 (zero-values) · gate: OPEN — training (L9) can start'}

];

function dqCol(s){return s==='OK'?TP:(s==='WARN'?AMB:SL);}



function manifest(a){var r=rng(a*991+7);

return {asset:ASSETS[a],strategy_file:'strategy_'+ASSETS[a]+'.py',

estimator:'XGBoost binary:logistic (meta-labeling: trend-line setup signal filter)',

model_b64:'QmFzZTY0LWFydGVmYWt0Li4u (truncated, ~180 kB)',

feature_manifest:FEATURES.filter(function(f){return [f.name](http://f.name)!=='closed_through_line';}).map(function(f){return [f.name](http://f.name);}),

label_contract:'TB_v1.1 · close-based · SL=L_opp(t) moving · geometric barriers R0 · H=24',

threshold_entry:0.60,

optuna:{n_trials:200,best_trial:BEST_TRIAL,best_value:TRIALS[BEST_TRIAL].v},

windows:{train:'2016-10-17 → 2023-12-29',oos:'2024-01-02 → 2026-05-29'},

metrics_cv:{auc_pr:+(0.52+0.10*r()).toFixed(3),logloss:+(0.58+0.08*r()).toFixed(3)},

selfcheck:'golden input → output: PASS'};

}



var BND_DZ=[189,189,192,189,189,189,185,189,202]; // 9 boundaries (10 levels): inserted L6 detector boundary



// ===== SINGLE SOURCE OF TRUTH: scene graph (spec v1.2) =====

// family = one of 5 silhouettes (PR-5), role = palette key by role (PR-5),

// col = current color (now used by caption; PR-5 will switch to roleColor(role)).

// title WITHOUT the 'Lx · ' prefix — caption() appends the number from lev, so renumbering is free.

// dataKey points to existing arrays (we don't copy content) → caption/legend/inspect read from them.

var DATA={FEATURES:FEATURES,QC:QC,SPLIT:SPLIT,DQ:DQ,METRICS:METRICS,OPTUNA:OPTUNA};

var PIPELINE={

nodes:[

{id:'L1',lev:0,family:'source',role:'source',col:CAN,

title:'SOURCE: ALPACA SIP · S&P 500 (503)',subtitle:'fetch 1h OHLCV for the S&P 500 universe',

summary:'SIP 1h feed, session 09:00–16:00 ET (~7 candles/day), cron :05',

input_contract:'Alpaca Market Data API (feed=sip, API key)',transform_verb:'parse',

output_contract:'raw 1h OHLCV per ticker (naive ET)',

metric:{label:'tickers',value:'503'},invariants:['ET session guard','upsert lookback 5 days'],

status:'ok',hitType:'universe'},

{id:'L2',lev:1,family:'store',role:'source',col:CAN,

title:'LEAN ZIP STORE (510 zip · prices ×10000)',subtitle:'write LEAN cache: 1 zip / ticker',

summary:'headerless CSV, prices in deci-cents ×10000, 139 MB',

input_contract:'raw 1h OHLCV',transform_verb:'store',

output_contract:'510 zip (CSV, prices ×10000)',metric:{label:'zip',value:'510'},

invariants:['immutable cache','prices ×10000 (BIGINT)'],status:'ok',hitType:'zip'},

{id:'L3',lev:2,family:'store',role:'store',col:TEAL,

title:'DUCKDB raw + VIEW ohlcv_1h (USD) · QC-01…QC-11',subtitle:'load into DuckDB + VIEW ohlcv_1h, QC gates',

summary:'8 841 820 rows · 503 symbols; QC-01…QC-11 gate every load',

input_contract:'510 zip',transform_verb:'load',

output_contract:'raw_ohlcv_1h (BIGINT ×10000) + VIEW ohlcv_1h (USD)',

metric:{label:'rows',value:'8.84M'},invariants:['QC-01…QC-11 PASS','VIEW = /10000.0 USD'],

status:'ok',dataKey:'QC',hitType:'db'},

{id:'L4',lev:3,family:'transform',role:'transform',col:GREEN,

title:'SNAPSHOT → PARQUET OHLCV (×503)',subtitle:'freeze snapshot → serialize parquet',

summary:'atomic snapshot + manifest → parquet per ticker, zero derived columns',

input_contract:'DuckDB raw + VIEW ohlcv_1h (USD, after QC)',transform_verb:'freeze',

output_contract:'503 × <TICKER>/ohlcv.parquet (clean OHLCV)',metric:{label:'files',value:'×503'},

invariants:['zero derived columns','atomic snapshot / torn-read guard'],status:'ok',hitType:'parquet'},

{id:'L5',lev:4,family:'gate',role:'control',col:AMB,

title:'SPLIT: WARM-UP / TRAIN / OOS',subtitle:'split by time + purge/embargo',

summary:'warm-up → train → OOS · purge H=24 + embargo ~5 sessions',

input_contract:'503 parquet OHLCV',transform_verb:'split',

output_contract:'disjoint time windows per asset',metric:{label:'OOS frac',value:'0.23'},

invariants:['purge = H = 24','embargo ≥ lookback (20 candles)','OOS frozen'],

status:'ok',dataKey:'SPLIT',hitType:'split'},

{id:'L6',lev:5,family:'transform',role:'transform',col:GREEN,

title:'TREND-LINE SETUP DETECTOR',subtitle:'detect L_trend, L_opp, entry_candle, R0',

summary:'detector contract (Layers_Short_SOT/L6_setup_detector_[eng.md](http://eng.md)) — bridge between raw candles and feature rows',

input_contract:'OHLCV in the Train window (candles ≤ t0)',transform_verb:'detect',

output_contract:'per setup: direction, L_trend(t), L_opp(t), topo_candles, t0, R0, take_profit, time_barrier',

metric:{label:'min touch',value:'2'},invariants:['causal fits (candles ≤ t0)','MIN_TOUCHES = 2','first break close-based'],

status:'ok',icon:'setupGeometry',hitType:'detector'},

{id:'L7',lev:6,family:'transform',role:'transform',col:GREEN,

title:'FEATURES X + LABEL Y (TRIPLE BARRIER)',subtitle:'transform setups → 7 X + audit + Y',

summary:'X,Y matrix per setup (Output B), features computed at t0',

input_contract:'setup objects (detector) in the Train window',transform_verb:'transform',

output_contract:'Output B: 7 X + closed_through_line(audit) + Y_outcome + w_unique',

metric:{label:'features',value:'7 X'},invariants:['features at t0 ⇐ candles ≤ t0','FEATURE_MANIFEST = 7 X'],

status:'ok',dataKey:'FEATURES',hitType:'feature'},

{id:'L8',lev:7,family:'gate',role:'control',col:AMB,

title:'QUALITY VALIDATION: STORES + TRANSFORMS',subtitle:'validate parities/gaps/NaN → dashboard',

summary:'parities zip→DuckDB→parquet→Output B, gaps, zero-values, NaN/Inf, split assertion',

input_contract:'Output B + store manifests',transform_verb:'validate',

output_contract:'reports/quality/summary.json + dashboard (FAIL blocks L9)',

metric:{label:'gate',value:'OPEN'},invariants:['any FAIL blocks training','green dashboard = start condition'],

status:'ok',dataKey:'DQ',hitType:'dqSummary'},

{id:'L9',lev:8,family:'transform',role:'transform',col:GREEN,

title:'OPTUNA → XGBOOST → STRATEGY .py',subtitle:'tune + train → pack artifact',

summary:'Optuna 200 trials (TPE, purged WF CV) → XGBoost → strategy .py (model b64)',

input_contract:'Output B (green dashboard)',transform_verb:'train',

output_contract:'strategy_<TICKER>.py: model b64 + FEATURE_MANIFEST + threshold + selfcheck',

metric:{label:'trials',value:'200'},invariants:['training only on Train','meta-labeling: setup signal filter'],

status:'ok',dataKey:'OPTUNA',hitType:'xgb'},

{id:'L10',lev:9,family:'output',role:'output',col:TP,

title:'OOS TEST: 503 ASSETS × METRICS',subtitle:'evaluate on the frozen OOS window',

summary:'single run on OOS 2024-01-02 → 2026-05-29',

input_contract:'503 frozen strategy artifacts',transform_verb:'evaluate',

output_contract:'results matrix: PF · Sharpe · MDD · TIM · WR',metric:{label:'assets',value:'503'},

invariants:['single run','zero tuning after seeing results'],status:'ok',dataKey:'METRICS',hitType:'oos'}

],

edges:[

{from:'L1',to:'L2',verb:'parse',payload:'Alpaca 1h → LEAN zip',causal_scope:'per ticker',

detail:'Alpaca SIP 1h (session 09:00–16:00 ET, ~7 candles/day) → LEAN write: 1 zip per ticker, CSV in deci-cents ×10000, hourly cron :05'},

{from:'L2',to:'L3',verb:'load',payload:'zip → DuckDB + VIEW ohlcv_1h (QC)',causal_scope:'QC-gated load',

detail:'510 zip (139 MB) → DuckDB raw_ohlcv_1h: 8 841 820 rows BIGINT ×10000 + VIEW ohlcv_1h = prices/10000.0 USD; QC-01…QC-11 gate every load'},

{from:'L3',to:'L4',verb:'freeze',payload:'snapshot → parquet OHLCV',causal_scope:'atomic',

detail:'atomic database snapshot + manifest JSON (rows / symbols / ts range / price_view) → COPY to parquet OHLCV per ticker — zero derived columns'},

{from:'L4',to:'L5',verb:'split',payload:'parquet OHLCV → time windows',causal_scope:'per asset',

detail:'503 parquet OHLCV (1/ticker) → time split: warm-up (roll-in max(W_ATR,W_VOL)=20 candles) / train / OOS + purge H=24 and embargo at boundaries'},

{from:'L5',to:'L6',verb:'detect',payload:'Train window → trend-line setups',causal_scope:'candles ≤ t0',

detail:'Train only: trend-line setup detector — fits of L_trend, L_opp, touchpoints, t0, R0, direction using only candles ≤ t0 (zero look-ahead)'},

{from:'L6',to:'L7',verb:'transform',payload:'setup objects → 7 X + audit + Y',causal_scope:'features at t0',

detail:'setup objects (detector) → 8 transformer features (7 X + 1 audit) computed at t0 + label Y = triple barrier (Output B)'},

{from:'L7',to:'L8',verb:'validate',payload:'Output B → quality dashboard',causal_scope:'checkpoint',

detail:'X,Y matrix per setup (Output B) + store manifests → quality validation: parities zip→DuckDB→parquet→Output B · gaps · zero-values · NaN/Inf · split assertion → summary.json + dashboard'},

{from:'L8',to:'L9',verb:'train',payload:'green dashboard → Optuna+XGB → .py',causal_scope:'Train only',

detail:'quality gate: training starts only with a green dashboard (FAIL blocks) → Optuna 200 trials (TPE + pruning, purged walk-forward CV) → XGBoost → strategy .py with a base64 model + selfcheck'},

{from:'L9',to:'L10',verb:'evaluate',payload:'artifacts → OOS results matrix',causal_scope:'single run',

detail:'503 frozen strategy artifacts → single run on the OOS window 2024-01-02 → 2026-05-29 → results matrix: PF · Sharpe · MDD · TIM · WR'}

]

};

var NODE_BY_ID={},NODE_BY_LEV=[];

PIPELINE.nodes.forEach(function(n){NODE_BY_ID[[n.id](http://n.id)]=n;NODE_BY_LEV[n.lev]=n;});

function edgeAt(i){return PIPELINE.edges[i];} // boundary i = edge between level i and i+1

// BND_DEF derived from the edges (content = edge.detail) — each boundary has a verb (edge.verb).

var BND_DEF=[PIPELINE.edges.map](http://PIPELINE.edges.map)(function(e){return e.detail;});



var stage=document.getElementById('stage'),cv=document.getElementById('tlc'),ctx=cv.getContext('2d');

var tip=document.getElementById('tip'),panel=document.getElementById('panel'),

panelTitle=document.getElementById('panelTitle'),panelBody=document.getElementById('panelBody');

var cw=940,chh=600;



var STATE={mode:'overview',asset:0,labels:true,flow:true,names:'sample',metric:'pf',speed:1,paused:false,camPreset:'iso',inspect:null};

var MODE_KEYS=['overview','dataflow','qc','split','setup','dq','optuna','artifact','oos','leak']; // keys 1-9,0 → mode (single source)

var CLK=0,lastTick=0,flash=0;

var LOD={cap:0.55,obj:0.55,name:0.75,micro:1.1};

var LBL_DEBUG=false;try{LBL_DEBUG=[location.search](http://location.search).indexOf('lbldebug')>=0;}catch(e){}

var LBL_AUDIT=false;try{LBL_AUDIT=[location.search](http://location.search).indexOf('lblaudit')>=0;}catch(e){} // CI: dump label boxes to <pre id=lblaudit>

var PIX_AUDIT=false;try{PIX_AUDIT=[location.search](http://location.search).indexOf('pixaudit')>=0;}catch(e){} // CI: pixel signature (downsample 64×40) to <pre id=pixaudit>

var EXPORT_FONT=1; // font-tier multiplier for PNG export



var userMoved=false;



var LBL_DEF={},LBL_OVR={},LBL_OFF={},LBL_ORDER=[],LBL_GRP={};



var HL={key:null,pending:false};

var ORIG_LBL={feat:[FEATURES.map](http://FEATURES.map)(function(f){return [f.name](http://f.name);}),asset:ASSETS.slice(),

gateId:[QC.map](http://QC.map)(function(g){return [g.id](http://g.id);}),gateName:[QC.map](http://QC.map)(function(g){return [g.name](http://g.name);})};

function tVal(key,def,grp){

if(LBL_DEF[key]==null){LBL_DEF[key]=def;LBL_GRP[key]=grp||'Other';LBL_ORDER.push(key);}

if(LBL_OFF[key])return '';

var o=LBL_OVR[key];return o!=null?o:LBL_DEF[key];

}

function T(key,def,grp){

var v=tVal(key,def,grp);

if(!LBL_OFF[key]&&HL.key===key)HL.pending=true;

return v;

}

function aname(i){if(HL.key==='asset'+i)HL.pending=true;return LBL_OFF['asset'+i]?'':ASSETS[i];}

function fname(i){if(HL.key==='feat'+i)HL.pending=true;return LBL_OFF['feat'+i]?'':FEATURES[i].name;}

function anameV(i){return LBL_OFF['asset'+i]?'':ASSETS[i];}

function fnameV(i){return LBL_OFF['feat'+i]?'':FEATURES[i].name;}

function gidv(k){if(HL.key==='gate'+k||HL.key==='gateN'+k)HL.pending=true;return LBL_OFF['gate'+k]?'':QC[k].id;}

function lblSave(){try{localStorage.setItem('sp500_pipeline_labels_v3',JSON.stringify({

ovr:LBL_OVR,off:LBL_OFF,

feat:[FEATURES.map](http://FEATURES.map)(function(f){return [f.name](http://f.name);}),asset:ASSETS.slice(),

gateId:[QC.map](http://QC.map)(function(g){return [g.id](http://g.id);}),gateName:[QC.map](http://QC.map)(function(g){return [g.name](http://g.name);})

}));}catch(e){}}

function lblLoad(){try{var s=localStorage.getItem('sp500_pipeline_labels_v3');if(!s)return;var d=JSON.parse(s);

if(d.ovr)LBL_OVR=d.ovr;if(d.off)LBL_OFF=d.off;

if(d.feat)d.feat.forEach(function(v,i){if(FEATURES[i]&&v!=null)FEATURES[i].name=v;});

if(d.asset)d.asset.forEach(function(v,i){if(v!=null&&i<ASSETS.length)ASSETS[i]=v;});

if(d.gateId)d.gateId.forEach(function(v,i){if(QC[i]&&v!=null)QC[i].id=v;});

if(d.gateName)d.gateName.forEach(function(v,i){if(QC[i]&&v!=null)QC[i].name=v;});

}catch(e){}}

function lblResetAll(){LBL_OVR={};LBL_OFF={};

ORIG_LBL.feat.forEach(function(v,i){if(FEATURES[i])FEATURES[i].name=v;});

ORIG_LBL.asset.forEach(function(v,i){ASSETS[i]=v;});

ORIG_LBL.gateId.forEach(function(v,i){if(QC[i])QC[i].id=v;});

ORIG_LBL.gateName.forEach(function(v,i){if(QC[i])QC[i].name=v;});

lblSave();}



var ISO={W:260,D:150,LEVH:240};

var PD0=5400;

var ROT={yaw:-0.62,pitch:0.55,t:{yaw:-0.62,pitch:0.55},cy:1,sy:0,cp:1,sp:0};

ROT.step=function(dt){var k=Math.min(1,dt*5);

this.yaw+=(this.t.yaw-this.yaw)*k;this.pitch+=(this.t.pitch-this.pitch)*k;

this.pitch=clamp(this.pitch,0.05,1.45);this.t.pitch=clamp(this.t.pitch,0.05,1.45);

[this.cy](http://this.cy)=Math.cos(this.yaw);[this.sy](http://this.sy)=Math.sin(this.yaw);

this.cp=Math.cos(this.pitch);this.sp=Math.sin(this.pitch);};

ROT.step(0);



function P3(x,y,z){

var x1=x*[ROT.cy](http://ROT.cy)-y*[ROT.sy](http://ROT.sy), y1=x*[ROT.sy](http://ROT.sy)+y*[ROT.cy](http://ROT.cy);

var d=y1*ROT.cp-z*ROT.sp;

var f=PD0/(PD0+d);

return {x:x1*f, y:-(y1*ROT.sp+z*ROT.cp)*f, d:d};}

function lp(lev,a,b,dz){return P3((a-0.5)*ISO.W,(b-0.5)*ISO.D,lev*ISO.LEVH+(dz||0));}



function bp(i,a,b){return P3((a-0.5)*ISO.W,(b-0.5)*ISO.D,i*ISO.LEVH+BND_DZ[i]);}



function faceVis(nx,ny,nz){var ny1=nx*[ROT.sy](http://ROT.sy)+ny*[ROT.cy](http://ROT.cy);return (ny1*ROT.cp-nz*ROT.sp)<-1e-4;}



function Camera2D(){this.x=0;this.y=0;this.z=1;this.t={x:0,y:0,z:1};}

Camera2D.prototype.step=function(dt){var k=Math.min(1,dt*5);

this.x+=(this.t.x-this.x)*k;this.y+=(this.t.y-this.y)*k;this.z+=(this.t.z-this.z)*k;};

Camera2D.prototype.S=function(p){return {x:(p.x-this.x)*this.z+cw/2,y:(p.y-this.y)*this.z+chh/2};};

var CAM=new Camera2D();

function SS(lev,a,b,dz){return CAM.S(lp(lev,a,b,dz));}



function HitTestIndex(){this.items=[];}

HitTestIndex.prototype.clear=function(){this.items.length=0;};

HitTestIndex.prototype.addPts=function(pts,payload){

var x0=1e9,y0=1e9,x1=-1e9,y1=-1e9,i;

for(i=0;i<pts.length;i++){var p=CAM.S(pts[i]);if(p.x<x0)x0=p.x;if(p.y<y0)y0=p.y;if(p.x>x1)x1=p.x;if(p.y>y1)y1=p.y;}

this.items.push({x0:x0,y0:y0,x1:x1,y1:y1,p:payload});};

HitTestIndex.prototype.addRect=function(x,y,w,h,payload){this.items.push({x0:x,y0:y,x1:x+w,y1:y+h,p:payload});};

HitTestIndex.prototype.find=function(mx,my){

for(var i=this.items.length-1;i>=0;i--){var it=this.items[i];

if(mx>=it.x0&&mx<=it.x1&&my>=it.y0&&my<=it.y1)return it.p;}

return null;};

var HITS=new HitTestIndex();



function poly(pts,fill,stroke,lw,dash){

ctx.beginPath();

for(var i=0;i<pts.length;i++){var s=CAM.S(pts[i]);if(i)ctx.lineTo(s.x,s.y);else ctx.moveTo(s.x,s.y);}

ctx.closePath();

if(fill){ctx.fillStyle=fill;ctx.fill();}

if(stroke){[ctx.save](http://ctx.save)();ctx.strokeStyle=stroke;ctx.lineWidth=lw||1;ctx.setLineDash(dash||[]);ctx.stroke();ctx.restore();}

return [pts.map](http://pts.map)(function(p){return CAM.S(p);});}

function polyS(pts,fill,stroke,lw,dash){

ctx.beginPath();

for(var i=0;i<pts.length;i++){if(i)ctx.lineTo(pts[i].x,pts[i].y);else ctx.moveTo(pts[i].x,pts[i].y);}

ctx.closePath();

if(fill){ctx.fillStyle=fill;ctx.fill();}

if(stroke){[ctx.save](http://ctx.save)();ctx.strokeStyle=stroke;ctx.lineWidth=lw||1;ctx.setLineDash(dash||[]);ctx.stroke();ctx.restore();}}

function line2(p1,p2,col,w,dash){var a=CAM.S(p1),b=CAM.S(p2);

[ctx.save](http://ctx.save)();ctx.strokeStyle=col;ctx.lineWidth=w||1;ctx.setLineDash(dash||[]);ctx.lineCap='round';

ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();ctx.restore();}

var CUR_FONT='';

function setFont(f){if(f!==CUR_FONT){CUR_FONT=f;ctx.font=f;}}

function txtS(s,x,y,col,al,sz,wt){

var fz=(sz||11)*zScale();

setFont(uiFont(wt,fz));

ctx.textAlign=al||'left';ctx.textBaseline='alphabetic';

if(HL.pending){HL.pending=false;

var tw=Math.max(10,ctx.measureText(s).width);

var ax=(al==='center')?x-tw/2:((al==='right')?x-tw:x);

var ph=pulse();

fillRR(ax-5,y-fz-3,tw+10,fz+8,5,rgba(TEAL,0.14+0.14*ph),rgba(TEAL,0.55+0.4*ph),1.3);}

ctx.fillStyle=txc(col);ctx.fillText(s,x,y);} // txc(): accent→text-safe (WCAG ≥4.5:1)

function txt(s,p,col,al,sz,wt,dx,dy){var q=CAM.S(p);txtS(s,q.x+(dx||0),q.y+(dy||0),col,al,sz,wt);}

function rrectS(x,y,w,h,r){if(ctx.roundRect){ctx.beginPath();ctx.roundRect(x,y,w,h,r);}else{ctx.beginPath();ctx.rect(x,y,w,h);}}

function fillRR(x,y,w,h,r,fillStyle,strokeStyle,lw){ // filled + stroked rounded-rect (tile/pill)

ctx.fillStyle=fillStyle;rrectS(x,y,w,h,r);ctx.fill();

[ctx.save](http://ctx.save)();ctx.strokeStyle=strokeStyle;ctx.lineWidth=lw||1.2;ctx.setLineDash([]);rrectS(x,y,w,h,r);ctx.stroke();ctx.restore();}

function strokeRR(x,y,w,h,r,col,lw){ // outline-only rounded-rect (glow/flash)

[ctx.save](http://ctx.save)();ctx.strokeStyle=col;ctx.lineWidth=lw||1;ctx.setLineDash([]);rrectS(x,y,w,h,r);ctx.stroke();ctx.restore();}

function triUpS(x,y,col){ctx.fillStyle=col;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x-4.5,y+7);ctx.lineTo(x+4.5,y+7);ctx.closePath();ctx.fill();}



function prism(lev,a0,b0,a1,b1,base,h,col,topA){

var B0=lp(lev,a0,b0,base),B1=lp(lev,a1,b0,base),B2=lp(lev,a1,b1,base),B3=lp(lev,a0,b1,base);

var T0=lp(lev,a0,b0,base+h),T1=lp(lev,a1,b0,base+h),T2=lp(lev,a1,b1,base+h),T3=lp(lev,a0,b1,base+h);

var F=[

{n:[0,0,1], p:[T0,T1,T2,T3], a:(topA==null?0.14:topA), s:true},

{n:[0,0,-1],p:[B0,B3,B2,B1], a:0.26},

{n:[1,0,0], p:[B1,B2,T2,T1], a:0.30},

{n:[-1,0,0],p:[B0,T0,T3,B3], a:0.30},

{n:[0,1,0], p:[B2,B3,T3,T2], a:0.20},

{n:[0,-1,0],p:[B0,B1,T1,T0], a:0.20}];

var vis=[],i;

for(i=0;i<6;i++)if(faceVis(F[i].n[0],F[i].n[1],F[i].n[2]))vis.push(F[i]);

vis.sort(function(p,q){return (q.p[0].d+q.p[2].d)-(p.p[0].d+p.p[2].d);});

var topScr=null;

for(i=0;i<vis.length;i++){var f=vis[i];

var scr=poly(f.p,rgba(col,f.a),f.s?col:null,1.1);

if(f.s)topScr=scr;}

return topScr||[CAM.S(T0),CAM.S(T1),CAM.S(T2),CAM.S(T3)];}



// Palette by ROLE (5 families), red (RED/SL) reserved for error/FAIL — it is not a category color.

function roleColor(role){var m={source:CAN,store:TEAL,transform:GREEN,control:AMB,output:TP};return m[role]||CAN;}

// layer title + color read from the graph (NODE_BY_LEV). The 'Lx' number is appended from lev → renumbering is free.

function caption(lev){if(!STATE.labels)return;

var n=NODE_BY_LEV[lev];if(!n)return;

var s=T('lvl'+(lev+1),'L'+(lev+1)+' · '+n.title,'Levels');if(!s)return;

var by=(BNDY[lev]!=null)?BNDY[lev]:CAM.S(P3(0,0,lev*ISO.LEVH+255)).y;

txtS(s,10,by+15,roleColor(n.role),'left',12.5,'700'); // color by role (qualitative) — the title is never red

var fz=12.5*zScale(),w=ctx.measureText(s).width;

obstacle(10,by+15-fz-2,10+w,by+18);

HITS.addRect(8,by+15-fz-4,w+10,fz+10,{type:'layercap',lev:lev}); // title click = Layer inspection

}



function flowArrow(lev){

var tert=vget('--color-text-tertiary','#777');

var p1=lp(lev,0.5,0.30,58),p2=lp(lev+1,0.5,0.30,2);

line2(p1,p2,tert,1.4,[]);

var s=CAM.S(p2);triUpS(s.x,s.y,tert);

if(STATE.flow&&!STATE.paused){

var k=((CLK*0.45+lev*0.19)%1),a=CAM.S(p1),b=CAM.S(p2);

var px=a.x+(b.x-a.x)*k,py=a.y+(b.y-a.y)*k;

ctx.fillStyle=TEAL;ctx.beginPath();ctx.arc(px,py,3,0,7);ctx.fill();}}



function byD(arr){return arr.slice().sort(function(p,q){return q.d-p.d;});}



var BNDY=[];

function boundaryLines(){

BNDY.length=0;

var col=vget('--color-border-tertiary','rgba(255,255,255,0.12)'),i,y;

[ctx.save](http://ctx.save)();ctx.strokeStyle=col;ctx.lineWidth=1;ctx.setLineDash([7,6]);

for(i=0;i<BND_DEF.length;i++){

y=CAM.S(bp(i,0.5,0.5)).y;BNDY[i]=y;

if(y<-8||y>chh+8)continue;

y=Math.round(y)+0.5;

ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(cw,y);ctx.stroke();

}

ctx.restore();

}

function wrapLines(s,maxW){

var words=String(s).split(/\s+/),lines=[],cur='',i;

for(i=0;i<words.length;i++){var t=cur?cur+' '+words[i]:words[i];

if(ctx.measureText(t).width>maxW&&cur){lines.push(cur);cur=words[i];}else cur=t;}

if(cur)lines.push(cur);

if(lines.length>4){lines.length=4;lines[3]+='…';}

return lines;}

function boundaryCards(){

if(!STATE.labels)return;

var sc=zScale(),W=178,inW=W-18,fz=8.5*sc,tz=8*sc,lh=Math.round(fz+3.5),pad=8;

var sec=vget('--color-text-secondary','#999'),bg=vget('--color-background-secondary','#2b2b28'),

brd=vget('--color-border-secondary','#555');

var cards=[],i,k;

for(i=0;i<BND_DEF.length;i++){

var s=T('bnd'+i,BND_DEF[i],'Layer boundaries');

var isHL=(HL.key==='bnd'+i);HL.pending=false;

if(!s)continue;

var sp=CAM.S(bp(i,(i%2===0)?1.04:-0.04,0.5)),c0=CAM.S(bp(i,0.5,0.5));



var yLo=(i>0)?BNDY[i-1]:CAM.S(P3(0,0,0)).y;

var anch={x:sp.x,y:(BNDY[i]+yLo)/2};

if(anch.x<-cw*0.2||anch.x>cw*1.2||anch.y<-chh*0.25||anch.y>chh*1.25)continue;

cards.push({i:i,s:s,hl:isHL,anch:anch,right:sp.x>=c0.x});

}

cards.sort(function(p,q){return p.anch.y-q.anch.y;});

var minY={l:6,r:6};

for(k=0;k<cards.length;k++){

var c=cards[k];

setFont(uiFont('400',fz));

var lines=wrapLines(c.s,inW);

var H=pad+Math.round(tz)+6+lines.length*lh+pad-2;

var x=c.right?cw-W-8:8;

var y=clamp(c.anch.y-H/2,c.right?minY.r:minY.l,Math.max(6,chh-H-6));



if(!c.right){

var lk='lvl'+(c.i+1),

capOn=STATE.labels&&!LBL_OFF[lk]&&(LBL_OVR[lk]==null||LBL_OVR[lk]!=='');

if(capOn){

var ycap=(BNDY[c.i]!=null?BNDY[c.i]:CAM.S(P3(0,0,c.i*ISO.LEVH+255)).y)+15;

if(ycap>y-13&&ycap<y+H+13){

var above=ycap-16-H,below=ycap+9;

y=(Math.abs(above-y)<=Math.abs(below-y)&&above>=6)?above:below;

y=clamp(y,c.right?minY.r:minY.l,Math.max(6,chh-H-6));

}

}

}

y=Math.min(y,chh-H-6);

if(c.right)minY.r=y+H+5;else minY.l=y+H+5;



ctx.fillStyle=bg;rrectS(x,y,W,H,8);ctx.fill();

[ctx.save](http://ctx.save)();ctx.strokeStyle=c.hl?TEAL:brd;ctx.lineWidth=c.hl?1.5:1;ctx.setLineDash(c.hl?[]:[5,4]);

rrectS(x,y,W,H,8);ctx.stroke();ctx.restore();

if(c.hl)strokeRR(x-2.5,y-2.5,W+5,H+5,10,rgba(TEAL,0.25+0.45*pulse()),3.5);

var yT=y+pad+tz;

var ev=(edgeAt(c.i)||{}).verb||''; // each boundary leads with a verb (from the graph edge)

txtS('L'+(c.i+1)+' → L'+(c.i+2)+(ev?' · '+ev:''),x+9,yT,TEAL,'left',8,'700');

for(i=0;i<lines.length;i++)txtS(lines[i],x+9,yT+6+i*lh+fz,sec,'left',8.5);

HITS.addRect(x,y,W,H,{type:'bnote',i:c.i});

obstacle(x,y,x+W,y+H);

}

}



function AlpacaSource(){}

AlpacaSource.prototype.draw=function(){

caption(0);



var cols=36,rows=14,n=7,r,c;

[ctx.save](http://ctx.save)();ctx.fillStyle=rgba(CAN,0.30);ctx.beginPath();

for(r=0;r<rows&&n<N_ASSETS;r++)for(c=0;c<cols&&n<N_ASSETS;c++,n++){

var a0=0.05+0.90*(c/cols),b0=0.34+0.62*(r/rows),da=0.90/cols*0.72,db=0.62/rows*0.62;

var q=[SS(0,a0,b0,1),SS(0,a0+da,b0,1),SS(0,a0+da,b0+db,1),SS(0,a0,b0+db,1)];

ctx.moveTo(q[0].x,q[0].y);ctx.lineTo(q[1].x,q[1].y);ctx.lineTo(q[2].x,q[2].y);ctx.lineTo(q[3].x,q[3].y);ctx.closePath();

}

ctx.fill();ctx.restore();

HITS.addPts([lp(0,0.05,0.34,0),lp(0,0.95,0.96,0)],{type:'universe'});

if(STATE.labels){var pu=SS(0,0.5,1.06,0);

qLabel({key:'uni_caption',def:'S&P 500 universe: 503 tickers · 7 named + the rest as a grid',grp:'Source / Universe',

x:pu.x,y:pu.y,col:vget('--color-text-secondary','#999'),al:'center',sz:10,pr:1});}



var named=[],i,k;

for(i=0;i<7;i++)named.push({i:i,a:0.18+i*0.114,d:lp(0,0.18+i*0.114,0.16,0).d});

named=byD(named);

for(k=0;k<named.length;k++){

var t=named[k],sel=(t.i===STATE.asset);

prism(0,t.a,0.10,t.a+0.056,0.24,1,sel?26:18,sel?GREEN:CAN,sel?0.30:0.22);

HITS.addPts([lp(0,t.a-0.008,0.08,sel?30:22),lp(0,t.a+0.064,0.26,0)],{type:'asset',a:t.i});

if(STATE.names==='sample'&&STATE.labels){

var s=SS(0,t.a+0.028,0.30,0),sa=SS(0,t.a+0.028,0.22,0);

qLabel({key:'asset'+t.i,text:anameV(t.i),x:s.x,y:s.y,col:sel?GREEN:vget('--color-text-secondary','#999'),

al:'right',sz:9,wt:sel?'600':'',rot:-0.55,pr:sel?3:2,lod:[LOD.name](http://LOD.name),ax:sa.x,ay:sa.y});}

}



var L='OHLCV'.split(''),cubes=[];

for(i=0;i<5;i++)cubes.push({i:i,d:lp(0,0.055+i*0.058,0.11,4).d});

cubes=byD(cubes);

for(k=0;k<cubes.length;k++){

i=cubes[k].i;

prism(0,0.04+i*0.058,0.07,0.075+i*0.058,0.15,1,9,CAN,0.26);

if(STATE.labels)txt(L[i],lp(0,0.057+i*0.058,0.11,10),vget('--color-text-primary','#eee'),'center',8,'600',0,-3);

}

if(STATE.labels){var pf=SS(0,0.16,0.34,0);

qLabel({key:'raw_flow',def:'1h OHLCV · session 09:00–16:00 ET (~7 candles/day) · 2016-01-04 → today',grp:'Source / Universe',

x:pf.x,y:pf.y,col:vget('--color-text-tertiary','#777'),al:'center',sz:8.5,pr:1});}



var sA=SS(0,0.84,0.10,24),wA=112,hA=34;

if(STATE.flow){

var start=SS(0,0.78,0.16,20),end=SS(1,0.18,0.50,16),iLine;

[ctx.save](http://ctx.save)();ctx.strokeStyle=rgba(TEAL,0.45);ctx.lineWidth=1;ctx.setLineDash([5,6]);

ctx.lineDashOffset=STATE.paused?0:-CLK*22;

for(iLine=-1;iLine<=1;iLine++){

ctx.beginPath();ctx.moveTo(start.x,start.y+iLine*5);ctx.bezierCurveTo(start.x-35,start.y-30+iLine*3,end.x+30,end.y+24-iLine*4,end.x,end.y+iLine*4);ctx.stroke();

}

ctx.restore();

}

if(flash>0)strokeRR(sA.x-wA/2-6,sA.y-hA/2-6,wA+12,hA+12,13,rgba(TEAL,flash*0.8),2);

[GLYPHS.cloud](http://GLYPHS.cloud)(sA.x,sA.y,wA,hA,TEAL,T('api_pill','Alpaca SIP · 1h','Source / Universe')||'');

if(STATE.labels)qLabel({key:'api_cron',def:'REST · cron :05 · ET session guard',grp:'Source / Universe',

x:sA.x,y:sA.y+hA/2+14,col:vget('--color-text-tertiary','#777'),al:'center',sz:7.5,pr:1,ax:sA.x,ay:sA.y+hA/2});

HITS.addRect(sA.x-wA/2,sA.y-hA/2,wA,hA,{type:'api'});

};



function ZipStore(){}

ZipStore.prototype.draw=function(){

caption(1);

var list=[],i;

for(i=0;i<7;i++){var pj=lp(1,0.08+i*0.128,0.5,16);list.push({i:i,pj:pj,d:pj.d});}

list=byD(list);

for(var k=0;k<list.length;k++){

var t=list[k],sel=(t.i===STATE.asset),s=CAM.S(t.pj);

if(flash>0&&sel)strokeRR(s.x-20,s.y-26,40,52,10,rgba(GREEN,flash*0.8),2);

var cZip=GLYPHS.zipCrate({lev:1,a:0.08+t.i*0.128,b:0.5,i:t.i,sel:sel,h:sel?32:24});

if(STATE.names==='sample'&&STATE.labels)qLabel({key:'asset'+t.i,text:(anameV(t.i)||'').toLowerCase(),

x:cZip.x,y:cZip.y+25,col:sel?GREEN:vget('--color-text-secondary','#999'),al:'center',sz:8.5,wt:sel?'600':'',

pr:sel?3:2,lod:[LOD.name](http://LOD.name),ax:cZip.x,ay:cZip.y+12});

}

GLYPHS.stackBadge(1,0.91,0.5,16,CAN,'×510','zip');

if(STATE.labels){var pz=SS(1,0.5,0.93,0);

qLabel({key:'zip_caption',def:'1 zip = 1 ticker · CSV: YYYYMMDD HH:MM,o,h,l,c,v · prices ×10000 · 139 MB',grp:'Store / DuckDB',

x:pz.x,y:pz.y,col:vget('--color-text-tertiary','#777'),al:'center',sz:8.5,pr:1});}

};



function DuckDBLayer(){}

DuckDBLayer.prototype.draw=function(){

caption(2);

GLYPHS.dbCylinder({lev:2,a:0.26,b:0.52,ra:0.17,rb:0.40,dz:2,h:34,col:TEAL});

if(STATE.labels){

var pd1=SS(2,0.26,0.52,40),pd2=SS(2,0.26,0.80,0),pda=SS(2,0.26,0.52,34);

qLabel({key:'db_raw',def:'raw_ohlcv_1h · BIGINT ×10000',grp:'Store / DuckDB',

x:pd1.x,y:pd1.y-2,col:vget('--color-text-primary','#eee'),al:'center',sz:9,wt:'600',pr:2,ax:pda.x,ay:pda.y});

qLabel({key:'db_rows',def:'8 841 820 rows · 166 MB',grp:'Store / DuckDB',

x:pd2.x,y:pd2.y,col:vget('--color-text-tertiary','#777'),al:'center',sz:8,pr:1});

}

GLYPHS.sqlView({lev:2,a0:0.64,b0:0.40,a1:0.92,b1:0.64,dz:20,col:TEAL,linkA:0.56,linkB:0.54,linkDz:26});

if(STATE.labels){

var pv1=SS(2,0.78,0.52,22),pv2=SS(2,0.78,0.80,0),pva=SS(2,0.78,0.52,16);

qLabel({key:'db_view',def:'VIEW ohlcv_1h → USD (/10000.0)',grp:'Store / DuckDB',

x:pv1.x,y:pv1.y-2,col:vget('--color-text-secondary','#999'),al:'center',sz:8.5,wt:'600',pr:2,ax:pva.x,ay:pva.y});

qLabel({key:'db_zero',def:'zero storage duplication',grp:'Store / DuckDB',

x:pv2.x,y:pv2.y,col:vget('--color-text-tertiary','#777'),al:'center',sz:8,pr:1});

}

var sm=SS(2,0.94,0.20,8),link=SS(2,0.56,0.40,18);

[ctx.save](http://ctx.save)();ctx.strokeStyle=rgba(TEAL,0.50);ctx.lineWidth=1;ctx.setLineDash([3,4]);

ctx.beginPath();ctx.moveTo(link.x,link.y);ctx.lineTo(sm.x-22,sm.y);ctx.stroke();ctx.restore();

GLYPHS.labelTag(sm.x,sm.y,48,20,TEAL,'_meta');

HITS.addRect(sm.x-24,sm.y-10,48,20,{type:'meta'});

};

function QCGateRing(){}

QCGateRing.prototype.draw=function(){

// locks placed at fractional 'a' (not fixed px) → they spread out and sit on the layer plane

var k,n=QC.length,aStart=0.10,aStep=0.045;

var s0=SS(2,aStart,0.88,4),sN=SS(2,aStart+(n-1)*aStep,0.88,4);

HITS.addRect(s0.x-8,s0.y-12,(sN.x-s0.x)+20,24,{type:'qcAll'});

for(k=0;k<n;k++){

var sk=SS(2,aStart+k*aStep,0.88,4);

drawLockS(sk.x,sk.y,12,PINK,String(k+1));

HITS.addRect(sk.x-6,sk.y-9,12,18,{type:'qc',g:k});

}

obstacle(s0.x-8,s0.y-12,sN.x+12,s0.y+16);

if(STATE.labels)qLabel({key:'qc_badge',def:'QC-01…QC-11 gate every load · view 3',grp:'QC gates',

x:sN.x+14,y:sN.y+3,col:vget('--color-text-tertiary','#777'),al:'left',sz:7.5,pr:1,

ax:sN.x+10,ay:sN.y});

};



function TransformLayer(){}

TransformLayer.prototype.draw=function(){

caption(3);

var sec=vget('--color-text-secondary','#999'),tert=vget('--color-text-tertiary','#777');



var sn=SS(3,0.16,0.52,18),wS=86,hS=26;

GLYPHS.snapshotCam(sn.x,sn.y,CAN,T('tf_snap','snapshot','Snapshot / Parquet')||'');

if(STATE.labels)qLabel({key:'tf_manifest',def:'atomic copy + manifest JSON (price_view)',grp:'Snapshot / Parquet',

x:sn.x,y:sn.y+hS/2+11,col:tert,al:'center',sz:7.5,pr:1,ax:sn.x,ay:sn.y+hS/2});

HITS.addRect(sn.x-27,sn.y-21,70,40,{type:'snapshot'});



line2(lp(3,0.24,0.52,18),lp(3,0.70,0.52,18),tert,1.2,[]);

var ah=CAM.S(lp(3,0.70,0.52,18));

[ctx.save](http://ctx.save)();ctx.translate(ah.x,ah.y);ctx.rotate(Math.PI/2);triUpS(0,0,tert);ctx.restore();



var pq=SS(3,0.80,0.52,18);

GLYPHS.parquetFile(pq.x,pq.y,AMB,true);

txtS('×503',pq.x+20,pq.y+18,sec,'center',7.5,'700');

HITS.addRect(pq.x-24,pq.y-30,58,54,{type:'parquet'});

if(STATE.labels){

var pt1=SS(3,0.5,0.16,8),pt2=SS(3,0.5,0.97,0);

qLabel({key:'tf_zero',def:'zero derived columns — features computed only by the transformer (L7, Layers_Short_SOT/L7_features_x_label_y_[eng.md](http://eng.md))',grp:'Snapshot / Parquet',

x:pt1.x,y:pt1.y,col:sec,al:'center',sz:8.5,pr:1});

qLabel({key:'tf_caption',def:'503 files · zstd · <TICKER>/ohlcv.parquet',grp:'Snapshot / Parquet',

x:pt2.x,y:pt2.y,col:tert,al:'center',sz:8.5,pr:1});

}

};



function SplitLayer(){}

SplitLayer.prototype.draw=function(){

caption(4);

var tert=vget('--color-text-tertiary','#777'),sec=vget('--color-text-secondary','#999');

var i,edges=[],nb=SPLIT.bands.length;

for(i=0;i<nb;i++){

var b=SPLIT.bands[i];

var acc=aOf(i===0?0:SPLIT.edgeF[i-1]),a1=aOf(i===nb-1?1:SPLIT.edgeF[i]);

poly([lp(4,acc,0.30,3),lp(4,a1,0.30,3),lp(4,a1,0.78,3),lp(4,acc,0.78,3)],rgba(b.col,0.20),b.col,1.1);

HITS.addPts([lp(4,acc,0.28,12),lp(4,a1,0.80,0)],{type:'split',k:i});

if(STATE.labels){

var ps1=SS(4,(acc+a1)/2,0.52,10);

qLabel({key:'split_'+[b.id](http://b.id),def:[b.name](http://b.name),grp:'Time split',

x:ps1.x,y:ps1.y,col:b.col,al:'center',sz:9.5,wt:'600',pr:3});

}

if(i<nb-1)edges.push(aOf(SPLIT.edgeF[i]));

}

for(i=0;i<edges.length;i++){

var e=edges[i],j,bb0,bb1;

if(CAM.z<0.7){

poly([lp(4,e-0.012,0.30,4),lp(4,e+0.012,0.30,4),lp(4,e+0.012,0.78,4),lp(4,e-0.012,0.78,4)],rgba(SL,0.26),SL,1,[4,3]);

}else{

for(j=0;j<5;j++){

bb0=0.31+j*0.092;bb1=bb0+0.052;

poly([lp(4,e-0.020,bb0,5),lp(4,e-0.011,bb0,5),lp(4,e-0.011,bb1,5),lp(4,e-0.020,bb1,5)],rgba(SL,0.35),SL,0.7,[]);

poly([lp(4,e+0.011,bb0,5),lp(4,e+0.020,bb0,5),lp(4,e+0.020,bb1,5),lp(4,e+0.011,bb1,5)],rgba(AMB,0.20),AMB,0.8,[3,3]);

}

}

HITS.addPts([lp(4,e-0.02,0.28,8),lp(4,e+0.02,0.80,0)],{type:'purge',k:i});

HITS.addPts([lp(4,e+0.006,0.28,8),lp(4,e+0.032,0.80,0)],{type:'embargo',k:i});

}

// --- Time axis under the bands: baseline + year ticks (for scale) + highlighted boundaries ---

var axB=0.86,axZ=1,axA0=aOf(0),axA1=aOf(1);

line2(lp(4,axA0,axB,axZ),lp(4,axA1,axB,axZ),tert,1.4,[]);

var pe=CAM.S(lp(4,axA1,axB,axZ)), // "time →" arrow as a chevron from world points (tilted slab)

pk1=CAM.S(lp(4,axA1-0.018,axB-0.03,axZ)),pk2=CAM.S(lp(4,axA1-0.018,axB+0.03,axZ));

[ctx.save](http://ctx.save)();ctx.strokeStyle=tert;ctx.lineWidth=1.4;ctx.setLineDash([]);ctx.lineCap='round';

ctx.beginPath();ctx.moveTo(pk1.x,pk1.y);ctx.lineTo(pe.x,pe.y);ctx.lineTo(pk2.x,pk2.y);ctx.stroke();ctx.restore();

if(STATE.labels)txt('time',lp(4,axA1,axB,axZ),tert,'left',7.5,null,8,4);

var emphF=[{f:dfrac('2016-10-14'),col:CAN,key:'split_axis_warmend',date:'2016-10-14'},

{f:SPLIT.edgeF[1],col:SL,key:'split_axis_trainoos',date:'2023-12-29 → 2024-01-02'}];

var firstY=SPLIT.years[0].y,lastY=SPLIT.years[SPLIT.years.length-1].y;

for(i=0;i<SPLIT.years.length;i++){

var Y=SPLIT.years[i],ay=aOf(Y.f),dup=false,e2,keep;

for(e2=0;e2<emphF.length;e2++)if(Math.abs(Y.f-emphF[e2].f)<0.004)dup=true; // dedup: year ≈ boundary → boundary takes the marker

if(dup)continue;

if(CAM.z>=0.75)keep=true; // LOD: every year / every 2 / sparse; ends always

else if(CAM.z>=0.55)keep=(Y.y%2===0)||Y.y===firstY||Y.y===lastY;

else keep=(Y.y%4===0)||Y.y===firstY||Y.y===lastY;

if(!keep)continue;

line2(lp(4,ay,axB-0.025,axZ),lp(4,ay,axB+0.025,axZ),tert,1,[]);

if(STATE.labels){var sy=CAM.S(lp(4,ay,axB+0.03,axZ)),fz=7.5*zScale();

txtS(String(Y.y),sy.x,sy.y+10,tert,'center',7.5);

var tw=ctx.measureText(String(Y.y)).width;

obstacle(sy.x-tw/2-2,sy.y+10-fz-2,sy.x+tw/2+2,sy.y+13);} // reserve space → qLabels avoid the years

}

for(i=0;i<emphF.length;i++){

var E=emphF[i],ae=aOf(E.f);

line2(lp(4,ae,axB-0.05,axZ),lp(4,ae,axB+0.05,axZ),E.col,1.6,[]); // taller tick for the window boundary

if(STATE.labels){var se=SS(4,ae,axB+0.06,axZ);

qLabel({key:E.key,def:[E.date](http://E.date),grp:'Time split',

x:se.x,y:se.y,col:E.col,al:'center',sz:8,wt:'600',pr:2,lod:0.55});}

}

if(STATE.labels){var pn=SS(4,0.5,0.14,6);

qLabel({key:'split_note',def:'TB labels overlap the boundaries → purge H=24 candles + embargo ~5 sessions',grp:'Time split',

x:pn.x,y:pn.y,col:sec,al:'center',sz:8.5,pr:1});}

};



function FeatureForest(){}

// L6 · trend-line setup detector (contract §3) — compact rig on the poster plane.

// Full anatomy in the flat 'setup' view (SetupGeometryView); here only the stage icon.

function SetupDetectorLayer(){}

SetupDetectorLayer.prototype.draw=function(){

caption(5);

var n=NODE_BY_LEV[5],tert=vget('--color-text-tertiary','#777'),bord=vget('--color-border-secondary','#555');

var a0=0.10,aw=0.80,bd=0.5,base=4,hgt=150,N=9,t0=6,ut0=t0/(N-1),i;

function W(u,h){return lp(5,a0+u*aw,bd,base+h*hgt);} // u∈[0,1] level, h∈[0,1] "price"

function LT(u){return 0.80-0.34*u;} // resistance (traded) — falls

function LO(u){return LT(u)-0.26;} // opposing line (the SL sits here)

polyS([CAM.S(W(0,1.02)),CAM.S(W(1,1.02)),CAM.S(W(1,0)),CAM.S(W(0,0))],rgba(TEAL,0.05),bord,1,[]);

line2(W(0,LT(0)),W(1,LT(1)),RED,2,[]); // L_trend solid

line2(W(0,LO(0)),W(1,LO(1)),CAN,1.5,[6,4]); // L_opp dashed

var prevc=0;

for(i=0;i<N;i++){

var u=i/(N-1),lt=LT(u),lo=LO(u),hc,htop,hbot;

if(i<t0){var mid=lo+0.45*(lt-lo);hc=mid;htop=(i===2||i===4)?lt:mid+0.05;hbot=mid-0.06;}

else if(i===t0){hc=lt+0.06;htop=hc+0.04;hbot=lo+0.10;}

else{hc=prevc+0.05;htop=hc+0.04;hbot=hc-0.04;}

prevc=hc;

var col=(i>=t0)?TP:CAN,du=0.030,bb=0.022;

line2(W(u,hbot),W(u,htop),col,1.2,[]); // wick

poly([W(u-du,hc+bb),W(u+du,hc+bb),W(u+du,hc-bb),W(u-du,hc-bb)],rgba(col,0.5),col,1);

if(i===2||i===4){var st=CAM.S(W(u,lt));ctx.fillStyle=AMB;ctx.beginPath();ctx.arc(st.x,st.y,3.5,0,7);ctx.fill();

HITS.addRect(st.x-6,st.y-6,12,12,{type:'setupTouch'});}

}

line2(W(ut0,0),W(ut0,1.0),rgba(TEAL,0.55),1.4,[2,3]); // vertical entry

var se=CAM.S(W(ut0,LT(ut0)+0.06));

[ctx.save](http://ctx.save)();ctx.strokeStyle=TEAL;ctx.lineWidth=2;ctx.beginPath();ctx.arc(se.x,se.y,5,0,7);ctx.stroke();ctx.restore();

HITS.addRect(se.x-7,se.y-7,14,14,{type:'setupEntry'});

var ur=ut0+0.05; // R0 bracket (close[t0] → L_opp)

line2(W(ur,LT(ut0)+0.06),W(ur,LO(ut0)),AMB,2,[]);

var sr=CAM.S(W(ur,(LT(ut0)+0.06+LO(ut0))/2));

txtS('R0',sr.x+7,sr.y+3,AMB,'left',9,'700');HITS.addRect(sr.x-8,sr.y-22,30,44,{type:'setupR0'});

HITS.addPts([W(0,0),W(1,0),W(0,1.02),W(1,1.02)],{type:'detector'});

if(STATE.labels){

var plt=CAM.S(W(1,LT(1))),plo=CAM.S(W(1,LO(1))),pe=CAM.S(W(ut0,1.05)),pinv=CAM.S(W(0.5,-0.12));

qLabel({key:'det_ltrend',def:'L_trend (resistance)',grp:'Setup detector',x:plt.x+4,y:plt.y,col:RED,al:'left',sz:8,wt:'600',pr:2,lod:[LOD.name](http://LOD.name)});

qLabel({key:'det_lopp',def:'L_opp (SL)',grp:'Setup detector',x:plo.x+4,y:plo.y+10,col:CAN,al:'left',sz:8,pr:2,lod:[LOD.name](http://LOD.name)});

qLabel({key:'det_t0',def:'entry_candle t0',grp:'Setup detector',x:pe.x,y:pe.y,col:TEAL,al:'center',sz:8.5,wt:'600',pr:2,lod:[LOD.name](http://LOD.name)});

qLabel({key:'det_inv',def:n.invariants.join(' · '),grp:'Setup detector',x:pinv.x,y:pinv.y,col:tert,al:'center',sz:8.5,pr:1});

}

};



// L7 as a standing 3D matrix (setups t × features X + label Y) — PT(u,v) pattern from OOSWall

FeatureForest.prototype.draw=function(){

caption(6);

var prim=vget('--color-text-primary','#eee'),tert=vget('--color-text-tertiary','#777'),

bord=vget('--color-border-secondary','#555'),ai=STATE.asset;

var bw=0.55,base=4,HZ6=150,nf=FEATURES.length; // nf=8 (7 X + 1 audit)

var NCOL=nf+2,NROW=6,ycol=NCOL-1; // col 0=header t · 1..nf=features · ycol=Y; rows 0=header x · 1..4=setups · 5=…

var A=CAM.S(lp(6,0.08,bw,base)),B=CAM.S(lp(6,0.92,bw,base)),

T1=CAM.S(lp(6,0.08,bw,base+HZ6)),T2=CAM.S(lp(6,0.92,bw,base+HZ6));

function PT(u,v){return lerp2(lerp2(T1,T2,u),lerp2(A,B,u),v);}

polyS([T1,T2,B,A],rgba(CAN,0.06),bord,1,[]);

var SUB='₁₂₃₄₅₆₇₈',rr,cc,showVal=(CAM.z>=1.0);

// readable column abbreviations (work order) mapped 1:1 to FEATURES; full names in hover/inspect

var FEAT_ABBR=['dTrend','dOpp','risk%','ret%','body/range','volZ','touches','close>line'];

for(rr=0;rr<NROW;rr++)for(cc=0;cc<NCOL;cc++){

var u0=cc/NCOL,u1=(cc+0.94)/NCOL,v0=rr/NROW,v1=(rr+0.92)/NROW;

var p00=PT(u0,v0),p10=PT(u1,v0),p11=PT(u1,v1),p01=PT(u0,v1),pc=PT((u0+u1)/2,(v0+v1)/2);

var hdrRow=(rr===0),hdrCol=(cc===0),isY=(cc===ycol),isEll=(rr===NROW-1);

if(hdrCol&&hdrRow){ // corner with the x/t diagonal

polyS([p00,p10,p11,p01],rgba(CAN,0.14),bord,0.8,[]);

[ctx.save](http://ctx.save)();ctx.strokeStyle=prim;ctx.lineWidth=1.4;ctx.setLineDash([]);

ctx.beginPath();ctx.moveTo(p00.x,p00.y);ctx.lineTo(p11.x,p11.y);ctx.stroke();ctx.restore();

var px=lerp2(p10,pc,0.4),pt=lerp2(p01,pc,0.4);

txtS('x',px.x,px.y+4,prim,'center',11,'700');txtS('t',pt.x,pt.y+4,prim,'center',11,'700');

}else if(hdrRow){ // column header — transform=GREEN (X) vs target=TP (Y)

polyS([p00,p10,p11,p01],isY?rgba(TP,0.20):rgba(GREEN,0.18),bord,0.8,[]);

if(isY)txtS('Y',pc.x,pc.y+5,TP,'center',12,'700');

else{var f=FEATURES[cc-1]; // family glyph instead of the x₁..x₈ placeholder; abbreviation on the axis label

drawFamilyMarker(pc.x,pc.y+3,[f.family](http://f.family),GREEN);

if(f.special)txtS('!',p10.x-6,p00.y+12,AMB,'center',9,'700');}

}else if(hdrCol){ // row header (setup)

polyS([p00,p10,p11,p01],rgba(CAN,0.10),bord,0.8,[]);

txtS(isEll?'…':('t'+SUB.charAt(rr-1)),pc.x,pc.y+4,prim,'center',10,'700');

}else if(isY){ // label Y cell (0/1)

var yv=isEll?-1:(rng(ai*23+rr*557+131)()<0.5?0:1);

polyS([p00,p10,p11,p01],yv<0?null:rgba(TP,0.10+0.45*yv),bord,0.8,[]);

if(showVal&&yv>=0)txtS(String(yv),pc.x,pc.y+3,yv?TP:tert,'center',8.5,'700');

}else{ // feature X cell — neutral (data), not red

polyS([p00,p10,p11,p01],rgba(CAN,0.09),bord,0.8,[]);

if(showVal&&!isEll)txtS((rng(ai*7+rr*131+cc*977)()*4-2).toFixed(1),pc.x,pc.y+3,tert,'center',7.5);

}

}

for(cc=1;cc<NCOL;cc++){ // HITS per column

var q0=PT(cc/NCOL,0),q1=PT((cc+0.94)/NCOL,0),q2=PT(cc/NCOL,1),q3=PT((cc+0.94)/NCOL,1);

var x0=Math.min(q0.x,q1.x,q2.x,q3.x),x1=Math.max(q0.x,q1.x,q2.x,q3.x),

y0=Math.min(q0.y,q1.y,q2.y,q3.y),y1=Math.max(q0.y,q1.y,q2.y,q3.y);

HITS.addRect(x0,y0,x1-x0,y1-y0,cc===ycol?{type:'label'}:{type:'feature',f:cc-1});

}

if(STATE.labels){

for(cc=1;cc<ycol;cc++){var ph=PT((cc+0.47)/NCOL,-0.05),pg=PT((cc+0.47)/NCOL,0.0); // column abbreviations (full names: hover/inspect)

qLabel({key:'feat'+(cc-1),text:FEAT_ABBR[cc-1],x:ph.x,y:ph.y,col:vget('--color-text-secondary','#999'),

al:'left',sz:9,rot:-0.62,pr:2,lod:[LOD.name](http://LOD.name),ax:pg.x,ay:pg.y});}

var phY=PT((ycol+0.47)/NCOL,-0.05),pgY=PT((ycol+0.47)/NCOL,0.0); // target label

qLabel({key:'feat_Y',def:'Y_outcome',grp:'Features & label',x:phY.x,y:phY.y,col:TP,

al:'left',sz:9,wt:'600',rot:-0.62,pr:2,lod:[LOD.name](http://LOD.name),ax:pgY.x,ay:pgY.y});

var pw=PT(1.02,0.12),pwa=PT(0.99,0.12); // sample weight (chip next to Y)

qLabel({key:'feat_w',def:'w_unique (weight)',grp:'Features & label',x:pw.x,y:pw.y,col:vget('--color-text-secondary','#999'),

al:'left',sz:8.5,rot:-0.62,pr:2,lod:[LOD.name](http://LOD.name),ax:pwa.x,ay:pwa.y});

var pcap=PT(0.5,-0.17);

qLabel({key:'ff_causal',def:'Features computed at t0 — only candles ≤ t0 (causality)',grp:'Features & label',

x:pcap.x,y:pcap.y,col:GREEN,al:'center',sz:10.5,wt:'600',pr:3});

var pn=PT(0.5,1.12);

qLabel({key:'ff_setup',def:'row = trend-line setup · columns = 7 X features + audit (close>line) + Y_outcome + weight w_unique · partition: asset × direction',grp:'Features & label',

x:pn.x,y:pn.y,col:tert,al:'center',sz:8.5,pr:1});

}

};



function QualityLayer(){}

QualityLayer.prototype.draw=function(){

caption(7);

var prim=vget('--color-text-primary','#eee'),tert=vget('--color-text-tertiary','#777'),i;

var ord=[];

for(i=0;i<DQ.length;i++){var ta=0.06+(i%3)*0.32,tb=(i<3)?0.24:0.76;

ord.push({i:i,a:ta,b:tb,d:lp(7,ta,tb,0).d});}

ord=byD(ord);

for(var k=0;k<ord.length;k++){

var t=ord[k],q=DQ[t.i],s=SS(7,t.a,t.b,16),w=46,h=20,col=dqCol(q.status);

fillRR(s.x-w/2,s.y-h/2,w,h,5,rgba(col,0.16),col,1.1);

drawStatusIcon(s.x-w/2+8,s.y-1,col,q.status);

txtS([q.name](http://q.name),s.x+5,s.y-2,prim,'center',7.5,'600');

txtS(q.status,s.x+5,s.y+8,col,'center',7.5,'700');

HITS.addRect(s.x-w/2,s.y-h/2,w,h,{type:'dqTile',q:t.i});

obstacle(s.x-w/2,s.y-h/2,s.x+w/2,s.y+h/2);

}

var sp=SS(7,0.88,0.5,16),wp=58,hp=36;

drawFold(sp.x-wp/2,sp.y-hp/2,wp,hp,9,PINK,0.12);

txtS('summary.json',sp.x,sp.y-2,prim,'center',7.5,'600');

txtS('+ dashboard',sp.x,sp.y+9,tert,'center',7.5);

HITS.addRect(sp.x-wp/2,sp.y-hp/2,wp,hp,{type:'dqSummary'});

addObstacleRect(sp.x-wp/2,sp.y-hp/2,wp,hp);

if(STATE.labels){

var pq1=SS(7,0.5,0.12,4),pq2=SS(7,0.5,0.95,0);

qLabel({key:'dq_gate',def:'quality gate: training (L9) starts only with a green dashboard — FAIL blocks',grp:'Quality validation',

x:pq1.x,y:pq1.y,col:tert,al:'center',sz:8.5,pr:1});

qLabel({key:'dq_scope',def:'validation of the whole flow: zip → DuckDB → parquet → split → Output B',grp:'Quality validation',

x:pq2.x,y:pq2.y,col:tert,al:'center',sz:8.5,pr:1});

}

};



function TrainingLayer(){}

TrainingLayer.prototype.draw=function(){

caption(8);

var prim=vget('--color-text-primary','#eee'),tert=vget('--color-text-tertiary','#777');

GLYPHS.trialFunnel(8,0.32,0.5,PINK);



var top=prism(8,0.20,0.38,0.44,0.64,2,26,GREEN,0.25),tc=ctr(top);

if(CAM.z>=0.75)GLYPHS.modelTree(tc.x,tc.y+2,GREEN);

HITS.addPts([lp(8,0.18,0.36,32),lp(8,0.46,0.66,0)],{type:'xgb'});

if(STATE.labels){

var px1=SS(8,0.32,0.5,32),px2=SS(8,0.32,0.74,0),pxa=SS(8,0.32,0.5,28);

qLabel({key:'xgb_title',def:'XGB',grp:'Training / Optuna',

x:px1.x,y:px1.y-2,col:prim,al:'center',sz:11,wt:'700',pr:3,ax:pxa.x,ay:pxa.y});

qLabel({key:'xgb_sub',def:'binary:logistic · meta-label',grp:'Training / Optuna',

x:px2.x,y:px2.y,col:tert,al:'center',sz:8,pr:1});

}

line2(lp(8,0.50,0.5,18),lp(8,0.72,0.5,18),tert,1.4,[]);

var ah=CAM.S(lp(8,0.72,0.5,18));

[ctx.save](http://ctx.save)();ctx.translate(ah.x,ah.y);ctx.rotate(Math.PI/2);triUpS(0,0,tert);ctx.restore();



var sp=SS(8,0.82,0.5,20),wp=92,hp=42;

if(flash>0)strokeRR(sp.x-wp/2-3,sp.y-hp/2-3,wp+6,hp+6,13,rgba(AMB,flash*0.8),2);

GLYPHS.pyFile(sp.x,sp.y,wp,hp,AMB,'strategy_'+(aname(STATE.asset)||ASSETS[STATE.asset])+'.py');

HITS.addRect(sp.x-wp/2,sp.y-hp/2,wp,hp,{type:'strategy',a:STATE.asset});

addObstacleRect(sp.x-wp/2,sp.y-hp/2,wp,hp);

GLYPHS.stackBadge(8,0.94,0.5,20,AMB,'×503','strategy');

if(STATE.labels){

var po1=SS(8,0.5,0.10,2),po2=SS(8,0.5,0.97,0);

qLabel({key:'opt_caption',def:'Optuna: 200 trials (TPE + MedianPruner) · purged walk-forward CV only on Train',grp:'Training / Optuna',

x:po1.x,y:po1.y,col:tert,al:'center',sz:8.5,pr:1});

qLabel({key:'champ_caption',def:'champion → strategy .py = base64 model + feature manifest + threshold 0.60 + selfcheck',grp:'Training / Optuna',

x:po2.x,y:po2.y,col:tert,al:'center',sz:8.5,pr:1});

}

};



function OOSWall(){}

OOSWall.prototype.draw=function(){

caption(9);

var C=26,R=METRICS.length,HZ=170,bw=0.60;

var A=CAM.S(lp(9,0.06,bw,6)),B=CAM.S(lp(9,0.94,bw,6)),

T1=CAM.S(lp(9,0.06,bw,6+HZ)),T2=CAM.S(lp(9,0.94,bw,6+HZ));

function PT(u,v){return lerp2(lerp2(T1,T2,u),lerp2(A,B,u),v);}

polyS([T1,T2,B,A],rgba(CAN,0.08),vget('--color-border-secondary','#555'),1,[]);

if(CAM.z>=1.0){

for(c=0;c<7;c++){

var ms=PT((c+0.45)/C,-0.105);

drawMicroSheet(ms.x-7,ms.y-9,14,18,AMB);

}

}

// wall obstacle in 6 strips (the AABB of the whole tilted quad would cover

// the empty triangle above the wall and push name labels away)

for(r=0;r<6;r++){

var su0=r/6,su1=(r+1)/6,

q00=PT(su0,0),q10=PT(su1,0),q01=PT(su0,1),q11=PT(su1,1);

obstacle(Math.min(q00.x,q10.x,q01.x,q11.x),Math.min(q00.y,q10.y,q01.y,q11.y),

Math.max(q00.x,q10.x,q01.x,q11.x),Math.max(q00.y,q10.y,q01.y,q11.y));

}

var r,c,omc=[];

for(c=0;c<C;c++)omc[c]=oosMock(c); // oosMock depends only on c → compute once per column (not 5×)

for(r=0;r<R;r++)for(c=0;c<C;c++){

var u0=c/C,u1=(c+0.82)/C,v0=r/R,v1=(r+0.78)/R;

var p00=PT(u0,v0),p10=PT(u1,v0),p11=PT(u1,v1),p01=PT(u0,v1);

var val=omc[c][METRICS[r].id],q=metricQ(val,r);

var colq=q>=0.5?rgba(TP,0.10+0.80*(q-0.5)*2):rgba(SL,0.10+0.72*(0.5-q)*2);

polyS([p00,p10,p11,p01],colq,null);

var bx0=Math.min(p00.x,p01.x,p10.x,p11.x),bx1=Math.max(p00.x,p01.x,p10.x,p11.x);

var by0=Math.min(p00.y,p01.y,p10.y,p11.y),by1=Math.max(p00.y,p01.y,p10.y,p11.y);

HITS.addRect(bx0,by0,bx1-bx0,by1-by0,{type:'oosCell',a:c,m:r});

}

var mi=0;for(r=0;r<R;r++)if(METRICS[r].id===STATE.metric)mi=r;

polyS([PT(-0.008,mi/R-0.01),PT(1.008,mi/R-0.01),PT(1.008,(mi+0.85)/R+0.01),PT(-0.008,(mi+0.85)/R+0.01)],null,TEAL,1.6,[5,3]);

if(STATE.labels){

var pc=PT(0.5,-0.07);

qLabel({key:'oos_caption',def:'OOS results matrix · 503 assets × 5 metrics · 2024-01-02 → 2026-05-29',grp:'OOS results',

x:pc.x,y:pc.y,col:vget('--color-text-primary','#eee'),al:'center',sz:10.5,wt:'600',pr:3});

for(r=0;r<R;r++){var pl=PT(-0.045,(r+0.55)/R);

qLabel({text:METRICS[r].name,x:pl.x,y:pl.y,col:r===mi?TEAL:vget('--color-text-secondary','#999'),

al:'right',sz:8.5,wt:r===mi?'600':'',pr:3,ax:pl.x+6,ay:pl.y});}

var pb=PT(0.5,1.12);

qLabel({key:'oos_note',def:'columns = assets (26 of 503 in frame) · rows = metrics · color = result quality',grp:'OOS results',

x:pb.x,y:pb.y,col:vget('--color-text-tertiary','#777'),al:'center',sz:8.5,pr:1});

if(STATE.names==='sample'){

for(c=0;c<7;c++){var ph=PT((c+0.45)/C,-0.155),pg=PT((c+0.45)/C,0.02);

qLabel({key:'asset'+c,text:anameV(c),x:ph.x,y:ph.y,col:vget('--color-text-tertiary','#777'),

al:'left',sz:7.5,rot:-0.7,pr:3,lod:0.65,ax:pg.x,ay:pg.y});}

}

}

};



function pillCore(px,py,w,h,col,label,fillA,lw,fz,dy){ // shared core of pill/pillF (single source, no divergence)

var s=CAM.S({x:px,y:py});

fillRR(s.x-w/2,s.y-h/2,w,h,8,rgba(col,fillA==null?0.12:fillA),col,lw);

txtS(label,s.x,s.y+dy,vget('--color-text-primary','#eee'),'center',fz,'600');

return s;}

function pill(px,py,w,h,col,label,fillA){return pillCore(px,py,w,h,col,label,fillA,1.2,10,3.5);}

function pillF(px,py,w,h,col,label,fillA,fz){return pillCore(px,py,w,h,col,label,fillA,1.1,fz||9,3);}

function edge(x1,y1,x2,y2){line2({x:x1,y:y1},{x:x2,y:y2},vget('--color-border-secondary','#555'),1,[]);}

function monoS(s,x,y,col,al,sz){

var fz=(sz||9)*zScale();

setFont(fz.toFixed(1)+'px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace');

ctx.textAlign=al||'left';ctx.textBaseline='alphabetic';

ctx.fillStyle=col;ctx.fillText(s,x,y);}



/* === GLYPH PASS ===

Immediate-mode renderers for 3D objects. Each glyph registers its own hit-area,

an obstacle for the declutter, and leaves the canvas without dashes. */

var GLYPHS={};

function scr(p){return CAM.S(p);} // bound wrapper for .map(scr); do NOT replace with .map(CAM.S) — CAM.S uses this

function addObstacleRect(x,y,w,h){obstacle(x,y,x+w,y+h);}

function addObstaclePts(pts,pad){

var x0=1e9,y0=1e9,x1=-1e9,y1=-1e9,i,p;

pad=pad||0;

for(i=0;i<pts.length;i++){p=pts[i];if(p.x<x0)x0=p.x;if(p.y<y0)y0=p.y;if(p.x>x1)x1=p.x;if(p.y>y1)y1=p.y;}

obstacle(x0-pad,y0-pad,x1+pad,y1+pad);

}

function ctr(pts){var x=0,y=0,i;for(i=0;i<pts.length;i++){x+=pts[i].x;y+=pts[i].y;}return {x:x/pts.length,y:y/pts.length};}

function pathPtsS(pts,close){

ctx.beginPath();

for(var i=0;i<pts.length;i++){if(i)ctx.lineTo(pts[i].x,pts[i].y);else ctx.moveTo(pts[i].x,pts[i].y);}

if(close)ctx.closePath();

}

function ringPts(lev,ca,cb,ra,rb,dz,n){

var pts=[],i,ang;

for(i=0;i<n;i++){ang=Math.PI*2*i/n;pts.push(lp(lev,ca+ra*Math.cos(ang),cb+rb*Math.sin(ang),dz));}

return pts;

}

function ringScr(lev,ca,cb,ra,rb,dz,n){return ringPts(lev,ca,cb,ra,rb,dz,n).map(scr);}

function foldedSheetPath(x,y,w,h,f){

f=f||8;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+w-f,y);ctx.lineTo(x+w,y+f);

ctx.lineTo(x+w,y+h);ctx.lineTo(x,y+h);ctx.closePath();

}

function drawFold(x,y,w,h,f,col,fillA){

foldedSheetPath(x,y,w,h,f);

ctx.fillStyle=rgba(col,fillA==null?0.13:fillA);ctx.fill();

[ctx.save](http://ctx.save)();ctx.strokeStyle=col;ctx.lineWidth=1.2;ctx.setLineDash([]);foldedSheetPath(x,y,w,h,f);ctx.stroke();

ctx.beginPath();ctx.moveTo(x+w-f,y);ctx.lineTo(x+w-f,y+f);ctx.lineTo(x+w,y+f);ctx.stroke();ctx.restore();

}

function tagPathS(x,y,w,h){

var cut=Math.min(10,w*0.18);

ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+w-cut,y);ctx.lineTo(x+w,y+h/2);

ctx.lineTo(x+w-cut,y+h);ctx.lineTo(x,y+h);ctx.closePath();

}

function drawTagS(x,y,w,h,col,label,fillA,fz){

ctx.fillStyle=rgba(col,fillA==null?0.12:fillA);tagPathS(x,y,w,h);ctx.fill();

[ctx.save](http://ctx.save)();ctx.strokeStyle=col;ctx.lineWidth=1.2;ctx.setLineDash([]);tagPathS(x,y,w,h);ctx.stroke();

ctx.beginPath();ctx.arc(x+w-9,y+h/2,2.2,0,7);ctx.stroke();ctx.restore();

if(label)txtS(label,x+w/2-4,y+h/2+(fz||8)*0.35,vget('--color-text-primary','#eee'),'center',fz||8,'600');

addObstacleRect(x,y,w,h);

}

function zigzagS(x0,y0,x1,y1,teeth,amp,col){

var dx=x1-x0,dy=y1-y0,len=Math.max(1,Math.sqrt(dx*dx+dy*dy)),nx=-dy/len,ny=dx/len,i,t,x,y;

[ctx.save](http://ctx.save)();ctx.strokeStyle=col;ctx.lineWidth=1.1;ctx.setLineDash([]);ctx.beginPath();

for(i=0;i<=teeth;i++){t=i/teeth;x=x0+dx*t+nx*amp*(i%2?-1:1);y=y0+dy*t+ny*amp*(i%2?-1:1);

if(i)ctx.lineTo(x,y);else ctx.moveTo(x,y);}

ctx.stroke();ctx.restore();

}

function drawLockS(x,y,s,col,label){

[ctx.save](http://ctx.save)();ctx.strokeStyle=col;ctx.fillStyle=rgba(col,0.18);ctx.lineWidth=1.05;ctx.setLineDash([]);

ctx.beginPath();ctx.arc(x,y-s*0.16,s*0.30,Math.PI,0);ctx.stroke();

rrectS(x-s*0.34,y-s*0.12,s*0.68,s*0.52,2.5);ctx.fill();ctx.stroke();

ctx.strokeStyle=TP;ctx.beginPath();ctx.moveTo(x-s*0.17,y+s*0.12);ctx.lineTo(x-s*0.04,y+s*0.25);ctx.lineTo(x+s*0.20,y);ctx.stroke();

ctx.restore();

if(label&&CAM.z>=LOD.micro)txtS(label,x,y+s*0.73,col,'center',7.5,'700');

}

function drawStatusIcon(x,y,col,status){

[ctx.save](http://ctx.save)();ctx.strokeStyle=col;ctx.lineWidth=1.4;ctx.lineCap='round';ctx.setLineDash([]);

ctx.beginPath();

if(status==='OK'){ctx.moveTo(x-4,y);ctx.lineTo(x-1,y+3);ctx.lineTo(x+5,y-4);}

else if(status==='WARN'){ctx.moveTo(x,y-5);ctx.lineTo(x,y+2);ctx.moveTo(x,y+5);ctx.lineTo(x,y+5.2);}

else{ctx.moveTo(x-4,y-4);ctx.lineTo(x+4,y+4);ctx.moveTo(x+4,y-4);ctx.lineTo(x-4,y+4);}

ctx.stroke();ctx.restore();

}

function drawFamilyMarker(x,y,fam,col){

[ctx.save](http://ctx.save)();ctx.strokeStyle=col;ctx.fillStyle=rgba(col,0.18);ctx.lineWidth=1.15;ctx.setLineDash([]);

if(fam==='price_action'){

ctx.beginPath();ctx.moveTo(x-3,y+4);ctx.lineTo(x-3,y-4);ctx.moveTo(x+3,y+5);ctx.lineTo(x+3,y-5);ctx.stroke();

ctx.fillRect(x-5,y-1,4,5);ctx.fillRect(x+1,y-4,4,6);

}else if(fam==='volume'){

ctx.fillRect(x-5,y+1,3,5);ctx.fillRect(x-1,y-3,3,9);ctx.fillRect(x+3,y-6,3,12);

}else{

ctx.beginPath();ctx.moveTo(x-6,y+4);ctx.lineTo(x-1,y-2);ctx.lineTo(x+2,y+0);ctx.lineTo(x+6,y-6);ctx.stroke();

}

ctx.restore();

}

function drawMicroSheet(x,y,w,h,col){

drawFold(x,y,w,h,Math.min(6,w*0.26),col,0.10);

[ctx.save](http://ctx.save)();ctx.strokeStyle=rgba(col,0.7);ctx.lineWidth=1;ctx.setLineDash([]);

ctx.beginPath();ctx.moveTo(x+4,y+h*0.45);ctx.lineTo(x+w-5,y+h*0.45);

ctx.moveTo(x+4,y+h*0.66);ctx.lineTo(x+w-7,y+h*0.66);ctx.stroke();ctx.restore();

}

function drawCloudSource(x,y,w,h,col,label){

[ctx.save](http://ctx.save)();ctx.fillStyle=rgba(col,0.13);ctx.strokeStyle=col;ctx.lineWidth=1.4;ctx.setLineDash([]);

ctx.beginPath();

ctx.moveTo(x-w*0.39,y+h*0.17);

ctx.quadraticCurveTo(x-w*0.47,y-h*0.08,x-w*0.25,y-h*0.10);

ctx.quadraticCurveTo(x-w*0.18,y-h*0.37,x+w*0.05,y-h*0.24);

ctx.quadraticCurveTo(x+w*0.20,y-h*0.43,x+w*0.36,y-h*0.18);

ctx.quadraticCurveTo(x+w*0.52,y-h*0.14,x+w*0.43,y+h*0.14);

ctx.quadraticCurveTo(x+w*0.17,y+h*0.32,x-w*0.39,y+h*0.17);

ctx.closePath();ctx.fill();ctx.stroke();

ctx.beginPath();ctx.moveTo(x-w*0.06,y-h*0.27);ctx.lineTo(x-w*0.06,y-h*0.53);

ctx.moveTo(x-w*0.12,y-h*0.47);ctx.lineTo(x-w*0.06,y-h*0.56);ctx.lineTo(x,y-h*0.47);

ctx.stroke();

ctx.beginPath();ctx.arc(x+w*0.28,y-h*0.28,7,4.0,5.65);ctx.stroke();

ctx.beginPath();ctx.arc(x+w*0.28,y-h*0.28,12,3.95,5.7);ctx.stroke();

ctx.restore();

txtS(label,x,y+3,vget('--color-text-primary','#eee'),'center',8.5,'700');

addObstacleRect(x-w*0.48,y-h*0.58,w*1.0,h*0.96);

}

function drawZipCrate(g){

var top=prism(g.lev,g.a-0.025,g.b-0.055,g.a+0.025,g.b+0.055,1,g.h||24,g.sel?GREEN:CAN,g.sel?0.32:0.24);

var c=ctr(top),pad=4;

txtS('.zip',c.x,c.y+3,vget('--color-text-primary','#eee'),'center',7.5,'700');

if(CAM.z>=0.8)zigzagS(c.x-7,c.y-12,c.x+7,c.y+12,7,1.7,g.sel?GREEN:CAN);

HITS.addPts([lp(g.lev,g.a-0.033,g.b-0.07,(g.h||24)+4),lp(g.lev,g.a+0.033,g.b+0.07,0)],{type:'zip',a:g.i});

addObstaclePts(top,pad);

return c;

}

function drawStackBadge(lev,a,b,dz,col,label,type){

var p=SS(lev,a,b,dz),i,payload={type:type};

if(type==='strategy')payload.a=STATE.asset;

[ctx.save](http://ctx.save)();ctx.strokeStyle=rgba(col,0.7);ctx.lineWidth=1;ctx.setLineDash([]);

for(i=2;i>=0;i--)rrectS(p.x-16+i*5,p.y-19+i*4,27,36,8);

ctx.stroke();ctx.restore();

txtS(label,p.x+3,p.y+5,vget('--color-text-secondary','#999'),'center',8.5,'700');

HITS.addRect(p.x-18,p.y-20,38,42,payload);

addObstacleRect(p.x-18,p.y-20,38,42);

}

function drawDbCylinder(g){

var top=ringScr(g.lev,g.a,g.b,g.ra,g.rb,[g.dz](http://g.dz)+g.h,28),bot=ringScr(g.lev,g.a,g.b,g.ra,g.rb,[g.dz](http://g.dz),28),i,body=[];

for(i=0;i<bot.length;i++)body.push(bot[i]);for(i=top.length-1;i>=0;i--)body.push(top[i]);

[ctx.save](http://ctx.save)();pathPtsS(body,true);ctx.fillStyle=rgba(g.col,0.18);ctx.fill();ctx.strokeStyle=rgba(g.col,0.55);ctx.lineWidth=1;ctx.stroke();

pathPtsS(bot,true);ctx.strokeStyle=rgba(g.col,0.35);ctx.stroke();

pathPtsS(top,true);ctx.fillStyle=rgba(g.col,0.18);ctx.fill();ctx.strokeStyle=g.col;ctx.lineWidth=1.3;ctx.stroke();

if(CAM.z>=0.7){for(i=1;i<=2;i++){var mid=ringScr(g.lev,g.a,g.b,g.ra,g.rb,[g.dz](http://g.dz)+g.h*i/3,28);pathPtsS(mid,true);ctx.strokeStyle=rgba(g.col,0.35);ctx.stroke();}}

ctx.restore();

var c=ctr(top);

if(CAM.z>=0.9){

txtS(T('db_badge','DuckDB','Store / DuckDB')||'',c.x,c.y-14,g.col,'center',7.5,'700');

}

HITS.addPts([lp(g.lev,g.a-g.ra*1.15,g.b-g.rb*1.15,[g.dz](http://g.dz)+g.h+4),lp(g.lev,g.a+g.ra*1.15,g.b+g.rb*1.15,[g.dz](http://g.dz))],{type:'db'});

addObstaclePts(top.concat(bot),4);

return c;

}

function drawSqlView(g){

var p=[lp(g.lev,g.a0,g.b0,[g.dz](http://g.dz)),lp(g.lev,g.a1,g.b0,[g.dz](http://g.dz)),lp(g.lev,g.a1,g.b1,[g.dz](http://g.dz)),lp(g.lev,g.a0,g.b1,[g.dz](http://g.dz))];

var s=poly(p,rgba(g.col,0.08),rgba(g.col,0.75),1,[5,4]);

[ctx.save](http://ctx.save)();ctx.strokeStyle=rgba(g.col,0.45);ctx.lineWidth=1;ctx.setLineDash([3,4]);

var c=ctr(s),d=SS(g.lev,g.linkA,g.linkB,g.linkDz);

ctx.beginPath();ctx.moveTo(s[0].x,s[0].y);ctx.lineTo(d.x,d.y);ctx.moveTo(s[1].x,s[1].y);ctx.lineTo(d.x,d.y);

ctx.moveTo(s[2].x,s[2].y);ctx.lineTo(d.x,d.y);ctx.moveTo(s[3].x,s[3].y);ctx.lineTo(d.x,d.y);ctx.stroke();ctx.restore();

[ctx.save](http://ctx.save)();ctx.strokeStyle=rgba(vget('--color-text-primary','#eee'),0.45);ctx.beginPath();ctx.moveTo(c.x-12,c.y-8);ctx.lineTo(c.x+8,c.y-14);ctx.stroke();ctx.restore();

HITS.addPts([lp(g.lev,g.a0-0.02,g.b0-0.02,[g.dz](http://g.dz)+4),lp(g.lev,g.a1+0.02,g.b1+0.02,[g.dz](http://g.dz)-4)],{type:'view'});

addObstaclePts(s,4);

return c;

}

function drawSnapshotCam(x,y,col,label){

var prim=vget('--color-text-primary','#eee');

fillRR(x-23,y-13,46,26,6,rgba(col,0.12),col,1.3);

[ctx.save](http://ctx.save)();ctx.strokeStyle=col;ctx.lineWidth=1.3;ctx.setLineDash([]);

rrectS(x-13,y-19,20,7,3);ctx.stroke();ctx.beginPath();ctx.arc(x+2,y,8,0,7);ctx.stroke();ctx.arc(x+2,y,4,0,7);ctx.stroke();ctx.restore();

drawMicroSheet(x+22,y-10,18,24,col);

txtS(label,x,y+3,prim,'center',7.5,'700');

addObstacleRect(x-25,y-21,67,38);

}

function drawParquetFile(x,y,col,stack){

var i,prim=vget('--color-text-primary','#eee');

if(stack){[ctx.save](http://ctx.save)();ctx.strokeStyle=rgba(col,0.55);ctx.lineWidth=1;ctx.setLineDash([]);

for(i=2;i>0;i--){foldedSheetPath(x-18+i*5,y-24-i*4,36,44,8);ctx.stroke();}ctx.restore();}

drawFold(x-18,y-24,36,44,8,col,0.13);

if(CAM.z>=0.8){[ctx.save](http://ctx.save)();ctx.fillStyle=rgba(col,0.35);

for(i=0;i<4;i++)ctx.fillRect(x-12+i*6,y-14,3,25);ctx.restore();}

txtS('parquet',x,y+5,prim,'center',7,'700');

addObstacleRect(x-20,y-29,stack?54:40,51);

}

function drawLabelTag(x,y,w,h,col,label){

drawTagS(x-w/2,y-h/2,w,h,col,label,0.12,8);

}

function drawPyFile(x,y,w,h,col,label){

var prim=vget('--color-text-primary','#eee'),i;

drawFold(x-w/2,y-h/2,w,h,10,col,0.14);

for(i=0;i<4;i++){[ctx.save](http://ctx.save)();ctx.strokeStyle=rgba(col,0.55);ctx.lineWidth=1;ctx.beginPath();

ctx.moveTo(x-w/2+9,y-h/2+17+i*8);ctx.lineTo(x+w/2-10-i*5,y-h/2+17+i*8);ctx.stroke();ctx.restore();}

txtS(label,x,y+1,prim,'center',7,'700');

txtS('.b64',x,y+14,col,'center',8,'700');

}

function drawModelTree(x,y,col){

// clean tree glyph — the "XGB" label goes through the label queue (xgb_title),

// so it's editable and decluttered; zero text here (no duplicate)

var pts=[[0,-17],[-16,0],[0,0],[16,0],[-24,16],[-8,16],[8,16],[24,16]],i;

[ctx.save](http://ctx.save)();ctx.strokeStyle=rgba(col,0.8);ctx.fillStyle=rgba(col,0.20);ctx.lineWidth=1;ctx.setLineDash([]);

for(i=1;i<4;i++){ctx.beginPath();ctx.moveTo(x+pts[0][0],y+pts[0][1]);ctx.lineTo(x+pts[i][0],y+pts[i][1]);ctx.stroke();}

for(i=4;i<8;i++){ctx.beginPath();ctx.moveTo(x+pts[2+(i>5?1:0)][0],y+pts[2+(i>5?1:0)][1]);ctx.lineTo(x+pts[i][0],y+pts[i][1]);ctx.stroke();}

for(i=0;i<pts.length;i++){ctx.beginPath();ctx.arc(x+pts[i][0],y+pts[i][1],3.2,0,7);ctx.fill();ctx.stroke();}

ctx.restore();

}

function drawTrialFunnel(lev,a,b,col){

var rings=[[0.33,0.86,30,'opt_funnel1','200 trials'],[0.23,0.58,24,'opt_funnel2','pruning'],[0.13,0.33,18,'opt_funnel3','champion']],i,rs,c;

for(i=0;i<rings.length;i++){

rs=ringScr(lev,a,b,rings[i][0],rings[i][1],rings[i][2],36);

[ctx.save](http://ctx.save)();pathPtsS(rs,true);ctx.strokeStyle=rgba(col,0.50+i*0.12);ctx.lineWidth=1.2;ctx.setLineDash(i===0?[5,4]:[]);ctx.stroke();ctx.restore();

if(STATE.labels&&CAM.z>=0.85){c=ctr(rs);qLabel({key:rings[i][3],def:rings[i][4],grp:'Training / Optuna',

x:c.x,y:c.y-12-i*2,col:rgba(col,0.85),al:'center',sz:7.5,pr:1,lod:0.9});}

}

var sT=CAM.S(lp(lev,a,b-0.86,30));drawTagS(sT.x-18,sT.y-7,36,14,col,'TPE',0.16,7.5);

var pp=CAM.S(lp(lev,a+0.33*Math.cos(CLK*1.3),b+0.86*Math.sin(CLK*1.3),30));

ctx.fillStyle=col;ctx.beginPath();ctx.arc(pp.x,pp.y,3,0,7);ctx.fill();

HITS.addPts([lp(lev,a-0.36,b-0.90,34),lp(lev,a+0.36,b+0.90,14)],{type:'optuna'});

addObstacleRect(sT.x-18,sT.y-7,36,14);

}

// Glyph registry. World-space (args lev,a,b or g={lev,a,b,...}): zipCrate, stackBadge,

// dbCylinder, sqlView, trialFunnel. Screen-space (args x,y w px): cloud, snapshotCam,

// parquetFile, labelTag, pyFile, modelTree.

[GLYPHS.cloud](http://GLYPHS.cloud)=drawCloudSource;

GLYPHS.zipCrate=drawZipCrate;

GLYPHS.stackBadge=drawStackBadge;

GLYPHS.dbCylinder=drawDbCylinder;

GLYPHS.sqlView=drawSqlView;

GLYPHS.snapshotCam=drawSnapshotCam;

GLYPHS.parquetFile=drawParquetFile;

GLYPHS.labelTag=drawLabelTag;

GLYPHS.pyFile=drawPyFile;

GLYPHS.modelTree=drawModelTree;

GLYPHS.trialFunnel=drawTrialFunnel;



/* === LABEL PASS ===

Deferred object labels: layers enqueue via qLabel(), drawn by

drawLabels() at the very end of the frame. q={key,def,grp,x,y,col,al,sz,wt,

rot,pr,lod,ax,ay}: (x,y) preferred screen position, (ax,ay) anchor for the

leader-line, pr=3 never disappears, lod = min CAM.z. */

var LQ=[],OBST=[];

function obstacle(x0,y0,x1,y1){OBST.push({x0:x0,y0:y0,x1:x1,y1:y1});}

function qLabel(q){

if(q.text==null){

var s=tVal(q.key,q.def,q.grp);

if(!s)return;

q.text=s;

}

if(!q.text)return;

LQ.push(q);

}

function lblBoxes(q,dx,dy){

// rotated labels: 3 segments along the text instead of one thick AABB

var x=q.x+dx,y=q.y+dy,out=[],i,k;

var x0=([q.al](http://q.al)==='center')?-q.w/2:(([q.al](http://q.al)==='right')?-q.w:0),x1=x0+q.w,y0=-q.fz-2,y1=3;

if(q.rot){

var c=Math.cos(q.rot),s=Math.sin(q.rot),n=3;

for(k=0;k<n;k++){

var sx0=x0+(x1-x0)*k/n,sx1=x0+(x1-x0)*(k+1)/n,

P=[[sx0,y0],[sx1,y0],[sx1,y1],[sx0,y1]],bx0=1e9,by0=1e9,bx1=-1e9,by1=-1e9;

for(i=0;i<4;i++){var X=P[i][0]*c-P[i][1]*s,Y=P[i][0]*s+P[i][1]*c;

if(X<bx0)bx0=X;if(Y<by0)by0=Y;if(X>bx1)bx1=X;if(Y>by1)by1=Y;}

out.push({x0:x+bx0,y0:y+by0,x1:x+bx1,y1:y+by1});

}

}else out.push({x0:x+x0,y0:y+y0,x1:x+x1,y1:y+y1});

return out;

}

function boxUnion(bs){

var u={x0:1e9,y0:1e9,x1:-1e9,y1:-1e9},i;

for(i=0;i<bs.length;i++){var b=bs[i];

if(b.x0<u.x0)u.x0=b.x0;if(b.y0<u.y0)u.y0=b.y0;if(b.x1>u.x1)u.x1=b.x1;if(b.y1>u.y1)u.y1=b.y1;}

return u;

}

function ovl(a,b,m){return a.x0-m<b.x1&&a.x1+m>b.x0&&a.y0-m<b.y1&&a.y1+m>b.y0;}

function ovlArea(a,b){

var w=Math.min(a.x1,b.x1)-Math.max(a.x0,b.x0),h=Math.min(a.y1,b.y1)-Math.max(a.y0,b.y0);

return (w>0&&h>0)?w*h:0;}

function drawLabels(){

var placed=[],ord=[],i,j,k,q;

var auditP=LBL_AUDIT?[]:null,auditD=LBL_AUDIT?[]:null;

for(i=0;i<LQ.length;i++){q=LQ[i];

if(q.lod!=null&&CAM.z<q.lod)continue;

q.fz=([q.sz](http://q.sz)||11)*zScale();

setFont(uiFont(q.wt,q.fz));

q.w=Math.max(6,ctx.measureText(q.text).width);

[q.pr](http://q.pr)=[q.pr](http://q.pr)||1;

ord.push(q);

}

ord.sort(function(p,r){return ([r.pr-p.pr](http://r.pr-p.pr))||(p.y-r.y);});

for(i=0;i<ord.length;i++){q=ord[i];

var dyS=q.fz+7,dxS=q.w/2+8,CAND,best=null,bestA=1e18,chosen=null;

if(q.rot){

// rotated: offsets along the text's own axis (u) and perpendicular (v)

// — labels step along their diagonal instead of scattering across the screen

var uc=Math.cos(q.rot),us=Math.sin(q.rot);

CAND=[[0,0],

[-uc*dyS,-us*dyS],[uc*dyS,us*dyS],

[-uc*2*dyS,-us*2*dyS],[uc*2*dyS,us*2*dyS],

[us*dyS,-uc*dyS],[-us*dyS,uc*dyS],

[-uc*3*dyS,-us*3*dyS],[uc*3*dyS,us*3*dyS]];

}else{

CAND=[[0,0],[0,-dyS],[0,dyS],[0,-2*dyS],[0,2*dyS],[dxS,0],[-dxS,0],

[dxS,-dyS],[-dxS,-dyS],[dxS,dyS],[-dxS,dyS],[0,-3*dyS],[0,3*dyS]];

}

for(k=0;k<CAND.length;k++){

var bs=lblBoxes(q,CAND[k][0],CAND[k][1]),u=boxUnion(bs),a=0,m,n;

// clamp to the frame (protects the PNG export edges)

var sx=0,sy=0;

if(u.x0<4)sx=4-u.x0;else if(u.x1>cw-4)sx=cw-4-u.x1;

if(u.y0<12)sy=12-u.y0;else if(u.y1>chh-4)sy=chh-4-u.y1;

if(sx||sy)for(m=0;m<bs.length;m++){var bb=bs[m];bb.x0+=sx;bb.y0+=sy;bb.x1+=sx;bb.y1+=sy;}

for(m=0;m<bs.length&&a<1e17;m++){

for(j=0;j<placed.length;j++){var P2=placed[j];

for(n=0;n<P2.length;n++)if(ovl(bs[m],P2[n],2))a+=ovlArea(bs[m],P2[n])+40;}

for(j=0;j<OBST.length;j++)if(ovl(bs[m],OBST[j],2))a+=ovlArea(bs[m],OBST[j])+40;

}

if(a===0){chosen={bs:bs,dx:CAND[k][0]+sx,dy:CAND[k][1]+sy};break;}

if(a<bestA){bestA=a;best={bs:bs,dx:CAND[k][0]+sx,dy:CAND[k][1]+sy};}

}

if(!chosen){

if([q.pr](http://q.pr)<=2){if(auditD)auditD.push({key:q.key,pr:[q.pr](http://q.pr)});continue;} // drop — pr3 never disappears

chosen=best;

}

var fx=q.x+chosen.dx,fy=q.y+chosen.dy;

placed.push([chosen.bs](http://chosen.bs));

var ub=boxUnion([chosen.bs](http://chosen.bs));

if(auditP)auditP.push({key:q.key||'?',pr:[q.pr](http://q.pr),x0:Math.round(ub.x0),y0:Math.round(ub.y0),x1:Math.round(ub.x1),y1:Math.round(ub.y1)});

if([q.ax](http://q.ax)!=null&&Math.abs(chosen.dx)+Math.abs(chosen.dy)>12){

var axx=[q.ax](http://q.ax),ayy=(q.ay!=null)?q.ay:q.y,

tx=clamp(axx,ub.x0,ub.x1),ty=clamp(ayy,ub.y0,ub.y1);

[ctx.save](http://ctx.save)();ctx.strokeStyle=rgba(vget('--color-text-tertiary','#777'),0.8);ctx.lineWidth=1;ctx.setLineDash([]);

ctx.beginPath();ctx.moveTo(axx,ayy);ctx.lineTo(tx,ty);ctx.stroke();ctx.restore();

}

if(HL.key===q.key)HL.pending=true;

if(q.rot){[ctx.save](http://ctx.save)();ctx.translate(fx,fy);ctx.rotate(q.rot);

txtS(q.text,0,0,q.col,[q.al](http://q.al),[q.sz](http://q.sz),q.wt);ctx.restore();CUR_FONT='';}

else txtS(q.text,fx,fy,q.col,[q.al](http://q.al),[q.sz](http://q.sz),q.wt);

if(LBL_DEBUG){[ctx.save](http://ctx.save)();ctx.strokeStyle='rgba(0,200,255,0.7)';ctx.lineWidth=1;ctx.setLineDash([]);

for(k=0;k<[chosen.bs](http://chosen.bs).length;k++){var db=[chosen.bs](http://chosen.bs)[k];

ctx.strokeRect(db.x0,db.y0,db.x1-db.x0,db.y1-db.y0);}

ctx.restore();}

}

if(LBL_DEBUG){[ctx.save](http://ctx.save)();ctx.strokeStyle='rgba(255,0,255,0.6)';ctx.lineWidth=1;ctx.setLineDash([2,3]);

for(i=0;i<OBST.length;i++){var o=OBST[i];ctx.strokeRect(o.x0,o.y0,o.x1-o.x0,o.y1-o.y0);}

ctx.setLineDash([]);setFont('700 14px ui-monospace,monospace');ctx.textAlign='left';

ctx.fillStyle='#f0f';ctx.fillText('CAM.z='+CAM.z.toFixed(3),8,chh-10);

ctx.restore();CUR_FONT='';}

if(LBL_AUDIT){ // CI: dump placed boxes + rejected ones to the DOM

var el=document.getElementById('lblaudit');

if(!el){el=document.createElement('pre');[el.id](http://el.id)='lblaudit';[el.style](http://el.style).display='none';document.body.appendChild(el);}

el.textContent=JSON.stringify({mode:STATE.mode,z:+CAM.z.toFixed(3),cw:Math.round(cw),chh:Math.round(chh),placed:auditP,dropped:auditD});

}

}



function DataDAGView(){}

DataDAGView.prototype.draw=function(){

var prim=vget('--color-text-primary','#eee'),sec=vget('--color-text-secondary','#999');

txt('Data flow: from API to parquet per ticker',{x:0,y:-262},prim,'center',14,'700');

edge(0,-222,0,-168);edge(0,-142,0,-68);edge(0,-42,0,32);edge(0,58,0,132);

edge(125,-55,168,-55);edge(-167,-55,-205,-55);

var s;

s=pill(0,-235,250,26,CAN,'Alpaca SIP API · 1h · 503 tickers',0.08);HITS.addRect(s.x-125,s.y-13,250,26,{type:'api'});

s=pill(0,-155,290,26,CAN,'510 × ZIP LEAN · prices ×10000 · 139 MB',0.10);HITS.addRect(s.x-145,s.y-13,290,26,{type:'zip',a:STATE.asset});

s=pill(0,-55,250,26,TEAL,'DuckDB raw_ohlcv_1h · 8 841 820 rows',0.10);HITS.addRect(s.x-125,s.y-13,250,26,{type:'db'});

s=pill(258,-55,176,26,TEAL,'VIEW ohlcv_1h → USD',0.05);HITS.addRect(s.x-88,s.y-13,176,26,{type:'view'});

s=pill(-262,-55,108,26,PINK,'QC-01…QC-11',0.12);HITS.addRect(s.x-54,s.y-13,108,26,{type:'qcAll'});

s=pill(0,45,290,26,CAN,'atomic snapshot + manifest JSON (price_view)',0.08);HITS.addRect(s.x-145,s.y-13,290,26,{type:'snapshot'});

s=pill(0,145,310,28,AMB,'parquet/<TICKER>/ohlcv.parquet · ×503',0.10);HITS.addRect(s.x-155,s.y-14,310,28,{type:'parquet'});

txt('zero duplication: USD exists only in the VIEW · raw stays in BIGINT ×10000',{x:0,y:200},sec,'center',10);

txt('features computed only by the transformer (L7, Layers_Short_SOT/L7_features_x_label_y_[eng.md](http://eng.md)) · snapshot isolates transforms from the live store',{x:0,y:218},sec,'center',10);

};



function SplitTimelineView(){}

SplitTimelineView.prototype.draw=function(){

var prim=vget('--color-text-primary','#eee'),sec=vget('--color-text-secondary','#999'),tert=vget('--color-text-tertiary','#777');

txt('Time split per asset: warm-up → train → OOS (frozen)',{x:0,y:-262},prim,'center',14,'700');

txt('triple barrier labels and rolling windows overlap the boundaries → purge + embargo',{x:0,y:-240},sec,'center',10.5);

var x0=-310,x1=310,yT=-185,yB=-155,acc=x0,i,edges=[];

for(i=0;i<SPLIT.bands.length;i++){

var b=SPLIT.bands[i],xe=acc+(x1-x0)*b.frac;

poly([{x:acc,y:yT},{x:xe,y:yT},{x:xe,y:yB},{x:acc,y:yB}],rgba(b.col,0.22),b.col,1.1);

var sx=CAM.S({x:(acc+xe)/2,y:yT});

txtS([b.name](http://b.name),sx.x,sx.y-18,b.col,'center',10,'600');

var sd=CAM.S({x:(acc+xe)/2,y:yB});

txtS(b.from+' → '+[b.to](http://b.to),sd.x,sd.y+16,tert,'center',8);

var sa=CAM.S({x:acc,y:yT}),sb=CAM.S({x:xe,y:yB});

HITS.addRect(sa.x,sa.y-4,sb.x-sa.x,sb.y-sa.y+8,{type:'split',k:i});

if(i<SPLIT.bands.length-1)edges.push(xe);

acc=xe;

}

var eb=edges[1];

line2({x:eb,y:yB},{x:-250,y:-115},tert,1,[4,3]);line2({x:eb,y:yB},{x:250,y:-115},tert,1,[4,3]);

var bx0=-250,bx1=250,by0=-115,by1=115;

poly([{x:bx0,y:by0},{x:bx1,y:by0},{x:bx1,y:by1},{x:bx0,y:by1}],null,vget('--color-border-secondary','#555'),1,[]);

poly([{x:bx0,y:by0},{x:-80,y:by0},{x:-80,y:by1},{x:bx0,y:by1}],rgba(TEAL,0.14));

poly([{x:-80,y:by0},{x:-10,y:by0},{x:-10,y:by1},{x:-80,y:by1}],rgba(SL,0.20),SL,1,[4,3]);

poly([{x:-10,y:by0},{x:40,y:by0},{x:40,y:by1},{x:-10,y:by1}],rgba(AMB,0.16),AMB,1,[4,3]);

poly([{x:40,y:by0},{x:bx1,y:by0},{x:bx1,y:by1},{x:40,y:by1}],rgba(AMB,0.10));

txt('TRAIN end',{x:-165,y:by0+22},TEAL,'center',9,'600');

txt('purge = 24 candles',{x:-45,y:by0+22},SL,'center',8.5,'600');

txt('windows [t0, t0+H]',{x:-45,y:by0+36},tert,'center',7.5);

txt('embargo ≈ 5 sessions',{x:15,y:by0+58},AMB,'center',8.5,'600');

txt('start OOS →',{x:150,y:by0+22},AMB,'center',9,'600');

var sP=CAM.S({x:-80,y:by0}),sP2=CAM.S({x:-10,y:by1});

HITS.addRect(sP.x,sP.y,sP2.x-sP.x,sP2.y-sP.y,{type:'purge',k:1});

var sE=CAM.S({x:-10,y:by0}),sE2=CAM.S({x:40,y:by1});

HITS.addRect(sE.x,sE.y,sE2.x-sE.x,sE2.y-sE.y,{type:'embargo'});

var sy=72;

line2({x:-220,y:sy},{x:220,y:sy},tert,1,[]);

line2({x:-130,y:sy},{x:-20,y:sy},SL,2.5,[]);

line2({x:-130,y:sy-5},{x:-130,y:sy+5},SL,2,[]);

line2({x:-20,y:sy-5},{x:-20,y:sy+5},SL,2,[]);

var sX=CAM.S({x:-75,y:sy});

[ctx.save](http://ctx.save)();ctx.strokeStyle=rgba(SL,0.9);ctx.lineWidth=2;

ctx.beginPath();ctx.moveTo(sX.x-12,sX.y-10);ctx.lineTo(sX.x+12,sX.y+10);ctx.moveTo(sX.x+12,sX.y-10);ctx.lineTo(sX.x-12,sX.y+10);ctx.stroke();ctx.restore();

txt('setup with a TB window crossing the boundary → row removed (purge)',{x:0,y:sy+28},sec,'center',9);

txt('Optuna and CV only on Train (purged walk-forward) · we touch OOS once, after freezing artifacts',{x:0,y:175},prim,'center',10.5,'600');

};



var SETUP=(function(){

var r=rng(7),n=38,t0=29,H=24,touch=[4,14,24],oppTouch=[9,19];

function LT(i){return 106-0.8*i;}

function LO(i){return LT(i)-6.2;}

var cs=[],prev=LO(0)+3.0,i;

for(i=0;i<n;i++){

var lt=LT(i),lo=LO(i),close,open=prev,high,low;

if(i<t0){

var f=0.30+0.42*r();

close=lo+f*(lt-lo);

high=Math.min(lt-0.4,Math.max(open,close)+0.4+1.2*r());

low=Math.max(lo+0.3,Math.min(open,close)-0.4-1.2*r());

if(touch.indexOf(i)>=0)high=lt;

if(oppTouch.indexOf(i)>=0)low=lo;

}else if(i===t0){

close=lt+1.6;high=close+0.9;low=open-0.8;

}else{

close=prev+1.0+1.0*r();

high=close+0.4+0.9*r();low=Math.min(open,close)-0.3-0.8*r();

}

high=Math.max(high,open,close);low=Math.min(low,open,close);

cs.push({o:open,h:high,l:low,c:close});

prev=close;

}

var R0=cs[t0].c-LO(t0),TPL=cs[t0].c+R0,tpHit=-1;

for(i=t0+1;i<n;i++)if(cs[i].c>=TPL){tpHit=i;break;}

return {cs:cs,n:n,t0:t0,H:H,touch:touch,oppTouch:oppTouch,LT:LT,LO:LO,R0:R0,TPL:TPL,tpHit:tpHit};

})();



function SetupGeometryView(){}

SetupGeometryView.prototype.draw=function(){

var prim=vget('--color-text-primary','#eee'),sec=vget('--color-text-secondary','#999'),tert=vget('--color-text-tertiary','#777');

var S=SETUP,t0=S.t0,i;

function X(i){return -300+i*14.8;}

function Y(p){return 40-(p-88)*7.5;}

txt('Trend-line setup anatomy → 8 X features + label Y',{x:0,y:-262},prim,'center',14,'700');

txt('detector (contract §3): fits using only candles ≤ t0 · zero look-ahead · direction = +1 (long)',{x:0,y:-240},sec,'center',10.5);



var sE=CAM.S({x:X(t0),y:-210}),sE2=CAM.S({x:X(t0),y:200});

ctx.fillStyle=rgba(TEAL,0.10);ctx.fillRect(sE.x-8,sE.y,16,sE2.y-sE.y);

HITS.addRect(sE.x-8,sE.y,16,sE2.y-sE.y,{type:'setupEntry'});



line2({x:X(0),y:Y([S.LT](http://S.LT)(0))},{x:X(34),y:Y([S.LT](http://S.LT)(34))},RED,2,[]);

line2({x:X(0),y:Y(S.LO(0))},{x:X(34),y:Y(S.LO(34))},CAN,1.5,[6,4]);

txt('L_trend (resistance · traded)',{x:X(33)+4,y:Y([S.LT](http://S.LT)(33))-8},RED,'left',8.5,'600');

txt('L_opp (SL sits here)',{x:X(33)+4,y:Y(S.LO(33))+14},CAN,'left',8.5);



for(i=0;i<S.n;i++){

var cd=S.cs[i],up=cd.c>=cd.o;

line2({x:X(i),y:Y(cd.l)},{x:X(i),y:Y(cd.h)},CAN,1,[]);

var yA=Y(Math.max(cd.o,cd.c)),yB=Y(Math.min(cd.o,cd.c));

poly([{x:X(i)-4,y:yA},{x:X(i)+4,y:yA},{x:X(i)+4,y:yB},{x:X(i)-4,y:yB}],up?rgba(TP,0.55):rgba(SL,0.5));

}

for(i=0;i<S.touch.length;i++){

var tx=S.touch[i],sT=CAM.S({x:X(tx),y:Y([S.LT](http://S.LT)(tx))});

ctx.fillStyle=AMB;ctx.beginPath();ctx.arc(sT.x,sT.y,4,0,7);ctx.fill();

txtS('touch '+(i+1),sT.x,sT.y-9,AMB,'center',8,'600');

HITS.addRect(sT.x-7,sT.y-7,14,14,{type:'setupTouch'});

}

txt('entry_candle t0',{x:X(t0),y:Y(S.cs[t0].h)-26},TEAL,'center',9,'700');

txt('first close breaks L_trend in the direction (after ≥ MIN_TOUCHES=2)',{x:X(t0),y:Y(S.cs[t0].h)-14},tert,'center',7.5);



var xR=X(t0)+10;

line2({x:xR,y:Y(S.cs[t0].c)},{x:xR,y:Y(S.LO(t0))},AMB,2,[]);

line2({x:xR-4,y:Y(S.cs[t0].c)},{x:xR+4,y:Y(S.cs[t0].c)},AMB,2,[]);

line2({x:xR-4,y:Y(S.LO(t0))},{x:xR+4,y:Y(S.LO(t0))},AMB,2,[]);

txt('R0',{x:xR+8,y:(Y(S.cs[t0].c)+Y(S.LO(t0)))/2+3},AMB,'left',9,'700');

var sR=CAM.S({x:xR,y:(Y(S.cs[t0].c)+Y(S.LO(t0)))/2});

HITS.addRect(sR.x-10,sR.y-26,34,52,{type:'setupR0'});



line2({x:X(t0),y:Y(S.TPL)},{x:X(37)+12,y:Y(S.TPL)},TP,1.5,[6,4]);

txt('take_profit = close[t0] + direction·R0',{x:X(t0)-6,y:Y(S.TPL)-7},TP,'right',8.5,'600');

if(S.tpHit>=0){

var sH=CAM.S({x:X(S.tpHit),y:Y(S.cs[S.tpHit].c)});

[ctx.save](http://ctx.save)();ctx.strokeStyle=TP;ctx.lineWidth=2;ctx.beginPath();ctx.arc(sH.x,sH.y,7,0,7);ctx.stroke();ctx.restore();

txtS('Y = 1 · TP first-touch (close-based)',sH.x,sH.y-14,TP,'center',8.5,'700');

HITS.addRect(sH.x-9,sH.y-9,18,18,{type:'setupTP'});

}

line2({x:308,y:-200},{x:308,y:195},tert,1.2,[3,4]);

txt('→ time barrier t0+H (H=24, off-frame)',{x:300,y:210},tert,'right',8);



var PA=[

{f:0,x:-272,y:236,ax:X(20),ay:(Y(S.cs[20].c)+Y([S.LT](http://S.LT)(20)))/2},

{f:1,x:-92, y:236,ax:X(17),ay:(Y(S.cs[17].c)+Y(S.LO(17)))/2},

{f:2,x:88, y:236,ax:xR,ay:(Y(S.cs[t0].c)+Y(S.LO(t0)))/2},

{f:3,x:255, y:236},

{f:4,x:-272,y:266},

{f:5,x:-92, y:266},

{f:6,x:88, y:266,ax:X(S.touch[2]),ay:Y([S.LT](http://S.LT)(S.touch[2]))},

{f:7,x:255, y:266,ax:X(t0),ay:Y(S.cs[t0].h)-4}

];

for(i=0;i<PA.length;i++){

var pa=PA[i];

if([pa.ax](http://pa.ax)!=null)line2({x:pa.x,y:pa.y-9},{x:[pa.ax](http://pa.ax),y:pa.ay},rgba(CAN,0.5),1,[3,3]);

var sp=pillF(pa.x,pa.y,168,20,RED,fname(pa.f)||FEATURES[pa.f].name,0.10,8);

HITS.addRect(sp.x-84,sp.y-10,168,20,{type:'feature',f:pa.f});

}

txt('8 transformer features computed at t0 · model X = 7 (closed_through_line: audit) · click = formula and unit',{x:0,y:300},tert,'center',8.5);

};



function OptunaView(){}

OptunaView.prototype.draw=function(){

var prim=vget('--color-text-primary','#eee'),sec=vget('--color-text-secondary','#999'),tert=vget('--color-text-tertiary','#777');

txt('Optuna — XGBoost tuning on Train',{x:0,y:-262},prim,'center',14,'700');

txt('objective: '+OPTUNA.objective+' · '+OPTUNA.sampler+' · '+OPTUNA.pruner,{x:0,y:-240},sec,'center',9.5);

function X(i){return -320+i*2.7;}

function Y(v){return 110-(v-0.30)*820;}

line2({x:-320,y:Y(0.30)},{x:230,y:Y(0.30)},tert,1,[]);

line2({x:-320,y:Y(0.30)},{x:-320,y:Y(0.66)},tert,1,[]);

var i,tk=[0,50,100,150,200];

for(i=0;i<tk.length;i++)txt(String(tk[i]),{x:X(tk[i]),y:Y(0.30)+16},tert,'center',8);

txt('trial →',{x:240,y:Y(0.30)+16},tert,'left',8);

var vk=[0.35,0.45,0.55,0.65];

for(i=0;i<vk.length;i++){txt(vk[i].toFixed(2),{x:-328,y:Y(vk[i])+3},tert,'right',8);

line2({x:-320,y:Y(vk[i])},{x:230,y:Y(vk[i])},rgba(CAN,0.18),1,[2,4]);}

[ctx.save](http://ctx.save)();ctx.strokeStyle=TEAL;ctx.lineWidth=1.6;ctx.setLineDash([]);ctx.beginPath();

for(i=0;i<TRIALS.length;i++){var sB=CAM.S({x:X(i),y:Y(TRIALS[i].best)});if(i)ctx.lineTo(sB.x,sB.y);else ctx.moveTo(sB.x,sB.y);}

ctx.stroke();ctx.restore();

for(i=0;i<TRIALS.length;i++){

var t=TRIALS[i],s=CAM.S({x:X(i),y:Y(t.v)});

if(t.pruned){[ctx.save](http://ctx.save)();ctx.strokeStyle=rgba(CAN,0.55);ctx.lineWidth=1;

ctx.beginPath();ctx.moveTo(s.x-2.5,s.y-2.5);ctx.lineTo(s.x+2.5,s.y+2.5);

ctx.moveTo(s.x+2.5,s.y-2.5);ctx.lineTo(s.x-2.5,s.y+2.5);ctx.stroke();ctx.restore();}

else{ctx.fillStyle=rgba(GREEN,0.8);ctx.beginPath();ctx.arc(s.x,s.y,2.4,0,7);ctx.fill();}

HITS.addRect(s.x-4,s.y-4,8,8,{type:'trial',i:i});

}

var bt=TRIALS[BEST_TRIAL],sBt=CAM.S({x:X(BEST_TRIAL),y:Y(bt.v)});

[ctx.save](http://ctx.save)();ctx.strokeStyle=AMB;ctx.lineWidth=2;ctx.beginPath();ctx.arc(sBt.x,sBt.y,7,0,7);ctx.stroke();ctx.restore();

txtS('best: trial #'+BEST_TRIAL+' · AUC-PR '+bt.v.toFixed(3),sBt.x+12,sBt.y-8,AMB,'left',9,'600');

txt('line = best-so-far · × = pruned (MedianPruner) · dot = completed trial',{x:-320,y:Y(0.30)+34},tert,'left',8.5);

txt('hyperparameter importance',{x:-320,y:168},prim,'left',10,'600');

for(i=0;i<PARAM_IMPORTANCE.length;i++){

var pi=PARAM_IMPORTANCE[i],yy=190+i*34;

txt(pi[0],{x:-180,y:yy+3},sec,'right',8.5);

poly([{x:-170,y:yy-6},{x:-170+pi[1]*620,y:yy-6},{x:-170+pi[1]*620,y:yy+6},{x:-170,y:yy+6}],rgba(RED,0.45),RED,1);

txt((pi[1]*100).toFixed(0)+'%',{x:-162+pi[1]*620,y:yy+3},tert,'left',8);

}

txt('search space: depth 3–9 · lr 0.01–0.3 log · estimators 100–1200 · subsample/colsample 0.5–1 · λ 1e-3–10 · spw 0.5–4',{x:0,y:430},tert,'center',8);

};



var B64FILL=(function(){var r=rng(99),cset='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',rows=[],i,j;

for(i=0;i<4;i++){var s='';for(j=0;j<58;j++)s+=cset[Math.floor(r()*cset.length)];rows.push(s);}return rows;})();



function ArtifactView(){}

ArtifactView.prototype.draw=function(){

var prim=vget('--color-text-primary','#eee'),sec=vget('--color-text-secondary','#999'),tert=vget('--color-text-tertiary','#777');

var a=STATE.asset,nm=ASSETS[a];

txt('Artifact = self-contained strategy file',{x:0,y:-262},prim,'center',14,'700');

txt('one file per asset → 503 artifacts in total · deterministic build (hash)',{x:0,y:-240},sec,'center',10.5);

// band tooltips live in abandTip() (single source — read by tipFor)

var BANDS=[

{h:26,col:tert,t:'# strategy_'+nm+'.py — generated by the pipeline'},

{h:30,col:prim,t:'PARAMS: TF=1h · H=24 · MIN_TOUCHES=2 · BARRIER=close'},

{h:30,col:RED, t:'FEATURE_MANIFEST = [7 X columns — frozen order]'},

{h:92,col:AMB, t:'MODEL_B64 = "QmFzZTY0…"',b64:true},

{h:30,col:prim,t:'LABEL_CONTRACT = TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24'},

{h:30,col:TP, t:'def selfcheck(): golden input → output · PASS'},

{h:32,col:TEAL,t:'def decide(x): p = model(x) · p ≥ 0.60 → ENTRY else FLAT'}

];

var xw=225,y=-205,i,j;

var sTop=CAM.S({x:-xw,y:y-8}),sBot=CAM.S({x:xw,y:y+BANDS.reduce(function(p,q){return p+q.h+12;},0)+2});

[ctx.save](http://ctx.save)();ctx.strokeStyle=vget('--color-border-secondary','#555');ctx.lineWidth=1.2;ctx.setLineDash([]);

rrectS(sTop.x-8,sTop.y-6,sBot.x-sTop.x+16,sBot.y-sTop.y+10,10);ctx.stroke();ctx.restore();

for(i=0;i<BANDS.length;i++){

var b=BANDS[i],s0=CAM.S({x:-xw,y:y}),s1=CAM.S({x:xw,y:y+b.h});

fillRR(s0.x,s0.y,s1.x-s0.x,s1.y-s0.y,6,rgba(b.col===tert?CAN:b.col,b.b64?0.14:0.07),rgba(b.col===tert?CAN:b.col,0.6),1);

monoS(b.t,s0.x+10,s0.y+17*zScale(),b.col,'left',9.5);

if(b.b64)for(j=0;j<B64FILL.length;j++)monoS(B64FILL[j],s0.x+10,s0.y+(34+j*15)*zScale(),rgba(AMB,0.45),'left',8);

HITS.addRect(s0.x,s0.y,s1.x-s0.x,s1.y-s0.y,{type:'aband',b:i,a:a});

y+=b.h+12;

}

txt('standalone import — no access to training data · click = full JSON manifest',{x:0,y:y+22},tert,'center',8.5);

};

function abandTip(i){

return [

'file header\ngenerated, not hand-edited\nhash = artifact identifier',

'contract parameters (Layers_Short_SOT/00_parameters_[eng.md](http://eng.md))\nfrozen at build time',

'exactly these columns and in this order,\non which the model was trained\nwithout closed_through_line (audit)',

'XGBoost model serialized\nand base64-encoded (~180 kB)\ndecoded on file import',

'label contract identifier\nSL = moving L_opp(t) (decision v1.2)\nthe model answers the question of this contract',

'golden vectors checked on import\nprediction mismatch → hard error',

'strategy decision rule\nTHRESHOLD_ENTRY=0.60 tuned on Train'][i];

}



function LeakView(){}

LeakView.prototype.draw=function(){

var prim=vget('--color-text-primary','#eee'),sec=vget('--color-text-secondary','#999');

txt('⚠ ZERO LEAKAGE — time hygiene',{x:0,y:-226},SL,'center',14,'700');

txt('The model must not see the future — not through features, not through the split, not through tuning.',{x:0,y:-202},sec,'center',10.5);

var bad=['training on full history (Train+OOS)','random split (shuffle) instead of time-based','Optuna tuning after seeing OOS results','LEAKAGE / OVERFIT'];

var good=['time split + purge H=24 + embargo','causal features: only candles ≤ t0','Optuna: purged walk-forward only on Train','OOS frozen → single run'];

var i;

txt('✗ incorrect',{x:-150,y:-160},SL,'center',12,'700');

txt('✓ correct',{x:150,y:-160},TP,'center',12,'700');

for(i=0;i<4;i++){

var y=-145+i*100;

pill(-150,y,236,30,SL,bad[i],i===3?0.22:0.08);

pill(150,y,236,30,TP,good[i],0.08);

if(i<3){var a=CAM.S({x:-150,y:y+15}),b=CAM.S({x:-150,y:y+85});

ctx.strokeStyle=rgba(SL,0.8);ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();

[ctx.save](http://ctx.save)();ctx.translate(b.x,b.y);ctx.rotate(Math.PI);triUpS(0,0,rgba(SL,0.8));ctx.restore();

var a2=CAM.S({x:150,y:y+15}),b2=CAM.S({x:150,y:y+85});

ctx.strokeStyle=rgba(TP,0.8);ctx.beginPath();ctx.moveTo(a2.x,a2.y);ctx.lineTo(b2.x,b2.y);ctx.stroke();

[ctx.save](http://ctx.save)();ctx.translate(b2.x,b2.y);ctx.rotate(Math.PI);triUpS(0,0,rgba(TP,0.8));ctx.restore();}

}

var sX=CAM.S({x:-150,y:5});

ctx.strokeStyle=rgba(SL,0.85);ctx.lineWidth=3;

ctx.beginPath();ctx.moveTo(sX.x-120,sX.y-165);ctx.lineTo(sX.x+120,sX.y+165);ctx.moveTo(sX.x+120,sX.y-165);ctx.lineTo(sX.x-120,sX.y+165);ctx.stroke();ctx.lineWidth=1;

txt('Rule: we touch OOS once — after freezing the strategy artifacts (hash).',{x:0,y:166},prim,'center',11,'600');

};



function QCView(){}

QCView.prototype.draw=function(){

var prim=vget('--color-text-primary','#eee'),sec=vget('--color-text-secondary','#999'),tert=vget('--color-text-tertiary','#777');

txt('Quality gates QC-01…QC-11 — every load into DuckDB',{x:0,y:-262},prim,'center',14,'700');

txt('any gate fail = load is not published · 8 841 820 rows · violations: 0',{x:0,y:-240},sec,'center',10.5);

var k;

for(k=0;k<QC.length;k++){

var colX=(k<6)?-170:170,y=-220+(k%6)*95;

var s=pill(colX-105,y,84,24,PINK,gidv(k)||QC[k].id,0.12);

txt(QC[k].desc,{x:colX-52,y:y+4},sec,'left',9.5);

HITS.addRect(s.x-42,s.y-12,84,24,{type:'qc',g:k});

}

txt('PASS = condition for publishing a load · in the 3D overview: a row of dots by the store (L3) · full description: ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_[eng.md](http://eng.md)',{x:0,y:285},tert,'center',9);

};



function DQView(){}

DQView.prototype.draw=function(){

var prim=vget('--color-text-primary','#eee'),sec=vget('--color-text-secondary','#999'),tert=vget('--color-text-tertiary','#777');

txt('Data quality dashboard — from raw zip to features',{x:0,y:-262},prim,'center',14,'700');

txt('validation of stores and transforms · gate before training (L9) · any FAIL blocks',{x:0,y:-240},sec,'center',10.5);

var st=['<ticker>.zip ×510','DuckDB raw+VIEW','parquet ×503','Output B'],sx=[-255,-85,85,255],i,j;

for(i=0;i<4;i++){

pill(sx[i],-195,150,24,CAN,st[i],0.08);

if(i<3)edge(sx[i]+76,-195,sx[i+1]-76,-195);

}

for(i=0;i<DQ.length;i++){

var cx=[-220,0,220][i%3],cy=(i<3)?-108:62,col=dqCol(DQ[i].status);

var s0=CAM.S({x:cx-105,y:cy-58}),s1=CAM.S({x:cx+105,y:cy+58});

fillRR(s0.x,s0.y,s1.x-s0.x,s1.y-s0.y,9,rgba(col,0.07),col,1.3);

var hp=CAM.S({x:cx-95,y:cy-32});

txtS(DQ[i].name,hp.x,hp.y,prim,'left',10,'700');

var bp2=CAM.S({x:cx+95,y:cy-32});

txtS(DQ[i].status,bp2.x,bp2.y,col,'right',10,'700');

var lines=DQ[i].detail.split(' · ');

for(j=0;j<lines.length&&j<4;j++){

var lpb=CAM.S({x:cx-95,y:cy-12+j*19});

txtS(lines[j],lpb.x,lpb.y,tert,'left',7.5);

}

HITS.addRect(s0.x,s0.y,s1.x-s0.x,s1.y-s0.y,{type:'dqTile',q:i});

}

txt('layer output: reports/quality/summary.json (counters + statuses + input hashes) + self-contained dashboard HTML',{x:0,y:150},tert,'center',9);

txt('Rule: green dashboard = start condition for Optuna (L9).',{x:0,y:172},prim,'center',10.5,'600');

};



var LAYERS={src:new AlpacaSource(),zip:new ZipStore(),db:new DuckDBLayer(),qcring:new QCGateRing(),

tf:new TransformLayer(),split:new SplitLayer(),detector:new SetupDetectorLayer(),feat:new FeatureForest(),

dq:new QualityLayer(),train:new TrainingLayer(),oos:new OOSWall()};

var VIEWS={dataflow:new DataDAGView(),qc:new QCView(),split:new SplitTimelineView(),setup:new SetupGeometryView(),

optuna:new OptunaView(),artifact:new ArtifactView(),leak:new LeakView(),dq:new DQView()};



function drawScene(){

var i,insp=STATE.inspect;

boundaryLines();

for(i=0;i<9;i++){[ctx.save](http://ctx.save)();ctx.globalAlpha=insp?0.22:1;flowArrow(i);ctx.restore();}

var ord=[0,1,2,3,4,5,6,7,8,9].map(function(l){return {l:l,d:lp(l,0.5,0.5,30).d};})

.sort(function(p,q){return q.d-p.d;});

for(i=0;i<10;i++){

var l=ord[i].l;

[ctx.save](http://ctx.save)();ctx.globalAlpha=(!insp||(NODE_BY_LEV[l]&&NODE_BY_LEV[l].id===insp))?1:0.16; // Inspection: dim the unselected

if(l===0)LAYERS.src.draw();

else if(l===1)[LAYERS.zip](http://LAYERS.zip).draw();

else if(l===2){LAYERS.db.draw();LAYERS.qcring.draw();}

else if(l===3)[LAYERS.tf](http://LAYERS.tf).draw();

else if(l===4)LAYERS.split.draw();

else if(l===5)LAYERS.detector.draw();

else if(l===6)LAYERS.feat.draw();

else if(l===7)LAYERS.dq.draw();

else if(l===8)LAYERS.train.draw();

else LAYERS.oos.draw();

ctx.restore();

}

if(!insp)boundaryCards(); // in inspection the contract is in the panel, not on the boundary cards

else{var nn=NODE_BY_ID[insp];if(nn){

var lv=nn.lev,cor=[lp(lv,0.02,0,0),lp(lv,0.98,0,0),lp(lv,0.02,1,0),lp(lv,0.98,1,0),lp(lv,0.5,0.5,170)],

x0=1e9,y0=1e9,x1=-1e9,y1=-1e9,ci;

for(ci=0;ci<cor.length;ci++){var sc=CAM.S(cor[ci]);if(sc.x<x0)x0=sc.x;if(sc.y<y0)y0=sc.y;if(sc.x>x1)x1=sc.x;if(sc.y>y1)y1=sc.y;}

strokeRR(x0-12,y0-12,(x1-x0)+24,(y1-y0)+24,14,rgba(roleColor(nn.role),0.22+0.30*pulse()),2.2); // one active halo

txtS('Inspect: L'+(nn.lev+1)+' · '+nn.title+' — Esc / click background = overview',

cw/2,18,vget('--color-text-secondary','#999'),'center',11,'600');}}

}



function fitView(pts,padL,padR,padT,padB,zCap){

var x0=1e9,y0=1e9,x1=-1e9,y1=-1e9,i;

for(i=0;i<pts.length;i++){var p=pts[i];if(p.x<x0)x0=p.x;if(p.y<y0)y0=p.y;if(p.x>x1)x1=p.x;if(p.y>y1)y1=p.y;}

x0-=padL;x1+=padR;y0-=padT;y1+=padB;

var z=Math.min((cw-20)/(x1-x0),(chh-20)/(y1-y0));

if(zCap)z=Math.min(z,zCap);

return {x:(x0+x1)/2,y:(y0+y1)/2,z:z};

}

function homeFit(){



return fitView([lp(0,0,1.1,0),lp(0,1,1.1,0),lp(0,1,0,0),lp(0,0,0,0),

lp(9,0,0,60),lp(9,1,0,60),lp(9,0,1,60),lp(9,0.5,0.6,226)],104,104,28,36,null);

}



function preset(mode){

if(mode==='overview')return homeFit();

if(mode==='oos'){

return fitView([lp(9,0.06,0.60,6),lp(9,0.94,0.60,6),lp(9,0.06,0.60,176),lp(9,0.94,0.60,176),

lp(9,0.5,0.60,226),lp(8,0.5,0.95,0),lp(7,0.5,0.95,0),lp(4,0.5,0.95,0)],58,58,88,190,0.94);

}

return {x:0,y:-10,z:clamp(Math.min((chh-90)/520,(cw-60)/660),1,1.9)};

}

function setMode(m){

STATE.inspect=null;STATE.mode=m;CAM.t=preset(m);userMoved=false; // changing mode ends inspection

var bs=document.querySelectorAll('#segMode button'),i;

for(i=0;i<bs.length;i++)bs[i].classList.toggle('on',bs[i].getAttribute('data-m')===m);

}

function isFlatView(){return !!VIEWS[STATE.mode];}



function TooltipManager(){}

[TooltipManager.prototype.show](http://TooltipManager.prototype.show)=function(html,mx,my){

tip.innerHTML=html;[tip.style](http://tip.style).display='block';

var r=stage.getBoundingClientRect();

var x=clamp(mx+14,4,r.width-280),y=clamp(my+14,4,r.height-90);

[tip.style](http://tip.style).left=x+'px';[tip.style.top](http://tip.style.top)=y+'px';};

TooltipManager.prototype.hide=function(){[tip.style](http://tip.style).display='none';};

var TIPM=new TooltipManager();



function SidePanel(){}

[SidePanel.prototype.show](http://SidePanel.prototype.show)=function(title,html){panelTitle.textContent=title;panelBody.innerHTML=html;[panel.style](http://panel.style).display='block';};

SidePanel.prototype.hide=function(){[panel.style](http://panel.style).display='none';};

var PANEL=new SidePanel();

document.getElementById('panelClose').onclick=function(){PANEL.hide();};



// === INSPECTION mode: click a layer title → frame + dim the rest + contract card ===

function renderContract(n){ // contract card from the node + graph edges

var inc=PIPELINE.edges.filter(function(e){return [e.to](http://e.to)===[n.id](http://n.id);})[0];

var out=PIPELINE.edges.filter(function(e){return e.from===[n.id](http://n.id);})[0];

var tg=vget('--color-text-tertiary','#777');

var h='<b>'+(n.subtitle||n.summary||'')+'</b>';

if(n.input_contract)h+='<br><b>Input:</b> '+n.input_contract;

h+='<br><b>Operation:</b> '+(n.transform_verb||'—');

if(n.output_contract)h+='<br><b>Output:</b> '+n.output_contract;

if(n.metric)h+='<br><b>'+n.metric.label+':</b> '+n.metric.value;

if(n.invariants&&n.invariants.length)h+='<br><b>Invariants:</b><br>• '+n.invariants.join('<br>• ');

if(inc)h+='<br><br><b>← '+inc.from+':</b> '+inc.verb+' — '+inc.payload+' <span style="color:'+tg+'">('+inc.causal_scope+')</span>';

if(out)h+='<br><b>'+[out.to](http://out.to)+' →:</b> '+out.verb+' — '+out.payload;

h+='<br><br><span style="color:'+tg+'">status: '+(n.status||'ok')+' · family: '+[n.family](http://n.family)+' · hover an object = details</span>';

return h;

}

function frameLevel(lev){ // frame on a single level (generalized preset('oos'))

return fitView([lp(lev,0.02,0.0,0),lp(lev,0.98,0.0,0),lp(lev,0.02,1.0,0),lp(lev,0.98,1.0,0),

lp(lev,0.5,0.5,170)],64,64,84,150,1.25);

}

function setInspect(id){

if(id&&NODE_BY_ID[id]){var n=NODE_BY_ID[id];STATE.inspect=id;CAM.t=frameLevel(n.lev);userMoved=false;

[PANEL.show](http://PANEL.show)('L'+(n.lev+1)+' · '+n.title,renderContract(n));}

else{STATE.inspect=null;CAM.t=preset(STATE.mode);userMoved=false;PANEL.hide();}

}



function tipFor(p){

if(!p)return null;

if(p.type==='layercap'){var nc=NODE_BY_LEV[p.lev];return '<b>'+nc.title+'</b>\n'+(nc.subtitle||nc.summary||'')+'\n<i>click = layer inspection (contract)</i>';}

if(p.type==='asset'){var st=setupsMock(p.a),m=oosMock(p.a);

return '<b>Asset: '+ASSETS[p.a]+'</b>\n~17 600 1h candles (2016 → 2026)\nsetups in Train: long '+st.long+' · short '+st.short+'\nOOS: PF '+[m.pf](http://m.pf).toFixed(2)+' · Sharpe '+m.sharpe.toFixed(2)+'\n<i>click = panel / select asset</i>';}

if(p.type==='universe')return '<b>Universe: 503 S&P 500 tickers</b>\n7 named samples + the rest as a grid\n1h OHLCV · 2016-01-04 → today';

if(p.type==='api')return '<b>Alpaca Market Data API</b>\nfeed=sip · auth: API key\nhourly cron :05 · ET session guard\nupsert with 5-day lookback';

if(p.type==='zip')return '<b>'+(ASSETS[p.a]||'aapl').toLowerCase()+'.zip</b>\n1 ticker = 1 zip · headerless CSV\nYYYYMMDD HH:MM,o,h,l,c,v\nprices = deci-cents ×10000\n<i>click = sample rows</i>';

if(p.type==='db')return '<b>raw_ohlcv_1h</b>\n8 841 820 rows · 166 MB\nsymbol · ts · o/h/l/c BIGINT ×10000 · volume\n<i>click = schema + QC</i>';

if(p.type==='view')return '<b>VIEW ohlcv_1h</b>\nprices /10000.0 → USD (canonical)\nzero storage duplication';

if(p.type==='meta')return '<b>_meta</b>\nschema_version · source · built_at\nrow and symbol counters';

if(p.type==='qc')return QC[p.g].name+'\n'+QC[p.g].desc+'\n'+qcStat();

if(p.type==='qcAll')return '<b>Quality gates QC-01…QC-11</b>\ngate every load into DuckDB\n<i>click = full list</i>';

if(p.type==='snapshot')return '<b>atomic snapshot</b>\ndatabase copy + torn-read guard\nmanifest: rows / symbols / ts range / price_view\n<i>click = JSON manifest</i>';

if(p.type==='parquet')return '<b>parquet per ticker</b>\n<TICKER>/ohlcv.parquet\n503 files · zstd · clean OHLCV\n(features: transformer L7)';

if(p.type==='split'){var b=SPLIT.bands[p.k];return '<b>'+[b.name](http://b.name)+'</b>\n'+b.from+' → '+[b.to](http://b.to)+'\n'+b.note;}

if(p.type==='purge')return '<b>purge</b>\n'+SPLIT.purge;

if(p.type==='embargo')return '<b>embargo</b>\n'+SPLIT.embargo;

if(p.type==='feature'){var f=FEATURES[p.f];

return '<b>Feature: '+[f.name](http://f.name)+'</b>\nFamily: '+[f.family](http://f.family)+'\nSource: '+f.src+'\nFormula: '+f.formula+' ['+f.unit+']'+(f.special?'\n<span style="color:'+AMB+'">! '+f.special+'</span>':'');}

if(p.type==='label')return '<b>Y = triple barrier (TB_v1.1)</b>\nTP=1: close reaches close[t0]+direction·R0\nSL=0: close pierces L_opp(t) (moving line)\ntime=0: nothing by t0+H (H=24)\nfirst-touch · close-based';

if(p.type==='xgb')return '<b>XGBoost · binary:logistic</b>\nmeta-labeling: setup signal filter\nsample weights: label_uniqueness_weight\n1 model per asset × direction';

if(p.type==='optuna')return '<b>Optuna</b>\n200 trials · TPE · MedianPruner\nobjective: AUC-PR (purged WF CV on Train)\n<i>click = study</i>';

if(p.type==='trial'){var t=TRIALS[p.i];return '<b>trial #'+p.i+'</b>\nAUC-PR: '+t.v.toFixed(3)+(t.pruned?' · PRUNED':'')+'\ndepth '+t.params.max_depth+' · lr '+t.params.learning_rate+'\nn_est '+t.params.n_estimators+' · subsample '+t.params.subsample;}

if(p.type==='strategy')return '<b>strategy_'+ASSETS[p.a]+'.py</b>\nbase64 model + feature manifest\nthreshold 0.60 + selfcheck\n<i>click = full manifest</i>';

if(p.type==='aband')return abandTip(p.b)+'\n<i>click = full manifest</i>';

if(p.type==='oosCell'){var nm=p.a<7?ASSETS[p.a]:'asset_'+String(p.a+1).padStart(3,'0');var m2=oosMock(p.a),M=METRICS[p.m];

return '<b>'+nm+' × '+[M.name](http://M.name)+'</b>\nvalue: '+m2[[M.id](http://M.id)]+'\ntrades: '+m2.trades+' · PF '+[m2.pf](http://m2.pf)+' · MDD '+m2.mdd+'%\n<i>click = full row</i>';}

if(p.type==='dqTile'){var q=DQ[p.q];

return '<b>'+[q.name](http://q.name)+' — '+q.status+'</b>\n'+q.detail.split(' · ').join('\n')+'\n<i>click = panel</i>';}

if(p.type==='dqSummary')return '<b>summary.json + dashboard</b>\ncounters + statuses + input hashes\nany FAIL blocks training (L9)\n<i>click = details</i>';

if(p.type==='detector'){var nd=NODE_BY_ID['L6'];return '<b>'+nd.title+'</b>\n'+nd.subtitle+'\noutput: '+nd.output_contract+'\n'+nd.invariants.join(' · ')+'\n<i>click = contract · view 5 = full anatomy</i>';}

if(p.type==='setupEntry')return '<b>entry_candle (t0)</b>\nfirst close piercing L_trend\nafter line validation (≥ MIN_TOUCHES=2)\nall X features computed at t0';

if(p.type==='setupTouch')return '<b>touchpoint</b>\na touch of L_trend before t0\ntouch_count counts them up to candle t';

if(p.type==='setupR0')return '<b>R0</b>\n|close[t0] − L_opp(t0)|\none geometric risk unit\nTP = close[t0] + direction·R0';

if(p.type==='setupTP')return '<b>Y_outcome = 1</b>\nfirst t: sign·close ≥ sign·take_profit\nfirst-touch · close-based\nin window [t0+1, t0+H]';

if(p.type==='bnote')return '<b>Boundary note L'+(p.i+1)+' → L'+(p.i+2)+'</b>\nexplains the flow between levels\n<i>click = edit text (label panel)</i>';

return null;}



function clickFor(p){

if(!p)return;

if(p.type==='layercap'){setInspect(NODE_BY_LEV[p.lev].id);return;}

if(p.type==='asset'){

STATE.asset=p.a;document.getElementById('selAsset').value=String(p.a);

var st=setupsMock(p.a),m=oosMock(p.a),mf=manifest(p.a),feats=[],i;

for(i=0;i<FEATURES.length;i++)feats.push(FEATURES[i].name+' ('+importanceMock(p.a,i).toFixed(2)+')');

[PANEL.show](http://PANEL.show)(ASSETS[p.a]+' — details',

'<b>Setups (Train):</b> long '+st.long+' · short '+st.short+

'<br><b>CV (Train):</b> AUC-PR '+mf.metrics_cv.auc_pr+' · logloss '+mf.metrics_cv.logloss+

'<br><b>OOS:</b> PF '+[m.pf](http://m.pf)+' · Sharpe '+m.sharpe+' · MDD '+m.mdd+'% · TIM '+m.tim+'% · WR '+m.wr+'% · trades '+m.trades+

'<br><b>Artifact:</b> '+mf.strategy_file+

'<br><b>Top features (gain):</b><br>'+feats.slice(0,5).join('<br>'));}

else if(p.type==='qc')[PANEL.show](http://PANEL.show)(QC[p.g].name,'<b>'+QC[p.g].desc+'</b><br>'+qcStat()+'<br><br><b>All gates:</b><br>'+[QC.map](http://QC.map)(function(g){return [g.id](http://g.id)+' — '+g.desc;}).join('<br>'));

else if(p.type==='qcAll')[PANEL.show](http://PANEL.show)('QC gates','<pre>'+[QC.map](http://QC.map)(function(g){return [g.id](http://g.id)+' '+g.desc;}).join('\n')+'</pre>'+qcStat());

else if(p.type==='zip')[PANEL.show](http://PANEL.show)((ASSETS[p.a]||'aapl').toLowerCase()+'.zip','<b>CSV (LEAN, headerless):</b><pre>20240102 10:00,1851200,1853900,1849100,1852300,182345\n20240102 11:00,1852300,1856800,1851700,1855400,141280\n20240102 12:00,1855400,1857200,1853000,1854100,98430</pre>prices ×10000 → USD only in the VIEW');

else if(p.type==='db')[PANEL.show](http://PANEL.show)('DuckDB raw_ohlcv_1h','<pre>symbol VARCHAR\nts TIMESTAMP\nopen BIGINT ×10000\nhigh BIGINT ×10000\nlow BIGINT ×10000\nclose BIGINT ×10000\nvolume BIGINT</pre><b>8 841 820 rows · 503 symbols</b><br>2016-01-04 09:00 → 2026-05-29 15:00<br>QC-01…QC-11: PASS');

else if(p.type==='view')[PANEL.show](http://PANEL.show)('VIEW ohlcv_1h','<pre>SELECT symbol, ts,\n open/10000.0 AS open,\n high/10000.0 AS high,\n low/10000.0 AS low,\n close/10000.0 AS close,\n volume\nFROM raw_ohlcv_1h</pre><b>canonical USD · zero duplication</b>');

else if(p.type==='meta')[PANEL.show](http://PANEL.show)('_meta','<pre>schema_version : v1\nsource : alpaca sip 1h\nbuilt_at_utc : …\nrows : 8 841 820\nsymbols : 503</pre>');

else if(p.type==='snapshot')[PANEL.show](http://PANEL.show)('Snapshot manifest','<pre>'+JSON.stringify({rows:8841820,symbols:503,ts_min:'2016-01-04 09:00',ts_max:'2026-05-29 15:00',price_view:'raw_usd_view'},null,2)+'</pre>atomic copy · torn-read guard · zero derived columns');

else if(p.type==='split'||p.type==='purge'||p.type==='embargo'){var html='',k;

for(k=0;k<SPLIT.bands.length;k++){var b=SPLIT.bands[k];html+='<b>'+[b.name](http://b.name)+'</b> '+b.from+' → '+[b.to](http://b.to)+'<br>'+b.note+'<br><br>';}

[PANEL.show](http://PANEL.show)('Time split',html+'<b>Purge:</b> '+SPLIT.purge+'<br><b>Embargo:</b> '+SPLIT.embargo);}

else if(p.type==='feature'){var f=FEATURES[p.f];

[PANEL.show](http://PANEL.show)('Feature: '+[f.name](http://f.name),'<b>Formula:</b> '+f.formula+'<br><b>Unit:</b> '+f.unit+'<br><b>Family:</b> '+[f.family](http://f.family)+'<br><b>Source:</b> '+f.src+(f.special?'<br><b style="color:'+AMB+'">! '+f.special+'</b>':'')+'<br><br>computed causally at t0 (candles ≤ t0)');}

else if(p.type==='label'||p.type==='setupTP')[PANEL.show](http://PANEL.show)('Label Y (triple barrier)','<b>TP → Y=1:</b> first t: sign·close[t] ≥ sign·(close[t0]+direction·R0)<br><b>SL → Y=0:</b> first close pierces L_opp(t) — <b>moving line</b> (Layers_Short_SOT/L7_features_x_label_y_[eng.md](http://eng.md), decision v1.2)<br><b>time → Y=0:</b> no resolution by t0+H (H=24)<br><br>first-touch · close-based · geometric barriers from R0 (not ATR)<br>sample weights: label_uniqueness_weight (Layers_Short_SOT/L7_features_x_label_y_[eng.md](http://eng.md))');

else if(p.type==='xgb')[PANEL.show](http://PANEL.show)('XGBoost estimator','<b>Objective:</b> binary:logistic — p(TP)<br><b>Role:</b> meta-labeling, trend-line setup signal filter<br><b>Training:</b> Train with uniqueness weights<br><b>Tuning:</b> Optuna 200 trials (purged WF CV)<br><b>Per:</b> asset × direction');

else if(p.type==='optuna'||p.type==='trial'){var bt=TRIALS[BEST_TRIAL];

var extra=(p.type==='trial')?('<b>trial #'+p.i+':</b><pre>'+JSON.stringify(TRIALS[p.i].params,null,2)+'</pre>'):'';

[PANEL.show](http://PANEL.show)('Optuna study',extra+'<b>n_trials:</b> 200 · <b>sampler:</b> TPE<br><b>pruner:</b> '+OPTUNA.pruner+'<br><b>objective:</b> '+OPTUNA.objective+'<br><b>best:</b> #'+BEST_TRIAL+' → '+bt.v.toFixed(3)+'<br><b>search space:</b><pre>'+JSON.stringify([OPTUNA.space](http://OPTUNA.space),null,2)+'</pre>');}

else if(p.type==='strategy'||p.type==='aband')[PANEL.show](http://PANEL.show)('strategy_'+ASSETS[p.a!=null?p.a:STATE.asset]+'.py','<pre>'+JSON.stringify(manifest(p.a!=null?p.a:STATE.asset),null,2)+'</pre>');

else if(p.type==='oosCell'){var nm=p.a<7?ASSETS[p.a]:'asset_'+String(p.a+1).padStart(3,'0'),m2=oosMock(p.a);

[PANEL.show](http://PANEL.show)('OOS: '+nm,'<b>PF:</b> '+[m2.pf](http://m2.pf)+' · <b>Sharpe:</b> '+m2.sharpe+'<br><b>MDD:</b> '+m2.mdd+'% · <b>TIM:</b> '+m2.tim+'% · <b>WR:</b> '+m2.wr+'%<br><b>trades:</b> '+m2.trades+'<br><b>window:</b> 2024-01-02 → 2026-05-29 (frozen)<br><b>artifact:</b> strategy_'+nm+'.py');}

else if(p.type==='dqTile'){var q=DQ[p.q];

[PANEL.show](http://PANEL.show)('Quality: '+[q.name](http://q.name),'<b>Status:</b> '+q.status+'<br>'+q.detail.split(' · ').join('<br>')+'<br><br>source: reports/quality/summary.json');}

else if(p.type==='dqSummary')[PANEL.show](http://PANEL.show)('summary.json','<pre>'+JSON.stringify({schema_version:'1.0',built_at_utc:'…',inputs_hash:'…',counters:{rows:8841820,symbols:503,parquet_files:503,setups_total:0,det09_rejected:0,gaps_in_session:0,gaps_filled:0,volume_zero_bars:0,zero_range_bars:0,prices_nonpos:0,duplicates:0,nan_inf_outputB:0},parities:{zip_duckdb_rows:true,duckdb_parquet_files:true,parquet_outputB:true},checks:[{id:'QC-06',level:'WARN',value:1,threshold:0,desc:'volume=0 bars'}],overall_status:'WARN'},null,2)+'</pre>generated per run · the HTML dashboard reads only this file');

else if(p.type==='detector'){var nd=NODE_BY_ID['L6'];

[PANEL.show](http://PANEL.show)('L6 · '+nd.title,'<b>'+nd.subtitle+'</b><br><b>Input:</b> '+nd.input_contract+'<br><b>Output:</b> '+nd.output_contract+'<br><b>Invariants:</b><br>• '+nd.invariants.join('<br>• ')+'<br><br>full anatomy: view <b>5 (Setup geometry)</b>');}

else if(p.type==='setupEntry')[PANEL.show](http://PANEL.show)('entry_candle (t0)','first close piercing L_trend in the direction,<br>after line validation (≥ MIN_TOUCHES=2 touches)<br><br>all X features computed at t0 — only candles ≤ t0');

else if(p.type==='setupTouch'||p.type==='setupR0')[PANEL.show](http://PANEL.show)('Setup geometry','<b>touchpoints:</b> touches of L_trend before t0 (validate the line)<br><b>L_opp:</b> opposing line — the stop loss sits on it<br><b>R0:</b> |close[t0] − L_opp(t0)| — one risk unit<br><b>TP:</b> close[t0] + direction·R0 · <b>time barrier:</b> t0+H (H=24)');

else if(p.type==='bnote')leOpenFocus('bnd'+p.i);

}



function draw(){

HL.pending=false;

themeRefresh();

LQ.length=0;OBST.length=0;

ctx.clearRect(0,0,cw,chh);

ctx.fillStyle=vget('--color-background-primary','#1e1e1c');

ctx.fillRect(0,0,cw,chh);

HITS.clear();

var v=VIEWS[STATE.mode];

if(v)v.draw();

else drawScene();

drawLabels();

if(PIX_AUDIT)pixAuditDump();

}

var PIX_OFF=null;

function pixAuditDump(){ // scene signature: scale the whole canvas to 64×40 and luminance per cell

try{

var GW=64,GH=40,i;

if(!PIX_OFF){PIX_OFF=document.createElement('canvas');PIX_OFF.width=GW;PIX_OFF.height=GH;}

var octx=PIX_OFF.getContext('2d');

octx.clearRect(0,0,GW,GH);octx.drawImage(cv,0,0,GW,GH);

var d=octx.getImageData(0,0,GW,GH).data,sig=[];

for(i=0;i<GW*GH;i++){var o=i*4;sig.push(Math.round(d[o]*0.299+d[o+1]*0.587+d[o+2]*0.114));}

var el=document.getElementById('pixaudit');

if(!el){el=document.createElement('pre');[el.id](http://el.id)='pixaudit';[el.style](http://el.style).display='none';document.body.appendChild(el);}

el.textContent=JSON.stringify({mode:STATE.mode,inspect:STATE.inspect,gw:GW,gh:GH,sig:sig});

}catch(e){}

}

function Animator(){this.last=[performance.now](http://performance.now)();}

Animator.prototype.frame=function(now){

var dt=Math.min(0.05,(now-this.last)/1000);this.last=now;

ROT.step(dt);CAM.step(dt);

if(!STATE.paused){

CLK+=dt*STATE.speed;

if(CLK-lastTick>1.8){lastTick=CLK;if(!STATE.inspect)flash=1;} // no ambient flash in inspection (one active halo)

}

flash=Math.max(0,flash-dt*1.1);

draw();

requestAnimationFrame(this.frame.bind(this));

};

var ANIM=new Animator();



var mx=0,my=0,drag=null;

function localXY(e){var r=cv.getBoundingClientRect();return {x:e.clientX-r.left,y:[e.clientY-r.top](http://e.clientY-r.top)};}

cv.addEventListener('contextmenu',function(e){e.preventDefault();});

cv.addEventListener('mousemove',function(e){

var p=localXY(e);

if(drag){

var dx=p.x-mx,dy=p.y-my;mx=p.x;my=p.y;

drag.dist+=Math.abs(dx)+Math.abs(dy);

if(drag.dist>3){drag.moved=true;userMoved=true;}

if(drag.pan){

CAM.x-=dx/CAM.z;CAM.y-=dy/CAM.z;

CAM.t.x=CAM.x;CAM.t.y=CAM.y;CAM.t.z=CAM.z;

}else{

ROT.yaw+=dx*0.008;

ROT.pitch=clamp(ROT.pitch+dy*0.008,0.05,1.45);

ROT.t.yaw=ROT.yaw;ROT.t.pitch=ROT.pitch;

}

TIPM.hide();return;

}

mx=p.x;my=p.y;

var hit=HITS.find(mx,my),h=tipFor(hit);

if(h)[TIPM.show](http://TIPM.show)(h.replace(/\n/g,'<br>'),mx,my);else TIPM.hide();

});

cv.addEventListener('mousedown',function(e){

if(e.button!==0&&e.button!==2)return;

var p=localXY(e);mx=p.x;my=p.y;

drag={moved:false,dist:0,btn:e.button,pan:(e.button===2||e.shiftKey||isFlatView()||STATE.camPreset==='flat')};

[cv.style](http://cv.style).cursor='grabbing';});

window.addEventListener('mouseup',function(){

if(drag&&!drag.moved&&drag.btn===0){var h=HITS.find(mx,my);if(h)clickFor(h);else if(STATE.inspect)setInspect(null);} // click on the background = exit inspection

drag=null;[cv.style](http://cv.style).cursor='grab';});

cv.addEventListener('mouseleave',function(){TIPM.hide();});

cv.addEventListener('wheel',function(e){

e.preventDefault();

var p=localXY(e),z2=clamp(CAM.z*Math.exp(-e.deltaY*0.0011),0.3,4);

var wx=(p.x-cw/2)/CAM.z+CAM.x,wy=(p.y-chh/2)/CAM.z+CAM.y;

CAM.z=z2;CAM.x=wx-(p.x-cw/2)/z2;CAM.y=wy-(p.y-chh/2)/z2;

CAM.t.x=CAM.x;CAM.t.y=CAM.y;CAM.t.z=CAM.z;userMoved=true;

},{passive:false});

function applyCamPreset(){

if(STATE.camPreset==='flat'){ROT.t.yaw=0;ROT.t.pitch=0.08;}

else{ROT.t.yaw=-0.62;ROT.t.pitch=0.55;}}

cv.addEventListener('dblclick',function(){

STATE.inspect=null;applyCamPreset();

CAM.t=preset(STATE.mode);userMoved=false;});

window.addEventListener('keydown',function(e){

if(e.key==='Escape'&&currentPanel()==='editor'){setPanel(null);return;}

if(e.key==='Escape'&&STATE.inspect){setInspect(null);return;} // Esc = exit inspection

var tg=[e.target](http://e.target)&&[e.target](http://e.target).tagName;

if(tg==='INPUT'||tg==='TEXTAREA'||tg==='SELECT')return;

var i=['1','2','3','4','5','6','7','8','9','0'].indexOf(e.key);

if(i>=0)setMode(MODE_KEYS[i]);

});



function bindSeg(id,attr,fn){

var box=document.getElementById(id),bs=box.querySelectorAll('button'),i;

for(i=0;i<bs.length;i++)(function(b){b.onclick=function(){

var j;for(j=0;j<bs.length;j++)bs[j].classList.toggle('on',bs[j]===b);

fn(b.getAttribute(attr));};})(bs[i]);

}

bindSeg('segMode','data-m',function(v){setMode(v);});

bindSeg('segMetric','data-s',function(v){STATE.metric=v;});

bindSeg('segCam','data-c',function(v){

STATE.camPreset=v;

applyCamPreset();

CAM.t=preset(STATE.mode);userMoved=false;});

bindSeg('segSpd','data-v',function(v){STATE.speed=parseFloat(v);});

bindSeg('segNames','data-n',function(v){STATE.names=v;});

document.getElementById('cLabels').onchange=function(){STATE.labels=this.checked;};

document.getElementById('cFlow').onchange=function(){STATE.flow=this.checked;};

var bPause=document.getElementById('bPause');

bPause.onclick=function(){STATE.paused=!STATE.paused;bPause.textContent=STATE.paused?'▶ Resume':'⏸ Pause';};

document.getElementById('bPng').onclick=function(){

EXPORT_FONT=1.3;draw(); // presentation export: larger font tiers (declutter reflows)

try{cv.toBlob(function(b){EXPORT_FONT=1;draw();if(!b)return;var a=document.createElement('a');

a.href=URL.createObjectURL(b);[a.download](http://a.download)='sp500_pipeline_3d.png';[a.click](http://a.click)();});}

catch(e){EXPORT_FONT=1;draw();}

};

var selAsset=document.getElementById('selAsset');

(function(){var i;for(i=0;i<7;i++){var o=document.createElement('option');o.value=String(i);o.textContent=ASSETS[i];selAsset.appendChild(o);}})();

selAsset.onchange=function(){STATE.asset=parseInt(this.value,10)||0;};



var leEl=document.getElementById('lblEditor'),leBody=document.getElementById('leBody'),

leTab=document.getElementById('lblTab'),leSearch=document.getElementById('leSearch'),leBuilt=false;

var LE_GROUPS=['Levels','Layer boundaries','QC gates','Transformer features','Assets (sample)','Source / Universe',

'Store / DuckDB','Snapshot / Parquet','Time split','Features & label','Quality validation','Training / Optuna','OOS results','Other'];

function leArrayItems(){var d=[],i;

for(i=0;i<QC.length;i++)(function(i){

d.push({key:'gate'+i,grp:'QC gates',hint:'Gate '+ORIG_LBL.gateId[i]+' — short (view 3 board)',

get:function(){return QC[i].id;},set:function(v){QC[i].id=v;}});

d.push({key:'gateN'+i,grp:'QC gates',novis:true,hint:'Gate '+ORIG_LBL.gateId[i]+' — full name (side panel)',

get:function(){return QC[i].name;},set:function(v){QC[i].name=v;}});

})(i);

for(i=0;i<FEATURES.length;i++)(function(i){

d.push({key:'feat'+i,grp:'Transformer features',hint:'Feature #'+(i+1)+' · full name (tooltip/inspect; short on scene) · default: '+ORIG_LBL.feat[i],

get:function(){return FEATURES[i].name;},set:function(v){FEATURES[i].name=v;}});

})(i);

for(i=0;i<ASSETS.length;i++)(function(i){

d.push({key:'asset'+i,grp:'Assets (sample)',hint:'Asset #'+(i+1)+' · default: '+ORIG_LBL.asset[i],

get:function(){return ASSETS[i];},set:function(v){ASSETS[i]=v;}});

})(i);

return d;}

function leAllItems(){var items=leArrayItems(),i;

for(i=0;i<LBL_ORDER.length;i++){var k=LBL_ORDER[i];

items.push({key:k,grp:LBL_GRP[k]||'Other',hint:'default: '+LBL_DEF[k],reg:true,

get:(function(k){return function(){var o=LBL_OVR[k];return o!=null?o:LBL_DEF[k];};})(k),

set:(function(k){return function(v){if(v===LBL_DEF[k])delete LBL_OVR[k];else LBL_OVR[k]=v;};})(k)});}

return items;}

function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

function buildLabelEditor(){

try{draw();}catch(e){}

var items=leAllItems(),byG={},i;

for(i=0;i<items.length;i++){var g=items[i].grp;(byG[g]=byG[g]||[]).push(items[i]);}

var order=LE_GROUPS.slice(),g2;for(g2 in byG)if(order.indexOf(g2)<0)order.push(g2);

var map={};for(i=0;i<items.length;i++)map[items[i].key]=items[i];

var html='';

for(i=0;i<order.length;i++){var gn=order[i],list=byG[gn];if(!list||!list.length)continue;

html+='<div class="le-grp"><div class="le-gh"><span class="le-car">▾</span><span class="le-gt">'+esc(gn)+'</span> <span class="le-cnt">('+list.length+')</span></div><div class="le-rows">';

for(var j=0;j<list.length;j++){var it=list[j],off=!!LBL_OFF[it.key];

html+='<div class="le-row'+(off?' off':'')+'" data-key="'+esc(it.key)+'">'+

(it.novis?'<span style="width:15px;flex:0 0 auto"></span>':'<input type="checkbox" class="le-vis"'+(off?'':' checked')+'>')+

'<div class="le-fields"><div class="le-hint">'+esc(it.hint)+'</div>'+

'<input type="text" class="le-txt" value="'+esc(it.get())+'"></div></div>';

}

html+='</div></div>';

}

leBody.innerHTML=html;

var rows=leBody.querySelectorAll('.le-row');

for(i=0;i<rows.length;i++)(function(row){

var key=row.getAttribute('data-key'),it=map[key],inp=row.querySelector('.le-txt'),cb=row.querySelector('.le-vis');



inp.addEventListener('focus',function(){HL.key=key;row.classList.add('editing');});

inp.addEventListener('blur',function(){if(HL.key===key)HL.key=null;row.classList.remove('editing');});

inp.addEventListener('input',function(){HL.key=key;it.set(inp.value);lblSave();});

if(cb)cb.addEventListener('change',function(){if(cb.checked)delete LBL_OFF[key];else LBL_OFF[key]=true;

row.classList.toggle('off',!cb.checked);lblSave();});

})(rows[i]);

var ghs=leBody.querySelectorAll('.le-gh');

for(i=0;i<ghs.length;i++)(function(gh){

gh.addEventListener('click',function(){var grp=gh.parentNode,c=grp.classList.toggle('collapsed');

gh.querySelector('.le-car').textContent=c?'▸':'▾';});

})(ghs[i]);

leBuilt=true;

}

function leApplyFilter(){var q=leSearch.value.toLowerCase(),rows=leBody.querySelectorAll('.le-row'),i;

for(i=0;i<rows.length;i++){var r=rows[i],t=(r.querySelector('.le-txt').value+' '+r.querySelector('.le-hint').textContent).toLowerCase();

[r.style](http://r.style).display=(!q||t.indexOf(q)>=0)?'':'none';}}

leSearch.addEventListener('input',leApplyFilter);

var legTab=document.getElementById('legTab'),legHead=document.getElementById('legHead');

function loadPanel(){try{var p=localStorage.getItem('sp500_pipeline_panel');

if(p==null)return 'legend';if(p==='editor'||p==='legend')return p;}catch(e){}return 'legend';}

function savePanel(p){try{localStorage.setItem('sp500_pipeline_panel',p||'');}catch(e){}}

function currentPanel(){return document.body.classList.contains('le-open')?'editor':

(document.body.classList.contains('leg-open')?'legend':null);}

// p ∈ null|'editor'|'legend' — mutually exclusive; both can be closed (full screen).

// WITHOUT fit()/paddingBottom — panels are fixed overlays, the canvas doesn't reset (no re-render).

function setPanel(p){

var editor=(p==='editor'),legend=(p==='legend');

if(editor&&!leBuilt)buildLabelEditor();

document.body.classList.toggle('le-open',editor);

document.body.classList.toggle('leg-open',legend);

leEl.setAttribute('aria-hidden',editor?'false':'true');

leTab.setAttribute('aria-pressed',editor?'true':'false');

legTab.setAttribute('aria-pressed',legend?'true':'false');

if(!editor)HL.key=null;

savePanel(p||'');

}

function leOpen(){setPanel('editor');} // shim for leOpenFocus (click on the scene → open the editor)



function leOpenFocus(key){

leOpen();

if(leSearch.value){leSearch.value='';leApplyFilter();}

var row=leBody.querySelector('.le-row[data-key="'+key+'"]');

if(!row)return;

var grp=row.closest?row.closest('.le-grp'):null;

if(grp&&grp.classList.contains('collapsed')){grp.classList.remove('collapsed');

var car=grp.querySelector('.le-car');if(car)car.textContent='▾';}

leBody.scrollTop=Math.max(0,row.offsetTop-44);

var inp=row.querySelector('.le-txt');inp.focus();[inp.select](http://inp.select)();

}

leTab.addEventListener('click',function(){setPanel(currentPanel()==='editor'?null:'editor');});

legTab.addEventListener('click',function(){setPanel(currentPanel()==='legend'?null:'legend');});

legHead.addEventListener('click',function(){setPanel(null);});

document.getElementById('leHead').addEventListener('click',function(){setPanel(null);});

document.getElementById('leClose').addEventListener('click',function(){setPanel(null);});

document.getElementById('leReset').addEventListener('click',function(){lblResetAll();buildLabelEditor();});

document.getElementById('leAll').addEventListener('click',function(){LBL_OFF={};lblSave();buildLabelEditor();});

document.getElementById('leExport').addEventListener('click',function(){

var out={},items=leAllItems(),i;for(i=0;i<items.length;i++)out[items[i].key]={text:items[i].get(),hidden:!!LBL_OFF[items[i].key]};

try{var b=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});

var a=document.createElement('a');a.href=URL.createObjectURL(b);[a.download](http://a.download)='sp500_pipeline_labels.json';[a.click](http://a.click)();}catch(e){}});



function fit(){

var dpr=window.devicePixelRatio||1;

var w=Math.max(360,stage.clientWidth||940),h=Math.max(360,stage.clientHeight||600);

var bw=Math.floor(w*dpr),bh=Math.floor(h*dpr);

if(cv.width===bw&&cv.height===bh)return; // backing-store unchanged → don't reset canvas/camera (anti-flicker)

cw=w;chh=h;

[cv.style](http://cv.style).width=w+'px';[cv.style](http://cv.style).height=h+'px';

cv.width=bw;cv.height=bh;

ctx.setTransform(dpr,0,0,dpr,0,0);

CUR_FONT='';

if(!userMoved)CAM.t=preset(STATE.mode);

try{draw();}catch(e){} // repaint immediately — without 1 empty frame until the next rAF

}

try{new ResizeObserver(function(){fit();}).observe(stage);}catch(e){window.addEventListener('resize',fit);}

var reduce=false;try{reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;}catch(e){}

if(reduce){STATE.paused=true;STATE.flow=false;

document.getElementById('cFlow').checked=false;bPause.textContent='▶ Resume';}



lblLoad();

fit();

var hp=homeFit();CAM.x=hp.x;CAM.y=hp.y;CAM.z=hp.z;CAM.t=hp;

setPanel(loadPanel()); // apply the remembered/default panel (default: Legend open) — without fit()

try{var hm=decodeURIComponent(location.hash.slice(1));

if(hm==='0')hm='leak';

else if(/^[1-9]$/.test(hm))hm=MODE_KEYS[parseInt(hm,10)-1];

if(/^[lL]\d+$/.test(hm)&&NODE_BY_ID[hm.toUpperCase()]){ // inspection deep-link: #L6 → frame + contract

setInspect(hm.toUpperCase());var fp=frameLevel(NODE_BY_ID[hm.toUpperCase()].lev);CAM.x=fp.x;CAM.y=fp.y;CAM.z=fp.z;}

else if(MODE_KEYS.indexOf(hm)>=0&&hm!=='overview'){setMode(hm);var hp2=preset(hm);CAM.x=hp2.x;CAM.y=hp2.y;CAM.z=hp2.z;}

}catch(e){}

requestAnimationFrame(ANIM.frame.bind(ANIM));

})();

</script>

</body>

</html>

  
Raport spójności — `A_Layers` (Pipeline A · S&P 500 ML)

**Data audytu:** 2026-06-17  
**Audytowany katalog:** `/opt/to_liora_school/liora-project-ml-engineering/Plan/A_Layers`  
**Zasada nadrzędna:** SOT = `ENG/Layers_Short_SOT/` jest wzorcem; wszystkie inne artefakty (towarzysze `ENG/*.md`, karty akceptacyjne, `config/`, `viz/`, `README_A_Layer.md`, generator PDF) są podrzędne i muszą być z nim zgodne.  
**Metoda:** 12 osi cross-matchingu (A–L), każdy finding weryfikowany adwersaryjnie przez 3 niezależnych sceptyków (próg utrzymania ≥ 2/3).  
**Pokrycie:** 12/12 osi · 224 wiersze macierzy · 46 findingów · 135 głosów weryfikacyjnych.

> Uwaga proceduralna: wieloagentowy proces audytu policzył wszystkie 12 analiz osi i 133/135 weryfikacji, po czym przerwał się tuż przed automatycznym krokiem składania raportu. Niniejszy raport został złożony **deterministycznie** z odzyskanych, już zweryfikowanych wyników (bez utraty danych analitycznych). Dwa nieukończone głosy dotyczyły wyłącznie findingu L3, który zaadjudykowano ręcznie.

## 1. Streszczenie wykonawcze

**Werdykt ogólny: katalog `A_Layers` jest w wysokim stopniu spójny.** Po weryfikacji adwersaryjnej **nie wykryto żadnej rozbieżności krytycznej (BLOCKER) ani wysokiej (HIGH)**. Dyscyplina SOT ("one home per fact", "on divergence SOT wins") trzyma się w rdzeniu: wszystkie 17 parametrów skalarnych, 6 dat splitu, 11 bramek QC, 12 liczników L8, formuły 8 cech, kontrakt Output B i kolejność metryk PF·Sharpe·MDD·TIM·WR są **wartościowo zgodne** między `config/params.json`, SOT, kartami i wizualizacją.

Potwierdzone findingi (po weryfikacji): **32** · odrzucone w weryfikacji: **14** (skuteczne odsianie fałszywych trafień).


| Severity  | Liczba potwierdzonych findingów |
| --------- | ------------------------------- |
| MEDIUM    | 5                               |
| LOW       | 21                              |
| INFO      | 6                               |
| **RAZEM** | **32**                          |


**Najważniejsze ustalenia (tematycznie):**

1. **Liczenie parametrów — wewnętrzna nieścisłość SOT (MEDIUM).** `config/params.json` ma 18 kluczy skalarnych top-level (łącznie z `EPS` i `TOUCH_TOL`), a narracja SOT/karty mówi "17 keys + EPS + TOUCH_TOL", przy czym `00_Crosscutting_Overview_Card.md` dodatkowo podwójnie liczy `EPS` ("exactly 17 keys + EPS"). Sama wartość każdego parametru jest zgodna — niespójne jest tylko *liczenie* (findingi **B1, B2, A2, A4, A5**).
2. `**viz/main_data_flow.html` jako równoległe źródło wartości nieosadzonych w SOT (MEDIUM) — największe naruszenie DRY.** Wizualizacja wprowadza pełną przestrzeń przeszukiwania hiperparametrów Optuny (`max_depth 3–9`, `learning_rate 0.01–0.3`, …), progi oceny metryk OOS (`lo/hiV`), frakcje okien splitu (`0.075/0.695/0.230`) oraz liczby ważności hiperparametrów — żadnej z tych wartości SOT nie definiuje (findingi **B3, J1, J2, E2, J4, G3**).
3. **Liczność foldów CV `k=4` bez domu (MEDIUM).** Wartość `k=4` żyje wyłącznie w prozie SOT `L9` (i jest powtarzana w viz/kartach), ale nie ma jej w `config/params.json` ani w rejestrze `00_parameters_eng.md` — to fakt build-critical bez kanonicznego domu (findingi **E1, B4**).
4. **Nazewnictwo: klucze `config` vs symbole SOT (LOW).** `params.json` używa `pivot_k/lookback_candles/cooldown_candles`, SOT — `k/LOOKBACK/COOLDOWN`; brak jawnej tabeli mapowania. Podobnie `viz.checks[].id` i skrót `w_unique` odbiegają od konwencji SOT (findingi **F1, I2, I3, G2**).
5. **Ryzyka driftu (LOW).** Wygenerowany `Master_Layer_Cards_Print_A4.pdf` jest starszy niż wszystkie karty `.md` (nieaktualny); generator PDF ma zaszytą listę `CARD_FILES` i stopkę "/ 11"; tożsamość/kolejność warstw utrzymywana jest przez trzy równoległe hardcody (findingi **L1, L2, D2, D3, F2**).

## 2. Zakres i metoda

**Audytowane grupy plików:**

- **SOT (wzorzec):** `ENG/Layers_Short_SOT/` — `00_conventions/parameters/input_contract/definition_of_done`, `L1..L10`, `README.md`.
- **Towarzysze (podrzędni):** `ENG/readme_eng.md`, `build_contract_eng.md`, `detector_algorithm_eng.md`, `quality_gate_spec_eng.md`, `glossary_eng.md`, `summary_rules_eng.md`.
- **Karty akceptacyjne:** `acceptance_data_transform_cards/` (L01–L10, `00_Crosscutting_Overview_Card.md`, `card_template.md`, `README_cards.md`, `generate_master_layer_cards_pdf.py`, PDF).
- **Konfiguracja:** `config/params.json`, `config/universe.txt`.
- **Wizualizacja / README:** `viz/main_data_flow.html`, `README_A_Layer.md`.

**Kategorie rozbieżności użyte w findingach:**

- **(a)** realna rozbieżność wartości/faktu;
- **(b)** rozbieżność nazewnictwa/struktury kluczy;
- **(c)** niejednoznaczność sformułowania;
- **(d)** fakt nieosadzony w SOT (artefakt podrzędny wprowadza wartość/zakres, których SOT nie definiuje → naruszenie "one home per fact");
- **(e)** ryzyko driftu (hardcode/lista pasująca dziś, łatwa do rozjechania).

**Metoda:** Dla każdej z 12 osi niezależny agent przeczytał komplet przypisanych plików, zbudował macierz cross-matchingu (każdy fakt → wszystkie miejsca wystąpienia z cytatem `plik:linia`) i zgłosił findingi tylko dla statusów innych niż OK. Każdy finding został następnie skonfrontowany z trzema niezależnymi sceptykami, którzy próbowali go obalić; finding utrzymano przy ≥ 2/3 głosach. Werdykty zmapowano do findingów po `id` osadzonym w promptach weryfikacji. Wewnętrzne niespójności samego SOT traktowane są jako priorytetowe (SOT jest wzorcem — jego własna nieścisłość ma większą wagę niż odchylenie artefaktu podrzędnego).

## 3. Mapa SOT i governance (technika użytkowania)

Hierarchia jest zadeklarowana jednoznacznie i spójnie w `README_A_Layer.md`, `ENG/readme_eng.md` oraz `ENG/Layers_Short_SOT/README.md`: katalog `Layers_Short_SOT/` jest kanoniczny, towarzysze i karty są podrzędne, a przy rozbieżności "SOT wygrywa". Mapa własności faktów (`Layers_Short_SOT/README.md:45–62`) przypisuje każdy fakt do jednego domu. Reguła "each fact has exactly one home" jest w praktyce przestrzegana dla wartości (parametry, daty, progi), a większość artefaktów podrzędnych poprawnie **odsyła** do SOT zamiast redefiniować.

Audyt techniki użytkowania ujawnił jednak trzy systematyczne pęknięcia tej dyscypliny, wszystkie ujęte w findingach:

- **Liczenie/rejestr parametrów** — narracja "17" i podwójne liczenie `EPS` powodują, że *opis* rejestru jest wewnętrznie niespójny, mimo że *wartości* się zgadzają (A2, A4, A5, B1, B2).
- **Wizualizacja jako cichy współ-właściciel faktów** — `viz` wprowadza wartości build-relevant (przestrzeń Optuny, progi metryk, frakcje, ważności), których SOT nie ma; to dokładnie przypadek "fact without a home" (B3, J1, J2, E2, J4, G3).
- **Drobne redefinicje w towarzyszach** — `build_contract_eng.md` mimo deklaracji "restates no fact" powtarza kilka wartości, a `glossary_eng.md` restatuje pochodne wzory/liczby (A6, K6).

## 4. Macierze cross-matchingu (osie A–L)

Pełne tabele zgodności. Status: ✅ OK (zgodne z SOT) · ❌ ROZBIEŻNE · ⚠️ RYZYKO driftu · 🔶 NIEOSADZONE (brak domu w SOT) · ❔ NIEUSTALONE.

### Oś A — Governance / technika użytkowania / DRY

**Werdykt:** Rdzen governance spojny; rozbieznosci i ryzyka w findingach A1-A7. Pelne uzasadnienie OK/DIVERGENT/RISK per fakt znajduje sie w findingach.  
**Statusy wierszy:** ❌1


| Fakt                             | Źródła (`plik:linia` = wartość)                     | Status      | Uwaga |
| -------------------------------- | --------------------------------------------------- | ----------- | ----- |
| rdzen OK; A1-A7 = DIVERGENT/RISK | `ENG/Layers_Short_SOT/README.md:3` = patrz findingi | ❌ ROZBIEŻNE |       |


### Oś B — Parametry (rejestr params.json ↔ 00_parameters)

**Werdykt:** Wartości skalarne i bloki (splits/detector/l8) są w 100% zgodne między config/params.json a 00_parameters_eng.md (parzystość 1:1 zachowana), ale narracja licząca parametry jest wewnętrznie sprzeczna w samym SOT (params.json ma 18 skalarnych kluczy top-level, nie 17; README.md i Overview Card liczą EPS dwa razy), a viz wprowadza pełną przestrzeń przeszukiwania Optuny, której SOT nigdzie nie definiuje (kategoria d).  
**Statusy wierszy:** ✅30 · ❌1 · 🔶1


| Fakt                                                                                                                                                     | Źródła (`plik:linia` = wartość)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Status         | Uwaga                                                                                                                                                                                                                                                                                                              |
| -------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Liczba skalarnych kluczy top-level w params.json vs narracja '17 parametrów'                                                                             | `config/params.json:2-19` = 18 skalarnych kluczy top-level: TF, H, MIN_TOUCHES, W_VOL, W_ATR, ATR_VARIANT, PRICE_VIEW, EPS, BARRIER_MODE, DISTANCE_NORM, THRESHOLD_ENTRY, PURGE_CANDLES, EMBARGO_SESSIONS, N_TRIALS, CV_SCHEME, ESTIMATOR, TUNER, TOUCH_TOL `ENG/Layers_Short_SOT/00_parameters_eng.md:7` = ## Contract parameters (17 keys from `params.json`) — tabela ma 17 wierszy, EPS jako wiersz wewnętrzny, TOUCH_TOL opisany osobno w sekcji detector `ENG/Layers_Short_SOT/README.md:50` = All parameters (17 `params.json` keys + EPS + `TOUCH_TOL` + detector `k`/`LOOKBACK`/`COOLDOWN` + L8 threshold constants) `ENG/Layers_Short_SOT/README.md:26` = 17 keys + EPS + detector reference values + L8 threshold constants (bez TOUCH_TOL) `acceptance_data_transform_cards/00_Crosscutting_Overview_Card.md:19` = Canonical params file: `config/params.json` (exactly 17 keys + EPS + detector constants + L8 thresholds) | ❌ ROZBIEŻNE    | params.json ma 18 skalarnych kluczy top-level. 00_parameters liczy EPS WEWNĄTRZ '17 keys' i wyklucza TOUCH_TOL. README.md:50 oraz Overview Card liczą '17 keys + EPS' (EPS poza siedemnastką) — sprzeczność wewnątrz SOT co do tego, czy EPS należy do 17. Dodatkowo żadna narracja nie nazywa wprost 18 skalarów. |
| TF (timeframe)                                                                                                                                           | `config/params.json:2` = "TF": "1h" `ENG/Layers_Short_SOT/00_parameters_eng.md:11` = `TF` | `1h` `ENG/Layers_Short_SOT/00_conventions_eng.md:45` = default `1h` `viz/main_data_flow.html:1797` = PARAMS: TF=1h                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | ✅ OK           | Zgodne wszędzie.                                                                                                                                                                                                                                                                                                   |
| H / HORIZON_CANDLES (długość time-barrier)                                                                                                               | `config/params.json:3` = "H": 24 `ENG/Layers_Short_SOT/00_parameters_eng.md:12` = `H` (`HORIZON_CANDLES`) | `24` `viz/main_data_flow.html:1797` = H=24                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | ✅ OK           | Zgodne.                                                                                                                                                                                                                                                                                                            |
| MIN_TOUCHES                                                                                                                                              | `config/params.json:4` = "MIN_TOUCHES": 2 `ENG/Layers_Short_SOT/00_parameters_eng.md:13` = `MIN_TOUCHES` | `2` `viz/main_data_flow.html:466` = MIN_TOUCHES = 2                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | ✅ OK           | Zgodne.                                                                                                                                                                                                                                                                                                            |
| W_VOL (okno volume_z_score)                                                                                                                              | `config/params.json:5` = "W_VOL": 20 `ENG/Layers_Short_SOT/00_parameters_eng.md:14` = `W_VOL` | `20` `viz/main_data_flow.html:334` = W_VOL=20                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | ✅ OK           | Zgodne.                                                                                                                                                                                                                                                                                                            |
| W_ATR (okno ATR)                                                                                                                                         | `config/params.json:6` = "W_ATR": 14 `ENG/Layers_Short_SOT/00_parameters_eng.md:15` = `W_ATR` | `14` `viz/main_data_flow.html:334` = W_ATR=14                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | ✅ OK           | Zgodne; viz Wilder ATR(14) (304-305) zgodne z ATR_VARIANT.                                                                                                                                                                                                                                                         |
| ATR_VARIANT                                                                                                                                              | `config/params.json:7` = "ATR_VARIANT": "wilder" `ENG/Layers_Short_SOT/00_parameters_eng.md:16` = `ATR_VARIANT` | `wilder` `viz/main_data_flow.html:304` = Wilder ATR(14)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ✅ OK           | Zgodne.                                                                                                                                                                                                                                                                                                            |
| PRICE_VIEW                                                                                                                                               | `config/params.json:8` = "PRICE_VIEW": "raw_usd_view" `ENG/Layers_Short_SOT/00_parameters_eng.md:17` = `PRICE_VIEW` | `raw_usd_view` `ENG/Layers_Short_SOT/00_conventions_eng.md:26` = Input price view | `raw_usd_view` `viz/main_data_flow.html:2065` = price_view:'raw_usd_view'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | ✅ OK           | Zgodne.                                                                                                                                                                                                                                                                                                            |
| EPS (ε, guard dzielenia przez zero)                                                                                                                      | `config/params.json:9` = "EPS": 1e-9 `ENG/Layers_Short_SOT/00_parameters_eng.md:18` = `EPS` | `1e-9` `ENG/Layers_Short_SOT/00_parameters_eng.md:67` = `ε = 1e-9` `ENG/Layers_Short_SOT/00_conventions_eng.md:12` = `ε` = `EPS` = `1e-9`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | ✅ OK           | Wartość identyczna (1e-9 == Python 1e-09). Uwaga: liczenie EPS jako '17.-tego klucza' jest sporne — patrz wiersz o liczbie kluczy.                                                                                                                                                                                 |
| BARRIER_MODE                                                                                                                                             | `config/params.json:10` = "BARRIER_MODE": "close" `ENG/Layers_Short_SOT/00_parameters_eng.md:19` = `BARRIER_MODE` | `close` | `close` (recommended) / `intrabar` `viz/main_data_flow.html:1797` = BARRIER=close                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | ✅ OK           | Zgodne.                                                                                                                                                                                                                                                                                                            |
| DISTANCE_NORM                                                                                                                                            | `config/params.json:11` = "DISTANCE_NORM": "atr" `ENG/Layers_Short_SOT/00_parameters_eng.md:20` = `DISTANCE_NORM` | `atr` | `atr` (recommended) / `pct` / `raw`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | ✅ OK           | Zgodne; viz nie wprowadza wartości sprzecznej.                                                                                                                                                                                                                                                                     |
| THRESHOLD_ENTRY (próg decyzyjny)                                                                                                                         | `config/params.json:12` = "THRESHOLD_ENTRY": 0.6 `ENG/Layers_Short_SOT/00_parameters_eng.md:21` = `THRESHOLD_ENTRY` | `0.60` `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:30` = `THRESHOLD_ENTRY = 0.60` `viz/main_data_flow.html:411` = threshold_entry:0.60 `viz/main_data_flow.html:1166` = threshold 0.60 `viz/main_data_flow.html:1802` = p ≥ 0.60 → ENTRY else FLAT `viz/main_data_flow.html:1826` = THRESHOLD_ENTRY=0.60 tuned on Train                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | ✅ OK           | Wartość liczbowa identyczna (0.6 == 0.60). Rozbieżność czysto formatowa (params.json 0.6, SOT/viz 0.60) — bez konsekwencji.                                                                                                                                                                                        |
| PURGE_CANDLES                                                                                                                                            | `config/params.json:13` = "PURGE_CANDLES": 24 `ENG/Layers_Short_SOT/00_parameters_eng.md:22` = `PURGE_CANDLES` | `H` (= 24) `acceptance_data_transform_cards/L05_Time_Split_Card.md:28` = PURGE_CANDLES=24 `viz/main_data_flow.html:459` = purge = H = 24                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ✅ OK           | Zgodne (24 = H).                                                                                                                                                                                                                                                                                                   |
| EMBARGO_SESSIONS                                                                                                                                         | `config/params.json:14` = "EMBARGO_SESSIONS": 5 `ENG/Layers_Short_SOT/00_parameters_eng.md:23` = `EMBARGO_SESSIONS` | `5` (≈ 35 candles) `acceptance_data_transform_cards/L05_Time_Split_Card.md:28` = EMBARGO=5 sessions `viz/main_data_flow.html:340` = embargo ≈ 5 sessions (~35 candles)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | ✅ OK           | Zgodne (5 sesji ≈ 35 świec).                                                                                                                                                                                                                                                                                       |
| N_TRIALS (budżet Optuny)                                                                                                                                 | `config/params.json:15` = "N_TRIALS": 200 `ENG/Layers_Short_SOT/00_parameters_eng.md:24` = `N_TRIALS` | `200` `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:9` = budget: 200 trials (`N_TRIALS`) `acceptance_data_transform_cards/L09_Optuna_XGBoost_Card.md:21` = `N_TRIALS=200` `viz/main_data_flow.html:354` = n_trials:200 `viz/main_data_flow.html:412` = optuna:{n_trials:200                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | ✅ OK           | Zgodne wszędzie (200).                                                                                                                                                                                                                                                                                             |
| CV_SCHEME                                                                                                                                                | `config/params.json:16` = "CV_SCHEME": "purged_walk_forward" `ENG/Layers_Short_SOT/00_parameters_eng.md:25` = `CV_SCHEME` | `purged_walk_forward` `acceptance_data_transform_cards/L05_Time_Split_Card.md:37` = CV scheme = purged walk-forward (k=4) `viz/main_data_flow.html:355` = k=4 purged walk-forward folds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | ✅ OK           | Zgodne. Wartość k=4 nie jest kluczem w params.json — jest osadzona w SOT L9:12 (i 00_parameters nie definiuje k). Karta i viz cytują k=4 zgodnie z L9.                                                                                                                                                             |
| ESTIMATOR                                                                                                                                                | `config/params.json:17` = "ESTIMATOR": "xgboost_binary_logistic" `ENG/Layers_Short_SOT/00_parameters_eng.md:26` = `ESTIMATOR` | `xgboost_binary_logistic` `viz/main_data_flow.html:407` = XGBoost binary:logistic (meta-labeling…)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | ✅ OK           | Zgodne.                                                                                                                                                                                                                                                                                                            |
| TUNER                                                                                                                                                    | `config/params.json:18` = "TUNER": "optuna_tpe_median_pruner" `ENG/Layers_Short_SOT/00_parameters_eng.md:27` = `TUNER` | `optuna_tpe_median_pruner` (TPE + MedianPruner) `viz/main_data_flow.html:354` = sampler:'TPE', pruner:'MedianPruner(n_warmup_steps=2)'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | ✅ OK           | Zgodne; MedianPruner(n_warmup_steps=2) homed w L9:11.                                                                                                                                                                                                                                                              |
| TOUCH_TOL (top-level skalar; tolerancja dotyku w ×ATR)                                                                                                   | `config/params.json:19` = "TOUCH_TOL": 0.25 `ENG/Layers_Short_SOT/00_parameters_eng.md:40` = `TOUCH_TOL` | `0.25` | × `ATR(t)`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | ✅ OK           | Wartość zgodna (0.25). TOUCH_TOL jest top-level skalarem w params.json, ale w 00_parameters jest opisany w bloku 'Detector reference-design', poza tabelą '17 keys' — przyczyna sporu o liczbę kluczy.                                                                                                             |
| splits.warmup_start / warmup_end                                                                                                                         | `config/params.json:21-22` = warmup_start 2016-01-04 / warmup_end 2016-10-14 `acceptance_data_transform_cards/L05_Time_Split_Card.md:22` = Warm-up: 2016-01-04 → 2016-10-14 `viz/main_data_flow.html:333` = warmup from:'2016-01-04' to:'2016-10-14'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | ✅ OK           | Daty zgodne; 00_parameters odsyła do params.json, daty homed w params.json + L5.                                                                                                                                                                                                                                   |
| splits.train_start / train_end                                                                                                                           | `config/params.json:23-24` = train_start 2016-10-17 / train_end 2023-12-29 `acceptance_data_transform_cards/L05_Time_Split_Card.md:23` = Train: 2016-10-17 → 2023-12-29 `viz/main_data_flow.html:335` = train from:'2016-10-17' to:'2023-12-29' `viz/main_data_flow.html:413` = train:'2016-10-17 → 2023-12-29'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | ✅ OK           | Zgodne.                                                                                                                                                                                                                                                                                                            |
| splits.oos_start / oos_end                                                                                                                               | `config/params.json:25-26` = oos_start 2024-01-02 / oos_end 2026-05-29 `acceptance_data_transform_cards/L05_Time_Split_Card.md:24` = OOS: 2024-01-02 → 2026-05-29 `viz/main_data_flow.html:337` = oos from:'2024-01-02' to:'2026-05-29' `viz/main_data_flow.html:491` = single run on OOS 2024-01-02 → 2026-05-29                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | ✅ OK           | Zgodne.                                                                                                                                                                                                                                                                                                            |
| detector.pivot_k (k pivot strength)                                                                                                                      | `config/params.json:29` = "pivot_k": 3 `ENG/Layers_Short_SOT/00_parameters_eng.md:39` = `k` (pivot strength) | `3` | candles each side                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | ✅ OK           | Zgodne. Viz nie wprowadza wartości pivot_k.                                                                                                                                                                                                                                                                        |
| detector.lookback_candles (LOOKBACK fit window)                                                                                                          | `config/params.json:30` = "lookback_candles": 120 `ENG/Layers_Short_SOT/00_parameters_eng.md:41` = `LOOKBACK` (fit window) | `120` | candles                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | ✅ OK           | Zgodne (120). Viz nie wprowadza tej wartości.                                                                                                                                                                                                                                                                      |
| detector.cooldown_candles (COOLDOWN)                                                                                                                     | `config/params.json:31` = "cooldown_candles": 24 `ENG/Layers_Short_SOT/00_parameters_eng.md:42` = `COOLDOWN` | `H` (= 24) | candles                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | ✅ OK           | Zgodne (24 = H).                                                                                                                                                                                                                                                                                                   |
| l8.in_session_gaps_fail_gt / filled_gaps_fail_gt / duplicates_fail_gt / prices_nonpos_fail_gt / nan_inf_outputB_fail_gt                                  | `config/params.json:34-38` = wszystkie = 0 (FAIL gdy > 0) `ENG/Layers_Short_SOT/00_parameters_eng.md:56-59` = gaps_in_session/gaps_filled/duplicates/prices_nonpos/nan_inf_outputB: OK iff ==0, FAIL iff >0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | ✅ OK           | Zgodne (próg 0, operator >). Uwaga (b): klucze params.json (in_session_gaps_fail_gt) vs etykiety w tabeli SOT (gaps_in_session) różnią się formą nazewniczą, ale to odwzorowanie licznika→klucz, nie rozbieżność wartości.                                                                                         |
| l8.parity_fail_on_mismatch                                                                                                                               | `config/params.json:39` = "parity_fail_on_mismatch": true `ENG/Layers_Short_SOT/00_parameters_eng.md:60` = parity P1/P2/P3 | equal | FAIL iff any mismatch                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | ✅ OK           | Zgodne.                                                                                                                                                                                                                                                                                                            |
| l8.volume_zero_warn_fraction / volume_zero_fail_fraction                                                                                                 | `config/params.json:40-41` = warn 0.005 / fail 0.02 `ENG/Layers_Short_SOT/00_parameters_eng.md:61` = volume_zero_bars/rows: OK ≤0.5% · WARN >0.5% i ≤2% · FAIL >2%                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | ✅ OK           | Zgodne (0.005=0.5%, 0.02=2%).                                                                                                                                                                                                                                                                                      |
| l8.zero_range_warn_fraction / zero_range_fail_fraction                                                                                                   | `config/params.json:42-43` = warn 0.005 / fail 0.02 `ENG/Layers_Short_SOT/00_parameters_eng.md:62` = zero_range_bars/rows: OK ≤0.5% · WARN >0.5% i ≤2% · FAIL >2%                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | ✅ OK           | Zgodne.                                                                                                                                                                                                                                                                                                            |
| l8.det09_rejected_warn_fraction                                                                                                                          | `config/params.json:44` = "det09_rejected_warn_fraction": 0.2 `ENG/Layers_Short_SOT/00_parameters_eng.md:63` = det09_rejected rate: OK ≤20% · WARN >20% (WARN max, diagnostic)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | ✅ OK           | Zgodne (0.2 = 20%).                                                                                                                                                                                                                                                                                                |
| Optuna hyperparameter search space (max_depth, learning_rate, n_estimators, min_child_weight, subsample, colsample_bytree, reg_lambda, scale_pos_weight) | `viz/main_data_flow.html:356-358` = max_depth:'3–9', learning_rate:'0.01–0.3 (log)', n_estimators:'100–1200', min_child_weight:'1–20', subsample:'0.5–1.0', colsample_bytree:'0.5–1.0', reg_lambda:'1e-3–10 (log)', scale_pos_weight:'0.5–4' `viz/main_data_flow.html:1782` = search space: depth 3–9 · lr 0.01–0.3 log · estimators 100–1200 · subsample/colsample 0.5–1 · λ 1e-3–10 · spw 0.5–4 `config/params.json:1-46` = BRAK — params.json nie zawiera przestrzeni przeszukiwania `ENG/Layers_Short_SOT/00_parameters_eng.md:1-67` = BRAK — SOT nie definiuje zakresów hiperparametrów `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:6-18` = BRAK — definiuje tylko budget/sampler/pruner/objective, bez zakresów space                                                                                                                                                                                                          | 🔶 NIEOSADZONE | Viz wprowadza pełną przestrzeń przeszukiwania jako konkretne fakty liczbowe, których SOT (params.json ani 00_parameters ani L9) nigdzie nie definiuje → naruszenie 'one home per fact' + ryzyko driftu.                                                                                                            |
| Optuna objective + pruner n_warmup_steps + k=4 (cytowane w viz)                                                                                          | `viz/main_data_flow.html:355` = objective:'AUC-PR (mean over k=4 purged walk-forward folds on Train)' `viz/main_data_flow.html:354` = pruner:'MedianPruner(n_warmup_steps=2)' `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:11-12` = pruner: MedianPruner (`n_warmup_steps=2`); objective: AUC-PR over purged walk-forward CV (k=4 folds), in Train only `acceptance_data_transform_cards/L09_Optuna_XGBoost_Card.md:22` = Objective: AUC-PR, purged walk-forward k=4                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | ✅ OK           | Zgodne z SOT L9 (objective AUC-PR, n_warmup_steps=2, k=4). To poprawne cytowanie SOT, nie redefinicja.                                                                                                                                                                                                             |


### Oś C — Liczby globalne (503/510/8 841 820/×10000/rozmiary)

**Werdykt:** Oś C jest w bardzo dobrym stanie wartościowym: wszystkie liczby globalne (503, 510, 8 841 820, ×10000, 139 MB, 166 MB, ~7/[5,9]) są zgodne z SOT i nie ma realnej rozbieżności wartości; jedyne zastrzeżenia to drobne niespójności prezentacji formatowania liczby wierszy (8 841 820 vs 8.84M vs 8841820) i zakresu świec ([5, 9] vs [5,9]) w viz oraz strukturalna luka SOT — blok "Global numbers" w 00_conventions nie wymienia rozmiarów 139 MB/166 MB, których jedynym domem są L2/L3.  
**Statusy wierszy:** ✅5 · ⚠️2


| Fakt                                                                   | Źródła (`plik:linia` = wartość)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Status    | Uwaga                                                                                                                                                                                                                                                                                                                  |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 503 = liczba tickerów uniwersum S&P 500 (lista w config/universe.txt)  | `ENG/Layers_Short_SOT/00_conventions_eng.md:34` = **503** — S&P 500 universe tickers (list pinned in `config/universe.txt`). `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:11` = symbol count: 503 (ticker list: file `config/universe.txt`) `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:17` = 503 symbols `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:31` = universe complete: 503/503 symbols `config/universe.txt:1-503` = wc -l = 503, awk NR = 503, grep -c . = 503, trailing newline present (0a po ZTS) `acceptance_data_transform_cards/L01_Source_Alpaca_Card.md:11,14,26,32` = 503 S&P 500 tickers / config/universe.txt (503 tickers) / 503 tickers / 503 tickers downloaded `acceptance_data_transform_cards/L02_Lean_Zip_Store_Card.md:32` = 503 universe + extras `acceptance_data_transform_cards/L03_DuckDB_Raw_View_QC_Card.md:15,32,47` = 503 symbols `acceptance_data_transform_cards/L08_Data_Quality_Gate_Card.md:36,48` = 503 symbols / 503×metrics `acceptance_data_transform_cards/00_Crosscutting_Overview_Card.md:9,33,45` = 503 tickers / 503 (uniwersum) `viz/main_data_flow.html:300` = var N_ASSETS=503; `viz/main_data_flow.html:7,243,251,391,429,433,449,452,457,490,493,789,2012` = 503 (tytuł, listy, węzły L1/L4/L10, panele) | ✅ OK      | wc -l = 503 i awk NR = 503 zgodnie; plik MA końcowy newline (ostatni bajt 0a po ZTS), więc brak ryzyka 'off-by-one' z brakującym newline. Wszystkie artefakty podrzędne cytują SOT wiernie.                                                                                                                            |
| 510 = liczba plików ZIP LEAN (503 uniwersum + kilku non-constituents)  | `ENG/Layers_Short_SOT/00_conventions_eng.md:35` = **510** — LEAN zip files = 503 universe tickers + a few non-constituents. `ENG/Layers_Short_SOT/L2_lean_zip_store_eng.md:5,7` = The raw store is 510 ZIP files. / 510 = 503 universe tickers + a few non-constituents `acceptance_data_transform_cards/L01_Source_Alpaca_Card.md:15,32,46` = 510 ZIP files / 510 ZIPs created / 510 ZIP folder icons `acceptance_data_transform_cards/L02_Lean_Zip_Store_Card.md:11,15,26,32,46` = 510 ZIPs, 139 MB / 510 .zip / Exactly 510 ZIPs, 503 universe + extras / '510 ZIPs' `acceptance_data_transform_cards/L03_DuckDB_Raw_View_QC_Card.md:14` = 510 ZIPs from L2 `viz/main_data_flow.html:169,244,436,439,444,500,848,1588,1876` = 510 (sr-only, lista, węzeł L2, edge L2→L3, badge ×510)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | ✅ OK      | Definicja 510 = 503 + non-constituents identyczna w obu plikach SOT (00_conventions i L2) oraz powtórzona w kartach/viz; brak rozbieżności.                                                                                                                                                                            |
| 8 841 820 = liczba wierszy w raw_ohlcv_1h                              | `ENG/Layers_Short_SOT/00_conventions_eng.md:36` = **8 841 820** — rows in `raw_ohlcv_1h` (503 symbols). `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:10` = row count: 8 841 820 `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:17` = 8 841 820 rows `acceptance_data_transform_cards/L02_Lean_Zip_Store_Card.md:15,47` = total 8 841 820 rows across all / '139 MB · 8 841 820 rows' `acceptance_data_transform_cards/L03_DuckDB_Raw_View_QC_Card.md:15,32,47` = 8 841 820 rows `acceptance_data_transform_cards/L08_Data_Quality_Gate_Card.md:36` = Reference targets from v1 (8 841 820 rows, 503 symbols) `acceptance_data_transform_cards/00_Crosscutting_Overview_Card.md:9,33,45` = 8 841 820 timestamped rows `viz/main_data_flow.html:329,391,443,500,862,1589,1860,2015,2062,2064` = 8 841 820 rows (spacje cienkie jako separator) `viz/main_data_flow.html:446` = metric:{label:'rows',value:'8.84M'} `viz/main_data_flow.html:2065,2081` = rows:8841820 (snapshot manifest + summary.json counters)                                                                                                                                                                                                                                                            | ⚠️ RYZYKO | Wartość zawsze ta sama (8841820); nigdzie nie ma formatu z przecinkami 8,841,820. Trzy formy prezentacji w viz: '8 841 820' (dominująca, zgodna z SOT), '8.84M' (zaokrąglony badge, linia 446) i '8841820' (literały JSON, linie 2065/2081). To niespójność prezentacji/zaokrąglenia, nie rozbieżność faktu.           |
| ×10000 = skala przechowywania cen (deci-cents) w LEAN/raw_ohlcv_1h     | `ENG/Layers_Short_SOT/00_conventions_eng.md:37` = **×10000** — price storage scale in the LEAN archive / `raw_ohlcv_1h` table (deci-cents). `ENG/Layers_Short_SOT/L2_lean_zip_store_eng.md:12` = prices: integers ×10000 (deci-cents; e.g. `$185.12 → 1851200`) `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:8,12` = open/high/low/close BIGINT ×10000 / VIEW ohlcv_1h (= prices `/10000.0`) `acceptance_data_transform_cards/L01_Source_Alpaca_Card.md:15,33` = open×10000,… / ×10000 integer prices `acceptance_data_transform_cards/L02_Lean_Zip_Store_Card.md:11,15,27,33,46` = prices ×10000 (integers ×10000) `acceptance_data_transform_cards/L03_DuckDB_Raw_View_QC_Card.md:15` = price /10000 `viz/main_data_flow.html:244,245,436,437,439,440,445,498,500,850,860,868,1588,1594,2014,2015,2016,2061,2062,2063` = ×10000 / /10000.0 (deci-cents, BIGINT, VIEW USD)                                                                                                                                                                                                                                                                                                                                                                                                    | ✅ OK      | Skala ×10000 i jej odwrotność /10000.0 spójne we wszystkich plikach; przykład $185.12 → 1851200 (L2) potwierdzony w sample-rowach viz (1851200). Brak rozbieżności.                                                                                                                                                    |
| 139 MB = całkowity rozmiar archiwum 510 ZIP                            | `ENG/Layers_Short_SOT/L2_lean_zip_store_eng.md:8` = total size: 139 MB `acceptance_data_transform_cards/L02_Lean_Zip_Store_Card.md:11,21,47` = 510 ZIPs, 139 MB / Size reference: 139 MB total / '139 MB · 8 841 820 rows' `viz/main_data_flow.html:244,437,500,850,1588` = 139 MB                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | ✅ OK      | Wartość 139 MB spójna wszędzie. Uwaga strukturalna: blok 'Global numbers (agree everywhere)' w 00_conventions:32-38 NIE wymienia rozmiaru 139 MB — jedynym domem faktu jest L2:8. Karty/viz cytują L2, więc fakt MA dom (status OK), ale dom rozmiarów leży poza centralnym blokiem global-numbers — patrz finding C3. |
| 166 MB = rozmiar bazy DuckDB                                           | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:17` = database 166 MB `acceptance_data_transform_cards/L03_DuckDB_Raw_View_QC_Card.md:15,32,47` = *.duckdb (166 MB) / 166 MB DB / '… 166 MB' `viz/main_data_flow.html:862,2015` = 166 MB                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | ✅ OK      | Wartość 166 MB spójna. Jedyny dom = L3:17 (Key numbers). Tak jak 139 MB, rozmiar nie jest wymieniony w centralnym bloku global-numbers 00_conventions — patrz finding C3.                                                                                                                                              |
| ~7 świec/dzień sesji RTH (09:00–16:00 ET); zakres candles/day ∈ [5, 9] | `ENG/Layers_Short_SOT/00_conventions_eng.md:38` = **~7** — 1h candles per RTH session day (09:00–16:00 ET); candles/day ∈ [5, 9]. `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:32` = candles per day `∈ [5, 9]` `acceptance_data_transform_cards/L01_Source_Alpaca_Card.md:26` = RTH 09:00–16:00 ET only, ~7 candles/day `viz/main_data_flow.html:324` = desc:'candles per day ∈ [5,9]' `viz/main_data_flow.html:243,430,498,814` = ~7 candles/day (session 09:00–16:00 ET)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | ⚠️ RYZYKO | Wartości ~7 i zakres [5,9] zgodne. Drobna niespójność prezentacji: SOT pisze '[5, 9]' (spacja po przecinku), viz:324 pisze '[5,9]' (bez spacji). Czysto kosmetyczne.                                                                                                                                                   |


### Oś D — Tożsamość warstw (nazwy/kolejność/liczba)

**Werdykt:** Oś w bardzo dobrym stanie: liczba warstw (10), kolejność L1→L10 i liczba krawędzi/separatorów (9) są spójne we wszystkich artefaktach (SOT, viz, karty, generator PDF, glosariusz); jedyne rozbieżności to wariantowe krótkie nazwy warstwy L8 ("Validation" vs "Data-quality gate" vs "Quality validation/QUALITY VALIDATION") — istnieje też wewnętrzna niespójność samego SOT dla L8 — oraz drobne ryzyka driftu w hardcodowanej liście kolejności/ALL-CAPS tytułach viz.  
**Statusy wierszy:** ✅17 · ❌1 · ⚠️3


| Fakt                                                                                                                                                                                      | Źródła (`plik:linia` = wartość)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Status      | Uwaga |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ----- |
| Liczba warstw pipeline'u = 10 (L1..L10)                                                                                                                                                   | `ENG/Layers_Short_SOT/README.md:32-43` = L1..L10 (10 wierszy) `ENG/Layers_Short_SOT/00_conventions_eng.md:25` = L1–L10 (Detector = L6, Features = L7, Validation = L8, Optuna = L9, OOS = L10) `viz/main_data_flow.html:427-495` = 10 węzłów id L1..L10 `viz/main_data_flow.html:169` = Ten levels from the bottom `acceptance_data_transform_cards/generate_master_layer_cards_pdf.py:17-29` = 00 + L01..L10 (11 plików, 10 warstw) `ENG/glossary_eng.md:33-139` = ## L1 .. ## L10 (10 sekcji) `README_A_Layer.md:1-4` = layers L1–L10                                                                                                            | ✅ OK        |       |
| Liczba krawędzi przepływu = 9 (L1→L2 … L9→L10)                                                                                                                                            | `viz/main_data_flow.html:496-515` = 9 krawędzi from/to: L1→L2…L9→L10 `viz/main_data_flow.html:418` = 9 boundaries (10 levels): inserted L6 detector boundary `viz/main_data_flow.html:418` = [189,189,192,189,189,189,185,189,202] = 9 wartości `ENG/Layers_Short_SOT/L8_data_quality_eng.md:9-18` = zip→DuckDB→parquet→Output B (3 hopy parzystości na łańcuchu warstw)                                                                                                                                                                                                                                                                           | ✅ OK        |       |
| Kolejność warstw lev = 0..9 odpowiada L1..L10 (ciągła, bez przestawień)                                                                                                                   | `viz/main_data_flow.html:428-494` = lev:0..lev:9 w kolejności L1..L10 `ENG/Layers_Short_SOT/00_conventions_eng.md:25` = Avoid: L1–L9; out-of-order layers `ENG/glossary_eng.md:9` = Order = layer by layer (L1 → L10)                                                                                                                                                                                                                                                                                                                                                                                                                              | ✅ OK        |       |
| Tytuł L1 — Source: Alpaca SIP / S&P 500 (503)                                                                                                                                             | `ENG/Layers_Short_SOT/L1_source_alpaca_eng.md:1` = # L1 · Source: Alpaca (SOT) `viz/main_data_flow.html:429` = SOURCE: ALPACA SIP · S&P 500 (503) `acceptance_data_transform_cards/L01_Source_Alpaca_Card.md:1` = L1 · Source: Alpaca — Master Layer Card `ENG/glossary_eng.md:33` = L1 · Source: Alpaca SIP · S&P 500 (503)                                                                                                                                                                                                                                                                                                                       | ✅ OK        |       |
| Tytuł L2 — LEAN ZIP store (510 zip · prices ×10000)                                                                                                                                       | `ENG/Layers_Short_SOT/L2_lean_zip_store_eng.md:1` = # L2 · LEAN ZIP store (SOT) `viz/main_data_flow.html:436` = LEAN ZIP STORE (510 zip · prices ×10000) `acceptance_data_transform_cards/L02_Lean_Zip_Store_Card.md:1` = L2 · LEAN ZIP Store — Master Layer Card `ENG/glossary_eng.md:43` = L2 · LEAN ZIP store (510 zip · prices ×10000)                                                                                                                                                                                                                                                                                                         | ✅ OK        |       |
| Tytuł L3 — DuckDB raw + VIEW ohlcv_1h (USD) · QC-01…QC-11                                                                                                                                 | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:1` = # L3 · DuckDB + VIEW ohlcv_1h + QC-01…QC-11 (SOT) `viz/main_data_flow.html:442` = DUCKDB raw + VIEW ohlcv_1h (USD) · QC-01…QC-11 `acceptance_data_transform_cards/L03_DuckDB_Raw_View_QC_Card.md:1` = L3 · DuckDB + VIEW ohlcv_1h + QC-01…QC-11 — Master Layer Card `ENG/glossary_eng.md:53` = L3 · DuckDB: raw + VIEW ohlcv_1h (USD) · QC-01…QC-11                                                                                                                                                                                                                                        | ✅ OK        |       |
| Tytuł L4 — Snapshot → parquet OHLCV (×503)                                                                                                                                                | `ENG/Layers_Short_SOT/L4_snapshot_parquet_eng.md:1` = # L4 · Snapshot → parquet OHLCV (SOT) `viz/main_data_flow.html:449` = SNAPSHOT → PARQUET OHLCV (×503) `acceptance_data_transform_cards/L04_Snapshot_Parquet_Card.md:1` = L4 · Snapshot → Parquet OHLCV — Master Layer Card `ENG/glossary_eng.md:65` = L4 · Snapshot → parquet OHLCV per ticker                                                                                                                                                                                                                                                                                               | ✅ OK        |       |
| Tytuł L5 — Split: WARM-UP / TRAIN / OOS (+ purge/embargo)                                                                                                                                 | `ENG/Layers_Short_SOT/L5_time_split_eng.md:1` = # L5 · Time split (SOT) `viz/main_data_flow.html:455` = SPLIT: WARM-UP / TRAIN / OOS `acceptance_data_transform_cards/L05_Time_Split_Card.md:1` = L5 · Time Split — Master Layer Card `ENG/glossary_eng.md:76` = L5 · Split: warm-up / train / OOS (+ purge / embargo)                                                                                                                                                                                                                                                                                                                             | ✅ OK        |       |
| Tytuł L6 — Trend-line setup detector (OUTPUT contract)                                                                                                                                    | `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:1` = # L6 · Trend-line setup detector — OUTPUT contract (SOT) `viz/main_data_flow.html:462` = TREND-LINE SETUP DETECTOR `acceptance_data_transform_cards/L06_Setup_Detector_Card.md:1` = L6 · Trend-line Setup Detector (OUTPUT Contract) — Master Layer Card `ENG/glossary_eng.md:87` = L6 · Trend-line setup detector                                                                                                                                                                                                                                                                             | ✅ OK        |       |
| Tytuł L7 — Features X + label Y (triple barrier)                                                                                                                                          | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:1` = # L7 · Features X + label Y (SOT) `viz/main_data_flow.html:469` = FEATURES X + LABEL Y (TRIPLE BARRIER) `acceptance_data_transform_cards/L07_Features_X_Label_Y_Card.md:1` = L7 · Features X + Label Y — Master Layer Card `ENG/glossary_eng.md:100` = L7 · Features X + label Y (triple barrier)                                                                                                                                                                                                                                                                                          | ✅ OK        |       |
| Tytuł/krótka nazwa L8 — niejednolite warianty (Validation / Data-quality gate / Quality validation / QUALITY VALIDATION)                                                                  | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:1` = # L8 · Data-quality gate (SOT) `ENG/Layers_Short_SOT/00_conventions_eng.md:25` = Validation = L8 `ENG/Layers_Short_SOT/README.md:41` = L8_data_quality_eng.md `viz/main_data_flow.html:476` = QUALITY VALIDATION: STORES + TRANSFORMS `acceptance_data_transform_cards/L08_Data_Quality_Gate_Card.md:1` = L8 · Data Quality Gate — Master Layer Card `ENG/glossary_eng.md:113` = L8 · Quality validation: stores + transforms (dashboard)                                                                                                                                                        | ❌ ROZBIEŻNE |       |
| Tytuł L9 — Optuna → XGBoost → strategy .py                                                                                                                                                | `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:1` = # L9 · Optuna → XGBoost → strategy .py (SOT) `viz/main_data_flow.html:483` = OPTUNA → XGBOOST → STRATEGY .py `acceptance_data_transform_cards/L09_Optuna_XGBoost_Card.md:1` = L9 · Optuna → XGBoost → strategy.py — Master Layer Card `ENG/glossary_eng.md:122` = L9 · Optuna → XGBoost → strategy .py (base64)                                                                                                                                                                                                                                                                                | ✅ OK        |       |
| Tytuł L10 — OOS test: 503 assets × metrics                                                                                                                                                | `ENG/Layers_Short_SOT/L10_oos_test_eng.md:1` = # L10 · OOS test (SOT) `viz/main_data_flow.html:490` = OOS TEST: 503 ASSETS × METRICS `acceptance_data_transform_cards/L10_OOS_Test_Card.md:1` = L10 · OOS Test — Master Layer Card `ENG/glossary_eng.md:132` = L10 · OOS test: 503 assets × metrics                                                                                                                                                                                                                                                                                                                                                | ✅ OK        |       |
| Traktowanie warstwy '00 Crosscutting' (cross-cutting nie jest numerowaną warstwą L; w SOT to 4 pliki 00_*, w kartach 1 karta zbiorcza, w viz brak węzła, w glosariuszu sekcja bez numeru) | `ENG/Layers_Short_SOT/README.md:23-28` = 4 pliki: 00_conventions / 00_parameters / 00_input_contract / 00_definition_of_done `acceptance_data_transform_cards/00_Crosscutting_Overview_Card.md:1` = 00 · Cross-Cutting Facts Overview — Master Layer Card `acceptance_data_transform_cards/README_cards.md:20` = 00_Crosscutting_Overview_Card.md — master card covering 00_ files (conventions, parameters, input contract, DoD) `README_A_Layer.md:13` = 11 cards (L1–L10 + 00 overview) `ENG/glossary_eng.md:17` = ## Cross-cutting concepts (view `0 Anti-leakage`) `viz/main_data_flow.html:427-495` = tylko 10 węzłów L1..L10, brak węzła 00 | ✅ OK        |       |
| Lista CARD_FILES w generatorze PDF = 11 plików w kolejności 00, L01..L10                                                                                                                  | `acceptance_data_transform_cards/generate_master_layer_cards_pdf.py:17-29` = 00_Crosscutting_Overview_Card.md, L01..L10 (11 pozycji, overview first) `acceptance_data_transform_cards/generate_master_layer_cards_pdf.py:53` = Page {page_no} / 11 `README_A_Layer.md:13` = 11 cards `acceptance_data_transform_cards/` = 00 + L01..L10 = 11 plików .md (+ template, README, PDF)                                                                                                                                                                                                                                                                  | ✅ OK        |       |
| Ekstrakcja tytułu karty w generatorze PDF zależy od obecności łańcucha 'Master Layer Card' w linii nagłówka #                                                                             | `acceptance_data_transform_cards/generate_master_layer_cards_pdf.py:62-65` = if line.startswith('# ') and 'Master Layer Card' in line: title = ... `acceptance_data_transform_cards/L01_Source_Alpaca_Card.md:1` = # L1 · Source: Alpaca — Master Layer Card (Acceptance Form) `acceptance_data_transform_cards/00_Crosscutting_Overview_Card.md:1` = # 00 · Cross-Cutting Facts Overview — Master Layer Card (Acceptance Form)                                                                                                                                                                                                                    | ⚠️ RYZYKO   |       |
| Kolejność warstw w viz jest sterowana 3 hardcodowanymi, równoległymi listami (nodes lev, MODE_KEYS, BND_DZ) bez asercji długości                                                          | `viz/main_data_flow.html:529` = ['overview','dataflow','qc','split','setup','dq','optuna','artifact','oos','leak'] (10 trybów) `viz/main_data_flow.html:418` = 9 wartości offsetu, 1:1 do krawędzi `viz/main_data_flow.html:428-494` = lev:0..9 wpisane ręcznie w każdym węźle `viz/main_data_flow.html:176-185` = 10 przycisków 1..9,0                                                                                                                                                                                                                                                                                                            | ⚠️ RYZYKO   |       |
| Tytuły warstw w viz są ALL-CAPS scene captions (np. 'TREND-LINE SETUP DETECTOR'), redagowane niezależnie od nagłówków plików SOT                                                          | `viz/main_data_flow.html:423` = title WITHOUT the 'Lx · ' prefix — caption() appends the number from lev `viz/main_data_flow.html:429-490` = wszystkie title w ALL-CAPS `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:1` = mixed-case '# L6 · Trend-line setup detector — OUTPUT contract'                                                                                                                                                                                                                                                                                                                                                        | ⚠️ RYZYKO   |       |
| Rezerwacja schematu: L1–L10 tylko dla Pipeline A; cechy używają Stages F0–F14 (nie L#)                                                                                                    | `ENG/Layers_Short_SOT/00_conventions_eng.md:29-30` = layer / L1–L10 belong to Pipeline A only … Stages F0–F14 … never L# `ENG/Layers_Short_SOT/README.md:73-74` = Stages F0–F14 … not part of this SOT `README_A_Layer.md:16-17` = Stages F0–F14, never L# `ENG/glossary_eng.md:150-152` = own Stage scheme F0–F14 (never L#)                                                                                                                                                                                                                                                                                                                      | ✅ OK        |       |
| Nazwy trybów widoku viz cytowane przez glosariusz zgadzają się z przyciskami viz (1 Overview, 0 Anti-leakage, 5 Setup geometry)                                                           | `ENG/glossary_eng.md:9-10` = the `1 Overview` view of viz/main_data_flow.html `ENG/glossary_eng.md:17` = Cross-cutting concepts (view `0 Anti-leakage`) `viz/main_data_flow.html:176-185` = 1 Overview … 5 Setup geometry … 0 Anti-leakage                                                                                                                                                                                                                                                                                                                                                                                                         | ✅ OK        |       |
| README_cards odwołuje się do konkretnych Stage'ów F (F1/F7/F8/F11) i 'Stages_Short_SOT' jako matchujących fakty L                                                                         | `acceptance_data_transform_cards/README_cards.md:31` = F-stages (F1/F7/F8/F11) directly inline the L5/L7/L8/L10 facts `ENG/Layers_Short_SOT/00_conventions_eng.md:30` = Stages F0–F14                                                                                                                                                                                                                                                                                                                                                                                                                                                              | ✅ OK        |       |


### Oś E — Split czasowy (daty/purge/embargo/CV)

**Werdykt:** Oś E jest w bardzo dobrym stanie: wszystkie 6 dat splitu, PURGE_CANDLES=H=24, EMBARGO_SESSIONS=5 (~35 świec) i CV_SCHEME=purged_walk_forward są 1:1 zgodne między params.json, SOT, kartą i viz, a asercja granicy oraz frac w viz weryfikują się arytmetycznie; jedyne zastrzeżenia to dwie wewnętrzne nieścisłości SOT (fold count k=4 oraz blok splits/oos-frac bez czystego domu w rejestrze parametrów / w params.json).  
**Statusy wierszy:** ✅16 · ⚠️1 · 🔶1


| Fakt                                                                                    | Źródła (`plik:linia` = wartość)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Status         | Uwaga                                                                                                                                                                                                                                                                                                       |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| warmup_start = 2016-01-04                                                               | `config/params.json:21` = "warmup_start": "2016-01-04" `ENG/Layers_Short_SOT/L5_time_split_eng.md:7` = WARM-UP window: 2016-01-04 → 2016-10-14 `acceptance_data_transform_cards/L05_Time_Split_Card.md:21` = Warm-up: 2016-01-04 → 2016-10-14 (W=20) `viz/main_data_flow.html:333` = {id:'warmup',...from:'2016-01-04',to:'2016-10-14',frac:0.075                                                                                                                                                                                                                                           | ✅ OK           | Identyczna we wszystkich źródłach; karta i viz cytują SOT/params.json bez redefinicji.                                                                                                                                                                                                                      |
| warmup_end = 2016-10-14                                                                 | `config/params.json:22` = "warmup_end": "2016-10-14" `ENG/Layers_Short_SOT/L5_time_split_eng.md:7` = WARM-UP window: 2016-01-04 → 2016-10-14 `acceptance_data_transform_cards/L05_Time_Split_Card.md:21` = Warm-up: ... → 2016-10-14 (W=20) `viz/main_data_flow.html:333` = to:'2016-10-14' `viz/main_data_flow.html:963` = key:'split_axis_warmend',date:'2016-10-14'                                                                                                                                                                                                                      | ✅ OK           | Zgodna wszędzie; viz dodatkowo używa jej jako etykiety osi czasu (bez redefinicji).                                                                                                                                                                                                                         |
| train_start = 2016-10-17                                                                | `config/params.json:23` = "train_start": "2016-10-17" `ENG/Layers_Short_SOT/L5_time_split_eng.md:10` = TRAIN window: 2016-10-17 → 2023-12-29 `acceptance_data_transform_cards/L05_Time_Split_Card.md:22` = Train: 2016-10-17 → 2023-12-29 `viz/main_data_flow.html:335` = {id:'train',...from:'2016-10-17',to:'2023-12-29',frac:0.695 `viz/main_data_flow.html:413` = train:'2016-10-17 → 2023-12-29'                                                                                                                                                                                       | ✅ OK           | Identyczna we wszystkich źródłach.                                                                                                                                                                                                                                                                          |
| train_end = 2023-12-29                                                                  | `config/params.json:24` = "train_end": "2023-12-29" `ENG/Layers_Short_SOT/L5_time_split_eng.md:10` = TRAIN window: 2016-10-17 → 2023-12-29 `acceptance_data_transform_cards/L05_Time_Split_Card.md:22` = Train: 2016-10-17 → 2023-12-29 `viz/main_data_flow.html:335` = to:'2023-12-29' `viz/main_data_flow.html:964` = date:'2023-12-29 → 2024-01-02'                                                                                                                                                                                                                                      | ✅ OK           | Zgodna; viz oznacza ją jako granicę Train→OOS (kolor SL).                                                                                                                                                                                                                                                   |
| oos_start = 2024-01-02                                                                  | `config/params.json:25` = "oos_start": "2024-01-02" `ENG/Layers_Short_SOT/L5_time_split_eng.md:12` = OOS window: 2024-01-02 → 2026-05-29, frozen `ENG/Layers_Short_SOT/L10_oos_test_eng.md:7` = single run over the OOS window 2024-01-02 → 2026-05-29 `acceptance_data_transform_cards/L05_Time_Split_Card.md:23` = OOS: 2024-01-02 → 2026-05-29 (frozen) `viz/main_data_flow.html:337` = {id:'oos',...from:'2024-01-02',to:'2026-05-29',frac:0.230                                                                                                                                        | ✅ OK           | Identyczna; pojawia się też w L10, manifest i opisach OOS w viz (514, 491, 1209, 2078) — wszystkie zgodne.                                                                                                                                                                                                  |
| oos_end = 2026-05-29                                                                    | `config/params.json:26` = "oos_end": "2026-05-29" `ENG/Layers_Short_SOT/L5_time_split_eng.md:12` = OOS window: 2024-01-02 → 2026-05-29, frozen `ENG/Layers_Short_SOT/L10_oos_test_eng.md:7` = OOS window 2024-01-02 → 2026-05-29 `acceptance_data_transform_cards/L05_Time_Split_Card.md:23` = OOS: ... → 2026-05-29 (frozen) `viz/main_data_flow.html:337` = to:'2026-05-29'                                                                                                                                                                                                               | ✅ OK           | Zgodna wszędzie (viz 337, 413, 414? n/d, 491, 514, 2078); brak rozbieżności.                                                                                                                                                                                                                                |
| PURGE_CANDLES = H = 24                                                                  | `config/params.json:13` = "PURGE_CANDLES": 24 `ENG/Layers_Short_SOT/00_parameters_eng.md:22` = PURGE_CANDLES | H (= 24) | purge at window boundaries `ENG/Layers_Short_SOT/L5_time_split_eng.md:14` = Purge (PURGE_CANDLES = H = 24): ... [t0, t0+H] crosses a window boundary is removed `acceptance_data_transform_cards/L05_Time_Split_Card.md:11` = purge (H=24) ... PURGE_CANDLES=24 `viz/main_data_flow.html:339` = purge = H = 24 candles                                                                                                                                            | ✅ OK           | Wartość 24 i tożsamość PURGE_CANDLES=H spójne; viz node L5 invariants 'purge = H = 24' (459) oraz opisy 247/456/504/988/1625 zgodne.                                                                                                                                                                        |
| EMBARGO_SESSIONS = 5 (≈ 35 świec)                                                       | `config/params.json:14` = "EMBARGO_SESSIONS": 5 `ENG/Layers_Short_SOT/00_parameters_eng.md:23` = EMBARGO_SESSIONS | 5 | embargo after the Train→OOS boundary (≈ 35 candles) `ENG/Layers_Short_SOT/L5_time_split_eng.md:16` = Embargo (EMBARGO_SESSIONS = 5 ≈ 35 candles) `acceptance_data_transform_cards/L05_Time_Split_Card.md:11` = embargo (5 sess); ... EMBARGO=5 sessions `viz/main_data_flow.html:340` = embargo ≈ 5 sessions (~35 candles)                                                                                                                                          | ✅ OK           | 5 sesji ≈ 35 świec (5×~7) potwierdzone L1:14 i 00_conventions:38; karta podaje '5 sessions' (podzbiór, bez redefinicji); viz 247/456/953/1627 zgodne.                                                                                                                                                       |
| Embargo ≥ max feature lookback (20 świec): 35 ≥ 20                                      | `ENG/Layers_Short_SOT/L5_time_split_eng.md:17` = 5 sessions ≈ 35 candles ≥ max feature lookback (20 candles) `viz/main_data_flow.html:340` = covers max feature lookback (20 candles) `viz/main_data_flow.html:399` = embargo 5 sessions ≥ lookback 20 candles                                                                                                                                                                                                                                                                                                                              | ✅ OK           | Lookback 20 = max(W_ATR=14, W_VOL=20); spójne w SOT (L5:8) i viz (459 'embargo ≥ lookback (20 candles)').                                                                                                                                                                                                   |
| CV_SCHEME = purged_walk_forward                                                         | `config/params.json:16` = "CV_SCHEME": "purged_walk_forward" `ENG/Layers_Short_SOT/00_parameters_eng.md:25` = CV_SCHEME | purged_walk_forward | CV inside Train (folds with purge+embargo) `ENG/Layers_Short_SOT/L5_time_split_eng.md:19` = Purged walk-forward CV (CV_SCHEME) separates the folds inside Train `acceptance_data_transform_cards/L05_Time_Split_Card.md:15` = CV scheme (purged walk-forward k=4) `viz/main_data_flow.html:336` = Optuna (purged walk-forward CV)                                                                                                           | ✅ OK           | Schemat zgodny; karta i viz cytują SOT. Liczność foldów k=4 traktowana w osobnym wierszu.                                                                                                                                                                                                                   |
| Liczba foldów CV: k = 4                                                                 | `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:12` = AUC-PR over purged walk-forward CV (k=4 folds), in Train only `ENG/Layers_Short_SOT/L5_time_split_eng.md:19` = separates the folds inside Train (bez podania k) `config/params.json:16` = brak klucza k / n_folds / CV_FOLDS `acceptance_data_transform_cards/L05_Time_Split_Card.md:15` = purged walk-forward k=4 `viz/main_data_flow.html:355` = mean over k=4 purged walk-forward folds on Train                                                                                                                                    | ⚠️ RYZYKO      | k=4 zdefiniowane jedynie jako literał w prozie SOT L9, nie w params.json ani w rejestrze 00_parameters (który deklaruje 'this file owns every parameter value'). Karta/viz cytują realny fakt SOT, więc po ich stronie OK — finding dotyczy braku domu liczby k w params.json (ryzyko driftu). Patrz E1.    |
| Karta L05: CV scheme = purged walk-forward k=4                                          | `acceptance_data_transform_cards/L05_Time_Split_Card.md:15` = CV scheme (purged walk-forward k=4) `acceptance_data_transform_cards/L05_Time_Split_Card.md:37` = CV scheme = purged walk-forward (k=4) `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:12` = purged walk-forward CV (k=4 folds)                                                                                                                                                                                                                                                                                               | ✅ OK           | Karta cytuje fakt SOT (k=4 z L9, schemat z 00_parameters/L5) i go nie redefiniuje → zgodna. Ewentualny problem jest po stronie SOT (E1), nie karty.                                                                                                                                                         |
| Asercja granicy: żadne okno [t0, t0+H] nie przecina granicy okna                        | `ENG/Layers_Short_SOT/00_definition_of_done_eng.md:16` = Splits verified by assertion: no label window [t0, t0+H] crosses a Warm-up/Train/OOS boundary (purge + embargo of L5) `ENG/Layers_Short_SOT/L5_time_split_eng.md:22` = Boundary assertion (CI): no [t0, t0+H] window crosses a window boundary `acceptance_data_transform_cards/L05_Time_Split_Card.md:36` = Purge/embargo prevent leakage across boundaries / Verify no label window crosses split (assertion) (krok 4, l.30) `viz/main_data_flow.html:399` = boundary assertion: no window [t0, t0+24] crosses a window boundary | ✅ OK           | Asercja sformułowana spójnie; viz konkretyzuje H=24 jako [t0,t0+24] (zgodne z PURGE_CANDLES=24). DoD i L5 zgodne.                                                                                                                                                                                           |
| Purge operuje na setupach, nie na świecach; indeksy liczone pozycją świecy              | `ENG/Layers_Short_SOT/L5_time_split_eng.md:15` = the purge operates on setups, not on candles `ENG/Layers_Short_SOT/L5_time_split_eng.md:18` = Indices, H and the purge are computed by integer candle position, not by timestamp `viz/main_data_flow.html:1641` = setup with a TB window crossing the boundary → row removed (purge)                                                                                                                                                                                                                                                       | ✅ OK           | viz oddaje semantykę 'na setupach' (row removed); zgodne z SOT.                                                                                                                                                                                                                                             |
| Warm-up roll-in = max(W_ATR=14, W_VOL=20) = 20 świec; wiersze z NULL features odrzucane | `ENG/Layers_Short_SOT/L5_time_split_eng.md:8` = rolls in the rolling windows: max(W_ATR=14, W_VOL=20) = 20 candles `acceptance_data_transform_cards/L05_Time_Split_Card.md:21` = Warm-up: ... (W=20) `viz/main_data_flow.html:334` = max(W_ATR=14, W_VOL=20) = 20 candles 1h → features without NULL                                                                                                                                                                                                                                                                                        | ✅ OK           | W_ATR=14 (params.json:6), W_VOL=20 (params.json:5) → max=20 spójne; karta skrótowo 'W=20', viz pełny wzór. Brak redefinicji.                                                                                                                                                                                |
| viz SPLIT.bands.frac = 0.075 / 0.695 / 0.230 (oraz node L5 'OOS frac'=0.23)             | `viz/main_data_flow.html:333` = warmup frac:0.075 · train frac:0.695 · oos frac:0.230 (l.335/337) `viz/main_data_flow.html:458` = metric:{label:'OOS frac',value:'0.23'} `ENG/Layers_Short_SOT/L5_time_split_eng.md:1` = SOT nie definiuje żadnej wartości frakcji okresów                                                                                                                                                                                                                                                                                                                  | 🔶 NIEOSADZONE | Weryfikacja arytmetyczna: długości kalendarzowe okien dają 0.075 / 0.692 / 0.231 (suma 0.998; viz-owy dord() daje 0.075/0.692/0.231), więc 0.075/0.695/0.230 są spójne w granicach zaokrąglenia i sumują się do 1.0. Wartości są jednak czysto prezentacyjne i NIE mają domu w SOT (kategoria d). Patrz E2. |
| Okna jako indeksy na jednej ciągłej serii (nie osobne pliki parquet)                    | `ENG/Layers_Short_SOT/L5_time_split_eng.md:20` = The windows are indices on one continuous series, not separate parquet files (a fixed design decision) `acceptance_data_transform_cards/L05_Time_Split_Card.md:14` = Out: Windowed series with hard boundaries; purged setup indices                                                                                                                                                                                                                                                                                                       | ✅ OK           | Karta nie redefiniuje; zgodna z decyzją projektową SOT.                                                                                                                                                                                                                                                     |
| OOS frozen / single run / zero tuning after seeing results                              | `ENG/Layers_Short_SOT/L5_time_split_eng.md:13` = one test run; zero tuning after looking at the results `ENG/Layers_Short_SOT/00_definition_of_done_eng.md:18` = OOS one-shot: artifacts frozen before the test; the OOS result never returns to tuning `acceptance_data_transform_cards/L05_Time_Split_Card.md:36` = OOS untouched until L10 one-shot `viz/main_data_flow.html:459` = invariants:['...','OOS frozen'] · L10:494 'single run','zero tuning after seeing results'                                                                                                            | ✅ OK           | Spójne między L5, DoD, kartą i viz.                                                                                                                                                                                                                                                                         |


### Oś F — Detektor L6 (kontrakt + reference algorithm + wartości)

**Werdykt:** Oś F jest w większości spójna: 5 inwariantów, DET-09 (trzy powody odrzucenia, kolejność missing_L_opp przed R0, sufit WARN >20%) oraz wartości detektora (k=3, TOUCH_TOL=0.25, LOOKBACK=120, COOLDOWN=H=24, MIN_TOUCHES=2, W_ATR=14 wilder) są zgodne między SOT, towarzyszem, kartą i config; jedyne realne ryzyka to rozjazd nazewnictwa kluczy config (pivot_k/lookback_candles/cooldown_candles vs symbole SOT k/LOOKBACK/COOLDOWN) bez jawnej tabeli mapowania symbol→klucz w SOT (kat. b) oraz podwójny hardcode cooldown_candles=24 zamiast pochodnej COOLDOWN=H (kat. e).  
**Statusy wierszy:** ✅12 · ⚠️3


| Fakt                                                                                                                                                                                                                  | Źródła (`plik:linia` = wartość)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Status    | Uwaga                                                                                                                                                                                                                                                                                                                                           |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5 inwariantów detektora (line >= MIN_TOUCHES touches before t0; entry = first close break strict >; L_opp exists before t0; fits use only candles <= t0; DET-09 reject+count)                                         | `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:23-29` = ## The 5 invariants the detector must satisfy ... 1. MIN_TOUCHES (=2) touches before t0 ... 5. DET-09: R0<=0/ATR(t0)<=0/missing L_opp rejected and counted `ENG/detector_algorithm_eng.md:368-371` = Invariants (§3) satisfied: (1)...§4; (2)...§6; (3)...§5; (4)...§0/§3/§5; (5) DET-09 rejects+counts...§8 `acceptance_data_transform_cards/L06_Setup_Detector_Card.md:11,32` = own the 5 invariants + DET-09 ... [ ] Every setup satisfies the 5 invariants `viz/main_data_flow.html:466` = invariants:['causal fits (candles <= t0)','MIN_TOUCHES = 2','first break close-based']                                                                           | ✅ OK      | Towarzysz i karta cytują SOT bez redefinicji. viz pokazuje 3 z 5 inwariantów jako etykiety stage'a (subset ilustracyjny, nie redefinicja).                                                                                                                                                                                                      |
| DET-09 trzy powody odrzucenia: R0<=0, ATR(t0)<=0, missing L_opp                                                                                                                                                       | `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:29,33-34` = a setup with R0<=0, ATR(t0)<=0, or a missing L_opp is rejected and counted ... incremented in det09_rejected when any of: R0<=0, ATR(t0)<=0, or L_opp missing `ENG/detector_algorithm_eng.md:206-210` = R0 <= 0 ... ATR(t0) <= 0 ... L_opp missing `ENG/Layers_Short_SOT/L8_data_quality_eng.md:27` = det09_rejected | setups rejected by DET-09 (R0<=0, ATR(t0)<=0, or missing L_opp) `acceptance_data_transform_cards/L06_Setup_Detector_Card.md:22` = DET-09: reject setups with R0 <= 0 / ATR(t0) <= 0 / missing L_opp                                                                                                                                   | ✅ OK      |                                                                                                                                                                                                                                                                                                                                                 |
| Kolejność DET-09: missing_L_opp sprawdzane PRZED R0<=0 (no abs/divide na brakującej linii)                                                                                                                            | `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:33-34` = Ordering guard: missing_L_opp is checked before R0<=0 (no abs on a missing line) `ENG/detector_algorithm_eng.md:217` = the missing_L_opp branch is checked before the R0<=0 branch (no division/abs on a missing line) `ENG/detector_algorithm_eng.md:264-271` = DET-09 (§8): order matters — missing first ... if Lopp is MISSING: audit.missing_L_opp += 1; continue ... if ATR... continue ... if R0<=0...                                                                                                                                                                                                                                                   | ✅ OK      | UWAGA wewnętrzna: w pseudokodzie towarzysza (linie 268-271) po missing_L_opp najpierw sprawdzane jest ATR(t0)<=0, potem R0<=0; w prozie (217) i SOT mowa tylko o relacji missing_L_opp przed R0. Kolejność ATR vs R0 nie jest sprecyzowana w SOT — neutralna (oba odrzucają+liczą), nie tworzy rozbieżności.                                    |
| Sufit DET-09 = WARN-only, próg > 20%, nigdy FAIL                                                                                                                                                                      | `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:35-36` = WARN-only diagnostic on the L8 dashboard (WARN if > 20%, never FAIL) `ENG/Layers_Short_SOT/00_parameters_eng.md:63` = det09_rejected rate | <= 20% | > 20% | never | WARN max (diagnostic) `config/params.json:44` = "det09_rejected_warn_fraction": 0.2 `ENG/detector_algorithm_eng.md:215,392-393` = WARN-only diagnostic at >20% and never FAILs ... WARN >20%, never FAIL (diagnostic): DET-09 rejection rate `ENG/Layers_Short_SOT/L8_data_quality_eng.md:49,99` = det09_rejected rate: WARN-only diagnostic (never FAIL) ... can never raise overall_status to FAIL                                                                                       | ✅ OK      |                                                                                                                                                                                                                                                                                                                                                 |
| Wzór DET-09 rate = det09_rejected / max(1, setups_total + det09_rejected) (guarded denominator)                                                                                                                       | `ENG/Layers_Short_SOT/00_parameters_eng.md:65-66` = the DET-09 rate uses det09_rejected / max(1, setups_total + det09_rejected) `ENG/detector_algorithm_eng.md:392-393` = DET-09 rejection rate = det09_rejected / max(1, setups_total + det09_rejected) (guarded denominator)                                                                                                                                                                                                                                                                                                                                                                                                                                          | ✅ OK      |                                                                                                                                                                                                                                                                                                                                                 |
| k / pivot_k (pivot strength) = 3                                                                                                                                                                                      | `ENG/Layers_Short_SOT/00_parameters_eng.md:39` = | k (pivot strength) | 3 | candles each side | reference design | `config/params.json:29` = "pivot_k": 3 `ENG/detector_algorithm_eng.md:34,85,228,405` = strength k=3 ... confirmed at i+3 ... swing_high_indices(ohlcv, k=3) ... k=3 pivots with i+3 confirmation                                                                                                                                                                                                                                                                                                                                                                                                     | ⚠️ RYZYKO | Wartość zgodna. Klucz config 'pivot_k' (w bloku detector) vs symbol SOT 'k'. SOT 00_parameters NIE podaje jawnej tabeli symbol->klucz JSON (mówi tylko 'Mirrored in config/params.json (detector block)'), więc mapowanie k->pivot_k jest dorozumiane = ryzyko driftu/nazewnictwa. Patrz finding F1.                                            |
| TOUCH_TOL = 0.25 (× ATR(t))                                                                                                                                                                                           | `ENG/Layers_Short_SOT/00_parameters_eng.md:40,44-45` = | TOUCH_TOL | 0.25 | × ATR(t) | ... name reserved by the L6 output contract ... |p_s - L(s)| <= TOUCH_TOL · ATR(s) `config/params.json:19` = "TOUCH_TOL": 0.25 `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:41,43` = the touch test (TOUCH_TOL · ATR(s)) ... Touch tolerance TOUCH_TOL ... see 00_parameters `ENG/detector_algorithm_eng.md:48,60,406` = TOUCH_TOL=0.25 ... |p_s - L(s)| <= TOUCH_TOL · ATR(s) # TOUCH_TOL = 0.25 ... TOUCH_TOL=0.25×ATR                                                                                                                                                                                                       | ✅ OK      | Klucz nazwany identycznie (top-level TOUCH_TOL) w SOT i config; SOT 00_parameters jawnie dokumentuje 'top-level TOUCH_TOL'. Towarzysz wpisuje literał 0.25 w §1/§13, ale w nagłówku §1 (linie 47-53) jawnie deklaruje, że tylko używa symboli i nie re-pinuje wartości; literały to ilustracja, nie definicja — nie traktować jako redefinicji. |
| LOOKBACK / lookback_candles (fit window) = 120 candles                                                                                                                                                                | `ENG/Layers_Short_SOT/00_parameters_eng.md:41` = | LOOKBACK (fit window) | 120 | candles | reference design | `config/params.json:30` = "lookback_candles": 120 `ENG/detector_algorithm_eng.md:49,131,146,238,406` = LOOKBACK=120 ... causal window [t0 - LOOKBACK, t0-3] ... win_lo = max(0, t0 - LOOKBACK) ... LOOKBACK=120                                                                                                                                                                                                                                                                                                                                                                                           | ⚠️ RYZYKO | Wartość zgodna. Klucz config 'lookback_candles' (blok detector) vs symbol SOT 'LOOKBACK'; mapowanie nie jest jawnie wytabelaryzowane w SOT. Patrz finding F1.                                                                                                                                                                                   |
| COOLDOWN / cooldown_candles = H (= 24 candles)                                                                                                                                                                        | `ENG/Layers_Short_SOT/00_parameters_eng.md:42` = | COOLDOWN | H (= 24) | candles | reference design | `config/params.json:31` = "cooldown_candles": 24 `ENG/detector_algorithm_eng.md:49,184,187-188,284,407` = COOLDOWN=H ... suppresses new entries on the same line for COOLDOWN = H = 24 bars ... cooldown_until[...] = t0 + COOLDOWN # = t0 + H ... COOLDOWN=H=24                                                                                                                                                                                                                                                                                                                                                  | ⚠️ RYZYKO | Wartość zgodna dziś (H=24, cooldown_candles=24). DWA ryzyka: (1) nazwa klucza cooldown_candles vs symbol COOLDOWN (kat. b); (2) config pinuje literał cooldown_candles=24 zamiast pochodnej od H — jeśli H zmieni się na inną wartość, SOT mówi COOLDOWN=H, ale config pozostanie 24 (kat. e). Patrz findingi F1, F2.                           |
| MIN_TOUCHES = 2 (minimum touches that validate a line)                                                                                                                                                                | `ENG/Layers_Short_SOT/00_parameters_eng.md:13` = | MIN_TOUCHES | 2 | minimum touches that validate a line | `config/params.json:4` = "MIN_TOUCHES": 2 `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:18,25` = after line validation (>= MIN_TOUCHES touches) ... at least MIN_TOUCHES (= 2) touches before t0 `ENG/detector_algorithm_eng.md:114,403` = require n >= MIN_TOUCHES = 2 ... MIN_TOUCHES=2 (canonical, do not change in F2) `acceptance_data_transform_cards/L06_Setup_Detector_Card.md:33` = MIN_TOUCHES = 2 `viz/main_data_flow.html:466,1705,1797` = MIN_TOUCHES = 2 ... >= MIN_TOUCHES=2 ... PARAMS: ... MIN_TOUCHES=2                                                                                  | ✅ OK      | Klucz nazwany identycznie (MIN_TOUCHES) w SOT i config; wartość 2 spójna we wszystkich źródłach. viz powtarza =2 jako fakt cytujący SOT (nie redefinicja).                                                                                                                                                                                      |
| W_ATR = 14, ATR_VARIANT = wilder, causal, candle t inclusive (jedyne ATR w L6: touch test + DET-09 guard)                                                                                                             | `ENG/Layers_Short_SOT/00_parameters_eng.md:15-16` = | W_ATR | 14 | ATR window | | ATR_VARIANT | wilder | ATR variant (Wilder); window W_ATR, causal, candle t inclusive | `config/params.json:6-7` = "W_ATR": 14, "ATR_VARIANT": "wilder" `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:40-42` = ATR(t) = Wilder, window W_ATR = 14, causal, candle t inclusive ... appears only inside the touch test (TOUCH_TOL · ATR(s)) and the DET-09 guard ATR(t0) > 0 `ENG/detector_algorithm_eng.md:37,70-75,403` = ATR(t) is Wilder, window W_ATR=14 ... Wilder recursion ... W_ATR=14 (canonical); ATR_VARIANT=wilder `viz/main_data_flow.html:304-305,334` = src:'detector + Wilder ATR(14)' ... max(W_ATR=14, W_VOL=20)    | ✅ OK      | Klucze W_ATR i ATR_VARIANT nazwane identycznie w SOT i config; wartości 14/wilder spójne. viz cytuje 'Wilder ATR(14)' jako fakt (nie redefinicja).                                                                                                                                                                                              |
| H (HORIZON) = 24 candles; time_barrier_candle = t0 + H; COOLDOWN = H                                                                                                                                                  | `ENG/Layers_Short_SOT/00_parameters_eng.md:12` = | H (HORIZON_CANDLES) | 24 | time-barrier length in candles (1h => 1 day); tuned | `config/params.json:3` = "H": 24 `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:21` = time_barrier_candle = t0 + H (H = 24 candles) `ENG/detector_algorithm_eng.md:282-284,366,403` = time_barrier_candle: t0 + H # H = 24 ... t0 + H (H=24) ... H=24 (canonical)                                                                                                                                                                                                                                                                                                                   | ✅ OK      | H jest kanoniczne ('tuned'); COOLDOWN jest zdefiniowane jako pochodna H. Spójne. Ryzyko driftu cooldown_candles wobec H ujęte osobno (finding F2).                                                                                                                                                                                              |
| Kontrakt output (per setup): direction(±1), L_trend(t)=a_t·t+b_t, L_opp(t)=a_o·t+b_o, topo_candles, entry_candle(t0), R0=abs(close[t0]-L_opp(t0)), take_profit_level=close[t0]+direction·R0, time_barrier_candle=t0+H | `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:12-21` = tabela Output objects (per setup): direction, L_trend, L_opp, topo_candles, entry_candle, R0, take_profit_level, time_barrier_candle `ENG/detector_algorithm_eng.md:357-367,274-283` = Contract conformance — mapping to L6 ... emit setup (§3 output contract): direction, L_trend, L_opp, topo_candles, entry_candle, R0, take_profit_level, time_barrier_candle `acceptance_data_transform_cards/L06_Setup_Detector_Card.md:15` = Setup objects ... direction (±1), lines, t0, ATR(t0), R0, entry_candle, etc. `viz/main_data_flow.html:465` = output_contract:'per setup: direction, L_trend(t), L_opp(t), topo_candles, t0, R0, take_profit, time_barrier' | ✅ OK      | Towarzysz §11 jawnie mapuje na SOT bez redefinicji. viz/karta cytują podzbiór tej samej listy.                                                                                                                                                                                                                                                  |
| Definicja break: entry_candle = first t z sign·(close[t] - L_trend(t)) > 0 (close-based, strict >, nie >=)                                                                                                            | `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:18,26` = first candle with sign·(close[t] - L_trend(t)) > 0 ... close-based break ... first close that breaks L_trend in the direction (close-based, strict >) `ENG/detector_algorithm_eng.md:170,174,404` = entry_candle t0 = first t ... sign · (close[t] - L_trend(t)) > 0 ... strict inequality > 0 (not >=) ... close-based, strict-> break `viz/main_data_flow.html:312,466` = closed_through_line ... '1 if sign·(c - L_trend(t)) > 0' ... 'first break close-based'                                                                                                                                                                                              | ✅ OK      |                                                                                                                                                                                                                                                                                                                                                 |
| EPS (division-by-zero guard) = 1e-9                                                                                                                                                                                   | `ENG/Layers_Short_SOT/00_parameters_eng.md:18` = | EPS | 1e-9 | division-by-zero guard (ε) | `config/params.json:8` = "EPS": 1e-9 `ENG/detector_algorithm_eng.md:120,125,403` = if den <= EPS ... (ε = 1e-9) ... EPS=1e-9 (canonical)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | ✅ OK      |                                                                                                                                                                                                                                                                                                                                                 |


### Oś G — Cechy L7 / label Y / Output B

**Werdykt:** Oś jest w większości spójna z SOT (formuły 8 cech, label Y triple-barrier TB_v1.1 z moving L_opp(t), label_uniqueness_weight i 14-kolumnowy Output B w viz/karcie/glosariuszu zgadzają się z L7 SOT); jedyna realna usterka to mylące sformułowanie w karcie L07 ("8 X feature columns at t0") sprzeczne z DoD/SOT, gdzie X = dokładnie 7 (8. kolumna closed_through_line jest audytowa, poza X), plus drobny drift nazewniczy w viz (skrót kolumny w_unique zamiast label_uniqueness_weight).  
**Statusy wierszy:** ✅22 · ❌2


| Fakt                                                                                                               | Źródła (`plik:linia` = wartość)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Status      | Uwaga                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Liczba cech liczonych przez transformer przy t0 = dokładnie 8 (Feature Set v1)                                     | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:8` = At `t0` the transformer computes **exactly 8 columns** (Feature Set v1). `ENG/glossary_eng.md:102` = transformer — computes exactly 8 columns at `t0` (Feature Set v1) `viz/main_data_flow.html:248` = 8 transformer features (7 X + closed_through_line audit) `viz/main_data_flow.html:303-314` = 8 obiektów cech w FEATURES[] `viz/main_data_flow.html:1042` = nf=8 (7 X + 1 audit) `acceptance_data_transform_cards/L07_Features_X_Label_Y_Card.md:11` = compute 8 causal features at t0                                                                                                                                                                                                                                                                                                                                                          | ✅ OK        | Wszystkie źródła zgodne: transformer = 8 kolumn.                                                                                   |
| FEATURE_MANIFEST (wektor cech modelu) = dokładnie 7 X kolumn (8 minus closed_through_line)                         | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:30-43` = FEATURE_MANIFEST (the 7 X), order frozen ... = the transformer's 8 columns minus `closed_through_line` `ENG/Layers_Short_SOT/00_definition_of_done_eng.md:19` = `FEATURE_MANIFEST` contains exactly the **7 X columns**; `closed_through_line` present in B as audit and constantly `= 1` `ENG/glossary_eng.md:104` = FEATURE_MANIFEST (7 X) — the 8 columns minus `closed_through_line`; order frozen `viz/main_data_flow.html:473` = metric value '7 X'; invariants ['FEATURE_MANIFEST = 7 X'] `viz/main_data_flow.html:409` = FEATURES.filter(f=>f.name!=='closed_through_line').map(f=>f.name) `viz/main_data_flow.html:1798` = FEATURE_MANIFEST = [7 X columns — frozen order] `acceptance_data_transform_cards/L07_Features_X_Label_Y_Card.md:22` = `FEATURE_MANIFEST`: exactly the 7 X columns + closed_through_line audit flag (Output B) | ✅ OK        | Manifest = 7 X spójny wszędzie.                                                                                                    |
| Sformułowanie 'liczba kolumn X' w karcie L07 (Notebook/Artifact)                                                   | `acceptance_data_transform_cards/L07_Features_X_Label_Y_Card.md:20` = 8 X feature columns at t0 (distance_to_trend_line … body_to_range_ratio) `ENG/Layers_Short_SOT/00_definition_of_done_eng.md:19` = exactly the **7 X columns** `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:25` = closed_through_line ... **audit/invariant column, NOT part of `FEATURE_MANIFEST*`*                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ❌ ROZBIEŻNE | Karta nazywa wszystkie 8 kolumn 'X feature columns'; SOT/DoD: X = 7, 8. kolumna jest audytowa, poza X. Patrz finding G1.           |
| distance_to_trend_line — formuła i guard                                                                           | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:18` = `sign·(c − L_trend(t)) / ATR(t)` ; denominator `max(ε, ATR(t))` `viz/main_data_flow.html:304` = formula:'sign·(c − L_trend(t)) / ATR(t)' unit '×ATR'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | ✅ OK        | Znak i normalizacja zgodne; viz nie redefiniuje guardu max(ε,ATR), tylko go pomija (skrót, nie konflikt).                          |
| distance_to_opposing_line — formuła                                                                                | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:19` = `sign·(c − L_opp(t)) / ATR(t)` ; denominator `max(ε, ATR(t))` `viz/main_data_flow.html:305` = formula:'sign·(c − L_opp(t)) / ATR(t)' unit '×ATR'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | ✅ OK        | Zgodne.                                                                                                                            |
| risk_if_entered_pct — formuła                                                                                      | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:20` = `abs(c − L_opp(t)) / c · 100` ; guard `c → max(ε, c)` `viz/main_data_flow.html:306` = formula:'|c − L_opp(t)| / c · 100' unit '%'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | ✅ OK        | abs vs |·| identyczne; znak/skala zgodne.                                                                                          |
| risk_if_entered_pct — podwójna rola (X + parametr geometrii Y, definiuje R0)                                       | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:20` = Also a parameter of the Y geometry (defines R0) → mandatory ablation (guardrail R7) `ENG/glossary_eng.md:106` = simultaneously an X feature and a parameter of the Y geometry (it defines R0) → mandatory ablation (guardrail R7) `viz/main_data_flow.html:307` = feature X + Y geometry parameter (defines R0) — importance can be mechanical, interpret separately                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | ✅ OK        | viz pomija etykietę 'guardrail R7 / mandatory ablation', ale nie wprowadza sprzecznej treści ani wartości spoza SOT — opis spójny. |
| bar_return_pct — formuła i guard den=0                                                                             | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:21` = `(c − close[t−1]) / close[t−1] · 100` ; `close[t−1] = 0 → 0` `viz/main_data_flow.html:308` = formula:'(c − c[t−1]) / c[t−1] · 100' unit '%'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | ✅ OK        | Zgodne (c[t−1] = close[t−1]); viz pomija guard den=0→0 (skrót).                                                                    |
| body_to_range_ratio — formuła i guard ε                                                                            | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:22` = `abs(c − o) / max(ε, h − l)` ; ε = 1e-9 ; high == low → 0 ; [0,1] `viz/main_data_flow.html:309` = formula:'|c − o| / max(ε, h − l)' unit '[0,1]'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | ✅ OK        | Identyczna formuła wraz z guardem max(ε,h−l).                                                                                      |
| volume_z_score — formuła, std=0→0, okno W_VOL=20                                                                   | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:23` = `(v − mean_W) / std_W` ; mean_W,std_W z `W_VOL = 20` ; `**std = 0 → 0**` (never NaN/Inf) `ENG/glossary_eng.md:107` = z-score ... from the rolling window `W_VOL`; `std = 0 → 0` `viz/main_data_flow.html:310` = formula:'(v − mean_20) / std_20 (std=0 → 0)' src 'OHLCV · W=20' `ENG/Layers_Short_SOT/00_definition_of_done_eng.md:11` = `volume_z_score` correct for `std = 0` (returns `0`, not NaN/Inf) `ENG/Layers_Short_SOT/00_parameters_eng.md:14` = `W_VOL` | `20` | rolling window for `volume_z_score` `config/params.json` = W_VOL = 20                                                                                                                                                                                                                                                                                                   | ✅ OK        | viz hardcoduje 'mean_20/std_20/W=20' — patrz finding G3 (ryzyko driftu, nie aktualna rozbieżność).                                 |
| touch_count — formuła                                                                                              | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:24` = `count(topo_candles ≤ t)` ; confirmed line touches up to candle `t` ; int `viz/main_data_flow.html:311` = formula:'count(topo_candles ≤ t)' unit 'n'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | ✅ OK        | Zgodne.                                                                                                                            |
| closed_through_line — formuła i status audit (=1 w Output B, poza FEATURE_MANIFEST)                                | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:25` = `1 if sign·(c − L_trend(t)) > 0 else 0` ; in Output B (row=t0) definitionally `= 1` → audit/invariant, NOT part of FEATURE_MANIFEST `viz/main_data_flow.html:312-313` = formula:'1 if sign·(c − L_trend(t)) > 0' ; special:'in Output B (t0) always =1 — break invariant; audit column, outside FEATURE_MANIFEST' `ENG/glossary_eng.md:105` = closed_through_line (audit) — at `t0` definitionally `=1`; an audit column, outside X `ENG/Layers_Short_SOT/00_definition_of_done_eng.md:9` = `closed_through_line` is `1` from `entry_candle` onward and `0` before                                                                                                                                                                                                                                                                                   | ✅ OK        | viz skraca 'else 0' (flaga), ale semantyka i status audit zgodne z SOT.                                                            |
| DISTANCE_NORM = atr (cechy distance_* normalizowane przez ATR)                                                     | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:27` = DISTANCE_NORM = atr (multiples of ATR) `ENG/Layers_Short_SOT/00_parameters_eng.md:20` = `DISTANCE_NORM` | `atr` (recommended) / `pct` / `raw` `config/params.json` = DISTANCE_NORM = atr `viz/main_data_flow.html:304-305` = unit '×ATR' dla distance_to_trend_line / distance_to_opposing_line                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | ✅ OK        | viz wyraża unit ×ATR — spójne z DISTANCE_NORM=atr; wartość ma dom w SOT/params.                                                    |
| ATR normalizer: Wilder, W_ATR=14, causal, candle t inclusive                                                       | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:12-13` = ATR(t) = Wilder, window W_ATR=14, causal, candle t inclusive `ENG/Layers_Short_SOT/00_parameters_eng.md:15-16` = `W_ATR`=14 ; `ATR_VARIANT`=wilder, causal, candle t inclusive `config/params.json` = W_ATR = 14 `viz/main_data_flow.html:304-305` = src:'detector + Wilder ATR(14)'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | ✅ OK        | viz hardcoduje 'ATR(14)' — patrz finding G3 (ryzyko driftu).                                                                       |
| Label Y — triple barrier, first-touch, close-based (TP→1, SL→0, time→0)                                            | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:52-56` = iterate t z t0+1 do time_barrier_candle; first touch wins; TP→Y=1, SL→Y=0, Time→Y=0; BARRIER_MODE=close `ENG/glossary_eng.md:108` = triple barrier / label Y (`TB_v1.1`) ... first-touch, close-based (TP→Y=1; SL on moving L_opp(t)→Y=0; time→Y=0) `viz/main_data_flow.html:2027` = TP=1: close reaches close[t0]+direction·R0 ; SL=0: close pierces L_opp(t) (moving line) ; time=0: nothing by t0+H ; first-touch · close-based `viz/main_data_flow.html:2071` = TP→Y=1: first t: sign·close[t] ≥ sign·(close[t0]+direction·R0) ; SL→Y=0: moving line ; time→Y=0 `acceptance_data_transform_cards/L07_Features_X_Label_Y_Card.md:21` = Label Y: first-touch triple-barrier outcome (TP/SL/time, BARRIER_MODE)                                                                                                                                  | ✅ OK        | Reguła first-touch, close-based i kierunki TP/SL/time spójne wszędzie.                                                             |
| Label Y — SL = L_opp(t) moving (decyzja v1.2), TB_v1.1                                                             | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:55-59` = SL: first t z sign·close[t] < sign·L_opp(t) — L_opp(t) **moving** (decision v1.2); LABEL_CONTRACT: SL = L_opp(t) moving `ENG/glossary_eng.md:108` = SL on moving L_opp(t) `viz/main_data_flow.html:410` = label_contract:'TB_v1.1 · close-based · SL=L_opp(t) moving · geometric barriers R0 · H=24' `viz/main_data_flow.html:1800` = LABEL_CONTRACT = TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24 `viz/main_data_flow.html:1824` = SL = moving L_opp(t) (decision v1.2) `viz/main_data_flow.html:2071` = SL→Y=0: ... moving line (decision v1.2)                                                                                                                                                                                                                                                                                      | ✅ OK        | Etykieta TB_v1.1, moving L_opp(t), decyzja v1.2 spójne; identyfikator H=24 zgodny z params.                                        |
| label_uniqueness_weight (average uniqueness) — formuła weight_i = mean_{t∈W_i}(1/c_t)                              | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:61-67` = weight_i = mean_{t ∈ W_i} (1 / c_t), c_t = |{j: t∈W_j}|, c_t ≥ 1 → denominator never zero; per {asset_id}×{direction} partition `ENG/glossary_eng.md:109` = formula `weight_i = mean_{t∈W_i}(1/c_t)` owned by L7 SOT `ENG/Layers_Short_SOT/00_definition_of_done_eng.md:13` = label_uniqueness_weight computed for overlapping windows (formula in L7) `acceptance_data_transform_cards/L07_Features_X_Label_Y_Card.md:27,34` = Compute `label_uniqueness_weight` for overlapping windows; [ ] computed correctly `viz/main_data_flow.html:2028` = sample weights: label_uniqueness_weight                                                                                                                                                                                                                                                        | ✅ OK        | Formuła ma jeden dom (L7 SOT); glossary/DoD/karta tylko cytują bez redefinicji.                                                    |
| Output B — 14-kolumnowy frozen schema (4 klucze + 7 X + closed_through_line + Y_outcome + label_uniqueness_weight) | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:77-92` = 14 kolumn: asset_id, direction, setup_id, entry_timestamp, 7×X, closed_through_line (audit=1), Y_outcome (target), label_uniqueness_weight (sample weight); schema frozen `ENG/Layers_Short_SOT/00_definition_of_done_eng.md:7` = Output B has exactly the schema of L7 (column names and types match by sign) `viz/main_data_flow.html:472` = Output B: 7 X + closed_through_line(audit) + Y_outcome + w_unique `viz/main_data_flow.html:1099` = row = trend-line setup · columns = 7 X features + audit (close>line) + Y_outcome + weight w_unique · partition: asset × direction `acceptance_data_transform_cards/L07_Features_X_Label_Y_Card.md:15` = Output B (FEATURE_MANIFEST 7-X + closed_through_line + label)                                                                                                                           | ✅ OK        | Skład Output B (7 X + audit + Y + weight) spójny; viz używa skrótu w_unique zamiast label_uniqueness_weight (patrz finding G2).    |
| Nazwa kolumny wagi w Output B: label_uniqueness_weight vs alias w_unique                                           | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:92` = `label_uniqueness_weight` | float | sample weight `viz/main_data_flow.html:472` = ... Y_outcome + w_unique `viz/main_data_flow.html:1093` = def:'w_unique (weight)' `viz/main_data_flow.html:1099` = weight w_unique                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | ❌ ROZBIEŻNE | viz wprowadza skrót w_unique jako nazwę kolumny Output B; kanoniczna nazwa to label_uniqueness_weight. Patrz finding G2.           |
| Partycjonowanie per {asset_id} × {direction}                                                                       | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:94` = a separate dataset/artifact per `{asset_id} × {direction}` pair `ENG/Layers_Short_SOT/00_definition_of_done_eng.md:14` = Partitioning per `{asset_id} × {direction}` `ENG/glossary_eng.md:111` = partition `{asset_id} × {direction}` — a separate dataset/artifact for each asset × direction pair `viz/main_data_flow.html:1099` = partition: asset × direction `acceptance_data_transform_cards/L07_Features_X_Label_Y_Card.md:36` = Partitioning per `{asset_id} × {direction}`                                                                                                                                                                                                                                                                                                                                                                  | ✅ OK        | Spójne wszędzie.                                                                                                                   |
| Output A (opcjonalny, inspekcja) — wiersz na świecę w oknie setupu                                                 | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:71-72` = Output A (optional, inspection) — one row per candle inside the setup window: candle_index, the 8 feature columns, Y_entry `ENG/glossary_eng.md:110` = Output A — an optional per-candle inspection table `acceptance_data_transform_cards/L07_Features_X_Label_Y_Card.md:15` = Output A (setups + X + Y)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | ✅ OK        | Output A jako per-candle inspekcja zgodny; viz modeluje matrycę jako 'row=setup' (Output B), co jest poprawne.                     |
| Y_entry — etykieta entry-signal w per-candle table (≠ Y_outcome)                                                   | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:49-50` = Y_entry = 1 if t == entry_candle else 0 (per-candle table); Y_outcome = triple barrier (training matrix) `viz/main_data_flow.html:1090` = feat_Y def:'Y_outcome'                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | ✅ OK        | viz w matrycy Output B słusznie pokazuje Y_outcome (target), nie Y_entry; rozróżnienie zgodne z SOT.                               |
| Anti-leakage: cechy przy t0 zależą tylko od świec ≤ t0; ATR causal; L_trend/L_opp fits causal                      | `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:96-101` = L_trend, L_opp fits causal (≤t0); ATR(t) causal; no feature at t0 depends on candles > t0; volume_z uses W_VOL=20 `viz/main_data_flow.html:1096` = Features computed at t0 — only candles ≤ t0 (causality) `viz/main_data_flow.html:473` = invariants:['features at t0 ⇐ candles ≤ t0', ...] `ENG/Layers_Short_SOT/00_definition_of_done_eng.md:8` = Causality verified: a test detecting use of any candle > t                                                                                                                                                                                                                                                                                                                                                                                                                                  | ✅ OK        | Zasada zero look-ahead spójna.                                                                                                     |
| viz.FEATURES nie wprowadza formuł cech spoza SOT                                                                   | `viz/main_data_flow.html:303-314` = 8 formuł: dokładnie te same 8 cech co L7 SOT (distance_to_trend_line ... closed_through_line) `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:16-25` = tabela 8 cech (wzorzec)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | ✅ OK        | Żadna formuła w viz nie jest spoza SOT; viz konsekwentnie skraca guardy (max(ε,·), den=0→0) ale nie dodaje nowej semantyki.        |


### Oś H — Bramki QC-01…QC-11

**Werdykt:** Oś jest w bardzo dobrym stanie: wszystkie 11 predykatów QC-01…QC-11 zgadza się co do numeracji, kolejności i treści między L3 SOT a tablicą QC w viz, quality_gate_spec poprawnie cytuje SOT bez redefiniowania predykatów, a konwencja nazewnicza "QC-01…QC-11" jest przestrzegana wszędzie; jedyne uwagi to dwie miękkie kwestie (band [5,9] i okno sesji 09:00–16:00 ET nieosadzone w 00_parameters oraz uproszczona etykieta "BARS/DAY"/"hard fail QC-08/09/10"), bez realnej rozbieżności wartości.  
**Statusy wierszy:** ✅14 · ⚠️2


| Fakt                                                                          | Źródła (`plik:linia` = wartość)                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Status    | Uwaga                                                                                                                                                                                                                                                                                                                           |
| ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Konwencja nazewnicza identyfikatorów bramek = QC-01…QC-11 (11 bramek)         | `ENG/Layers_Short_SOT/00_conventions_eng.md:22` = Quality gates | `QC-01…QC-11` (11 QC gates) | Avoid: "QC-01…11", "11 padlocks" `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:1` = # L3 · DuckDB + VIEW ohlcv_1h + QC-01…QC-11 (SOT) `ENG/quality_gate_spec_eng.md:24` = L3 already enforces QC-01…QC-11 on every load `acceptance_data_transform_cards/L03_DuckDB_Raw_View_QC_Card.md:8` = L3 · DuckDB + VIEW ohlcv_1h + QC-01…QC-11 `viz/main_data_flow.html:1591` = pill ... 'QC-01…QC-11' | ✅ OK      | Forma 'QC-01…QC-11' użyta jednolicie we wszystkich plikach; brak zakazanych form.                                                                                                                                                                                                                                               |
| Liczba predykatów = 11 (pełny zakres QC-01..QC-11, bez luk w numeracji)       | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:21` = Every load passes 11 quality predicates `viz/main_data_flow.html:316-327` = 12 obiektów? nie — 11 wpisów QC-01..QC-11 w tablicy QC=[...] `ENG/quality_gate_spec_eng.md:46` = One row per check (the 11 items) `acceptance_data_transform_cards/L03_DuckDB_Raw_View_QC_Card.md:22` = QC: 11 predicates (QC-01…QC-11) run on load                                                                                                            | ✅ OK      | Tablica QC w viz (linie 316-327) ma dokładnie 11 wpisów QC-01..QC-11, zgodnie z SOT.                                                                                                                                                                                                                                            |
| QC-01 = high ≥ low (integrity)                                                | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:25` = QC-01 | `high ≥ low` `viz/main_data_flow.html:317` = QC-01 INTEGRITY ... 'high ≥ low on every candle' `ENG/Layers_Short_SOT/L8_data_quality_eng.md:31` = zero_range_bars | high == low | QC-01                                                                                                                                                                                                                                             | ✅ OK      | Treść i numer zgodne; viz dodaje 'on every candle' — doprecyzowanie, nie rozbieżność.                                                                                                                                                                                                                                           |
| QC-02 = high ≥ max(open,close) AND low ≤ min(open,close)                      | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:26` = QC-02 | `high ≥ max(open, close)` and `low ≤ min(open, close)` `viz/main_data_flow.html:318` = QC-02 OHLC CONSISTENT ... 'high ≥ max(o,c) · low ≤ min(o,c)'                                                                                                                                                                                                                                                                                | ✅ OK      | Identyczna treść (skrót o,c = open,close).                                                                                                                                                                                                                                                                                      |
| QC-03 = no duplicate (symbol, ts)                                             | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:27` = QC-03 | no duplicate `(symbol, ts)` `viz/main_data_flow.html:319` = QC-03 DUPLICATES ... 'no duplicates (symbol, ts)' `ENG/Layers_Short_SOT/L8_data_quality_eng.md:33` = duplicates | duplicate (symbol, ts) pairs | QC-03/10                                                                                                                                                                                                              | ✅ OK      | Zgodne. Mapowanie L8 łączy QC-03 z QC-10 pod counterem duplicates — dopuszczalne (oba dotyczą porządku/unikalności).                                                                                                                                                                                                            |
| QC-04 = zero NULL w open/high/low/close/volume                                | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:28` = QC-04 | zero NULL in `open/high/low/close/volume` `viz/main_data_flow.html:320` = QC-04 NULL ... 'zero NULL in o/h/l/c/v' `ENG/quality_gate_spec_eng.md:30` = nulls (QC-04) → null assertion + nan_inf_outputB discipline                                                                                                                                                                                                                  | ✅ OK      | Zgodne; o/h/l/c/v = open/high/low/close/volume.                                                                                                                                                                                                                                                                                 |
| QC-05 = prices > 0                                                            | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:29` = QC-05 | prices `> 0` `viz/main_data_flow.html:321` = QC-05 PRICES > 0 ... 'all prices positive' `ENG/Layers_Short_SOT/L8_data_quality_eng.md:32` = prices_nonpos | any price ≤ 0 | QC-05                                                                                                                                                                                                                                                   | ✅ OK      | Zgodne (prices>0 == not nonpos).                                                                                                                                                                                                                                                                                                |
| QC-06 = volume ≥ 0                                                            | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:30` = QC-06 | `volume ≥ 0` `viz/main_data_flow.html:322` = QC-06 VOLUME ≥ 0 ... 'volume non-negative' `ENG/Layers_Short_SOT/L8_data_quality_eng.md:30` = volume_zero_bars | volume == 0 | QC-06 `viz/main_data_flow.html:2081` = checks:[{id:'QC-06',level:'WARN',value:1,threshold:0,desc:'volume=0 bars'}]                                                                                                                                     | ✅ OK      | Zgodne; QC-06 (volume≥0, twarda bramka) różni się od L8 counter volume_zero_bars (WARN-only volume==0) — to defense-in-depth, nie rozbieżność predykatu.                                                                                                                                                                        |
| QC-07 = universe complete 503/503 symbols                                     | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:31` = QC-07 | universe complete: 503/503 symbols `viz/main_data_flow.html:323` = QC-07 UNIVERSE ... '503/503 symbols present' `ENG/Layers_Short_SOT/L8_data_quality_eng.md:24` = symbols | distinct asset_id present | P1, QC-07                                                                                                                                                                                                                 | ✅ OK      | Zgodne; liczba 503 jest globalnym numerem osadzonym w SOT (poza zakresem tej osi).                                                                                                                                                                                                                                              |
| QC-08 = candles per day ∈ [5, 9]                                              | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:32` = QC-08 | candles per day `∈ [5, 9]` `viz/main_data_flow.html:324` = QC-08 BARS/DAY ... 'candles per day ∈ [5,9]' `ENG/Layers_Short_SOT/L8_data_quality_eng.md:28` = gaps_in_session | missing in-session 1h candles (inside RTH 09:00–16:00 ET) | QC-08/09/10 `viz/main_data_flow.html:393` = in-session gaps: 0 (hard fail QC-08/09/10)                                                                                                    | ⚠️ RYZYKO | Treść/zakres [5,9] zgodne L3↔viz, ale wartość band [5,9] występuje TYLKO inline w L3 SOT i jest powielona literalnie w viz (linia 324) — brak osadzenia w 00_parameters; przy edycji bandu łatwo o rozjazd. Dodatkowo etykieta viz 'BARS/DAY' i grupowe 'hard fail QC-08/09/10' uogólniają QC-08; szczegóły w findingach H1/H3. |
| QC-09 = ts within session 09:00–16:00 ET                                      | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:33` = QC-09 | `ts` within the session 09:00–16:00 ET `viz/main_data_flow.html:325` = QC-09 SESSION ... 'ts in 09:00–16:00 ET' `ENG/Layers_Short_SOT/L8_data_quality_eng.md:28` = (inside RTH 09:00–16:00 ET) | QC-08/09/10                                                                                                                                                                                                                       | ⚠️ RYZYKO | Treść/okno 09:00–16:00 ET zgodne L3↔viz↔L8, ale okno sesji nieosadzone w 00_parameters — fakt żyje tylko w L3 SOT i jest powielony jako literał (viz:325, L8:28). Patrz finding H2 (ryzyko driftu).                                                                                                                             |
| QC-10 = ts strictly increasing per symbol (monotonic)                         | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:34` = QC-10 | `ts` strictly increasing per symbol `viz/main_data_flow.html:326` = QC-10 MONOTONIC ... 'ts increasing per symbol' `ENG/Layers_Short_SOT/L8_data_quality_eng.md:33` = duplicates | ... | QC-03/10                                                                                                                                                                                                                                  | ✅ OK      | Zgodne; viz pomija słowo 'strictly' ('ts increasing' vs 'strictly increasing') — pomijalne doprecyzowanie, nie zmienia faktu.                                                                                                                                                                                                   |
| QC-11 = date range and counters match _meta (manifest)                        | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:35` = QC-11 | date range and counters match `_meta` `viz/main_data_flow.html:327` = QC-11 MANIFEST ... 'date range and counters match _meta' `ENG/Layers_Short_SOT/L8_data_quality_eng.md:23` = rows | ... | P1, QC-11 `ENG/quality_gate_spec_eng.md:31` = range/counters (QC-11) → inputs_hash + parity P1                                                                                                                                      | ✅ OK      | Identyczna treść; mapowanie L8/quality_gate_spec poprawnie wiąże QC-11 z inputs_hash + P1.                                                                                                                                                                                                                                      |
| Kolejność predykatów QC-01→QC-11 (sekwencja w tabeli)                         | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:25-35` = QC-01 high≥low → QC-02 OHLC → QC-03 dups → QC-04 NULL → QC-05 prices>0 → QC-06 vol≥0 → QC-07 universe → QC-08 bars/day → QC-09 session → QC-10 monotonic → QC-11 manifest `viz/main_data_flow.html:317-327` = ta sama kolejność 1:1 (INTEGRITY, OHLC CONSISTENT, DUPLICATES, NULL, PRICES>0, VOLUME≥0, UNIVERSE, BARS/DAY, SESSION, MONOTONIC, MANIFEST)                                                                                | ✅ OK      | Kolejność identyczna w obu wyliczeniach; viz renderuje tablicę przez pętlę po QC (linia 1862), zachowując porządek.                                                                                                                                                                                                             |
| quality_gate_spec NIE redefiniuje predykatów QC — deferuje własność do L3 SOT | `ENG/quality_gate_spec_eng.md:26-27` = The QC predicates are owned by Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:19` = ## QC-01…QC-11 (load gate predicates)                                                                                                                                                                                                                                                                                  | ✅ OK      | Oczekiwana referencja towarzysza cytującego SOT bez redefinicji — zgodnie z zasadą nie jest findingiem; tu jako wiersz OK.                                                                                                                                                                                                      |
| Status bramki przy fail (load not published) — semantyka gate'u               | `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:21` = a load that fails any QC is not published `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:37` = A fail of any gate = the load is not published `viz/main_data_flow.html:446` = invariants:['QC-01…QC-11 PASS','VIEW = /10000.0 USD'] `viz/main_data_flow.html:2062` = QC-01…QC-11: PASS                                                                                                                                                 | ✅ OK      | Semantyka 'fail any → not published / PASS' spójna między L3 SOT a viz.                                                                                                                                                                                                                                                         |


### Oś I — Bramka jakości L8 + progi

**Werdykt:** Wartości progowe bloku l8 są w pełni spójne między config/params.json, 00_parameters_eng.md i L8 SOT (0%, 0.5%/2%, sufit WARN dla DET-09), a towarzysz quality_gate_spec i karta poprawnie cytują SOT bez redefinicji liczb; rozbieżności dotyczą wyłącznie schematu pola checks[].id/threshold w viz (QC-06 + threshold numeryczny zamiast string-key 1..11 i "FAIL>0"), wewnętrznej niejednoznaczności SOT 12 liczników vs 11 checks z numerycznym id 1..11 przy przykładzie string-keyed, oraz karty roszczącej sobie własność schematu summary.json i opisującej bramkę jako binarną PASS/FAIL.  
**Statusy wierszy:** ✅21 · ❌3 · ⚠️2


| Fakt                                                                                                                                                                                                      | Źródła (`plik:linia` = wartość)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Status      | Uwaga                                                                                                                                                                                                                                                                                                               |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| in_session_gaps_fail_gt = 0 (gaps_in_session: OK iff ==0, FAIL iff >0, zero-tolerance)                                                                                                                    | `config/params.json:34` = "in_session_gaps_fail_gt": 0 `ENG/Layers_Short_SOT/00_parameters_eng.md:55` = `gaps_in_session` | `== 0` | — | `> 0` | FAIL `ENG/Layers_Short_SOT/L8_data_quality_eng.md:46` = Zero-tolerance FAIL `> 0`: `gaps_in_session`, ...                                                                                                                                                                                                                                                                                                                                                               | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| filled_gaps_fail_gt = 0 (gaps_filled: OK iff ==0, FAIL iff >0; pipeline fills nothing)                                                                                                                    | `config/params.json:35` = "filled_gaps_fail_gt": 0 `ENG/Layers_Short_SOT/00_parameters_eng.md:56` = `gaps_filled` | `== 0` | — | `> 0` | FAIL `ENG/Layers_Short_SOT/L8_data_quality_eng.md:29` = `gaps_filled` | synthetically filled candles (must be 0 ...) | —                                                                                                                                                                                                                                                                                                                                                        | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| duplicates_fail_gt = 0 (duplicates: OK iff ==0, FAIL iff >0)                                                                                                                                              | `config/params.json:36` = "duplicates_fail_gt": 0 `ENG/Layers_Short_SOT/00_parameters_eng.md:57` = `duplicates` | `== 0` | — | `> 0` | FAIL `ENG/Layers_Short_SOT/L8_data_quality_eng.md:46` = Zero-tolerance FAIL `> 0`: ... `duplicates`, ...                                                                                                                                                                                                                                                                                                                                                                          | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| prices_nonpos_fail_gt = 0 (prices_nonpos: OK iff ==0, FAIL iff >0)                                                                                                                                        | `config/params.json:37` = "prices_nonpos_fail_gt": 0 `ENG/Layers_Short_SOT/00_parameters_eng.md:58` = `prices_nonpos` | `== 0` | — | `> 0` | FAIL `ENG/Layers_Short_SOT/L8_data_quality_eng.md:46` = Zero-tolerance FAIL `> 0`: ... `prices_nonpos`, ...                                                                                                                                                                                                                                                                                                                                                                 | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| nan_inf_outputB_fail_gt = 0 (nan_inf_outputB undocumented only: OK iff ==0, FAIL iff >0)                                                                                                                  | `config/params.json:38` = "nan_inf_outputB_fail_gt": 0 `ENG/Layers_Short_SOT/00_parameters_eng.md:59` = `nan_inf_outputB` (undocumented only) | `== 0` | — | `> 0` | FAIL `ENG/Layers_Short_SOT/L8_data_quality_eng.md:36` = Documented Output-B exception (does NOT count): `volume_z_score = NaN` ... Every other NaN/Inf counts.                                                                                                                                                                                                                                                                                      | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| parity_fail_on_mismatch = true (P1/P2/P3 FAIL on any mismatch, exact equality, no tolerance)                                                                                                              | `config/params.json:39` = "parity_fail_on_mismatch": true `ENG/Layers_Short_SOT/00_parameters_eng.md:60` = parity P1 / P2 / P3 | equal | — | any mismatch | FAIL `ENG/Layers_Short_SOT/L8_data_quality_eng.md:11` = both sides are re-counted and asserted exactly equal (no tolerance) `ENG/Layers_Short_SOT/L8_data_quality_eng.md:47` = Parity P1 / P2 / P3: FAIL on any mismatch (this rule is from the contract, not reference design).                                                                                                                                                                             | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| volume_zero_warn_fraction = 0.005 (WARN band lower edge = 0.5% of rows for volume_zero_bars)                                                                                                              | `config/params.json:40` = "volume_zero_warn_fraction": 0.005 `ENG/Layers_Short_SOT/00_parameters_eng.md:61` = `volume_zero_bars` / `rows` | `≤ 0.5%` | `> 0.5%` and `≤ 2%` | `> 2%` | FAIL                                                                                                                                                                                                                                                                                                                                                                                                                               | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| volume_zero_fail_fraction = 0.02 (FAIL band = >2% of rows for volume_zero_bars)                                                                                                                           | `config/params.json:41` = "volume_zero_fail_fraction": 0.02 `ENG/Layers_Short_SOT/00_parameters_eng.md:61` = `volume_zero_bars` / `rows` | `≤ 0.5%` | `> 0.5%` and `≤ 2%` | `> 2%` | FAIL                                                                                                                                                                                                                                                                                                                                                                                                                                | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| zero_range_warn_fraction = 0.005 (WARN band lower edge = 0.5% of rows for zero_range_bars)                                                                                                                | `config/params.json:42` = "zero_range_warn_fraction": 0.005 `ENG/Layers_Short_SOT/00_parameters_eng.md:62` = `zero_range_bars` / `rows` | `≤ 0.5%` | `> 0.5%` and `≤ 2%` | `> 2%` | FAIL                                                                                                                                                                                                                                                                                                                                                                                                                                 | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| zero_range_fail_fraction = 0.02 (FAIL band = >2% of rows for zero_range_bars)                                                                                                                             | `config/params.json:43` = "zero_range_fail_fraction": 0.02 `ENG/Layers_Short_SOT/00_parameters_eng.md:62` = `zero_range_bars` / `rows` | `≤ 0.5%` | `> 0.5%` and `≤ 2%` | `> 2%` | FAIL                                                                                                                                                                                                                                                                                                                                                                                                                                  | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| det09_rejected_warn_fraction = 0.2 (DET-09 rate: OK iff ≤20%, WARN iff >20%, never FAIL — WARN ceiling diagnostic)                                                                                        | `config/params.json:44` = "det09_rejected_warn_fraction": 0.2 `ENG/Layers_Short_SOT/00_parameters_eng.md:63` = `det09_rejected` rate | `≤ 20%` | `> 20%` | never | **WARN max** (diagnostic) `ENG/Layers_Short_SOT/L8_data_quality_eng.md:49` = `det09_rejected` rate: WARN-only diagnostic (never FAIL). `ENG/quality_gate_spec_eng.md:34` = L8 surfaces it as WARN-only — it can never FAIL the gate.                                                                                                                                                                                                                  | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| Zero-denominator guards: fractions use den=max(1,rows); DET-09 rate uses det09_rejected/max(1, setups_total+det09_rejected); float ratios use max(ε,…), ε=1e-9; den=0→0                                   | `ENG/Layers_Short_SOT/00_parameters_eng.md:65` = fractions use `den = max(1, rows)`; the DET-09 rate uses `det09_rejected / max(1, setups_total + det09_rejected)`; ... `den = 0 → 0` `ENG/Layers_Short_SOT/L8_data_quality_eng.md:42` = The numeric bands and the zero-denominator guards are owned by [00_parameters_eng.md] (`l8` block). `ENG/quality_gate_spec_eng.md:77` = Every divisor uses an explicit guard (`max(1, …)` ... `max(ε, …)` with `ε = 1e-9`; `den = 0 → 0`) — guards owned by `00_parameters_eng.md`.                                                                                             | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| Counter catalogue = 12 counters (rows, symbols, parquet_files, setups_total, det09_rejected, gaps_in_session, gaps_filled, volume_zero_bars, zero_range_bars, prices_nonpos, duplicates, nan_inf_outputB) | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:23` = 12 table rows rows…nan_inf_outputB (lines 23-34) `ENG/Layers_Short_SOT/L8_data_quality_eng.md:62` = "rows":8841820,"symbols":503,"parquet_files":503,"setups_total":0,"det09_rejected":0,"gaps_in_session":0,"gaps_filled":0,"volume_zero_bars":0,"zero_range_bars":0,"prices_nonpos":0,"duplicates":0,"nan_inf_outputB":0 `viz/main_data_flow.html:2081` = counters:{rows:8841820,symbols:503,parquet_files:503,setups_total:0,det09_rejected:0,gaps_in_session:0,gaps_filled:0,volume_zero_bars:0,zero_range_bars:0,prices_nonpos:0,duplicates:0,nan_inf_outputB:0} | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| Number of gate checks = 11 (the 11 thresholded items: 8 counter-checks + 3 parities); ids 1..11                                                                                                           | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:40` = ## Checks (11 items) → thresholds `ENG/Layers_Short_SOT/L8_data_quality_eng.md:73` = "checks": [ // exactly one object per check id 1..11 `ENG/quality_gate_spec_eng.md:46` = One row per check (the 11 items)                                                                                                                                                                                                                                                                                                                                                        | ⚠️ RYZYKO   | Wewnątrz samego SOT współistnieją 12 liczników (catalogue) i 11 checks; 4 liczniki populacyjne (rows/symbols/parquet_files/setups_total) nie są niezależnie progowane, lecz zasilają parytety — relacja 12→11 nie jest nigdzie jawnie wyjaśniona, co rodzi ryzyko błędnej walidacji 'dokładnie 12 obiektów checks'. |
| summary.json checks[].id schema: identyfikator pozycji checks (string-key counter/parity vs numeryczne 1..11 vs QC-xx)                                                                                    | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:74` = { "id": "gaps_in_session", "level": "OK", "value": 0, "threshold": "FAIL>0", ... } `ENG/Layers_Short_SOT/L8_data_quality_eng.md:73` = exactly one object per check id 1..11 `viz/main_data_flow.html:2081` = checks:[{id:'QC-06',level:'WARN',value:1,threshold:0,desc:'volume=0 bars'}]                                                                                                                                                                                                                                                                              | ❌ ROZBIEŻNE | Trzy różne konwencje id w obrębie pola checks[].id: SOT przykład = string-key licznika ('gaps_in_session'), SOT komentarz = numeryczne 1..11, viz = identyfikator QC ('QC-06').                                                                                                                                     |
| summary.json checks[].threshold field type/format                                                                                                                                                         | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:74` = "threshold": "FAIL>0" (string) `ENG/quality_gate_spec_eng.md:47` = the `threshold` string `viz/main_data_flow.html:2081` = threshold:0 (number)                                                                                                                                                                                                                                                                                                                                                                                                                       | ❌ ROZBIEŻNE | viz koduje threshold jako liczbę 0, SOT i towarzysz jako string 'FAIL>0'.                                                                                                                                                                                                                                           |
| summary.json top-level schema (schema_version 1.0, built_at_utc, inputs_hash, counters, parities, checks[], overall_status)                                                                               | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:57` = schema_version:'1.0', built_at_utc, inputs_hash, counters{}, parities{}, checks[], overall_status `viz/main_data_flow.html:2081` = {schema_version:'1.0',built_at_utc:'…',inputs_hash:'…',counters:{...},parities:{...},checks:[...],overall_status:'WARN'}                                                                                                                                                                                                                                                                                                           | ✅ OK        | Struktura nadrzędnych pól zgodna; rozbieżności tylko wewnątrz checks[] (id/threshold — patrz wiersze powyżej).                                                                                                                                                                                                      |
| Parity P1/P2/P3 definicje (P1 zip→DuckDB rows+symbols; P2 DuckDB→parquet files+per-ticker rows; P3 parquet→Output B per {asset×direction} setup-count)                                                    | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:15` = P1 zip→DuckDB row+symbol; P2 DuckDB→parquet file+per-ticker; P3 parquet→Output B per {asset_id}×{direction} (audit R4) `acceptance_data_transform_cards/L08_Data_Quality_Gate_Card.md:20` = Parity chain: P1 (zip↔DuckDB), P2 (DuckDB↔parquet), P3 (parquet↔Output B) `viz/main_data_flow.html:2081` = parities:{zip_duckdb_rows:true,duckdb_parquet_files:true,parquet_outputB:true} `viz/main_data_flow.html:391` = zip → DuckDB: 8 841 820 rows / 503 symbols · DuckDB → parquet: 503 files · parquet → Output B: setup count per {asset × direction} (R4)         | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| Parity P1 reference target = 8 841 820 rows · 503 symbols; parquet_files = 503                                                                                                                            | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:15` = 8 841 820 rows · 503 symbols (P1); 503 files (P2) `ENG/quality_gate_spec_eng.md:62` = rows = 8 841 820, symbols = 503, parquet_files = 503 `acceptance_data_transform_cards/L08_Data_Quality_Gate_Card.md:36` = Reference targets from v1 (8 841 820 rows, 503 symbols). `viz/main_data_flow.html:2081` = rows:8841820, symbols:503, parquet_files:503                                                                                                                                                                                                                | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| Gate aggregation rule = FAIL > WARN > OK (any FAIL→FAIL; else any WARN→WARN; else OK)                                                                                                                     | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:87` = if any FAIL: FAIL; elif any WARN: WARN; else OK `viz/main_data_flow.html:401` = FAIL: 0 · WARN: 1 (zero-values) · gate: OPEN `viz/main_data_flow.html:2081` = overall_status:'WARN' (1 WARN, no FAIL)                                                                                                                                                                                                                                                                                                                                                                 | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| Kontrakt L8→L9: FAIL → BLOCKED (training does not start); WARN/OK → PROCEED; L9 reads overall_status z summary.json                                                                                       | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:92` = FAIL=BLOCKED; WARN=PROCEED; OK=PROCEED; L9 reads overall_status from summary.json, not the HTML `ENG/quality_gate_spec_eng.md:79` = binary toward L9: overall_status is the only field L9 reads to decide go/no-go `viz/main_data_flow.html:511` = training starts only with a green dashboard (FAIL blocks) `viz/main_data_flow.html:480` = ['any FAIL blocks training','green dashboard = start condition']                                                                                                                                                         | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |
| Własność schematu summary.json (one home per fact): należy do L8 SOT                                                                                                                                      | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:5` = This file owns the counters, the parity chain, the `summary.json` schema and the aggregation rule `ENG/quality_gate_spec_eng.md:4` = the `summary.json` field schema ... are owned by [Layers_Short_SOT/L8_data_quality_eng.md] `acceptance_data_transform_cards/L08_Data_Quality_Gate_Card.md:21` = `summary.json` schema owned here                                                                                                                                                                                                                                  | ❌ ROZBIEŻNE | Karta deklaruje 'summary.json schema owned here', co przeczy SOT (schemat należy do L8 SOT); stopka karty równocześnie wskazuje SOT owner — wewnętrznie sprzeczne.                                                                                                                                                  |
| Stan bramki / decyzja: trój-stanowy overall_status OK/WARN/FAIL (binarny tylko TOWARD L9)                                                                                                                 | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:78` = overall_status "OK" | "WARN" | "FAIL" `ENG/quality_gate_spec_eng.md:79` = The gate is binary toward L9 `acceptance_data_transform_cards/L08_Data_Quality_Gate_Card.md:15` = gate decision (PASS/FAIL)                                                                                                                                                                                                                                                                                                                                                                 | ⚠️ RYZYKO   | Karta opisuje wynik jako binarny PASS/FAIL, podczas gdy SOT definiuje trój-stanowy overall_status (WARN PROCEED jest stanem nie-PASS i nie-FAIL); WARN gubi się w binarnym opisie karty.                                                                                                                            |
| DET-09 rejection populacja jako wartość przykładowa w viz (sample 1 982; WARN/diagnostyczny)                                                                                                              | `viz/main_data_flow.html:397` = DET-09 rejections: 1 982 (audit) `ENG/Layers_Short_SOT/L8_data_quality_eng.md:27` = `det09_rejected` | setups rejected by DET-09 (`R0 ≤ 0`, `ATR(t0) ≤ 0`, or missing `L_opp`)                                                                                                                                                                                                                                                                                                                                                                                                           | ✅ OK        | Liczba 1 982 to dane poglądowe (mock) wizualizacji, nie redefiniuje progu det09_rejected_warn_fraction=0.2 ani definicji licznika; akceptowalne jako ilustracja.                                                                                                                                                    |
| Wartości WARN zero-values w viz (volume=0: 1 274; zero-range: 312; prices≤0: 0) jako sample bez cytowania pasm 0.5%/2%                                                                                    | `viz/main_data_flow.html:395` = volume=0 bars: 1 274 · high==low candles (zero-range): 312 · prices ≤ 0: 0 · WARN: zero-volume above the informational threshold `ENG/Layers_Short_SOT/00_parameters_eng.md:61` = `volume_zero_bars` / `rows` | `≤ 0.5%` | `> 0.5%` and `≤ 2%` | `> 2%` | FAIL                                                                                                                                                                                                                                                                                                                           | ✅ OK        | Liczby to dane poglądowe; viz nie wprowadza własnych progów liczbowych (mówi ogólnikowo 'informational threshold'), więc nie narusza one-home-per-fact. Brak hardcodu progu = bez ryzyka driftu.                                                                                                                    |
| summary.json zapisany przed dashboard.html; dashboard = deterministyczny self-contained render (zero zależności)                                                                                          | `ENG/Layers_Short_SOT/L8_data_quality_eng.md:101` = dashboard.html is a self-contained (zero-dependency) deterministic render of summary.json `ENG/quality_gate_spec_eng.md:76` = summary.json is written before dashboard.html; the HTML is a deterministic render of the JSON `viz/main_data_flow.html:2081` = generated per run · the HTML dashboard reads only this file                                                                                                                                                                                                                                             | ✅ OK        |                                                                                                                                                                                                                                                                                                                     |


### Oś J — Model L9 / ewaluacja L10 / metryki

**Werdykt:** Oś J jest w większości spójna z SOT (N_TRIALS, TUNER, objective, ESTIMATOR, THRESHOLD_ENTRY, exity TB i kanoniczna kolejność metryk PF·Sharpe·MDD·TIM·WR zgadzają się wszędzie), ale viz wprowadza dwa zestawy faktów nieosadzonych w SOT — przestrzeń przeszukiwania Optuny (OPTUNA.space) oraz progi metryk lo/hiV (METRICS) — co narusza zasadę "one home per fact"; dodatkowo viz ma drobną wewnętrzną i międzyplikową rozbieżność sformułowania LABEL_CONTRACT.  
**Statusy wierszy:** ✅14 · ❌1 · ⚠️1 · 🔶2


| Fakt                                                                                                                                                                                                    | Źródła (`plik:linia` = wartość)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Status         | Uwaga                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Budżet tuningu N_TRIALS = 200                                                                                                                                                                           | `config/params.json:15` = "N_TRIALS": 200 `ENG/Layers_Short_SOT/00_parameters_eng.md:24` = `N_TRIALS` | `200` | Optuna trial budget `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:9` = budget: 200 trials (`N_TRIALS`) `acceptance_data_transform_cards/L09_Optuna_XGBoost_Card.md:21` = `N_TRIALS=200`, TPE sampler, MedianPruner `viz/main_data_flow.html:354` = var OPTUNA={n_trials:200,...} `viz/main_data_flow.html:487` = metric:{label:'trials',value:'200'}                                                                                                                                                                                                                              | ✅ OK           |                                                                                                                                                |
| TUNER = optuna_tpe_median_pruner (TPE + MedianPruner, n_warmup_steps=2)                                                                                                                                 | `config/params.json:18` = "TUNER": "optuna_tpe_median_pruner" `ENG/Layers_Short_SOT/00_parameters_eng.md:27` = `TUNER` | `optuna_tpe_median_pruner` | hyperparameter tuning (TPE + MedianPruner) `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:10` = sampler: TPE ... pruner: MedianPruner (`n_warmup_steps=2`) `acceptance_data_transform_cards/L09_Optuna_XGBoost_Card.md:21` = TPE sampler, MedianPruner `viz/main_data_flow.html:354` = sampler:'TPE',pruner:'MedianPruner(n_warmup_steps=2)'                                                                                                                                                                                                 | ✅ OK           |                                                                                                                                                |
| Objective = AUC-PR nad purged walk-forward CV (k=4 folds), tylko Train                                                                                                                                  | `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:12` = objective: AUC-PR over purged walk-forward CV (k=4 folds), in Train only `acceptance_data_transform_cards/L09_Optuna_XGBoost_Card.md:22` = Objective: AUC-PR, purged walk-forward k=4 `viz/main_data_flow.html:355` = objective:'AUC-PR (mean over k=4 purged walk-forward folds on Train)'                                                                                                                                                                                                                                                                                                                                                   | ✅ OK           |                                                                                                                                                |
| CV_SCHEME = purged_walk_forward                                                                                                                                                                         | `config/params.json:16` = "CV_SCHEME": "purged_walk_forward" `ENG/Layers_Short_SOT/00_parameters_eng.md:25` = `CV_SCHEME` | `purged_walk_forward` `ENG/Layers_Short_SOT/L5_time_split_eng.md:19` = Purged walk-forward CV (`CV_SCHEME`) separates the folds inside Train                                                                                                                                                                                                                                                                                                                                                                                                                           | ✅ OK           |                                                                                                                                                |
| ESTIMATOR = xgboost_binary_logistic (meta-labeling: filtr sygnału setupu)                                                                                                                               | `config/params.json:17` = "ESTIMATOR": "xgboost_binary_logistic" `ENG/Layers_Short_SOT/00_parameters_eng.md:26` = `ESTIMATOR` | `xgboost_binary_logistic` | meta-labeling: setup-signal filter `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:14` = XGBoost trains as `binary:logistic` (meta-labeling) `acceptance_data_transform_cards/L09_Optuna_XGBoost_Card.md:11` = train binary:logistic XGB `viz/main_data_flow.html:2072` = Objective: binary:logistic — p(TP) ... Role: meta-labeling, trend-line setup signal filter                                                                                                                                                                    | ✅ OK           |                                                                                                                                                |
| THRESHOLD_ENTRY = 0.60 (p ≥ 0.60 → ENTRY, else FLAT)                                                                                                                                                    | `config/params.json:12` = "THRESHOLD_ENTRY": 0.6 `ENG/Layers_Short_SOT/00_parameters_eng.md:21` = `THRESHOLD_ENTRY` | `0.60` `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:30` = `THRESHOLD_ENTRY = 0.60` `ENG/Layers_Short_SOT/L10_oos_test_eng.md:11` = entry rule: `p ≥ 0.60 → ENTRY` `acceptance_data_transform_cards/L10_OOS_Test_Card.md:22` = Entry rule: probability p ≥ 0.60 `viz/main_data_flow.html:411` = threshold_entry:0.60 `viz/main_data_flow.html:1802` = p ≥ 0.60 → ENTRY else FLAT                                                                                                                                                                                            | ✅ OK           | params.json zapisuje 0.6, markdown/viz 0.60 — ta sama wartość liczbowa, różnica wyłącznie w formacie tekstowym; reguła mirror spełniona.       |
| Exity triple-barrier: TP fixed z R0 · SL = moving L_opp(t) · time barrier 24 świece                                                                                                                     | `ENG/Layers_Short_SOT/L10_oos_test_eng.md:12` = exits per triple barrier: fixed TP from `R0` · SL = moving `L_opp(t)` · time barrier 24 candles `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:20` = `take_profit_level = close[t0] + direction · R0` (fixed level) `acceptance_data_transform_cards/L10_OOS_Test_Card.md:24` = Exit rules: TP = R0, SL = moving L_opp(t), time-barrier = 24 candles `viz/main_data_flow.html:2085` = TP: close[t0] + direction·R0 · time barrier: t0+H (H=24)                                                                                                                                                                                                     | ✅ OK           |                                                                                                                                                |
| LABEL_CONTRACT identyfikator = TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24                                                                                                                   | `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:29` = `TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24` `viz/main_data_flow.html:1800` = LABEL_CONTRACT = TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24 `viz/main_data_flow.html:410` = label_contract:'TB_v1.1 · close-based · SL=L_opp(t) moving · geometric barriers R0 · H=24'                                                                                                                                                                                                                                                                                                                                                  | ❌ ROZBIEŻNE    |                                                                                                                                                |
| Kontrakt artefaktu strategy_.py: MODEL_B64, FEATURE_MANIFEST (7 X), LABEL_CONTRACT, THRESHOLD_ENTRY, selfcheck()                                                                                        | `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:25` = Mandatory sections: MODEL_B64 / FEATURE_MANIFEST (7 X) / LABEL_CONTRACT / THRESHOLD_ENTRY / selfcheck() `acceptance_data_transform_cards/L09_Optuna_XGBoost_Card.md:16` = Artifact: base64 model + `selfcheck()` `viz/main_data_flow.html:405` = manifest(a) {... model_b64, feature_manifest, label_contract, threshold_entry, selfcheck} `viz/main_data_flow.html:1798` = FEATURE_MANIFEST = [7 X columns — frozen order]                                                                                                                                                                                                                   | ✅ OK           |                                                                                                                                                |
| FEATURE_MANIFEST = 7 X (bez closed_through_line, frozen order)                                                                                                                                          | `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:28` = the **7 X columns** in frozen order (without `closed_through_line`) `viz/main_data_flow.html:473` = invariants:['FEATURE_MANIFEST = 7 X'] `viz/main_data_flow.html:409` = feature_manifest:FEATURES.filter(...f.name!=='closed_through_line'...)                                                                                                                                                                                                                                                                                                                                                                                              | ✅ OK           |                                                                                                                                                |
| Kanoniczna kolejność metryk OOS: PF · Sharpe · MDD · TIM · WR (= METRICS)                                                                                                                               | `ENG/Layers_Short_SOT/00_conventions_eng.md:21` = OOS metrics order | **PF · Sharpe · MDD · TIM · WR** (= `METRICS` array) | Avoid: PF · MDD · TIM · Sharpe · WR `ENG/Layers_Short_SOT/L10_oos_test_eng.md:14` = OOS metrics canonical order: PF · Sharpe · MDD · TIM · WR (= `METRICS`) `viz/main_data_flow.html:381` = [{id:'pf'},{id:'sharpe'},{id:'mdd'},{id:'tim'},{id:'wr'}] (kolejność PF·Sharpe·MDD·TIM·WR) `viz/main_data_flow.html:493` = results matrix: PF · Sharpe · MDD · TIM · WR `acceptance_data_transform_cards/L10_OOS_Test_Card.md:23` = Metrics canonical order in matrix: PF · Sharpe · MDD% · TIM% · WR% (plus trades count)                                                | ✅ OK           |                                                                                                                                                |
| Matryca wyników 503 assets × {PF · Sharpe · MDD% · TIM% · WR% · trades}                                                                                                                                 | `ENG/Layers_Short_SOT/L10_oos_test_eng.md:13` = a matrix `503 assets × {PF · Sharpe · MDD% · TIM% · WR% · trades}` `acceptance_data_transform_cards/L10_OOS_Test_Card.md:15` = 503×{PF, Sharpe, MDD%, TIM%, WR%, trades} matrix `viz/main_data_flow.html:489` = OOS TEST: 503 ASSETS × METRICS                                                                                                                                                                                                                                                                                                                                                                                                     | ✅ OK           |                                                                                                                                                |
| Okno OOS = 2024-01-02 → 2026-05-29, single run / one-shot                                                                                                                                               | `config/params.json:25` = "oos_start": "2024-01-02", "oos_end": "2026-05-29" `ENG/Layers_Short_SOT/L10_oos_test_eng.md:7` = a single run over the OOS window `2024-01-02 → 2026-05-29` `acceptance_data_transform_cards/L10_OOS_Test_Card.md:21` = OOS window dates: 2024-01-02 → 2026-05-29 (frozen, never tuned) `viz/main_data_flow.html:491` = single run on OOS 2024-01-02 → 2026-05-29                                                                                                                                                                                                                                                                                                       | ✅ OK           |                                                                                                                                                |
| Przestrzeń przeszukiwania Optuny (max_depth 3-9, learning_rate 0.01-0.3 log, n_estimators 100-1200, min_child_weight 1-20, subsample/colsample 0.5-1.0, reg_lambda 1e-3-10 log, scale_pos_weight 0.5-4) | `viz/main_data_flow.html:356` = space:{max_depth:'3–9',learning_rate:'0.01–0.3 (log)',n_estimators:'100–1200',min_child_weight:'1–20',subsample:'0.5–1.0',colsample_bytree:'0.5–1.0',reg_lambda:'1e-3–10 (log)',scale_pos_weight:'0.5–4'} `viz/main_data_flow.html:1782` = search space: depth 3–9 · lr 0.01–0.3 log · estimators 100–1200 · subsample/colsample 0.5–1 · λ 1e-3–10 · spw 0.5–4 `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:6` = sekcja Tuning + training NIE definiuje żadnych zakresów hiperparametrów `config/params.json:1` = params.json nie zawiera żadnego z kluczy max_depth/learning_rate/n_estimators/min_child_weight/subsample/colsample/reg_lambda/scale_pos_weight | 🔶 NIEOSADZONE |                                                                                                                                                |
| Progi jakości metryk OOS w viz (lo/hiV): pf lo0.7/hiV2.1, sharpe lo-0.5/hiV2.2, mdd lo5/hiV35, tim lo4/hiV28, wr lo32/hiV58                                                                             | `viz/main_data_flow.html:382` = {id:'pf',hi:true,lo:0.7,hiV:2.1} ... {id:'sharpe',lo:-0.5,hiV:2.2} ... {id:'mdd',lo:5,hiV:35} ... {id:'tim',lo:4,hiV:28} ... {id:'wr',lo:32,hiV:58} `viz/main_data_flow.html:387` = function metricQ(val,m){... (val-M.lo)/(M.hiV-M.lo) ...} `ENG/Layers_Short_SOT/L10_oos_test_eng.md:13` = L10 opisuje metryki jakościowo, NIE podaje progów lo/hiV ani skali kolorowania `config/params.json:1` = params.json nie zawiera progów oceny metryk                                                                                                                                                                                                                   | 🔶 NIEOSADZONE |                                                                                                                                                |
| Param importance (learning_rate 0.31, max_depth 0.22, min_child_weight 0.14, subsample 0.12, n_estimators 0.09, colsample_bytree 0.07, reg_lambda 0.05)                                                 | `viz/main_data_flow.html:371` = var PARAM_IMPORTANCE=[['learning_rate',0.31],['max_depth',0.22],...] `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:6` = SOT nie definiuje importance hiperparametrów (wartości czysto ilustracyjne/mock)                                                                                                                                                                                                                                                                                                                                                                                                                                                          | ⚠️ RYZYKO      | Wartości ewidentnie ilustracyjne (mock), ale wymienione jako konkretne liczby procentowe w viz; brak domu w SOT i ryzyko odczytania jako fakt. |
| Sample weights = label_uniqueness_weight; jeden model per {asset × direction}                                                                                                                           | `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:15` = sample weights: `label_uniqueness_weight`; one model per `{asset × direction}` pair `viz/main_data_flow.html:2072` = Training: Train with uniqueness weights ... Per: asset × direction `viz/main_data_flow.html:2071` = sample weights: label_uniqueness_weight                                                                                                                                                                                                                                                                                                                                                                              | ✅ OK           |                                                                                                                                                |
| Liczba artefaktów strategy_.py = 503 (×503)                                                                                                                                                             | `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:22` = one self-contained `strategy_<TICKER>.py` per Asset (target ×503) `acceptance_data_transform_cards/L10_OOS_Test_Card.md:14` = Frozen `strategy_*.py` from L9 `viz/main_data_flow.html:1793` = one file per asset → 503 artifacts in total · deterministic build (hash)                                                                                                                                                                                                                                                                                                                                                                        | ✅ OK           | Karta L09 (linia 22) pisze 'per asset (×503)'; konwencja 503 = uniwersum (00_conventions:34). Spójne.                                          |


### Oś K — Glosariusz (kompletność/spójność)

**Werdykt:** glossary_eng.md jest w ~90% zgodny z SOT i poprawnie deklaruje się jako podrzędny słownik pojęć (nie redefiniuje liczbowo parametrów: 200/0.60/2 itd. są tylko delegowane do 00_parameters_eng.md, nazewnictwo kanoniczne DuckDB/VIEW ohlcv_1h/QC-01…QC-11/PF·Sharpe·MDD·TIM·WR/warm-up/L1–L10/F0–F14 jest zachowane); rozbieżności są drobne i dotyczą: (1) braku w słowniku kanonicznych nazw kolumn Y_entry/Y_outcome (zlane w jeden generyczny wpis „label Y"), (2) notacji p(TP) niewystępującej w SOT (SOT używa p = model(x)), (3) terminu cooldown używanego w SOT a nieobecnego w słowniku, (4) restatementu wzorów/liczb pochodnych (R0, z-score, rolling lookback = 20) wbrew własnej deklaracji „point, don't restate", (5) drobnej niespójności „hash registry" vs „hash register".  
**Statusy wierszy:** ✅20 · ❌4 · ⚠️4


| Fakt                                                                                                                             | Źródła (`plik:linia` = wartość)                                                                                                                                                                                                                                                                                                                                                                                 | Status      | Uwaga                                                                                                                                                                                                                                                                                                                   |
| -------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Status słownika: podrzędny term dictionary, SOT wins on divergence, point-not-restate dla wartości build-critical                | `ENG/glossary_eng.md:3-7` = Subordinate to the SOT. This is a term dictionary ... it points to the SOT rather than restating it; on any divergence, the SOT wins. `ENG/Layers_Short_SOT/00_conventions_eng.md:4` = Owned here; companion docs reference this file and restate nothing.                                                                                                                          | ✅ OK        | Deklaracja roli zgodna z zasadą nadrzędną audytu.                                                                                                                                                                                                                                                                       |
| Forma kanoniczna DuckDB (nie 'kaczka'/'duck')                                                                                    | `ENG/glossary_eng.md:53,55,145` = DuckDB ... DuckDB — the analytical database ... The canonical naming forms (DuckDB ...) `ENG/Layers_Short_SOT/00_conventions_eng.md:19` = Analytical store ... `DuckDB` ... Avoid "duck", "kaczka"                                                                                                                                                                            | ✅ OK        | Brak wystąpień 'kaczka'/'duck' (poza DuckDB) w całym A_Layers (grep negatywny).                                                                                                                                                                                                                                         |
| Forma kanoniczna VIEW ohlcv_1h (USD)                                                                                             | `ENG/glossary_eng.md:53,58,145` = VIEW ohlcv_1h (USD) ... VIEW `ohlcv_1h` — a named view of prices in USD ... `VIEW ohlcv_1h` `ENG/Layers_Short_SOT/00_conventions_eng.md:20` = USD price view ... `VIEW ohlcv_1h` (in prose: the `ohlcv_1h` view), add "(USD)"                                                                                                                                                 | ✅ OK        |                                                                                                                                                                                                                                                                                                                         |
| Forma QC-01…QC-11 (11 bramek)                                                                                                    | `ENG/glossary_eng.md:53,62,145` = QC-01…QC-11 ... 11 load-validation predicates ... `QC-01…QC-11` `ENG/Layers_Short_SOT/00_conventions_eng.md:22` = Quality gates ... `QC-01…QC-11` (11 QC gates) ... Avoid "QC-01…11", "11 padlocks"                                                                                                                                                                           | ✅ OK        |                                                                                                                                                                                                                                                                                                                         |
| Kolejność metryk OOS: PF · Sharpe · MDD · TIM · WR                                                                               | `ENG/glossary_eng.md:136,137,145` = canonical order **PF · Sharpe · MDD · TIM · WR** (+ trades) `ENG/Layers_Short_SOT/00_conventions_eng.md:21` = OOS metrics order ... **PF · Sharpe · MDD · TIM · WR** (= `METRICS` array) `ENG/Layers_Short_SOT/L10_oos_test_eng.md:14` = OOS metrics canonical order: PF · Sharpe · MDD · TIM · WR (= `METRICS`)                                                            | ✅ OK        |                                                                                                                                                                                                                                                                                                                         |
| warm-up (proza) / warmup (kod)                                                                                                   | `ENG/glossary_eng.md:76,146` = warm-up / train / OOS ... `warm-up` `ENG/Layers_Short_SOT/00_conventions_eng.md:24` = Roll-in phase (prose) ... `warm-up` (code/filenames: `warmup`)                                                                                                                                                                                                                             | ✅ OK        | Glossary używa formy prozatorskiej 'warm-up' konsekwentnie.                                                                                                                                                                                                                                                             |
| Rezerwacja schematów: L1–L10 dla Pipeline A; Stages F0–F14 dla Plan B (never L#)                                                 | `ENG/glossary_eng.md:19,151-152` = 10 levels L1–L10 ... own Stage scheme F0–F14 (never `L#`) and ids `f{stage}_…` `ENG/Layers_Short_SOT/00_conventions_eng.md:29-30` = `layer` / `L1–L10` belong to Pipeline A only ... uses Stages `F0–F14` and ids `f{stage}_…` — never `L#`                                                                                                                                  | ✅ OK        |                                                                                                                                                                                                                                                                                                                         |
| Liczby globalne: 503 / 510 / 8 841 820 / ×10000 / ~7 candles/day                                                                 | `ENG/glossary_eng.md:20,46,63,37` = 503 tickers ... 510 zip ... 8 841 820 rows · 503 symbols · database 166 MB ... ~7 1h candles per session day `ENG/Layers_Short_SOT/00_conventions_eng.md:34-38` = 503 ... 510 ... 8 841 820 ... ×10000 ... ~7 ... candles/day ∈ [5, 9] `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:17` = 8 841 820 rows · 503 symbols · database 166 MB · range 2016-01-04 → rolling | ✅ OK        | Wartości zgodne z 'Global numbers' SOT; glossary jako term dictionary cytuje je — dopuszczalne (liczby globalne są mienione w conventions). Glossary pomija jednak zakres candles/day ∈ [5,9] z conventions:38 (tylko '~7'), co jest skróceniem, nie rozbieżnością.                                                     |
| Delegacja wartości parametrów (TF/H/MIN_TOUCHES/THRESHOLD_ENTRY/N_TRIALS/EPS ...) do 00_parameters_eng.md bez restatementu liczb | `ENG/glossary_eng.md:29,94,125` = all values owned by `00_parameters_eng.md` (`TF`, `H`, `MIN_TOUCHES`, ... `N_TRIALS`, `CV_SCHEME`, `EPS`, …) ... values in `00_parameters_eng.md` `ENG/Layers_Short_SOT/00_parameters_eng.md:7-27` = Contract parameters (17 keys from `params.json`) ... THRESHOLD_ENTRY 0.60 ... N_TRIALS 200 ... MIN_TOUCHES 2                                                             | ✅ OK        | Glossary NIE restatuje 0.60/200/2 — poprawnie linkuje do domu. Wzorcowe zachowanie.                                                                                                                                                                                                                                     |
| Etykieta wersji triple barrier: TB_v1.1                                                                                          | `ENG/glossary_eng.md:108` = triple barrier / label Y (`TB_v1.1`) `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:29` = `TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24` `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:55` = `L_opp(t)` is moving (the line value at `t`; decision v1.2)                                                                                                             | ⚠️ RYZYKO   | Glossary kojarzy znacznik TB_v1.1 z wpisem L7, ale L7 SOT nie mintuje TB_v1.1 (używa 'decision v1.2'); jedynym domem identyfikatora TB_v1.1 jest L9 LABEL_CONTRACT. Wskaźnik domu w glossary (owned by L7 SOT) nie pokrywa się z miejscem zdefiniowania samego tokenu — ryzyko niejednoznaczności/driftu numeru wersji. |
| Nazwy kanoniczne etykiety Y: Y_entry vs Y_outcome                                                                                | `ENG/glossary_eng.md:108` = triple barrier / label Y (`TB_v1.1`) ... TP → `Y=1`; SL ... → `Y=0`; time → `Y=0` `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:48-50,91` = `Y_entry` ... `Y_outcome` ... `Y_outcome` int {0,1} target                                                                                                                                                                         | ❌ ROZBIEŻNE | Słownik nie definiuje kanonicznych nazw kolumn Y_entry / Y_outcome; zlewa je w jedno 'Y'. Luka kompletności i niespójność nazewnictwa kluczy.                                                                                                                                                                           |
| Notacja wyjścia modelu: p(TP) vs p = model(x)                                                                                    | `ENG/glossary_eng.md:127` = the model returns `p(TP)` and filters the detector's setup signal `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:30` = `p = model(x)`, `p ≥ THRESHOLD_ENTRY → ENTRY` `ENG/Layers_Short_SOT/L10_oos_test_eng.md:10` = the model returns `p = model(x)`                                                                                                                               | ❌ ROZBIEŻNE | Token p(TP) nie występuje w żadnym pliku SOT; SOT konsekwentnie używa p = model(x) / p. Glossary wprowadza odmienną formę notacyjną.                                                                                                                                                                                    |
| Termin cooldown / COOLDOWN                                                                                                       | `ENG/glossary_eng.md` = (brak wpisu 'cooldown' w całym słowniku) `ENG/Layers_Short_SOT/00_conventions_eng.md:13` = All line functions ... `H`, the purge and the cooldown operate on the index `ENG/Layers_Short_SOT/00_parameters_eng.md:42` = `COOLDOWN` | `H` (= 24) | candles | reference design                                                                                                            | ❌ ROZBIEŻNE | Termin używany w cross-cutting rules conventions SOT i w detector reference design, lecz nieobecny w słowniku (purge i embargo są zdefiniowane, cooldown nie). Luka kompletności.                                                                                                                                       |
| Restatement wzoru R0 w słowniku                                                                                                  | `ENG/glossary_eng.md:96` = risk unit `abs(close[t0] − L_opp(t0))`; TP level; `t0 + H`. Definitions owned by L6 SOT. `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:19` = `R0 = abs(close[t0] − L_opp(t0))` — one geometric unit of risk                                                                                                                                                                         | ⚠️ RYZYKO   | Wartości identyczne (nie DIVERGENT), ale glossary restatuje wzór build-critical wbrew własnej deklaracji 'points to the SOT rather than restating it' (glossary:3-7) → ryzyko driftu przy zmianie wzoru w L6.                                                                                                           |
| Restatement wzoru z-score w słowniku                                                                                             | `ENG/glossary_eng.md:107` = z-score — a standardized value `(x − mean)/std` from the rolling window `W_VOL`; `std = 0 → 0` `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:23` = `volume_z_score` | `(v − mean_W) / std_W` ... `std = 0 → 0`                                                                                                                                                                 | ⚠️ RYZYKO   | Wartość zgodna; restatement wzoru i guarda std=0→0 w słowniku wbrew zasadzie 'point, don't restate' → ryzyko driftu.                                                                                                                                                                                                    |
| Restatement liczby pochodnej rolling lookback = 20                                                                               | `ENG/glossary_eng.md:81` = rolling lookback — the longest backward window of a feature: `max(W_ATR, W_VOL) = 20` candles `ENG/Layers_Short_SOT/L5_time_split_eng.md:8` = rolls in the rolling windows: `max(W_ATR=14, W_VOL=20) = 20` candles                                                                                                                                                                   | ⚠️ RYZYKO   | Glossary podaje gotowy wynik 20 (zależny od W_ATR/W_VOL z 00_parameters). Liczba pochodna w podrzędnym słowniku — ryzyko driftu przy zmianie W_VOL/W_ATR.                                                                                                                                                               |
| Forma terminu 'rejestr hashów': hash registry vs hash register                                                                   | `ENG/glossary_eng.md:135` = hash registry — the hash of each artifact recorded before the test `ENG/Layers_Short_SOT/L10_oos_test_eng.md:5` = the hash of each strategy file goes into the hash register                                                                                                                                                                                                        | ❌ ROZBIEŻNE | Drobna niespójność formy: 'registry' (glossary) vs 'register' (L10 SOT). Naruszenie 'one naming'.                                                                                                                                                                                                                       |
| Definicja Gate (1:1 z conventions)                                                                                               | `ENG/glossary_eng.md:28` = Gate — an automatic pass-on condition (QC on the L3 load; a non-FAIL L8 dashboard before training) `ENG/Layers_Short_SOT/00_conventions_eng.md:50` = Gate — an automatic pass-on condition (QC on the L3 load; a non-FAIL L8 dashboard before training)                                                                                                                              | ✅ OK        | Identyczne sformułowanie — wzorcowa zgodność.                                                                                                                                                                                                                                                                           |
| DET-09 (warunki odrzucenia + counted)                                                                                            | `ENG/glossary_eng.md:98` = DET-09 — a setup with `R0 ≤ 0`, `ATR(t0) ≤ 0` or missing `L_opp` is rejected and counted in the audit `ENG/Layers_Short_SOT/L6_setup_detector_eng.md:29,33` = DET-09: a setup with `R0 ≤ 0`, `ATR(t0) ≤ 0`, or a missing `L_opp` is rejected and counted ... incremented in `det09_rejected`                                                                                         | ✅ OK        | Glossary nie wspomina kanonicznej kolejności guarda (missing_L_opp przed R0≤0) ani nazwy licznika det09_rejected, ale to skrót, nie rozbieżność.                                                                                                                                                                        |
| FEATURE_MANIFEST = 7 X (8 kolumn minus closed_through_line), kolejność zamrożona                                                 | `ENG/glossary_eng.md:104,105` = `FEATURE_MANIFEST` (7 X) — the 8 columns minus `closed_through_line`; order frozen ... `closed_through_line` (audit) ... outside X `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:30-43` = FEATURE_MANIFEST (the 7 X), order frozen ... = the transformer's 8 columns minus `closed_through_line`                                                                           | ✅ OK        |                                                                                                                                                                                                                                                                                                                         |
| Feature Set v1 = 8 cech (lista nazw)                                                                                             | `ENG/glossary_eng.md:103` = Feature Set v1 (8 features) — distance_to_trend_line · distance_to_opposing_line · risk_if_entered_pct · bar_return_pct · body_to_range_ratio · volume_z_score · touch_count · closed_through_line `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:17-25,33-39` = tabela 8 kolumn + FEATURE_MANIFEST 1..7                                                                        | ✅ OK        | Lista nazw cech identyczna z SOT. Glossary deleguje wzory do L7 SOT — poprawnie.                                                                                                                                                                                                                                        |
| label_uniqueness_weight (average uniqueness)                                                                                     | `ENG/glossary_eng.md:109` = sample weight (average uniqueness) ... formula `weight_i = mean_{t∈W_i}(1/c_t)` owned by L7 SOT `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:66-67` = `c_t = |{ j : t ∈ W_j }|` ... `weight_i = mean_{t ∈ W_i} (1 / c_t)`                                                                                                                                                     | ✅ OK        | Wzór zgodny z SOT (1/c_t, NIE poprzedni bug). Glossary restatuje krótki wzór, ale jawnie wskazuje dom L7 — borderline z 'point-not-restate', niska waga.                                                                                                                                                                |
| Partycjonowanie {asset_id} × {direction}                                                                                         | `ENG/glossary_eng.md:111` = partition `{asset_id} × {direction}` — a separate dataset/artifact for each asset × direction pair `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:94` = Partitioning: a separate dataset / artifact per `{asset_id} × {direction}` pair                                                                                                                                         | ✅ OK        |                                                                                                                                                                                                                                                                                                                         |
| L8 quality validation: mierzy/raportuje, nic nie naprawia; FAIL blokuje L9                                                       | `ENG/glossary_eng.md:114,119` = quality validation — measures and reports, fixes nothing ... any FAIL = gate closed → L9 blocked `ENG/Layers_Short_SOT/L8_data_quality_eng.md:3-5` = measures and reports; it fixes nothing ... any FAIL closes the gate and training (L9) does not start                                                                                                                       | ✅ OK        |                                                                                                                                                                                                                                                                                                                         |
| det09_rejected = WARN-only (nigdy FAIL)                                                                                          | `ENG/glossary_eng.md:117-119` = gaps / zero-values / alarms (OK/WARN/FAIL) — glossary nie nazywa pojedynczych liczników L8 `ENG/Layers_Short_SOT/L8_data_quality_eng.md:49,99` = `det09_rejected` rate: WARN-only diagnostic (never FAIL)                                                                                                                                                                       | ✅ OK        | Glossary celowo nie definiuje nazw liczników L8 (deleguje do L8 SOT/quality_gate_spec); to skrót, nie rozbieżność. Brak terminów licznikowych nie jest 'martwym terminem' ani luką wymaganą do raportowania.                                                                                                            |
| One-shot / OOS testowany raz                                                                                                     | `ENG/glossary_eng.md:27,139` = One-shot — the OOS window is tested once ... the OOS result never goes back into tuning `ENG/Layers_Short_SOT/00_conventions_eng.md:49 ; ENG/Layers_Short_SOT/L10_oos_test_eng.md:23` = One-shot — the OOS window is tested once ... never goes back into tuning                                                                                                                 | ✅ OK        |                                                                                                                                                                                                                                                                                                                         |
| OOS okno dat 2024-01-02 → 2026-05-29 (NIE restatowane w glossary)                                                                | `ENG/glossary_eng.md:79,134` = Dates owned by L5_time_split_eng.md ... entry rule and TB exits are owned by L10 SOT (brak konkretnych dat) `ENG/Layers_Short_SOT/L10_oos_test_eng.md:7` = OOS window `2024-01-02 → 2026-05-29`                                                                                                                                                                                  | ✅ OK        | Glossary poprawnie NIE restatuje dat OOS/Warm-up — linkuje do L5/L10 SOT. Wzorcowe.                                                                                                                                                                                                                                     |
| Champion / meta-labeling (model filtruje sygnał detektora)                                                                       | `ENG/glossary_eng.md:127,128` = meta-labeling — the model ... filters the detector's setup signal ... champion — retrain on the full Train with the best trial's parameters; one model per {asset × direction} `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:17,18` = champion = retrain on the full Train with the parameters of the best trial ... the model filters the trend-line setup signal             | ✅ OK        |                                                                                                                                                                                                                                                                                                                         |


### Oś L — Integralność linków i artefaktów

**Werdykt:** Wszystkie aktywne linki markdown (w tym zewnętrzne ../B_Features/...) w audytowanych plikach A_Layers rozwiązują się do istniejących plików, a lista CARD_FILES (11) zgadza się 1:1 z kartami na dysku i ze stopką "/ 11"; jedyne realne problemy to zweryfikowanie nieaktualnego PDF (Master_Layer_Cards_Print_A4.pdf wygenerowany 2026-06-16, podczas gdy wszystkie 11 kart .md zmieniono 2026-06-17), hardcodowana lista CARD_FILES + stopka "/ 11" jako ryzyko driftu, oraz niespójnie zakorzenione (część od A_Layers, część od katalogu kart) inline-ścieżki w README_cards.md.  
**Statusy wierszy:** ✅14 · ⚠️3 · ❔1


| Fakt                                                                                                                                                                                                                                                                                                                                                                        | Źródła (`plik:linia` = wartość)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Status        | Uwaga                                                                                                                               |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Aktywne linki markdown ]( ) w README_A_Layer.md wskazują istniejące pliki (ENG/Layers_Short_SOT/, ENG/readme_eng.md, ENG/build_contract_eng.md, ENG/detector_algorithm_eng.md, ENG/quality_gate_spec_eng.md, ENG/glossary_eng.md, ENG/summary_rules_eng.md, config/params.json, config/universe.txt, viz/main_data_flow.html, acceptance_data_transform_cards/)             | `README_A_Layer.md:6-13` = 14 linków, wszystkie OK po realpath -m względem A_Layers/                                                                                                                                                                                                                                                                                                                                                                                                                                                | ✅ OK          |                                                                                                                                     |
| Zewnętrzny link ../B_Features/ z README_A_Layer.md istnieje                                                                                                                                                                                                                                                                                                                 | `README_A_Layer.md:16` = `[../B_Features/](../B_Features/)` -> Plan/B_Features (EXISTS)                                                                                                                                                                                                                                                                                                                                                                                                                                             | ✅ OK          |                                                                                                                                     |
| Zewnętrzny link ../../B_Features/feature_explanation_plan_b_eng.md (z ENG/readme_eng.md, ENG/build_contract_eng.md, ENG/glossary_eng.md) istnieje                                                                                                                                                                                                                           | `ENG/readme_eng.md:45` = -> Plan/B_Features/feature_explanation_plan_b_eng.md (EXISTS, 5028 B) `ENG/build_contract_eng.md:94` = -> Plan/B_Features/feature_explanation_plan_b_eng.md (EXISTS) `ENG/glossary_eng.md:150` = -> Plan/B_Features/feature_explanation_plan_b_eng.md (EXISTS)                                                                                                                                                                                                                                             | ✅ OK          |                                                                                                                                     |
| Zewnętrzny link ../../../B_Features/ z ENG/Layers_Short_SOT/README.md istnieje                                                                                                                                                                                                                                                                                              | `ENG/Layers_Short_SOT/README.md:74` = -> Plan/B_Features (RESOLVED EXISTS)                                                                                                                                                                                                                                                                                                                                                                                                                                                          | ✅ OK          |                                                                                                                                     |
| Wszystkie aktywne linki markdown w ENG/readme_eng.md (22 linki: SOT folder, 4× 00_*, L1..L10, 5 towarzyszy, B_Features, ../README_A_Layer.md) wskazują istniejące pliki                                                                                                                                                                                                     | `ENG/readme_eng.md:4-48` = 22/22 OK po realpath -m względem ENG/                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | ✅ OK          |                                                                                                                                     |
| Wszystkie aktywne linki markdown w ENG/Layers_Short_SOT/README.md (.., 4× 00_*, L1..L10, 6 towarzyszy ../, ../../../B_Features/) wskazują istniejące pliki                                                                                                                                                                                                                  | `ENG/Layers_Short_SOT/README.md:9-74` = 22/22 OK po realpath -m względem ENG/Layers_Short_SOT/                                                                                                                                                                                                                                                                                                                                                                                                                                      | ✅ OK          |                                                                                                                                     |
| Wszystkie aktywne linki markdown w ENG/build_contract_eng.md (SOT folder, README, 4× 00_*, L1..L10, detector/quality_gate/glossary towarzysze, B_Features) wskazują istniejące pliki                                                                                                                                                                                        | `ENG/build_contract_eng.md:4-94` = 25/25 OK po realpath -m względem ENG/                                                                                                                                                                                                                                                                                                                                                                                                                                                            | ✅ OK          |                                                                                                                                     |
| Wszystkie aktywne linki markdown w ENG/glossary_eng.md (SOT folder, 00_conventions, 00_parameters, L3/L5/L6/L7/L8/L9/L10, detector/quality_gate towarzysze, B_Features) wskazują istniejące pliki                                                                                                                                                                           | `ENG/glossary_eng.md:5-150` = 14/14 OK po realpath -m względem ENG/                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | ✅ OK          |                                                                                                                                     |
| Aktywne linki markdown w ENG/summary_rules_eng.md (Layers_Short_SOT/, Layers_Short_SOT/README.md) wskazują istniejące pliki                                                                                                                                                                                                                                                 | `ENG/summary_rules_eng.md:3,30` = 2/2 OK po realpath -m względem ENG/                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ✅ OK          |                                                                                                                                     |
| Aktywne linki markdown w acceptance_data_transform_cards/README_cards.md (../README_A_Layer.md, ../ENG/Layers_Short_SOT/README.md) wskazują istniejące pliki                                                                                                                                                                                                                | `acceptance_data_transform_cards/README_cards.md:33` = 2/2 OK po realpath -m względem acceptance_data_transform_cards/                                                                                                                                                                                                                                                                                                                                                                                                              | ✅ OK          |                                                                                                                                     |
| Aktywne linki markdown w acceptance_data_transform_cards/card_template.md (../ENG/Layers_Short_SOT/00_input_contract_eng.md i {{LAYER_SOT_FILE}} placeholder) używają poprawnego prefiksu ../ENG/Layers_Short_SOT/                                                                                                                                                          | `acceptance_data_transform_cards/card_template.md:17` = `[00_input_contract_eng.md](../A_Layers/ENG/Layers_Short_SOT/00_input_contract_eng.md)` — rozwiązuje się poprawnie                                                                                                                                                                                                                                                                                                                                                                   | ✅ OK          |                                                                                                                                     |
| Lista CARD_FILES w generate_master_layer_cards_pdf.py odpowiada faktycznym plikom kart na dysku                                                                                                                                                                                                                                                                             | `acceptance_data_transform_cards/generate_master_layer_cards_pdf.py:17-29` = 11 wpisów: 00_Crosscutting_Overview_Card.md + L01..L10_*_Card.md `acceptance_data_transform_cards/` = 11 kart .md na dysku, każdy wpis CARD_FILES = OK (existuje)                                                                                                                                                                                                                                                                                      | ✅ OK          |                                                                                                                                     |
| Stopka PDF '/ 11' == len(CARD_FILES)(11) == liczba realnych kart (11) — ale wartość zahardkodowana (drift)                                                                                                                                                                                                                                                                  | `acceptance_data_transform_cards/generate_master_layer_cards_pdf.py:53` = f"Page {self.page_no()} / 11 ..." (literal 11) `acceptance_data_transform_cards/generate_master_layer_cards_pdf.py:17-29` = len(CARD_FILES)=11 `README_A_Layer.md:13` = "11 cards (L1–L10 + 00 overview)"                                                                                                                                                                                                                                                 | ⚠️ RYZYKO     |                                                                                                                                     |
| PDF Master_Layer_Cards_Print_A4.pdf istnieje, ale jest starszy niż WSZYSTKIE 11 kart .md (wygenerowany przed ostatnią edycją źródeł)                                                                                                                                                                                                                                        | `acceptance_data_transform_cards/Master_Layer_Cards_Print_A4.pdf` = mtime 2026-06-16 20:42:18, size 58087 B `acceptance_data_transform_cards/*.md` = wszystkie 11 kart + README_cards.md zmienione 2026-06-17 (10:30–11:24), tj. PO PDF                                                                                                                                                                                                                                                                                             | ⚠️ RYZYKO     |                                                                                                                                     |
| Inline-ścieżki backtick w README_cards.md są niespójnie zakorzenione: część od A_Layers-root (`ENG/Layers_Short_SOT/`, `viz/main_data_flow.html`, `B_Features/ENG/Stages_Short_SOT/`), część od katalogu kart (`card_template.md`, `L01_..._Card.md`); linia 31 `../B_Features/ENG/Stages_Short_SOT/` rozwiązana z katalogu kart trafia w nieistniejące A_Layers/B_Features | `acceptance_data_transform_cards/README_cards.md:9` = `B_Features/ENG/Stages_Short_SOT/` (bez ../) oraz `viz/main_data_flow.html`, `ENG/Layers_Short_SOT/` — root od A_Layers `acceptance_data_transform_cards/README_cards.md:31` = `../B_Features/ENG/Stages_Short_SOT/` — z katalogu kart rozwiązuje się do A_Layers/B_Features (BROKEN); poprawny target to ../../B_Features/ENG/Stages_Short_SOT/ `../B_Features/ENG/Stages_Short_SOT/` = katalog EXISTS pod Plan/B_Features/ENG/Stages_Short_SOT/ (20 plików F0–F14 + README) | ⚠️ RYZYKO     |                                                                                                                                     |
| Cel referencji README_cards.md: ../B_Features/ENG/Stages_Short_SOT/ (kanonicznie spod Plan/B_Features) istnieje                                                                                                                                                                                                                                                             | `Plan/B_Features/ENG/Stages_Short_SOT/` = EXISTS: 00_*, F0..F14_*_eng.md, README.md                                                                                                                                                                                                                                                                                                                                                                                                                                                 | ✅ OK          |                                                                                                                                     |
| Claim README_cards.md: 'F-stages (F1/F7/F8/F11) directly inline the L5/L7/L8/L10 facts' — pliki F-stage faktycznie odwołują się do tych L#                                                                                                                                                                                                                                  | `../B_Features/ENG/Stages_Short_SOT/F1,F7,F8,F11_*_eng.md` = F1→L5, F7→L7, F8→L8, F11→L10 (grep L#)                                                                                                                                                                                                                                                                                                                                                                                                                                 | ✅ OK          | Treść B_Features poza zakresem osi L (sprawdzono tylko istnienie i obecność odniesień L#).                                          |
| Plik PDF jest świeży względem .md (staleność z treści .md nieweryfikowalna) — ograniczenie audytu                                                                                                                                                                                                                                                                           | `acceptance_data_transform_cards/Master_Layer_Cards_Print_A4.pdf` = treść PDF (binarna) nie była renderowana/porównywana z .md; weryfikacja oparta o mtime                                                                                                                                                                                                                                                                                                                                                                          | ❔ NIEUSTALONE | Zgodność TREŚCI PDF z kartami .md nieweryfikowalna bez renderu; mtime dowodzi jednak staleności (PDF starszy od wszystkich źródeł). |


## 5. Findingi potwierdzone (po weryfikacji adwersaryjnej)

Razem **32** findingów, posortowane wg końcowej severity. Każdy zawiera dowody `plik:linia`, wpływ i rekomendację (domyślnie: "dostosuj artefakt podrzędny do SOT").

### Severity: MEDIUM

#### [B1] Sprzeczność wewnątrz SOT co do liczby parametrów: params.json ma 18 skalarnych kluczy top-level, a narracje liczą '17' niespójnie (EPS raz wliczany, raz nie)

- **Oś:** B (Parametry (rejestr params.json ↔ 00_parameters)) · **severity:** `HIGH`→`MEDIUM` · **kategoria:** (a) · **głosy:** 3/3
- **Dowody:**
  - `config/params.json:2-19` — TF, H, MIN_TOUCHES, W_VOL, W_ATR, ATR_VARIANT, PRICE_VIEW, EPS, BARRIER_MODE, DISTANCE_NORM, THRESHOLD_ENTRY, PURGE_CANDLES, EMBARGO_SESSIONS, N_TRIALS, CV_SCHEME, ESTIMATOR, TUNER, TOUCH_TOL = 18 skalarnych kluczy top-level
  - `ENG/Layers_Short_SOT/00_parameters_eng.md:7` — ## Contract parameters (17 keys from `params.json`) — tabela 17 wierszy z EPS jako wierszem nr 8, TOUCH_TOL opisany osobno
  - `ENG/Layers_Short_SOT/README.md:50` — All parameters (17 `params.json` keys + EPS + `TOUCH_TOL` + detector `k`/`LOOKBACK`/`COOLDOWN` + L8 threshold constants)
  - `ENG/Layers_Short_SOT/README.md:26` — 17 keys + EPS + detector reference values + L8 threshold constants
- **Wpływ:** Dwa pliki należące do SOT (00_parameters_eng.md oraz README.md) podają sprzeczną interpretację liczby '17': w 00_parameters EPS jest WEWNĄTRZ siedemnastki (wiersz 8), natomiast README.md:50 i README.md:26 traktują EPS jako dodatek POZA siedemnastką ('17 keys + EPS'). Faktycznie params.json ma 18 skalarów top-level (siedemnastka z tabeli + TOUCH_TOL). Czytelnik weryfikujący 'mirror of params.json' nie wie, które keys liczą się do 17, co podważa rolę 00_parameters jako rejestru i utrudnia detekcję realnego brakującego/nadmiarowego klucza. To niespójność samego SOT (najwyższy priorytet).
- **Rekomendacja:** Ujednolicić konwencję liczenia wewnątrz SOT i nazwać ją wprost: params.json ma 18 skalarnych kluczy top-level (17 z tabeli kontraktu + TOUCH_TOL) + 3 bloki obiektowe (splits=6, detector=3, l8=11). Albo (a) zmienić nagłówek 00_parameters na '18 scalar keys' i wciągnąć TOUCH_TOL do tabeli kontraktu, albo (b) wszędzie liczyć konsekwentnie tak samo. Przede wszystkim usunąć '+ EPS' z README.md:50 i :26 (EPS jest jednym z kluczy tabeli, nie dodatkiem), tak by README i 00_parameters mówiły to samo.

#### [B2] Overview Card podwójnie liczy EPS i deklaruje 'exactly 17 keys + EPS' niezgodnie z tabelą SOT, w której EPS jest jednym z 17

- **Oś:** B (Parametry (rejestr params.json ↔ 00_parameters)) · **severity:** `MEDIUM` · **kategoria:** (a) · **głosy:** 3/3
- **Dowody:**
  - `acceptance_data_transform_cards/00_Crosscutting_Overview_Card.md:19` — Canonical params file: `config/params.json` (exactly 17 keys + EPS + detector constants + L8 thresholds)
  - `ENG/Layers_Short_SOT/00_parameters_eng.md:7` — ## Contract parameters (17 keys from `params.json`)  [EPS jest wierszem nr 8 wewnątrz tej tabeli — ENG/Layers_Short_SOT/00_parameters_eng.md:18]
- **Wpływ:** Karta (artefakt podrzędny) liczy EPS poza siedemnastką ('17 keys + EPS'), podczas gdy wzorzec SOT 00_parameters trzyma EPS wewnątrz '17 keys'. To utrwala błędną liczbę i powiela rozbieżność B1 na poziomie kart akceptacyjnych. Dodatkowo Overview Card nie wspomina TOUCH_TOL jako osobnego skalara, więc faktyczna liczba 18 skalarów top-level znika z opisu.
- **Rekomendacja:** Dostosować Overview Card do SOT: po ustaleniu kanonicznej konwencji (B1) zapisać dokładnie tak samo, np. '18 scalar top-level keys (incl. EPS, TOUCH_TOL) + splits/detector/l8 blocks', i nie wymieniać EPS jako dodatku poza liczbą kluczy. Domyślnie: dostosuj artefakt podrzędny do SOT.

#### [B3] Viz wprowadza pełną przestrzeń przeszukiwania Optuny (zakresy hiperparametrów XGBoost), której SOT nigdzie nie definiuje

- **Oś:** B (Parametry (rejestr params.json ↔ 00_parameters)) · **severity:** `MEDIUM` · **kategoria:** (d) · **głosy:** 3/3
- **Dowody:**
  - `viz/main_data_flow.html:356-358` — space:{max_depth:'3–9',learning_rate:'0.01–0.3 (log)',n_estimators:'100–1200',min_child_weight:'1–20',subsample:'0.5–1.0',colsample_bytree:'0.5–1.0',reg_lambda:'1e-3–10 (log)',scale_pos_weight:'0.5–4'}
  - `viz/main_data_flow.html:1782` — search space: depth 3–9 · lr 0.01–0.3 log · estimators 100–1200 · subsample/colsample 0.5–1 · λ 1e-3–10 · spw 0.5–4
  - `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:6-18` — [sekcja Tuning + training definiuje budget/sampler/pruner/objective/sample weights — BRAK zakresów przestrzeni przeszukiwania]
  - `ENG/Layers_Short_SOT/00_parameters_eng.md:24` — `N_TRIALS`  `200`  Optuna trial budget  [00_parameters nie zawiera żadnych zakresów search-space]
- **Wpływ:** Viz (artefakt podrzędny) wprowadza osiem konkretnych zakresów hiperparametrów jako fakty build-critical, których SOT (params.json, 00_parameters, L9) nie definiuje. Narusza zasadę 'one home per fact' i tworzy ryzyko driftu: gdy ktoś zmieni zakresy w pipeline lub params.json, viz pozostanie z innymi liczbami i nikt ich nie wykryje, bo nie mają kanonicznego domu.
- **Rekomendacja:** Dodać przestrzeń przeszukiwania jako fakt do SOT — najlepiej blok `optuna_space` w config/params.json + tabela w 00_parameters_eng.md (lub w L9_optuna_xgboost_eng.md jako home). Następnie viz powinien tylko cytować ten home. Jeśli zakresy mają pozostać 'reference design', oznaczyć je tak jak detector reference-design values, ale i tak osadzić w SOT, a viz nie powinien wprowadzać liczb spoza SOT.

#### [E1] Liczność foldów CV k=4 jest literałem w prozie SOT L9, bez domu w params.json/rejestrze parametrów

- **Oś:** E (Split czasowy (daty/purge/embargo/CV)) · **severity:** `MEDIUM` · **kategoria:** (d) · **głosy:** 3/3
- **Dowody:**
  - `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:12` — objective: AUC-PR over purged walk-forward CV (k=4 folds), in Train only
  - `ENG/Layers_Short_SOT/00_parameters_eng.md:5` — This file owns every parameter value; companion docs reference it and restate no number.
  - `config/params.json:16` — "CV_SCHEME": "purged_walk_forward"  (brak klucza k / n_folds / CV_FOLDS)
  - `acceptance_data_transform_cards/L05_Time_Split_Card.md:37` — CV scheme = purged walk-forward (k=4)
  - `viz/main_data_flow.html:355` — objective:'AUC-PR (mean over k=4 purged walk-forward folds on Train)'
- **Wpływ:** k=4 to liczbowy parametr CV, który steruje walidacją w Train, ale żyje wyłącznie jako literał w jednym zdaniu L9. Rejestr parametrów (00_parameters_eng.md) deklaruje, że params.json 'owns every parameter value' i 'zero thresholds are hardcoded', a mimo to k nie ma klucza w params.json ani wiersza w tabeli 17 kluczy. Karta i viz powtarzają '4'; zmiana liczby foldów wymagałaby ręcznej edycji L9, karty i viz, co łatwo się rozjeżdża (drift) i narusza zasadę 'one home per fact'.
- **Rekomendacja:** Dodać k foldów jako jawny parametr w config/params.json (np. "CV_FOLDS": 4) i wpisać go do rejestru 00_parameters_eng.md (sekcja Contract parameters) jako dom faktu; L9 ma cytować ten parametr zamiast literału '4'. Po nadaniu domu — karta (L05:15,37) i viz (355) referują do parametru bez redefinicji. Alternatywnie, jeśli k=4 ma świadomie pozostać reference-design (jak blok detector), oznaczyć to w 00_parameters i zsynchronizować sformułowanie.

#### [J1] viz.OPTUNA.space wprowadza pełną przestrzeń przeszukiwania hiperparametrów, której SOT (L9 ani params.json) nie definiuje

- **Oś:** J (Model L9 / ewaluacja L10 / metryki) · **severity:** `HIGH`→`MEDIUM` · **kategoria:** (d) · **głosy:** 3/3
- **Dowody:**
  - `viz/main_data_flow.html:356` — space:{max_depth:'3–9',learning_rate:'0.01–0.3 (log)',n_estimators:'100–1200', min_child_weight:'1–20',subsample:'0.5–1.0',colsample_bytree:'0.5–1.0', reg_lambda:'1e-3–10 (log)',scale_pos_weight:'0.5–4'}
  - `viz/main_data_flow.html:1782` — search space: depth 3–9 · lr 0.01–0.3 log · estimators 100–1200 · subsample/colsample 0.5–1 · λ 1e-3–10 · spw 0.5–4
  - `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:6` — ## Tuning + training [sekcja nie podaje żadnych zakresów hiperparametrów]
  - `config/params.json:15` — "N_TRIALS": 200 [params.json nie zawiera kluczy max_depth/learning_rate/n_estimators/min_child_weight/subsample/colsample/reg_lambda/scale_pos_weight]
- **Wpływ:** viz definiuje osiem konkretnych zakresów (granice, skala log, spw) będących twardymi faktami inżynierskimi, których żaden plik SOT nie posiada. Narusza zasadę 'one home per fact': przestrzeń przeszukiwania jest realnym parametrem buildu L9 i powinna mieć dom w SOT. Wartości są zduplikowane w dwóch miejscach viz (linie 356 i 1782) — ryzyko rozjechania między sobą i z kodem przy zmianie zakresu.
- **Rekomendacja:** Dodać przestrzeń przeszukiwania Optuny jako sekcję/blok w SOT — albo nowy blok 'optuna_space' w config/params.json (mirror w 00_parameters_eng.md), albo tabelę w L9_optuna_xgboost_eng.md jako 'reference design (one valid realization)'. Następnie viz.OPTUNA.space i tekst z linii 1782 mają cytować ten jeden dom, a nie definiować zakresy lokalnie. Do czasu osadzenia oznaczyć w viz, że zakresy są reference-design, by nie były czytane jako kanon.

### Severity: LOW

#### [A2] SOT-wewnetrznie: opis registru parametrow podwojnie liczy EPS i pomija TOUCH_TOL

- **Oś:** A (Governance / technika użytkowania / DRY) · **severity:** `MEDIUM`→`LOW` · **kategoria:** (a) · **głosy:** 3/3
- **Dowody:**
  - `ENG/Layers_Short_SOT/README.md:26` — the single parameter registry (mirror of config/params.json): 17 keys + EPS + detector reference values + L8 threshold constants
  - `config/params.json:2-19` — 18 kluczy skalarnych: 17 + TOUCH_TOL; EPS jest jednym z 17 (00_parameters_eng.md:18)
- **Wpływ:** 17 keys + EPS liczy EPS dwukrotnie (EPS jest w tabeli 17 kluczy) i pomija TOUCH_TOL (18-ty klucz); wewnetrzna niespojnosc SOT propagowana do karty (A5).
- **Rekomendacja:** Ujednolicic opis do 17 contract keys (EPS included) + TOUCH_TOL + detector + l8; usunac osobne + EPS z README.md:26 i :50.

#### [A4] SOT-wewnetrznie: 00_parameters_eng.md wskazuje nieistniejaca sciezke kanoniczna Plan/config/params.json

- **Oś:** A (Governance / technika użytkowania / DRY) · **severity:** `MEDIUM`→`LOW` · **kategoria:** (a) · **głosy:** 3/3
- **Dowody:**
  - `ENG/Layers_Short_SOT/00_parameters_eng.md:3-4` — canonical file: Plan/config/params.json, mirror of the source config/params.json
  - `config/params.json` — plik istnieje wylacznie jako Plan/A_Layers/config/params.json; Plan/config/ nie istnieje
  - `ENG/Layers_Short_SOT/00_conventions_eng.md:51` — the only configuration site is config/params.json
- **Wpływ:** Kanoniczny plik Plan/config/params.json nie istnieje, sprzecznie z 00_conventions_eng.md:51; wprowadza dwa konkurujace kanoniczne miejsca konfiguracji.
- **Rekomendacja:** Usunac odwolanie do Plan/config/params.json; pozostawic config/params.json (= Plan/A_Layers/config/params.json).

#### [A5] Crosscutting Card propaguje 17 keys + EPS, dodaje exactly 17 keys i zmyslone 20+ checklist items

- **Oś:** A (Governance / technika użytkowania / DRY) · **severity:** `MEDIUM`→`LOW` · **kategoria:** (a) · **głosy:** 2/3
- **Dowody:**
  - `acceptance_data_transform_cards/00_Crosscutting_Overview_Card.md:19` — config/params.json (exactly 17 keys + EPS + detector constants + L8 thresholds)
  - `acceptance_data_transform_cards/00_Crosscutting_Overview_Card.md:21` — Definition of Done: 20+ checklist items with layer ownership
  - `ENG/Layers_Short_SOT/00_definition_of_done_eng.md:6-20` — 15 pozycji checklisty
- **Wpływ:** Karta wprowadza wartosci nieosadzone w SOT: exactly 17 keys (faktycznie 18) i Definition of Done 20+ items (SOT ma 15); narusza one home per fact i moze zmylic osobe zatwierdzajaca.
- **Rekomendacja:** Zastapic 20+ przez 15 items (lub odeslac do 00_definition_of_done_eng.md); usunac exactly 17 keys; ujednolicic z A2.

#### [A6] build_contract_eng.md deklaruje restates no fact a powtarza szesc wartosci parametrow

- **Oś:** A (Governance / technika użytkowania / DRY) · **severity:** `LOW` · **kategoria:** (e) · **głosy:** 2/3
- **Dowody:**
  - `ENG/build_contract_eng.md:6` — It restates no fact; on any divergence, the SOT wins.
  - `ENG/build_contract_eng.md:85-86` — the canonical parameters (MIN_TOUCHES=2, H=24, W_ATR=14, ATR_VARIANT=wilder, PRICE_VIEW=raw_usd_view, EPS=1e-9)
- **Wpływ:** Doslowne powtorzenie wartosci to restate a value zakazany przez DRY i przeczy deklaracji restates no fact; realny punkt driftu.
- **Rekomendacja:** Usunac zaszyte wartosci z build_contract_eng.md:85-86; zostawic same nazwy parametrow z odeslaniem do 00_parameters_eng.md.

#### [B4] Wartość k=4 (liczba foldów CV) żyje wyłącznie w prozie SOT L9, nie jest kluczem w params.json — ryzyko driftu rejestru

- **Oś:** B (Parametry (rejestr params.json ↔ 00_parameters)) · **severity:** `LOW` · **kategoria:** (e) · **głosy:** 3/3
- **Dowody:**
  - `config/params.json:16` — "CV_SCHEME": "purged_walk_forward"  [params.json koduje tylko schemat, bez liczby foldów k]
  - `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:12` — objective: AUC-PR over purged walk-forward CV (k=4 folds), in Train only
  - `acceptance_data_transform_cards/L05_Time_Split_Card.md:37` — CV scheme = purged walk-forward (k=4)
  - `viz/main_data_flow.html:355` — objective:'AUC-PR (mean over k=4 purged walk-forward folds on Train)'
- **Wpływ:** k=4 jest parametrem build-critical (kształtuje CV i objective), ale nie ma reprezentacji w config/params.json — rejestr deklarowany jako 'jedyne miejsce konfiguracji' go nie zawiera. Jest osadzony tylko w prozie L9 i powielony w karcie L05 oraz viz. Zmiana k w jednym miejscu nie zostanie wymuszona na pozostałych (params.json nie waliduje k), co stwarza ryzyko rozjechania się wartości.
- **Rekomendacja:** Rozważyć dodanie `cv_folds: 4` (lub `CV_FOLDS`) do config/params.json i 00_parameters_eng.md, by k=4 miał dom w rejestrze parametrów; alternatywnie jawnie udokumentować w 00_parameters, że k=4 jest własnością L9 i celowo poza params.json. Karta L05 i viz powinny dalej tylko cytować ten home.

#### [D2] Ekstrakcja tytułu karty w generatorze PDF zależy od magicznego łańcucha 'Master Layer Card' obecnego w nagłówku (kruchy kontrakt)

- **Oś:** D (Tożsamość warstw (nazwy/kolejność/liczba)) · **severity:** `LOW` · **kategoria:** (e) · **głosy:** 3/3
- **Dowody:**
  - `acceptance_data_transform_cards/generate_master_layer_cards_pdf.py:62-65` — for line in lines:             if line.startswith("# ") and "Master Layer Card" in line:                 title = line.lstrip("# ").strip()                 break
  - `acceptance_data_transform_cards/L01_Source_Alpaca_Card.md:1` — # L1 · Source: Alpaca — Master Layer Card (Acceptance Form)
- **Wpływ:** Generator wyciąga tytuł strony PDF tylko z linii # zawierającej dosłownie 'Master Layer Card'. Dziś wszystkie 11 kart spełnia ten warunek, więc działa poprawnie. Jednak gdyby kiedyś nagłówek karty zmieniono (np. na samą nazwę warstwy bez frazy 'Master Layer Card', spójną z SOT po D1), tytuł cicho spadłby do domyślnego 'Master Layer Card', a PDF straciłby identyfikację warstwy — bez błędu, bez ostrzeżenia. To ryzyko driftu między konwencją nagłówków SOT/kart a hardkodem w generatorze.
- **Rekomendacja:** Uodpornij ekstrakcję w generate_master_layer_cards_pdf.py: bierz pierwszą linię zaczynającą się od '# ' jako tytuł (bez wymogu frazy 'Master Layer Card'), albo waliduj i wypisz WARNING, gdy fraza nie wystąpi. Dzięki temu zmiana nagłówków kart pod SOT (D1) nie rozjedzie się z PDF.

#### [D3] Kolejność/tożsamość warstw w viz utrzymywana przez trzy równoległe hardcodowane listy bez asercji długości (ryzyko cichego rozjazdu)

- **Oś:** D (Tożsamość warstw (nazwy/kolejność/liczba)) · **severity:** `LOW` · **kategoria:** (e) · **głosy:** 3/3
- **Dowody:**
  - `viz/main_data_flow.html:529` — var MODE_KEYS=['overview','dataflow','qc','split','setup','dq','optuna','artifact','oos','leak']; // keys 1-9,0 → mode (single source)
  - `viz/main_data_flow.html:418` — var BND_DZ=[189,189,192,189,189,189,185,189,202];   // 9 boundaries (10 levels): inserted L6 detector boundary
  - `viz/main_data_flow.html:428-494` — {id:'L1',lev:0,...} ... {id:'L10',lev:9,...} (lev wpisany ręcznie w każdym z 10 węzłów)
- **Wpływ:** Tożsamość i kolejność warstw w wizualizacji wynika z trzech niezależnych, ręcznie utrzymywanych struktur: PIPELINE.nodes[].lev (0..9), MODE_KEYS (10 trybów) i BND_DZ (9 separatorów). Dziś wszystkie są spójne (10 warstw, 9 granic). Brak jest jednak asercji runtime sprawdzającej, że len(nodes)==len(MODE_KEYS)==len(BND_DZ)+1 oraz że lev tworzą ciągłą sekwencję 0..n-1. Wstawienie/usunięcie warstwy (jak udokumentowane 'inserted L6 detector boundary') wymaga ręcznej, skorelowanej edycji trzech list — łatwe do rozjechania bez sygnału błędu.
- **Rekomendacja:** Dodaj w viz lekką asercję inicjalizacyjną (np. console.assert / throw) sprawdzającą: PIPELINE.nodes.length===MODE_KEYS.length, BND_DZ.length===PIPELINE.edges.length===PIPELINE.nodes.length-1, oraz że lev to permutacja 0..n-1. Alternatywnie wyprowadź BND_DZ/MODE_KEYS z PIPELINE.nodes, by była jedna lista źródłowa kolejności.

#### [E2] viz wprowadza wartości frakcji okien (frac 0.075/0.695/0.230, 'OOS frac'=0.23) nieosadzone w SOT

- **Oś:** E (Split czasowy (daty/purge/embargo/CV)) · **severity:** `LOW` · **kategoria:** (d) · **głosy:** 3/3
- **Dowody:**
  - `viz/main_data_flow.html:333` — {id:'warmup',...frac:0.075, ... } / train frac:0.695 (l.335) / oos frac:0.230 (l.337)
  - `viz/main_data_flow.html:458` — metric:{label:'OOS frac',value:'0.23'}
  - `ENG/Layers_Short_SOT/L5_time_split_eng.md:1` — (cały plik L5 — SOT nie definiuje żadnej wartości frakcji długości okresów)
- **Wpływ:** Frakcje 0.075/0.695/0.230 oraz metryka 'OOS frac'=0.23 to wartości, których SOT nigdzie nie definiuje (kategoria d — artefakt podrzędny wprowadza wartość bez domu). Są wprawdzie spójne z arytmetyką kalendarzową (długości okien: 0.075 / 0.692 / 0.231, suma 0.998; viz-owa funkcja dord() daje 0.075/0.692/0.231) i sumują się do 1.0, więc nie ma realnej rozbieżności wartości — ale frac jest zaszyty jako stała ręczna obok dat. Jeśli ktoś zmieni daty w params.json, frac nie przeliczy się automatycznie (jest niezależnym literałem) i prezentacja rozjedzie się z rzeczywistymi proporcjami → ryzyko driftu.
- **Rekomendacja:** Potraktować frac jako wartość czysto prezentacyjną i wyliczać ją w viz z dat (funkcje dfrac/SPLIT_SPAN już istnieją — l.343-347 — wystarczy zastąpić stały frac wyliczeniem b._f1-b._f0), eliminując ręczny literał. Metrykę 'OOS frac' na node L5 (l.458) również wyprowadzić z dat lub oznaczyć jako 'derived (display only)'. Nie wymaga zmian w SOT — frakcje pozostają poza zakresem SOT (są pochodną dat, których dom jest w params.json).

#### [F1] Brak jawnej tabeli mapowania symbol SOT -> klucz JSON dla detektora (k->pivot_k, LOOKBACK->lookback_candles, COOLDOWN->cooldown_candles)

- **Oś:** F (Detektor L6 (kontrakt + reference algorithm + wartości)) · **severity:** `MEDIUM`→`LOW` · **kategoria:** (b) · **głosy:** 3/3
- **Dowody:**
  - `ENG/Layers_Short_SOT/00_parameters_eng.md:32-42` — ## Detector reference-design values (`detector` block + top-level `TOUCH_TOL`) ... Mirrored in `config/params.json` (`detector` block, plus top-level `TOUCH_TOL`).  `k` (pivot strength)  `3`  ...  `LOOKBACK` (fit window)  `120`  ...  `COOLDOWN`  `H` (= 24) 
  - `config/params.json:28-32` — "detector": { "pivot_k": 3, "lookback_candles": 120, "cooldown_candles": 24 }
- **Wpływ:** SOT (00_parameters) deklaruje regułę mirror 'mirror of config/params.json', lecz tabela detektora używa symboli k/LOOKBACK/COOLDOWN, podczas gdy config używa innych identyfikatorów kluczy (pivot_k/lookback_candles/cooldown_candles). Mapowanie jest dorozumiane przez kolejność i opis, nie jawne. Czytelnik/automat weryfikujący mirror nie ma jednoznacznego klucza dopasowania symbol<->JSON-key; podatne na pomyłkę przy edycji lub przy dodaniu czwartego parametru detektora. (TOUCH_TOL i MIN_TOUCHES/W_ATR są bezpieczne, bo klucz JSON == symbol.)
- **Rekomendacja:** W SOT 00_parameters (tabela 'Detector reference-design values') dodać kolumnę 'params.json key' z jawnym mapowaniem: k -> detector.pivot_k, LOOKBACK -> detector.lookback_candles, COOLDOWN -> detector.cooldown_candles, TOUCH_TOL -> TOUCH_TOL (top-level). To utrzymuje SOT jako wzorzec i czyni regułę mirror weryfikowalną mechanicznie. Alternatywnie (mniej preferowane) ujednolicić nazwy kluczy JSON do symboli SOT.

#### [F2] config pinuje cooldown_candles=24 jako literał zamiast pochodnej COOLDOWN=H — ryzyko rozjazdu przy zmianie H

- **Oś:** F (Detektor L6 (kontrakt + reference algorithm + wartości)) · **severity:** `LOW` · **kategoria:** (e) · **głosy:** 3/3
- **Dowody:**
  - `ENG/Layers_Short_SOT/00_parameters_eng.md:42` —  `COOLDOWN`  `H` (= 24)  candles  reference design (one valid realization) 
  - `config/params.json:3,13,31` — "H": 24, ... "PURGE_CANDLES": 24, ... "detector": { ... "cooldown_candles": 24 }
- **Wpływ:** SOT definiuje COOLDOWN jako pochodną H (COOLDOWN=H), a H jest oznaczone jako 'tuned' (00_parameters:12). config zapisuje cooldown_candles=24 niezależnym literałem (analogicznie PURGE_CANDLES=24). Jeśli H zostanie przestrojone (np. na 36), to cooldown_candles (i PURGE_CANDLES) nie podążą automatycznie — config rozjedzie się z regułą SOT 'COOLDOWN=H', dając cichy bug w detektorze (sufit dedupu odsprzęgnięty od horyzontu etykiety, co SOT uzasadnia jako celowe wyrównanie). Dziś wartości zgodne, więc to ryzyko driftu, nie aktualna rozbieżność.
- **Rekomendacja:** Udokumentować w 00_parameters (nota przy COOLDOWN/PURGE_CANDLES) regułę spójności 'cooldown_candles MUST == H' (i 'PURGE_CANDLES MUST == H') oraz dodać do quality gate / testu walidacji configu asercję detector.cooldown_candles == H (i PURGE_CANDLES == H). Pozostawienie literału 24 w JSON jest dopuszczalne tylko z taką jawną asercją; w przeciwnym razie wyprowadzać te wartości z H w warstwie ładowania configu.

#### [G1] Karta L07 nazywa wszystkie 8 kolumn 'X feature columns' — sprzeczność z DoD/SOT, gdzie X = dokładnie 7

- **Oś:** G (Cechy L7 / label Y / Output B) · **severity:** `MEDIUM`→`LOW` · **kategoria:** (c) · **głosy:** 3/3
- **Dowody:**
  - `acceptance_data_transform_cards/L07_Features_X_Label_Y_Card.md:20` — - 8 X feature columns at t0 (distance_to_trend_line … body_to_range_ratio)
  - `ENG/Layers_Short_SOT/00_definition_of_done_eng.md:19` — `FEATURE_MANIFEST` contains exactly the **7 X columns**; `closed_through_line` present in B as audit and constantly `= 1`.
  - `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:25` — in Output B (row = `t0`) definitionally `= 1` → **audit/invariant column, NOT part of `FEATURE_MANIFEST*`*
- **Wpływ:** Sformułowanie 'X feature columns' przypisuje status cechy X (wektor modelu) wszystkim 8 kolumnom, podczas gdy SOT/DoD jednoznacznie definiują X = 7, a 8. (closed_through_line) jest kolumną audytową poza X. Czytelnik karty może błędnie uznać, że model trenuje na 8 cechach, co kolidowałoby z FEATURE_MANIFEST=7 i schematem Output B. To niejednoznaczność na granicy realnej rozbieżności faktu (status X vs audit).
- **Rekomendacja:** Dostosuj kartę do SOT: zmień linię 20 na np. '8 transformer feature columns at t0 (7 X + closed_through_line audit)' lub '8 feature columns (7 X + 1 audit)'. Pozostaw resztę karty (linie 15, 22) bez zmian, bo tam '7 X' jest już poprawne — uspójnij tylko mylące 'X' w linii 20.

#### [G2] viz wprowadza skrót 'w_unique' jako nazwę kolumny wagi w kontrakcie Output B zamiast kanonicznego label_uniqueness_weight

- **Oś:** G (Cechy L7 / label Y / Output B) · **severity:** `LOW` · **kategoria:** (b) · **głosy:** 3/3
- **Dowody:**
  - `viz/main_data_flow.html:472` — output_contract:'Output B: 7 X + closed_through_line(audit) + Y_outcome + w_unique'
  - `viz/main_data_flow.html:1099` — columns = 7 X features + audit (close>line) + Y_outcome + weight w_unique · partition: asset × direction
  - `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md:92` —  `label_uniqueness_weight`  float  sample weight 
- **Wpływ:** Kanoniczna nazwa kolumny Output B to label_uniqueness_weight (schema frozen, każda zmiana = hard fail). viz w kontrakcie wyjścia (linia 472) i w opisie wiersza (linia 1099) używa skrótu 'w_unique', który nie jest nazwą kolumny w żadnym pliku SOT. To rozbieżność nazewnicza/struktury kluczy — niska istotność (viz tooltip xgb w linii 2028 używa pełnej nazwy), ale w kontekście 'frozen schema' alias kolumny może mylić co do dokładnej nazwy pola.
- **Rekomendacja:** Dostosuj artefakt podrzędny do SOT: zmień 'w_unique' na 'label_uniqueness_weight' w output_contract (linia 472) i w etykiecie ff_setup (linia 1099); w chipie sceny (linia 1093) można zachować skrót jako wyświetlaną etykietę, ale wtedy zaznacz '(label_uniqueness_weight)' w tooltipie, by nie sugerować, że to nazwa kolumny.

#### [G3] viz hardcoduje wartości okien (ATR(14), mean_20/std_20, W=20) w formułach cech zamiast referencji do parametrów — ryzyko driftu

- **Oś:** G (Cechy L7 / label Y / Output B) · **severity:** `LOW` · **kategoria:** (e) · **głosy:** 3/3
- **Dowody:**
  - `viz/main_data_flow.html:304` — src:'detector + Wilder ATR(14)'
  - `viz/main_data_flow.html:310` — formula:'(v − mean_20) / std_20  (std=0 → 0)',  src:'OHLCV · W=20'
  - `ENG/Layers_Short_SOT/00_parameters_eng.md:14` —  `W_VOL`  `20`  rolling window for `volume_z_score` 
  - `ENG/Layers_Short_SOT/00_parameters_eng.md:15` —  `W_ATR`  `14`  ATR window (feature normalizer) 
- **Wpływ:** Wartości 14 (W_ATR) i 20 (W_VOL) są wstrzyknięte jako literały w stringach formuł viz ('ATR(14)', 'mean_20', 'std_20', 'W=20'). Są dziś zgodne z params.json/00_parameters_eng.md, ale jako hardcode w trzech miejscach łatwo rozjadą się przy przyszłej zmianie W_ATR/W_VOL (parametr jest 'tuned'/timeframe-dependent wg 00_parameters:29). To nie aktualna rozbieżność, lecz ryzyko driftu typowe dla wizualizacji statycznej. Analogicznie L7 SOT:13 i :23 też zawierają literał '20', ale tam fakt ma swój dom; w viz to powielenie podrzędne.
- **Rekomendacja:** Zaakceptuj jako świadomy kompromis viz (literały dla czytelności) ALBO zmień stringi na formy parametryzowane (np. 'mean_{W_VOL} / std_{W_VOL}', 'ATR(W_ATR)') i dodaj w nagłówku sceny przypis 'wartości okien: 00_parameters_eng.md / config/params.json'. Minimalnie: dodaj komentarz przy FEATURES[] wskazujący, że literały 14/20 muszą być re-pinowane razem z params.json przy zmianie W_ATR/W_VOL.

#### [I2] viz: checks[].id='QC-06' niezgodne z konwencją id w SOT (ani string-key licznika, ani 1..11)

- **Oś:** I (Bramka jakości L8 + progi) · **severity:** `MEDIUM`→`LOW` · **kategoria:** (b) · **głosy:** 3/3
- **Dowody:**
  - `viz/main_data_flow.html:2081` — checks:[{id:'QC-06',level:'WARN',value:1,threshold:0,desc:'volume=0 bars'}]
  - `ENG/Layers_Short_SOT/L8_data_quality_eng.md:74` — { "id": "gaps_in_session", "level": "OK", "value": 0, "threshold": "FAIL>0", ... }
- **Wpływ:** Wizualizacja prezentuje przykład summary.json z checks[].id='QC-06' (kod QC, nie nazwa licznika z SOT i nie numer 1..11). Dla licznika volume_zero_bars właściwym kluczem wg wzorca SOT byłby 'volume_zero_bars' (QC-06 to tie źródłowy w katalogu, nie id pozycji checks). Wprowadza to trzecią konwencję id i może sugerować błędny schemat osobie czytającej tooltip.
- **Rekomendacja:** Dostosować artefakt podrzędny do SOT: zmienić w viz/main_data_flow.html:2081 'id:QC-06' na klucz licznika zgodny z finalnie ustaloną konwencją SOT (np. 'volume_zero_bars'). Zależne od rozstrzygnięcia I1.

#### [I3] viz: checks[].threshold zakodowane jako liczba (0) zamiast string ('FAIL>0') ze wzorca SOT

- **Oś:** I (Bramka jakości L8 + progi) · **severity:** `MEDIUM`→`LOW` · **kategoria:** (b) · **głosy:** 3/3
- **Dowody:**
  - `viz/main_data_flow.html:2081` — checks:[{id:'QC-06',level:'WARN',value:1,threshold:0,desc:'volume=0 bars'}]
  - `ENG/Layers_Short_SOT/L8_data_quality_eng.md:74` — "threshold": "FAIL>0"
- **Wpływ:** SOT (i towarzysz quality_gate_spec:47 'the threshold string') definiuje checks[].threshold jako string opisujący próg ('FAIL>0'). viz pokazuje threshold:0 jako liczbę — niezgodność typu pola w przykładowym summary.json, który ma być dosłownym renderem schematu. Mylące dla każdego, kto wzoruje generator na wizualizacji.
- **Rekomendacja:** Dostosować artefakt podrzędny do SOT: w viz/main_data_flow.html:2081 zmienić 'threshold:0' na string zgodny z pasmem licznika (dla volume_zero_bars np. 'WARN>0.5% FAIL>2%'), aby typ pola checks[].threshold był stringiem jak w L8 SOT.

#### [I4] Karta L08 rości sobie własność schematu summary.json ('owned here'), co przeczy SOT i własnej stopce

- **Oś:** I (Bramka jakości L8 + progi) · **severity:** `MEDIUM`→`LOW` · **kategoria:** (d) · **głosy:** 3/3
- **Dowody:**
  - `acceptance_data_transform_cards/L08_Data_Quality_Gate_Card.md:21` — - `summary.json` schema owned here
  - `ENG/Layers_Short_SOT/L8_data_quality_eng.md:5` — This file owns the counters, the parity chain, the `summary.json` schema and the aggregation rule
- **Wpływ:** Naruszenie zasady 'one home per fact': karta (artefakt podrzędny) deklaruje, że schemat summary.json jest 'owned here', podczas gdy jedynym domem schematu jest L8 SOT. Karta zaprzecza nawet samej sobie — jej stopka (linia 52) wskazuje 'SOT owner: ENG/Layers_Short_SOT/L8_data_quality_eng.md'. Powiela ryzyko, że ktoś będzie edytował schemat na karcie zamiast w SOT.
- **Rekomendacja:** Dostosować artefakt podrzędny do SOT: w L08_Data_Quality_Gate_Card.md:21 zmienić '`summary.json` schema owned here' na referencję, np. '`summary.json` schema defined in L8 SOT (see L8_data_quality_eng.md)'. Linia 46 'Right: summary.json + counters' jest opisowa i może zostać.

#### [J2] viz.METRICS wprowadza progi oceny metryk OOS (lo/hiV) nieosadzone w SOT

- **Oś:** J (Model L9 / ewaluacja L10 / metryki) · **severity:** `MEDIUM`→`LOW` · **kategoria:** (d) · **głosy:** 3/3
- **Dowody:**
  - `viz/main_data_flow.html:382` — {id:'pf',hi:true,lo:0.7,hiV:2.1}, {id:'sharpe',hi:true,lo:-0.5,hiV:2.2}, {id:'mdd',hi:false,lo:5,hiV:35}, {id:'tim',hi:true,lo:4,hiV:28}, {id:'wr',hi:true,lo:32,hiV:58}
  - `viz/main_data_flow.html:387` — function metricQ(val,m){var M=METRICS[m],q=clamp((val-M.lo)/(M.hiV-M.lo),0,1);return M.hi?q:1-q;}
  - `ENG/Layers_Short_SOT/L10_oos_test_eng.md:13` — a matrix `503 assets × {PF · Sharpe · MDD% · TIM% · WR% · trades}` [opis jakościowy, brak progów lo/hiV]
- **Wpływ:** Dziesięć liczbowych progów (po dwa na metrykę) plus kierunek 'hi' sterują kolorowaniem komórek matrycy OOS (zielony/czerwony) — to wizualna ocena jakości wyniku, której SOT nie definiuje. Czytelnik viz odbiera lo/hiV jako progi akceptacji per metryka, choć nigdzie nie mają domu. Ryzyko przekłamania interpretacji (np. PF>2.1 jako 'maks dobry', MDD>35% jako 'zły') bez podstawy w dokumentacji.
- **Rekomendacja:** Jeśli progi mają znaczenie analityczne — osadzić je w SOT (np. tabela w L10 'metric quality scale, reference-design') i kazać viz je cytować. Jeśli są tylko skalą wizualizacji (color ramp), oznaczyć je w komentarzu/legendzie viz jako 'visual scale only, not an acceptance threshold', aby nie były czytane jako fakt inżynierski. Domyślnie: dostosować artefakt podrzędny (viz) do SOT przez dodanie domu progów w L10 lub explicit dyskwalifikację jako fakt.

#### [J3] Niespójne sformułowanie LABEL_CONTRACT w viz (manifest vs band) względem wzorca SOT

- **Oś:** J (Model L9 / ewaluacja L10 / metryki) · **severity:** `LOW` · **kategoria:** (b) · **głosy:** 3/3
- **Dowody:**
  - `viz/main_data_flow.html:410` — label_contract:'TB_v1.1 · close-based · SL=L_opp(t) moving · geometric barriers R0 · H=24'
  - `viz/main_data_flow.html:1800` — LABEL_CONTRACT = TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24
  - `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:29` — `TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24`
- **Wpływ:** SOT L9 definiuje identyfikator LABEL_CONTRACT jako string '... moving · R0 · H=24'. viz.manifest (linia 410) wstawia dodatkowy człon 'geometric barriers R0', podczas gdy ten sam viz w banerze artefaktu (linia 1800) używa formy zgodnej z SOT. Identyfikator kontraktu powinien być bit-dokładny (jest to label-semantics identifier weryfikowany przy selfcheck/buildzie); rozjazd w samym viz utrudnia traktowanie go jako stałej.
- **Rekomendacja:** Ujednolicić oba wystąpienia w viz do dokładnej formy SOT: 'TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24'. Usunąć dodatek 'geometric barriers' z linii 410 (geometryczność R0 jest opisana osobno w L6/L7, nie należy do identyfikatora kontraktu).

#### [L1] PDF Master_Layer_Cards_Print_A4.pdf jest nieaktualny — starszy niż wszystkie 11 kart źródłowych .md

- **Oś:** L (Integralność linków i artefaktów) · **severity:** `MEDIUM`→`LOW` · **kategoria:** (e) · **głosy:** 3/3
- **Dowody:**
  - `acceptance_data_transform_cards/Master_Layer_Cards_Print_A4.pdf` — mtime=2026-06-16 20:42:18, size=58087
  - `acceptance_data_transform_cards/*.md` — wszystkie 11 kart .md (00_Crosscutting + L01..L10) + README_cards.md mają mtime 2026-06-17 10:30–11:24, tj. PO wygenerowaniu PDF
  - `acceptance_data_transform_cards/generate_master_layer_cards_pdf.py:55-57` — render_card() czyta `content = md_path.read_text(...)` — PDF jest deterministycznym renderem kart .md, więc edycja kart unieważnia PDF
- **Wpływ:** Wydrukowany/rozpowszechniony PDF (artefakt aprobacyjny pinowany do modelu 3D) odzwierciedla starszą wersję kart, podczas gdy karty .md (pochodne SOT) zostały zaktualizowane później. Osoba zatwierdzająca z PDF może podpisać nieaktualny stan faktów wywiedzionych z SOT.
- **Rekomendacja:** Zregenerować PDF: `python3 acceptance_data_transform_cards/generate_master_layer_cards_pdf.py` po ostatniej edycji kart, i włączyć ten krok do procesu (np. hook/Make), aby PDF zawsze powstawał po kartach. Docelowo rozważyć stempel daty/hasha źródeł w stopce PDF dla weryfikowalności świeżości.

#### [L2] Hardcodowana stopka '/ 11' i hardcodowana lista CARD_FILES — ryzyko driftu przy dodaniu/usunięciu karty

- **Oś:** L (Integralność linków i artefaktów) · **severity:** `LOW` · **kategoria:** (e) · **głosy:** 2/2
- **Dowody:**
  - `acceptance_data_transform_cards/generate_master_layer_cards_pdf.py:53` — self.cell(0, 10, f"Page {self.page_no()} / 11      Pin to 3D model      Source: ENG/Layers_Short_SOT", align="C")
  - `acceptance_data_transform_cards/generate_master_layer_cards_pdf.py:17-29` — CARD_FILES = [ "00_Crosscutting_Overview_Card.md", "L01_...", ... "L10_OOS_Test_Card.md" ]  (11 wpisów, jawnie wymienione)
  - `README_A_Layer.md:13` — 11 cards (L1–L10 + 00 overview) derived from SOT
- **Wpływ:** Dziś wszystko jest spójne (11 = 11 = 11), więc to nie jest realna rozbieżność. Jednak liczba '11' w stopce i lista CARD_FILES są niezależnie zahardkodowane; dodanie/usunięcie karty wymaga ręcznej zmiany w trzech miejscach (CARD_FILES, stopka, README_A_Layer.md) i łatwo o rozjechanie (np. stopka pokaże '/ 11' przy 12 stronach).
- **Rekomendacja:** Zastąpić literał w stopce zmienną liczbą stron, np. przechowywać `total = len(CARD_FILES)` jako atrybut i użyć w stopce `f"Page {self.page_no()} / {self.total_cards}"`; opcjonalnie generować CARD_FILES przez sortowane `glob('[0-9L]*_*Card.md')` aby lista wynikała z dysku, nie z literału. Liczbę w README_A_Layer.md:13 utrzymywać przez ten sam mechanizm lub odsyłać do README_cards.md.

#### [L3] Niespójne zakorzenienie inline-ścieżek w README_cards.md (część od A_Layers-root, część od katalogu kart; linia 31 `../B_Features/...` rozwiązuje się błędnie)

- **Oś:** L (Integralność linków i artefaktów) · **severity:** `LOW` · **kategoria:** (b) · **głosy:** ręczna · *weryfikacja ręczna (proces przerwany)*
- **Dowody:**
  - `acceptance_data_transform_cards/README_cards.md:9` — `ENG/Layers_Short_SOT/` ... `viz/main_data_flow.html` ... `B_Features/ENG/Stages_Short_SOT/` — zapisane jako root od A_Layers, ale plik leży w acceptance_data_transform_cards/, więc rozwiązane stąd są BROKEN (np. acceptance_data_transform_cards/ENG/Layers_Short_SOT)
  - `acceptance_data_transform_cards/README_cards.md:31` — `../B_Features/ENG/Stages_Short_SOT/` — z katalogu kart rozwiązuje się do A_Layers/B_Features (nie istnieje); kanoniczny target to ../../B_Features/ENG/Stages_Short_SOT/
  - `acceptance_data_transform_cards/README_cards.md:33` — `[../README_A_Layer.md](../A_Layers/README_A_Layer.md)` · `[../ENG/Layers_Short_SOT/README.md](../A_Layers/ENG/Layers_Short_SOT/README.md)` — TE aktywne linki są poprawnie zakorzenione (../), co kontrastuje z inline-ścieżkami w l.9/31
- **Wpływ:** Są to inline-code (backtick) etykiety, nie aktywne linki markdown, więc nie psują nawigacji klikalnej; mimo to mylą czytelnika co do faktycznej lokalizacji artefaktów i są łatwe do skopiowania jako błędna ścieżka. Niespójność: ta sama ścieżka B_Features/ENG/Stages_Short_SOT/ raz bez `../` (l.9), raz z pojedynczym `../` (l.31) — żadna z nich nie rozwiązuje się poprawnie spod katalogu kart (poprawnie: ../../B_Features/ENG/Stages_Short_SOT/).
- **Rekomendacja:** Ujednolicić zakorzenienie w README_cards.md: albo wszystkie inline-ścieżki podawać jako root-relative od A_Layers z wyraźnym prefiksem (np. `A_Layers/ENG/Layers_Short_SOT/`), albo jako poprawne ścieżki względne od katalogu kart (`../ENG/Layers_Short_SOT/`, `../viz/main_data_flow.html`, `../../B_Features/ENG/Stages_Short_SOT/`). W szczególności poprawić l.31 `../B_Features/...` -> `../../B_Features/...` aby zgadzała się z faktycznym położeniem Plan/B_Features. Dostosować artefakt podrzędny (README_cards.md) do realnej struktury katalogów.

### Severity: INFO

#### [C2] Niespójne formatowanie zakresu świec: SOT '[5, 9]' vs viz '[5,9]'

- **Oś:** C (Liczby globalne (503/510/8 841 820/×10000/rozmiary)) · **severity:** `INFO` · **kategoria:** (c) · **głosy:** 2/3
- **Dowody:**
  - `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md:32` —  QC-08  candles per day `∈ [5, 9]` 
  - `ENG/Layers_Short_SOT/00_conventions_eng.md:38` — candles/day ∈ [5, 9].
  - `viz/main_data_flow.html:324` — {id:'QC-08',name:'QC-08 BARS/DAY',     desc:'candles per day ∈ [5,9]'}
- **Wpływ:** Zakres wartości (5..9) jest identyczny; różnica dotyczy wyłącznie obecności spacji po przecinku ('[5, 9]' w SOT vs '[5,9]' w viz:324). Brak ryzyka merytorycznego, ale niejednolita typografia tej samej krotki w pakiecie.
- **Rekomendacja:** Ujednolicić zapis w viz:324 do '[5, 9]' (forma SOT) dla spójności prezentacji predykatu QC-08; alternatywnie świadomie ujednolicić w drugą stronę i odnotować, lecz domyślnie dostosować artefakt podrzędny (viz) do SOT.

#### [I6] Wewnętrzna niejednoznaczność SOT: '12 liczników (catalogue)' vs 'Checks (11 items) / id 1..11' bez jawnego mapowania

- **Oś:** I (Bramka jakości L8 + progi) · **severity:** `LOW`→`INFO` · **kategoria:** (c) · **głosy:** 3/3
- **Dowody:**
  - `ENG/Layers_Short_SOT/L8_data_quality_eng.md:40` — ## Checks (11 items) → thresholds
  - `ENG/Layers_Short_SOT/L8_data_quality_eng.md:23` — Counter catalogue table (12 rows: rows … nan_inf_outputB, lines 23-34)
- **Wpływ:** Katalog liczników ma 12 pozycji, a sekcja Checks deklaruje 11 (oraz schemat 'id 1..11'). Rekoncyliacja istnieje (4 liczniki populacyjne rows/symbols/parquet_files/setups_total nie są niezależnie progowane, lecz zasilają parytety; 8 liczników-checków + 3 parytety = 11), ale nigdzie nie jest zapisana wprost. Walidator lub czytelnik może oczekiwać 12 obiektów checks[] albo 12 progów, co prowadzi do błędu lub fałszywego alarmu.
- **Rekomendacja:** Dodać w L8 SOT jedno zdanie wyjaśniające relację 12→11, np. 'Cztery liczniki populacyjne (rows, symbols, parquet_files, setups_total) nie są progowane samodzielnie — zasilają parytety P1–P3; pozostałe 8 liczników + 3 parytety dają 11 pozycji checks[]'. Umieścić przy sekcji 'Checks (11 items)' lub przy katalogu.

#### [J4] viz.PARAM_IMPORTANCE podaje konkretne liczby ważności hiperparametrów bez domu w SOT

- **Oś:** J (Model L9 / ewaluacja L10 / metryki) · **severity:** `INFO` · **kategoria:** (e) · **głosy:** 3/3
- **Dowody:**
  - `viz/main_data_flow.html:371` — var PARAM_IMPORTANCE=[['learning_rate',0.31],['max_depth',0.22],['min_child_weight',0.14],['subsample',0.12],['n_estimators',0.09],['colsample_bytree',0.07],['reg_lambda',0.05]];
  - `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:6` — ## Tuning + training [SOT nie definiuje ważności hiperparametrów]
- **Wpływ:** Wartości są ewidentnie ilustracyjne (towarzyszą mockowanym TRIALS), ale w warstwie wizualnej prezentowane są jako konkretne procenty importance. Bez etykiety 'mock/illustrative' istnieje ryzyko odczytania ich jako rzeczywistego wyniku tuningu — drift interpretacyjny, choć nie ma realnej rozbieżności wartości z SOT (SOT po prostu milczy).
- **Rekomendacja:** Oznaczyć w viz (komentarz w kodzie + ewentualnie podpis na wykresie) że PARAM_IMPORTANCE oraz mockowane TRIALS są wartościami ilustracyjnymi, niewynikającymi z faktycznego runu. SOT nie wymaga zmian — to fakt celowo nieosadzony, należy go jedynie jednoznacznie zadeklarować jako placeholder.

#### [K2] Notacja wyjścia modelu p(TP) w słowniku nie istnieje w SOT (SOT używa p = model(x))

- **Oś:** K (Glosariusz (kompletność/spójność)) · **severity:** `LOW`→`INFO` · **kategoria:** (b) · **głosy:** 3/3
- **Dowody:**
  - `ENG/glossary_eng.md:127` — **XGBoost `binary:logistic` / meta-labeling** — the model returns `p(TP)` and **filters** the detector's setup signal (it does not look for trades).
  - `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md:30` — `THRESHOLD_ENTRY`  decision threshold: `p = model(x)`, `p ≥ THRESHOLD_ENTRY → ENTRY`, else FLAT
- **Wpływ:** Słownik wprowadza formę notacyjną p(TP), która nie występuje w żadnym pliku SOT (L9 i L10 używają konsekwentnie p = model(x) / p). Drobna rozbieżność nazewnictwa notacji w podrzędnym dokumencie; ryzyko że czytelnik uzna p(TP) za kanoniczne.
- **Rekomendacja:** Ujednolicić notację: w glossary:127 zastąpić `p(TP)` formą zgodną z SOT, np. 'the model returns `p = model(x)` (interpretowane jako p(TP))', lub po prostu `p`. Domyślnie: dostosować artefakt podrzędny (glossary) do SOT.

#### [K5] Niespójność formy: 'hash registry' (glossary) vs 'hash register' (L10 SOT)

- **Oś:** K (Glosariusz (kompletność/spójność)) · **severity:** `INFO` · **kategoria:** (b) · **głosy:** 3/3
- **Dowody:**
  - `ENG/glossary_eng.md:135` — **hash registry** — the hash of each artifact recorded before the test; from that moment the files are immutable.
  - `ENG/Layers_Short_SOT/L10_oos_test_eng.md:5` — Before the test, the hash of each strategy file goes into the hash register.
- **Wpływ:** Drobna niespójność jednego naming (registry vs register) między podrzędnym słownikiem a domem L10. Narusza zasadę 'one naming across the whole project'.
- **Rekomendacja:** Ujednolicić do formy z L10 SOT ('hash register') w glossary:135.

#### [K6] Słownik restatuje wzory/liczby pochodne (R0, z-score, rolling lookback = 20) wbrew własnej deklaracji 'point, don't restate'

- **Oś:** K (Glosariusz (kompletność/spójność)) · **severity:** `LOW`→`INFO` · **kategoria:** (e) · **głosy:** 2/3
- **Dowody:**
  - `ENG/glossary_eng.md:96` — `**R0` / `take_profit_level` / `time_barrier_candle`** — risk unit `abs(close[t0] − L_opp(t0))`; ... Definitions owned by L6 SOT.
  - `ENG/glossary_eng.md:81` — **rolling lookback** — the longest backward window of a feature: `max(W_ATR, W_VOL) = 20` candles.
- **Wpływ:** Choć wartości są dziś zgodne z SOT (L6:19 dla R0, L7:23 dla z-score, L5:8 dla 20), słownik mimo deklaracji 'it points to the SOT rather than restating it' (glossary:3-7) restatuje wzór R0, wzór z-score oraz pochodną liczbę 20 (zależną od W_ATR/W_VOL). Przy zmianie wzoru/parametru w SOT te kopie w słowniku łatwo się rozjadą (drift), a 20 jest wartością wyprowadzoną z parametrów ownowanych przez 00_parameters_eng.md.
- **Rekomendacja:** Zastąpić w glossary restatementy wzorów R0 i z-score zwięzłym opisem słownym + odesłaniem do domu (L6/L7 SOT); dla 'rolling lookback' usunąć konkretne '= 20' i zapisać 'max(W_ATR, W_VOL) (zob. 00_parameters_eng.md / L5_time_split_eng.md)', aby liczba miała jeden dom.

## 6. Findingi odrzucone w weryfikacji (transparentność)

**14** kandydatów na findingi zostało obalonych przez weryfikację adwersaryjną (większość sceptyków uznała je za nieistotne, błędnie odczytane, albo za oczekiwaną referencję do SOT, nie rozbieżność).


| id  | Oś  | Kandydat                                                                                                                                          | Kat. | Głosy za utrzymaniem |
| --- | --- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | -------------------- |
| A1  | A   | viz nazywa scene graph SINGLE SOURCE OF TRUTH bez deklaracji podrzednosci wobec ENG/Layers_Short_SOT                                              | c    | 1/3                  |
| A3  | A   | spec v1.2 w viz nieosadzona w SOT i kolida z decision v1.2 z L7                                                                                   | d    | 0/3                  |
| A7  | A   | Zakres Stage F0 do F14 twardo wpisany w 7 miejscach A_Layers, ryzyko driftu wobec B_Features                                                      | e    | 0/3                  |
| C1  | C   | Niespójne formatowanie liczby wierszy w viz: 8 841 820 vs 8.84M vs 8841820                                                                        | c    | 0/3                  |
| C3  | C   | Rozmiary 139 MB i 166 MB nie są wymienione w centralnym bloku 'Global numbers' SOT (00_conventions)                                               | d    | 0/3                  |
| D1  | D   | Niejednolita krótka nazwa warstwy L8 — wewnętrzna niespójność samego SOT (Validation vs Data-quality gate) plus rozjazd w artefaktach podrzędnych | b    | 1/3                  |
| H1  | H   | Band [5,9] dla QC-08 (candles per day) nieosadzony w 00_parameters — fakt żyje tylko inline w L3 SOT i jest literalnie powielony w viz            | e    | 1/3                  |
| H2  | H   | Okno sesji 09:00–16:00 ET (QC-09) nieosadzone w 00_parameters — powielone jako literał w L3 SOT, viz i L8 SOT                                     | e    | 0/3                  |
| H3  | H   | Etykieta viz 'BARS/DAY' i grupowy zapis 'hard fail QC-08/09/10' zacierają indywidualną treść predykatu QC-08 (count świec) względem QC-09/QC-10   | c    | 0/3                  |
| I1  | I   | Wewnętrzna niespójność SOT: pole checks[].id ma dwie sprzeczne konwencje (string-key 'gaps_in_session' vs numeryczne 'id 1..11')                  | c    | 1/3                  |
| I5  | I   | Karta L08 opisuje decyzję bramki jako binarną PASS/FAIL, gubiąc trój-stanowy overall_status (WARN)                                                | c    | 0/3                  |
| K1  | K   | Słownik nie definiuje kanonicznych nazw kolumn Y_entry / Y_outcome (zlane w generyczne 'label Y')                                                 | b    | 0/3                  |
| K3  | K   | Termin cooldown używany w SOT (conventions + detector reference design) jest nieobecny w słowniku                                                 | b    | 1/3                  |
| K4  | K   | Identyfikator wersji TB_v1.1 przypisany w słowniku do L7, ale mintowany tylko w L9 (L7 SOT używa 'decision v1.2')                                 | c    | 1/3                  |


## 7. Cele pipeline'u i ich spójność

Cross-cutting cele/decyzje są deklarowane spójnie i nie wykluczają się wzajemnie:

- **Causality / zero look-ahead** — spójnie egzekwowane: `L6` inwariant 4 ("fits use only candles ≤ t0"), `L7` anti-leakage, `00_definition_of_done` poz. 3 (test wykrywający użycie candle > t), glosariusz. Jedyne okno w przód = okno etykiety `[t0, t0+H]`. Zgodne we wszystkich źródłach.
- **Determinism** — spójne: same input → same output (seeds/hash) w `00_conventions`, `L4` parity, `L9`/`L10` (hash register, deterministic build, `selfcheck()`).
- **One-shot OOS** — spójne: OOS testowane raz, artefakty zamrożone przed testem, wynik nigdy nie wraca do tuningu (`L5`, `L9`, `L10`, DoD poz. 13).
- **Scale-/timeframe-independence** — spójne: zero zaszytych progów cenowych; jedyna zależność od TF w `H` (`00_conventions`, DoD poz. 1).
- **Gate L8 → L9** — spójne: FAIL blokuje trening, WARN przepuszcza; `det09_rejected` z sufitem WARN; agregacja FAIL>WARN>OK (`L8`, `quality_gate_spec`, karta L08). Drobna nieścisłość prozy (karta L08 opisuje bramkę jako binarną PASS/FAIL — finding I5, odrzucony jako nieistotny, bo karta dalej wymienia trój-stan w innym miejscu).

Wniosek: **warstwa celów jest spójna** — pęknięcia dotyczą wyłącznie *rejestracji wartości* (gdzie fakt mieszka), nie *treści decyzji*.

## 8. Rekomendacje (priorytetyzowane)

**P1 — wewnętrzna spójność SOT (najpierw, bo SOT jest wzorcem):**

1. Ujednolicić liczenie parametrów: przyjąć jeden, jednoznaczny opis (np. "18 kluczy skalarnych top-level + 3 bloki zagnieżdżone: `splits`, `detector`, `l8`") i poprawić go w `00_parameters_eng.md`, `00_Crosscutting_Overview_Card.md` (usunąć podwójne liczenie `EPS`) oraz wszędzie, gdzie pada "17" (B1, B2, A2, A5).
2. Naprawić błędne/nieistniejące odwołanie ścieżkowe w `00_parameters_eng.md` (A4).
3. Nadać dom wartości `k=4` (liczba foldów CV): dodać `CV_FOLDS: 4` do `config/params.json` i `00_parameters_eng.md`, a w prozie `L9` tylko ją cytować (E1, B4).

**P2 — domknięcie DRY w wizualizacji (fakty nieosadzone):**
4. Przenieść do SOT (lub jawnie oznaczyć jako pochodne z linkiem do domu) wartości obecne dziś tylko w `viz`: przestrzeń Optuny, progi metryk `lo/hiV`, frakcje okien, ważności hiperparametrów, zaszyte okna w formułach cech (B3, J1, J2, E2, J4, G3). Docelowo `viz` powinno *czytać* z jednego źródła, nie *definiować*.
5. Dodać w SOT jawną tabelę mapowania symbol↔klucz JSON dla detektora (`k`↔`pivot_k`, `LOOKBACK`↔`lookback_candles`, `COOLDOWN`↔`cooldown_candles`) (F1); ujednolicić `viz.checks[].id`/`threshold` z konwencją SOT (I2, I3) i usunąć skrót `w_unique` na rzecz `label_uniqueness_weight` (G2).

**P3 — redukcja ryzyka driftu (CI/automatyzacja):**
6. Doprecyzować kartę `L07`: nazwać 8 kolumn "8 cech (7 X + `closed_through_line` audit)", nie "8 X feature columns" (G1).
7. Zregenerować `Master_Layer_Cards_Print_A4.pdf` (jest starszy niż karty) i dodać auto-discovery kart (`L\d+_*_Card.md`) zamiast zaszytej `CARD_FILES` + dynamiczną stopkę zamiast "/ 11" (L1, L2, D2).

**Proponowane asercje CI (utrzymanie spójności):**

- `config/params.json` ≡ rejestr `00_parameters_eng.md` (równość kluczy i wartości, obustronnie).
- `wc -l config/universe.txt == 503` oraz liczba zip == 510, liczba wierszy == 8 841 820 (zgodność z `00_conventions`).
- lista plików kart na dysku == `CARD_FILES` w generatorze; `len(CARD_FILES)` == liczba w stopce.
- kolejność `METRICS` (PF·Sharpe·MDD·TIM·WR) identyczna w `00_conventions`, `L10`, `viz.METRICS`, karcie L10.
- żaden plik podrzędny nie wprowadza liczbowej wartości parametru bez odwołania do domu w SOT (lint na 'unsourced facts', zwł. w `viz`).

## 9. Załącznik

**Inwentarz katalogu (audytowane pliki):** SOT — `ENG/Layers_Short_SOT/` (15 plików); towarzysze — `ENG/{readme,build_contract,detector_algorithm,quality_gate_spec,glossary,summary_rules}_eng.md`; karty — `acceptance_data_transform_cards/` (L01–L10, `00_Crosscutting_Overview_Card.md`, `card_template.md`, `README_cards.md`, `generate_master_layer_cards_pdf.py`, `Master_Layer_Cards_Print_A4.pdf`); konfiguracja — `config/params.json`, `config/universe.txt`; wizualizacja/README — `viz/main_data_flow.html`, `README_A_Layer.md`.

**Integralność linków (oś L):** wszystkie aktywne linki markdown (w tym zewnętrzne `../../B_Features/...` i `../../../B_Features/`) rozwiązują się do istniejących ścieżek. Jedyny wyjątek to mieszane zakorzenienie *inline*-ścieżek (backtick) w `README_cards.md` — część rootowana od `A_Layers` (`ENG/...`, `B_Features/...`), a `../B_Features/...` rozwiązuje się błędnie (finding L3, LOW).

**Referencje zewnętrzne:** `B_Features` (Plan B, Stages F0–F14) jest poprawnie traktowane jako odrębny, podrzędny helper poza SOT Pipeline A; ścieżki istnieją.

**Ograniczenia audytu:**

- `Master_Layer_Cards_Print_A4.pdf` jest binarny — jego *treści* nie dało się zweryfikować względem `.md`; staleness wykryto wyłącznie po czasie modyfikacji (PDF starszy od kart).
- Dwa z 135 głosów weryfikacyjnych (dla findingu L3) nie ukończyły się przed przerwaniem procesu; L3 zaadjudykowano ręcznie (potwierdzony, LOW).
- Audyt jest **read-only**: nie zmodyfikowano żadnego istniejącego pliku; jedynym nowym plikiem jest ten raport.

