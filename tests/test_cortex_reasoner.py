"""a3 spike: engine/cortex_reasoner.py's CortexReasoner. Snowpark isn't installed in this
environment, deliberately: CLAUDE.md's dependencies-stay-short rule, and the whole reason
cortex_reasoner.py keeps that import scoped to itself rather than engine/reasoner.py (see both
modules' docstrings). So this fakes snowflake.snowpark.context.get_active_session via
sys.modules rather than pulling in the real package.

Proves the calling convention (bound SQL parameters, not string interpolation; how the reply
column is read back) and that CortexReasoner shares every prompt with ClaudeCodeReasoner via
_PromptedReasoner, not that a live Cortex call actually behaves sensibly. Only running this for
real against Streamlit in Snowflake can prove that, which is the point of the spike itself.
"""

import sys
import types
import unittest
from unittest.mock import MagicMock


def _install_fake_snowpark(session):
    """Registers a minimal fake snowflake.snowpark.context module in sys.modules so
    `from snowflake.snowpark.context import get_active_session` succeeds with no real package
    installed. get_active_session() just returns the given fake session."""
    fake_snowflake = types.ModuleType("snowflake")
    fake_snowpark = types.ModuleType("snowflake.snowpark")
    fake_context = types.ModuleType("snowflake.snowpark.context")
    fake_context.get_active_session = lambda: session
    fake_snowflake.snowpark = fake_snowpark
    fake_snowpark.context = fake_context
    sys.modules["snowflake"] = fake_snowflake
    sys.modules["snowflake.snowpark"] = fake_snowpark
    sys.modules["snowflake.snowpark.context"] = fake_context


class CortexReasonerTest(unittest.TestCase):
    def setUp(self):
        self._fake_session = MagicMock()
        _install_fake_snowpark(self._fake_session)

    def tearDown(self):
        for name in ("snowflake", "snowflake.snowpark", "snowflake.snowpark.context"):
            sys.modules.pop(name, None)

    def _make_reasoner(self, reply: str):
        from engine.cortex_reasoner import CortexReasoner
        self._fake_session.sql.return_value.collect.return_value = [{"RESPONSE": reply}]
        return CortexReasoner(model="claude-sonnet-5")

    def test_call_uses_ai_complete_with_bound_parameters_not_string_interpolation(self):
        reasoner = self._make_reasoner("yes")
        reasoner.judge("Is this a solution in disguise?", "some free text with ' a quote")
        args, kwargs = self._fake_session.sql.call_args
        self.assertIn("AI_COMPLETE(?, ?)", args[0])
        self.assertEqual(kwargs["params"][0], "claude-sonnet-5")
        self.assertIn("some free text with ' a quote", kwargs["params"][1])

    def test_reply_parsed_and_stripped_from_response_column(self):
        reasoner = self._make_reasoner("  active customer, engaged member  ")
        self.assertEqual(reasoner._call("anything"), "active customer, engaged member")

    def test_a_different_model_name_is_actually_used(self):
        from engine.cortex_reasoner import CortexReasoner
        self._fake_session.sql.return_value.collect.return_value = [{"RESPONSE": "yes"}]
        reasoner = CortexReasoner(model="llama3.3-70b")
        reasoner._call("anything")
        _, kwargs = self._fake_session.sql.call_args
        self.assertEqual(kwargs["params"][0], "llama3.3-70b")

    def test_shares_every_prompt_with_claude_code_reasoner(self):
        # Both extend _PromptedReasoner and only override __init__ and _call; this identity
        # is what makes the spike's comparison meaningful, see _PromptedReasoner's docstring
        # in engine/reasoner.py.
        from engine.cortex_reasoner import CortexReasoner
        from engine.reasoner import ClaudeCodeReasoner, _PromptedReasoner
        self.assertTrue(issubclass(CortexReasoner, _PromptedReasoner))
        self.assertTrue(issubclass(ClaudeCodeReasoner, _PromptedReasoner))
        for method in ("judge", "extract_terms", "summarise_for_reflection", "reframe",
                       "consolidate_terms", "find_conceptual_overlaps"):
            self.assertIs(getattr(CortexReasoner, method), getattr(_PromptedReasoner, method))
            self.assertIs(getattr(ClaudeCodeReasoner, method), getattr(_PromptedReasoner, method))

    def test_raises_when_no_active_snowpark_session_exists(self):
        # get_active_session() itself raises outside Snowflake; CortexReasoner shouldn't
        # swallow that; app.py's _select_reasoner is what catches it and falls back.
        def _raise():
            raise RuntimeError("No default Session is found")
        sys.modules["snowflake.snowpark.context"].get_active_session = _raise
        from engine.cortex_reasoner import CortexReasoner
        with self.assertRaises(RuntimeError):
            CortexReasoner()


if __name__ == "__main__":
    unittest.main()
