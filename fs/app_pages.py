"""WO-FS study — Streamlit presentation pages (PL). Read-only over fs/artifacts/<universe>: the
seven pages walk a professor from the data contract through label calibration, validation, both
feature-selection loops, the SHAP universality audit, and the honest OOS verdict. Nothing trains
at render time; a page with no artifact tells you exactly which `make` target produces it.

Rendered inside app/app.py when the sidebar mode = "Studium selekcji cech (WO-FS)".
"""
import json
import sqlite3

import numpy as np
import pandas as pd
import streamlit as st

from . import ART, CONFIG, read_json
from . import features as FEAT

# CVD-safe palette (validated pair): classes are a polarity, so blue(+1)/gray(0)/orange(-1);
# magnitude (SHAP) uses a single-hue light->dark sequential ramp.
C_UP, C_ZERO, C_DOWN = "#4269d0", "#9aa0a6", "#e58606"
CLASS_COLOR = {"1": C_UP, "0": C_ZERO, "-1": C_DOWN}
CLASS_NAME = {"1": "+1 (long)", "0": "0 (brak)", "-1": "−1 (short)"}
SEQ = ["#eaf0fb", "#c9d7f2", "#9fbce8", "#6f97db", "#4269d0", "#2f4da3", "#1e326b"]


def art(universe):
    return ART / universe


def _exists(universe, name):
    return (art(universe) / name).exists()


def _load(universe, name, default=None):
    p = art(universe) / name
    return read_json(p) if p.exists() else default


def _need(universe, cmd):
    st.info(f"Ten artefakt jeszcze nie istnieje. Uruchom:\n\n```\n{cmd}\n```")


def _duck(universe, query):
    import duckdb
    db = art(universe) / "fs_results.duckdb"
    if not db.exists():
        return pd.DataFrame()
    con = duckdb.connect(str(db), read_only=True)
    try:
        tables = {t[0] for t in con.execute("show tables").fetchall()}
        tbl = query.split(" from ")[1].split()[0]
        if tbl not in tables:
            return pd.DataFrame()
        return con.execute(query).fetchdf()
    finally:
        con.close()


# ============================ page 1: data & contract ============================

@st.cache_data(ttl=120)
def _sample_frame(universe, ticker):
    from . import data
    bars, feats = data.bar_frame(ticker, universe)
    return bars, feats


def page_data(universe):
    st.header("1 · Dane i kontrakt czasowy")
    st.markdown(
        "**Trzy horyzonty czasu, jedna decyzja.** Cechy liczone są z *natywnych* barów każdego "
        "interwału: **1h** (timing), **1d** (setup, natywny store dzienny), **1w** (kontekst/reżim, "
        "agregat ISO-tygodnia z 1d). Zakaz resamplingu 1h→1d. Decyzja w barze 1h zapada na jego "
        "**zamknięciu** (`close = open + 1h`), a cechy 1d/1w pochodzą **wyłącznie z ostatniej "
        "ZAMKNIĘTEJ** świecy wyższego TF — join `merge_asof(backward, allow_exact_matches=False)`, "
        "czyli jawny lag ≥ 1 bara TF. To jest bramka anty-lookahead.")
    frozen = _load(universe, "labels_frozen.json")
    tickers = (frozen or {}).get("study1_tickers") or ["AAPL"]
    tk = st.selectbox("Ticker podglądu", tickers, index=0)
    try:
        bars, feats = _sample_frame(universe, tk)
    except Exception as e:  # noqa: BLE001
        st.warning(f"Nie udało się wczytać barów dla {tk}: {e}")
        return
    from . import data
    n1h = len(bars)
    d1 = data.load_1d(tk)
    w1 = data.weekly_from_daily(d1)
    hier = data.tf_hierarchy_check(n1h, len(d1), len(w1))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bary 1h", f"{n1h:,}")
    c2.metric("Bary 1d (natywne)", f"{len(d1):,}")
    c3.metric("Bary 1w (z 1d)", f"{len(w1):,}")
    c4.metric("Hierarchia TF", f"{hier['ratio_1h_1d']:.0f}× / {hier['ratio_1d_1w']:.0f}×",
              help="proporcje 1h/1d i 1d/1w; obie muszą być ≥ 3× (bramka §1)")
    st.success("Bramka anty-lookahead: test „przesuń wszystkie cechy o +1 bar → metryka NIE rośnie” "
               "przechodzi (patrz `make fs-test`).")
    st.subheader("Pula cech (WO §1)")
    st.caption("≤ 4 wskaźniki na TF (po jednym na kategorię obserwacyjną) + cechy cross-TF "
               "mean-reversion. Wszystko stacjonarne / znormalizowane / ograniczone — bez surowych cen.")
    pool = pd.DataFrame(
        [{"TF": "1h", "cechy": ", ".join(FEAT.POOL_1H)},
         {"TF": "1d", "cechy": ", ".join(FEAT.POOL_1D)},
         {"TF": "1w", "cechy": ", ".join(FEAT.POOL_1W)},
         {"TF": "cross-TF", "cechy": ", ".join(FEAT.POOL_XTF)}])
    st.dataframe(pool, hide_index=True, width="stretch")
    st.caption(f"Wymuszony kanał cross-TF mean-reversion (rdzeń tezy, start pętli LSTM): "
               f"`{FEAT.MR_CHANNEL}`.")


