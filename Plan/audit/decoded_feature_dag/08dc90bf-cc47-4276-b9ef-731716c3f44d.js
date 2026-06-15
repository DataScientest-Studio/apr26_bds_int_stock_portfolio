/* global React, ReactDOM, PIPELINE */
// OHLCV → L5 lineage diagram.
// Layout: geological — L0 at bottom, L5 at top (or left→right when orientation flipped).
// Each node positioned by (layer, family, stack index within family-in-layer).
// Edges = SVG paths drawn behind nodes. Pan + zoom on the whole canvas.

const { useState, useMemo, useRef, useEffect, useCallback } = React;

// ─── family palette (subtle, wireframe-friendly) ─────────────────────────────
const FAMILY = {
  price:   { c: "#3a6fa3", label: "Price",            tint: "#e9f0f7" },
  returns: { c: "#3f8556", label: "Returns / Δ",     tint: "#e8f1ec" },
  range:   { c: "#b87333", label: "Range / Vol",      tint: "#f5ece1" },
  candle:  { c: "#7a4e9e", label: "Candle Geometry",  tint: "#efe9f4" },
  volume:  { c: "#b54a45", label: "Volume",           tint: "#f5e7e6" },
  meta:    { c: "#3a3a3a", label: "Synthesis / Meta", tint: "#ececec" },
};

const LAYER_INFO = {
  0: { title: "L0 · Raw OHLCV",                blurb: "Raw material. Five series. Everything else is a function of these." },
  1: { title: "L1 · Atomic transforms",        blurb: "Point-wise operations on a single candle or a pair of adjacent candles." },
  2: { title: "L2 · Rolling / temporal",       blurb: "Lags and rolling windows of length n. Where time first enters." },
  3: { title: "L3 · MTF · regime",             blurb: "Resample 1h → 1d (native 1h store), recompute L1/L2, context aggregates." },
  4: { title: "L4 · Classical indicators",     blurb: "RSI / MACD / ATR / OBV. Compressed functions of L1–L3, not magic." },
  5: { title: "L5 · Research representations", blurb: "Stack → standardize → compression: PCA, wavelets, AE, sequences." },
};

// ─── layout ──────────────────────────────────────────────────────────────────
// vertical: layers stacked top(L5) → bottom(L0). data flows upward.
// node W × H
const NW = 218, NH = 60;

// Vertical layout constants
const V_FAMILY_X = { price: 240, returns: 680, range: 1120, candle: 1560, volume: 2000, meta: 1120 };
const V_LAYER_TOP = { 5: 80, 4: 590, 3: 1020, 2: 1530, 1: 2130, 0: 2620 };
const V_CANVAS = { w: 2240, h: 2780 };

// Horizontal layout constants
const H_FAMILY_Y = { price: 180, returns: 540, range: 900, candle: 1260, volume: 1620, meta: 900 };
const H_LAYER_LEFT = { 0: 100, 1: 460, 2: 960, 3: 1460, 4: 1960, 5: 2460 };
const H_CANVAS = { w: 2860, h: 1820 };

