#!/usr/bin/env python3
"""Per Ticker ML-Model — the sealed per-asset indicator study, as three sub-tabs.

The study lives verbatim under per_ticker_ml/ (a 1:1 graft of the presentation branch
Stable_Presentable_Version). Its pages are Streamlit SCRIPT-style modules — top-level code,
no render() — so they are executed with runpy rather than imported, which is what keeps the
vendored tree byte-identical to its source and diffable against it.

Three things have to be contained so the vendor cannot disturb this app:

  * st.stop() is ordinary control flow over there, not an error path:
    per_ticker_ml/app/pages/simulator.py:323 fires on every fresh load (stage == "pick").
    In Streamlit 1.58 st.stop() does not raise at the call site — it latches
    ScriptRequestType.STOP and yields, and ScriptRequests.on_scriptrunner_yield() then
    "remains stopped" for the rest of the run. So the stop CANNOT be swallowed: catching the
    exception is pointless because the next session-state access re-raises it. It is allowed
    to propagate (see the ScriptControlException re-raise below), which ends the run exactly
    as it does when the study runs standalone. app/app.py therefore renders its sidebar
    caption and Ctrl+B hotkey BEFORE pg.run(), so a page that stops cannot take them down.

  * Because of that latch, the session-key swap cannot go through st.session_state: it would
    abort on its first access and strand the study's basket in the host's keys. It goes
    through the raw SessionState instead — see _raw_state().

  * Each study page calls sys.path.insert(0, ...) unconditionally, so the path is snapshot
    and restored; otherwise it grows by one entry on every rerun for the whole session.

  * The study ships a dark .streamlit/config.toml, but only the ROOT config is honoured and this
    app's has no [theme] block — so the chrome follows the VIEWER'S BROWSER and can be either.
    Its charts are handed back to Streamlit's own adaptive template and its other surfaces
    follow the reported theme, then everything is restored. See _host_theme().

The study shares stage / basket / method / method_sel (and the host adds preset*) with
app/page_simulator.py, over a DIFFERENT universe — 993 sealed assets vs the 498-ticker OOS
store. sync_session_scope() gives those keys to whichever page is active, so a basket built
here cannot leak into Basket Simulator (Track B) or the other way round. It is called from
app/app.py before pg.run(), NOT around this render: widget callbacks run before the script
body, so a render-scoped swap leaves them reading keys that are not there.

Tabs are lazy — on_change="rerun" plus tab.open — so only the selected sub-tab executes and
the 31.6 MB store is not queried three times per interaction.
"""
import runpy
import sys
from contextlib import contextmanager
from pathlib import Path

import streamlit as st
from streamlit.runtime.scriptrunner_utils.exceptions import ScriptControlException

STUDY = Path(__file__).resolve().parents[1] / "per_ticker_ml"
STUDY_APP = STUDY / "app"
URL_PATH = "per-ticker-ml"                   # must match the st.Page(...) in app/app.py

# (tab label, page script) — the study's own sidebar order, preserved.
TABS = [
    ("Basket Simulator (Recommender)", STUDY_APP / "pages" / "simulator.py"),
    ("Statistics",                     STUDY_APP / "pages" / "overview.py"),
    ("Data Pipeline Lego Plan",        STUDY_APP / "pages" / "blueprint.py"),
]

# Keys the study and app/page_simulator.py both write, with different meanings.
# (formular/ui.py writes stage/basket/basket_source/basket_edited too — same namespace.)
_SHARED = ("stage", "basket", "basket_source", "basket_edited", "method", "method_sel",
           "preset", "preset_sel", "preset_result")
_NS = "_ptml__"          # the study's parked copy
_HOST = "_host__"        # the rest of the app's parked copy
_OWNER = "_ptml__owner"  # which side currently holds the bare keys

# The study hard-codes a dark palette because it ships its own .streamlit/config.toml with
# base="dark". Only the ROOT config is honoured here and this app's has NO [theme] block — which
# means the chrome follows the VIEWER'S BROWSER, and can be either. So there is no single right
# palette to bake in, and the colours are decided when the figures are BUILT
# (theme.plotly_layout(), the graphviz DOT's bgcolor, GRID_CSS), not applied as styles CSS could
# later override. Two different mechanisms are needed:
#
#   * Plotly is made theme-AGNOSTIC and left to Streamlit. st.plotly_chart defaults to
#     theme="streamlit", whose template already adapts to light and dark; the study was fighting
#     it by forcing paper/plot backgrounds and a font colour. Forcing a LIGHT background while
#     the template supplied dark-mode (light) text is what produced unreadable charts. The
#     wrapper below drops those keys instead, so the template wins on a transparent canvas.
#
#   * Graphviz and the CSS classes are not themed by Streamlit, so those constants are switched
#     using the viewer's reported theme — and only when it says "light". When it says "dark", or
#     says nothing, the study's native palette is left exactly as designed, which is also the
#     safe failure mode: a dark diagram on a light page is merely out of place, whereas a light
#     diagram on a dark page can be unreadable.
#
# A global dark theme is the wrong lever: it would restyle all eight existing pages and fight
# page_simulator.py's hard-coded light tiles.
#
# ACCENT darkens for the light case because overview.py's DOT paints ACCENT-filled nodes with
# fontcolor=BG — once BG is white, the study's #6EA8CF has too little contrast behind white text.
# GREEN/AMBER/RED are used as TEXT, so they take their light-background variants.
_LIGHT_PALETTE = {
    "BG": "#FFFFFF", "SURFACE": "#F0F2F6", "BORDER": "#D5D9E0",
    "TEXT": "#31333F", "TEXT_DIM": "#6E7681",
    "ACCENT": "#1F6FEB", "NEUTRAL": "#57606A", "MUTED": "#8C959F",
    "GREEN": "#1A7F37", "AMBER": "#9A6700", "RED": "#CF222E",
}


