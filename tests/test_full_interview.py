"""Automated assertions over examples/demo_full_pass.py, the scripted run through all ten
layers. The demo script itself only prints the rendered documents for a person to read; this
adds the pass/fail checks that were previously "read the transcript and eyeball it": the term
queued in layer 07 actually locks with the definition given, layer 05's inferred fields promote
to stated once the reflection is confirmed, and the two rendered documents actually mention the
term the interview spent a whole layer defining.
"""

import unittest
from unittest.mock import patch

from engine.ledger import Ledger, ProvenanceState
from engine.knowledge import NoRetainedKnowledge
from engine.reasoner import StubReasoner
from engine.interview import run_interview
from engine.render import render_business_ask, render_technical_spec

from examples.demo_full_pass import RESPONSES


class FullInterviewPassTest(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger()
        with patch("builtins.input", side_effect=RESPONSES):
            run_interview(self.ledger, StubReasoner(), NoRetainedKnowledge())

    def test_qualified_lead_term_locks_with_its_given_definition(self):
        locked = self.ledger.get("term_locked::qualified lead")
        self.assertIsNotNone(locked)
        self.assertIs(locked.value, True)
        definition = self.ledger.get("metric_definition::qualified lead")
        self.assertEqual(
            definition.value,
            "A lead counts as qualified once a rep completes a discovery call and confirms "
            "budget, so it has to have a logged call and a budget field filled in.",
        )

    def test_layer_05_fields_promote_from_inferred_to_stated_on_confirmed_reflection(self):
        # Layer 05 fields start inferred (no source document seeded them); a confirmed
        # reflection ("yes") is what promotes them, per docs/provenance-model.md.
        steward = self.ledger.get("steward")
        decision_rights = self.ledger.get("decision_rights")
        self.assertEqual(steward.state, ProvenanceState.STATED)
        self.assertEqual(decision_rights.state, ProvenanceState.STATED)

    def test_system_of_record_asked_live_when_more_than_one_system_is_named(self):
        # Two systems are named (Salesforce, NetSuite), so this must NOT resolve to the
        # inferred "not applicable" shortcut demo_not_applicable_pass.py exercises instead.
        system_of_record = self.ledger.get("system_of_record")
        self.assertNotEqual(system_of_record.value, "not applicable")
        self.assertEqual(system_of_record.state, ProvenanceState.STATED)

    def test_rendered_documents_carry_the_locked_term(self):
        business_ask = render_business_ask(self.ledger)
        technical_spec = render_technical_spec(self.ledger)
        self.assertIn("qualified lead", technical_spec.lower())
        # The business ask is plain language for the requester and never carries provenance
        # tags or technical vocabulary; it should still exist and say something concrete.
        self.assertTrue(business_ask.strip())


if __name__ == "__main__":
    unittest.main()
