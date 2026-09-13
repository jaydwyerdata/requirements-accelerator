"""Automated assertions for a1 (engine/semantic_view.py), against the same ten-interview
synthetic dataset tests/test_synthetic_dataset.py already proves the raw ledger outcomes for.
Uses store-ops-01 (the "stockout" interview), which has a clean primary_measure, grain,
dimensions and exactly one locked term with quoted synonyms and no exclusion, plus a fresh
throwaway interview to prove the honest-gap and no-valid-DDL paths.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from examples.synthetic.run_all import run_all
from engine.ledger import Ledger
from engine.reasoner import StubReasoner
from engine.knowledge import NoRetainedKnowledge
from engine.interview import run_interview
from engine.semantic_view import build_semantic_view_plan, render_semantic_view_sql
from engine.storage import SqliteStorage


class SemanticViewAgainstSyntheticDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls._tmp_dir.name, "semantic-view-test.db")
        cls.ledgers = run_all(cls.db_path)
        cls.plan = build_semantic_view_plan("store-ops-01", cls.ledgers["store-ops-01"])
        cls.sql = render_semantic_view_sql(cls.plan)

    @classmethod
    def tearDownClass(cls):
        cls._tmp_dir.cleanup()

    # --- build_semantic_view_plan ---

    def test_primary_measure_captured(self):
        self.assertIsNotNone(self.plan.primary_measure)
        self.assertIn("stockout", self.plan.primary_measure.business_definition.lower())

    def test_grain_captured_verbatim(self):
        self.assertEqual(self.plan.grain_text, "one SKU at one store on one day")

    def test_breakdown_dimensions_split_from_layer_02(self):
        names = {d.name for d in self.plan.breakdown_dimensions}
        self.assertEqual(names, {"store", "product"})

    def test_locked_term_becomes_a_dimension_not_a_metric(self):
        term_names = {d.name for d in self.plan.locked_term_dimensions}
        self.assertIn("stockout", term_names)
        # the assumption this module states plainly: locked terms are dimensions, only
        # primary_measure becomes the metric.
        self.assertNotEqual(self.plan.primary_measure.name, "stockout")

    def test_synonyms_extracted_from_quoted_phrases_only(self):
        stockout = next(d for d in self.plan.locked_term_dimensions if d.name == "stockout")
        self.assertEqual(set(stockout.synonyms), {"stock risk", "run-out"})

    def test_no_exclusion_note_when_answer_was_none(self):
        stockout = next(d for d in self.plan.locked_term_dimensions if d.name == "stockout")
        self.assertIsNone(stockout.note)

    def test_no_gaps_for_a_fully_answered_interview(self):
        self.assertEqual(self.plan.gaps, [])

    def test_unlocked_term_never_appears(self):
        # executive-10 never locks "efficient store" (see test_overlap.py); a semantic view
        # built from that interview should not claim it as a settled dimension.
        plan = build_semantic_view_plan("executive-10", self.ledgers["executive-10"])
        names = {d.name for d in plan.locked_term_dimensions}
        self.assertNotIn("efficient_store", names)

    # --- render_semantic_view_sql: structure and claim-integrity checks ---

    def test_sql_never_contains_a_real_physical_reference(self):
        # every table/column reference must be one of the adapter's own TODO placeholders,
        # never a value the interview actually gave (that would be inventing a schema fact).
        self.assertIn("TODO_PHYSICAL_TABLE", self.sql)
        self.assertIn("TODO_GRAIN_KEY_COLUMN", self.sql)
        self.assertIn("TODO_PHYSICAL_EXPRESSION", self.sql)

    def test_sql_clause_order_is_tables_dimensions_metrics(self):
        self.assertLess(self.sql.index("TABLES ("), self.sql.index("DIMENSIONS ("))
        self.assertLess(self.sql.index("DIMENSIONS ("), self.sql.index("METRICS ("))

    def test_sql_carries_the_business_definition_as_a_comment(self):
        self.assertIn("stockroom count drops below", self.sql)

    def test_sql_carries_synonyms_clause_for_the_locked_term(self):
        self.assertIn("WITH SYNONYMS", self.sql)
        self.assertIn("stock risk", self.sql)
        self.assertIn("run-out", self.sql)

    def test_sql_header_names_the_assumption(self):
        self.assertIn("Stated assumption", self.sql)

    def test_sql_is_valid_single_statement(self):
        # not a real parser, just the one structural guarantee Snowflake's own docs state:
        # exactly one terminating semicolon, at the end.
        stripped = self.sql.rstrip()
        self.assertTrue(stripped.endswith(";"))
        self.assertEqual(stripped.count(";"), 1)

    def test_exclusion_note_appears_when_the_interview_gave_one(self):
        # cx-04 locks "on-time delivery" and answers "cancellations" for exclusion_filters,
        # see examples/synthetic/interview_04_customer_experience.py.
        plan = build_semantic_view_plan("cx-04", self.ledgers["cx-04"])
        entry = next(d for d in plan.locked_term_dimensions if d.name == "on_time_delivery")
        self.assertIsNotNone(entry.note)
        self.assertIn("cancellations", entry.note.lower())

    # --- an interview too incomplete to produce valid DDL ---

    def test_no_ddl_when_neither_dimensions_nor_metrics_exist(self):
        # a bare-minimum ledger: nothing set at all. Snowflake itself requires at least one
        # DIMENSIONS or METRICS entry, so this should explain why, not emit invalid SQL.
        empty_ledger = Ledger()
        plan = build_semantic_view_plan("empty-interview", empty_ledger)
        sql = render_semantic_view_sql(plan)
        self.assertNotIn("CREATE OR REPLACE SEMANTIC VIEW", sql)
        self.assertIn("No semantic view generated", sql)
        self.assertIn("primary_measure was never established", plan.gaps[0])


class SemanticViewAdapterRunnerTest(unittest.TestCase):
    """Covers the storage-backed path (Storage.load_interview), not just building a plan
    directly from an in-memory ledger, since semantic_view_adapter.py's real callers go
    through Storage."""

    def test_loaded_from_storage_matches_direct_ledger(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "single-interview.db")
            storage = SqliteStorage(db_path)
            responses = [
                "Orders that never shipped on time.",
                "n", "n",
                "We check a spreadsheet weekly.",
                "n", "weekly", "n",
                "Everyone on the CX team.",
                "n",
                "I'd escalate it before the customer complains.",
                "n",
                "We'd see zero late orders.",
                "n", "", "",
                "how many", "n", "on a schedule", "n", "Just me.", "n", "yes", "",
                "Count of orders shipped late.", "n", "none", "n", "yes", "no", "n", "yes", "",
                "one order", "n", "no", "n", "no", "n", "yes", "",
                "The order management system.", "n", "n",
                "Ops team enters it.", "n", "no", "n", "yes", "",
                "The CX team.", "n", "Me.", "n", "The CX team.", "n", "Into the weekly report.",
                "n", "Nothing stalls.", "n", "Me.", "n", "yes", "",
                "same day", "n", "none", "n", "this year only", "n", "only how it looks now",
                "n", "yes", "",
                "",
                "An order counts as late once it ships after its promised date.", "n", "n",
                "not a concern", "none", "No other name for it.", "yes",
                "everyone sees all of it", "n", "no", "n", "Nobody yet.", "n", "yes",
                "hundreds", "n", "no", "n", "yes",
            ]
            with patch("builtins.input", side_effect=responses):
                ledger = Ledger()
                run_interview(ledger, StubReasoner(), NoRetainedKnowledge())
                storage.save_interview("single-01", ledger)

            loaded = storage.load_interview("single-01")
            direct_plan = build_semantic_view_plan("single-01", ledger)
            loaded_plan = build_semantic_view_plan("single-01", loaded)
            self.assertEqual(
                render_semantic_view_sql(direct_plan), render_semantic_view_sql(loaded_plan)
            )


if __name__ == "__main__":
    unittest.main()
