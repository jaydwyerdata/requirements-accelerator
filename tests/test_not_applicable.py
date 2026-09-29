"""Automated form of the assertions examples/demo_not_applicable_pass.py already makes inline
under its `if __name__ == "__main__":` guard. Moved here rather than duplicated: the demo script
stays a readable, runnable walkthrough of the "not applicable" branches (layer 02's drill-through,
layer 04's system of record) and the silent-reflection path, while this is what actually runs
under a test discovery command rather than only when someone remembers to run the script by hand
and check it doesn't raise.
"""

import unittest
from unittest.mock import patch

from engine.ledger import Ledger, ProvenanceState
from engine.knowledge import NoRetainedKnowledge
from engine.reasoner import StubReasoner
from engine.interview import run_interview

from examples.demo_not_applicable_pass import RESPONSES


class NotApplicableBranchesTest(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger()
        with patch("builtins.input", side_effect=RESPONSES):
            run_interview(self.ledger, StubReasoner(), NoRetainedKnowledge())

    def test_drill_through_resolves_not_applicable_when_no_dimensions_named(self):
        drill = self.ledger.get("drill_through_required")
        self.assertIsNotNone(drill)
        self.assertEqual(drill.value, "not applicable")

    def test_system_of_record_resolves_not_applicable_when_only_one_system_named(self):
        system_of_record = self.ledger.get("system_of_record")
        self.assertIsNotNone(system_of_record)
        self.assertEqual(system_of_record.value, "not applicable")

    def test_steward_stays_inferred_when_reflection_gets_no_reaction(self):
        steward = self.ledger.get("steward")
        self.assertIsNotNone(steward)
        self.assertEqual(steward.state, ProvenanceState.INFERRED)


if __name__ == "__main__":
    unittest.main()
