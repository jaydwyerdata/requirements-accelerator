# Requirements Accelerator

A curious business analyst at the front, a data engineer at the back.

Built for a data engineer running their own request pipeline with no business analyst or
project manager support, the individual contributor who ends up doing all three jobs because
nobody else is. A self-serve tool that interviews the person requesting a data solution, in plain
language, and turns a vague ask into concrete data and solution requirements. Its real job is
triage: before any investigation time gets spent, it answers one question, is there enough
substance here yet to be worth my attention. Whether a ready request is actually worth doing next
is a separate call it deliberately leaves alone; readiness and value are two different axes, and
this tool only ever grades the first.

## Status

Feature-complete for a single-user portfolio build, not production software: every interview layer
runs end to end, both output documents render, delivery writes finished `.docx` files, and the
same app has been run live in two different environments (below). No auth, multi-tenancy or hosted
service, by design, see Scope. `python cli.py` walks all nine interview layers (00 through 09) from a terminal, including layer 07's
per-term definition loop, then prints a business ask and the full technical spec from what it
collected. Every interview is saved to a local SQLite file (`requirements_accelerator.db`,
gitignored - it's runtime data, not source), so a later interview that touches the same term sees
what a prior one locked in as its definition, rather than starting from nothing every time. Model
access (e4) is built and now verified end to end: every judgement call the interview makes (is this
a solution in disguise, does that name more than one system, is that definition too vague to test)
goes to `ClaudeCodeReasoner`, a real Claude Code CLI subprocess, not a person at the keyboard. It
needs the `claude` CLI installed and logged in on whatever machine runs `cli.py`; see
`docs/architecture-decisions.md` for the reasoning and for the live terminal run that confirmed it
actually works, not just that it parses correctly against mocked output.

That live run surfaced a real gap: the interview asked its fixed question list correctly but felt
transactional rather than conversational, no way to say "I don't understand" or "not sure" and get
a different framing back, and layer 07's term queue picked up duplicates and structural words
rather than only genuine ambiguous business terms. `docs/interview-branching.md` v0.2 and
`docs/architecture-decisions.md`'s `reframe` revision specify the fix; it is built, every question
now classifies a reply and reframes rather than accepting or looping forever, and all five
`examples/` scripts and the full `tests/` suite (see below) pass against it under `StubReasoner`.
A real regression in this slice, an unguarded `consolidate_terms` call that should only fire when
a term is actually queued, shipped believed-fixed and wasn't; the new automated tests caught it
immediately, see `docs/architecture-decisions.md`'s note on it. That question, whether
`ClaudeCodeReasoner`'s real `judge`, `reframe` and `consolidate_terms` calls behave sensibly against
real interview content and not just correct control flow, has since been run twice, live, against
the real model (12 and 13 September 2026), and both runs found real issues rather than a clean
pass. The first caught `reframe()` inventing two product names the requester never gave, a direct
miss against its own prompt instruction; the prompt was tightened to forbid inventing anything not
verbatim in what the requester actually said, and a rerun the next day reframed again under a
different trigger and stayed fully grounded, treated as resolved and watched, not closed and
forgotten, since one clean nondeterministic rerun is a data point, not proof. `extract_terms` and
`consolidate_terms` converging on the term an interview is obviously about is a separate, still open
question, unresolved across both runs, tracked in `docs/architecture-decisions.md` rather than
silently patched over.

A locally hosted Streamlit frontend (e7) now exists (`app.py`), the same `run_interview` `cli.py`
runs, on a background thread bridged to Streamlit's rerun model via `bridge.py`; see
`docs/architecture-decisions.md`'s e7 entry for how and why. It now implements
`docs/interview-ux.md`'s widget-per-question design too: `engine/protocol.py`'s `Question.choices`
already encoded the free-text/multi-choice/hybrid/banded classification as data, so `bridge.py`
passes it straight through and `app.py` renders buttons for a closed answer set, buttons plus an
always-visible text box when "something else" is one of the options, and a plain text box
otherwise, with no per-field lookup table needed. Layer 07's competing-definition check, the one
question whose choices depend on runtime state rather than a fixed list, now also renders as
buttons: `matches / doesn't match / not sure` when retained knowledge has a prior definition for
the term, `worth flagging / not a concern / not sure` when it doesn't, exactly as
`docs/interview-ux.md` specifies. Confirmed working end to end on a real browser (`streamlit run
app.py`) on 12 September 2026: the rendered widgets behave as intended, and a real mock interview
against `ClaudeCodeReasoner` surfaced two real gaps, both fixed the same day, an internal
"LAYER NN" header leaking into the requester-facing transcript, and four closed-choice questions
that read as generic out of context (`blast_radius`, `fan_out_risk`, `cardinality_risk`, `volume`,
reworded in `docs/coaxing-protocol.md` and `engine/protocol.py`). See
`docs/architecture-decisions.md`'s e7 and e9 entries and "First real mock interview, findings" for
the full detail.

Delivery (a2) is built: once an interview finishes, both `cli.py` and `app.py` write the two
rendered documents to disk via `engine/delivery.py`, one to a business-ask folder and one to a
technical-spec folder (gitignored local defaults, `delivered/business-ask/` and
`delivered/technical-spec/`), never the same folder for both, since the technical spec is
internal-only and the business ask isn't. Point those two folders at a synced OneDrive- or
SharePoint-synced directory instead to get finished documents there with zero integration or
tenant configuration; see `docs/architecture-decisions.md`'s a2 entry for the full reasoning and
the real design risk it was built to avoid.

What actually lands in those two folders (e13) is now a letterheaded Word document, not plain
text: `engine/docx_render.py` renders the same ledger content `engine/render.py` already prints to
a terminal or a browser tab, as a `.docx` file with a title, document type and interview id on
every page, and a coloured badge on the technical spec's provenance states (green stated, blue
inferred, amber assumed, red missing), so what came from the requester and what the tool inferred
or assumed is visible before you've read a word of it. See `docs/output-template.md`'s Word
template section and `docs/architecture-decisions.md`'s e13 entry.