# ============================ page 2: labels & Study 1 ============================

@st.cache_data(ttl=120)
def _label_sample(universe, ticker, params):
    from . import data, labels
    bars, feats = data.bar_frame(ticker, universe)
    close = bars["close"].to_numpy(float)
    sigma = labels.ewma_vol(close, params["ewma_span"])
    t0s = labels.cusum_events(close, sigma, params["cusum_mult"])
    t0k, y, t1, _ = labels.triple_barrier(close, t0s, sigma, params["pt"], params["sl"], params["h_bars"])
    ev = labels.build_events(bars, feats, params, ticker)
    ev = labels.assign_uniqueness(ev) if len(ev) else ev
    return bars, close, t0k, y, t1, ev


def page_labels(universe):
    st.header("2 · Etykiety i kalibracja (Study 1)")
    frozen = _load(universe, "labels_frozen.json")
    if not frozen:
        _need(universe, f"make fs-study1 UNIVERSE={universe}")
        return
    p = frozen["params"]
    st.markdown(
        "**Jedna prawda etykiet dla obu modeli.** Zdarzenia = symetryczny filtr **CUSUM** na "
        "log-zwrotach 1h (próg `h = mult · σ`, σ = EWMA-std). Etykieta = **3-klasowy Triple Barrier** "
        "(pierwsze dotknięcie): +1 gdy cena osiągnie `+pt·σ`, −1 gdy `−sl·σ`, 0 na barierze pionowej "
        "po `H` barach. Bez kosztów i fillów — to etykieta, nie transakcja. Parametry poniżej wybrała "
        "Optuna maksymalizując **macro-F1** referencyjnego XGB na Purged K-Fold.")
    cols = st.columns(6)
    labels_map = [("CUSUM mult", f"{p['cusum_mult']:.2f}"), ("EWMA span", f"{p['ewma_span']}"),
                  ("pt (TP·σ)", f"{p['pt']:.2f}"), ("sl (SL·σ)", f"{p['sl']:.2f}"),
                  ("H (bary)", f"{p['h_bars']}"), ("macro-F1 CV", f"{frozen['best_macro_f1_cv']:.3f}")]
    for c, (k, v) in zip(cols, labels_map):
        c.metric(k, v)

    st.subheader("Balans klas etykiety")
    cf = frozen["class_frac"]
    bal = pd.DataFrame([{"klasa": CLASS_NAME[k], "udział": cf[k], "_c": CLASS_COLOR[k]}
                        for k in ("-1", "0", "1")])
    _bar(bal, "klasa", "udział", "Rozkład klas (zamrożony zbiór CV)", fmt="%")

    tk = st.selectbox("Ticker podglądu zdarzeń", frozen["study1_tickers"], index=0)
    try:
        bars, close, t0k, y, t1, ev = _label_sample(universe, tk, p)
    except Exception as e:  # noqa: BLE001
        st.warning(f"Podgląd niedostępny: {e}")
        return
    st.subheader(f"Zdarzenia CUSUM + bariery na cenie — {tk}")
    st.caption("Ostatnie ~600 barów 1h okna CV. Kolor punktu = klasa pierwszego dotknięcia.")
    _price_events(bars, close, t0k, y, t1, p)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Wagi average-uniqueness**")
        st.caption("mean(1/współbieżność) po oknie [t0, t1] — nakładające się etykiety ważą mniej.")
        if len(ev):
            _hist(ev["w"].to_numpy(), "waga", "Rozkład wag próbek", color=C_UP)
    with c2:
        st.markdown("**Historia prób Optuny (Study 1)**")
        _optuna_history(universe, f"study1_{universe}", "macro-F1 (CV)")


