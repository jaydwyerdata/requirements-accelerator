"""Synthetic interview 6 of 10: a People Analytics Partner at Alderglen Outfitters, on
understaffed shifts during peak season.

A clean pass, standalone: locks the term "active employee" with no reuse elsewhere in this
dataset. Exercises layer 08's sensitive-data branch directly (the requester names names and
pay-adjacent scheduling data as personal), paired with row-level security scoped to each store
lead's own store.

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
    "During peak season, some stores are visibly understaffed on their busiest days, but I "
    "can't tell if that's a scheduling problem or an actual headcount problem until I've "
    "already dug through timesheets by hand.",
    "n",
    "n",
    "I pull scheduled hours from the workforce system and actual sales from store reporting "
    "separately, then line them up myself in a spreadsheet store by store.",
    "n",
    "monthly",
    "n",
    "Store leads during peak planning, and regional ops when a store underperforms.",
    "n",
    "I'd flag understaffed stores before peak season starts, while there's still time to hire "
    "or reschedule.",
    "n",
    "I can see labour hours against sales, by store, without manually joining two spreadsheets.",
    "n",
    "",
    "",

    # --- layer 01 ---
    "how much",
    "n",
    "on a schedule",
    "n",
    "Regional ops, and yes, they ask essentially the same thing at a higher level.",
    "n",
    "yes",
    "",

    # --- layer 02 ---
    "Labour hours scheduled against sales volume, by store.",
    "n",
    "store, time",
    "n",
    "yes",  # drill_through_required, asked live
    "n",
    "another team",
    "n",
    "yes",
    "active employee",

    # --- layer 03 ---
    "one day",
    "n",
    "no",
    "n",
    "no",
    "n",
    "yes",
    "",

    # --- layer 04 ---
    "The workforce scheduling system, and the store sales reporting system.",
    "n",
    "y",  # reasoner judge: yes, more than one system
    "The workforce scheduling system, for hours; sales just comes along for the ratio.",
    "n",
    "Store leads build the schedule about two weeks out, and it can still change up to the day "
    "itself.",
    "n",
    "yes",  # restatement_handling
    "n",
    "Store leads correct the schedule after the fact if someone called in sick and got swapped.",
    "yes",
    "",

    # --- layer 05 ---
    "Regional ops, and store leads for their own peak planning.",
    "n",
    "Regional ops, they get asked first when a store's numbers look off.",
    "n",
    "Regional ops.",
    "n",
    "Into peak-season headcount planning.",
    "n",
    "Headcount planning for peak has nothing current to work from.",
    "n",
    "Regional ops.",
    "n",
    "yes",
    "",

    # --- layer 06 ---
    "next morning",
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

    # --- layer 07: "active employee" ---
    "An employee counts as active on a given day if they're currently employed, not on leave, "
    "and have at least one scheduled shift that day.",
    "n",
    "n",
    "not a concern",
    "none",
    "Scheduling just calls this 'rostered staff'.",
    "yes",

    # --- layer 08 ---
    "only their own part",
    "n",
    "yes",  # names and pay-adjacent scheduling data
    "n",
    "Payroll, probably, once labour cost gets tied into the same view.",
    "n",
    "yes",

    # --- layer 09 ---
    "thousands",
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
