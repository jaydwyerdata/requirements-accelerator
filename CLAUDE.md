# Requirements Accelerator

A self-serve tool that interviews the person requesting a data solution, in plain language, and
turns a vague ask into concrete data and solution requirements: a semantic layer definition, a
grain declaration, source and stewardship mapping, and testable acceptance criteria.

It exists because most requirements tooling stops at the business layer. It writes a tidy user
story and leaves every expensive technical decision unasked. This tool does the translation a data
engineer would do, and it does it by asking questions a non-technical person can actually answer.

It is project work intake, tied to a program increment cycle, not a BAU ticket queue. Its output is
therefore a prioritisation input as much as a build input: what is ready to work on, what is
missing before it can be sized, and which requests overlap with each other.

Built for individual contributors who act as their own business analyst, project manager and scrum
master because nobody else is doing it.

## Companion documents

- **Coaxing Protocol** (v0.2) is the question bank: nine interview layers, each plain-language
  question paired with the technical attribute its answer reveals.
- **Provenance model** (v0.1) defines how every collected field is marked: stated, inferred,
  assumed or missing.
- **Interview branching and skip logic** (v0.1) defines the control flow: what gets asked, what
  gets skipped, and why.
- **Output template and renderer** (v0.1) defines the fixed structure both output documents
  follow, and which ledger fields feed which part of that structure.
- **Readiness scoring and gap attribution** (v0.1) defines the status, the completion score, and
  who owns closing each named gap.
- **Interview interaction design** (v0.1) defines which widget, free text, multi-choice, hybrid or
  banded, each question uses on screen.

All six are reference documents. This file governs how work happens; those define what gets built.

## Working rules

**No em dashes.** Anywhere. Not in prose, documentation, code comments, commit messages, or
generated output. Use commas, colons, semicolons or full stops.

**Document as you go, not afterwards.** Every design decision gets written down when it is made.
Retrofitted documentation does not happen, and this repo is intended to be readable by people
assessing how its author thinks, so the reasoning matters as much as the code.

**Plain language in anything the requester sees.** The tool's whole premise is that technical
vocabulary excludes the people whose answers it needs. A prompt, label or error message that
assumes the reader knows what "grain" or "cardinality" means is a bug, not a style preference.

**Australian spelling** in prose: organisation, optimisation, prioritise.

## Claim integrity

Non-negotiable, and it applies both to what this repo says about itself and to what the tool
generates. It exists because AI assistance produces claims that are plausible, specific and
invented, and the failure is silent.

**Nothing enters this repo or its documentation unless it can be defended under direct
questioning.** When in doubt, cut it.

**The tool never invents a requirement.** If the interview did not establish something, the spec
records it as a gap. A plausible guess presented as a requirement is the worst possible output,
because it survives review by looking reasonable.

**Unverified numbers stay flagged rather than hardening into fact.** A figure that has not been
checked against a source is marked as unverified in the document that carries it, every time it
appears, until it is checked.

**Tense discipline.** Work that has been proposed is described as proposed. Work that has been
approved is described as approved. Work that has been delivered is described as delivered. These
are three different claims and they are not interchangeable.

## Two personas

The tool has a front of house and a back of house, and they never blend.

**Front of house is a curious business analyst.** Everything the requester sees is in this voice:
warm, plainly spoken, interested in their problem rather than in the data model. It asks about the
work, not the warehouse. It never uses technical vocabulary, and it never explains why it is asking
a question, because the reasoning belongs to the other persona.

**Back of house is a data engineer, a solution architect and a BI developer.** It listens to every
answer for what it implies technically: the grain, the cardinality risk, the missing system of
record, the change-tracking requirement nobody mentioned, and the shape of the report or model that
would actually answer the question asked. It decides what to ask next and what to write down. The
requester never hears from it directly.

The BI half matters as much as the engineering half. Most requests arrive as "I need to see
something", so a reporting specification, and where it is warranted a prototype, is often the
clearest possible expression of what was understood.

Three rules keep the separation clean:

**Curiosity is bounded by usefulness.** A good analyst's follow-up question is how exceptions and
edge cases surface, so curiosity is the right instinct, but it is spent only where an answer
populates a field. Interview length is the single biggest risk to a requester finishing, so the
tool is warm and efficient rather than chatty. Interested, not talkative.

**Reflect understanding back at each layer boundary.** Paraphrase what has been understood so far
in the requester's own vocabulary and let them correct it. Corrections are cheap at this point and
expensive after a build has started. This is also the moment a requester realises their own request
was ambiguous.

**Technical vocabulary appears only in the internal spec.** That document is written for builders,
so it says grain, cardinality and system of record plainly.

## What it produces

Every completed interview produces two documents, one from each persona.

**The business ask, written by the analyst, for the requester.** Half a page of plain language:
this is the problem we understood you are facing, this is what you are trying to solve, this is
what happens next. It describes understanding, never commitment, so it says what was understood
rather than what will be built. Its purpose is to catch misunderstandings while they are still
cheap, to confirm the requester was heard, and to give them something to show their own colleagues.

