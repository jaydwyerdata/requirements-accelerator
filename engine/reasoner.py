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

Two more methods, `reframe` and `consolidate_terms`, were added once e4 met a real interview
(docs/architecture-decisions.md's "reframe capability" revision, docs/interview-branching.md
v0.2). Neither guesses at content the requester hasn't given: `reframe` rephrases a question
using only what is already on the ledger, `consolidate_terms` merges and filters a candidate list
using only the terms and field values it is handed, the same claim-integrity boundary `judge` and
`extract_terms` already hold to.
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

    @abstractmethod
    def reframe(self, question: str, prior_reply: str, context: dict[str, str]) -> str:
        """A different way into a question the requester didn't actually answer: a clarifying
        question back, a don't-know, or a blank. `question` is the plain-language prompt as
        asked, `prior_reply` is what came back, `context` is everything already on the ledger
        (field_id to value) to ground the new attempt in what the requester has actually said,
        never in an invented example. Returns the rephrased question to ask, not an answer."""

    @abstractmethod
    def consolidate_terms(self, candidate_terms: list[str], known_fields: dict[str, str]) -> list[str]:
        """The layer 07 term queue, deduplicated and filtered, once per interview rather than
        once per layer. `candidate_terms` is everything `extract_terms` has queued so far, in
        the order collected. `known_fields` is the ledger's field values up to this point, so a
        term already fully answered by a structured field (the interview's own vocabulary, not
        an ambiguous business concept) can be dropped rather than sent through a full layer 07
        pass. Merges near-duplicates a string match would miss. Returns the final list, in a
        sensible order; never adds a term that wasn't in `candidate_terms`."""

    @abstractmethod
    def find_conceptual_overlaps(self, definitions: dict[str, str]) -> list[list[str]]:
        """e8 Phase B (docs/architecture-decisions.md's "e8 scope" entry): given every locked
        term on file and its definition, which two or more describe the same underlying
        concept even though different requesters used different words for it (the "active
        customer" / "engaged member" case retained knowledge's exact-string matching can never
        catch on its own). Not called per interview: engine/overlap.py runs this once, in a
        planning-time report, never during a live interview. Returns groups of term names, each
        group two or more terms from `definitions`' own keys; empty list if nothing groups.
        A flag to review, exactly like retained knowledge's own competing-definition check,
        never an asserted fact, and never a term that wasn't a key of `definitions`."""


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

    def reframe(self, question: str, prior_reply: str, context: dict[str, str]) -> str:
        print()
        print("  [stub reasoner] That wasn't a clear answer. Question as asked:")
        print(f"  {question!r}")
        print(f"  Reply received: {prior_reply!r}")
        if context:
            print("  Known so far:")
            for field_id, value in context.items():
                print(f"    - {field_id.replace('_', ' ')}: {value}")
        return input("  Type a different way to ask this: ")

    def consolidate_terms(self, candidate_terms: list[str], known_fields: dict[str, str]) -> list[str]:
        print()
        print("  [stub reasoner] Layer 07's candidate term queue, before dedup:")
        print(f"  {candidate_terms!r}")
        print("  Known fields, for spotting terms already covered structurally:")
        for field_id, value in known_fields.items():
            print(f"    - {field_id.replace('_', ' ')}: {value}")
        reply = input("  Type the final list, comma-separated, or press enter to keep as-is: ")
        if not reply.strip():
            return candidate_terms
        return [t.strip() for t in reply.split(",") if t.strip()]

    def find_conceptual_overlaps(self, definitions: dict[str, str]) -> list[list[str]]:
        print()
        print("  [stub reasoner] Every locked term on file, looking for the same idea under")
        print("  different words:")
        for term, definition in definitions.items():
            print(f"    - {term!r}: {definition}")
        print("  Type one group per line (comma-separated term names), blank line to finish:")
        groups = []
        while True:
            line = input("  > ")
            if not line.strip():
                break
            terms = [t.strip() for t in line.split(",") if t.strip()]
            if len(terms) >= 2:
                groups.append(terms)
        return groups


