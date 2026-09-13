"""Automated assertions for e8 Phase A (engine/overlap.py), against the same ten-interview
synthetic dataset tests/test_synthetic_dataset.py already proves the raw ledger outcomes for.
This suite proves the report built on top of those outcomes groups and renders them correctly,
not that the outcomes themselves are right, that's test_synthetic_dataset.py's job.

Same fixture pattern as test_synthetic_dataset.py: one throwaway SQLite file, one full run of
all ten interviews, shared across the class since running all ten is what actually produces
term reuse to report on.
"""

import os
import tempfile
import unittest

from examples.synthetic.run_all import run_all
from engine.overlap import (
    term_groups, dependency_view, render_report,
    locked_term_definitions, render_conceptual_overlaps,
)


class OverlapReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls._tmp_dir.name, "overlap-test.db")
        run_all(cls.db_path)
        cls.groups = {g.term: g for g in term_groups(cls.db_path)}
        cls.dependencies = {d.term: d for d in dependency_view(cls.db_path)}

    @classmethod
    def tearDownClass(cls):
        cls._tmp_dir.cleanup()

    # --- term_groups: the two-interview overlap cases ---

    def test_stockout_seen_by_both_interviews_in_order(self):
        occurrences = self.groups["stockout"].occurrences
        self.assertEqual([o.interview_id for o in occurrences], ["store-ops-01", "supply-chain-05"])
        self.assertTrue(all(o.locked for o in occurrences))
        self.assertEqual(occurrences[1].competing_check, "matches")

    def test_active_customer_conflict_recorded(self):
        occurrences = self.groups["active customer"].occurrences
        self.assertEqual([o.interview_id for o in occurrences], ["marketing-02", "finance-03"])
        self.assertEqual(occurrences[1].competing_check, "doesn't match")
        # the two definitions are genuinely different, not just flagged as different
        self.assertNotEqual(occurrences[0].definition, occurrences[1].definition)

    def test_on_time_delivery_conflict_recorded_other_direction(self):
        occurrences = self.groups["on-time delivery"].occurrences
        self.assertEqual([o.interview_id for o in occurrences], ["cx-04", "supply-chain-05"])
        self.assertEqual(occurrences[1].competing_check, "doesn't match")

    def test_seen_by_multiple_interviews_flag(self):
        self.assertTrue(self.groups["stockout"].seen_by_multiple_interviews)
        self.assertFalse(self.groups["active employee"].seen_by_multiple_interviews)

    # --- term_groups: single-occurrence terms still show up, locked or not ---

    def test_single_occurrence_terms_present(self):
        for term in ("active employee", "engaged member", "restricted field"):
            with self.subTest(term=term):
                self.assertEqual(len(self.groups[term].occurrences), 1)
                self.assertTrue(self.groups[term].occurrences[0].locked)

    def test_unlocked_term_still_appears_with_locked_false(self):
        occurrence = self.groups["efficient store"].occurrences[0]
        self.assertEqual(occurrence.interview_id, "executive-10")
        self.assertFalse(occurrence.locked)

    # --- e11's headline finding: overlap detection cannot see this pair at all, by design ---

    def test_active_customer_and_engaged_member_are_unrelated_groups(self):
        # Confirms the known gap stays a gap: no shared key, no cross-reference, nothing
        # here claims these two terms are connected. Phase B is where that gets solved.
        self.assertIn("active customer", self.groups)
        self.assertIn("engaged member", self.groups)
        self.assertIsNot(self.groups["active customer"], self.groups["engaged member"])

    # --- dependency_view: locked terms only, verbatim, not resolved across interviews ---

    def test_dependency_view_excludes_unlocked_terms(self):
        self.assertNotIn("efficient store", self.dependencies)

    def test_dependency_view_includes_every_locking_interview(self):
        snapshots = self.dependencies["stockout"].snapshots
        self.assertEqual([s.interview_id for s in snapshots], ["store-ops-01", "supply-chain-05"])

    def test_dependency_snapshot_carries_stakeholder_text_verbatim(self):
        snapshot = self.dependencies["stockout"].snapshots[0]
        self.assertIn("regional merchandising", snapshot.values["steward"].lower())
        self.assertEqual(
            snapshot.values["downstream_dependencies"],
            "Regional merchandising and the replenishment planning team.",
        )

    def test_dependency_view_does_not_merge_differently_worded_teams(self):
        # "regional merchandising" (stockout) and whatever finance-03 called its own approver
        # are never compared or merged here, that resolution is explicitly out of scope.
        stockout_steward = self.dependencies["stockout"].snapshots[0].values["steward"]
        active_customer_steward = self.dependencies["active customer"].snapshots[0].values["steward"]
        self.assertNotEqual(stockout_steward, active_customer_steward)

    # --- render_report: smoke-test the human-readable rendering doesn't blow up or drop data ---

    def test_render_report_includes_every_term(self):
        report = render_report(list(self.groups.values()), list(self.dependencies.values()))
        for term in self.groups:
            self.assertIn(term, report)

    def test_render_report_shows_competing_check_values(self):
        report = render_report(list(self.groups.values()), list(self.dependencies.values()))
        self.assertIn("matches", report)
        self.assertIn("doesn't match", report)

    # --- locked_term_definitions: Phase B's input, recency convention ---

    def test_locked_term_definitions_uses_most_recent_locked_definition(self):
        definitions = locked_term_definitions(list(self.groups.values()))
        # supply-chain-05 locked "stockout" after store-ops-01 did, and should win.
        self.assertEqual(
            definitions["stockout"],
            self.groups["stockout"].occurrences[-1].definition,
        )

    def test_locked_term_definitions_excludes_unlocked_terms(self):
        definitions = locked_term_definitions(list(self.groups.values()))
        self.assertNotIn("efficient store", definitions)

    def test_locked_term_definitions_covers_every_locked_term(self):
        definitions = locked_term_definitions(list(self.groups.values()))
        for term, group in self.groups.items():
            if any(o.locked for o in group.occurrences):
                self.assertIn(term, definitions)

    # --- render_conceptual_overlaps: Phase B's output framing ---

    def test_render_conceptual_overlaps_labels_output_as_unconfirmed(self):
        report = render_conceptual_overlaps([["active customer", "engaged member"]])
        self.assertIn("unconfirmed", report.lower())
        self.assertIn("active customer", report)
        self.assertIn("engaged member", report)

    def test_render_conceptual_overlaps_handles_no_groups(self):
        report = render_conceptual_overlaps([])
        self.assertIn("Nothing flagged", report)


if __name__ == "__main__":
    unittest.main()