function computePositions(nodes, orientation) {
  const vert = orientation === "vertical";
  // group nodes by (layer, family) keeping original order
  const groups = new Map();
  for (const n of nodes) {
    const key = n.layer + "/" + n.family;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(n);
  }

  const out = {};
  for (const [key, arr] of groups) {
    arr.forEach((n, i) => {
      if (n.layer === 0) {
        // L0 special — spread 5 nodes evenly across the bottom (vert) / left (horiz)
        const order = ["O", "H", "L", "C", "V"];
        const idx = order.indexOf(n.id);
        if (vert) {
          const xs = [240, 680, 1120, 1560, 2000];
          out[n.id] = { x: xs[idx] - NW / 2, y: V_LAYER_TOP[0] + 10 };
        } else {
          const ys = [180, 540, 900, 1260, 1620];
          out[n.id] = { x: H_LAYER_LEFT[0] + 10, y: ys[idx] - NH / 2 };
        }
        return;
      }
      if (n.layer === 5) {
        // L5 special funnel: stack at center-bottom, 4 branches above it, x_final at top
        if (vert) {
          const layouts = {
            l5_stack:   { cx: 1120, cy: V_LAYER_TOP[5] + 360 },
            l5_pca:     { cx:  500, cy: V_LAYER_TOP[5] + 200 },
            l5_wave:    { cx:  900, cy: V_LAYER_TOP[5] + 200 },
            l5_ae:      { cx: 1340, cy: V_LAYER_TOP[5] + 200 },
            l5_seq:     { cx: 1740, cy: V_LAYER_TOP[5] + 200 },
            l5_x_final: { cx: 1120, cy: V_LAYER_TOP[5] + 40  },
          };
          const p = layouts[n.id];
          out[n.id] = { x: p.cx - NW / 2, y: p.cy };
        } else {
          const layouts = {
            l5_stack:   { cx: H_LAYER_LEFT[5] + 20,  cy: 900 },
            l5_pca:     { cx: H_LAYER_LEFT[5] + 240, cy: 360 },
            l5_wave:    { cx: H_LAYER_LEFT[5] + 240, cy: 720 },
            l5_ae:      { cx: H_LAYER_LEFT[5] + 240, cy: 1080 },
            l5_seq:     { cx: H_LAYER_LEFT[5] + 240, cy: 1440 },
            l5_x_final: { cx: H_LAYER_LEFT[5] + 460, cy: 900 },
          };
          const p = layouts[n.id];
          out[n.id] = { x: p.cx, y: p.cy - NH / 2 };
        }
        return;
      }
      // generic layers 1..4
      if (vert) {
        const cx = V_FAMILY_X[n.family];
        const top = V_LAYER_TOP[n.layer];
        out[n.id] = { x: cx - NW / 2, y: top + i * 78 };
      } else {
        const cy = H_FAMILY_Y[n.family];
        const left = H_LAYER_LEFT[n.layer];
        out[n.id] = { x: left + i * 232, y: cy - NH / 2 };
      }
    });
  }
  return out;
}

// edge: from source's "out" edge to target's "in" edge
function edgePath(s, t, orientation, sketchy) {
  const vert = orientation === "vertical";
  let sx, sy, tx, ty;
  if (vert) {
    // source is BELOW target (higher y), data goes UP — exit top of source, enter bottom of target
    sx = s.x + NW / 2; sy = s.y;
    tx = t.x + NW / 2; ty = t.y + NH;
  } else {
    // source LEFT of target — exit right of source, enter left of target
    sx = s.x + NW; sy = s.y + NH / 2;
    tx = t.x;      ty = t.y + NH / 2;
  }
  const dx = tx - sx, dy = ty - sy;
  let c1x, c1y, c2x, c2y;
  if (vert) {
    const k = Math.max(40, Math.abs(dy) * 0.42);
    c1x = sx;       c1y = sy - k;
    c2x = tx;       c2y = ty + k;
  } else {
    const k = Math.max(40, Math.abs(dx) * 0.42);
    c1x = sx + k;   c1y = sy;
    c2x = tx - k;   c2y = ty;
  }
  if (sketchy) {
    // add slight midpoint wobble
    const mx = (sx + tx) / 2 + (Math.sin(sx * 0.13 + tx * 0.07) * 6);
    const my = (sy + ty) / 2 + (Math.cos(sy * 0.11 + ty * 0.05) * 6);
    return `M ${sx} ${sy} Q ${c1x} ${c1y} ${mx} ${my} Q ${c2x} ${c2y} ${tx} ${ty}`;
  }
  return `M ${sx} ${sy} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${tx} ${ty}`;
}

// BFS up the lineage (predecessors) from a node
function ancestorsOf(nodeId, edges) {
  const adjFrom = new Map(); // child -> [parents]
  for (const e of edges) {
    if (!adjFrom.has(e.to)) adjFrom.set(e.to, []);
    adjFrom.get(e.to).push(e.from);
  }
  const seen = new Set([nodeId]);
  const edgeSet = new Set();
  const stack = [nodeId];
  while (stack.length) {
    const cur = stack.pop();
    const parents = adjFrom.get(cur) || [];
    for (const p of parents) {
      edgeSet.add(p + "→" + cur);
      if (!seen.has(p)) { seen.add(p); stack.push(p); }
    }
  }
  return { nodes: seen, edges: edgeSet };
}

