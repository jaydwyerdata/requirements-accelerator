"""Demo run 5: e3 (SQLite storage) actually retaining something across interviews.

Runs one scripted layer-07 pass over two terms: "at risk customer" locks (concrete definition,
explicit exclusions, confirmed reflection), "healthy account" does not (the reflection gets no
reaction). Saves the ledger to a throwaway SQLite file via SqliteStorage, then proves
SqliteRetainedKnowledge finds the locked term's definition and correctly reports nothing for the
unlocked one - only a locked definition counts as retained knowledge, per
docs/interview-branching.md's three lock conditions, not just "a term someone typed something
for once."
"""

import os
import tempfile
from unittest.mock import patch

from engine.ledger import Ledger
from engine.reasoner import StubReasoner
from engine.knowledge import NoRetainedKnowledge, SqliteRetainedKnowledge
from engine.storage import SqliteStorage
from engine.interview import run_layer_07

RESPONSES = [
    # --- "at risk customer": locks ---
    "A customer counts as at risk once they've had two support escalations in 30 days with no "
    "resolution.",
    "n",  # reasoner: not too vague, concrete enough
    "No, retention hasn't defined this before.",
    "cancellations",
    "Some call it a churn flag.",
    "yes",  # reflection confirm - locks it

    # --- "healthy account": does not lock ---
    "An account is healthy if it's not at risk, basically.",
    "y",  # reasoner: too vague
    "One that's renewed on time the last two cycles with no open escalation.",
    "n",  # reasoner: concrete enough now, loop breaks
    "No.",
    "none",
    "Nothing else, really.",
    "",  # no reaction to reflection - stays unlocked regardless of the definition being fine
]

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")

        with patch("builtins.input", side_effect=RESPONSES):
            ledger = Ledger()
            reasoner = StubReasoner()
            knowledge = NoRetainedKnowledge()  # nothing on file yet to check this interview against
            run_layer_07(ledger, reasoner, knowledge, ["at risk customer", "healthy account"])

        storage = SqliteStorage(db_path)
        storage.save_interview("interview-a", ledger)

        retained = SqliteRetainedKnowledge(db_path)
        locked_definition = retained.definition_for("at risk customer")
        unlocked_definition = retained.definition_for("healthy account")

        expected = ("A customer counts as at risk once they've had two support escalations "
                    "in 30 days with no resolution.")
        assert locked_definition == expected, (
            f"expected the locked definition back, got {locked_definition!r}")
        assert unlocked_definition is None, (
            f"an unlocked term should never come back as retained knowledge, got "
            f"{unlocked_definition!r}")

        # A second interview, same database, should now see the prior definition mid-interview -
        # not just via a direct definition_for() call, but through the actual layer 07 question.
        SECOND_INTERVIEW_RESPONSES = [
            "Basically the same idea, two unresolved escalations inside a month.",  # definition
            "n",  # not vague
            "yes",  # answering the now-concrete competing-definition question: matches
            "cancellations",
            "Churn flag, same as before.",
            "yes",  # reflection confirm
        ]
        with patch("builtins.input", side_effect=SECOND_INTERVIEW_RESPONSES):
            ledger_b = Ledger()
            run_layer_07(ledger_b, StubReasoner(), retained, ["at risk customer"])

        competing_check = ledger_b.get("competing_definition_check::at risk customer")
        assert competing_check is not None and competing_check.value == "yes", (
            "second interview should have been asked the retained-knowledge phrasing and "
            "answered it"
        )

        print("Retained knowledge check passed:")
        print(f'  "at risk customer" -> {locked_definition!r}')
        print(f'  "healthy account" -> {unlocked_definition!r} (not locked, correctly absent)')
        print('  Second interview against the same term saw the retained definition and '
              'answered the concrete version of the competing-definition question.')
