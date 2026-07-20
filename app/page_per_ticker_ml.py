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


def render() -> None:
    if not STUDY.is_dir():
        st.error(f"The per-ticker study is missing: {STUDY.name}/ not found in this checkout.")
        return

    st.markdown(SCOPED_CSS, unsafe_allow_html=True)

    labels = [label for label, _ in TABS]
    for tab, (label, script) in zip(st.tabs(labels, key="ptml_tab", on_change="rerun"), TABS):
        if not tab.open:                 # lazy: only the selected sub-tab executes
            continue
        with tab, _restore_sys_path():
            try:
                runpy.run_path(str(script), run_name="__main__")
            except ScriptControlException:
                raise                    # st.stop() / st.rerun(): Streamlit's own control flow
            except Exception as exc:     # a broken vendor must not take the host app down
                st.error(f"“{label}” failed to render: {exc}")
