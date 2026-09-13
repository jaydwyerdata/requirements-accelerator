"""Runs all ten synthetic interviews (see docs/synthetic-dataset.md) in order against one shared
fixture database, so the deliberate term reuse across them actually exercises retained knowledge
rather than each interview starting from nothing.

Order matters and is not arbitrary: interview 3 checks "active customer" against interview 2's
locked definition, and interview 5 checks "stockout" against interview 1's and "on-time delivery"
against interview 4's, so every dependency runs before the interview that depends on it. The list
below is the actual dependency order, not just a numbering convention.

Running this module directly rebuilds `examples/synthetic/alderglen.db` from scratch (gitignored,
generated output, exactly like `requirements_accelerator.db`; deleted first so re-running this
script is idempotent) and prints, for every locked term, what it locked as and what any
competing-definition check against it came back as. `tests/test_synthetic_dataset.py` is what
actually proves these outcomes in pass/fail terms; this script is for a human to read.
"""

import os
from unittest.mock import patch

from engine.ledger import Ledger
from engine.knowledge import SqliteRetainedKnowledge
from engine.reasoner import StubReasoner
from engine.interview import run_interview
from engine.storage import SqliteStorage

from examples.synthetic.interview_01_store_ops import RESPONSES as R1
from examples.synthetic.interview_02_marketing import RESPONSES as R2
from examples.synthetic.interview_03_finance import RESPONSES as R3
from examples.synthetic.interview_04_customer_experience import RESPONSES as R4
from examples.synthetic.interview_05_supply_chain import RESPONSES as R5
from examples.synthetic.interview_06_hr import RESPONSES as R6
from examples.synthetic.interview_07_loyalty import RESPONSES as R7
from examples.synthetic.interview_08_district_manager import RESPONSES as R8
from examples.synthetic.interview_09_governance import RESPONSES as R9
from examples.synthetic.interview_10_executive import RESPONSES as R10

# (interview id, requester role, scripted responses), in dependency order.
INTERVIEWS = [
    ("store-ops-01", "Store Operations Manager", R1),
    ("marketing-02", "Digital Marketing Manager", R2),
    ("finance-03", "FP&A Analyst", R3),
    ("cx-04", "Customer Experience Lead", R4),
    ("supply-chain-05", "Supply Chain Analyst", R5),
    ("hr-06", "People Analytics Partner", R6),
    ("loyalty-07", "Basecamp Rewards Manager", R7),
    ("district-08", "District Manager", R8),
    ("governance-09", "Data Governance Lead", R9),
    ("executive-10", "Chief Operating Officer", R10),
]


def run_all(db_path: str) -> dict[str, Ledger]:
    """Runs every interview in order against db_path, saving each as it finishes so later
    interviews in the list see earlier ones as retained knowledge. Returns every interview's
    ledger, keyed by interview id, for a caller (this module's __main__ block, or the test
    suite) to inspect afterwards.
    """
    storage = SqliteStorage(db_path)
    ledgers: dict[str, Ledger] = {}
    for interview_id, _role, responses in INTERVIEWS:
        knowledge = SqliteRetainedKnowledge(db_path)
        with patch("builtins.input", side_effect=responses):
            ledger = Ledger()
            run_interview(ledger, StubReasoner(), knowledge)
        storage.save_interview(interview_id, ledger)
        ledgers[interview_id] = ledger
    return ledgers


def _locked_terms(ledger: Ledger) -> list[str]:
    terms = []
    for record in ledger.all():
        if record.field_id.startswith("term_locked::") and record.value:
            terms.append(record.field_id.split("::", 1)[1])
    return terms


def _competing_checks(ledger: Ledger) -> dict[str, str]:
    checks = {}
    for record in ledger.all():
        if record.field_id.startswith("competing_definition_check::"):
            term = record.field_id.split("::", 1)[1]
            checks[term] = record.value
    return checks


if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(__file__), "alderglen.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    ledgers = run_all(db_path)

    print(f"Ran {len(ledgers)} synthetic interviews against {db_path}\n")
    for interview_id, role, _responses in INTERVIEWS:
        ledger = ledgers[interview_id]
        locked = _locked_terms(ledger)
        checks = _competing_checks(ledger)
        print(f"{interview_id} ({role})")
        if not locked and not checks:
            print("  no terms queued")
        for term in locked:
            check = checks.get(term)
            check_note = f", competing check: {check!r}" if check else ""
            print(f"  locked {term!r}{check_note}")
        for term, check in checks.items():
            if term not in locked:
                print(f"  saw {term!r} but did not lock it, competing check: {check!r}")
        print()

    print("See docs/synthetic-dataset.md for what these outcomes mean for e8, and")
    print("tests/test_synthetic_dataset.py for the automated assertions over them.")
