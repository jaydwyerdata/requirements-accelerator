"""The judgment interface: everywhere the back-of-house persona has to interpret free text
rather than just record it.

Per CLAUDE.md's portability rule, model provider sits behind an interface with an
implementation per environment, so the interview logic never talks to a specific model
directly. This is the seam.

StubReasoner is the v1 implementation: no model wired up yet (that's e4). It asks a human
to make the call in the terminal instead, so the branching logic in engine/interview.py is
real and testable now rather than faked. Swapping in a real model later means writing a
new class here, nothing else changes.
"""

from abc import ABC, abstractmethod


class Reasoner(ABC):
    @abstractmethod
    def is_solution_in_disguise(self, answer: str) -> bool:
        """True if the answer describes a proposed fix rather than the underlying problem."""

    @abstractmethod
    def summarise_for_reflection(self, answers: dict[str, str]) -> str:
        """A short paraphrase of what was understood, in the requester's own vocabulary,
        to reflect back at a layer boundary."""


class StubReasoner(Reasoner):
    """No model wired up. Asks a person at the keyboard to make the call instead."""

    def is_solution_in_disguise(self, answer: str) -> bool:
        print()
        print("  [stub reasoner] No model wired up yet (that's e4). Judging this one by hand:")
        print(f"  Answer given: {answer!r}")
        reply = input("  Does this read as a proposed solution rather than the problem itself? [y/N] ")
        return reply.strip().lower().startswith("y")

    def summarise_for_reflection(self, answers: dict[str, str]) -> str:
        lines = ["Here's what I've understood so far:"]
        for field_id, value in answers.items():
            lines.append(f"  - {field_id.replace('_', ' ')}: {value}")
        return "\n".join(lines)
