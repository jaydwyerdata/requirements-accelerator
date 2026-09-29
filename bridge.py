"""The thread/queue bridge between engine/interview.py's blocking, input()-based question loop
and a UI that can't block waiting for one: today that's app.py's Streamlit rerun model, and per
CLAUDE.md's portability rule (local first, Streamlit in Snowflake later) this is written so it
doesn't know or care which one is asking.

Why this exists: run_interview() asks its questions by calling a blocking `ask(prompt)` function
and expects an answer back before it will print the next one, all inside one linear call, exactly
the shape a terminal script wants (cli.py just passes it `input`). A UI built around handling one
event at a time and returning, Streamlit's rerun-per-interaction model included, has no matching
call to make: there is no live call stack to resume between one interaction and the next.

The fix is to give run_interview() the blocking call it wants, on a thread of its own, and let the
UI thread talk to it through two queues instead of a return value:

- `input_queue`: the UI thread puts the requester's typed reply here; the engine thread's ask()
  blocks on it.
- `signal_queue`: the engine thread puts every piece of narration it prints here as it happens,
  plus one terminal signal, ("waiting", choices) once it's blocked on ask() again, ("done", None)
  once run_interview() returns, or ("error", exc) if it raises. The UI thread drains this once
  per interaction, blocking until it sees the terminal signal, so it only resumes once the engine
  actually has something new to show and never needs to poll.

`choices` on a "waiting" signal is the same list `engine/protocol.py`'s Question.choices carries
(or None for a genuinely open question), passed straight through from whichever call site
supplied it to `ask(prompt, choices=...)`. This is what lets a real UI render docs/interview-ux.md's
widget-per-question design (buttons for a closed set, free text otherwise) instead of one text
box for everything: the engine already knows, per question, whether its answer space is closed,
and this is the one channel that opinion travels through. The engine never sees or cares what the
UI does with it, the same as it never sees or cares that its narration ends up in a Streamlit
transcript instead of a terminal.

`Bridge` doubles as a stand-in for sys.stdout for the engine thread's run: everything
engine/interview.py prints (every question, choice list, reflection, and the two rendered
documents at the end) is narration meant for the person answering, not the process's own
terminal, so it goes through the same queue rather than the real stdout. This is a process-wide
sys.stdout swap for the lifetime of one interview thread, correct for one person running one
interview locally, which is this tool's whole v1 shape (CLAUDE.md: "local first, port later").
Serving more than one interview from the same process at once, which the eventual Streamlit in
Snowflake port could plausibly need, would need this scoped per-thread instead; noted here so
that's a decision for that port, not a silent gap.
"""

import queue
import sys
import threading


class Bridge:
    """One interview's channel between its engine thread and whatever UI thread is driving it."""

    def __init__(self):
        self.input_queue: "queue.Queue" = queue.Queue()
        self.signal_queue: "queue.Queue" = queue.Queue()

    # sys.stdout interface, for the duration of the engine thread's run -----
    def write(self, text: str) -> None:
        if text:
            self.signal_queue.put(("narration", text))

    def flush(self) -> None:
        pass

    # engine ask() interface -------------------------------------------------
    def ask(self, prompt: str = "", choices: list | None = None) -> str:
        if prompt:
            self.write(prompt)
        self.signal_queue.put(("waiting", choices))
        return self.input_queue.get()


def run_interview_worker(bridge: Bridge, run_interview, ledger, reasoner, knowledge) -> None:
    """Runs `run_interview(ledger, reasoner, knowledge, ask=bridge.ask)` on the calling thread
    with sys.stdout swapped to `bridge` for its duration, and reports how it ended on
    `bridge.signal_queue` as ("done", None) or ("error", exc). Meant to be the target of a
    background thread the UI thread starts and never joins; `run_interview` is passed in rather
    than imported here so this module stays free of any dependency on engine/interview.py's
    exact import path, matching the same seam discipline the rest of the engine follows.
    """
    old_stdout = sys.stdout
    sys.stdout = bridge
    try:
        run_interview(ledger, reasoner, knowledge, ask=bridge.ask)
        bridge.signal_queue.put(("done", None))
    except Exception as exc:  # noqa: BLE001 - reported to the caller, not swallowed
        bridge.signal_queue.put(("error", exc))
    finally:
        sys.stdout = old_stdout


def start_interview_thread(bridge: Bridge, run_interview, ledger, reasoner, knowledge) -> threading.Thread:
    """Starts run_interview_worker on a daemon thread and returns it. Daemon so an abandoned
    interview (the requester closes the tab mid-way) never blocks the process from exiting; the
    thread simply stops being read from, which is fine, since ClaudeCodeReasoner's own subprocess
    calls are each bounded by their own timeout rather than needing to be joined.
    """
    thread = threading.Thread(
        target=run_interview_worker, args=(bridge, run_interview, ledger, reasoner, knowledge),
        daemon=True,
    )
    thread.start()
    return thread
