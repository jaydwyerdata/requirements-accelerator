# Requirements Accelerator

A curious business analyst at the front, a data engineer at the back.

A self-serve tool that interviews the person requesting a data solution, in plain language, and
turns a vague ask into concrete data and solution requirements.

## Status

Design stage. Not yet runnable. The interview design and working principles are documented; no
code has been written.

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

It also accumulates knowledge across interviews. Not to prefill later answers, which would quietly
homogenise the language of an organisation, but to ask better questions, surface overlap between
requests, and build a dependency map that answers "who is affected if this changes" as a byproduct
of ordinary intake.

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

## Scope

The core is warehouse-agnostic. Platform-specific output, for example Snowflake semantic views
generated from dbt models, is an adapter on top rather than an assumption baked in.

No organisation's real schemas, data, or internal documents appear anywhere in this repository.
Examples are invented or drawn from public datasets.
