"""A regression guard for the real ClaudeCodeReasoner.reframe() prompt, added after a real run
against the live model (see docs/architecture-decisions.md's "Real ClaudeCodeReasoner run
against synthetic interview 1") surfaced it inventing a detail the requester never gave, a
direct miss against its own "never invent" instruction.

Mocks `subprocess.run` since ClaudeCodeReasoner shells out to a real `claude` CLI process; this
cannot prove a live model actually honours the instruction (only a real run like
examples/synthetic/verify_against_claude_code_reasoner.py can do that), but it does prove the
strengthened wording stays in the prompt going forward, rather than someone editing this method
later and quietly dropping the constraint that was tightened here.
"""

import json
import unittest
from unittest.mock import patch, MagicMock

from engine.reasoner import ClaudeCodeReasoner


def _fake_completed_process(result_text: str):
    completed = MagicMock()
    completed.returncode = 0
    completed.stdout = json.dumps({"is_error": False, "result": result_text})
    completed.stderr = ""
    return completed


class ReframePromptTest(unittest.TestCase):
    def test_prompt_forbids_inventing_specifics_not_in_context(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _fake_completed_process(
                "Roughly how many of these come up in a typical week?"
            )
            ClaudeCodeReasoner().reframe(
                question="What are you actually asking: how much, how many, which ones, or has "
                          "something changed?",
                prior_reply="which ones",
                context={"problem_statement": "Packs and boots sell out mid-week."},
            )

        self.assertEqual(mock_run.call_count, 1)
        prompt = mock_run.call_args[0][0][2]  # ["claude", "-p", <prompt>, ...]

        self.assertIn("only reuse words, phrases, names, categories or numbers that appear "
                      "verbatim", prompt)
        self.assertIn("Do not invent, guess, or extrapolate a plausible-sounding specific "
                      "example", prompt)
        self.assertIn("ask a plainer, more general version of the question instead of reaching "
                      "for an invented one", prompt)

    def test_reframe_still_returns_the_models_rephrased_question(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _fake_completed_process("A plainer version of the question.")
            result = ClaudeCodeReasoner().reframe(
                question="Original question", prior_reply="not sure", context={},
            )
        self.assertEqual(result, "A plainer version of the question.")


if __name__ == "__main__":
    unittest.main()
