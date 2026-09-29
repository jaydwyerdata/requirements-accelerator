# Output Template and Renderer

Version 0.1, last revised 10 September 2026.

Defines the fixed structure both output documents follow, and what the renderer draws from the
field ledger to produce them. This document assumes the field ledger, the provenance states and
the interview's layer order as given (Provenance Model, Interview Branching and Skip Logic), and
its only job is to say what shape the two documents take and which ledger fields feed which part of
that shape. It does not decide what a request scores on readiness, that belongs to the readiness
scoring and gap attribution work, this document only reserves the place that score renders into.

Both documents are generated from the same ledger. Nothing here asks the requester anything new;
the interview is finished, or stopped, by the time either document exists.

## The business ask

Half a page, plain language, for the requester. Three beats, matching the shape CLAUDE.md already
sets out, and nothing else. No headers borrowed from the technical side, no field names, no
provenance labels, no mention of stated, inferred or missing anywhere in it: that machinery is
internal, and showing it here would invite exactly the implementation debate the two-persona split
exists to prevent.

**What we understood.** A paraphrase, not a field dump, built from `problem_statement` and
`current_process`. Written in the requester's own language, since the reflection steps during the
interview already established what that language is.

**What you're trying to solve.** Built from `activation_use_case` and `acceptance_criteria`,
phrased as the outcome the requester is after, not as a list of features.

**What happens next.** A plain-language read of readiness, not the readiness machinery itself.
Ready to size, it says so. Blocked on something only the requester can close, it says what, in
their own terms, as an ordinary sentence: "we'd still like to understand who else relies on this,"
never "gap: downstream_dependencies, owner: requester." The tags and the word gap stay internal;
the substance of an open question is allowed to surface as prose, because otherwise this beat has
nothing honest left to say. Gaps the data team can close on its own are not mentioned here at all,
since they are not the requester's to act on.

**No business ask renders at all if layer 00's gate never cleared.** With no established problem
statement there is nothing genuine to reflect back, and a placeholder acknowledging a stalled
attempt would be exactly the kind of hollow content claim integrity rules out. The technical side
can still note that an ungated attempt exists; the requester-facing document simply does not
generate.

## The technical spec

Internal only, terse, ordered by the interview's own layer sequence since that is already a fixed
and defensible order. Structure:

**Readiness, first.** Score and named gaps with their owners. This is what the spec exists to
answer for its readers, a data engineer, a BI developer and a data lead deciding what to size, so it
leads rather than sitting at the end as a summary of what was already read.

**Layers 00 through 09, in order.** Each field renders exactly as the Provenance Model's worked
example already specifies: value, state, source, and owner where the state is missing. Nothing new
invented here, this document just says these go in this order, under headings that match the
Coaxing Protocol's own layer names.

**Definitions, as its own subsection**, not folded into layer 07's place in the sequence, since
layer 07 is structurally a loop rather than a single set of fields. One block per term the interview
touched, each showing its definition, its exclusions, its synonyms, and whether it cleared all three
conditions to count as locked. A term that never locked renders with whatever it has and is marked
not locked, rather than omitted, so the gap is visible rather than silently dropped.

**Reporting specification, appended whenever a primary measure exists.** Almost every request that
clears layer 02 has something to report on, so this is included by default rather than gated on
being a recurring or multi-viewer request; a one-off pull just produces a thin version. Drawn
directly from ledger fields already collected, nothing new asked to populate it:

- Measures and dimensions, from `primary_measure` and `dimensions`
- Drill path, from `drill_through_required` and `grain`, what a drill-down actually lands on
- Comparison basis, from `benchmark_comparison`
- Filters, from `exclusion_filters`
- Refresh cadence, from `freshness_sla` and `schedule_alignment`
- Row-level security, from `row_level_security`

This appendix maps ledger fields into a mini-spec; it does not decide chart types or page layout.
Which visual a given measure and dimension combination should become is a judgement call for
whoever builds it, or a future extension of this document, not something invented here.

## What the renderer does not do

It does not compute the readiness score, only places it. It does not decide whether a field counts
as locked, that is the interview branching document's rule, applied before the field ever reaches
the renderer. It does not soften or interpret a gap's wording, a missing field renders as missing
regardless of how close the interview got. Rendering is the last, most mechanical step: by the time
it runs, every real decision has already been made.

## The Word template (e13)

Decided 14 September 2026 (see `docs/architecture-decisions.md`'s e13 entry for the full account).
Both documents are delivered as `.docx` files, not plain text: engine/render.py's plain-text
functions still exist and still feed the terminal printout (cli.py) and the on-screen recap
(app.py), but what gets written to disk goes through a second renderer, `engine/docx_render.py`,
that turns the same ledger into a letterheaded Word document. This section says how that structure
maps onto the two documents above, not a new content decision, the content is unchanged.

**Letterhead, on both documents.** A title ("Requirements Accelerator"), the document type
("Business Ask" or "Technical Spec (internal only)"), the interview id's first eight characters,
and the date. Enough to identify which document this is and which interview it came from once it's
sitting in someone's downloads folder, detached from any conversation that produced it.

**The business ask** keeps its three beats as headings ("What we understood", "What you're trying
to solve", "What happens next") with the same gate: no problem statement, no document beyond the
letterhead and a one-line explanation why.

**The technical spec** renders every field table (one per layer) with an added fourth visual
element beyond what the plain-text version shows: a coloured badge in the State column, matching
the colour already used for status on the project's build tracker (green stated, blue inferred,
amber assumed, red missing). The readiness block leads with the same badge treatment on its overall
status (green "READY TO SIZE", red "NOT READY TO SIZE"). This is deliberate: the provenance model's
whole point is what came from the requester versus what was inferred or assumed, and a colour you
see before you read anything makes that distinction the first thing a reader notices rather than
something they have to parse from a bracketed label.

Nothing here is asked or computed differently than the plain-text renderer already does; this is
presentation only, layered on top per this document's own "What the renderer does not do" section
above.
