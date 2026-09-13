# Requirements Accelerator

A curious business analyst at the front, a data engineer at the back.

A self-serve tool that interviews the person requesting a data solution, in plain language, and
turns a vague ask into concrete data and solution requirements.

## Status

Early build, but the interview engine now runs end to end and remembers what it's told. `python
cli.py` walks all nine interview layers (00 through 09) from a terminal, including layer 07's
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
immediately, see `docs/architecture-decisions.md`'s note on it. What is not yet confirmed is the
same gap e4 had before its own live run: whether `ClaudeCodeReasoner`'s real `judge`, `reframe`
and `consolidate_terms` calls behave sensibly against real interview content, not just that the
control flow around them is correct.

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

## Running it

```
python cli.py          # terminal
streamlit run app.py   # local browser UI (e7, UI not yet confirmed working, see above)
```

Both need the `claude` CLI installed and logged in. `python cli.py` has no dependencies beyond
the standard library; `streamlit run app.py` additionally needs `pip install -r requirements.txt`.

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
disk-writing behaviour (a2), the ten-interview synthetic dataset below, e8's overlap report, and
a1's semantic view adapter (both below), in real pass/fail assertions (stdlib `unittest`, no new
dependency, 85 tests as of this writing), reusing each demo script's scripted dialogue by import
rather than duplicating it. The demo scripts stay as readable, runnable walkthroughs; this is what
actually catches a regression rather than relying on someone reading printed output. See
`docs/architecture-decisions.md`'s Testing section for why this exists.

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
  ask and the technical spec, and which ledger fields render into each.
- [`docs/readiness-scoring.md`](docs/readiness-scoring.md) defines the status, the completion
  score, the blocking-versus-workable split, and who owns closing each named gap.
- [`docs/interview-ux.md`](docs/interview-ux.md) defines which widget, free text, multi-choice,
  hybrid or banded, each interview question uses on screen.
- [`docs/architecture-decisions.md`](docs/architecture-decisions.md) records the portability-seam
  decisions: how the reasoner gets real model access, what holds interview state and retained
  knowledge, how a frontend runs the engine's blocking interview loop, and the plan for a
  Streamlit in Snowflake port (documented, not built).
- [`docs/synthetic-dataset.md`](docs/synthetic-dataset.md) describes the ten-interview synthetic
  dataset built to give e8 (overlap detection, dependency map) real data to design against.

## Scope

The core is warehouse-agnostic. Platform-specific output, for example Snowflake semantic views
generated from dbt models, is an adapter on top rather than an assumption baked in.

No organisation's real schemas, data, or internal documents appear anywhere in this repository.
Examples are invented or drawn from public datasets.
