"""Automated assertions over the ten-interview synthetic dataset (examples/synthetic/, see
docs/synthetic-dataset.md), run once for the whole test class since running all ten is what
actually exercises retained knowledge across them, not something to repeat per assertion.

This is the real proof behind examples/synthetic/run_all.py's printed narration: every claim
that document and docs/synthetic-dataset.md make about term conflicts, agreements and gaps is
checked here in pass/fail terms, not just eyeballed from a transcript. Uses a throwaway SQLite
file per test run (tempfile.TemporaryDirectory), same as test_retained_knowledge.py, so nothing
here touches examples/synthetic/alderglen.db or requirements_accelerator.db.
"""

import os
import tempfile
import unittest

from examples.synthetic.run_all import run_all


class SyntheticDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(cls._tmp_dir.name, "synthetic-test.db")
        cls.ledgers = run_all(db_path)

    @classmethod
    def tearDownClass(cls):
        cls._tmp_dir.cleanup()

    def _locked(self, interview_id: str, term: str) -> bool:
        record = self.ledgers[interview_id].get(f"term_locked::{term}")
        self.assertIsNotNone(record, f"expected a term_locked record for {term!r}")
        return bool(record.value)

    def _competing_check(self, interview_id: str, term: str) -> str:
        record = self.ledgers[interview_id].get(f"competing_definition_check::{term}")
        self.assertIsNotNone(record, f"expected a competing_definition_check for {term!r}")
        return record.value

    # --- every interview completes and produces the ledger a full run implies ---

    def test_all_ten_interviews_completed(self):
        self.assertEqual(len(self.ledgers), 10)
        for interview_id, ledger in self.ledgers.items():
            with self.subTest(interview_id=interview_id):
                self.assertIsNotNone(ledger.get("problem_statement"))
                self.assertIsNotNone(ledger.get("volume"))  # layer 09's last question

    # --- "stockout": Store Ops locks it, Supply Chain agrees ---

    def test_stockout_locks_in_store_ops(self):
        self.assertTrue(self._locked("store-ops-01", "stockout"))

    def test_stockout_matches_between_store_ops_and_supply_chain(self):
        self.assertTrue(self._locked("supply-chain-05", "stockout"))
        self.assertEqual(self._competing_check("supply-chain-05", "stockout"), "matches")

    # --- "active customer": Marketing locks it, Finance genuinely disagrees ---

    def test_active_customer_locks_in_marketing(self):
        self.assertTrue(self._locked("marketing-02", "active customer"))

    def test_active_customer_conflicts_between_marketing_and_finance(self):
        self.assertTrue(self._locked("finance-03", "active customer"))
        self.assertEqual(self._competing_check("finance-03", "active customer"), "doesn't match")

    # --- "on-time delivery": Customer Experience locks it, Supply Chain disagrees the other way ---

    def test_on_time_delivery_locks_in_customer_experience(self):
        self.assertTrue(self._locked("cx-04", "on-time delivery"))

    def test_on_time_delivery_conflicts_between_customer_experience_and_supply_chain(self):
        self.assertTrue(self._locked("supply-chain-05", "on-time delivery"))
        self.assertEqual(
            self._competing_check("supply-chain-05", "on-time delivery"), "doesn't match")

    # --- standalone terms, no reuse engineered ---

    def test_active_employee_locks_standalone_in_hr(self):
        self.assertTrue(self._locked("hr-06", "active employee"))

    def test_engaged_member_locks_standalone_in_loyalty(self):
        # Deliberately a different term string from "active customer", even though the two
        # describe an overlapping idea: retained knowledge matches on exact term text, so this
        # produces no conflict signal at all, not even a "doesn't match" - see
        # docs/synthetic-dataset.md's "What this surfaces for e8".
        self.assertTrue(self._locked("loyalty-07", "engaged member"))
        record = self.ledgers["marketing-02"].get("term_locked::engaged member")
        self.assertIsNone(record, "marketing's ledger should have no record of a term it was "
                           "never asked about, proving the two terms never crossed paths")

    def test_restricted_field_locks_standalone_in_governance(self):
        self.assertTrue(self._locked("governance-09", "restricted field"))

    # --- realistic non-outcomes: nothing queued, and something recorded but not locked ---

    def test_district_manager_queues_no_term(self):
        ledger = self.ledgers["district-08"]
        locked_fields = [
            record for record in ledger.all() if record.field_id.startswith("term_locked::")
        ]
        self.assertEqual(locked_fields, [])

    def test_efficient_store_recorded_but_not_locked(self):
        record = self.ledgers["executive-10"].get("term_locked::efficient store")
        self.assertIsNotNone(record)
        self.assertFalse(record.value)
        # It still has a concrete definition on file, from after the one reframe; only the
        # missing reflection confirmation is what kept it from locking.
        definition = self.ledgers["executive-10"].get("metric_definition::efficient store")
        self.assertIn("labour-to-sales ratio", definition.value)

    # --- the two redirects actually redirected, not just answered on the first try ---

    def test_finance_interview_was_redirected_before_the_real_problem(self):
        record = self.ledgers["finance-03"].get("problem_statement")
        self.assertIn("two days each close reconciling", record.value)
        self.assertNotIn("Power BI dashboard", record.value)

    def test_district_manager_interview_was_redirected_before_the_real_problem(self):
        record = self.ledgers["district-08"].get("problem_statement")
        self.assertIn("underperforming", record.value)
        self.assertNotIn("scorecard", record.value)


if __name__ == "__main__":
    unittest.main()
