"""The judgment interface: everywhere the back-of-house persona has to interpret free text
rather than just record it.

Per CLAUDE.md's portability rule, model provider sits behind an interface with an
implementation per environment, so the interview logic never talks to a specific model
directly. This is the seam.

Revised for e5 slice 2 (layers 01 through 09): what started as one bespoke method
(`is_solution_in_disguise`) is now a general `judge(question)` a call site can phrase however
it needs, plus `extract_terms` for layer 07's term queue. This is the shape e4 was built
against: one real model call behind `judge`, one behind `extract_terms`, rather than a growing
list of specific methods. Decided while adding the layers that need more than one kind of
judgment call, rather than waiting for e4 to force the refactor.

Two implementations now. StubReasoner asks a human to make the call in the terminal, which is
what made the branching logic in engine/interview.py real and testable before e4 existed.
ClaudeCodeReasoner is e4 itself (decided in docs/architecture-decisions.md to be a Claude Code
CLI subprocess call, not a direct API call): see its docstring below for the reasoning and the
implementation note in that document for what's actually been verified.
"""

from abc import ABC, abstractmethod
import json
import subprocess


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


class ClaudeCliError(RuntimeError):
    """The claude CLI subprocess failed, or returned something the reasoner couldn't parse
    into an answer. Raised rather than swallowed: a judgement call this tool can't actually
    get an honest answer to must stop the interview, not silently guess one. Guessing is
    exactly what CLAUDE.md's claim-integrity rule rules out."""


class ClaudeCodeReasoner(Reasoner):
    """e4. Calls the locally installed Claude Code CLI in non-interactive mode
    (`claude -p "<prompt>"`) for every judgement call, instead of asking a person at the
    keyboard. Decided in docs/architecture-decisions.md: this runs against the Claude Pro
    subscription's usage pool rather than metered API billing, which is why it shells out to
    the CLI rather than calling the Anthropic API directly.

    Each call is a fresh, tool-free, unsaved one-shot: `--tools ""` because a yes/no judgement,
    a term list or a paraphrase never needs to read a file or run a command, and
    `--no-session-persistence` because a full interview makes dozens of these calls and none of
    them is a conversation worth resuming later. `--bare` was considered and rejected for the
    same reason as a direct API call: it forces API-key-only auth and never reads the keychain,
    which would defeat the entire point of shelling out to the CLI instead of calling the API.
    """

    def __init__(self, timeout_seconds: int = 60):
        self._timeout_seconds = timeout_seconds

    def _call(self, prompt: str) -> str:
        try:
            completed = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "json", "--tools", "",
                 "--no-session-persistence"],
                capture_output=True, text=True, timeout=self._timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise ClaudeCliError(
                "the `claude` CLI isn't on PATH - e4 needs it installed and logged in"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ClaudeCliError(
                f"claude -p didn't respond within {self._timeout_seconds}s"
            ) from exc

        # A non-zero exit and a JSON payload aren't mutually exclusive: `claude -p` exits 1 for
        # "not logged in" while still writing valid JSON with is_error and a plain-English
        # result to stdout. Parsing first and only falling back to the raw exit code when that
        # fails is what actually surfaces that message instead of a wall of JSON.
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            if completed.returncode != 0:
                raise ClaudeCliError(
                    f"claude -p exited {completed.returncode}: "
                    f"{completed.stderr.strip() or completed.stdout.strip()}"
                ) from exc
            raise ClaudeCliError(
                f"claude -p returned output that wasn't valid JSON: {completed.stdout!r}"
            ) from exc

        if payload.get("is_error"):
            raise ClaudeCliError(f"claude -p reported an error: {payload.get('result')!r}")
        if completed.returncode != 0:
            raise ClaudeCliError(
                f"claude -p exited {completed.returncode}: {payload.get('result')!r}"
            )

        result = payload.get("result")
        if not isinstance(result, str):
            raise ClaudeCliError(f"claude -p's JSON had no usable 'result' field: {payload!r}")
        return result.strip()

    def judge(self, question: str, context: str) -> bool:
        prompt = (
            "You are making a single yes/no judgement call for a requirements-gathering tool.\n"
            f"Question: {question}\n"
            f"Text to judge: {context!r}\n"
            "Reply with exactly one word, yes or no. Nothing else."
        )
        return self._call(prompt).lower().startswith("y")

    def extract_terms(self, text: str) -> list[str]:
        prompt = (
            "You are scanning an answer from a requirements interview for ambiguous business "
            "terms: a status, a category or a metric name that different people could "
            "reasonably define differently, and that would need pinning down before it's safe "
            "to build against. Ignore generic words and anything already concrete.\n"
            f"Text: {text!r}\n"
            "Reply with the exact terms, comma-separated, using the words as they appear in "
            "the text. If there are none, reply with exactly: none. Nothing else, no "
            "explanation."
        )
        reply = self._call(prompt)
        if reply.strip().lower() == "none":
            return []
        return [t.strip() for t in reply.split(",") if t.strip()]

    def summarise_for_reflection(self, answers: dict[str, str]) -> str:
        fields_text = "\n".join(
            f"- {field_id.replace('_', ' ')}: {value}" for field_id, value in answers.items()
        )
        prompt = (
            "You are the business-analyst voice of a requirements-gathering tool, reflecting "
            "understanding back to the person who just answered these questions so they can "
            "correct it before anything is built. Paraphrase in plain, warm language, using "
            "their own words rather than technical vocabulary - never mention grain, "
            "cardinality, or any other technical term. Open with exactly the line \"Here's "
            "what I've understood so far:\" then one short line per point below it. No "
            "preamble, no explanation of why you're asking, just the reflection.\n\n"
            f"{fields_text}"
        )
        return self._call(prompt)