// ─── components ──────────────────────────────────────────────────────────────
function NodeCard({ n, pos, showFormula, sketchy, dim, hi, onClick, orientation }) {
  const fam = FAMILY[n.family];
  const isL0 = n.layer === 0;
  const isL5stack = n.id === "l5_stack";
  const isL5final = n.id === "l5_x_final";
  const w = NW, h = NH;

  const tilt = sketchy ? ((n.id.charCodeAt(0) + n.id.length) % 5 - 2) * 0.15 : 0;
  const radius = sketchy
    ? `${6 + (n.id.charCodeAt(0) % 5)}px ${10 + (n.id.charCodeAt(1) % 7)}px ${8 + (n.id.length % 6)}px ${5 + (n.id.charCodeAt(0) % 4)}px / ${8 + (n.id.length % 5)}px ${5 + (n.id.charCodeAt(1) % 6)}px ${9 + (n.id.charCodeAt(0) % 5)}px ${6 + (n.id.length % 4)}px`
    : "6px";

  return (
    <div
      className={"node " + (sketchy ? "sk " : "cl ") + (dim ? "dim " : "") + (hi ? "hi " : "")}
      style={{
        left: pos.x, top: pos.y,
        width: w, height: isL5stack ? h + 16 : h,
        borderColor: fam.c,
        background: hi ? fam.tint : "#fdfcfa",
        transform: `rotate(${tilt}deg)`,
        borderRadius: radius,
      }}
      onClick={() => onClick(n.id)}
    >
      <div className="node-side" style={{ background: fam.c }}></div>
      <div className="node-body">
        <div className="node-name" style={{ color: isL0 ? fam.c : "#222" }}>
          {isL0 ? n.id : n.name}
        </div>
        {!isL0 && showFormula && n.formula && (
          <div className="node-formula">{n.formula}</div>
        )}
        {isL0 && <div className="node-note">{n.note}</div>}
        {isL5stack && <div className="node-note">all features → z-score</div>}
        {isL5final && <div className="node-note">model input X</div>}
      </div>
    </div>
  );
}

function LayerBand({ layer, orientation, sketchy }) {
  const info = LAYER_INFO[layer];
  const vert = orientation === "vertical";
  // Compute band rect
  let style;
  const layerHeights = vert
    ? { 0: 100, 1: 460, 2: 560, 3: 460, 4: 380, 5: 460 }
    : { 0: H_CANVAS.h, 1: H_CANVAS.h, 2: H_CANVAS.h, 3: H_CANVAS.h, 4: H_CANVAS.h, 5: H_CANVAS.h };
  if (vert) {
    style = {
      left: 0, width: V_CANVAS.w,
      top: V_LAYER_TOP[layer] - 30, height: layerHeights[layer] + 30,
    };
  } else {
    const layerWidths = { 0: 360, 1: 500, 2: 500, 3: 500, 4: 500, 5: H_CANVAS.w - H_LAYER_LEFT[5] };
    style = {
      top: 0, height: H_CANVAS.h,
      left: H_LAYER_LEFT[layer] - 30, width: layerWidths[layer] + 30,
    };
  }
  return (
    <div className={"band " + (sketchy ? "sk" : "cl") + " band-" + layer + " band-" + orientation}
         style={style}>
      <div className="band-label">
        <div className="band-title">{info.title}</div>
        <div className="band-blurb">{info.blurb}</div>
      </div>
    </div>
  );
}

