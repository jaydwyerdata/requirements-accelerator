"""Demo run 3: a full pass through all nine layers, including layer 07's per-term loop.

Exercises, in one scripted run: layer 00's clean (non-redirected) gate; layer 02's
drill-through question NOT skipped (dimensions are named); layer 04's system-of-record
question asked live (more than one source system named, via the reasoner) plus the
restatement-handling follow-up; layer 05's steward/decision_rights fields promoted from
inferred to stated by a confirmed reflection; one queued term ("qualified lead") run through
layer 07's full loop to a locked definition; and layers 06, 08 and 09 straight through.

This is the scenario the renderer needs to prove out the full technical spec shape (a
promoted-from-inferred field, a "not applicable" case is exercised separately in
demo_not_applicable_pass.py, and a locked term with its reporting-spec entry) end to end.
"""

from unittest.mock import patch
from engine.ledger import Ledger
from engine.knowledge import NoRetainedKnowledge
from engine.reasoner import StubReasoner
from engine.interview import run_interview
from engine.render import render_business_ask, render_technical_spec

RESPONSES = [
    # --- layer 00 ---
    "Our regional sales leads keep asking finance to re-run the qualified lead numbers "
    "because the number in the CRM dashboard never matches what they report to their VP.",
    "n",  # reasoner: not a solution in disguise
    "Right now each region exports their own CRM view, recalculates by hand in Excel, and "
    "finance reconciles it against the pipeline report before the Monday leadership call.",
    "weekly",
    "Regional sales leads, the sales VP, and finance during month-end close.",
    "I'd stop rebuilding the same spreadsheet every Monday and just trust the dashboard.",
    "The dashboard number matches what finance reports without anyone re-deriving it by hand.",
    "",  # layer 00 reflection: no correction
    "",  # extract_terms after layer 00: nothing yet

    # --- layer 01 ---
    "how many",
    "on a schedule",
    "Regional sales leads and the sales VP, and yes, they're all asking the same question.",
    "yes",  # layer 01 reflection confirm
    "",  # extract_terms after layer 01

    # --- layer 02 ---
    "qualified lead count",
    "region, time",
    "yes",  # drill_through_required - asked live, since dimensions isn't "none"
    "last year",
    "yes",  # layer 02 reflection confirm
    "qualified lead",  # extract_terms after layer 02: queues our one term

    # --- layer 03 ---
    "one lead",
    "no",
    "no",
    "yes",  # layer 03 reflection confirm
    "",  # extract_terms after layer 03

    # --- layer 04 ---
    "Salesforce for the raw leads, and NetSuite for the billing confirmation once one converts.",
    "y",  # reasoner: yes, this names more than one system
    "Salesforce, since that's where a lead first gets marked qualified.",
    "Sales reps mark a lead qualified as soon as they finish a discovery call.",
    "yes",  # restatement_handling
    "Sales ops corrects it during weekly pipeline review if a rep mismarked something.",
    "yes",  # layer 04 reflection confirm
    "",  # extract_terms after layer 04

    # --- layer 05 ---
    "Sales ops and the regional forecasting model both read off this number.",
    "Sales ops, they're who gets asked first when the number looks off.",
    "The sales VP, if sales ops and finance can't agree.",
    "Into the regional forecast and the quarterly board pack.",
    "The Monday leadership call stalls without it.",
    "The sales VP.",
    "yes",  # layer 05 reflection confirm - promotes steward & decision_rights to stated
    "",  # extract_terms after layer 05

    # --- layer 06 ---
    "next morning",
    "Monday morning",
    "last two to three years",
    "only how it looks now",
    "yes",  # layer 06 reflection confirm
    "",  # extract_terms after layer 06

    # --- layer 07: "qualified lead" ---
    "A lead counts as qualified once a rep completes a discovery call and confirms budget, "
    "so it has to have a logged call and a budget field filled in.",
    "n",  # reasoner: not too vague, concrete enough
    "No, marketing still counts a lead qualified just from a form fill, so this would need "
    "reconciling with them.",
    "tests",
    "Some people just call it an SQL.",
    "yes",  # term reflection confirm - locks the definition

    # --- layer 08 ---
    "everyone sees all of it",
    "no",
    "Marketing ops, once they see sales tightened up their definition.",
    "yes",  # layer 08 reflection confirm

    # --- layer 09 ---
    "thousands",
    "yes",
    "yes",  # layer 09 reflection confirm
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