# ============================ page 3: validation ============================

def page_validation(universe):
    st.header("3 · Walidacja: Purged K-Fold, embargo, CPCV")
    st.markdown(
        "Nakładające się etykiety psują zwykłą CV. Stąd **Purged K-Fold** (k=5): z treningu usuwa się "
        "zdarzenia, których okno informacyjny `[t_start, t1]` przecina blok testowy, plus **embargo** "
        "(~1% okna) tuż za nim. Dla XGB `t_start = t0` (purge = H); dla LSTM `t_start = t0 − (L−1)` "
        "(**purge = L + H**). Ocena końcowa to **CPCV**: N=6 grup, 2 testowe → C(6,2)=15 splitów, z "
        "których składa się 5 pełnych ścieżek OOS — dostajemy *rozkład* metryki, nie punkt.")
    k = CONFIG["CV"]["k"]
    _kfold_diagram(k)
    st.subheader("Mapa CPCV (6 grup, 2 testowe → 15 splitów)")
    st.caption("Każda grupa jest testowana w dokładnie 5 splitach; z tego powstaje 5 ścieżek OOS.")
    _cpcv_map(CONFIG["CPCV"]["n_groups"], CONFIG["CPCV"]["n_test_groups"])


# ============================ page 4: XGB loop ============================

def page_xgb(universe):
    st.header("4 · Pętla XGBoost — eliminacja wsteczna + clustered MDA")
    loop = _load(universe, "loop_xgb.json")
    champ = _load(universe, "selected_xgb.json")
    if not loop:
        _need(universe, f"make fs-xgb UNIVERSE={universe}")
        return
    st.markdown(
        "Klastrowanie korelacji (1−|ρ Spearman|) grupuje substytuty; **clustered MDA** (permutacja "
        "całego klastra na OOF, Δ macro-F1) rządzi rankingiem, a natywny SHAP (`pred_contribs`) "
        "kontroluje jego zgodność. Co rundę usuwany jest najsłabszy klaster; **STOP** = spadek "
        "> 1 SE od maksimum / 3 rundy bez poprawy / ≤ 15 cech. Wybrany zbiór = **najmniejszy zbiór w 1 SE**, "
        "utrwalony przez stabilność π.")
    _trajectory(loop["trajectory"], loop["one_se_choice"])
    rounds = _duck(universe, "select round, n_features, cv_mean, cv_se, removed from loop_rounds "
                             "where model='XGB' order by round")
    if len(rounds):
        st.subheader("Usunięcia per runda")
        rounds["removed"] = rounds["removed"].map(lambda s: ", ".join(json.loads(s)))
        st.dataframe(rounds.rename(columns={"round": "runda", "n_features": "liczba cech",
                                            "cv_mean": "macro-F1", "cv_se": "SE",
                                            "removed": "usunięto"}),
                     hide_index=True, width="stretch")
    if champ:
        _stability_bars(champ["pi"], champ["selected"], CONFIG["XGB_LOOP"]["stability_pi"])
        st.success(f"**Wybrany zbiór XGB ({len(champ['selected'])} cech):** {', '.join(champ['selected'])}")
    s2 = _load(universe, "study2_xgb.json")
    if s2:
        c1, c2, c3 = st.columns(3)
        c1.metric("macro-F1 CV (Study 2)", f"{s2['cv_macro_f1']:.3f} ± {s2['cv_se']:.3f}")
        c2.metric("próg p*", f"{s2['pstar']:.2f}")
        c3.metric("macro-F1 @ p*", f"{s2['pstar_macro_f1']:.3f}")
        with st.expander("Najlepsze hiperparametry (Study 2, HPO XGB)"):
            st.json(s2["best_params"])


# ============================ page 5: LSTM loop ============================

