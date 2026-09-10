"""The layer 00 interview loop.

Implements the gate and capped redirect from docs/interview-branching.md: the problem
statement is the only gated field in this slice, checked against the reasoner, redirected
and re-asked once if it reads as a solution rather than a problem, then accepted either way
once the two-attempt cap is reached. Ends with a reflection checkpoint per CLAUDE.md's
"reflect understanding back at each layer boundary" rule.
"""

from .ledger import Ledger, ProvenanceState
from .protocol import LAYER_00_QUESTIONS, MAX_LAYER_00_ATTEMPTS
from .reasoner import Reasoner

REDIRECT_MESSAGE = (
    "  That sounds like where you'd like to end up. Before we get there: what's\n"
    "  actually going wrong today that led you to that?"
)


def run_layer_00(ledger: Ledger, reasoner: Reasoner, ask=None) -> dict[str, str]:
    if ask is None:
        ask = input
    answers: dict[str, str] = {}
    gated_question = LAYER_00_QUESTIONS[0]

    print(gated_question.prompt)
    value = ask("> ")
    attempt = 1
    flagged = False
    while True:
        flagged = reasoner.is_solution_in_disguise(value)
        if not flagged or attempt >= MAX_LAYER_00_ATTEMPTS:
            break
        attempt += 1
        print()
        print(REDIRECT_MESSAGE)
        value = ask("> ")

    note = "" if not flagged else "still reads as a proposed solution after two attempts, flagged for review"
    answers[gated_question.field_id] = value
    ledger.set(gated_question.field_id, "00", value, ProvenanceState.STATED,
               source="requester, layer 00", note=note)

    for question in LAYER_00_QUESTIONS[1:]:
        print()
        print(question.prompt)
        if question.choices:
            print("  (" + " / ".join(question.choices) + ")")
        value = ask("> ")
        answers[question.field_id] = value
        ledger.set(question.field_id, "00", value, ProvenanceState.STATED,
                   source="requester, layer 00")

    print()
    print(reasoner.summarise_for_reflection(answers))
    correction = ask("Anything you'd change about that? Enter to move on, or type a correction: ")
    if correction.strip():
        ledger.set("layer_00_reflection_correction", "00", correction, ProvenanceState.STATED,
                    source="requester, layer 00 reflection")

    return answers
