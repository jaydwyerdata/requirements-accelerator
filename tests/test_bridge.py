"""Verifies bridge.py, the thread/queue handoff app.py's Streamlit UI depends on, against the
real (unthreaded-in-source) run_interview. This is the actual architectural risk in e7: a wrong
queue handoff means a hung or silently wrong interview, not something a rendered widget could
ever catch, so it gets its own test independent of whether Streamlit itself is installed or
running.

Reuses examples/demo_full_pass.py's exact 97-reply script, already exercised directly (without
the bridge) in test_full_interview.py, and drives it through bridge.py exactly as app.py's _pump
function does: start the interview thread, then alternately hand a reply to the input queue and
block on the signal queue for the next narration/waiting/done/error. Asserts the bridge-driven
run produces a business ask and technical spec byte-identical to a direct call with the same
script, not just that it "finishes".

Note on StubReasoner: its judge()/extract_terms()/reframe()/consolidate_terms() call the
`input()` builtin directly rather than the injected `ask`, which only ever mattered for a direct
call under unittest.mock.patch until this test came along. Run through the bridge on a real
background thread, an unpatched input() has no attached stdin and raises EOFError (hit while
building this). This test patches builtins.input to bridge.ask() for the duration of the
threaded run to close that gap; app.py never needs this, since it never uses StubReasoner (see
docs/architecture-decisions.md's e7 entry).
"""

import builtins
import unittest
from unittest.mock import patch

from engine.ledger import Ledger
from engine.knowledge import NoRetainedKnowledge
from engine.reasoner import StubReasoner
from engine.interview import run_interview
from engine.render import render_business_ask, render_technical_spec

from bridge import Bridge, start_interview_thread

from examples.demo_full_pass import RESPONSES


def _pump(bridge, reply=None, timeout=10):
    if reply is not None:
        bridge.input_queue.put(reply)
    narration = []
    while True:
        signal, payload = bridge.signal_queue.get(timeout=timeout)
        if signal == "narration":
            narration.append(payload)
            continue
        return signal, payload, "".join(narration)


class BridgeQueueHandoffTest(unittest.TestCase):
    def test_bridge_driven_run_matches_a_direct_run_byte_for_byte(self):
        ledger = Ledger()
        bridge = Bridge()

        old_input = builtins.input
        builtins.input = bridge.ask
        try:
            thread = start_interview_thread(
                bridge, run_interview, ledger, StubReasoner(), NoRetainedKnowledge(),
            )
            responses = iter(RESPONSES)
            signal, payload, _ = _pump(bridge)
            steps = 0
            while signal == "waiting":
                steps += 1
                signal, payload, _ = _pump(bridge, next(responses))
            thread.join(timeout=5)
        finally:
            builtins.input = old_input

        self.assertEqual(signal, "done", f"interview did not finish cleanly: {payload!r}")
        self.assertFalse(thread.is_alive(), "engine thread should exit once it signals done")
        self.assertEqual(
            list(responses), [], "bridge run consumed fewer replies than the direct run does"
        )
        self.assertEqual(steps, len(RESPONSES), "every scripted reply should be one round-trip")

        direct_ledger = Ledger()
        with patch("builtins.input", side_effect=RESPONSES):
            run_interview(direct_ledger, StubReasoner(), NoRetainedKnowledge())

        self.assertEqual(render_business_ask(ledger), render_business_ask(direct_ledger))
        self.assertEqual(render_technical_spec(ledger), render_technical_spec(direct_ledger))


if __name__ == "__main__":
    unittest.main()
