# Architecture Decisions

Version 0.1, last revised 11 September 2026.

Short-form decision records for the two portability-seam questions CLAUDE.md left open: model
provider and storage. Each entry states the decision, the reasoning, and what it costs. Revised in
place if a decision changes, per repo conventions.

## Model provider (e4)

**Decision**: the reasoner calls Claude Code in non-interactive mode as a subprocess (`claude -p
"<prompt>"`), rather than calling the Anthropic API directly.

**Reasoning**: this runs against the existing Claude Pro subscription's usage pool instead of
separate, metered API billing, which is the constraint that mattered most: paying for API access on
top of a subscription that's already sitting there unused for this purpose didn't make sense.

**Cost**: each judgement call spins up a CLI process rather than reusing a live connection, so it's
slower than a direct API call, on the order of a couple of seconds. Acceptable at interview pace,
where a person is typing between calls anyway.

**Consequence**: `engine/reasoner.py` gains a second implementation of the `Reasoner` interface
alongside `StubReasoner`, call it a Claude Code-backed one, with nothing else in the engine
changing. The interface is what makes this swap free.

**Implementation (11 September 2026)**: built as `ClaudeCodeReasoner` in `engine/reasoner.py`.
Each of `judge`, `extract_terms` and `summarise_for_reflection` builds a plain-language prompt
and shells out to `claude -p "<prompt>" --output-format json --tools "" --no-session-persistence`,
then parses the JSON payload's `result` field. `--tools ""` because a judgement call never needs
to read a file or run a command; `--no-session-persistence` because a full interview makes
dozens of these calls and none is a conversation worth resuming. `--bare` was considered and
rejected: it forces API-key-only auth and never reads the keychain, which would defeat the whole
reason this shells out to the CLI instead of calling the API. A call that fails, whether the
process errors, times out, or the JSON has no usable result, raises `ClaudeCliError` rather than
guessing an answer: per CLAUDE.md's claim-integrity rule, a judgement this tool can't actually
get an honest answer to has to stop the interview, not fake one. `cli.py` now constructs
`ClaudeCodeReasoner` instead of `StubReasoner`.

Verification is partial, and the gap is worth stating plainly rather than glossing over.
Parsing and command construction were checked against mocked subprocess output (a fake `yes`,
`no`, a term list, `none`, an `is_error` payload, a non-zero exit) and all parse or raise
correctly. Wiring was checked against the real CLI: running `cli.py` end to end raises
`ClaudeCliError: claude -p reported an error: 'Not logged in · Please run /login'` at the first
judgement call, confirming the call actually reaches a real `claude -p` subprocess rather than a
stub, and that a failed call surfaces cleanly instead of hanging or crashing on an unparsed
result. What could not be verified here: whether `judge`, `extract_terms` and
`summarise_for_reflection` actually produce sensible answers to real interview content, because
this build ran inside a sandboxed session whose Bash tool spawns subprocesses that can't read
this machine's own `claude` CLI credentials (confirmed: `~/.claude/.credentials.json` exists and
is current, but `claude -p` still reports not logged in when run this way) - a sandbox isolation
boundary, not a defect in the code or a fact about the machine's normal setup. Running `python
cli.py` from an ordinary terminal, outside that sandbox, is the real end-to-end proof still
outstanding.

## Storage (e3)

**Decision**: SQLite, via Python's standard library `sqlite3` module, one local database file,
behind the storage seam.

**Reasoning**: zero external dependency, which matters for the eventual Streamlit in Snowflake port
where the runtime is fussier about imports. The retained-knowledge goals in the README, recalling a
prior term's definition, detecting overlap between requests, building the dependency map, all need
real queries across interviews, not just within one. Flat JSON files make that painful; a real
database makes it a query.

**Cost**: none significant for v1. One more moving part than a flat file, but a standard one.

**Consequence**: chosen with the eventual Snowflake port in view. The storage interface stays the
same either way; only the implementation swaps, a local SQLite file becomes a Snowflake table,
mirroring how the reasoner seam swaps its implementation without the engine noticing. Local schema
design (what tables, what's a field record versus a retained term versus a dependency edge) is
implementation work for e3 itself, not decided here.

**Implementation (11 September 2026)**: built as `engine/storage.py`. Two tables, `interviews`
(id, created_at) and `field_records` (interview_id, field_id, layer, value, state, source, owner,
note), one row per field per interview, values JSON-encoded so a term_locked boolean round-trips
correctly alongside every other field's string value. `SqliteStorage` implements `save_interview`,
`load_interview` and `list_interviews`. `engine/knowledge.py` gained a second `RetainedKnowledge`
implementation, `SqliteRetainedKnowledge`, that queries across every interview on file for a term
and returns the most recent one that actually locked, per the three lock conditions in
docs/interview-branching.md; an unlocked term never comes back as retained knowledge, on purpose.
`cli.py` now saves every interview to `requirements_accelerator.db` (gitignored, it's runtime
data) and uses `SqliteRetainedKnowledge` instead of the `NoRetainedKnowledge` stub. Verified with
`examples/demo_retained_knowledge_pass.py`: one interview locks a definition and leaves a second
term unlocked, a second interview against the same term sees the retained definition and gets the
concrete version of the competing-definition question.

Overlap detection between requests and the dependency map, both named as goals for this same data
in the README, are not built. Both need real interviews on file to know what a useful query even
looks like against, so guessing at one now against zero real data would be exactly the kind of
hollow feature CLAUDE.md's claim-integrity rule warns against. Tracked separately as e8.
