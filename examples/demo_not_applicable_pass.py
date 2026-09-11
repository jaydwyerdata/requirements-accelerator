"""Demo run 4: the "not applicable" branch, on both layers that have one.

Dimensions come back "none", so layer 02's drill_through_required resolves to inferred "not
applicable" instead of being asked (docs/interview-branching.md's second exception). Only one
source system is named, so layer 04's system_of_record resolves the same way. No ambiguous
term ever surfaces, so layer 07 runs zero times, per the same document ("if no such term
surfaced, which would be unusual, layer 07 runs zero times"). Layer 05's reflection gets no
reaction this time (an empty reply), so steward and decision_rights stay inferred rather than
being promoted - the third path through reflect_and_promote that demo_full_pass.py doesn't
exercise (that one confirms, this one is silent).
"""

from unittest.mock import patch
from engine.ledger import Ledger, ProvenanceState
from engine.knowledge import NoRetainedKnowledge
from engine.reasoner import StubReasoner
from engine.interview import run_interview
from engine.render import render_business_ask, render_technical_spec

RESPONSES = [
    # --- layer 00 ---
    "The exec team keeps asking for a single number for open support tickets and everyone "
    "quotes a different one in the Monday standup.",
    "n",  # reasoner: not a solution in disguise
    "Whoever's presenting pulls their own count from whatever tool they have open at the time.",
    "daily",
    "The support lead and whoever's covering the standup that week.",
    "I'd stop reconciling three different ticket counts before every standup.",
    "Everyone in the standup is looking at the same number without checking first.",
    "",  # layer 00 reflection: no correction
    "",  # extract_terms after layer 00

    # --- layer 01 ---
    "how many",
    "on a schedule",
    "Just the support lead, standing in for whoever presents that week.",
    "yes",  # layer 01 reflection confirm
    "",  # extract_terms after layer 01

    # --- layer 02 ---
    "open ticket count",
    "none",  # dimensions - this is what makes drill_through_required not applicable
    "no target, no comparison needed",  # benchmark_comparison
    "yes",  # layer 02 reflection confirm (also promotes the inferred drill_through_required)
    "",  # extract_terms after layer 02

    # --- layer 03 ---
    "one ticket",
    "no",
    "no",
    "yes",  # layer 03 reflection confirm
    "",  # extract_terms after layer 03

    # --- layer 04 ---
    "Just the support desk tool, nothing else.",
    "n",  # reasoner: no, this only names one system
    "Support agents log it the moment a ticket is opened.",
    "no",  # restatement_handling - "no", so no follow-up question
    "yes",  # layer 04 reflection confirm
    "",  # extract_terms after layer 04

    # --- layer 05 ---
    "The support lead and the on-call engineering rotation both watch this.",
    "The support lead, they'd know why a number looks off.",
    "The support lead, it's their number to call.",
    "Straight into the standup deck.",
    "The standup has nothing to open with if this is wrong.",
    "The support lead.",
    "",  # layer 05 reflection: no reaction - steward/decision_rights stay inferred
    "",  # extract_terms after layer 05

    # --- layer 06 ---
    "real-time",
    "none",
    "this year only",
    "only how it looks now",
    "yes",  # layer 06 reflection confirm
    "",  # extract_terms after layer 06 - still nothing, so layer 07 runs zero times

    # --- layer 08 ---
    "everyone sees all of it",
    "no",
    "Not sure, nobody's asked yet.",
    "yes",  # layer 08 reflection confirm

    # --- layer 09 ---
    "hundreds",
    "no",
    "yes",  # layer 09 reflection confirm
]

if __name__ == "__main__":
    with patch("builtins.input", side_effect=RESPONSES):
        ledger = Ledger()
        reasoner = StubReasoner()
        knowledge = NoRetainedKnowledge()
        run_interview(ledger, reasoner, knowledge)

        drill = ledger.get("drill_through_required")
        assert drill is not None and drill.value == "not applicable", "drill-through should be n/a"
        system_of_record = ledger.get("system_of_record")
        assert system_of_record is not None and system_of_record.value == "not applicable", \
            "system of record should be n/a"
        steward = ledger.get("steward")
        assert steward is not None and steward.state == ProvenanceState.INFERRED, \
            "steward should stay inferred with no reaction to the reflection"

        print()
        print("=" * 60)
        print()
        print(render_business_ask(ledger))
        print()
        print(render_technical_spec(ledger))
