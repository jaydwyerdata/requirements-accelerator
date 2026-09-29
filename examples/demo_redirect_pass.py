"""Demo run 2: the problem statement trips the redirect on attempt one, self-corrects on
attempt two (the two-attempt cap), and the reflection step gets used to fix a detail.

Updated for docs/interview-branching.md v0.2. The redirect is now `_classify_and_reframe`'s
shared loop: the generic non-answer check comes back clean (this is a confidently stated
answer, not confusion), so layer 00's extra solution-in-disguise check is what actually flags
it, `reasoner.reframe()` (StubReasoner: a person at the keyboard) supplies the follow-up
question, phrased here the same way the old fixed redirect message was, and the second attempt
clears both checks. Every other question in the layer gets the one generic check that didn't
exist in the original version of this demo.
"""

from unittest.mock import patch
from engine.ledger import Ledger
from engine.reasoner import StubReasoner
from engine.interview import run_layer_00
from engine.render import render_business_ask, render_readiness_block

RESPONSES = [
    "We need a Power BI dashboard for renewals.",
    "n",  # generic check: reads like a real answer on its own
    "y",  # layer 00's extra check: yes, this is a solution in disguise
    "That sounds like where you'd like to end up. Before we get there: what's actually "
    "going wrong today that led you to that?",  # reframe: the redirect, in different words
    "Nobody trusts the renewals numbers because finance and sales calculate them "
    "differently and nobody's ever reconciled that.",
    "n",  # generic check: a genuine answer this time
    "n",  # layer 00's extra check: no, this is the actual problem
    "I don't, really. Finance and sales each keep their own spreadsheet and argue about "
    "whose is right.",
    "n",  # generic check
    "weekly",
    "n",  # generic check
    "Finance, sales ops, and the regional directors who get asked to explain the gap.",
    "n",  # generic check
    "I'd stop getting pulled into the argument and just point at one number.",
    "n",  # generic check
    "Finance and sales stop disagreeing about the renewals number in the same meeting.",
    "n",  # generic check
    "actually it's closer to twice a week, not just weekly",  # reflection correction
]

if __name__ == "__main__":
    with patch("builtins.input", side_effect=RESPONSES):
        ledger = Ledger()
        reasoner = StubReasoner()
        run_layer_00(ledger, reasoner)
        print()
        print("=" * 60)
        print()
        print(render_business_ask(ledger))
        print()
        print(render_readiness_block(ledger))
