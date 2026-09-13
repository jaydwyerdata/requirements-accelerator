"""Synthetic interview 4 of 10: a Customer Experience Lead at Alderglen Outfitters, on
inconsistent return reason codes.

A clean pass. Layer 03's fan_out_risk gets a genuine "yes" here (a single return can span
multiple order lines), a branch the other nine interviews in this set don't exercise. Locks the
term "on-time delivery" as a promised-date definition, the term interview 5's Supply Chain
Analyst later checks and genuinely disagrees with, using a ship-date definition instead.

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
    "Customers call in furious about a return, and half the time the actual issue is the order "
    "never showed up when we told them it would, but our reason codes don't separate 'late "
    "delivery' from an actual product problem, so we can't even see how often it's really "
    "happening.",
    "n",
    "n",
    "Agents pick whatever reason code feels closest from a long dropdown, so 'arrived late' and "
    "'changed my mind' and 'wrong item' all get logged inconsistently depending on who's typing.",
    "n",
    "daily",
    "n",
    "Every contact centre agent, and the supply chain team when they ask us why returns spiked.",
    "n",
    "I'd know within a week if a specific carrier lane started running late, instead of finding "
    "out from an angry customer.",
    "n",
    "I can see return volume specifically tagged as late delivery, separate from every other "
    "reason.",
    "n",
    "",
    "",

    # --- layer 01 ---
    "how many",
    "n",
    "on a schedule",
    "n",
    "Supply chain, and yes, they're asking essentially the same question from their side.",
    "n",
    "yes",
    "",

    # --- layer 02 ---
    "Count of returns tagged as caused by a late delivery.",
    "n",
    "time, product",
    "n",
    "yes",  # drill_through_required, asked live
    "n",
    "last year",
    "n",
    "yes",
    "on-time delivery",

    # --- layer 03 ---
    "one order",  # grain: one return, closest fixed choice is "one order"
    "n",
    "yes",  # fan_out_risk: a return can span multiple order lines
    "n",
    "not sure",
    "n",
    "yes",
    "",

    # --- layer 04 ---
    "The contact centre case system, and separately the order management system for the "
    "original promised date.",
    "n",
    "y",  # reasoner judge: yes, more than one system
    "The order management system, since that's what actually told the customer a date in the "
    "first place.",
    "n",
    "The agent logs the case the moment the customer calls.",
    "n",
    "no",  # restatement_handling
    "n",
    "yes",
    "",

    # --- layer 05 ---
    "Supply chain, and the carrier performance review.",
    "n",
    "Me, agents escalate reason-code disputes to me.",
    "n",
    "Supply chain and customer experience jointly, if it's ever disputed.",
    "n",
    "Into the monthly carrier performance review.",
    "n",
    "The carrier performance review has nothing to point to without it.",
    "n",
    "Me.",
    "n",
    "yes",
    "",

    # --- layer 06 ---
    "same day",
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

    # --- layer 07: "on-time delivery" ---
    "A delivery counts as on-time if it arrives by the date we promised the customer at "
    "checkout, not the date the carrier says they shipped it.",
    "n",
    "n",
    "worth flagging",  # no prior definition yet; CX suspects supply chain measures it differently
    "cancellations",
    "Agents just call it 'late delivery' when it fails, there's no separate name for the good "
    "case.",
    "yes",

    # --- layer 08 ---
    "everyone sees all of it",
    "n",
    "no",
    "n",
    "Carrier account managers, probably, once we can actually name the worst lanes.",
    "n",
    "yes",

    # --- layer 09 ---
    "thousands",
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
