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

Updated for docs/interview-branching.md v0.2: every live question now runs the shared
classify-and-reframe check, one extra scripted reply per question that doesn't exactly match
one of its own offered choices. The problem statement and layer 07's definition question each
get a second check too (layer 00's solution-in-disguise check, layer 07's testability check),
since those only run once the generic check comes back clean. restatement_handling picked up
the same generic check when it was folded into the shared mechanism. The one new call with no
per-question equivalent is the single `consolidate_terms` pass between layer 06 and layer 07,
once for the whole queue rather than per term.

An answer that exactly matches one of the question's own choices (frequency's "weekly",
drill_through_required's "yes", and so on) skips the reasoner call entirely: confirmed live
against ClaudeCodeReasoner that this is the only way to stop the classifier flagging a reply
like "how many" or "not sure" as a non-answer when it is, in fact, one of the question's own
listed options, and the classifier has no way to know that from the reply text alone. No "n"
line follows those answers below; free-text answers, and choice answers that don't exactly
match (grain's "one lead", dimensions' "region, time"), still get one.
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
    "n",  # generic check: a genuine answer
    "n",  # layer 00's extra check: not a solution in disguise
    "Right now each region exports their own CRM view, recalculates by hand in Excel, and "
    "finance reconciles it against the pipeline report before the Monday leadership call.",
    "n",  # generic check
    "weekly",
    "n",  # generic check
    "Regional sales leads, the sales VP, and finance during month-end close.",
    "n",  # generic check
    "I'd stop rebuilding the same spreadsheet every Monday and just trust the dashboard.",
    "n",  # generic check
    "The dashboard number matches what finance reports without anyone re-deriving it by hand.",
    "n",  # generic check
    "",  # layer 00 reflection: no correction
    "",  # extract_terms after layer 00: nothing yet

    # --- layer 01 ---
    "how many",
    "n",  # generic check
    "on a schedule",
    "n",  # generic check
    "Regional sales leads and the sales VP, and yes, they're all asking the same question.",
    "n",  # generic check
    "yes",  # layer 01 reflection confirm
    "",  # extract_terms after layer 01

    # --- layer 02 ---
    "qualified lead count",
    "n",  # generic check
    "region, time",
    "n",  # generic check
    "yes",  # drill_through_required - asked live, since dimensions isn't "none"
    "n",  # generic check
    "last year",
    "n",  # generic check
    "yes",  # layer 02 reflection confirm
    "qualified lead",  # extract_terms after layer 02: queues our one term

    # --- layer 03 ---
    "one lead",
    "n",  # generic check
    "no",
    "n",  # generic check
    "no",
    "n",  # generic check
    "yes",  # layer 03 reflection confirm
    "",  # extract_terms after layer 03

    # --- layer 04 ---
    "Salesforce for the raw leads, and NetSuite for the billing confirmation once one converts.",
    "n",  # generic check
    "y",  # reasoner: yes, this names more than one system (unchanged, its own judge call)
    "Salesforce, since that's where a lead first gets marked qualified.",  # system_of_record, asked live
    "n",  # generic check
    "Sales reps mark a lead qualified as soon as they finish a discovery call.",
    "n",  # generic check
    "yes",  # restatement_handling
    "n",  # generic check
    "Sales ops corrects it during weekly pipeline review if a rep mismarked something.",
    "yes",  # layer 04 reflection confirm
    "",  # extract_terms after layer 04

    # --- layer 05 ---
    "Sales ops and the regional forecasting model both read off this number.",
    "n",  # generic check
    "Sales ops, they're who gets asked first when the number looks off.",
    "n",  # generic check
    "The sales VP, if sales ops and finance can't agree.",
    "n",  # generic check
    "Into the regional forecast and the quarterly board pack.",
    "n",  # generic check
    "The Monday leadership call stalls without it.",
    "n",  # generic check
    "The sales VP.",
    "n",  # generic check
    "yes",  # layer 05 reflection confirm - promotes steward & decision_rights to stated
    "",  # extract_terms after layer 05

    # --- layer 06 ---
    "next morning",
    "n",  # generic check
    "Monday morning",
    "n",  # generic check
    "last two to three years",
    "n",  # generic check
    "only how it looks now",
    "n",  # generic check
    "yes",  # layer 06 reflection confirm
    "",  # extract_terms after layer 06

    # --- term queue consolidation, once, before layer 07 opens ---
    "",  # consolidate_terms: keep the one candidate as-is

    # --- layer 07: "qualified lead" ---
    "A lead counts as qualified once a rep completes a discovery call and confirms budget, "
    "so it has to have a logged call and a budget field filled in.",
    "n",  # generic check: a genuine answer
    "n",  # layer 07's extra check: not too vague, concrete enough
    "No, marketing still counts a lead qualified just from a form fill, so this would need "
    "reconciling with them.",
    "tests",
    "Some people just call it an SQL.",
    "yes",  # term reflection confirm - locks the definition

    # --- layer 08 ---
    "everyone sees all of it",
    "n",  # generic check
    "no",
    "n",  # generic check
    "Marketing ops, once they see sales tightened up their definition.",
    "n",  # generic check
    "yes",  # layer 08 reflection confirm

    # --- layer 09 ---
    "thousands",
    "n",  # generic check
    "yes",
    "n",  # generic check
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
