"""Synthetic interview 3 of 10: an FP&A Analyst at Alderglen Outfitters, on reconciling a
board-reported customer count against marketing's own number.

Opens with a proposed solution ("a Power BI dashboard that recalculates this automatically"),
so layer 00's gate flags it and redirects before the real problem comes out, the first of two
scripted redirects in this set (interview 8's District Manager is the second). Reuses the term
"active customer" with a genuinely different, subscription-based definition, so when this
interview is run against the shared fixture database after interview 2 (see run_all.py), the
retained-knowledge check comes back "doesn't match": a real governance conflict, not a bug.

Part of the ten-interview synthetic dataset, see docs/synthetic-dataset.md. Run standalone below
against a throwaway, empty database, so the competing-definition question here shows the
no-prior-definition phrasing rather than the retained-knowledge one; run_all.py is what actually
exercises the conflict against interview 2's locked definition.
"""

from unittest.mock import patch
from engine.ledger import Ledger
from engine.knowledge import NoRetainedKnowledge
from engine.reasoner import StubReasoner
from engine.interview import run_interview
from engine.render import render_business_ask, render_technical_spec

RESPONSES = [
    # --- layer 00: gated question, redirected once ---
    "I need a Power BI dashboard that recalculates our active customer count automatically "
    "every month so I stop chasing marketing for numbers.",
    "n",  # generic check: a clear statement
    "y",  # layer 00 extra check: yes, this reads as a solution
    "Before we get into dashboards: what's actually going wrong today when you need the active "
    "customer count?",  # the reframed question (StubReasoner's own rephrasing)
    "The number I report to the board every month never matches what marketing says, and I "
    "spend two days each close reconciling the two before anyone will sign off on it.",
    "n",  # generic check on the second attempt
    "n",  # layer 00 extra check: not a solution this time
    "I pull our subscription and store-credit numbers from finance systems, marketing sends me "
    "their list separately, and I manually reconcile the two in a spreadsheet before close.",
    "n",
    "monthly",
    "n",
    "Me, the finance director who signs off the board pack, and marketing when the numbers "
    "don't match.",
    "n",
    "I'd close the books without a two-day reconciliation fight every month.",
    "n",
    "Finance and marketing report the same number without me manually reconciling it first.",
    "n",
    "",
    "",

    # --- layer 01 ---
    "how many",
    "n",
    "on a schedule",
    "n",
    "The finance director, and yes, same number for the board pack.",
    "n",
    "yes",
    "",

    # --- layer 02 ---
    "Count of active customers for the board pack.",
    "n",
    "time",
    "n",
    "no",  # drill_through_required, asked live
    "n",
    "a target",
    "n",
    "yes",
    "active customer",

    # --- layer 03 ---
    "one customer",
    "n",
    "no",
    "n",
    "not sure",
    "n",
    "yes",
    "",

    # --- layer 04 ---
    "The billing system for subscriptions, and the store-credit ledger in the ERP.",
    "n",
    "y",  # reasoner judge: yes, more than one system
    "The ERP's store-credit ledger, since that's what finance ultimately signs off against.",
    "n",
    "Subscription status updates in real time, store credit balances post overnight.",
    "n",
    "yes",  # restatement_handling
    "n",
    "Finance corrects a misposted credit during month-end close.",
    "yes",
    "",

    # --- layer 05 ---
    "The board pack, and the FP&A forecast model.",
    "n",
    "Me, I'm the one who reconciles it every month.",
    "n",
    "The finance director, if marketing and finance can't agree.",
    "n",
    "Into the board pack and the quarterly forecast.",
    "n",
    "The board pack can't close without it.",
    "n",
    "The finance director.",
    "n",
    "yes",
    "",

    # --- layer 06 ---
    "next morning",
    "n",
    "month end",
    "n",
    "five years or more",
    "n",
    "what it looked like back then",
    "n",
    "yes",
    "",

    # --- consolidate ---
    "",

    # --- layer 07: "active customer" (a real conflict against interview 2, via run_all.py) ---
    "A customer is active if they hold an open subscription or a positive store-credit balance "
    "right now, regardless of when they last actually bought something.",
    "n",
    "n",
    "doesn't match",  # against interview 2's prior definition, when run via run_all.py
    "internal accounts",
    "Finance just calls this 'current active customer' internally.",
    "yes",

    # --- layer 08 ---
    "only their own part",
    "n",
    "yes",  # data_classification: financial account data
    "n",
    "Treasury, probably, once we tie this to cash flow forecasting.",
    "n",
    "yes",

    # --- layer 09 ---
    "hundreds",
    "n",
    "no",
    "n",
    "yes",
]

if __name__ == "__main__":
    with patch("builtins.input", side_effect=RESPONSES):
        ledger = Ledger()
        reasoner = StubReasoner()
        knowledge = NoRetainedKnowledge()
        run_interview(ledger, reasoner, knowledge)
        print()
        print("=" * 60)
        print()
        print(render_business_ask(ledger))
        print()
        print(render_technical_spec(ledger))
