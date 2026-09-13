"""Requirements Accelerator, v1 frontend: a locally hosted Streamlit app.

streamlit run app.py

Same engine as cli.py (Ledger, ClaudeCodeReasoner, SqliteRetainedKnowledge, SqliteStorage,
run_interview), none of it touched. The only new code is bridge.py, which lets
engine/interview.py's blocking question loop run on a background thread and talk to Streamlit's
rerun-per-interaction model through two queues; see that module's docstring for the reasoning.
This file is the Streamlit-specific half: wiring the engine up to session state, and drawing
whatever the current state calls for.

Widget fidelity: docs/interview-ux.md classifies every question as free text (FT), multi-choice
(MC), hybrid (HYB, a few preset chips plus an always-visible "something else" text box) or banded
(BAND, a continuum, mechanically the same as MC). That classification already lives as data, not
prose: engine/protocol.py's Question.choices carries the exact option list for every MC/HYB/BAND
question and is None for every FT one, and bridge.py now passes it straight through on every
"waiting" signal (see its docstring). `_render_question` below renders from that alone: choices
present and containing "something else" is HYB (buttons for the fixed options, plus an
always-visible text box), present without it is MC/BAND (buttons only, no free-text escape hatch,
matching docs/interview-ux.md's own rule that a genuinely closed answer space gets none), absent
is FT (the text box, as before). Layer 07's competing-definition check, the one field whose
choices depend on runtime state (whether retained knowledge has a prior definition for the term),
now has a real list too: engine/protocol.py's COMPETING_DEFINITION_CHOICES_WITH_PRIOR /
_NO_PRIOR, whichever matches the phrasing engine/interview.py already branches on for that term.
That was the last MC/HYB/BAND question in the protocol still rendering as free text.

Delivery: once an interview finishes, the two rendered documents are also written to disk via
engine/delivery.py (a2), the same call cli.py makes, so they land somewhere real (a synced
OneDrive/SharePoint folder, if that's what the two configured paths point at) rather than only
existing in a browser tab that closes.

a3 spike (docs/architecture-decisions.md's "a3 spike" entry): this same file is also the one
deployed as the Streamlit-in-Snowflake app for that spike, unmodified except for
`_select_reasoner` below. Storage and delivery are untouched, still SqliteStorage and a local
disk write, since the spike is scoped to the model-provider seam only; a local SQLite file
inside the app's container is fine for proving the reasoner swap and bridge.py's threading
model, even though it won't persist across app restarts, that's a3's storage seam, not this
spike's job.
"""

import uuid

import streamlit as st

from bridge import Bridge, start_interview_thread
from engine.delivery import deliver_documents
from engine.interview import run_interview
from engine.knowledge import SqliteRetainedKnowledge
from engine.ledger import Ledger
from engine.reasoner import ClaudeCodeReasoner
from engine.render import render_business_ask, render_technical_spec
from engine.storage import SqliteStorage

DB_PATH = "requirements_accelerator.db"

SESSION_KEYS = (
    "bridge", "thread", "ledger", "interview_id", "transcript", "status", "error", "choices",
    "delivered",
)


def _rerun() -> None:
    """st.rerun(), falling back to the older st.experimental_rerun() name. Needed because
    Streamlit-in-Snowflake's bundled Streamlit build (as of this a3 spike run, 13 September
    2026) predates the rerun() rename and only exposes experimental_rerun(), confirmed live
    against the deployed app after st.rerun() raised AttributeError there. Local Streamlit
    installs have st.rerun() and never touch the fallback.
    """
    rerun = getattr(st, "rerun", None) or st.experimental_rerun
    rerun()


def _pump(reply: str | None = None) -> None:
    """Hand a reply to the waiting engine thread (if any) and block until it produces the next
    thing worth showing: more narration to display, a new prompt to wait on, or a terminal
    signal. Narration arrives interleaved with the "waiting" signal on the same queue, so this
    drains everything up to and including the first waiting/done/error before returning. The
    block is the point: Streamlit shows its own spinner for as long as the reasoner call
    underneath takes, ClaudeCodeReasoner's `claude -p` calls included, rather than this needing
    any polling of its own.
    """
    bridge: Bridge = st.session_state.bridge
    if reply is not None:
        bridge.input_queue.put(reply)
    while True:
        signal, payload = bridge.signal_queue.get()
        if signal == "narration":
            st.session_state.transcript += payload
            continue
        if signal == "waiting":
            st.session_state.status = "waiting"
            st.session_state.choices = payload  # the pending question's fixed options, or None
        elif signal == "done":
            st.session_state.status = "done"
            ledger = st.session_state.ledger
            SqliteStorage(DB_PATH).save_interview(st.session_state.interview_id, ledger)
            st.session_state.delivered = deliver_documents(
                st.session_state.interview_id,
                render_business_ask(ledger),
                render_technical_spec(ledger),
            )
        elif signal == "error":
            st.session_state.status = "error"
            st.session_state.error = payload
        return