def _raw_state():
    """Session state WITHOUT the script-runner yield check.

    Every read and write through st.session_state calls the runner's yield callback
    (SafeSessionState.__getitem__/__setitem__/__delitem__/__contains__), and once a stop has
    been requested that callback re-raises StopException at every single access — the request
    latches for the whole run and on_scriptrunner_yield() explicitly "remains stopped". The
    study latches one on nearly every render, so a swap performed through the public proxy
    aborts on its first access and strands the study's basket in the host's keys. The
    SessionState underneath does the same work without the yield check.
    """
    try:
        from streamlit.runtime.state.session_state_proxy import get_session_state
        return get_session_state()._state
    except Exception:                        # pragma: no cover — future-Streamlit fallback
        return st.session_state


_MISSING = object()


def _get(state, key):
    try:
        return state[key]
    except KeyError:
        return _MISSING


def _drop(state, key):
    try:
        del state[key]
    except KeyError:
        pass


def sync_session_scope(active_url_path: str) -> None:
    """Hand the shared session keys to whichever page owns them now. Call before pg.run().

    The swap CANNOT be done around this page's render. Widget callbacks (the study's
    _select_method and _toggle) run from on_script_will_rerun, at the very start of the next
    script run — before app.py executes, so before any render-scoped swap could put the
    study's keys back. A callback would then read a key that had been parked away and die with
    "st.session_state has no attribute method_sel".

    So ownership changes on PAGE TRANSITION instead, and persists between runs: whichever page
    the user is on keeps the bare keys, which is exactly what its callbacks expect to find.
    """
    state = _raw_state()
    want = "study" if active_url_path == URL_PATH else "host"
    if _get(state, _OWNER) is _MISSING:
        state[_OWNER] = "host"
    if state[_OWNER] == want:
        return

    park, load = (_NS, _HOST) if want == "host" else (_HOST, _NS)
    for key in _SHARED:
        current = _get(state, key)
        if current is not _MISSING:
            state[park + key] = current
        _drop(state, key)
        saved = _get(state, load + key)
        if saved is not _MISSING:
            state[key] = saved
    state[_OWNER] = want


@contextmanager
def _restore_sys_path():
    """Each study page inserts its own app/ at sys.path[0] unconditionally; without this the
    path grows by one entry on every rerun for the life of the session."""
    path = list(sys.path)
    try:
        yield
    finally:
        sys.path[:] = path


def viewer_theme() -> str:
    """"light" or "dark" as reported by the browser, "dark" when Streamlit will not say.

    st.context.theme.type is documented as possibly wrong while a theme is changing and on the
    first load of a session, so it decides only the surfaces whose failure mode stays readable.
    """
    try:
        return st.context.theme.type or "dark"
    except Exception:                               # pragma: no cover — no script context
        return "dark"


def _agnostic_layout(original):
    """Wrap theme.plotly_layout so figures stop dictating their own light/dark surface."""
    def layout(**overrides):
        out = original(**overrides)
        out["paper_bgcolor"] = "rgba(0,0,0,0)"      # let the Streamlit template paint it
        out["plot_bgcolor"] = "rgba(0,0,0,0)"
        out.pop("font", None)                       # ...and colour the text, in either theme
        for axis in ("xaxis", "yaxis"):             # grid that reads on white and on near-black
            if isinstance(out.get(axis), dict):
                out[axis] = {**out[axis], "gridcolor": "rgba(128,128,128,0.25)",
                             "zerolinecolor": "rgba(128,128,128,0.35)"}
        return out
    return layout


@contextmanager
def _host_theme():
    """Render the study in the viewer's theme, without editing per_ticker_ml/ on disk.

    theme.plotly_layout() reads the constants at CALL time, and overview.py's DOT and
    simulator.py's GRID_CSS are f-strings rebuilt on every runpy execution — so swapping the
    constants first reaches the diagram, the tiles and the tables alike. theme.CSS is the
    exception: an f-string frozen at import. It is re-lit by substituting the old hex values for
    the new ones, rather than restating the stylesheet here where it would rot the moment the
    study's own changed.
    """
    if str(STUDY_APP) not in sys.path:              # the study's own pages do this too, later
        sys.path.insert(0, str(STUDY_APP))
    import theme
    names = (*_LIGHT_PALETTE, "CSS", "MODEL_COLORS", "plotly_layout")
    saved = {name: getattr(theme, name) for name in names}
    try:
        theme.plotly_layout = _agnostic_layout(saved["plotly_layout"])
        if viewer_theme() == "light":
            css = saved["CSS"]
            for name, light in _LIGHT_PALETTE.items():
                css = css.replace(saved[name], light)
                setattr(theme, name, light)
            theme.CSS = css
            theme.MODEL_COLORS = {"xgb": theme.ACCENT, "lstm": theme.NEUTRAL, "hodl": theme.MUTED}
        yield
    finally:
        for name, value in saved.items():
            setattr(theme, name, value)


def render() -> None:
    if not STUDY.is_dir():
        st.error(f"The per-ticker study is missing: {STUDY.name}/ not found in this checkout.")
        return

    labels = [label for label, _ in TABS]
    for tab, (label, script) in zip(st.tabs(labels, key="ptml_tab", on_change="rerun"), TABS):
        if not tab.open:                 # lazy: only the selected sub-tab executes
            continue
        with tab, _restore_sys_path(), _host_theme():
            try:
                runpy.run_path(str(script), run_name="__main__")
            except ScriptControlException:
                raise                    # st.stop() / st.rerun(): Streamlit's own control flow
            except Exception as exc:     # a broken vendor must not take the host app down
                st.error(f"“{label}” failed to render: {exc}")
