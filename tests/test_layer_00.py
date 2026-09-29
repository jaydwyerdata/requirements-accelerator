"""Automated assertions over examples/demo_clean_pass.py and examples/demo_redirect_pass.py.

Both scripts already exist as readable, narrated walkthroughs (run them directly with
`python examples/demo_clean_pass.py` to see the flow and the rendered business ask); neither had
an automated pass/fail before this, just printed output for a person to read. These tests reuse
each script's exact RESPONSES list, no scripted dialogue duplicated, and add the assertions that
were previously "read the transcript and eyeball it": that a clean answer is never flagged or
reworded, and that a redirected one is captured as it stood after the requester's second attempt,
not the solution-in-disguise reply that triggered the redirect in the first place.
"""

import unittest
from unittest.mock import patch

from engine.ledger import Ledger, ProvenanceState
from engine.reasoner import StubReasoner
from engine.interview import run_layer_00

from examples.demo_clean_pass import RESPONSES as CLEAN_RESPONSES
from examples.demo_redirect_pass import RESPONSES as REDIRECT_RESPONSES


class CleanPassTest(unittest.TestCase):
    """demo_clean_pass.py: every layer 00 question is accepted on the first try."""

    def setUp(self):
        self.ledger = Ledger()
        with patch("builtins.input", side_effect=CLEAN_RESPONSES):
            run_layer_00(self.ledger, StubReasoner())

    def test_problem_statement_recorded_as_given_and_not_flagged(self):
        record = self.ledger.get("problem_statement")
        self.assertIsNotNone(record)
        self.assertEqual(
            record.value,
            "Our finance team spends two days every month manually reconciling renewals "
            "because nobody trusts the numbers in the dashboard.",
        )
        self.assertEqual(record.state, ProvenanceState.STATED)
        self.assertEqual(record.note, "", "a clean answer should never carry a redirect note")

    def test_reflection_with_no_correction_leaves_no_correction_record(self):
        # demo_clean_pass's reflection reply is "", i.e. nothing to correct.
        self.assertIsNone(self.ledger.get("layer_00_reflection_correction"))


class RedirectPassTest(unittest.TestCase):
    """demo_redirect_pass.py: the problem statement trips the solution-in-disguise check on
    attempt one and self-corrects on attempt two, within MAX_REDIRECT_ATTEMPTS."""

    def setUp(self):
        self.ledger = Ledger()
        with patch("builtins.input", side_effect=REDIRECT_RESPONSES):
            run_layer_00(self.ledger, StubReasoner())

    def test_problem_statement_holds_the_corrected_reply_not_the_original(self):
        # "We need a Power BI dashboard for renewals." is the solution-in-disguise reply that
        # triggered the redirect; it must not be what ends up on the ledger.
        record = self.ledger.get("problem_statement")
        self.assertIsNotNone(record)
        self.assertEqual(
            record.value,
            "Nobody trusts the renewals numbers because finance and sales calculate them "
            "differently and nobody's ever reconciled that.",
        )

    def test_problem_statement_not_flagged_once_the_redirect_lands(self):
        # Clearing both checks on the second attempt means this was resolved within the cap,
        # not merely recorded-with-a-flag after running out of attempts.
        record = self.ledger.get("problem_statement")
        self.assertEqual(record.note, "")

    def test_reflection_correction_is_captured_verbatim(self):
        correction = self.ledger.get("layer_00_reflection_correction")
        self.assertIsNotNone(correction)
        self.assertEqual(correction.value, "actually it's closer to twice a week, not just weekly")
        self.assertEqual(correction.state, ProvenanceState.STATED)


if __name__ == "__main__":
    unittest.main()
