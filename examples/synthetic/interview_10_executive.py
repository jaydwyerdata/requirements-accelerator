"""Synthetic interview 10 of 10: Alderglen Outfitters' COO, wanting one number for "how the
business is doing".

A clean layer 00 pass, but layer 02's dimensions answer is "none", so drill-through resolves to
inferred "not applicable" without being asked, the other not-applicable branch this dataset
exercises for layer 02 specifically (layer 04's "not applicable" branch appears in interviews 2,
7 and 9). The term "efficient store" starts too vague to test ("one that's just running well"),
gets reframed once inside layer 07's own vagueness loop (the same mechanism as layer 00's
solution-in-disguise redirect, `_classify_and_reframe`, just with layer 07's extra check
instead), becomes concrete, but the final reflection gets no reaction, so it ends up recorded but
explicitly not locked, a realistic "requester ran out of time or patience" outcome, not a bug.

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
    "Every report I get tells a different story about how the business is actually doing, so I "
    "end up in every leadership meeting arguing about whose number is right before we can even "
    "discuss what to do about it.",
    "n",
    "n",
    "Each function brings their own version to the leadership meeting and we spend the first "
    "twenty minutes reconciling numbers instead of making decisions.",
    "n",
    "weekly",
    "n",
    "The entire leadership team, every single week.",
    "n",
    "I'd walk into leadership meetings ready to make a decision, not to referee whose number is "
    "correct.",
    "n",
    "One number everyone agrees on, before we even start the meeting.",
    "n",
    "",
    "",

    # --- layer 01 ---
    "how much",
    "n",
    "on a schedule",
    "n",
    "The whole leadership team, and yes, everyone's ultimately asking the same thing in their "
    "own language.",
    "n",
    "yes",
    "",

    # --- layer 02 ---
    "One overall measure of how the business is performing this week.",
    "n",
    "none",  # dimensions: "none" - drill_through_required is skipped entirely, no input needed
    "n",
    "a target",
    "n",
    "yes",
    "",  # extract_terms after layer 02: nothing yet

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
    "The finance ERP, and the BI layer that already blends store, e-commerce and loyalty data "
    "together.",
    "n",
    "y",  # reasoner judge: yes, more than one system
    "The finance ERP, since that's what ultimately gets reported externally.",
    "n",
    "Finance closes and posts overnight.",
    "n",
    "yes",  # restatement_handling
    "n",
    "Finance restates during month-end close if something was miscoded.",
    "yes",
    "efficient store",  # extract_terms after layer 04: the one term this interview queues

    # --- layer 05 ---
    "Every function on the leadership team.",
    "n",
    "Finance, in practice, everyone defers to them when a number's disputed.",
    "n",
    "Me, if finance and another function still can't agree.",
    "n",
    "Into the weekly leadership meeting and the board pack.",
    "n",
    "The entire leadership meeting stalls without it.",
    "n",
    "Me.",
    "n",
    "yes",
    "",

    # --- layer 06 ---
    "next morning",
    "n",
    "Monday morning",
    "n",
    "five years or more",
    "n",
    "what it looked like back then",
    "n",
    "yes",
    "",

    # --- consolidate ---
    "",

    # --- layer 07: "efficient store", vague first, reframed, then not locked ---
    "An efficient store is basically one that's just running well.",
    "n",  # generic check: a confident claim, not confusion
    "y",  # layer 07 extra check: yes, too vague to test - loop once
    "What would actually make a store count as efficient, concretely enough to check against "
    "its own numbers?",  # the reframed question
    "One hitting both its labour-to-sales ratio target and its stockout target in the same "
    "month.",
    "n",
    "n",  # concrete enough now, loop breaks
    "not a concern",
    "none",
    "Nobody's really named this yet, it's just what I mean when I say a store's 'firing on all "
    "cylinders'.",
    "",  # no reaction to the final reflection - stays unlocked regardless of being concrete now

    # --- layer 08 ---
    "everyone sees all of it",
    "n",
    "no",
    "n",
    "Probably every function eventually, once it's actually trusted.",
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
