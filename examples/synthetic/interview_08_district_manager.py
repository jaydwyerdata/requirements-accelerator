"""Synthetic interview 8 of 10: a District Manager at Alderglen Outfitters, comparing six
stores.

Opens with a proposed solution ("a scorecard comparing my six stores every Monday morning"), so
layer 00's gate flags it and redirects, the second scripted redirect in this set (interview 3's
FP&A Analyst is the first). Adds no new term to the queue at all: `pending_terms` stays empty
through every layer, so `run_interview`'s `if pending_terms` guard, the same guard whose missing
check caused a real regression once (see docs/architecture-decisions.md), skips
`consolidate_terms` entirely, and `run_layer_07` is called with an empty list and returns
immediately. A realistic outcome, not an edge case: plenty of requests genuinely define nothing
new, and the technical spec still needs to render sensibly with an empty semantic layer section.

Part of the ten-interview synthetic dataset, see docs/synthetic-dataset.md.
"""

from unittest.mock import patch
from engine.ledger import Ledger
from engine.knowledge import NoRetainedKnowledge
from engine.reasoner import StubReasoner
from engine.interview import run_interview
from engine.render import render_business_ask, render_technical_spec

RESPONSES = [
    # --- layer 00: gated question, redirected once ---
    "I want a scorecard comparing my six stores side by side every Monday morning.",
    "n",  # generic check: a clear statement
    "y",  # layer 00 extra check: yes, this reads as a solution
    "Before the scorecard: what's the actual problem you run into without one?",  # reframed
    "I can't tell which of my six stores is actually underperforming until the monthly "
    "district review, and by then a whole month's already gone by.",
    "n",
    "n",  # not a solution this time
    "I wait for the monthly district pack finance puts together, which is already three weeks "
    "stale by the time I see it.",
    "n",
    "monthly",
    "n",
    "Every store lead in my district, they all get compared whether they like it or not.",
    "n",
    "I'd step into a struggling store the same week it starts slipping, not a month later.",
    "n",
    "I can compare my six stores against each other every week, not just at month end.",
    "n",
    "",
    "",  # extract_terms after layer 00: nothing

    # --- layer 01 ---
    "which ones",
    "n",
    "on a schedule",
    "n",
    "Just me, honestly, my store leads see their own store's number but not each other's.",
    "n",
    "yes",
    "",

    # --- layer 02 ---
    "Sales against target, by store.",
    "n",
    "store, time",
    "n",
    "yes",  # drill_through_required, asked live
    "n",
    "another team",
    "n",
    "yes",
    "",  # extract_terms after layer 02: nothing

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
    "Just the POS system, store by store.",
    "n",
    "n",  # reasoner judge: no, only one system - system_of_record -> not applicable
    "Sales post the same day they happen.",
    "n",
    "no",  # restatement_handling
    "n",
    "yes",
    "",

    # --- layer 05 ---
    "My store leads, once they see how they compare.",
    "n",
    "Me.",
    "n",
    "Me.",
    "n",
    "Into my own weekly district huddle.",
    "n",
    "The weekly huddle has nothing current to open with.",
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
    "this year only",
    "n",
    "only how it looks now",
    "n",
    "yes",
    "",  # extract_terms after layer 06: still nothing - pending_terms stays empty

    # --- no consolidate_terms call, no layer 07 at all: pending_terms is empty ---

    # --- layer 08 ---
    "everyone sees all of it",
    "n",
    "no",
    "n",
    "Probably regional ops, if they want to compare across districts too.",
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