def page_lstm(universe):
    st.header("5 · Pętla LSTM — permutacja kanałów + ablacja")
    loop = _load(universe, "loop_lstm.json")
    champ = _load(universe, "selected_lstm.json")
    if not loop:
        _need(universe, f"make fs-lstm UNIVERSE={universe}")
        return
    st.markdown(
        "Sekwencje `(L, F)` barów 1h; kanały 1d/1w są stałe między zamknięciami wyższego TF (naturalny "
        "ffill z kontraktu danych). Scaler **z-score fitowany na train danego foldu** (artefakt audytu). "
        "Ranking kanałów = **permutacja** (tasowanie jednego kanału w całym oknie na OOF, ×10 po seedach) "
        "+ **ablacja** (retrening bez kanału) dla kandydatów do usunięcia. Start = top-k rankingu XGB + "
        "wymuszony kanał cross-TF mean-reversion. STOP = 1 SE / 3 rundy / ≤ 8 kanałów.")
    _trajectory(loop["trajectory"], loop["one_se_choice"], seed_std=True)
    st.caption(f"Zbiór startowy (top-k XGB + MR): {', '.join(loop.get('start_channels', []))}")
    if champ:
        _stability_bars(champ["pi"], champ["selected"], CONFIG["LSTM"]["stability_pi"])
        st.success(f"**Wybrany zbiór LSTM ({len(champ['selected'])} kanałów):** "
                   f"{', '.join(champ['selected'])}")
    s2 = _load(universe, "study2_lstm.json")
    if s2:
        c1, c2, c3 = st.columns(3)
        c1.metric("macro-F1 CV", f"{s2['cv_macro_f1']:.3f} ± {s2['cv_se']:.3f}")
        c2.metric("std między seedami", f"{s2.get('seed_std', 0):.4f}",
                  help="rozrzut macro-F1 między inicjalizacjami; wysoki = niestabilny trening")
        c3.metric("próg p*", f"{s2['pstar']:.2f}")
        with st.expander("Najlepsze hiperparametry (Study 2, HPO LSTM)"):
            st.json(s2["best_params"])


# ============================ page 6: SHAP ============================

def page_shap(universe):
    st.header("6 · SHAP per asset — audyt uniwersalności")
    df = _duck(universe, "select model, method, ticker, feature, shap_share, rank_in_ticker "
                         "from feature_importance_shap")
    if not len(df):
        _need(universe, f"make fs-xgb UNIVERSE={universe}   # etap shap  (i make fs-lstm)")
        return
    st.markdown(
        "Dla każdego tickera liczymy |SHAP| na predykcjach **out-of-fold** → udział cechy "
        "(`shap_share`, Σ = 1) i jej rangę. **coverage** = % tickerów, w których cecha ma udział "
        "> 1% (kryterium uniwersalności ≥ 80%). Cecha silna w < 20% tickerów jest flagowana jako "
        "asset-specific — kandydat do usunięcia.")
    model = st.radio("Model", sorted(df["model"].unique()), horizontal=True)
    d = df[df["model"] == model]
    st.caption(f"Metoda: `{d['method'].iloc[0]}`  ·  {d['ticker'].nunique()} tickerów × "
               f"{d['feature'].nunique()} cech")
    _shap_heatmap(d)
    uni = _duck(universe, f"select feature, median_rank, iqr_rank, coverage, asset_specific "
                          f"from shap_universality where model='{model}' order by coverage desc")
    if len(uni):
        st.subheader("Audyt uniwersalności cech")
        uni["asset_specific"] = uni["asset_specific"].map({1: "⚠ tak", 0: "nie"})
        st.dataframe(uni.rename(columns={"feature": "cecha", "median_rank": "mediana rangi",
                                         "iqr_rank": "IQR rangi", "coverage": "coverage",
                                         "asset_specific": "asset-specific"}),
                     hide_index=True, width="stretch",
                     column_config={"coverage": st.column_config.NumberColumn("coverage", format="%.2f")})


# ============================ page 7: verdict ============================