## Running it

```
python cli.py                              # terminal
streamlit run app.py                       # local browser UI (e7, confirmed working 12 Sep 2026)
snow streamlit deploy --replace --open     # Streamlit in Snowflake (a3 spike, see below)
```

The first two run `ClaudeCodeReasoner`, which needs the `claude` CLI installed and logged in on
whatever machine runs them. Deployed into Snowflake, the same `app.py` swaps that for
`CortexReasoner` on its own (`_select_reasoner`, no CLI or login, Cortex is already part of the
account), so that path only needs the `snow` CLI configured against the trial account to deploy
it. All three need `pip install -r requirements.txt` (`streamlit`, `python-docx`) wherever they
run.

The Snowflake path was run live against a trial account on 13 September 2026 (the a3 spike, see
`docs/architecture-decisions.md`'s entry) and confirmed working end to end, but it is a bounded
spike, not a standing service. `docs/a3-spike-deployment.md` has the deploy steps, what to watch
for, and the teardown if it isn't still running.

See `examples/` for five scripted runs against the engine directly: a clean layer 00
pass, one that trips the layer 00 redirect and self-corrects within the two-attempt cap, a full
nine-layer pass that locks a definition in layer 07 and promotes an inferred field on
confirmation, one that exercises both "not applicable" branches (layer 02's drill-through, layer
04's system of record) plus a reflection that gets no reaction, and one that proves retained
knowledge actually persists: a term locked in one interview shows up as a concrete question in a
second one against a throwaway database. Useful for seeing the whole flow, and every branch of it,
without typing it out by hand.

`examples/synthetic/` is ten more scripted interviews, comprehensive and deliberately not
self-contained: a made-up mid-size retailer, Alderglen Outfitters, across ten different business
functions, run together against one shared fixture database so several of them can genuinely
agree or disagree with a term a prior one already locked. Built because e8 (below) needed real
interview data on file before a useful query design was obvious, and ten real requesters weren't
available. `python -m examples.synthetic.run_all` runs the whole set and prints what it found;
`docs/synthetic-dataset.md` explains the scenarios and what they surfaced, most usefully that two
different teams describing the same underlying idea in two different words produces no overlap
signal at all today, which turns out to be the single most useful finding for designing e8
against.

## Testing

```
python -m unittest discover -s tests
```

`tests/` wraps every one of those five scenarios, plus `bridge.py`'s thread/queue handoff, the
per-question `choices` plumbing app.py's widget layer depends on, `engine/delivery.py`'s
disk-writing behaviour (a2, now `.docx` files, see below), `engine/docx_render.py`'s letterhead,
readiness badge and per-field provenance badge colours (e13), the ten-interview synthetic dataset
below, e8's overlap report, a1's semantic view adapter, and a3's `CortexReasoner` calling
convention against a faked Snowpark session (all below), in real pass/fail assertions (stdlib
`unittest`, no new dependency beyond `python-docx`, 105 tests as of this writing), reusing each
demo script's scripted dialogue by import rather than duplicating it. The demo scripts stay as
readable, runnable walkthroughs; this is what actually catches a regression rather than relying on
someone reading printed output. See `docs/architecture-decisions.md`'s Testing section for why
this exists.

## The problem

Data teams without business analyst support spend their time translating. A request arrives as "I
need to see our renewals", and somewhere between that sentence and a working data product, someone
has to work out what one row represents, which system is authoritative, whether history needs
tracking, and what the requester actually means by "renewal".

Most requirements tooling stops before any of that. It writes a tidy user story and leaves every
expensive technical decision unasked, which means the translation work still lands on the engineer,
usually in a series of follow-up conversations that neither side enjoys.

The people making the requests cannot answer those questions directly, and it is unreasonable to
expect them to. Nobody outside a data team knows what grain is. Everybody knows what one row of a
spreadsheet would represent.

Without a business analyst absorbing that translation work, it lands directly on whoever owns the
backlog, alongside everything else already on their plate. Every incoming request needs roughly
the same investigation before it is even clear whether it is ready to size, work that competes for
the same hour as actually building things.

## What it does

The tool interviews the requester in plain language, never using technical vocabulary, and infers
the technical requirements from answers a non-technical person can comfortably give. Behind the
conversational surface it is reasoning as a data engineer, a solution architect and a BI developer
would.

It produces two documents from one interview:

- **A business ask**, in plain language, for the requester. What we understood about the problem
  and what happens next. It confirms comprehension while corrections are still cheap.
- **A technical spec**, for the data team. Grain, source and system of record, semantic layer
  definitions, reporting specification, access requirements, testable acceptance criteria, and a
  readiness score naming exactly what is still missing and who can resolve it.

Readiness and value are kept deliberately separate. The score above answers one question only, is
there enough here to size and build, never whether it is worth doing. That judgement, weighing a
ready request against everything else already competing for the same sprint, stays with whoever
owns the backlog.

It also accumulates knowledge across interviews, not to prefill later answers (which would quietly
homogenise the language of an organisation) but to ask better questions: a term one interview
locked a definition for gets checked against, not re-asked from nothing, the next time it comes up.

`overlap_report.py` (e8) surfaces that accumulated knowledge on demand, a planning-time report
across every interview on file, not something that runs during any one interview. `python
overlap_report.py` groups every term two or more interviews have used, shows what each said and
whether they agreed, and lays out a raw, unresolved dependency view (who each locking interview
named as a steward, approver or downstream team) for every locked term. Add `--semantic` for the
harder case exact-string matching can't see at all, two teams describing the same idea in
different words, one batched call to the real reasoner, always shown as a flag to review, never
as an asserted fact. Both built against `docs/synthetic-dataset.md`'s ten-interview dataset; see
`docs/architecture-decisions.md`'s "e8 scope" entry for what's deliberately still out of scope
(resolving "the regional merchandising lead" and "regional merchandising" into one entity, for
instance).

`semantic_view_adapter.py` (a1) is the first platform-specific output, turning one finished
interview into a Snowflake `CREATE SEMANTIC VIEW` scaffold aimed at Cortex Analyst and Snowflake
Intelligence. `python semantic_view_adapter.py <interview_id>` fills in every business-side piece
the interview actually captured (the primary measure, locked term definitions, synonyms,
exclusions, grain) and leaves every physical table or column reference as an explicit TODO
placeholder, never invented, since the interview never asks for physical schema in the first
place. See `docs/architecture-decisions.md`'s "a1 scope" entry for why that gap is real and what
this adapter deliberately does and doesn't do about it.

## Portability

Runs unmodified in two very different places: a laptop terminal and a Streamlit app deployed
inside Snowflake. Not a rewrite, not two versions to keep in sync, the same `app.py` and the same
`engine/` package either way.

The mechanism is the seam pattern CLAUDE.md commits to from the first commit: model provider,
storage, secrets and user identity are the four things that differ by environment, and none of
them are allowed to leak into the interview logic. `engine/interview.py` only ever talks to an
abstract `Reasoner`, never a concrete one. Locally that resolves to `ClaudeCodeReasoner`, shelling
out to the `claude` CLI; inside Snowflake it resolves to `CortexReasoner`, calling `AI_COMPLETE` on
the Snowpark session that is already there. The swap is one function, `_select_reasoner` in
`app.py`: try `get_active_session()`, and if that fails, you are local, fall back to the CLI.
Nothing else in the app knows or cares which one answered.

Proven, not just designed: the a3 spike (13 September 2026) deployed that exact file into a
Snowflake trial account with `snow streamlit deploy` and ran a full 35-field interview through it
end to end, business ask and technical spec both rendered. Two real bugs surfaced only by running
it live, neither guessable from reading the code first: Streamlit-in-Snowflake's bundled build
predates `st.rerun()`, and `AI_COMPLETE` wraps every reply in a JSON string literal that silently
broke `judge()`'s yes/no parsing until unwrapped. Both fixed, both covered by tests. Storage and
delivery still assume a local disk (`SqliteStorage`, `engine/delivery.py`); the same seam pattern
applies to those, it just has not been swapped yet, that is the rest of a3, not built. Full account
in `docs/architecture-decisions.md`'s "a3 spike" entry; `docs/a3-spike-deployment.md` has the
deploy steps.

## Design documents

- [`CLAUDE.md`](CLAUDE.md) states the working rules, the two-persona design, and the build
  discipline this project holds itself to.
- [`docs/coaxing-protocol.md`](docs/coaxing-protocol.md) is the question bank: nine interview
  layers, each plain-language question paired with the technical attribute its answer reveals.
- [`docs/provenance-model.md`](docs/provenance-model.md) defines how every field in the technical
  spec is tagged: stated, inferred, assumed or missing, and how each state is earned.
- [`docs/interview-branching.md`](docs/interview-branching.md) defines the interview's control
  flow: the field ledger, what gets asked, what gets skipped, and the three layers that don't
  follow the plain version of that recipe.
- [`docs/output-template.md`](docs/output-template.md) defines the fixed structure of the business
  ask and the technical spec, which ledger fields render into each, and how that structure maps
  onto the Word (`.docx`) template both are actually delivered as (e13).
- [`docs/readiness-scoring.md`](docs/readiness-scoring.md) defines the status, the completion
  score, the blocking-versus-workable split, and who owns closing each named gap.
- [`docs/interview-ux.md`](docs/interview-ux.md) defines which widget, free text, multi-choice,
  hybrid or banded, each interview question uses on screen.
- [`docs/architecture-decisions.md`](docs/architecture-decisions.md) records the portability-seam
  decisions: how the reasoner gets real model access, what holds interview state and retained
  knowledge, how a frontend runs the engine's blocking interview loop, and the a3 spike that
  verified the model-provider seam and the frontend's threading model against a live Snowflake
  trial account.
- [`docs/a3-spike-deployment.md`](docs/a3-spike-deployment.md) is the deployment write-up for that
  spike: steps to redeploy it, what to watch for, and what actually happened when it ran.
- [`docs/synthetic-dataset.md`](docs/synthetic-dataset.md) describes the ten-interview synthetic
  dataset built to give e8 (overlap detection, dependency map) real data to design against.

## How this was built

Built with Claude, disclosed rather than hidden, because the point of a portfolio piece is showing
how its author thinks, and that includes how they work with the tools available to them now.

The problem framing, the design calls, and the scope decisions are mine: what the tool should
refuse to do (invent a requirement, blend the two personas, treat readiness as a gate rather than a
score), what to build next and what to leave on the backlog, and every call recorded as "decided" in
`docs/architecture-decisions.md`. Claude drafted the code and the documentation against `CLAUDE.md`'s
rules, and its other job was to push back: several of the findings in `docs/architecture-decisions.md`
are Claude catching its own prior output failing the claim-integrity rule this project holds itself
to: a live `reframe()` call inventing product names nobody gave it, a regression that shipped
believed-fixed and wasn't, a stale "not yet confirmed" claim this README kept carrying after the
thing it doubted had already been checked twice, live, and found real issues. Some of that was
caught the same day it was built; the README claims were caught later, on a deliberate re-audit
against the actual test suite and architecture record rather than trusted as still current.

That distinction, whose call it was versus who typed it, is also why the technical spec `docs/
provenance-model.md` defines exists at all: the same discipline this tool applies to a requester's
answers is applied here, to what actually came from Jay and what came from the model.

## Scope

The core is warehouse-agnostic. Platform-specific output, for example Snowflake semantic views
generated from dbt models, is an adapter on top rather than an assumption baked in.

No organisation's real schemas, data, or internal documents appear anywhere in this repository.
Examples are invented or drawn from public datasets.