function Diagram({ tweaks, focusId, setFocusId }) {
  const { NODES, EDGES } = window.PIPELINE;
  const orientation = tweaks.orientation;
  const sketchy = tweaks.mode === "sketchy";
  const showFormula = tweaks.showFormula;
  const CANVAS = orientation === "vertical" ? V_CANVAS : H_CANVAS;

  const positions = useMemo(() => computePositions(NODES, orientation), [orientation]);

  const hi = useMemo(() => {
    if (!focusId) return null;
    return ancestorsOf(focusId, EDGES);
  }, [focusId]);

  // pan/zoom
  const wrapRef = useRef(null);
  const [view, setView] = useState({ x: 0, y: 0, z: 0.5 });
  const drag = useRef(null);

  // fit-to-screen on mount + orientation change
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const W = el.clientWidth, H = el.clientHeight;
    const z = Math.min(W / CANVAS.w, H / CANVAS.h) * 0.95;
    const x = (W - CANVAS.w * z) / 2;
    const y = (H - CANVAS.h * z) / 2;
    setView({ x, y, z });
  }, [orientation]);

  const onWheel = useCallback((e) => {
    e.preventDefault();
    const el = wrapRef.current; if (!el) return;
    const rect = el.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    setView((v) => {
      const factor = Math.exp(-e.deltaY * 0.0015);
      const nz = Math.max(0.15, Math.min(2.5, v.z * factor));
      // keep mouse point fixed
      const k = nz / v.z;
      return { x: mx - (mx - v.x) * k, y: my - (my - v.y) * k, z: nz };
    });
  }, []);

  const onMouseDown = (e) => {
    if (e.target.closest(".node") || e.target.closest(".twk-panel") || e.target.closest(".legend") || e.target.closest(".zctrl")) return;
    drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y };
  };
  const onMouseMove = (e) => {
    const d = drag.current;
    if (!d) return;
    const cx = e.clientX, cy = e.clientY;
    setView((v) => ({ ...v, x: d.vx + (cx - d.x), y: d.vy + (cy - d.y) }));
  };
  const onMouseUp = () => { drag.current = null; };

  useEffect(() => {
    const el = wrapRef.current; if (!el) return;
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [onWheel]);

  const zoomBy = (factor) => {
    const el = wrapRef.current; if (!el) return;
    const W = el.clientWidth, H = el.clientHeight;
    setView((v) => {
      const nz = Math.max(0.15, Math.min(2.5, v.z * factor));
      const k = nz / v.z;
      const cx = W / 2, cy = H / 2;
      return { x: cx - (cx - v.x) * k, y: cy - (cy - v.y) * k, z: nz };
    });
  };
  const fit = () => {
    const el = wrapRef.current; if (!el) return;
    const W = el.clientWidth, H = el.clientHeight;
    const z = Math.min(W / CANVAS.w, H / CANVAS.h) * 0.95;
    setView({ x: (W - CANVAS.w * z) / 2, y: (H - CANVAS.h * z) / 2, z });
  };

  return (
    <div
      className={"wrap " + (sketchy ? "sk-mode" : "cl-mode")}
      ref={wrapRef}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
    >
      <div className="canvas" style={{
        width: CANVAS.w, height: CANVAS.h,
        transform: `translate(${view.x}px, ${view.y}px) scale(${view.z})`,
        transformOrigin: "0 0",
      }}>
        {/* Layer bands behind everything */}
        {[5,4,3,2,1,0].map((l) => (
          <LayerBand key={l} layer={l} orientation={orientation} sketchy={sketchy} />
        ))}

        {/* Edges */}
        <svg className="edges" width={CANVAS.w} height={CANVAS.h}>
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" fill="#999" />
            </marker>
            <marker id="arrow-hi" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" fill="#1a1a1a" />
            </marker>
          </defs>
          {EDGES.map((e, i) => {
            const s = positions[e.from], t = positions[e.to];
            if (!s || !t) return null;
            const d = edgePath(s, t, orientation, sketchy);
            const isHi = hi && hi.edges.has(e.from + "→" + e.to);
            const isDim = hi && !isHi;
            const isCtx = e.kind === "ctx";
            return (
              <path
                key={i} d={d}
                fill="none"
                stroke={isHi ? "#1a1a1a" : (isCtx ? "#bbb" : "#bcbcbc")}
                strokeWidth={isHi ? 2.2 : (isCtx ? 1 : 1.2)}
                strokeDasharray={isCtx ? "4 4" : "none"}
                opacity={isDim ? 0.15 : 1}
                markerEnd={isHi ? "url(#arrow-hi)" : "url(#arrow)"}
              />
            );
          })}
        </svg>

        {/* Nodes */}
        {NODES.map((n) => {
          const isHi = hi && hi.nodes.has(n.id);
          const isDim = hi && !isHi;
          return (
            <NodeCard
              key={n.id}
              n={n}
              pos={positions[n.id]}
              showFormula={showFormula}
              sketchy={sketchy}
              hi={isHi}
              dim={isDim}
              orientation={orientation}
              onClick={(id) => setFocusId(focusId === id ? null : id)}
            />
          );
        })}
      </div>

      {/* Floating controls */}
      <div className="zctrl">
        <button onClick={() => zoomBy(1.25)}>+</button>
        <button onClick={() => zoomBy(0.8)}>−</button>
        <button onClick={fit}>fit</button>
        <button onClick={() => setFocusId(null)} disabled={!focusId}>clear</button>
      </div>

      {focusId && (
        <div className="focus-bar">
          <div className="focus-bar-l">Lineage: <b>{focusId}</b></div>
          <div className="focus-bar-r">
            <span>{hi.nodes.size} nodes · {hi.edges.size} edges</span>
            <button onClick={() => setFocusId(null)}>✕</button>
          </div>
        </div>
      )}

      <div className="legend">
        <div className="legend-title">Feature families</div>
        {Object.entries(FAMILY).map(([k, v]) => (
          <div key={k} className="legend-row">
            <span className="legend-sw" style={{ background: v.c }}></span>
            <span>{v.label}</span>
          </div>
        ))}
        <div className="legend-title" style={{ marginTop: 10 }}>Edges</div>
        <div className="legend-row"><span className="legend-line solid"></span><span>data lineage</span></div>
        <div className="legend-row"><span className="legend-line dashed"></span><span>regime context</span></div>
        <div className="legend-hint">Click a node → highlight its lineage from L0</div>
      </div>

      <div className="title-card">
        <div className="title-card-eyebrow">Feature pipeline · technical demo</div>
        <div className="title-card-title">OHLCV → L5</div>
        <div className="title-card-sub">
          Each layer <b>extends</b> the previous ones — it doesn't replace them.
          Naming: <code>l{"{"}layer{"}"}_{"{"}metric{"}"}_{"{"}params{"}"}_{"{"}timeframe{"}"}</code>.
          Drag to pan · scroll to zoom · click a node to see where it came from.
        </div>
      </div>
    </div>
  );
}