def page_verdict(universe):
    st.header("7 · Werdykt OOS — rozkład CPCV, holdout, PBO, DSR")
    st.markdown(
        "Uczciwy test: **holdout czytany dokładnie raz** (strażnik `holdout_used_*.flag`). **PBO** "
        "(prawdopodobieństwo przeuczenia backtestu, CSCV) i **DSR** (deflated Sharpe, korekta na "
        "liczbę prób Optuny) mówią, czy wynik nie jest artefaktem wielokrotnego testowania. "
        "Oba modele oceniamy na **tych samych etykietach** — porównanie jest sprawiedliwe.")
    for model, tag in (("XGB", "verdict_xgb.json"), ("LSTM", "verdict_lstm.json")):
        v = _load(universe, tag)
        st.subheader(f"Model {model}")
        if not v:
            st.info(f"Holdout dla {model} jeszcze nie odczytany (świadomie, raz): "
                    f"`make fs-holdout-{model.lower()} UNIVERSE={universe}`")
            continue
        rep = v["holdout_report"]
        c = st.columns(5)
        c[0].metric("macro-F1 (holdout)", f"{rep['macro_f1']:.3f}")
        c[1].metric("MCC", f"{rep['mcc']:.3f}")
        c[2].metric("Sharpe", f"{v['holdout_sharpe']:.2f}")
        c[3].metric("PBO", f"{v['pbo']['pbo']:.2f}" if v.get("pbo") else "—",
                    help="< 0.5 dobrze; cel < 0.1")
        c[4].metric("DSR", f"{v['dsr']['dsr']:.2f}" if v.get("dsr") else "—",
                    help="> 0.95 = wynik przebija szum wielokrotnego testowania")
        paths = _duck(universe, f"select unit_id, score from cv_scores where model='{model}' "
                                f"and stage='cpcv' and unit='path' order by unit_id")
        if len(paths):
            st.caption("Rozkład macro-F1 na 5 ścieżkach CPCV (OOS Train-side):")
            _bar(paths.assign(_c=C_UP).rename(columns={"unit_id": "ścieżka", "score": "macro-F1"}),
                 "ścieżka", "macro-F1", f"CPCV — {model}", fmt="f")
    st.divider()
    _compare(universe)


# ============================ chart helpers (Altair) ============================

def _alt():
    import altair as alt
    return alt


def _bar(df, x, y, title, fmt="f"):
    alt = _alt()
    fmt_s = ".0%" if fmt == "%" else ".3f"
    color = alt.Color("_c:N", scale=None) if "_c" in df else alt.value(C_UP)
    ch = (alt.Chart(df).mark_bar(cornerRadiusEnd=4, size=40)
          .encode(x=alt.X(f"{x}:N", sort=None, title=None),
                   y=alt.Y(f"{y}:Q", title=None, axis=alt.Axis(format=fmt_s)),
                   color=color,
                   tooltip=[x, alt.Tooltip(f"{y}:Q", format=fmt_s)])
          .properties(title=title, height=240))
    st.altair_chart(ch, width="stretch")


def _hist(x, label, title, color=C_UP, bins=40):
    alt = _alt()
    df = pd.DataFrame({label: np.asarray(x)[np.isfinite(x)]})
    ch = (alt.Chart(df).mark_bar(color=color, cornerRadiusEnd=2)
          .encode(x=alt.X(f"{label}:Q", bin=alt.Bin(maxbins=bins), title=label),
                   y=alt.Y("count():Q", title="liczba"))
          .properties(title=title, height=220))
    st.altair_chart(ch, width="stretch")


def _price_events(bars, close, t0k, y, t1, p, window=600):
    alt = _alt()
    n = len(close)
    lo = max(n - window, 0)
    price = pd.DataFrame({"i": np.arange(lo, n), "close": close[lo:]})
    line = (alt.Chart(price).mark_line(color="#5b6470", strokeWidth=1.5)
            .encode(x=alt.X("i:Q", title="bar 1h (indeks)"),
                    y=alt.Y("close:Q", title="cena", scale=alt.Scale(zero=False))))
    m = (t0k >= lo)
    ev = pd.DataFrame({"i": t0k[m], "close": close[t0k[m]],
                       "klasa": [CLASS_NAME[str(int(v))] for v in y[m]]})
    dom = [CLASS_NAME["1"], CLASS_NAME["0"], CLASS_NAME["-1"]]
    rng = [C_UP, C_ZERO, C_DOWN]
    pts = (alt.Chart(ev).mark_point(size=55, filled=True, opacity=0.85)
           .encode(x="i:Q", y="close:Q",
                   color=alt.Color("klasa:N", scale=alt.Scale(domain=dom, range=rng),
                                   legend=alt.Legend(title="klasa (first touch)")),
                   tooltip=["i", "klasa"]))
    st.altair_chart((line + pts).properties(height=320), width="stretch")


