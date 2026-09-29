"""The interview loop: layers 00 through 09, run in order against one shared ledger.

Implements the recipes from docs/interview-branching.md. Most layers follow the shared
recipe with no complication (ask what's missing, tag it, reflect at the boundary) and are
handled by `run_simple_layer`. Three layers don't, and get their own function:

- Layer 00 has the only gate: the problem statement, via `_classify_and_reframe`, the same
  reply-classifying loop every question now runs, plus one extra field-specific check for a
  solution stated in disguise.
- Layer 02's drill-through question and layer 04's system-of-record question have real
  preconditions (no dimensions named / only one source system named) and resolve to an
  inferred "not applicable" instead of being silently skipped.
- Layer 07 is a loop over queued terms, not a single pass, with a retained-knowledge-aware
  competing-definition question and a per-term lock decision. Its definition question runs
  through `_classify_and_reframe` too, plus one extra field-specific check for a definition
  too vague to test.

Every live question, not just layer 00's and layer 07's, now classifies a reply before it is
written to the ledger: a clarifying question, a don't-know, or a genuine answer, per
docs/interview-branching.md v0.2's "Classifying a reply" section. `_ask_question` and
`_classify_and_reframe` are the shared machinery every layer function calls into; a reply
that still isn't a clear answer after `MAX_REDIRECT_ATTEMPTS` is recorded as-is, flagged in a
note, rather than looped on indefinitely or silently accepted on the first try.

Layer 07's candidate term queue is also deduplicated once, via `reasoner.consolidate_terms()`,
before the layer 07 loop opens, rather than trusting the per-layer exact-string dedup
`_collect_terms` used to rely on alone.

`run_interview` is the actual entry point cli.py calls: it owns the layer order and the
term queue that layer 07 runs against, so cli.py stays a thin shell.
"""

from .knowledge import RetainedKnowledge
from .ledger import Ledger, ProvenanceState
from .protocol import (
    LAYER_00_QUESTIONS, LAYER_01_QUESTIONS, LAYER_02_QUESTIONS, LAYER_03_QUESTIONS,
    LAYER_04_QUESTIONS, LAYER_05_QUESTIONS, LAYER_06_QUESTIONS, LAYER_07_QUESTIONS,
    LAYER_08_QUESTIONS, LAYER_09_QUESTIONS, MAX_REDIRECT_ATTEMPTS,
    COMPETING_DEFINITION_CHOICES_WITH_PRIOR, COMPETING_DEFINITION_CHOICES_NO_PRIOR,
)
from .reasoner import Reasoner

# Plain string matching, not a reasoner call: whether a reply confirms a reflection is a
# closed-set judgement about the reply's own wording, not an interpretive question about the
# requester's meaning.
AFFIRMATIVE = {
    "y", "yes", "yeah", "yep", "yup", "correct", "right", "that's right",
    "sounds right", "sounds good", "good", "confirmed",
}


def _is_affirmative(text: str) -> bool:
    return text.strip().lower() in AFFIRMATIVE


def _console_ask(prompt: str, choices: list[str] | None = None) -> str:
    """The default `ask`, when nothing is injected: plain console input via the `input`
    builtin. Takes the same `(prompt, choices=None)` shape every call site now uses and just
    ignores `choices`, since the console path already prints them as a hint via
    `_print_choices` right before asking. A UI that wants to render real widgets per
    docs/interview-ux.md (buttons for a closed set, a text box otherwise), bridge.py included,
    supplies its own `ask` and reads `choices` instead of ignoring it; the engine itself never
    branches on which kind it got, so this stays the only place console behaviour is defined.
    """
    return input(prompt)


def _print_choices(choices: list[str]) -> None:
    """The one place a question's fixed choices get printed as a console hint. Kept as a
    single function, not copy-pasted at each call site, so there is exactly one text format to
    keep in sync if it ever changes."""
    print("  (" + " / ".join(choices) + ")")


