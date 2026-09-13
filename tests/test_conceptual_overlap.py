"""e8 Phase B: ClaudeCodeReasoner.find_conceptual_overlaps(). Mocks `subprocess.run`, same
approach as tests/test_reframe_prompt.py, since this shells out to a real `claude` CLI process.
Proves the prompt asks for the right thing and, more importantly, that a hallucinated term the
model names but wasn't actually given gets dropped rather than trusted, the defensive check
consolidate_terms doesn't currently have. Cannot prove a live model's grouping judgement is
correct, only a real run can do that.
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


class FindConceptualOverlapsTest(unittest.TestCase):
    def test_fewer_than_two_definitions_never_calls_the_model(self):
        with patch("subprocess.run") as mock_run:
            result = ClaudeCodeReasoner().find_conceptual_overlaps({"stockout": "..."})
        mock_run.assert_not_called()
        self.assertEqual(result, [])

    def test_prompt_forbids_inventing_a_term_and_forbids_shared_topic_alone(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _fake_completed_process("none")
            ClaudeCodeReasoner().find_conceptual_overlaps({
                "active customer": "ordered on any channel in the last 90 days",
                "engaged member": "opened a loyalty offer in the last 60 days",
            })
        prompt = mock_run.call_args[0][0][2]
        self.assertIn("Never invent a term that isn't in the", prompt)
        self.assertIn("vague thematic similarity is not enough", prompt)
        self.assertIn("active customer", prompt)
        self.assertIn("engaged member", prompt)

    def test_none_reply_returns_empty_list(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _fake_completed_process("none")
            result = ClaudeCodeReasoner().find_conceptual_overlaps({
                "active customer": "...", "on-time delivery": "...",
            })
        self.assertEqual(result, [])

    def test_valid_group_is_returned(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _fake_completed_process("active customer, engaged member")
            result = ClaudeCodeReasoner().find_conceptual_overlaps({
                "active customer": "...", "engaged member": "...", "stockout": "...",
            })
        self.assertEqual(result, [["active customer", "engaged member"]])

    def test_hallucinated_term_not_in_input_is_dropped(self):
        with patch("subprocess.run") as mock_run:
            # "loyal shopper" was never in the definitions dict handed to the model.
            mock_run.return_value = _fake_completed_process(
                "active customer, engaged member, loyal shopper"
            )
            result = ClaudeCodeReasoner().find_conceptual_overlaps({
                "active customer": "...", "engaged member": "...",
            })
        self.assertEqual(result, [["active customer", "engaged member"]])

    def test_group_that_drops_to_one_real_term_is_discarded(self):
        with patch("subprocess.run") as mock_run:
            # Only "stockout" was real; the rest of the line gets filtered away, leaving one.
            mock_run.return_value = _fake_completed_process("stockout, not a real term")
            result = ClaudeCodeReasoner().find_conceptual_overlaps({
                "stockout": "...", "active customer": "...",
            })
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
