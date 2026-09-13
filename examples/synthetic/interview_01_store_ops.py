"""Synthetic interview 1 of 10: a Store Operations Manager at Alderglen Outfitters (fictional
retailer, see docs/synthetic-dataset.md), on stockouts of best-selling SKUs.

A clean pass: no redirect, both layer 02's drill-through and layer 04's system-of-record
questions are asked live (dimensions are named, more than one source system is named). Locks
the term "stockout", the first of three terms this dataset deliberately reuses across later
interviews (interview 5's Supply Chain Analyst agrees with this definition).

Part of the ten-interview synthetic dataset built to give e8 (overlap detection, dependency map)
real data to design against, since it was blocked on exactly that since e3. Run standalone below
against a throwaway database for a quick read of the transcript; examples/synthetic/run_all.py
runs all ten together against the shared fixture database that later interviews actually depend
on, and tests/test_synthetic_dataset.py is what actually proves the outcomes below.
"""

from unittest.mock import patch
from engine.ledger import Ledger
from engine.knowledge import NoRetainedKnowledge
from engine.reasoner import StubReasoner
from engine.interview import run_interview
from engine.render import render_business_ask, render_technical_spec

RESPONSES = [
    # --- layer 00 ---
    "Our best-selling packs and boots sell out at individual stores mid-week, but nobody notices "
    "until a customer walks out empty-handed, and by the time head office reacts the "
    "replenishment truck has already left without the extra units.",
    "n",  # generic check
    "n",  # layer 00 extra check: not a solution in disguise
    "Store leads check the shelf by eye, and if they remember, they email the DC to ask for a "
    "rush top-up, but there's no report that flags it before it happens.",
    "n",
    "weekly",
    "n",
    "Every store lead, and the regional merchandising team when a stockout shows up in weekly "
    "sales.",
    "n",
    "I'd action a rush replenishment before the shelf actually goes empty, not after.",
    "n",
    "I can see, every morning, which SKUs at which stores are about to run out.",
    "n",
    "",  # layer 00 reflection: no correction
    "",  # extract_terms after layer 00

    # --- layer 01 ---
    "which ones",
    "n",
    "on a schedule",
    "n",
    "Store leads and the regional merchandising team, and yes, same question for both.",
    "n",
    "yes",  # reflection confirm
    "",  # extract_terms

    # --- layer 02 ---
    "Number of SKUs at risk of a stockout in the next few days.",
    "n",
    "store, product",
    "n",
    "yes",  # drill_through_required, asked live: dimensions aren't "none"
    "n",
    "last year",
    "n",
    "yes",  # reflection confirm
    "stockout",  # extract_terms after layer 02: queues our one term

    # --- layer 03 ---
    "one SKU at one store on one day",
    "n",
    "no",
    "n",
    "no",
    "n",
    "yes",  # reflection confirm
    "",  # extract_terms

    # --- layer 04 ---
    "The point-of-sale system for what's sold, and the warehouse management system for what's "
    "actually left in the stockroom.",
    "n",
    "y",  # reasoner judge: yes, this names more than one system
    "The warehouse management system, since the POS only knows what's sold, not what's "
    "physically still on the shelf.",  # system_of_record, asked live
    "n",
    "The stockroom count updates overnight after the evening cycle count.",
    "n",
    "yes",  # restatement_handling
    "n",
    "Store leads correct a miscount the next morning if the overnight number looks wrong.",
    "yes",  # reflection confirm
    "",  # extract_terms

    # --- layer 05 ---
    "Regional merchandising and the replenishment planning team.",
    "n",
    "The regional merchandising lead, people ask her first.",
    "n",
    "Regional merchandising, they own the replenishment call.",
    "n",
    "Into the weekly replenishment planning meeting.",
    "n",
    "Replenishment planning stalls without it.",
    "n",
    "The regional merchandising lead.",
    "n",
    "yes",  # reflection confirm - promotes steward & decision_rights
    "",  # extract_terms

    # --- layer 06 ---
    "next morning",
    "n",
    "Monday morning",
    "n",
    "last two to three years",
    "n",
    "only how it looks now",
    "n",
    "yes",  # reflection confirm
    "",  # extract_terms

    # --- consolidate the term queue, once, before layer 07 opens ---
    "",  # keep "stockout" as-is

    # --- layer 07: "stockout" ---
    "A SKU counts as a stockout risk once the stockroom count drops below what we'd sell before "
    "the next scheduled delivery, not simply hitting zero.",
    "n",  # generic check
    "n",  # layer 07 extra check: not too vague, concrete enough
    "not a concern",  # competing_definition_check, no prior definition on file yet
    "none",
    "Some people just call it a 'stock risk' or a 'run-out'.",
    "yes",  # term reflection confirm - locks the definition

    # --- layer 08 ---
    "everyone sees all of it",
    "n",
    "no",
    "n",
    "Probably the DC replenishment planners directly, once this proves out.",
    "n",
    "yes",  # reflection confirm

    # --- layer 09 ---
    "thousands",
    "n",
    "no",
    "n",
    "yes",  # reflection confirm
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
