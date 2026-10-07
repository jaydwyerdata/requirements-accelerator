"""a3 spike (see docs/architecture-decisions.md's "a3 spike" entry), not the full a3 port:
proves the model-provider seam swaps cleanly onto Snowflake Cortex before committing real time
to the other two seams (storage, delivery) and a full Streamlit-in-Snowflake deployment.

CortexReasoner is exactly the same prompts as ClaudeCodeReasoner (both extend
_PromptedReasoner in engine/reasoner.py, only `_call` differs), calling AI_COMPLETE through the
active Snowpark session instead of shelling out to the `claude` CLI. Deliberately not imported
from engine/reasoner.py itself: this module imports snowflake.snowpark, a dependency the rest
of the engine has never needed and shouldn't gain just by existing, so cli.py and app.py stay
runnable with no Snowflake packages installed, exactly as they are today. Only code that
actually runs inside Snowflake (or a script deliberately testing against it) imports this file.

Only usable where an active Snowpark session already exists: a Streamlit-in-Snowflake app, a
stored procedure, or a script that opened one itself. get_active_session() raises if there
isn't one, which is the correct failure, not something to work around here.

AI_COMPLETE, not the legacy SNOWFLAKE.CORTEX.COMPLETE: Snowflake's own docs mark COMPLETE
"provided for backward compatibility" and name AI_COMPLETE as "the canonical surface going
forward," with COMPLETE slated for deprecation by the end of 2026. Building
against a function already flagged for removal would be exactly the kind of undefendable
choice CLAUDE.md's claim-integrity rule rules out, so this targets the current one.

Model default is claude-sonnet-5, current at the time this was written per Snowflake's Cortex
model availability docs (docs.snowflake.com, checked 13 September 2026, not recalled from
memory). Availability varies by region and account, verify with a direct AI_COMPLETE call in
your own account before relying on this, and pass a different model name if needed, this
adapter never hardcodes an assumption you can't override.
"""

import json

from .reasoner import _PromptedReasoner


class CortexReasoner(_PromptedReasoner):
    """The a3 spike's reasoner: identical prompts to ClaudeCodeReasoner, AI_COMPLETE as the
    transport. See this module's docstring for why AI_COMPLETE over the legacy COMPLETE
    function, and why this file is kept separate from engine/reasoner.py.
    """

    def __init__(self, model: str = "claude-sonnet-5"):
        # Imported here, not at module level: keeps the Snowpark dependency scoped to the one
        # class that actually needs it, and gives a clear, specific error (not a bare
        # ModuleNotFoundError somewhere else) if this is ever instantiated outside Snowflake.
        from snowflake.snowpark.context import get_active_session

        self._session = get_active_session()
        self._model = model

    def _call(self, prompt: str) -> str:
        # Qmark bind parameters, not string interpolation: AI_COMPLETE takes the prompt as an
        # ordinary SQL string argument, and a prompt built from interview answers is exactly
        # the kind of untrusted text a bound parameter exists to handle safely, the same
        # reason engine/semantic_view.py never string-formats a value straight into DDL.
        row = self._session.sql(
            "SELECT AI_COMPLETE(?, ?) AS response", params=[self._model, prompt]
        ).collect()[0]
        response = row["RESPONSE"].strip()
        # claude-sonnet-5 via AI_COMPLETE wraps every response, short or long, as a full JSON
        # string literal: outer quotes plus proper escaping of embedded newlines and quotes
        # (e.g. judge()'s "yes" comes back as the four characters "yes", and
        # summarise_for_reflection()'s multi-line paraphrase comes back with literal \n
        # sequences, not real newlines). Confirmed live during this a3 spike run by querying
        # AI_COMPLETE directly with judge()'s and summarise_for_reflection()'s exact prompts.
        # json.loads() undoes exactly that wrapping (quotes and all standard escapes) in one
        # step, rather than hand-stripping only the outer quote pair, which left \n literal.
        # Falls back to the raw text on anything that isn't a clean JSON string, since nothing
        # here guarantees the model always wraps its answer this way. ClaudeCodeReasoner's
        # `claude` CLI doesn't do this, so the unwrap lives here rather than in the shared base
        # class.
        try:
            decoded = json.loads(response)
        except json.JSONDecodeError:
            return response
        return decoded if isinstance(decoded, str) else response
