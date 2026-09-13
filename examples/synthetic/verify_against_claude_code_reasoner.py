"""Runs interview 1 of the synthetic dataset (Store Operations Manager, "stockout") against the
real ClaudeCodeReasoner (e4), not StubReasoner, to check the scripted requester answers hold up
against an actual model's judgement calls, not just a hand-authored "n"/"y" for every check.

Chosen deliberately as the one to verify for real: it was designed as a clean pass with no
redirect, both dimensions and multiple systems named, so a real model's judge() calls should
agree with the branch this dataset assumed - this is the safest place to first point a live model
at scripted data, before trusting the rest of the dataset's branch assumptions unverified.

Unlike the StubReasoner scripts, this cannot supply one flat RESPONSES list in call order: with a
real reasoner, extract_terms(), consolidate_terms(), judge() and reframe() all go straight to the
model, not through input(), so there is no fixed number of prompts to pre-count, and the model
decides for itself which terms to queue for layer 07 (it might not be exactly "stockout"). Instead
this supplies a custom `ask` that matches the actual question text against the fixed prompts in
engine/protocol.py. Most call sites in engine/interview.py hand `ask()` nothing more descriptive
than the literal "> " input marker, since the real question was already printed separately just
before, so this wraps stdout to capture what was printed since the previous ask() call and
matches against that instead of against `ask()`'s own argument. Every question is static text
except layer 07's definition question, matched by its "When you say" fragment and answered
on-topic regardless of the exact term the model chose to extract. Anything still unrecognised,
most likely a live reframe in the model's own words, gets a plain, honest, on-topic fallback
answer and is flagged clearly in the summary at the end, rather than crashing or silently
answering the wrong question with a mismatched reply.

Needs the `claude` CLI installed and logged in (same requirement as cli.py itself). Costs real
Claude Pro usage: roughly 25-30 separate `claude -p` calls, one per judgement or extraction the
interview makes, each a fresh unsaved one-shot per ClaudeCodeReasoner's own docstring.
"""

import sys

from engine.ledger import Ledger
from engine.knowledge import NoRetainedKnowledge
from engine.reasoner import ClaudeCodeReasoner
from engine.interview import run_interview
from engine.render import render_business_ask, render_technical_spec

# Fixed-text prompts only: every LAYER_NN_QUESTIONS prompt in engine/protocol.py except layer
# 07's definition question, which is formatted per-term and handled separately below.
ANSWERS = {
    "What's happening today that shouldn't be?":
        "Our best-selling packs and boots sell out at individual stores mid-week, but nobody "
        "notices until a customer walks out empty-handed, and by the time head office reacts "
        "the replenishment truck has already left without the extra units.",
    "Walk me through what you do today when you need this.":
        "Store leads check the shelf by eye, and if they remember, they email the DC to ask for "
        "a rush top-up, but there's no report that flags it before it happens.",
    "How often does this bite you?": "weekly",
    "Who else deals with this same problem?":
        "Every store lead, and the regional merchandising team when a stockout shows up in "
        "weekly sales.",
    "If this were fixed, what would you do differently on Monday?":
        "I'd action a rush replenishment before the shelf actually goes empty, not after.",
    "How would you know it worked?":
        "I can see, every morning, which SKUs at which stores are about to run out.",
    "What are you actually asking: how much, how many, which ones, or has something changed?":
        "which ones",
    "Do you check this on a schedule, or go looking when something feels wrong?":
        "on a schedule",
    "Who else will look at this, and are they asking the same question?":
        "Store leads and the regional merchandising team, and yes, same question for both.",
    "If I put this on one slide, what's the number in the middle?":
        "Number of SKUs at risk of a stockout in the next few days.",
    "What would you want to break that number down by?": "store, product",
    "Would you ever click a total to see what's inside it?": "yes",
    "Is there anything you'd compare it against: last year, a target, another team?": "last year",
    "If I handed you a spreadsheet of this, what would one row be: one customer, one order, one "
    "day?": "one SKU at one store on one day",
    "Could that ever show up more than once in the spreadsheet?": "no",
    "Could one of these ever belong to more than one group at the same time?": "no",
    "Where do you look today when you need this?":
        "The point-of-sale system for what's sold, and the warehouse management system for "
        "what's actually left in the stockroom.",
    "If two systems showed different numbers, which would you believe?":
        "The warehouse management system, since the POS only knows what's sold, not what's "
        "physically still on the shelf.",
    "Who types this in, and when in the process?":
        "The stockroom count updates overnight after the evening cycle count.",
    "Does anyone go back and correct it after the fact?": "yes",
    "  When, and who does the correcting? ":
        "Store leads correct a miscount the next morning if the overnight number looks wrong.",
    "Which teams would notice if this stopped updating?":
        "Regional merchandising and the replenishment planning team.",
    "Who do you go to when the numbers look wrong?":
        "The regional merchandising lead, people ask her first.",
    "If two people disagreed about what this should say, who'd settle it?":
        "Regional merchandising, they own the replenishment call.",
    "Once you've got this, where does it go next?":
        "Into the weekly replenishment planning meeting.",
    "Which process stalls if this is late or wrong?": "Replenishment planning stalls without it.",
    "Who'd need to sign off on someone new seeing this?": "The regional merchandising lead.",
    "How fresh does this need to be: good enough this morning, or right this second?":
        "next morning",
    "Is there a moment when this matters most: month end, Monday morning?": "Monday morning",
    "How far back do you need to see?": "last two to three years",
    "Do you need to see what it looked like back then, or only how it looks now?":
        "only how it looks now",
    "Should everyone looking at this see all of it, or only their own part?":
        "everyone sees all of it",
    "Is any of this personal or sensitive: names, pay, anything you'd not want widely shared?":
        "no",
    "Who's likely to ask for this next?":
        "Probably the DC replenishment planners directly, once this proves out.",
    "Roughly how much data is this: hundreds, thousands, or millions of records?": "thousands",
    "Is that number growing fast?": "no",

    # Layer 07's fixed-text questions (only the definition question is per-term formatted).
    "Would the finance team define that the same way?": "not a concern",
    "Is there anything that shouldn't count: tests, internal accounts, cancellations?": "none",
    "What do you call this? Does anyone call it something else?":
        "Some people just call it a 'stock risk' or a 'run-out'.",

    # Layer 00's own bespoke reflection line and the shared reflect_and_promote line.
    "Anything you'd change about that? Enter to move on, or type a correction: ": "",
    "Does that sound right? Enter to move on, 'yes' to confirm, or type a correction: ": "yes",
    "Does that sound right? ": "yes",
}

