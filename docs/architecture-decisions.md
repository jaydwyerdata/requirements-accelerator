# Architecture Decisions

Version 0.12, last revised 13 September 2026.

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

**Verified (11 September 2026)**: run from an ordinary PowerShell terminal on Jay's own machine,
outside any sandbox. `claude --version` reported 2.1.263 and `claude -p "hello"` returned real,
project-aware content, confirming the CLI is installed, logged in, and reachable from that shell.
`python cli.py` then ran the full nine-layer interview against `ClaudeCodeReasoner`: every
judgement, term extraction and reflection in the transcript went through a real `claude -p` call,
with no `[stub reasoner]` output anywhere in it, and no `ClaudeCliError`. The verification gap
above is closed. What the transcript also did, which was not the point of the exercise but turned
out to matter more, was surface two real gaps in the interview design itself once it met an actual
person instead of a scripted demo: see the revision below, and `docs/interview-branching.md` v0.2.

**Revision (11 September 2026): a fourth Reasoner method, `reframe`**. The live run above produced
a technically correct interview that felt transactional rather than conversational: a reply of "I
don't understand what you mean" to layer 02's primary measure question was stored as the answer and
carried through to the final document, and several later terms in layer 07 got "not sure" answered
to the same fixed follow-up text three and four times in a row with no attempt to ask differently.
Decided in response: `Reasoner` gains a fourth abstract method, `reframe(question, prior_reply,
context_so_far)`, called whenever a reply is classified as a clarifying question or a don't-know
rather than a genuine answer (the classification and the control-flow rules around it are specified
in `docs/interview-branching.md`'s "Classifying a reply" section, not here). `StubReasoner`'s
implementation prompts a person at the keyboard to type a rephrasing by hand, the same pattern as
its other three methods. `ClaudeCodeReasoner`'s implementation builds a prompt from the field's
plain-language intent and everything already on the ledger at that point, and calls out for a
grounded rephrase rather than a generic one, the same `claude -p` mechanism as the other three
methods.

**Cost**: this adds at least one more `claude -p` call to every question that gets reframed, on top
of the calls the interview already makes. Deliberately not treated as a constraint here: the goal is
demonstrating an adaptive interview capability, not minimising calls against the Pro plan's usage
pool, so slower and more expensive was accepted without trying to design around it. Worth recording
plainly rather than glossing over, since it is a real tradeoff a metered-billing environment would
have to weigh differently.

**Consequence**: layer 00's redirect and layer 07's vagueness loop, previously two separate pieces
of bespoke logic, both become the same `reframe` call applied to one question each. `engine/
interview.py`'s shared `_ask_question` gains the classify-then-reframe behaviour so every question
gets it, not just those two. Not yet built: this is a decision record, not an implementation note,
per `CLAUDE.md`'s document-as-you-go rule, the decision is written down before the code exists to
match it.

**Regression caught and fixed (11 September 2026)**: the guard on `consolidate_terms`, call it
only when there is a non-empty term queue, was believed built and demo-verified, but the version
actually on disk called it unconditionally regardless of queue length. A new automated test
suite (`tests/`, see the note under this document's introduction) caught it immediately:
`examples/demo_not_applicable_pass.py`'s scripted run, which queues zero terms on purpose, ran
one call past what its script provides and failed with `StopIteration` rather than the clean
`exit 0` the tracker had recorded. Refixed with the same `if pending_terms:` guard the design
called for; all five `examples/demo_*.py` scripts and the full `tests/` suite pass again,
confirmed by actually running them, not by re-reading the code and assuming. Recorded here
plainly because the earlier "verified" claim was wrong, per `CLAUDE.md`'s claim-integrity rule:
a build note that turns out to have been premature gets corrected in place, not quietly
overwritten.

**Verified (12 September 2026)**: run against the real `ClaudeCodeReasoner`, the same live-terminal
proof e4 needed. Jay's mock store-sales interview (see "First real mock interview, findings"
below) exercised `reframe` directly: an ambiguous reply to the query-shape question ("how much")
got a grounded, context-aware follow-up back ("When you say 'how much', do you mean the total
value or volume of what's been sold, like daily sales figures for each store?"), not a generic
rephrase, and the same happened at other points in the run. `consolidate_terms` correctly kept the
single genuine business term ("target") without duplicates across the whole interview. Confirmed
directly by Jay as working well. The verification gap this decision record flagged after the
initial build (`ClaudeCodeReasoner`'s `reframe` and `consolidate_terms` behaving sensibly against
real interview content, not just correct control flow around them) is closed.

## Testing

Five scripted interview runs already existed as `examples/demo_*.py`, readable narrated
walkthroughs meant to be run directly (`python examples/demo_full_pass.py`) to see the flow and
the two rendered documents. Most had no automated pass/fail, though, just printed output for a
person to read and judge, which is exactly how the `consolidate_terms` regression above sat
undetected: `exit 0` alone was being read as success.

`tests/` (stdlib `unittest`, no new dependency, run with `python -m unittest discover -s tests`)
wraps every one of the five scenarios with real assertions, reusing each script's exact scripted
dialogue by import rather than duplicating it, plus its own test for `bridge.py`'s thread/queue
handoff (e7). The demo scripts stay as they are, still useful to read and run by hand; `tests/`
is what a test runner, or a person who just wants a fast yes/no, actually executes.

## Delivery (a2)

**Decision**: once an interview finishes, the two rendered documents are also written to disk as
plain-text files, one to a business-ask folder and one to a technical-spec folder, via a new
`engine/delivery.py`. No adapter interface: there is only one implementation, and no upload, API
call or authentication of any kind, just two `Path.write_text` calls.

**Reasoning**: CLAUDE.md names writing to a synced folder as the default delivery mechanism,
because pointing the two destination paths at a OneDrive- or SharePoint-synced directory reaches
those systems with zero integration, credentials or tenant configuration, and because delivery
must never be what blocks the build. Building a `Delivery` interface now, with only one real
implementation and no second one in sight, would be exactly the speculative abstraction CLAUDE.md's
build discipline warns against; if a richer mechanism (a real API push, for instance) is ever
needed, `deliver_documents` is the one function that changes.

**Cost**: none significant. The two folders are gitignored, runtime output in the same category as
`requirements_accelerator.db`; a caller who wants real synced delivery just points the two
directory arguments at synced folders instead of the local defaults.

**A real design risk caught before writing code**: the business ask and technical spec must never
be able to land in the same folder by default. The business ask is requester-facing and fine to
share; the technical spec is internal-only, per `docs/output-template.md` and CLAUDE.md alike ("the
requester never sees the technical spec"). One folder with one optional second parameter defaulting
to the first would make that separation trivially easy to break the moment that folder is shared or
synced. Solved by making both destination directories required, positional parameters with two
different local defaults (`delivered/business-ask/`, `delivered/technical-spec/`), never one
defaulting to the other, so even a caller who supplies neither can't recreate the mistake.

**Implementation (11 September 2026)**: `deliver_documents(interview_id, business_ask,
technical_spec, business_ask_dir=..., technical_spec_dir=...)` in `engine/delivery.py`. Each
document is written under a UTC-timestamped, interview-id-prefixed filename
(`<timestamp>_<short_id>_business-ask.md`), microsecond resolution so two deliveries in the same
process and the same second still sort chronologically and never collide; each destination
directory is created if it doesn't already exist. Returns the two written paths so the caller can
tell the requester or the data team where to find them. `cli.py` calls it right after printing both
documents and prints the two saved paths; `app.py` calls it from the bridge's `"done"` handler and
shows the two saved paths as a caption once the interview finishes.

**Verified**: `tests/test_delivery.py` (4 tests, stdlib `unittest`, `tempfile.TemporaryDirectory`
per test): each document lands in its own folder with its own content; both destination folders get
created when they don't exist; two deliveries in a row never collide and each keeps its own
content, not the other's; the filename carries the interview id's short prefix for traceability.
All pass. A real bug surfaced while writing that last test: it originally asserted the literal
substring `"interview"` appeared in the filename, using `"interview-abcdef1234"` as the sample id,
which happens to survive an 8-character truncation into `"intervie"` (missing the trailing `w`) -
a coincidence of that specific sample string, not a real property of `deliver_documents`, since a
real `interview_id` is a `uuid.uuid4()` string that never contains the word "interview" at all. The
test was wrong, not the code; fixed to assert the actual property that matters, that the short-id
prefix used in the filename matches `interview_id[:8]`. Caught and corrected before this was
committed, not after, per CLAUDE.md's claim-integrity rule. Also manually smoke-tested end to end
outside the test suite (a standalone `deliver_documents` call, checked the two files existed with
the right content, then cleaned them up) to confirm the behaviour matches what the tests assert.
The full `tests/` suite (27 tests, up from 23) and all five `examples/demo_*.py` scripts still pass
unchanged; delivery is not wired into any of the demo scripts, only `cli.py` and `app.py`, so this
also confirms no regression from the change.

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

## Frontend (e7)

**Decision**: a locally hosted Streamlit app (`app.py`), running `engine/interview.py`'s existing
`run_interview` unchanged, on a background thread bridged to Streamlit's rerun-per-interaction
model via a small queue-based module (`bridge.py`).

**Reasoning**: per CLAUDE.md's "local first, port later", and the same portability seam already
paid for at e4 and e3. `run_interview` asks its questions by calling a blocking `ask(prompt)`
and expects a reply back before continuing, the natural shape for a terminal script (`cli.py`
just hands it `input`), but not one Streamlit's rerun-per-interaction model can call directly:
a script reruns top to bottom on every widget interaction with no call stack carried over from
the last run. Rather than rewriting the interview as a state machine Streamlit can drive
directly, which would mean the engine encoding UI concerns it has no business knowing about, the
interview keeps running exactly as `cli.py` runs it, just on a thread of its own, talking to the
Streamlit thread through two queues: one carries the requester's typed reply in, the other
carries every piece of narration and a terminal done/error/waiting signal back out. `engine/
interview.py`, `engine/reasoner.py`, `engine/storage.py`, `engine/render.py` and `engine/
knowledge.py` are all untouched; `run_interview`'s existing `ask=None` parameter (added when the
classify-and-reframe mechanism was built) turned out to already be exactly the seam this needed,
so no engine change was required to add a frontend at all.

**Cost**: one new runtime dependency, Streamlit itself, scoped to `app.py`; the engine stays
dependency-free. A background thread per interview that is started but never explicitly joined,
by design (an abandoned browser tab should not block the process), which is fine for one person
running one interview locally but would need to become per-session state rather than a bare
thread if this is ever asked to serve more than one interview from the same process, the
eventual Streamlit in Snowflake port CLAUDE.md names as a later target. Noted here as a real
limit of this decision, not discovered by accident later.

**Consequence**: `bridge.py` is new, standalone, and knows nothing about Streamlit specifically,
only about the shape `run_interview` needs (a blocking `ask`, and somewhere for its stdout-bound
narration to go); a future non-Streamlit frontend, or the Streamlit in Snowflake port, could reuse
it unchanged. `app.py` is the Streamlit-specific half: session state, and drawing whatever the
current status calls for. `cli.py` is unaffected and stays the terminal entry point.

**Scope cut, stated plainly (original pass)**: `docs/interview-ux.md` specifies a widget per
question, free text, multi-choice, hybrid or banded, and the first pass at this build did not
implement that mapping; every question went through one free-text box. The thread/queue bridge
was the real architectural risk in standing up a frontend at all: a wrong queue handoff means a
hung or silently wrong interview, which no amount of polished widgets would fix, so it came
first. Widget fidelity was tracked as the next slice rather than folded into that one.

**Widget layer, built (11 September 2026)**: `docs/interview-ux.md`'s classification already
lived as data, not just prose, once looked for: `engine/protocol.py`'s `Question.choices` carries
the exact option list for every MC, HYB and BAND question and is `None` for every FT one. The gap
was never a missing classification, only that nothing carried it past `engine/interview.py`'s own
console output. Closed with the smallest change that does that honestly:

- `ask`'s contract gains one optional, keyword-only argument: `ask(prompt, choices=None)`.
  `engine/interview.py`'s default when nothing is injected changes from the bare `input` builtin
  to a small `_console_ask(prompt, choices=None)` that ignores `choices` and calls `input(prompt)`,
  since the console path already prints the same list as a hint (now via one shared
  `_print_choices` helper instead of three copy-pasted print statements). `cli.py`, every
  `examples/demo_*.py` script, and the whole `tests/` suite never pass `ask` explicitly, so they
  pick up `_console_ask` automatically and are unaffected: same console behaviour, confirmed by
  rerunning all five demos and the full test suite, not assumed from the diff.
- Every call site that already had a question's `choices` to hand (`_ask_question`, layer 04's
  `restatement_handling` special case, layer 07's `exclusion_q`) now passes it through:
  `ask("> ", choices=question.choices)`. `_classify_and_reframe`'s own re-ask after a reframe
  passes none, correctly: a reframed question is a fresh, open-ended rephrasing by design, never
  a fixed set.
- `bridge.py`'s `Bridge.ask` takes the same `choices` argument and puts it on the `signal_queue`
  alongside the `"waiting"` signal (`("waiting", choices)` instead of `("waiting", None)`
  unconditionally), so a UI reading that queue gets the classification for free.
- `app.py`'s `_render_question` renders from `st.session_state.choices` alone: `None` is the
  existing free-text box; a list containing `"something else"` is HYB, buttons for the fixed
  options plus an always-visible text box; a list without it is MC/BAND, buttons only, no
  free-text escape hatch, matching `docs/interview-ux.md`'s own rule that a genuinely closed
  answer space gets none. No per-field lookup table was needed in `app.py`: the presence and
  shape of `choices` is sufficient on its own to reproduce the document's classification, which
  is possible only because the data in `engine/protocol.py` already encodes it correctly.

**Known gap, closed (11 September 2026)**: layer 07's `competing_definition_check` was documented
in `docs/interview-ux.md` as MC (matches / doesn't match / not sure, worded one way when retained
knowledge has a prior definition and another way when it doesn't) but rendered as free text,
because `engine/protocol.py` never gave it a `choices` list and `run_layer_07` asks it with
bespoke inline logic, not through `_ask_question`. Re-reading `docs/interview-ux.md` closely
showed the exact wording for both phrasings was already specified there, not something left to
invent: `matches / doesn't match / not sure` when a prior definition exists, `worth flagging /
not a concern / not sure` when it doesn't. Closed by adding both lists as their own constants in
`engine/protocol.py`, `COMPETING_DEFINITION_CHOICES_WITH_PRIOR` and
`COMPETING_DEFINITION_CHOICES_NO_PRIOR`, since this is the one field in the whole protocol whose
choices depend on runtime state rather than being fixed per `field_id` (so it can't just be
`Question.choices`); `run_layer_07` picks the matching list alongside the phrasing it already
branches on and passes it to `ask`, the same mechanism every other choice-bearing question uses.

**Verified**: `tests/test_widget_choices.py` gained `test_competing_definition_check_reports_the_
no_prior_choices`, confirming the no-prior list is reported and the with-prior one isn't in a
scenario with no retained knowledge; the existing not-invented and question-count checks were
updated to include it (count now 20, up from 19, since `demo_full_pass.py` queues exactly one
term). All five `examples/demo_*.py` scripts still exit 0, and running
`demo_retained_knowledge_pass.py` by hand confirms both phrasings print with their correct
choices: `worth flagging / not a concern / not sure` for the first, unlocked term with no prior
definition, `matches / doesn't match / not sure` for the second interview's term that does have
one on file. The full `tests/` suite is now 28 tests, all passing.

**Verification**: Streamlit itself is still not installable in this sandbox (unchanged from the
base e7 entry above), so the actual rendered buttons are unconfirmed the same way the base
thread/queue bridge was. What could be verified without it: a new test,
`tests/test_widget_choices.py`, drives `demo_full_pass.py`'s script through `bridge.py` exactly as
`tests/test_bridge.py` does, but records the `choices` payload from every `"waiting"` signal
instead of discarding it, and checks each one against `engine/protocol.py` directly rather than a
hand-typed expectation. It confirms: a free-text question reports `None`; a representative MC,
HYB and BAND question each report their real, unaltered choices list; every non-`None` list seen
across the whole run matches some real `Question.choices` in the protocol, never an invented one;
and the exact count of choice-bearing questions actually asked in this scenario is 19, counted
independently from `engine/protocol.py` and this scenario's own known branches (both
`drill_through_required` and `system_of_record` are asked live here, not shortcut to "not
applicable"), not assumed. All 23 tests in `tests/` pass, and all five `examples/demo_*.py`
scripts still exit 0 unchanged. What this does not prove is that Streamlit's own `st.button` and
`st.form` widgets render and behave as `_render_question` intends; that needs `streamlit run
app.py` on a machine where the install works, the same outstanding confirmation the base e7 entry
already named.

**Verification**: Streamlit itself could not be installed in the sandbox this was built in
(`pip install streamlit` fails: pypi.org is not in this environment's network egress allowlist,
confirmed via the proxy status endpoint rather than assumed), so the actual rendered UI is not
yet confirmed to work, the same category of gap e4 had before its live terminal run. What could
be verified without Streamlit installed: `bridge.py` driven directly, with the real
(unthreaded-in-source) `run_interview`, `demo_full_pass.py`'s exact 97-reply script fed through
the bridge's queues exactly as `app.py`'s `_pump` function drives them, asserting the engine
thread signals done, exits cleanly, and produces a business ask and technical spec byte-identical
to a direct, unthreaded run of the same script. That passed. It proves the queue handoff itself
is correct, no dropped or duplicated replies, no deadlock, no divergent ledger state, which was
the actual architectural risk in this decision. It does not prove the Streamlit widgets render
correctly, that a real `claude -p` call's latency feels acceptable inside Streamlit's spinner, or
that the browser-facing UI behaves as intended; that confirmation is still outstanding and needs
running `streamlit run app.py` on a machine where `pip install streamlit` succeeds, the same kind
of live run e4 needed and got.

**Verified (12 September 2026)**: run live on Jay's own machine, `streamlit run app.py` in a
browser, the same kind of proof e4 and e9 needed. Confirmed working: the rendered widgets behave
as `_render_question` intends (buttons for closed questions, the always-visible text box for
"something else"), and the "First real mock interview" fixes below (the LAYER-header leak, the
four reworded questions) read clean in the actual browser UI too, not just the console this was
originally built and tested against. This closes the last outstanding gap on this decision: the
queue handoff was already proven correct, and now the browser-facing half is too.

## First real mock interview, findings (12 September 2026)

**What happened**: Jay ran a full nine-layer mock interview against the real `ClaudeCodeReasoner`
(a store-sales-reporting scenario), the first genuine end-to-end run by an actual person rather
than a scripted demo. It completed cleanly, produced a business ask and a technical spec, and the
reframe mechanism (e9) visibly worked: free-text answers that read as ambiguous got grounded,
context-aware follow-ups (`"When you say 'how much', do you mean the total value or volume of
what's been sold, like daily sales figures for each store?"`), not generic ones. Feedback surfaced
two distinct issues, one a clear bug, one a real open design question.

**Bug, fixed**: internal `"LAYER 00"` / `"LAYER 02"` / `"LAYER 04"` / `"LAYER 07"` section headers
were being printed straight into the requester-facing transcript, in `run_simple_layer`,
`run_layer_02`, `run_layer_04` and `run_layer_07`. Since `bridge.py` mirrors every `print()` call
into the narration a requester actually reads (see e7's entry), these leaked verbatim into the
Streamlit transcript too, not just the CLI. This is a direct violation of the two-persona design
CLAUDE.md states: front of house is a curious business analyst speaking plain language, never
warehouse-side structure. Fixed by removing the bare layer-number headers entirely (a blank
`print()` still separates question groups visually) and replacing layer 07's per-term marker with
plain language: `Let's pin down what you mean by "{term}".`, which keeps the useful part (which
term is being clarified next) without the internal label. The technical spec renderer's own
`"Layer 00: the problem"` section headings are unaffected and correctly untouched: that document
is for Jay's team, who are as technical as he is, not the requester.

**Verified**: full `tests/` suite (28 tests) and all five `examples/demo_*.py` scripts still pass
unchanged; no test asserted on the old header text, confirmed by searching for it first. Manually
re-ran `demo_full_pass.py` and confirmed no bare `"Layer NN"` string appears anywhere in the live
interview transcript now, only in the technical spec output where it belongs, and that the new
layer-07 line reads naturally in context.

**Open design question, not resolved here**: several closed-choice (MC/BAND) questions read as
generic and hard to parse out of context even when they're answered without any trouble, for
example `fan_out_risk` (`"Could the same one show up on more than one row?"`) and
`cardinality_risk` (`"Does one of these ever belong to more than one of those at the same
time?"`), both quoted directly in Jay's feedback, plus `volume` (`"Roughly how many of these are
we talking about?"`) and `blast_radius` (`"And who else does it bite?"`). This isn't a bug in the
reframe mechanism: `_classify_and_reframe` runs on every question already and correctly grounds a
reply that reads as unclear, but it only fires reactively, when the *answer* given is ambiguous.
None of these were reworded here because a clear, on-topic answer was given each time; the
*question's own wording*, read cold before any answer, is what's generic, since the Coaxing
Protocol's MC/BAND templates are deliberately written to apply across any domain. Grounding a
question proactively, before showing it, is a real, unimplemented capability, not an oversight in
the existing one. Left open for Jay to decide the direction: rewrite the flagged templates'
static wording to read more naturally in the abstract (cheap, `docs/coaxing-protocol.md` and
`engine/protocol.py` only), or add proactive grounding to every closed question (a real reasoner
call before each one is shown, the same latency/cost tradeoff already accepted for reframe, just
applied earlier and more often).

**Resolved (12 September 2026)**: rewrite the static templates. Cheapest option, no added
latency or reasoner cost, and directly addresses the four fields actually flagged rather than a
speculative general mechanism. `docs/coaxing-protocol.md` and `engine/protocol.py` updated
together, kept verbatim-identical per this module's own docstring rule:

- `blast_radius`: `"And who else does it bite?"` -> `"Who else deals with this same problem?"`.
  Previously bundled with `frequency` under one blockquote in `docs/coaxing-protocol.md` even
  though they're two separate `Question` objects in code; split into two, matching the code.
- `fan_out_risk`: `"Could the same one show up on more than one row?"` -> `"Could that ever show
  up more than once in the spreadsheet?"`. Keeps the spreadsheet metaphor grain already
  established two questions earlier, drops the dangling "the same one".
- `cardinality_risk`: `"Does one of these ever belong to more than one of those at the same
  time?"` -> `"Could one of these ever belong to more than one group at the same time?"`. Same
  generic, domain-agnostic shape the templates need to keep (this has to work for any interview,
  not just this one), just with a concrete noun ("group") standing in for the doubled, referent-
  free "one of those".
- `volume`: `"Roughly how many of these are we talking about: hundreds, thousands, millions?"` ->
  `"Roughly how much data is this: hundreds, thousands, or millions of records?"`. `volume` is
  asked in layer 09, several layers and many turns after grain was last discussed in layer 03, so
  "these" had drifted too far from its antecedent to still read clearly; "records" re-anchors it
  without naming anything domain-specific.

Proactive per-question grounding (the reasoner-call option) stays a real, unimplemented idea for
later if generic wording keeps causing trouble across more mock interviews; not built now; not
needed to close this round of feedback.

**Verified**: full `tests/` suite (28 tests) and all five `examples/demo_*.py` scripts still pass
unchanged, since nothing but display text moved (no test asserts on a question's exact prompt
text, only its `choices`). Manually re-ran `demo_full_pass.py` and confirmed all four new
wordings print correctly in place of the old ones.

## a3. Streamlit in Snowflake port plan (documented, not built)

**Decision (12 September 2026)**: not porting yet. e7 and e9 had only just been confirmed working
against a real person and a real model when the question came up, the current Snowflake trial's
usable window is already committed to the separately tracked SE portfolio demo builds, and the
part of this project that actually demonstrates engineering judgement, the interview design and
the provenance model, doesn't need Snowflake hosting to be shown. Porting now would trade a
working, verified local tool for a partially-verified hosted one, for no real gain this month.
What follows is the seam-by-seam plan for when it does make sense to build, not a build log; every
line below is a design decision, not a confirmed implementation, and CLAUDE.md's claim-integrity
rule applies to this section exactly as it does to code that ships.

**Why this is safe to defer**: every place the engine touches something environment-specific was
already built as a seam, not wired in directly, specifically so a port would be a swap of
implementations behind an existing interface rather than a rewrite. `engine/interview.py`,
`engine/protocol.py` and `engine/ledger.py`, the actual interview logic, do not import Streamlit,
SQLite, or the `claude` CLI anywhere; they only see `Reasoner`, `RetainedKnowledge` and whatever
calls `deliver_documents`. That's the whole reason this plan can be written seam-by-seam below
instead of as one undifferentiated rewrite.

**Model provider seam**: `ClaudeCodeReasoner` (`engine/reasoner.py`) shells out to a local `claude`
CLI subprocess, which doesn't exist inside a Streamlit in Snowflake container and shouldn't need
to: Cortex is the native replacement. A `CortexReasoner` would implement the same five abstract
methods (`judge`, `extract_terms`, `summarise_for_reflection`, `reframe`, `consolidate_terms`)
against `SNOWFLAKE.CORTEX.COMPLETE`, called through Snowpark using the session already live inside
a Streamlit in Snowflake app (`get_active_session()`), not a fresh connection. Each method keeps
its own prompt, same as `ClaudeCodeReasoner`'s current prompts, adapted for whichever Cortex model
is picked (Claude models have been available through Cortex; the specific model choice is a
build-time decision, not a design one). No change to `engine/interview.py` or anything that calls
`reasoner.*`: this is the entire point of the seam, and it's the one already exercised twice, once
building `StubReasoner`, once building `ClaudeCodeReasoner`.

**Storage seam**: `SqliteStorage` and `SqliteRetainedKnowledge` (`engine/storage.py`,
`engine/knowledge.py`) hold interview state and locked term definitions in a local, gitignored
`.db` file, correct for a laptop, wrong for a multi-user hosted app where "local" disk is
ephemeral per container and not shared across sessions. Both would get native-Snowflake-table
implementations of the same interfaces: `interviews` and `field_records` for storage, whatever
`RetainedKnowledge` needs for the definitions table, same two-table shape already proven out
locally, written through the Snowpark session rather than `sqlite3`. This is a rename of the
storage target, not a redesign of the schema.

**Delivery seam (a2)**: `engine/delivery.py` currently writes the business ask and the technical
spec to two local folders, on the assumption that pointing those folders at a synced OneDrive or
SharePoint directory is enough to get finished documents to people with zero tenant integration.
That assumption breaks inside Streamlit in Snowflake: there's no synced local folder to write
into. The two honest replacements are a Snowflake internal stage (durable, governed by the same
RBAC as everything else, needs an explicit connector or a scheduled task to actually land the file
somewhere a person opens without going into Snowsight) or `st.download_button` handing the
rendered document straight to whoever finished the interview, no stage or sync step at all. The
second is simpler and probably right for the business ask; the technical spec, meant for the data
team rather than the requester, likely still wants a stage. Neither is built or chosen yet.

**Frontend compatibility**: `bridge.py`'s design, running `run_interview`'s blocking loop on a
background thread and bridging it to Streamlit's rerun model via a queue, was built for local
Streamlit, not verified against Streamlit in Snowflake's execution model (Snowpark Container
Services). Python's threading should carry over unchanged since SiS runs a real Python process,
not a restricted sandbox, but that's an assumption, not something confirmed by running it there;
first thing to check before writing any other SiS-specific code.

**Explicitly orthogonal to a1**: a1 (the Snowflake semantic view adapter, still not built) turns a
finished interview's captured requirements into Snowflake semantic view DDL; a3 is about where the
interview tool itself runs. A finished interview run entirely on a laptop against `SqliteStorage`
can still feed a1's adapter later. Porting the tool's own hosting has no bearing on whether a1
gets built, and vice versa.

**Not decided, and not needed to decide now**: which Cortex model to call, exact stage-vs-download
split for delivery, and whether retained knowledge should be shared across a team (a single shared
Snowflake table naturally would be, which is arguably a feature, not just a side effect of the
seam swap) or scoped some other way. These are real open questions to resolve at build time, not
gaps in this plan.

## Real ClaudeCodeReasoner run against synthetic interview 1 (12 September 2026)

**What happened**: the synthetic dataset (see docs/synthetic-dataset.md) was built and verified
entirely against `StubReasoner`, which is scripted, not model judgement. Asked to check whether
those scripts hold up against a real model, `examples/synthetic/verify_against_claude_code_reasoner.py`
runs interview 1 (Store Operations Manager, "stockout") against the real `ClaudeCodeReasoner`, with
a custom `ask` that matches the actual question text (captured from stdout, since most call sites
only hand `ask()` the bare "> " marker, not the question) against the same scripted answers
interview 1 used, so the requester's side stays fixed and only the reasoner's judgement is real.
Chosen deliberately as the safest first one to verify live: designed as a clean pass with no
redirect expected.

Most of it behaved exactly as hoped: every judge() call on a clear closed-set answer agreed with
the assumed branch (system_of_record asked live, since two systems were genuinely named), every
`summarise_for_reflection()` paraphrase was accurate and stayed in plain language, and the
interview reached 100% readiness with a coherent business ask and technical spec. Three real
findings surfaced, not harness noise:

**1. A live reframe happened where none was scripted, and the reframe invented an unstated
detail.** The plain "which ones" answer to layer 01's query_type question was judged a non-answer,
and the model's reframe was: "When you picture that morning check, do you mean you'd want to see
specific product names, like 'the trail runner packs' or 'size 10 hiking boots', flagged as
running low, so you know exactly which items to chase up?" Those two product names were never
given anywhere in the interview. `reframe()`'s own prompt explicitly says "Never invent a detail
they have not actually given you", and here the model didn't honour that instruction. This is the
sharpest finding in this run: worth a second real interview to see if it recurs before deciding
whether the prompt needs a stronger constraint (e.g. explicitly forbidding invented examples,
only ever quoting the requester's own words back) or a post-call check that rejects a reframe
containing text not traceable to the ledger.

**2. extract_terms()/consolidate_terms() didn't converge on the one term the interview was
obviously about.** Across the seven layers before layer 07, extract_terms() queued ten candidates
("best-selling", "sell out", "rush replenishment", "about to run out", "running out", "scheduled
delivery", "on a schedule", "at risk of a stockout in the next few days", "stockroom count",
"evening cycle count"), noticeably more than StubReasoner's scripted single "stockout".
consolidate_terms() then kept three of them ("best-selling", "rush replenishment", "scheduled
delivery") and dropped "stockout" itself entirely, even though it appears verbatim in two answers.
On reflection this isn't obviously wrong: those three are arguably three genuinely separate
definitional questions (what counts as best-selling, what counts as urgent enough to rush, what
counts as the delivery schedule), not pure synonyms of each other, so the model may have been
reasonably declining to force-merge them. What's genuinely uncertain is whether asking a real
requester three separate, near-identically-worded "when you say X, what makes something count"
questions in a row is good interview design or just noise; this run can't settle that on its own,
since this script answers every layer 07 definition question with the same canned text (a harness
limitation, not something to read as the tool giving three identical answers).

**3. `consolidate_terms()` timed out at the default 60 seconds once ten candidates and the full
known_fields context were in the prompt**, and only succeeded once retried with `timeout_seconds`
raised to 150. The default was set against e4's original single-question judge() calls; a
ten-candidate consolidate_terms() call late in a long interview is a meaningfully bigger prompt.
Worth raising the default, or trimming what's sent, rather than leaving requesters to hit a
`ClaudeCliError` on a real interview that happens to queue a lot of terms.

**Not fixed here**: this is a finding, not a fix. e9 stays marked done on the tracker for the
control-flow work it actually built and already verified (the redirect and consolidation
mechanism itself runs correctly, per this same run completing end to end); these three points are
new evidence about real-model prompt quality once fed genuinely long interview content, tracked
separately rather than silently patched into a "done" item's claim.

## Reframe invention fix, and a second live run (13 September 2026)

**What changed**: finding 1 above, a live `reframe()` call inventing two product names never given
in the interview, was judged serious enough to fix rather than leave parked, since it is a direct
miss against both `reframe()`'s own prompt instruction and CLAUDE.md's claim-integrity rule ("The
tool never invents a requirement... A plausible guess presented as a requirement is the worst
possible output"). `ClaudeCodeReasoner.reframe()`'s prompt was rewritten with an explicit,
much stronger constraint: it may only reuse words, phrases, names, categories or numbers that
appear verbatim in the requester's prior reply or in what is already known from the interview, it
must not invent, guess or extrapolate a plausible-sounding specific even if it would read better,
and when there isn't enough already stated to build a concrete worked example from, it must fall
back to a plainer, more general version of the question instead of reaching for an invented one.

`tests/test_reframe_prompt.py` was added as a regression guard: it mocks `subprocess.run` and
asserts the strengthened wording is actually present in the prompt sent to `claude -p`. This
cannot prove a live model honours the instruction, only that someone editing this method later
can't silently drop the constraint without a test failing. Full suite: 44/44 passing.

**Second live run**: `examples/synthetic/verify_against_claude_code_reasoner.py` was rerun
unchanged (interview 1, same scripted requester answers) against the tightened prompt, to check
actual model behaviour, not just trust the new wording. Result: one live reframe fired again (a
different trigger this time, and a different one from the first run), and this time it stayed
fully grounded.

The trigger was layer 07's definition question for the term "what we'd expect to sell": the
harness's canned definition text is circular when applied to that specific term (it defines the
term using the term itself), which the model correctly flagged as too vague to test and reframed
as: "When does a shelf actually need topping up, in your eyes: the point where what's left in the
stockroom won't get it through to the next delivery truck, or the point where it hits zero?" Both
"stockroom" and "delivery truck" and "hits zero" are concepts already present, near-verbatim, in
the requester's own stated definition text earlier in the transcript. No new product name, number
or category was introduced. Unlike the first run's fabricated "trail runner packs" and "size 10
hiking boots", nothing here is traceable to anywhere other than what the requester (or the
harness, standing in for them) had already said.

The other two findings from the first run were not the subject of this fix and behaved
similarly again: `extract_terms()`/`consolidate_terms()` queued and kept a different set of four
terms this time ("best-selling", "rush top-up", "what we'd expect to sell", "scheduled delivery"),
still not converging on a single "stockout", underscoring that term-extraction breadth is a
separate, real, still-open question (tracked as its own item, not resolved by this fix). The
interview reached 100% readiness (39/39 fields) with a coherent business ask and technical spec
either way.

**Honest read of what this proves**: one clean run is one data point, not proof the model can
never invent an unstated detail in a reframe again; `reframe()` calls a nondeterministic model, and
the previous run's own three findings are proof that behaviour genuinely varies run to run. What
it does show is that the specific failure mode caught in the first run (inventing a plausible
brand-appropriate specific) did not recur under a tightened, more explicit instruction, on a run
that gave the model a genuine reason to reframe again. Worth treating as resolved-and-watched, not
closed-and-forgotten: any future live run of this harness, or a real interview, is the next check,
and `tests/test_reframe_prompt.py` guards the wording from silently regressing in the meantime.

## e8 scope: overlap detection and the dependency map (13 September 2026)

**What e8 is, precisely**: two related but separate outputs, both named in CLAUDE.md's retained
knowledge section, both blocked since e3 on having no real interview data to design against.
Unblocked by e11's synthetic dataset (docs/synthetic-dataset.md), which supplies actual cases to
design each against instead of a guess.

**First finding, before any design: the schema has no structured "who".** Every field that names
a team or a person, `blast_radius`, `audience_breadth`, `downstream_dependencies`, `steward`,
`decision_rights`, `access_approver`, is free text. The synthetic dataset's own interview titles
("Store Operations Manager", "Digital Marketing Manager") exist only in docs/synthetic-dataset.md,
never in the ledger or the database; `interviews` (storage.py) is just `id, created_at`, nothing
else. This matters for scope: a dependency map that claims to know "Marketing" and "Finance" are
distinct, comparable entities across interviews would be inventing a normalisation the data
doesn't actually support today. What the schema can honestly support right now is showing what
each interview said in its own words, side by side, not resolving "the regional merchandising
lead" and "regional merchandising" into one node on a graph. That resolution is a real, separate
piece of work, not a free side effect of what's already collected.

**Second finding: overlap detection splits into three cases of different difficulty, and one of
them is already half-built.** Per docs/synthetic-dataset.md's "What this surfaces for e8":

1. Same term, requesters agree ("stockout", Store Ops and Supply Chain). Already captured today:
   layer 07's competing-definition check runs a real retained-knowledge lookup
   (`SqliteRetainedKnowledge.definition_for`) and the answer is stored as
   `competing_definition_check::{term}`, tagged stated, against the exact same term key. Reading
   this back across every interview on file is a plain SQL query over `field_records`, no new
   reasoner call and no invention: the judgement was already made live, by the requester, during
   the interview that reused the term.
2. Same term, requesters conflict ("active customer", Marketing vs Finance). Structurally
   identical to case 1, same query, the stored answer is just "doesn't match" instead of
   "matches". Both cases are one report away from existing data, not new engineering.
3. Different term, same underlying idea ("active customer" vs "engaged member", Marketing and
   Loyalty). This is the hard case and the one the synthetic dataset was built specifically to
   surface: `SqliteRetainedKnowledge.definition_for` matches on exact term text, so this pair
   produces no signal at all, not even a "doesn't match", silence. Catching it needs a genuine
   semantic judgement (do these two locked definitions describe the same thing), which means a
   reasoner call, and it cannot be exact-string matching no matter how the query is written.

**Design decision: overlap detection and the dependency map are a planning-time report, not a
per-interview output.** Every existing render (business ask, technical spec) is scoped to one
interview, produced the moment that interview finishes, and CLAUDE.md is explicit that
"self-serve" means the requester completes it alone with nothing extra required. Comparing one
interview against every other one on file, and worse, running a reasoner pass over all locked
terms, doesn't belong inside that path: it would slow down or complicate the one moment the
project has deliberately kept simple. CLAUDE.md's own framing agrees: overlap detection "matters
most at planning time, when a cohort of requests is being compared", not during intake. So e8 is
scoped as a separate script/report run on demand against the existing database
(`requirements_accelerator.db`), the same relationship cli.py already has to
examples/synthetic/run_all.py: reads the same file, adds nothing to the live interview path.

**Proposed phased build, structured first, semantic second, not built yet, this is the plan to
review before code is written:**

*Phase A, no reasoner calls, ships first*: a report that queries `field_records` for every
`term_locked::{term} = true` row, groups by exact term string across interviews, and for any term
touched by more than one interview prints each interview's definition side by side with its
recorded `competing_definition_check` verdict. This alone renders cases 1 and 2 correctly using
data that's already on the ledger, is fully unit-testable against the synthetic dataset's known
outcomes (stockout matches, active customer conflicts, on-time delivery conflicts the other
way), and needs no new judgement calls, so it can't invent anything by construction. The
dependency side gets the same treatment: for each locked term, list every interview's own
`downstream_dependencies`, `steward`, `decision_rights`, `access_approver` text verbatim,
grouped by term, not resolved into named entities. Honest output: shows what was said, not a
graph of what it means.

*Phase B, one batched reasoner call, not per-pair, ships second, only if Phase A's shape holds
up*: case 3 needs a semantic pass, but doing it as an O(n^2) reasoner call per pair of locked
terms doesn't scale and multiplies exactly the kind of cost e12 already flagged as a real
constraint (consolidate_terms's 150s timeout on one interview's worth of candidates). The better
shape is one batched call per report run: hand the reasoner the full list of locked terms and
their definitions once, ask it to group any that describe the same underlying concept, and treat
its answer the same way retained knowledge already works, as a flag to review, never as an
asserted fact. This is genuinely new engineering, not a report over existing fields, and it's
the part actually worth scoping carefully before building, not the part to start with.

**Open questions for Jay, not decided here**: whether Phase B is worth building at all given its
cost and nondeterminism, versus leaving semantic overlap as a human-reviewed report forever (Phase
A's side-by-side view already surfaces the raw material a person could spot the "active
customer"/"engaged member" connection from, just without the tool naming it); and whether the
dependency map's entity-resolution problem (normalising "regional merchandising" across differently
worded mentions) is worth its own future item, separate from e8, given it's the same underlying
problem applied to team names instead of term definitions.

**Decided (13 September 2026): build both, keep Phase B narrow.** Jay's call: worth building,
since exact-term dedup alone isn't the differentiated part, catching "active customer" and
"engaged member" as one idea under two names is. Explicitly scoped tight: one batched call per
report run, output always framed as a flag to review rather than an asserted fact (the same
framing retained knowledge's own competing-definition check already uses), and the dependency
map's entity-resolution problem stays parked, out of scope here, not folded in.

**Built, same day**: `engine/overlap.py` (Phase A: `term_groups()` and `dependency_view()`, pure
queries over `field_records`, no reasoner call) and `overlap_report.py` (the runner, `python
overlap_report.py [db_path]`). `Reasoner` gained `find_conceptual_overlaps(definitions)`,
implemented on both `StubReasoner` and `ClaudeCodeReasoner`; the real implementation defensively
drops any term the model names that wasn't actually a key of `definitions`, a stricter check than
`consolidate_terms` currently applies to its own output, added here specifically because e12
already showed a live reasoner call can say more than it was given. Phase B is opt-in via
`--semantic` on the runner, since it's a real model call with real cost and nothing about running
the base report should require it. Verified against the synthetic dataset: `tests/test_overlap.py`
(18 tests, both phases' data-shaping logic, run against a real SQLite fixture built from all ten
interviews, no reasoner involved) and `tests/test_conceptual_overlap.py` (6 tests, mocked
`subprocess.run`, same limits as `test_reframe_prompt.py`: proves the prompt and the hallucinated-
term filter, cannot prove a live model's grouping judgement is right). Full suite: 68 tests, all
passing. Correction to what this document said a moment earlier in this same session: the `claude`
CLI is in fact installed and logged in in the cloud sandbox this build runs in (it shares the
session that's editing this repo), the same place e12's live verification actually ran; "on
jaypc" was never accurate for either of them, and saying Phase B needed jaypc specifically was
wrong.

## Phase B run against a live model, and a genuinely open finding (13 September 2026)

**What happened**: `python overlap_report.py --semantic` run against a fresh copy of the synthetic
dataset, the real `ClaudeCodeReasoner`, not `StubReasoner`. Two safety properties held: it
finished cleanly, no errors, no timeout; and a sanity check with a deliberately obvious duplicate
pair (two near-paraphrased "stockout"-style definitions) correctly returned as one group, proving
the mechanism can produce a real result, not just always come back empty from a parsing bug.

**But it did not flag the dataset's own headline case.** "Active customer" and "engaged member",
the pair `docs/synthetic-dataset.md` was specifically built to surface as "the same underlying
idea... described by two different teams", came back ungrouped. Checked three ways before
accepting that as real rather than a fluke: against the full six-term set the actual report ran
(empty); isolated to just those two terms alone, ruling out other terms diluting the comparison
(still empty); and substituted marketing's original definition (recency of any-channel order,
closer in spirit to "engaged member" than the finance-conflict definition `locked_term_definitions`'
recency convention actually picked) in place of finance's (still empty). All three: no group.

**Asked the model directly why, outside the actual method, to see its reasoning** (the production
prompt deliberately suppresses explanation, so this used a separate one-off prompt purely for
diagnosis): "They're genuinely two different things: 'active customer' is a transactional
definition (placed an order anywhere in 90 days), while 'engaged member' is a
behavioural/attention definition (redeemed points or opened an email in 60 days) that explicitly
rejects mere card status as sufficient. Different underlying concept (purchase behaviour vs.
program engagement), different time window, and different data sources, so treating them as
synonyms would conflate two things the business itself has distinguished."

**This is a defensible answer, not an obvious miss.** Read plainly, the model is making a real,
specific distinction (purchase activity versus loyalty-program interaction) that the two
definitions, as actually worded, genuinely support. `docs/synthetic-dataset.md`'s framing of these
two as "the same underlying idea" was this project's own design-time assertion when the scenario
was written, not something independently confirmed against a real requester. The honest reading
of this result isn't "Phase B missed an obvious case", it's closer to "Phase B's caution
(`find_conceptual_overlaps`'s prompt explicitly says a vague thematic similarity is not enough,
written that way in direct response to e12's invention finding) may be calibrated toward too few
false positives at the cost of missing a real one, or the synthetic scenario's own premise was
never as settled as it read when it was written." Both are real possibilities and this one run
doesn't distinguish between them.

**Decided (13 September 2026): leave the prompt as-is, deliberately conservative.** Jay's call:
this tool's job is the legwork, not the final governance judgement, he picks up whatever it
surfaces and clarifies with the actual stakeholders regardless, so a Phase B that stays quiet on a
genuinely uncertain pair is the correct failure mode, not a bug to tune away. Loosening the
prompt to catch more borderline cases would trade a known, defensible cost (an occasional real
connection stays unflagged, for a human to catch some other way) for an unknown one (more
thematic-similarity false positives, exactly what this prompt's wording was written after e12 to
avoid). Not revisited unless a real interview cohort shows this conservatism actually costing
something in practice.

## Portability seam review (a0, 13 September 2026)

CLAUDE.md's "Portability seams exist from the first commit" names four things that must sit
behind an interface and never leak into the interview logic: storage, model provider, secrets, and
user identity. e3 and e4 built two of these as decisions (SQLite, the Claude Code CLI). This entry
is the formal review CLAUDE.md's own discipline calls for: not new code, a check that what exists
actually satisfies the seam it was meant to, and an honest statement of what doesn't exist yet.

**Storage and model provider: built correctly, confirmed by re-reading the actual wiring, not just
the class names.** `engine/interview.py` imports only the abstract types, `Reasoner` and
`RetainedKnowledge`, never a concrete class; `Storage` doesn't appear in `engine/interview.py` at
all, save and load happen at the `cli.py`/`app.py` boundary, outside the interview loop entirely.
Both `Storage` and `RetainedKnowledge` are `ABC`s with `@abstractmethod`-only contracts and exactly
one production implementation each (`SqliteStorage`, `SqliteRetainedKnowledge`), the shape a second
environment's implementation would slot into without touching `engine/interview.py`. `Reasoner`
carries six abstract methods (`judge`, `extract_terms`, `summarise_for_reflection`, `reframe`,
`consolidate_terms`, `find_conceptual_overlaps`), two concrete implementations (`StubReasoner` for
scripted/test use, `ClaudeCodeReasoner` for real model access), same shape. All 68 tests still pass
against this reading with no changes made, so this is a review, not a refactor.

**Secrets and user identity: not built, and there is nothing to point to.** A repo-wide search
found no secrets handling anywhere (`ClaudeCodeReasoner` shells out to an already-authenticated
`claude` CLI, so the tool itself never touches a credential) and no user-identity concept anywhere
(one interview, one local process, nobody to distinguish from anybody else yet). Per this project's
claim-integrity rule, an absent seam left undocumented reads as an oversight; naming it here is the
honest version. Neither is a defect in the current single-user, locally hosted design, CLAUDE.md
itself scopes "local first, port later", but both become real the moment a3 (Streamlit in
Snowflake) is actually built rather than merely documented: Streamlit in Snowflake needs a secrets
seam (Snowflake's own secrets object, not an env var) and a user-identity seam
(`st.experimental_user`) that don't exist today in any form, not even a placeholder like
`NoRetainedKnowledge`. Recorded here so a3, if and when it's picked up, starts from a known list of
two seams to build rather than rediscovering the gap.

**Outcome**: a0 closed as a review, not a build. Storage and model provider seams pass; secrets and
user identity are named as genuine, currently-empty gaps, deferred to a3 rather than built ahead of
need, consistent with "one tool finished beats three started."

## a1 scope: the Snowflake semantic view adapter (13 September 2026)

CLAUDE.md names the target directly: "the first adapter targets Snowflake semantic views built
from dbt models, because that is what makes the output directly consumable by Cortex Analyst and
Snowflake Intelligence." Before writing code, the same question e8's scoping asked applies here:
what does this adapter actually have to work with, and what would it have to invent to hit that
target as stated.

**The real finding**: the interview never asks for physical schema. No question anywhere in
`docs/coaxing-protocol.md` asks for a table name, a column name, or a dbt model reference, because
a non-technical requester genuinely cannot answer that, the tool's entire premise. `source_systems`
(layer 04) captures where the data lives in business language ("the point-of-sale system"), not a
queryable reference. So an adapter that tried to emit a fully resolved `CREATE SEMANTIC VIEW`
against real dbt models would have to invent every table and column reference in it, which is
precisely the kind of hollow, undefendable claim CLAUDE.md's claim-integrity rule already rules out,
and exactly the discipline `find_conceptual_overlaps` (e8 Phase B) was built to for a different
reason.

**Decided: build a scaffold, not a resolved view.** The adapter reads one completed interview (not
a cross-interview report like e8, one interview in, one semantic view out, matching CLAUDE.md's own
framing) and emits a `CREATE SEMANTIC VIEW` skeleton with every business-side piece filled in for
real, primary measure, locked term definitions, synonyms, exclusions, grain, and every physical
table or column reference left as an explicit `TODO_*` placeholder for a data engineer to fill in
against the actual warehouse. Nothing physical is ever invented.

**A second, smaller decision, stated rather than hidden**: the ledger doesn't record whether a
locked business term is conceptually a measure or a dimension, so this adapter takes a stated
position rather than guessing per term: `primary_measure` becomes the one `METRICS` entry, every
other locked layer 07 term becomes a `DIMENSIONS` entry, a named category or segment. Layer 07's own
question, "what makes something count", is fundamentally about membership in a category, which
makes DIMENSIONS the more conservative read, but it is a read, not something the ledger states
outright, so it's named plainly in the generated file's own header rather than left as a silent
modelling choice.

**Output target confirmed as SQL, not YAML**: Snowflake also has a Cortex Analyst
`semantic_model.yaml` format covering similar ground, a different artifact. CLAUDE.md names
semantic views specifically, so that's what this targets. Decided with Jay before building.

**Built same day**: `engine/semantic_view.py` (`build_semantic_view_plan`, reading one interview's
`Ledger`, and `render_semantic_view_sql`, the DDL renderer) and `semantic_view_adapter.py` (the
runner, `--list` to see what's on file, an interview id to generate its scaffold). `CREATE SEMANTIC
VIEW` syntax (clause order, `WITH SYNONYMS`, `COMMENT =`, `PRIMARY KEY`) was verified against
Snowflake's own SQL reference and its worked example on docs.snowflake.com on 13 September 2026, not
recalled from memory, the same standard this repo holds its own documentation to. Where an
interview hasn't established enough to meet Snowflake's own requirement (at least one `DIMENSIONS`
or `METRICS` entry), the adapter says so plainly rather than emitting DDL it already knows is
invalid.

`tests/test_semantic_view.py` (17 tests) verifies this against the synthetic dataset's store-ops-01
interview (a clean primary measure, grain, two breakdown dimensions and one locked term with quoted
synonyms and no exclusion) and cx-04 (a locked term with a real exclusion), plus a from-scratch
interview run through `run_interview` and `Storage.save_interview` / `load_interview` to prove the
storage-backed path matches building a plan directly from a ledger. Explicitly checks the
claim-integrity property that matters most here: every physical reference in the rendered SQL is
one of the adapter's own `TODO_*` constants, never a value the interview actually gave. Full suite
85/85.

**What's still a known limitation, not fixed here**: identifiers are slugged from whatever free
text the requester gave (`primary_measure`'s full sentence becomes the metric name), so a long or
run-on answer produces a long, valid but unwieldy identifier. Cosmetic, not a correctness issue,
left as-is given the project's own "don't gold-plate one tool" discipline.

## a3 spike (13 September 2026)

a3 (Streamlit in Snowflake) was deferred on 12 September: trial time was committed to the SE
Portfolio Demos sequence (Listening Lens, then Iceberg), and this project's portfolio value was
judged to be the interview design, not the hosting. Revisited today once Jay had trial capacity
in hand, with the trade-off named plainly rather than silently reopened: this still draws on the
same trial budget as that sequence, and it cuts against his own 13 September instruction not to
over-invest time in this project specifically. Decided as a small, bounded spike rather than the
full port: prove the two things that were genuinely unverified before committing real time to
the other two seams (storage, delivery) and a full deployment.

**What was actually unverified, narrowed from the original a3 plan**: not "does Streamlit run in
Snowflake at all", Listening Lens already answers that, and not "is Cortex unblocked on this
trial account", also already true (Listening Lens's Discover tab). The two real open questions
were whether the model-provider seam (`ClaudeCodeReasoner` swapped for a Cortex-backed reasoner)
produces sensible judgement calls through a different transport, and whether `bridge.py`'s
background-thread-plus-queue pattern, which lets the blocking interview loop run under
Streamlit's rerun model, survives inside Snowflake's compute environment rather than a laptop.

**Built**: `engine/reasoner.py` refactored, `judge`, `extract_terms`,
`summarise_for_reflection`, `reframe`, `consolidate_terms` and `find_conceptual_overlaps` moved
onto a new shared base, `_PromptedReasoner`, with only `_call(prompt) -> str` left abstract.
`ClaudeCodeReasoner` keeps its subprocess `_call`, behaviour unchanged (85 tests still passed
after the refactor, before any new code was added). `engine/cortex_reasoner.py` adds
`CortexReasoner(_PromptedReasoner)`, calling `AI_COMPLETE` (not the legacy
`SNOWFLAKE.CORTEX.COMPLETE`, which Snowflake's own docs mark for deprecation by the end of 2026,
building a portfolio piece against a function already flagged for removal would be exactly the
undefendable choice CLAUDE.md's claim-integrity rule rules out) through
`get_active_session().sql(..., params=[...])`, qmark-bound, not string-interpolated, for the
same reason `engine/semantic_view.py` never string-formats a value into DDL. Kept out of
`engine/reasoner.py` itself and imported only inside `CortexReasoner.__init__`, so `cli.py` and
every existing test keep running with no Snowflake packages installed, unchanged. Default model
`claude-sonnet-5`, confirmed present in Snowflake's Cortex model availability docs on 13
September 2026, not recalled from memory, overridable since regional availability varies.

`app.py` gained one function, `_select_reasoner`, which tries `get_active_session()` and falls
back to `ClaudeCodeReasoner` on any failure, so the same file is what's deployed to Snowflake
and what runs locally, unmodified otherwise. `snowflake.yml` (warehouse runtime, no compute
pool, since nothing here needs container-runtime packages or Native App-style consumer
installability like Listening Lens) and `docs/a3-spike-deployment.md` (the actual deploy and
verification steps) round out what's needed to run it. `tests/test_cortex_reasoner.py` (5
tests, a faked `snowflake.snowpark.context` via `sys.modules` since the real package isn't
installed here, matching the CLAUDE.md dependencies-stay-short reasoning `cortex_reasoner.py`'s
own docstring gives) proves the calling convention and that `CortexReasoner` shares every prompt
with `ClaudeCodeReasoner`. Full suite 90/90.

**Run live against the trial account on 13 September 2026, via Claude Code on jaypc.** Both real
questions are answered: `bridge.py`'s background-thread-plus-queue pattern completes cleanly
inside Snowflake's compute environment (no hangs across a full interview, one call ran ~25s,
most 5-8s, but every one returned), and the model-provider seam works, once two bugs the live
run actually surfaced were fixed. A full interview ran end to end: 35/35 fields collected, status
"ready to size", both the business ask and technical spec rendered, and `SqliteStorage` /
`deliver_documents` both completed without error.

**Deployed into `REQUIREMENTS_ACCELERATOR.PUBLIC`, a database created for this spike**, not
Jay's personal database (`snow` refused a stage there: "Stages cannot currently be created in a
personal database") and not anything under Listening Lens's Native App objects, keeping the two
projects' trial-account footprints separate as intended.

**Connection: Programmatic Access Token, not browser SSO.** `--authenticator externalbrowser`
failed outright on this trial account (`390190: There was an error related to the SAML Identity
Provider account parameter`), because a fresh trial has no SAML IdP federated to it, the
authenticator needs. Snowflake CLI's documented PAT pattern,
`authenticator = "PROGRAMMATIC_ACCESS_TOKEN"` plus `token_file_path`, also failed on the
installed CLI (v3.1.0, well behind the v3.27.0 current release): `251006: Password is empty`,
most likely a version gap rather than a config mistake, since the config matched Snowflake's docs
exactly. What actually worked: the PAT value placed directly in the plain `password` field with
the default authenticator, the same "use a PAT anywhere a password goes" fallback Snowflake
documents for BI tools with no native PAT support. Recorded here since the documented method
didn't work as documented on this CLI version, and the fallback isn't obviously the first thing
to reach for.

**Two real bugs the live run found, both fixed and covered by tests, neither guessable from
reading the code beforehand**:

1. **Streamlit-in-Snowflake's bundled Streamlit build doesn't have `st.rerun()`**, only the older
   `st.experimental_rerun()`, so every rerun call in `app.py` raised `AttributeError` the moment
   the interview was started. This directly falsifies this entry's earlier claim that `app.py`
   runs "unmodified" apart from `_select_reasoner`, it does not. Fixed with a small `_rerun()`
   helper (`getattr(st, "rerun", None) or st.experimental_rerun`) used everywhere `app.py`
   previously called `st.rerun()` directly; local Streamlit installs have `st.rerun()` and never
   touch the fallback.
2. **`AI_COMPLETE` wraps every reply, short or long, in a full JSON string literal**: outer
   quotes plus proper escaping, so `judge()`'s expected `"yes"` came back as the four characters
   `"yes"` (breaking `.startswith("y")`, every judge() call silently read as False) and
   `summarise_for_reflection()`'s multi-line paraphrase came back with literal `\n` two-character
   sequences instead of real newlines. Fixed in `CortexReasoner._call()` with `json.loads()` on
   the raw response, falling back to the raw text when it isn't valid JSON, rather than
   hand-stripping quotes, which would have left the escaped newlines broken.
   `ClaudeCodeReasoner`'s `claude` CLI output doesn't exhibit this, so the unwrap lives in the
   Cortex adapter only. Confirmed directly with `SELECT AI_COMPLETE('claude-sonnet-5', ...)`
   before writing the fix, not inferred from the app's behaviour alone.

**One packaging issue, not a Cortex or Streamlit issue**: `snow streamlit deploy` failed
(`253006: Not a file but a directory`) trying to upload `engine/__pycache__`, a leftover local
build artifact already gitignored but present on disk. Cleared before each deploy; worth an
`.snowflakeignore` or a pre-deploy clean step if this spike becomes the real a3 port.

**One cosmetic finding, not fixed**: the model's own phrasing in a couple of generated questions
used an em dash, which is against this repo's own no-em-dash rule for "generated output" in
CLAUDE.md. Not something `_PromptedReasoner`'s prompts currently instruct against; worth a prompt
tweak if this becomes the real port, not blocking for a spike whose job was the transport and
threading, not prompt polish.

## e13: the document template (14 September 2026)

Named on the build tracker as the last real piece of the puzzle once a3 was verified: everything
the interview collects was already rendering as terse plain text (engine/render.py, since v0.1 of
docs/output-template.md), correct in content but not something either persona in CLAUDE.md's
two-persona split would actually hand someone. The requester's business ask in particular is
meant to be "something to show their own colleagues"; a wall of monospaced text does not do that.

**Decided on the train, before any code was written**: Word (.docx) for both documents, not PDF
or a second markdown variant, since a requester or a data lead editing or annotating a Word file
needs no extra tooling. A light letterhead on both (title, document type, interview id, date), so
either document still identifies itself once it's saved somewhere detached from this tool. And,
for the technical spec specifically, the provenance state (stated, inferred, assumed, missing)
shown as a coloured badge rather than a bracketed label, using the same green/blue/amber/red the
build tracker artifact already uses for status, because a plain-language answer sitting next to
its engineer-grade translation with the gap visually obvious, rather than something read carefully
to notice, is the single clearest demo moment this tool has.

**Built**: `engine/docx_render.py`, a new module and the only place in the engine that imports
python-docx, the same dependency-isolation reasoning this file already gives `engine/reasoner.py`
keeping `engine/cortex_reasoner.py`'s `snowflake.snowpark` import out of itself. It imports its
field lists and gap logic (`LAYER_FIELDS`, `LAYER_NAMES`, `ALL_FIELDS`, `BLOCKING_FIELDS`,
`GAP_REASONS`, `GAP_PLAIN_LANGUAGE`, `_terms_in_ledger`) directly from `engine/render.py` rather
than re-deriving them, so the two renderers cannot drift apart on what a gap is or which fields
belong to which layer. `render_business_ask_docx` and `render_technical_spec_docx` mirror
`render_business_ask`/`render_technical_spec`'s structure field for field; the one addition is the
badge, built by hand (`_shade_cell`/`_badge`) since python-docx exposes no public cell-fill API,
the standard `w:shd` OXML recipe instead.

`engine/delivery.py` changed to accept anything with a `.save(path)` method rather than a string,
and writes `.docx` files instead of `.md`, staying free of a python-docx import itself per its own
"thinnest layer" docstring, the same duck-typing reasoning `cortex_reasoner.py` already models.
`cli.py` and `app.py` both changed the same way: the terminal printout and the on-screen recap
still use `engine/render.py`'s plain-text functions unchanged, only the `deliver_documents` call
now builds and passes the two Word documents from `engine/docx_render.py`. `docs/output-template.md`
gained a short section mapping this structure onto the Word template; no content decision changed,
only its presentation.

`tests/test_docx_render.py` (15 tests) covers the layer-00 gate, the ready/not-ready readiness
badge and its colour, the provenance badge colour for each of the four states, the definitions
section with and without a term, and the reporting appendix's primary_measure gate, reading
documents back through python-docx's own object model rather than raw XML except for the one
OXML cell-fill lookup this module has to hand-roll to verify a badge's colour at all.
`tests/test_delivery.py` was rewritten to build real Document fixtures and reopen the saved
`.docx` files rather than asserting on plain-text content, since that is now genuinely what the
module does. Full suite 105/105. Two real generated documents (`render_business_ask_docx` and
`render_technical_spec_docx` against a hand-built ledger with a mix of stated, inferred and
assumed fields) were also saved and reopened directly, not just exercised through the test suite,
confirming both actually produce a valid, readable `.docx` file with the expected structure
before this entry was written.

## Test count correction (29 September 2026)

The e13 entry above closed with "Full suite 105/105", accurate when it was written. A
documentation audit found the live count is 109: `tests/test_cortex_reasoner.py` grew from the 5
tests the a3 spike entry above counted to 9, with no note logging the addition, a gap against this
file's own "document as you go" convention. `README.md`'s Testing section is corrected to match.
No behaviour changed, only the count was stale.
