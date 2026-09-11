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
access (e4) is built too: every judgement call the interview makes (is this a solution in
disguise, does that name more than one system, is that definition too vague to test) goes to
`ClaudeCodeReasoner`, a real Claude Code CLI subprocess, not a person at the keyboard. It needs
the `claude` CLI installed and logged in on whatever machine runs `cli.py`; see
`docs/architecture-decisions.md` for the reasoning and, honestly, for what verifying it actually
still needs (its live output hasn't been checked from inside a sandboxed build session that
can't reach the CLI's own stored login).

There's no frontend yet: this is a terminal script, useful for proving the branching logic and the
two output documents are correct, not for demoing to anyone outside this project.

## Running it

```
python cli.py
```

Python 3.11 or later, no dependencies. See `examples/` for five scripted runs: a clean layer 00
pass, one that trips the layer 00 redirect and self-corrects within the two-attempt cap, a full
nine-layer pass that locks a definition in layer 07 and promotes an inferred field on
confirmation, one that exercises both "not applicable" branches (layer 02's drill-through, layer
04's system of record) plus a reflection that gets no reaction, and one that proves retained
knowledge actually persists: a term locked in one interview shows up as a concrete question in a
second one against a throwaway database. Useful for seeing the whole flow, and every branch of it,
without typing it out by hand.

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
Surfacing overlap between requests and building a dependency map that answers "who is affected if
this changes" are the same idea taken further, from the same stored data; both are still scope, not
built yet.

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
- [`docs/architecture-decisions.md`](docs/architecture-decisions.md) records the two portability-
  seam decisions: how the reasoner gets real model access, and what holds interview state and
  retained knowledge.

## Scope

The core is warehouse-agnostic. Platform-specific output, for example Snowflake semantic views
generated from dbt models, is an adapter on top rather than an assumption baked in.

No organisation's real schemas, data, or internal documents appear anywhere in this repository.
Examples are invented or drawn from public datasets.