STOCKOUT_DEFINITION = (
    "It counts once the stockroom's on-hand count for that item drops below what we'd expect to "
    "sell before the next scheduled delivery arrives, not simply hitting zero."
)

_unmapped_prompts: list[str] = []


class _CapturingStdout:
    """Wraps real stdout so every question and choices hint the engine prints (engine/
    interview.py calls the bare `print()` builtin directly, not something this script can hand
    an argument to) is still visible on the terminal, while also being captured so `ask()` below
    can tell which question is actually being asked. Most call sites hand `ask()` nothing more
    descriptive than the literal "> " input marker, so the question text itself only exists in
    what was printed just before, never in ask()'s own argument.
    """

    def __init__(self, real):
        self._real = real
        self._buffer: list[str] = []

    def write(self, text: str) -> None:
        self._real.write(text)
        self._buffer.append(text)

    def flush(self) -> None:
        self._real.flush()

    def pop_since_last_ask(self) -> str:
        text = "".join(self._buffer)
        self._buffer = []
        return text


def _make_ask(stdout: _CapturingStdout):
    def ask(prompt: str, choices=None) -> str:
        # The real question text is almost always in what was printed since the last ask() call,
        # not in `prompt` itself (usually just "> "); the one exception is a bespoke follow-up
        # question passed straight as `prompt` with no separate print (layer 04's restatement
        # follow-up), so both are checked together.
        haystack = stdout.pop_since_last_ask() + "\n" + prompt

        answer = None
        for key, scripted in ANSWERS.items():
            if key in haystack:
                answer = scripted
                break
        if answer is None and 'When you say "' in haystack:
            # Layer 07's definition question, per term. Answered on-topic regardless of which
            # exact term the model chose to queue, since this interview is about one underlying
            # concept.
            answer = STOCKOUT_DEFINITION
        if answer is None:
            # Genuinely unrecognised: almost certainly a live reframe in the model's own words
            # that doesn't share text with anything scripted. Flag it loudly rather than guess
            # silently, and give a plain, honest, on-topic fallback so the interview can finish.
            _unmapped_prompts.append(haystack.strip())
            answer = (
                "To be concrete: a SKU running out on the shelf before the next scheduled "
                "delivery arrives."
            )

        print(f"> {answer}")
        return answer

    return ask


if __name__ == "__main__":
    real_stdout = sys.stdout
    capturing = _CapturingStdout(real_stdout)
    sys.stdout = capturing
    try:
        ledger = Ledger()
        reasoner = ClaudeCodeReasoner(timeout_seconds=150)
        knowledge = NoRetainedKnowledge()
        run_interview(ledger, reasoner, knowledge, ask=_make_ask(capturing))
    finally:
        sys.stdout = real_stdout

    print()
    print("=" * 60)
    print()
    if _unmapped_prompts:
        print(f"NOTE: {len(_unmapped_prompts)} prompt(s) didn't match a scripted answer "
              "(most likely a live reframe the real model triggered):")
        for p in _unmapped_prompts:
            print(f"  - {p!r}")
        print()
    print(render_business_ask(ledger))
    print()
    print(render_technical_spec(ledger))