# The generic non-answer check every question runs, per docs/interview-branching.md v0.2's
# "Classifying a reply" section. Phrased so True means "this isn't a genuine answer, reframe
# and ask again" - the same polarity as the judge() calls this replaces.
NON_ANSWER_QUESTION = (
    "Is this a clarifying question about what's being asked, an admission of not knowing "
    "(not sure, don't know, unclear, or effectively blank), or otherwise not a genuine "
    "attempt to answer the question itself?"
)


def _classify_and_reframe(ledger, reasoner, prompt_text, value, ask, extra_flag_question=None):
    """The shared reply loop every live question now runs: classify what came back, and if it
    isn't a genuine answer, get a different way into the same question and ask again, capped at
    MAX_REDIRECT_ATTEMPTS.

    `extra_flag_question` lets one specific question add one more, field-specific reason to
    treat a reply as a non-answer even though it reads like one on its own, layer 00's solution-
    in-disguise check and layer 07's testability check are both this, OR'd with the generic
    check above rather than replacing it. Everything else just uses the generic check.

    Returns (final_value, flagged): flagged is True only if the cap was hit without landing a
    genuine answer, so the caller can note it on the ledger rather than treat it as settled.
    """
    attempt = 1
    flagged = False
    while True:
        flagged = reasoner.judge(NON_ANSWER_QUESTION, value)
        if not flagged and extra_flag_question is not None:
            flagged = reasoner.judge(extra_flag_question, value)
        if not flagged or attempt >= MAX_REDIRECT_ATTEMPTS:
            break
        attempt += 1
        reframed = reasoner.reframe(prompt_text, value, ledger.known_values())
        print()
        print(reframed)
        value = ask("> ")
    return value, flagged


def _ask_question(ledger, question, layer_id, ask, reasoner):
    print()
    print(question.prompt)
    if question.choices:
        _print_choices(question.choices)
    value = ask("> ", choices=question.choices)
    value, flagged = _classify_and_reframe(ledger, reasoner, question.prompt, value, ask)
    note = "" if not flagged else "not a clear answer after two attempts, flagged for review"
    state = ProvenanceState.INFERRED if question.inferred else ProvenanceState.STATED
    ledger.set(question.field_id, layer_id, value, state, source=f"requester, layer {layer_id}",
               note=note)
    return value


def reflect_and_promote(ledger: Ledger, reasoner: Reasoner, layer_id: str,
                         field_ids: list[str], ask) -> None:
    """The layer-boundary reflection step, shared by every non-gated layer.

    Per docs/interview-branching.md: explicit confirmation promotes every inferred row from
    this layer to stated; no reaction changes nothing, since silence isn't confirmation.
    Explicit correction is a harder case in a multi-field layer: the source document describes
    correcting a specific field's value, but a free-text reply here doesn't say which field it's
    about. Rather than guess, this records the correction as a layer-level note and leaves
    inferred fields inferred (a correction means the reflection wasn't right, so promoting
    something just flagged as wrong would be dishonest). Field-level correction is a real gap
    against the source doc, worth closing once there's a UI that can point at one field.
    """
    answers = {}
    for field_id in field_ids:
        record = ledger.get(field_id)
        if record is not None and record.state != ProvenanceState.MISSING:
            answers[field_id] = record.value
    if not answers:
        return
    print()
    print(reasoner.summarise_for_reflection(answers))
    reply = ask("Does that sound right? Enter to move on, 'yes' to confirm, or type a correction: ")
    reply = reply.strip()
    if not reply:
        return
    if _is_affirmative(reply):
        for field_id in field_ids:
            record = ledger.get(field_id)
            if record is not None and record.state == ProvenanceState.INFERRED:
                ledger.set(field_id, layer_id, record.value, ProvenanceState.STATED,
                           source=record.source + ", confirmed by reflection", note=record.note)
        return
    ledger.set(f"layer_{layer_id}_reflection_correction", layer_id, reply, ProvenanceState.STATED,
               source=f"requester, layer {layer_id} reflection")


