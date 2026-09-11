"""The judgment interface: everywhere the back-of-house persona has to interpret free text
rather than just record it.

Per CLAUDE.md's portability rule, model provider sits behind an interface with an
implementation per environment, so the interview logic never talks to a specific model
directly. This is the seam.

Revised for e5 slice 2 (layers 01 through 09): what started as one bespoke method
(`is_solution_in_disguise`) is now a general `judge(question)` a call site can phrase however
it needs, plus `extract_terms` for layer 07's term queue. This is the shape e4 will actually
implement against: one real model call behind `judge`, one behind `extract_terms`, rather than
a growing list of specific methods. Decided now, while adding the layers that need more than
one kind of judgment call, rather than waiting for e4 to force the refactor.

StubReasoner is still the only implementation: no model wired up (e4, decided in
docs/architecture-decisions.md to be a Claude Code CLI subprocess call, not yet built). It asks
a human to make the call in the terminal instead, so the branching logic in
engine/interview.py is real and testable now rather than faked.
"""

from abc import ABC, abstractmethod


class Reasoner(ABC):
    @abstractmethod
    def judge(self, question: str, context: str) -> bool:
        """Ask a yes/no judgement about the given context. `question` is what's being asked
        of it, `context` is the answer or text the judgement is about."""

    @abstractmethod
    def extract_terms(self, text: str) -> list[str]:
        """Ambiguous business terms in this text that layer 07 should define. Empty list if
        none. Never guesses at a definition, only names candidates for the interview to ask
        about later."""

    @abstractmethod
    def summarise_for_reflection(self, answers: dict[str, str]) -> str:
        """A short paraphrase of what was understood, in the requester's own vocabulary,
        to reflect back at a layer boundary."""


class StubReasoner(Reasoner):
    """No model wired up. Asks a person at the keyboard to make the call instead."""

    def judge(self, question: str, context: str) -> bool:
        print()
        print("  [stub reasoner] No model wired up yet (that's e4). Judging this one by hand:")
        print(f"  {context!r}")
        reply = input(f"  {question} [y/N] ")
        return reply.strip().lower().startswith("y")

    def extract_terms(self, text: str) -> list[str]:
        print()
        print("  [stub reasoner] Any business terms here that need pinning down later?")
        print(f"  {text!r}")
        reply = input("  Type any, comma-separated, or press enter for none: ")
        return [t.strip() for t in reply.split(",") if t.strip()]

    def summarise_for_reflection(self, answers: dict[str, str]) -> str:
        lines = ["Here's what I've understood so far:"]
        for field_id, value in answers.items():
            lines.append(f"  - {field_id.replace('_', ' ')}: {value}")
        return "\n".join(lines)
