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

  * Because of that latch, the session-state swap below cannot go through st.session_state:
    it would abort on its first access and strand the study's basket in the host's keys. It
    goes through the raw SessionState instead — see _raw_state().

  * Each study page calls sys.path.insert(0, ...) unconditionally, so the path is snapshot
    and restored; otherwise it grows by one entry on every rerun for the whole session.

The study shares stage / basket / method / method_sel with app/page_simulator.py, over a
DIFFERENT universe (993 sealed assets vs the 498-ticker OOS store). Those keys are swapped
into a private namespace around the run, so a basket built here cannot leak into Basket
Simulator (Track B) or the other way round.

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

# (tab label, page script) — the study's own sidebar order, preserved.
TABS = [
    ("Basket Simulator (Recommender)", STUDY_APP / "pages" / "simulator.py"),
    ("Statistics",                     STUDY_APP / "pages" / "overview.py"),
    ("Data Pipeline Lego Plan",        STUDY_APP / "pages" / "blueprint.py"),
]

# Keys the study and app/page_simulator.py both write, with different meanings.
# (formular/ui.py writes stage/basket/basket_source/basket_edited too — same namespace.)
_SHARED = ("stage", "basket", "basket_source", "basket_edited", "method", "method_sel")
_NS = "_ptml__"

# The study hard-codes a dark palette in Python (plotly figures, the graphviz DOT, the tile
# and tooltip CSS) because it ships its own .streamlit/config.toml with base="dark". Only the
# ROOT config is honoured here and this app's has no [theme] block, so those surfaces land on
# light chrome. Rather than restyle all eight existing pages — page_simulator.py hard-codes
# light tiles and would fight a global dark theme — the few classes that actually break are
# repaired for this page only. .disclaimer-box is the one that is unreadable otherwise: it
# sets a near-black background and inherits the host's dark text.
SCOPED_CSS = """
<style>
.disclaimer-box { color: #E6EDF3; }
.disclaimer-box b, .disclaimer-box strong { color: #FFFFFF; }
</style>
"""


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


@contextmanager
def _isolated():
    """Run the study against its OWN copy of the colliding session keys."""
    state = _raw_state()

    def get(key, default=None):
        try:
            return state[key]
        except KeyError:
            return default

    def drop(key):
        try:
            del state[key]
        except KeyError:
            pass

    missing = object()
    host = {k: get(k, missing) for k in _SHARED}
    for k in _SHARED:
        drop(k)
        saved = get(_NS + k, missing)
        if saved is not missing:
            state[k] = saved
    path = list(sys.path)
    try:
        yield
    finally:
        sys.path[:] = path
        for k in _SHARED:
            current = get(k, missing)
            if current is not missing:
                state[_NS + k] = current
            drop(k)
            if host[k] is not missing:
                state[k] = host[k]


def render() -> None:
    if not STUDY.is_dir():
        st.error(f"The per-ticker study is missing: {STUDY.name}/ not found in this checkout.")
        return

    st.markdown(SCOPED_CSS, unsafe_allow_html=True)

    labels = [label for label, _ in TABS]
    for tab, (label, script) in zip(st.tabs(labels, key="ptml_tab", on_change="rerun"), TABS):
        if not tab.open:                 # lazy: only the selected sub-tab executes
            continue
        with tab, _isolated():
            try:
                runpy.run_path(str(script), run_name="__main__")
            except ScriptControlException:
                raise                    # st.stop() / st.rerun(): Streamlit's own control flow
            except Exception as exc:     # a broken vendor must not take the host app down
                st.error(f"“{label}” failed to render: {exc}")