class _PromptedReasoner(Reasoner):
    """Shared prompt logic for any reasoner that answers by sending one text prompt and getting
    one text reply back, regardless of transport. `ClaudeCodeReasoner` (e4, a CLI subprocess)
    and `CortexReasoner` (engine/cortex_reasoner.py, the a3 spike: an AI_COMPLETE SQL call
    through the active Snowpark session) are both this shape: only `_call` differs, every
    prompt and every bit of parsing on what comes back is identical. Staying identical is the
    point, not an accident, it's what makes the spike's comparison meaningful: if the same
    prompts against a different model produce sensibly similar judgement calls, that's real
    signal about the swap, not an artifact of also having rewritten the prompts.

    Subclasses implement only `_call(prompt) -> str`. Extracted from what was, before the a3
    spike, `ClaudeCodeReasoner`'s only reasoner implementation; behaviour is unchanged."""

    def _call(self, prompt: str) -> str:
        raise NotImplementedError

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

    def reframe(self, question: str, prior_reply: str, context: dict[str, str]) -> str:
        context_text = "\n".join(
            f"- {field_id.replace('_', ' ')}: {value}" for field_id, value in context.items()
        ) or "(nothing recorded yet)"
        prompt = (
            "You are the business-analyst voice of a requirements-gathering tool. The person "
            "you're interviewing did not give a usable answer to the question below: they asked "
            "what you meant, said they don't know, or left it effectively blank. Ask the same "
            "thing again, in a genuinely different way, plain language, no technical vocabulary.\n\n"
            "Strict rule, more important than making the question sound concrete: you may only "
            "reuse words, phrases, names, categories or numbers that appear verbatim in 'Their "
            "reply' or in 'What's already known from this interview' below. Do not invent, "
            "guess, or extrapolate a plausible-sounding specific example, product name, "
            "category, or number, even one that fits the domain and even if it would make the "
            "question read better. 'Ground it in what they've already told you' means quoting "
            "or directly reusing their own words back to them, never synthesising a new "
            "specific that sounds like something they might have meant. If there isn't enough "
            "already stated to build a concrete worked example from, ask a plainer, more "
            "general version of the question instead of reaching for an invented one. Reply "
            "with only the rephrased question, nothing else, no preamble.\n\n"
            f"Original question: {question}\n"
            f"Their reply: {prior_reply!r}\n"
            f"What's already known from this interview:\n{context_text}"
        )
        return self._call(prompt)

    def consolidate_terms(self, candidate_terms: list[str], known_fields: dict[str, str]) -> list[str]:
        if not candidate_terms:
            return []
        fields_text = "\n".join(
            f"- {field_id.replace('_', ' ')}: {value}" for field_id, value in known_fields.items()
        ) or "(none)"
        prompt = (
            "You are reviewing a queue of candidate business terms a requirements interview has "
            "flagged as ambiguous, each one needs its own definition question later unless it "
            "can be dropped or merged now. Two things to do. First, merge near-duplicates, "
            "different wordings of the same underlying concept ('trends' and 'product trends', "
            "'opportunities' and 'growth opportunities'), keeping one term per concept, worded as "
            "it appears most naturally in the list. Second, drop any term that is already fully "
            "answered by one of the known fields below rather than being a genuine ambiguous "
            "business concept, a generic time reference already captured elsewhere, or the "
            "interview's own structural vocabulary rather than something two departments could "
            "reasonably define differently. Never add a term that isn't already in the "
            "candidate list.\n\n"
            f"Candidate terms: {', '.join(candidate_terms)}\n"
            f"Known fields from this interview so far:\n{fields_text}\n\n"
            "Reply with the final list, comma-separated, using the wording as it appears in the "
            "candidate list. If none survive, reply with exactly: none. Nothing else, no "
            "explanation."
        )
        reply = self._call(prompt)
        if reply.strip().lower() == "none":
            return []
        return [t.strip() for t in reply.split(",") if t.strip()]

    def find_conceptual_overlaps(self, definitions: dict[str, str]) -> list[list[str]]:
        if len(definitions) < 2:
            return []
        definitions_text = "\n".join(
            f'- "{term}": {definition}' for term, definition in definitions.items()
        )
        prompt = (
            "You are reviewing every business term a requirements-gathering tool has on file, "
            "each with the definition its own requester gave it, looking for terms that describe "
            "the same real-world concept even though different requesters used different words "
            "for it. This is not about shared words or topic, it's about whether two definitions "
            "genuinely describe the same underlying thing a business would recognise as one "
            "idea. Only group terms whose definitions actually describe the same concept; a "
            "vague thematic similarity is not enough. Never invent a term that isn't in the "
            "list below, and never group a term on its own.\n\n"
            f"{definitions_text}\n\n"
            "Reply with one group per line, each line the exact term names from the list above "
            "that belong together, comma-separated, only for groups of two or more terms. If "
            "nothing groups, reply with exactly: none. Nothing else, no explanation."
        )
        reply = self._call(prompt)
        if reply.strip().lower() == "none":
            return []
        groups = []
        for line in reply.splitlines():
            # Defensive, not just prompt-level: a term the model names that isn't actually one
            # of the terms it was given would be exactly the kind of invented connection
            # CLAUDE.md's claim-integrity rule rules out, so it's dropped here rather than
            # trusted the way consolidate_terms currently trusts its own prompt alone.
            terms = [t.strip() for t in line.split(",") if t.strip() and t.strip() in definitions]
            if len(terms) >= 2:
                groups.append(terms)
        return groups


class ClaudeCliError(RuntimeError):
    """The claude CLI subprocess failed, or returned something the reasoner couldn't parse
    into an answer. Raised rather than swallowed: a judgement call this tool can't actually
    get an honest answer to must stop the interview, not silently guess one. Guessing is
    exactly what CLAUDE.md's claim-integrity rule rules out."""


class ClaudeCodeReasoner(_PromptedReasoner):
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

    # judge, extract_terms, summarise_for_reflection, reframe, consolidate_terms and
    # find_conceptual_overlaps are all inherited from _PromptedReasoner unchanged: only the
    # transport above (_call) is specific to shelling out to the CLI.
