"""Demo run 2: the problem statement trips the redirect on attempt one, self-corrects on
attempt two (the two-attempt cap), and the reflection step gets used to fix a detail."""

from unittest.mock import patch
from engine.ledger import Ledger
from engine.reasoner import StubReasoner
from engine.interview import run_layer_00
from engine.render import render_business_ask, render_readiness_block

RESPONSES = [
    "We need a Power BI dashboard for renewals.",
    "y",  # reasoner judgment: yes, this is a solution in disguise
    "Nobody trusts the renewals numbers because finance and sales calculate them "
    "differently and nobody's ever reconciled that.",
    "n",  # reasoner judgment: no, this is the actual problem
    "I don't, really. Finance and sales each keep their own spreadsheet and argue about "
    "whose is right.",
    "weekly",
    "Finance, sales ops, and the regional directors who get asked to explain the gap.",
    "I'd stop getting pulled into the argument and just point at one number.",
    "Finance and sales stop disagreeing about the renewals number in the same meeting.",
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