// ─── root ────────────────────────────────────────────────────────────────────
function App() {
  const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
    "orientation": "vertical",
    "mode": "sketchy",
    "showFormula": true
  }/*EDITMODE-END*/;
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [focusId, setFocusId] = useState(null);

  return (
    <React.Fragment>
      <Diagram tweaks={t} focusId={focusId} setFocusId={setFocusId} />
      <TweaksPanel>
        <TweakSection label="Layout" />
        <TweakRadio
          label="Orientation" value={t.orientation}
          options={["vertical", "horizontal"]}
          onChange={(v) => setTweak("orientation", v)}
        />
        <TweakRadio
          label="Style" value={t.mode}
          options={["sketchy", "clean"]}
          onChange={(v) => setTweak("mode", v)}
        />
        <TweakSection label="Detail" />
        <TweakToggle
          label="Show formulas" value={t.showFormula}
          onChange={(v) => setTweak("showFormula", v)}
        />
        <TweakSection label="Lineage" />
        <div style={{ fontSize: 11, color: "rgba(41,38,27,.62)", lineHeight: 1.45 }}>
          Click any node on the diagram to highlight all of its ancestors up to L0.
          Click it again or use <b>clear</b> to deselect.
        </div>
      </TweaksPanel>
    </React.Fragment>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