def _optuna_history(universe, study_name, ylabel):
    db = art(universe) / "optuna.db"
    if not db.exists():
        st.caption("brak optuna.db")
        return
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        q = ("select t.number, t.value from trials t join studies s on t.study_id=s.study_id "
             "where s.study_name=? and t.value is not null order by t.number")
        rows = con.execute(q, [study_name]).fetchall()
        con.close()
    except sqlite3.Error:
        rows = []
    if not rows:
        st.caption("brak zakończonych prób")
        return
    df = pd.DataFrame(rows, columns=["próba", "value"])
    df["najlepsza dotąd"] = df["value"].cummax()
    alt = _alt()
    base = alt.Chart(df)
    pts = base.mark_circle(size=30, color=C_ZERO, opacity=0.5).encode(
        x="próba:Q", y=alt.Y("value:Q", title=ylabel, scale=alt.Scale(zero=False)),
        tooltip=["próba", alt.Tooltip("value:Q", format=".3f")])
    best = base.mark_line(color=C_UP, strokeWidth=2).encode(x="próba:Q", y="najlepsza dotąd:Q")
    st.altair_chart((pts + best).properties(height=220), width="stretch")


def _trajectory(traj, chosen, seed_std=False):
    alt = _alt()
    df = pd.DataFrame([{"liczba cech": len(t["features"]), "macro-F1": t["mean"],
                        "lo": t["mean"] - t["se"], "hi": t["mean"] + t["se"],
                        "wybrany": len(t["features"]) == len(chosen)} for t in traj])
    band = (alt.Chart(df).mark_area(opacity=0.18, color=C_UP)
            .encode(x=alt.X("liczba cech:Q", sort="descending",
                            scale=alt.Scale(reverse=True), title="liczba cech (← eliminacja)"),
                    y=alt.Y("lo:Q", title="macro-F1 (CV)", scale=alt.Scale(zero=False)), y2="hi:Q"))
    line = (alt.Chart(df).mark_line(color=C_UP, strokeWidth=2, point=True)
            .encode(x=alt.X("liczba cech:Q", scale=alt.Scale(reverse=True)), y="macro-F1:Q",
                    tooltip=["liczba cech", alt.Tooltip("macro-F1:Q", format=".4f")]))
    pick = (alt.Chart(df[df["wybrany"]]).mark_point(size=160, color=C_DOWN, filled=False,
                                                    strokeWidth=3)
            .encode(x=alt.X("liczba cech:Q", scale=alt.Scale(reverse=True)), y="macro-F1:Q"))
    st.altair_chart((band + line + pick).properties(
        title="Trajektoria eliminacji (±1 SE); ◯ = wybór 1-SE", height=300),
        width="stretch")
    if seed_std:
        ss = pd.DataFrame([{"liczba cech": len(t["features"]), "std-seed": t.get("seed_std", 0)}
                           for t in traj])
        st.caption("Std macro-F1 między seedami per runda (wysoki = niestabilny trening, nie „lepsza cecha”):")
        st.altair_chart(alt.Chart(ss).mark_bar(color=C_ZERO, cornerRadiusEnd=2).encode(
            x=alt.X("liczba cech:Q", scale=alt.Scale(reverse=True)),
            y=alt.Y("std-seed:Q", title="std")).properties(height=140), width="stretch")


def _stability_bars(pi, selected, threshold):
    alt = _alt()
    df = pd.DataFrame([{"cecha": f, "π": v, "selected": f in selected}
                       for f, v in sorted(pi.items(), key=lambda kv: -kv[1])])
    ch = (alt.Chart(df).mark_bar(cornerRadiusEnd=3)
          .encode(y=alt.Y("cecha:N", sort="-x", title=None),
                  x=alt.X("π:Q", title="częstość wyboru π (bootstrapy)",
                          scale=alt.Scale(domain=[0, 1])),
                  color=alt.Color("selected:N",
                                  scale=alt.Scale(domain=[True, False], range=[C_UP, C_ZERO]),
                                  legend=alt.Legend(title=f"π ≥ {threshold}")),
                  tooltip=["cecha", alt.Tooltip("π:Q", format=".2f")])
          .properties(title="Stabilność selekcji", height=max(240, 22 * len(df))))
    rule = alt.Chart(pd.DataFrame({"t": [threshold]})).mark_rule(
        color=C_DOWN, strokeDash=[4, 3]).encode(x="t:Q")
    st.altair_chart(ch + rule, width="stretch")


