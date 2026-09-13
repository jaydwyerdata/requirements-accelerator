# a3 spike: running it in Snowflake

Version 0.1, 13 September 2026. Companion to docs/architecture-decisions.md's "a3 spike" entry.
Not a full a3 port, a narrow test of the one thing that was genuinely unverified: whether the
model-provider seam swaps onto Snowflake Cortex cleanly, and whether bridge.py's
background-thread pattern survives inside Snowflake's compute environment. Storage and
delivery are untouched (still SQLite and a local disk write), that's the rest of a3, not this.

This step needs to run somewhere that can actually reach your Snowflake trial account and the
`snow` CLI, which this write-up was prepared from can't do directly. Run it from Claude Code on
jaypc, or by hand, the same pattern e4's and e12's live verification and the Listening Lens
build all used.

## What's already built, ready to deploy as-is

- `engine/cortex_reasoner.py`: `CortexReasoner`, the same prompts as `ClaudeCodeReasoner` (both
  now extend a shared `_PromptedReasoner` in `engine/reasoner.py`), calling `AI_COMPLETE`
  through the active Snowpark session instead of shelling out to the `claude` CLI.
- `app.py`: unchanged except `_select_reasoner()`, which tries `get_active_session()` first and
  only falls back to `ClaudeCodeReasoner` if that fails, so the exact same file runs locally
  and inside Snowflake.
- `snowflake.yml`: a `snow streamlit deploy` project file, warehouse runtime, no compute pool.
- `tests/test_cortex_reasoner.py`: proves the calling convention (bound parameters, response
  parsing) with a faked Snowpark session, not that a live Cortex call behaves sensibly, only
  this actual deployment can prove that.

## Steps

1. Fill in `query_warehouse` in `snowflake.yml` (the `TODO_YOUR_WAREHOUSE` placeholder) with a
   warehouse in your trial account, whatever you already used for Listening Lens is fine.
2. From the repo root, with the `snow` CLI configured against your trial account:
   ```
   snow streamlit deploy --replace --open
   ```
   This stages `app.py`, `bridge.py` and the whole `engine/` package, creates the Streamlit
   object, and opens it in a browser.
3. Start an interview in the opened app and answer a few questions, enough to trigger at least
   one `judge()` call (layer 00's redirect check fires on every answer) and, ideally, one
   `reframe()` (answer something like "not sure" to force it) and one `extract_terms()` (layer
   02 onward).
4. Watch for exactly two things, since these are the two unknowns this spike exists to close:
   - Does the app actually respond, rather than hanging, after an answer that triggers a
     reasoner call? That's `bridge.py`'s background thread actually completing inside
     Snowflake's compute environment, not just locally.
   - Does the `AI_COMPLETE` call succeed at all (a real judgement, reframed question, or term
     list comes back), rather than erroring? That's the model-provider seam itself.
5. Let it run through to the end once if the above look fine, so a full interview producing a
   business ask and technical spec is confirmed too, not just the first couple of questions.

## If AI_COMPLETE errors

- A permission error naming `CORTEX_USER` or similar: your trial account already has Cortex
  functions unblocked (Listening Lens's Discover tab uses them), but the specific role running
  this Streamlit app might not hold that grant. Run, as a role that can grant it:
  ```sql
  GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE <the role running this app>;
  ```
- A model-not-found or region error: `claude-sonnet-5` is `CortexReasoner`'s default (verified
  against Snowflake's Cortex model availability docs on 13 September 2026), but availability is
  cross-region and can vary. Pass a different model name to `CortexReasoner(model=...)` in
  `app.py`'s `_select_reasoner`, or check what's enabled for your account with a direct
  `SELECT AI_COMPLETE('claude-sonnet-5', 'say hi');` in a worksheet first.
- "No default Session is found" or similar: this means `get_active_session()` failed, which
  means you're not actually running inside a Snowflake-hosted Streamlit app, check the
  deployment actually succeeded rather than debugging the reasoner.

## What this does NOT test, on purpose

- Storage or delivery: this spike still uses `SqliteStorage` against a local file inside the
  app's container, which won't persist across app restarts. That's a3's storage seam, out of
  scope here.
- The container runtime, compute pools, or a Native App packaging (unlike Listening Lens): this
  targets the plain warehouse-runtime Streamlit object, the simpler of the two, since nothing
  here needs Native App-style consumer installability.
- Multiple concurrent users, or anything about production hardening. This is a feasibility
  check, not a launch.

## Afterwards

Whatever happens, tell Claude what you saw (worked cleanly, hung, errored, partially worked)
so the tracker, architecture-decisions.md and memory get the honest outcome recorded, the same
way e4's and e12's live runs were, rather than this staying a documented-but-unconfirmed claim.

## Cleanup

This is a spike, not a keeper by default. If you don't want it running against your trial
account's compute/credits afterwards:
```sql
DROP STREAMLIT IF EXISTS requirements_accelerator_spike;
DROP STAGE IF EXISTS requirements_accelerator_stage;
```
