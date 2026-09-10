"""Demo run 1: a clean pass, problem statement accepted on the first try."""

from unittest.mock import patch
from engine.ledger import Ledger
from engine.reasoner import StubReasoner
from engine.interview import run_layer_00
from engine.render import render_business_ask, render_readiness_block

RESPONSES = [
    "Our finance team spends two days every month manually reconciling renewals because "
    "nobody trusts the numbers in the dashboard.",
    "n",  # reasoner judgment: not a solution in disguise
    "I pull last month's export from the CRM, cross-check it against the finance ledger "
    "in a spreadsheet, and email finance if the two don't match.",
    "monthly",
    "Regional finance leads, and occasionally sales ops when they pull their own numbers.",
    "I'd stop double-checking the numbers by hand before every leadership meeting, and "
    "just trust the dashboard.",
    "Finance stops asking me to double check renewals every month, and the dashboard "
    "number matches what we actually bill.",
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