def run_layer_00(ledger: Ledger, reasoner: Reasoner, ask=None) -> dict[str, str]:
    if ask is None:
        ask = _console_ask
    answers: dict[str, str] = {}
    gated_question = LAYER_00_QUESTIONS[0]

    print(gated_question.prompt)
    value = ask("> ")
    value, flagged = _classify_and_reframe(
        ledger, reasoner, gated_question.prompt, value, ask,
        extra_flag_question=(
            "Does this read as a proposed solution rather than a description of what's wrong?"
        ),
    )

    note = "" if not flagged else "still reads as a proposed solution after two attempts, flagged for review"
    answers[gated_question.field_id] = value
    ledger.set(gated_question.field_id, "00", value, ProvenanceState.STATED,
               source="requester, layer 00", note=note)

    for question in LAYER_00_QUESTIONS[1:]:
        value = _ask_question(ledger, question, "00", ask, reasoner)
        answers[question.field_id] = value

    print()
    print(reasoner.summarise_for_reflection(answers))
    correction = ask("Anything you'd change about that? Enter to move on, or type a correction: ")
    if correction.strip():
        ledger.set("layer_00_reflection_correction", "00", correction, ProvenanceState.STATED,
                    source="requester, layer 00 reflection")

    return answers


def run_simple_layer(layer_id: str, questions, ledger: Ledger, reasoner: Reasoner,
                      ask=None) -> dict[str, str]:
    """The shared recipe: ask what's missing, tag it, reflect at the boundary.

    Covers layers 01, 03, 05, 06, 08 and 09 - every layer where every question is independent
    of the others in the same layer and none has a real precondition.
    """
    if ask is None:
        ask = _console_ask
    print()
    answers: dict[str, str] = {}
    for question in questions:
        if not ledger.is_missing(question.field_id):
            continue  # already known (e.g. from seed intake) - reflected on, not re-asked
        answers[question.field_id] = _ask_question(ledger, question, layer_id, ask, reasoner)
    reflect_and_promote(ledger, reasoner, layer_id, [q.field_id for q in questions], ask)
    return answers


def run_layer_02(ledger: Ledger, reasoner: Reasoner, ask=None) -> dict[str, str]:
    """Layer 02. drill_through_required has a real precondition: no dimensions named means
    nothing to drill into, so it resolves to inferred "not applicable" rather than being asked.
    """
    if ask is None:
        ask = _console_ask
    print()
    answers: dict[str, str] = {}
    for question in LAYER_02_QUESTIONS:
        if not ledger.is_missing(question.field_id):
            continue
        if question.field_id == "drill_through_required":
            dimensions = ledger.get("dimensions")
            if dimensions is not None and str(dimensions.value).strip().lower() == "none":
                ledger.set(question.field_id, "02", "not applicable", ProvenanceState.INFERRED,
                           source="inferred from dimensions, layer 02",
                           note="no dimensions named, so nothing to drill into")
                continue
        answers[question.field_id] = _ask_question(ledger, question, "02", ask, reasoner)
    reflect_and_promote(ledger, reasoner, "02", [q.field_id for q in LAYER_02_QUESTIONS], ask)
    return answers


