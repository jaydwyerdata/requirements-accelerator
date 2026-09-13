"""Synthetic interview 2 of 10: a Digital Marketing Manager at Alderglen Outfitters, on
re-targeting lapsed customers for a win-back campaign.

A clean pass, and exercises layer 04's "not applicable" branch: only one source system is named
(the email marketing platform), so system_of_record resolves to inferred "not applicable" rather
than being asked. Locks the term "active customer" as a recency-based, any-channel definition,
the term interview 3's FP&A Analyst later checks and genuinely disagrees with.

Part of the ten-interview synthetic dataset, see docs/synthetic-dataset.md.
"""

from unittest.mock import patch
from engine.ledger import Ledger
from engine.knowledge import NoRetainedKnowledge
from engine.reasoner import StubReasoner
from engine.interview import run_interview
from engine.render import render_business_ask, render_technical_spec

RESPONSES = [
    # --- layer 00 ---
    "Every time we plan a win-back campaign, I end up asking someone in the data team to "
    "manually pull a customer list, and by the time I get it back the campaign window's half "
    "gone.",
    "n",
    "n",
    "I ask the data team for an export, they write a one-off query, I wait a few days, then I "
    "upload the list into the email platform by hand.",
    "n",
    "monthly",
    "n",
    "Me, and the two other campaign managers on my team who ask for the same kind of list.",
    "n",
    "I'd launch the win-back campaign the same day I decide to run it, instead of a week later.",
    "n",
    "I can pull the list myself, the same day, without waiting on anyone.",
    "n",
    "",
    "",

    # --- layer 01 ---
    "which ones",
    "n",
    "when something feels wrong",
    "n",
    "The other two campaign managers, and yes, they ask for the same kind of list.",
    "n",
    "yes",
    "",

    # --- layer 02 ---
    "Count of customers who qualify for a win-back campaign.",
    "n",
    "channel, time",
    "n",
    "not sure",  # drill_through_required, asked live
    "n",
    "none",
    "n",
    "yes",
    "active customer",  # extract_terms after layer 02

    # --- layer 03 ---
    "one customer",
    "n",
    "no",
    "n",
    "no",
    "n",
    "yes",
    "",

    # --- layer 04 ---
    "The email marketing platform, that's the only place I look.",
    "n",
    "n",  # reasoner judge: no, this only names one system - system_of_record -> not applicable
    "Whenever someone places an order online or in a store, it syncs into the platform "
    "overnight.",
    "n",
    "not sure",  # restatement_handling
    "n",
    "yes",
    "",

    # --- layer 05 ---
    "The other campaign managers, and finance when they reconcile marketing spend against reach.",
    "n",
    "Me, honestly, since I'm the one who built the list logic by hand so far.",
    "n",
    "Marketing ops, if anyone disagreed with who counts.",
    "n",
    "Straight into the email platform's audience list.",
    "n",
    "The campaign launch date slips if this is late.",
    "n",
    "Marketing ops.",
    "n",
    "yes",
    "",

    # --- layer 06 ---
    "same day",
    "n",
    "something else",
    "n",
    "last two to three years",
    "n",
    "only how it looks now",
    "n",
    "yes",
    "",

    # --- consolidate ---
    "",

    # --- layer 07: "active customer" ---
    "Someone counts as active if they've placed an order on any channel, online or in a store, "
    "in the last 90 days.",
    "n",
    "n",
    "not a concern",  # no prior definition yet, first time this term appears
    "internal accounts",
    "Some people on my team just say 'recent customer'.",
    "yes",

    # --- layer 08 ---
    "everyone sees all of it",
    "n",
    "yes",  # data_classification: contains email addresses
    "n",
    "Probably the loyalty team next, they've asked about something similar.",
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
