"""Synthetic interview 5 of 10: a Supply Chain Analyst at Alderglen Outfitters, on vendor lead
times creeping up.

Reuses two prior terms in one interview, run in this order once the term queue reaches layer 07:
"stockout" (agrees with interview 1's Store Operations definition, a "matches" result) and
"on-time delivery" (disagrees with interview 4's Customer Experience definition, using a
ship-date definition instead of a delivery-date one, a "doesn't match" result, in the opposite
direction from how "active customer" conflicted between interviews 2 and 3). Also exercises
layer 04's system-of-record question live (two systems named).

Part of the ten-interview synthetic dataset, see docs/synthetic-dataset.md. Run standalone below
against a throwaway, empty database, so both competing-definition questions show the
no-prior-definition phrasing; run_all.py is what actually exercises the match and the conflict
against interviews 1 and 4's locked definitions.
"""

from unittest.mock import patch
from engine.ledger import Ledger
from engine.knowledge import NoRetainedKnowledge
from engine.reasoner import StubReasoner
from engine.interview import run_interview
from engine.render import render_business_ask, render_technical_spec

RESPONSES = [
    # --- layer 00 ---
    "Vendor lead times have crept up over the last two quarters, but I only find out a vendor's "
    "slipping once we're already short on shelf, there's no early signal from the purchase "
    "order data itself.",
    "n",
    "n",
    "I manually compare promised PO dates against when stock actually lands in the DC, in a "
    "spreadsheet I rebuild every month.",
    "n",
    "monthly",
    "n",
    "Procurement, and store ops once it turns into an actual stockout.",
    "n",
    "I'd flag a slipping vendor before it turns into empty shelves, not after.",
    "n",
    "I can see vendor lead time trending against target, without rebuilding the spreadsheet.",
    "n",
    "",
    "stockout",  # extract_terms after layer 00: reused, mentioned describing the consequence

    # --- layer 01 ---
    "has something changed",
    "n",
    "on a schedule",
    "n",
    "Procurement leadership, and yes, same question.",
    "n",
    "yes",
    "",

    # --- layer 02 ---
    "Average vendor lead time against target, by vendor.",
    "n",
    "product, team",
    "n",
    "yes",  # drill_through_required, asked live
    "n",
    "a target",
    "n",
    "yes",
    "on-time delivery",  # extract_terms after layer 02: the second reused term

    # --- layer 03 ---
    "one order",
    "n",
    "no",
    "n",
    "no",
    "n",
    "yes",
    "",

    # --- layer 04 ---
    "The ERP for purchase orders, and the vendor portal for their own shipment confirmations.",
    "n",
    "y",  # reasoner judge: yes, more than one system
    "The ERP, since that's what we hold the vendor to contractually.",
    "n",
    "Procurement logs the PO the day it's placed, the vendor portal updates whenever the vendor "
    "bothers to log a shipment.",
    "n",
    "yes",  # restatement_handling
    "n",
    "Procurement corrects a PO date if the vendor renegotiates it mid-cycle.",
    "yes",
    "",

    # --- layer 05 ---
    "Store ops, once a slip turns into a stockout, and the merchandising team on stock planning.",
    "n",
    "Me, I already own the monthly spreadsheet version of this.",
    "n",
    "Procurement leadership, if a vendor disputes being flagged.",
    "n",
    "Into the quarterly vendor scorecard.",
    "n",
    "The vendor scorecard review has nothing current to work from.",
    "n",
    "Procurement leadership.",
    "n",
    "yes",
    "",

    # --- layer 06 ---
    "next morning",
    "n",
    "month end",
    "n",
    "last two to three years",
    "n",
    "what it looked like back then",
    "n",
    "yes",
    "",

    # --- consolidate: pending queue is ["stockout", "on-time delivery"] ---
    "",

    # --- layer 07: "stockout" (agrees with interview 1, via run_all.py) ---
    "A stockout, from our side, is when the DC itself runs out before the next inbound PO "
    "lands, which usually cascades into individual stores running out too.",
    "n",
    "n",
    "matches",  # against interview 1's prior definition, when run via run_all.py
    "none",
    "Same thing store ops calls a stock risk, just further upstream.",
    "yes",

    # --- layer 07: "on-time delivery" (conflicts with interview 4, via run_all.py) ---
    "On-time, for a vendor, means they shipped by the cutoff we agreed in the PO, regardless of "
    "when the carrier actually gets it to the DC afterwards, that's on the carrier, not the "
    "vendor.",
    "n",
    "n",
    "doesn't match",  # against interview 4's prior definition, when run via run_all.py
    "none",
    "Procurement just calls this 'vendor OTIF', on-time-in-full.",
    "yes",

    # --- layer 08 ---
    "everyone sees all of it",
    "n",
    "no",
    "n",
    "Category managers, probably, to negotiate with vendors directly.",
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