def run_layer_04(ledger: Ledger, reasoner: Reasoner, ask=None) -> dict[str, str]:
    """Layer 04. system_of_record has a real precondition: only one source system named means
    nothing to reconcile against, so it resolves to inferred "not applicable" instead. Whether
    source_systems names more than one system is an interpretive read of free text, so it goes
    to the reasoner rather than a string check. restatement_handling's own yes/no answer is a
    closed set, so that part is plain string matching, not a reasoner call.
    """
    if ask is None:
        ask = _console_ask
    print()
    answers: dict[str, str] = {}
    for question in LAYER_04_QUESTIONS:
        if not ledger.is_missing(question.field_id):
            continue
        if question.field_id == "system_of_record":
            source_systems = ledger.get("source_systems")
            names_multiple = False
            if source_systems is not None:
                names_multiple = reasoner.judge(
                    "Does this name more than one system?", source_systems.value)
            if not names_multiple:
                ledger.set(question.field_id, "04", "not applicable", ProvenanceState.INFERRED,
                           source="inferred from source_systems, layer 04",
                           note="only one source system named, nothing to reconcile against")
                continue
        if question.field_id == "restatement_handling":
            print()
            print(question.prompt)
            _print_choices(question.choices)
            value = ask("> ", choices=question.choices)
            value, flagged = _classify_and_reframe(ledger, reasoner, question.prompt, value, ask)
            note = "not a clear answer after two attempts, flagged for review" if flagged else ""
            if not flagged and value.strip().lower().startswith("y"):
                note = ask("  When, and who does the correcting? ")
            ledger.set(question.field_id, "04", value, ProvenanceState.STATED,
                       source="requester, layer 04", note=note)
            answers[question.field_id] = value
            continue
        answers[question.field_id] = _ask_question(ledger, question, "04", ask, reasoner)
    reflect_and_promote(ledger, reasoner, "04", [q.field_id for q in LAYER_04_QUESTIONS], ask)
    return answers


def _lock_gap_reason(vague: bool, exclusions_given: bool, confirmed: bool) -> str:
    reasons = []
    if vague:
        reasons.append("no clear, testable definition after two attempts")
    if not exclusions_given:
        reasons.append("no exclusions answer on file")
    if not confirmed:
        reasons.append("not confirmed at reflection")
    return "; ".join(reasons)


def run_layer_07(ledger: Ledger, reasoner: Reasoner, knowledge: RetainedKnowledge,
                  terms: list[str], ask=None) -> None:
    """Layer 07. Runs once per term queued (from `reasoner.extract_terms()` calls made against
    every layer up to this point), not once total. A term locks - counts as an authoritative
    definition in the technical spec - only once it clears all three: a concrete testable
    definition, an explicit exclusions answer, and reflection confirming it.
    """
    if ask is None:
        ask = _console_ask
    if not terms:
        return
    definition_q, competing_q, exclusion_q, synonym_q = LAYER_07_QUESTIONS

    for term in terms:
        print()
        print(f"Let's pin down what you mean by \"{term}\".")

        print()
        definition_prompt = definition_q.prompt.format(term=term)
        print(definition_prompt)
        value = ask("> ")
        value, vague = _classify_and_reframe(
            ledger, reasoner, definition_prompt, value, ask,
            extra_flag_question=(
                f"Is this too vague to check against an actual row of data for \"{term}\" (a "
                "boundary like 'recently' or 'engaged' with nothing concrete to test it "
                "against)?"
            ),
        )
        definition_note = "" if not vague else "no clear, testable definition after two attempts, flagged for review"
        ledger.set(f"metric_definition::{term}", "07", value, ProvenanceState.STATED,
                   source=f"requester, layer 07 ({term})", note=definition_note)

        prior_definition = knowledge.definition_for(term)
        print()
        if prior_definition is not None:
            # Per docs/interview-branching.md: retained knowledge makes this question concrete
            # - does this match what a previous requester meant by it - rather than generic.
            print(f"  A previous interview defined \"{term}\" as: {prior_definition!r}")
            print("  Does that match what you mean here?")
            competing_choices = COMPETING_DEFINITION_CHOICES_WITH_PRIOR
        else:
            print(competing_q.prompt)
            competing_choices = COMPETING_DEFINITION_CHOICES_NO_PRIOR
        _print_choices(competing_choices)
        competing_value = ask("> ", choices=competing_choices)
        ledger.set(f"competing_definition_check::{term}", "07", competing_value,
                   ProvenanceState.STATED, source=f"requester, layer 07 ({term})")

        print()
        print(exclusion_q.prompt)
        _print_choices(exclusion_q.choices)
        exclusion_value = ask("> ", choices=exclusion_q.choices)
        ledger.set(f"exclusion_filters::{term}", "07", exclusion_value, ProvenanceState.STATED,
                   source=f"requester, layer 07 ({term})")

        print()
        print(synonym_q.prompt)
        synonym_value = ask("> ")
        ledger.set(f"synonyms::{term}", "07", synonym_value, ProvenanceState.STATED,
                   source=f"requester, layer 07 ({term})")

        print()
        print(f"Here's what I've got for \"{term}\":")
        print(f"  Counts as: {value}")
        print(f"  Excludes: {exclusion_value}")
        print(f"  Also called: {synonym_value}")
        reflection_reply = ask("Does that sound right? ")
        confirmed = _is_affirmative(reflection_reply)
        exclusions_given = bool(exclusion_value.strip())
        locked = confirmed and not vague and exclusions_given
        lock_note = "" if locked else f"not locked: {_lock_gap_reason(vague, exclusions_given, confirmed)}"
        ledger.set(f"term_locked::{term}", "07", locked, ProvenanceState.STATED,
                   source=f"requester, layer 07 ({term}) reflection", note=lock_note)


