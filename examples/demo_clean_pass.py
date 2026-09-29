"""Demo run 1: a clean pass, every layer 00 question accepted on the first try.

Updated for docs/interview-branching.md v0.2: every live question now runs the shared
classify-and-reframe check (engine/interview.py's _classify_and_reframe), one extra scripted
reply per question compared to the original version of this demo. The problem statement gets
two checks, the generic non-answer check plus layer 00's own solution-in-disguise check, since
the second only runs when the first comes back clean; every other question in this layer gets
just the one generic check.
"""

from unittest.mock import patch
from engine.ledger import Ledger
from engine.reasoner import StubReasoner
from engine.interview import run_layer_00
from engine.render import render_business_ask, render_readiness_block

RESPONSES = [
    "Our finance team spends two days every month manually reconciling renewals because "
    "nobody trusts the numbers in the dashboard.",
    "n",  # generic check: a genuine answer
    "n",  # layer 00's extra check: not a solution in disguise
    "I pull last month's export from the CRM, cross-check it against the finance ledger "
    "in a spreadsheet, and email finance if the two don't match.",
    "n",  # generic check: a genuine answer
    "monthly",
    "n",  # generic check: a genuine answer
    "Regional finance leads, and occasionally sales ops when they pull their own numbers.",
    "n",  # generic check: a genuine answer
    "I'd stop double-checking the numbers by hand before every leadership meeting, and "
    "just trust the dashboard.",
    "n",  # generic check: a genuine answer
    "Finance stops asking me to double check renewals every month, and the dashboard "
    "number matches what we actually bill.",
    "n",  # generic check: a genuine answer
    "",  # reflection: no correction
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