def _shap_heatmap(d):
    alt = _alt()
    order = (d.groupby("feature")["shap_share"].mean().sort_values(ascending=False).index.tolist())
    ch = (alt.Chart(d).mark_rect()
          .encode(x=alt.X("ticker:N", title=None),
                  y=alt.Y("feature:N", sort=order, title=None),
                  color=alt.Color("shap_share:Q", title="udział SHAP",
                                  scale=alt.Scale(range=SEQ)),
                  tooltip=["ticker", "feature", alt.Tooltip("shap_share:Q", format=".3f"),
                           "rank_in_ticker"])
          .properties(title="|SHAP| per asset (udział, OOF)",
                      height=max(240, 26 * d["feature"].nunique())))
    st.altair_chart(ch, width="stretch")


def _kfold_diagram(k):
    alt = _alt()
    rows = []
    for f in range(k):
        for g in range(k):
            if g == f:
                role = "test"
            elif abs(g - f) == 1:
                role = "purge/embargo"
            else:
                role = "train"
            rows.append({"fold": f"fold {f + 1}", "blok": g, "rola": role})
    df = pd.DataFrame(rows)
    dom = ["train", "purge/embargo", "test"]
    rng = [C_UP, C_DOWN, C_ZERO]
    ch = (alt.Chart(df).mark_rect(stroke="white", strokeWidth=2)
          .encode(x=alt.X("blok:O", title="blok czasu →"),
                  y=alt.Y("fold:N", title=None),
                  color=alt.Color("rola:N", scale=alt.Scale(domain=dom, range=rng),
                                  legend=alt.Legend(title=None, orient="top")),
                  tooltip=["fold", "rola"])
          .properties(title=f"Purged K-Fold (k={k}) + embargo", height=40 * k))
    st.altair_chart(ch, width="stretch")


def _cpcv_map(n, ntest):
    from itertools import combinations
    alt = _alt()
    rows = []
    for si, gs in enumerate(combinations(range(n), ntest)):
        for g in range(n):
            rows.append({"split": si, "grupa": g, "rola": "test" if g in gs else "train"})
    df = pd.DataFrame(rows)
    ch = (alt.Chart(df).mark_rect(stroke="white", strokeWidth=1.5)
          .encode(x=alt.X("grupa:O", title="grupa"),
                  y=alt.Y("split:O", title="split"),
                  color=alt.Color("rola:N", scale=alt.Scale(domain=["train", "test"],
                                                            range=[C_UP, C_DOWN]),
                                  legend=alt.Legend(title=None, orient="top")),
                  tooltip=["split", "grupa", "rola"])
          .properties(height=26 * len(list(combinations(range(n), ntest)))))
    st.altair_chart(ch, width="stretch")


def _compare(universe):
    st.subheader("XGB vs LSTM — te same etykiety")
    vx, vl = _load(universe, "verdict_xgb.json"), _load(universe, "verdict_lstm.json")
    rows = []
    for name, v in (("XGBoost", vx), ("LSTM", vl)):
        if v:
            rows.append({"model": name, "macro-F1 (holdout)": v["holdout_report"]["macro_f1"],
                         "macro-F1 (CV)": v.get("cv_macro_f1"), "Sharpe": v["holdout_sharpe"],
                         "PBO": (v.get("pbo") or {}).get("pbo"),
                         "DSR": (v.get("dsr") or {}).get("dsr"),
                         "selected": len(v["selected"])})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    else:
        st.info("Uruchom holdout obu modeli, aby zobaczyć porównanie.")


PAGES = {
    "1 · Dane i kontrakt": page_data,
    "2 · Etykiety i Study 1": page_labels,
    "3 · Walidacja (CV/CPCV)": page_validation,
    "4 · Pętla XGBoost": page_xgb,
    "5 · Pętla LSTM": page_lstm,
    "6 · SHAP per asset": page_shap,
    "7 · Werdykt OOS": page_verdict,
}


def render(universe="demo"):
    st.title("Studium selekcji cech (WO-FS)")
    st.caption("Jak powstają artefakty ML i jak kalibruje się parametry — XGBoost i LSTM na wspólnych, "
               "3-klasowych etykietach Triple-Barrier. Wszystko renderowane z `fs/artifacts/` — nic "
               "nie trenuje się w trakcie.")
    universes = [u.name for u in ART.iterdir() if u.is_dir() and u.name in ("demo", "full")] \
        if ART.exists() else []
    universes = universes or ["demo"]
    u = st.sidebar.selectbox("Uniwersum", universes, index=0)
    page = st.sidebar.radio("Strona", list(PAGES), index=0)
    PAGES[page](u)
