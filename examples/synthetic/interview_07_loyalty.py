"""Synthetic interview 7 of 10: the Basecamp Rewards (Alderglen Outfitters' loyalty programme)
Manager, on declining member engagement.

A clean pass. Locks the term "engaged member", deliberately a different word from interview 2's
"active customer" even though the two describe an overlapping idea (a customer the business
still considers worth marketing to). Retained knowledge matches on exact term text, so this pair
produces no signal at all today, not even a "doesn't match": see docs/synthetic-dataset.md's
"What this surfaces for e8" section, this is the most useful finding in the whole dataset, and
it's this interview's whole reason for existing.

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
    "Basecamp Rewards signups keep climbing, but I can't tell how many members are actually "
    "still engaging with the program versus just sitting on a card they signed up for once and "
    "forgot about.",
    "n",
    "n",
    "I look at total membership count, which only ever goes up, and I don't have a separate "
    "view of who's actually still redeeming points or opening our emails.",
    "n",
    "monthly",
    "n",
    "Me, and marketing when they plan a loyalty-specific campaign.",
    "n",
    "I'd target a re-engagement push at exactly the members drifting away, instead of emailing "
    "everyone the same way.",
    "n",
    "I can see a count of members who are still genuinely engaging, separate from total "
    "signups.",
    "n",
    "",
    "",

    # --- layer 01 ---
    "how many",
    "n",
    "on a schedule",
    "n",
    "Marketing, and yes, they'd use the same number to plan campaigns.",
    "n",
    "yes",
    "",

    # --- layer 02 ---
    "Count of engaged Basecamp Rewards members.",
    "n",
    "time",
    "n",
    "not sure",  # drill_through_required, asked live
    "n",
    "last year",
    "n",
    "yes",
    "engaged member",

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
    "The loyalty platform, that tracks points, redemptions and email opens all in one place.",
    "n",
    "n",  # reasoner judge: no, only one system - system_of_record -> not applicable
    "Points and redemptions post in real time, email engagement syncs in overnight.",
    "n",
    "no",  # restatement_handling
    "n",
    "yes",
    "",

    # --- layer 05 ---
    "Marketing, for campaign targeting.",
    "n",
    "Me.",
    "n",
    "Me, in practice, nobody else has looked at this closely.",
    "n",
    "Into the quarterly loyalty program review.",
    "n",
    "The quarterly loyalty review has no real number to open with.",
    "n",
    "Me.",
    "n",
    "yes",
    "",

    # --- layer 06 ---
    "next morning",
    "n",
    "none",
    "n",
    "last two to three years",
    "n",
    "only how it looks now",
    "n",
    "yes",
    "",

    # --- consolidate ---
    "",

    # --- layer 07: "engaged member" ---
    "A member counts as engaged if they've redeemed points or opened a program email in the "
    "last 60 days, not just if their card is technically still active.",
    "n",
    "n",
    "worth flagging",  # no prior definition on file for this exact term
    "none",
    "Some people on the team just say 'active member', which honestly probably needs sorting "
    "out against whatever marketing means by 'active customer'.",
    "yes",

    # --- layer 08 ---
    "everyone sees all of it",
    "n",
    "yes",  # contact and purchase-adjacent data
    "n",
    "Marketing, directly, once the definitions get reconciled.",
    "n",
    "yes",

    # --- layer 09 ---
    "hundreds",
    "n",
    "yes",
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
