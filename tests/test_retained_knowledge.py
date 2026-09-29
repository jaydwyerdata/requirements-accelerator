"""Automated form of the assertions examples/demo_retained_knowledge_pass.py already makes
inline. Moved here for the same reason as test_not_applicable.py: the demo script stays a
readable walkthrough of e3 (SQLite storage and retained knowledge), this is what a test runner
actually executes.

Uses a throwaway SQLite file per test (tempfile.TemporaryDirectory), same as the demo script, so
nothing here touches requirements_accelerator.db.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from engine.ledger import Ledger
from engine.reasoner import StubReasoner
from engine.knowledge import NoRetainedKnowledge, SqliteRetainedKnowledge
from engine.storage import SqliteStorage
from engine.interview import run_layer_07

from examples.demo_retained_knowledge_pass import (
    RESPONSES,
    SECOND_INTERVIEW_RESPONSES,
)


class RetainedKnowledgeTest(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.db_path = os.path.join(self._tmp_dir.name, "test.db")

        with patch("builtins.input", side_effect=RESPONSES):
            self.ledger = Ledger()
            run_layer_07(
                self.ledger, StubReasoner(), NoRetainedKnowledge(),
                ["at risk customer", "healthy account"],
            )

        SqliteStorage(self.db_path).save_interview("interview-a", self.ledger)
        self.retained = SqliteRetainedKnowledge(self.db_path)

    def test_locked_term_comes_back_as_retained_knowledge(self):
        definition = self.retained.definition_for("at risk customer")
        self.assertEqual(
            definition,
            "A customer counts as at risk once they've had two support escalations in 30 "
            "days with no resolution.",
        )

    def test_unlocked_term_never_comes_back_as_retained_knowledge(self):
        # "healthy account" gets a concrete definition but the reflection gets no reaction,
        # so it must not count, per docs/interview-branching.md's three lock conditions.
        self.assertIsNone(self.retained.definition_for("healthy account"))

    def test_second_interview_sees_the_retained_definition_via_the_live_question(self):
        with patch("builtins.input", side_effect=SECOND_INTERVIEW_RESPONSES):
            ledger_b = Ledger()
            run_layer_07(ledger_b, StubReasoner(), self.retained, ["at risk customer"])

        competing_check = ledger_b.get("competing_definition_check::at risk customer")
        self.assertIsNotNone(competing_check)
        self.assertEqual(competing_check.value, "yes")


if __name__ == "__main__":
    unittest.main()