def _select_reasoner():
    """Picks the reasoner for wherever this file is actually running, ClaudeCodeReasoner
    locally (unchanged from before the a3 spike) or CortexReasoner inside Streamlit in
    Snowflake. get_active_session() only succeeds inside an actual Snowflake-hosted runtime, so
    trying it first and falling back is a real environment check, not a guess; the import
    itself lives inside the try so a local run with no snowflake packages installed never sees
    an ImportError, exactly the same reasoning engine/cortex_reasoner.py's own docstring gives
    for keeping that import out of engine/reasoner.py.
    """
    try:
        from snowflake.snowpark.context import get_active_session
        get_active_session()
    except Exception:
        return ClaudeCodeReasoner()
    from engine.cortex_reasoner import CortexReasoner
    return CortexReasoner()


def _reasoner_requirement_caption() -> str:
    """What this deployment needs in order to answer, in the requester's own terms: the `claude`
    CLI locally, or nothing extra inside Snowflake since Cortex is already part of the account.
    Runs the same environment check as _select_reasoner so this caption never claims the wrong
    one; discovered as stale (it named the `claude` CLI unconditionally) once the a3 spike
    actually ran inside Snowflake, where that CLI was never true.
    """
    try:
        from snowflake.snowpark.context import get_active_session
        get_active_session()
    except Exception:
        return "Needs the `claude` CLI installed and logged in on this machine."
    return "Runs on Snowflake Cortex, already available in this account."


def _start_interview() -> None:
    # StubReasoner is never an option here, on top of the environment choice above: its
    # judge()/extract_terms()/reframe()/consolidate_terms() ask via the `input()` builtin
    # directly rather than the injected `ask`, which only works when something is actively
    # patching that builtin for a direct, unthreaded call (exactly what every
    # examples/demo_*.py script does). Run through this bridge instead, on a background thread
    # with no attached terminal stdin, that same call raises EOFError - confirmed while
    # building this. Not a StubReasoner bug to fix: it was always test/demo-only machinery, and
    # cli.py never offered it as a runtime choice either.
    ledger = Ledger()
    reasoner = _select_reasoner()
    knowledge = SqliteRetainedKnowledge(DB_PATH)
    bridge = Bridge()

    st.session_state.bridge = bridge
    st.session_state.thread = start_interview_thread(bridge, run_interview, ledger, reasoner,
                                                       knowledge)
    st.session_state.ledger = ledger
    st.session_state.interview_id = str(uuid.uuid4())
    st.session_state.transcript = ""
    st.session_state.status = "running"
    st.session_state.choices = None

    _pump()


def _reset() -> None:
    for key in SESSION_KEYS:
        st.session_state.pop(key, None)


def _render_question() -> None:
    """Renders whatever the pending question needs, purely from `st.session_state.choices`:
    None is free text (FT), a list without "something else" is a closed set of buttons only
    (MC/BAND), a list with it is that same button row plus an always-visible text box (HYB). No
    other per-question knowledge is needed here; engine/protocol.py's Question.choices already
    encodes the classification docs/interview-ux.md specifies, and bridge.py hands it straight
    through.
    """
    choices = st.session_state.choices

    if not choices:
        with st.form("reply_form", clear_on_submit=True):
            reply = st.text_input("Your answer", label_visibility="collapsed",
                                   placeholder="Type your answer and press Enter")
            submitted = st.form_submit_button("Send")
        if submitted:
            _pump(reply)
            _rerun()
        return

    has_escape_hatch = "something else" in choices
    fixed_choices = [choice for choice in choices if choice != "something else"]

    for choice in fixed_choices:
        if st.button(choice, key=f"choice_{choice}", use_container_width=True):
            _pump(choice)
            _rerun()

    if has_escape_hatch:
        with st.form("something_else_form", clear_on_submit=True):
            reply = st.text_input("Something else", label_visibility="visible",
                                   placeholder="Type your own answer")
            submitted = st.form_submit_button("Send")
        if submitted and reply.strip():
            _pump(reply)
            _rerun()


st.set_page_config(page_title="Requirements Accelerator", page_icon="\U0001F4CB")
st.title("Requirements Accelerator")

if "status" not in st.session_state:
    st.session_state.status = "idle"

if st.session_state.status == "idle":
    st.write(
        "Answer a short interview about what you need. It ends with a plain-language business "
        "ask and a technical spec ready for engineering."
    )
    st.caption(_reasoner_requirement_caption())
    if st.button("Start interview", type="primary"):
        _start_interview()
        _rerun()

elif st.session_state.status in ("running", "waiting"):
    st.text(st.session_state.transcript)
    _render_question()

elif st.session_state.status == "done":
    st.text(st.session_state.transcript)
    st.divider()
    ledger = st.session_state.ledger
    st.subheader("Business ask")
    st.text(render_business_ask(ledger))
    st.subheader("Technical spec")
    st.text(render_technical_spec(ledger))
    delivered = st.session_state.get("delivered")
    if delivered:
        st.caption(
            f"Business ask saved to {delivered['business_ask']}  \n"
            f"Technical spec saved to {delivered['technical_spec']}"
        )
    if st.button("Start a new interview"):
        _reset()
        _rerun()

elif st.session_state.status == "error":
    st.text(st.session_state.transcript)
    st.error(f"The interview hit an error and stopped: {st.session_state.error}")
    if st.button("Start over"):
        _reset()
        _rerun()
