"""Synthetic interview 9 of 10: the Data Governance Lead at Alderglen Outfitters, on who can see
customer PII across existing reports.

A clean pass. Exercises layer 04's "not applicable" branch a second time in this dataset (only
one system named, the report catalogue itself), and layer 08's access questions in full. Locks a
standalone term, "restricted field", not reused elsewhere.

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
    "Nobody can tell me, without checking every report by hand, which dashboards actually "
    "expose customer names, addresses or payment details to people who shouldn't see them.",
    "n",
    "n",
    "When a new report request comes in, I ask around and hope someone remembers what's "
    "sensitive, there's no actual list.",
    "n",
    "monthly",
    "n",
    "Every data team member who builds a report, and legal when an access review comes up.",
    "n",
    "I'd approve or reject a new report's access model against an actual list, instead of "
    "asking around.",
    "n",
    "I can see, for any report, exactly which fields on it are sensitive and who's allowed to "
    "see them.",
    "n",
    "",
    "",

    # --- layer 01 ---
    "which ones",
    "n",
    "when something feels wrong",
    "n",
    "Legal, and yes, they're asking essentially the same thing from an audit angle.",
    "n",
    "yes",
    "",

    # --- layer 02 ---
    "Count of fields classified as sensitive, by report.",
    "n",
    "team",
    "n",
    "yes",  # drill_through_required, asked live
    "n",
    "none",
    "n",
    "yes",
    "restricted field",

    # --- layer 03 ---
    "one sensitive field on one report",
    "n",
    "no",
    "n",
    "yes",  # cardinality_risk: a field can be classified under more than one sensitivity category
    "n",
    "yes",
    "",

    # --- layer 04 ---
    "Just the report catalogue itself, that's the only place any of this is tracked at all "
    "right now.",
    "n",
    "n",  # reasoner judge: no, only one system - system_of_record -> not applicable
    "Whoever builds a report is supposed to tag its fields at build time, but it's inconsistent.",
    "n",
    "yes",  # restatement_handling
    "n",
    "I correct a missed classification whenever an access review turns one up.",
    "yes",
    "",

    # --- layer 05 ---
    "Every team with an existing report, and legal for the annual access review.",
    "n",
    "Me.",
    "n",
    "Me, with legal as the final call on anything genuinely disputed.",
    "n",
    "Into the annual access review and any new report's build checklist.",
    "n",
    "The annual access review has no reliable source to check against.",
    "n",
    "Me.",
    "n",
    "yes",
    "",

    # --- layer 06 ---
    "weekly or slower",
    "n",
    "none",
    "n",
    "all available history",
    "n",
    "what it looked like back then",
    "n",
    "yes",
    "",

    # --- consolidate ---
    "",

    # --- layer 07: "restricted field" ---
    "A field counts as restricted if it identifies an individual customer or employee "
    "directly, like a name, address or payment detail, or would let someone work out who it "
    "is when combined with another field on the same report.",
    "n",
    "n",
    "worth flagging",  # no prior definition; legal might define this more broadly
    "none",
    "Legal calls this 'personal data', the data team's always just said 'PII'.",
    "yes",

    # --- layer 08 ---
    "only their own part",
    "n",
    "yes",
    "n",
    "Legal, directly, for the audit trail.",
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
