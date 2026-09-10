"""Layer 00 of the Coaxing Protocol, encoded as data.

Question text is copied verbatim from docs/coaxing-protocol.md. This module is the only
place that text should live in code; the interview engine just walks the list.
"""

from dataclasses import dataclass, field


@dataclass
class Question:
    field_id: str
    prompt: str
    layer: str = "00"
    choices: list[str] | None = None  # set for a banded question
    gated: bool = False  # True if this answer runs the redirect check


LAYER_00_QUESTIONS = [
    Question(
        field_id="problem_statement",
        prompt="What's happening today that shouldn't be?",
        gated=True,
    ),
    Question(
        field_id="current_process",
        prompt="Walk me through what you do today when you need this.",
    ),
    Question(
        field_id="frequency",
        prompt="How often does this bite you?",
        choices=["daily", "weekly", "monthly", "rarely"],
    ),
    Question(
        field_id="blast_radius",
        prompt="And who else does it bite?",
    ),
    Question(
        field_id="activation_use_case",
        prompt="If this were fixed, what would you do differently on Monday?",
    ),
    Question(
        field_id="acceptance_criteria",
        prompt="How would you know it worked?",
    ),
]

MAX_LAYER_00_ATTEMPTS = 2