def _collect_terms(reasoner: Reasoner, answers: dict[str, str], pending_terms: list[str]) -> None:
    text = " ".join(str(value) for value in answers.values() if value)
    if not text.strip():
        return
    for term in reasoner.extract_terms(text):
        if term not in pending_terms:
            pending_terms.append(term)


def run_interview(ledger: Ledger, reasoner: Reasoner, knowledge: RetainedKnowledge,
                   ask=None) -> None:
    """Runs layers 00 through 09 in order against one shared ledger, per
    docs/interview-branching.md. Owns the term queue layer 07 runs against, so cli.py only
    has to wire up the ledger, reasoner and knowledge seam and call this once.
    """
    if ask is None:
        ask = _console_ask
    pending_terms: list[str] = []

    answers = run_layer_00(ledger, reasoner, ask)
    _collect_terms(reasoner, answers, pending_terms)

    answers = run_simple_layer("01", LAYER_01_QUESTIONS, ledger, reasoner, ask)
    _collect_terms(reasoner, answers, pending_terms)

    answers = run_layer_02(ledger, reasoner, ask)
    _collect_terms(reasoner, answers, pending_terms)

    answers = run_simple_layer("03", LAYER_03_QUESTIONS, ledger, reasoner, ask)
    _collect_terms(reasoner, answers, pending_terms)

    answers = run_layer_04(ledger, reasoner, ask)
    _collect_terms(reasoner, answers, pending_terms)

    answers = run_simple_layer("05", LAYER_05_QUESTIONS, ledger, reasoner, ask)
    _collect_terms(reasoner, answers, pending_terms)

    answers = run_simple_layer("06", LAYER_06_QUESTIONS, ledger, reasoner, ask)
    _collect_terms(reasoner, answers, pending_terms)

    # One dedup pass over the whole queue, not the per-layer exact-string check
    # `_collect_terms` does while collecting. Per docs/interview-branching.md v0.2: catches
    # near-duplicates ("trends" / "product trends") and drops terms already answered by a
    # named field ("dimensions") rather than sending every literal candidate through a full
    # layer 07 pass. Guarded on a non-empty queue: an empty one means no ambiguous term
    # surfaced anywhere in the interview, so there is nothing to dedup, and calling out to the
    # reasoner anyway would be a wasted judgement call (a real `claude -p` process for
    # ClaudeCodeReasoner) for a decision with only one possible answer.
    consolidated_terms = (
        reasoner.consolidate_terms(pending_terms, ledger.known_values()) if pending_terms else []
    )
    run_layer_07(ledger, reasoner, knowledge, consolidated_terms, ask)

    run_simple_layer("08", LAYER_08_QUESTIONS, ledger, reasoner, ask)
    run_simple_layer("09", LAYER_09_QUESTIONS, ledger, reasoner, ask)
