"""Verifies the plumbing app.py's widget layer depends on: that every "waiting" signal
bridge.py emits carries the real Question.choices for whatever is actually being asked (None
for free text, the exact list from engine/protocol.py otherwise), not a hallucinated one and not
silently dropped. This is the actual risk in the widget layer, a real UI can be wired to any
signal; a wrong or missing choices value there is what would make it render the wrong widget.

Runs demo_full_pass.py's script through bridge.py exactly as tests/test_bridge.py does, but
records the choices payload from every "waiting" signal instead of just consuming it, then
checks it against engine/protocol.py directly rather than a hand-typed expectation, so a future
edit to a question's choice list can't silently desync this test from what the engine actually
asks.
"""

import builtins
import unittest

from engine.ledger import Ledger
from engine.knowledge import NoRetainedKnowledge
from engine.reasoner import StubReasoner
from engine.interview import run_interview
from engine.protocol import (
    LAYER_00_QUESTIONS, LAYER_01_QUESTIONS, LAYER_02_QUESTIONS, LAYER_03_QUESTIONS,
    LAYER_04_QUESTIONS, LAYER_05_QUESTIONS, LAYER_06_QUESTIONS, LAYER_07_QUESTIONS,
    LAYER_08_QUESTIONS, LAYER_09_QUESTIONS,
    COMPETING_DEFINITION_CHOICES_WITH_PRIOR, COMPETING_DEFINITION_CHOICES_NO_PRIOR,
)

from bridge import Bridge, start_interview_thread

from examples.demo_full_pass import RESPONSES

ALL_LAYERS = (
    LAYER_00_QUESTIONS + LAYER_01_QUESTIONS + LAYER_02_QUESTIONS + LAYER_03_QUESTIONS
    + LAYER_04_QUESTIONS + LAYER_05_QUESTIONS + LAYER_06_QUESTIONS + LAYER_07_QUESTIONS
    + LAYER_08_QUESTIONS + LAYER_09_QUESTIONS
)


def _choices_for(field_id: str):
    return next(q.choices for q in ALL_LAYERS if q.field_id == field_id)


def _next_signal(bridge, timeout=10):
    """Drains narration silently and returns the next waiting/done/error signal."""
    while True:
        signal, payload = bridge.signal_queue.get(timeout=timeout)
        if signal != "narration":
            return signal, payload


class WidgetChoicesPlumbingTest(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger()
        bridge = Bridge()
        self.waiting_choices = []

        old_input = builtins.input
        builtins.input = bridge.ask
        try:
            thread = start_interview_thread(
                bridge, run_interview, self.ledger, StubReasoner(), NoRetainedKnowledge(),
            )
            responses = iter(RESPONSES)
            signal, payload = _next_signal(bridge)
            while signal == "waiting":
                self.waiting_choices.append(payload)
                bridge.input_queue.put(next(responses))
                signal, payload = _next_signal(bridge)
            thread.join(timeout=5)
        finally:
            builtins.input = old_input

        self.assertEqual(signal, "done", f"interview did not finish cleanly: {payload!r}")

    def test_a_free_text_question_reports_no_choices(self):
        # problem_statement is always the very first question asked, and it's free text.
        self.assertIsNone(self.waiting_choices[0])

    def test_a_multi_choice_question_reports_its_real_choices(self):
        frequency_choices = _choices_for("frequency")
        self.assertIn(frequency_choices, self.waiting_choices)

    def test_a_banded_question_reports_its_real_choices_with_no_escape_hatch(self):
        volume_choices = _choices_for("volume")
        self.assertIn(volume_choices, self.waiting_choices)
        self.assertNotIn("something else", volume_choices)

    def test_a_hybrid_question_reports_its_real_choices_with_an_escape_hatch(self):
        grain_choices = _choices_for("grain")
        self.assertIn(grain_choices, self.waiting_choices)
        self.assertIn("something else", grain_choices)

    def test_drill_through_and_system_of_record_get_their_choices_when_asked_live(self):
        # demo_full_pass.py names dimensions and more than one source system, so neither
        # resolves to the inferred "not applicable" shortcut; drill_through_required has a real
        # choices list, system_of_record (asked live here) has none defined at all in
        # engine/protocol.py, a known gap noted in app.py's own docstring, not invented here.
        self.assertIn(_choices_for("drill_through_required"), self.waiting_choices)

    def test_competing_definition_check_reports_the_no_prior_choices(self):
        # This scenario runs against NoRetainedKnowledge, so every term hits the "no prior
        # definition on file" branch, worth flagging / not a concern / not sure, never the
        # matches / doesn't match / not sure branch (tests/test_retained_knowledge.py covers
        # that one instead, where a prior definition genuinely exists).
        self.assertIn(COMPETING_DEFINITION_CHOICES_NO_PRIOR, self.waiting_choices)
        self.assertNotIn(COMPETING_DEFINITION_CHOICES_WITH_PRIOR, self.waiting_choices)

    def test_every_reported_choices_list_is_a_real_one_from_the_protocol_not_invented(self):
        # competing_definition_check's two choice lists live as their own constants in
        # engine/protocol.py, not on a Question object (see that module's comment on why), so
        # they're added to the known set explicitly rather than picked up via ALL_LAYERS.
        known_lists = {tuple(q.choices) for q in ALL_LAYERS if q.choices}
        known_lists.add(tuple(COMPETING_DEFINITION_CHOICES_WITH_PRIOR))
        known_lists.add(tuple(COMPETING_DEFINITION_CHOICES_NO_PRIOR))
        for choices in self.waiting_choices:
            if choices is not None:
                self.assertIn(tuple(choices), known_lists)

    def test_every_question_with_choices_that_gets_asked_reports_them(self):
        # Independently counted from engine/protocol.py and this scenario's own known branches:
        # every MC/HYB/BAND question in layers 00-09 is asked live here (dimensions and
        # source_systems both name more than one thing, so neither "not applicable" shortcut is
        # taken), except system_of_record (asked live but has no choices list at all). Every
        # term queued also now gets a real competing_definition_check choices list (closed the
        # gap noted in app.py's docstring): demo_full_pass.py queues exactly one term ("at risk
        # customer"), so that's one more choice-bearing question than before.
        non_none = [c for c in self.waiting_choices if c is not None]
        self.assertEqual(len(non_none), 20)


if __name__ == "__main__":
    unittest.main()