**The technical spec, written by the engineer, for the data team.** Internal only. The requester
never sees it, because it invites implementation debate with someone who has no basis to have it.
Its readers are a data engineer, a BI developer and a data lead who owns modelling and tagging, all
working in the same warehouse and as technical as the author, so it is terse and precise rather
than explanatory. Where the request is a reporting one, it carries a reporting specification
covering pages, visuals, filters and measures, detailed enough to build from.

**Requirements are stated in business language even inside the technical spec.** What is required
is described in the words the business uses, because that is what makes it verifiable against the
requester's intent. How it will be built is where technical vocabulary belongs. Keeping the two
separate means a requirement can be checked by the person who asked for it, without them ever
seeing the document.

**Readiness is a score, not a gate.** The spec grades how ready the request is to be sized, and
names the specific gaps rather than returning a verdict. A request where the requester cannot say
what data they need is not ready. A request missing an expected data volume is workable.

**Gaps are attributed by who can close them.** Some gaps only the requester can resolve: what the
problem actually is, what a business term means, who arbitrates a definition. Others the data team
can close from its own knowledge: where the data lives, how tables relate, rough volumes. These are
listed separately, because they are different work items with different owners. A gap closed by the
team is recorded as stated by the team, not attributed to the requester.

## Retained knowledge

Individual requests are self-contained. What the tool learns across them is not.

**Recalled knowledge enters a new interview as a question, never as an answer.** If a previous
requester defined "active member" a particular way, the tool does not prefill it. It asks whether
that is what this requester means. Agreement confirms an alignment; disagreement surfaces a real
governance conflict nobody had noticed. Either outcome is worth more than a silent assumption, and
prefilling would quietly homogenise the organisation's language and produce specs that look
consistent and are wrong.

**Never assume two people mean the same thing by the same word.** Terms are captured with who said
them and in what context, as observations, not as an agreed glossary.

**Overlap detection is a first-class output.** Requests that want similar data, or the same data at
a different grain, should be surfaced against each other. This matters most at planning time, when
a cohort of requests is being compared rather than a single one assessed.

**The accumulated dependency map is an impact assessment.** Knowing which teams rely on which data,
gathered as a byproduct of ordinary intake, answers "who is affected if this changes" without
anyone having run a governance exercise to find out.

**Deferred requests are kept.** A request raised and not prioritised in three consecutive cycles is
evidence in itself, either of a genuine unmet need or of a persistent misunderstanding about what
is possible. Retaining them costs nothing.

## Build discipline

**Self-serve from the first version.** The requester completes the interview alone. A version that
requires the data lead to sit with each stakeholder saves nobody any time and defeats the purpose.
Scope cuts come off the depth of the output, never off the audience: fewer output formats, a
shallower semantic layer, no platform-specific export. Not fewer users.

**Partial interviews still produce output.** Someone will abandon at question fourteen. The tool
emits the spec it can from what it has, with the gaps flagged, rather than refusing.

**Local first, port later.** Development and refinement happen on a locally hosted Streamlit app.
That keeps the whole thing self-contained while the design is still moving, and avoids standing up
hosting and credentials for something that is still changing shape.

**Portability seams exist from the first commit.** The tool must eventually run in Streamlit in
Snowflake as well as locally. Four things differ between those environments and none of them may
leak into the interview logic: storage, model provider, secrets, and user identity. Each sits
behind an interface with an implementation per environment. Dependencies stay short and boring,
since the Snowflake runtime is fussier about imports than a laptop is.

**Tool-agnostic core.** The tool must be useful to someone working on any warehouse. The generic
core produces a platform-neutral semantic model: entities, measures, dimensions, synonyms and
filters. Platform-specific output is an adapter on top, never baked in. The first adapter targets
Snowflake semantic views built from dbt models, because that is what makes the output directly
consumable by Cortex Analyst and Snowflake Intelligence.

**Delivery is the thinnest layer.** Writing finished documents to a synced folder is the default,
because it reaches SharePoint or OneDrive without any integration, credentials or tenant
configuration. Anything richer is an adapter added later, and delivery must never block the build.

**One tool finished beats three started.** Scope additions go to a backlog, not into the build. The
failure mode for this project is not picking the wrong idea, it is the design work being more
enjoyable than the build work.

**No employer data.** No real schemas, table names, stakeholder names, internal documents or
extracts from the author's workplace, at any point, including in test fixtures and examples.
Examples are invented or drawn from public datasets.

## Repository conventions

- `README.md` states what the tool does, its status, and how to run it. Status is stated honestly,
  including when the answer is "design only, not yet runnable".
- `docs/` holds the reference documents, one concept per file, each with a version number and a
  date at the top.
- Reference documents are versioned and revised in place rather than duplicated. When a design
  decision changes, the document changes and the reasoning for the change is noted.
- Commit messages say why, not what. The diff already says what.
