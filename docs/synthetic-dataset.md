# Synthetic Interview Dataset

Version 0.1, 12 September 2026.

Ten scripted, comprehensive interviews against a made-up retailer, run through the real engine
(`run_interview`, `StubReasoner`, `SqliteStorage`, `SqliteRetainedKnowledge`), not against mocked
output. Exists because e8 (overlap detection and a dependency map) has been blocked since e3 on a
concrete gap: there was no real interview data on file, so no useful query design was obvious.
Ten interviews, deliberately engineered to disagree with each other in places, is enough data to
make that design obvious, without waiting on ten real requesters.

No organisation's real schemas, data, stakeholder names or internal documents appear anywhere in
this dataset, per CLAUDE.md. Everything below, the retailer, its systems, its people and their
words, is invented for this purpose.

## The retailer

**Alderglen Outfitters**: a fictional mid-size outdoor and camping retailer, roughly 120 stores
plus an e-commerce channel, a handful of regional distribution centres, and a loyalty programme
called Basecamp Rewards. Large enough to have the usual data team problems (several systems of
record, several teams with their own vocabulary for the same idea, no single glossary anyone
trusts), small enough that one small data team is expected to serve all of it, which is exactly
the audience this tool is built for.

## The ten interviews

Run in this order, against one shared SQLite fixture database, because several of them are
engineered to reuse or contest a term a prior interview already locked; the order is what makes
that possible.

1. **Store Operations Manager**, on stockouts of best-selling SKUs. Clean pass, no redirect.
   Locks the term **"stockout"**.
2. **Digital Marketing Manager**, on re-targeting lapsed customers for a campaign. Clean pass.
   Locks the term **"active customer"** as a recency-based, any-channel definition. Exercises
   layer 04's "not applicable" branch (only one source system named).
3. **FP&A Analyst**, on reconciling a board-reported customer count. Opens with a proposed
   solution ("a Power BI dashboard that recalculates this automatically") and is redirected by
   layer 00's gate before giving the real problem. Reuses the term **"active customer"** with a
   genuinely different, subscription-based definition, so the retained-knowledge check comes back
   "doesn't match": a real governance conflict, not a data quality bug.
4. **Customer Experience Lead**, on inconsistent return reason codes. Clean pass. Locks the term
   **"on-time delivery"** as a promised-date definition.
5. **Supply Chain Analyst**, on vendor lead times. Reuses two prior terms in one interview:
   **"stockout"** (agrees with Store Ops' definition, "matches") and **"on-time delivery"**
   (disagrees with Customer Experience's definition, using a ship-date definition instead,
   "doesn't match"). Exercises layer 04's live system-of-record question (two systems named).
6. **People Analytics Partner**, on labour hours against peak-season sales. Clean pass. Locks a
   standalone term, **"active employee"**. Exercises layer 08's sensitive-data branch directly
   (personal and pay data named explicitly).
7. **Loyalty Programme Manager** (Basecamp Rewards), on declining member engagement. Clean pass.
   Locks a standalone term, **"engaged member"**, deliberately a different word for a concept that
   overlaps with interview 2's "active customer" without sharing any text with it. See "What this
   surfaces for e8" below: this is the interesting case, not the exact-string repeats.
8. **District Manager**, comparing six stores. Opens with a proposed solution ("a scorecard
   comparing my six stores every Monday") and is redirected by layer 00's gate, the second
   scripted redirect in this set. Adds no new term to the queue at all, a realistic outcome layer
   07 needs to handle (an interview that locks nothing new).
9. **Data Governance Lead**, on who can see customer PII across existing reports. Clean pass.
   Locks a standalone term, **"restricted field"**. Exercises layer 04's "not applicable" branch a
   second time (a single system named again) and layer 08's access questions in full.
10. **Chief Operating Officer**, wanting one number for "how the business is doing". Clean layer
    00 pass, but layer 02's dimensions answer is "none", so drill-through resolves to "not
    applicable" without being asked, the other not-applicable branch in this set. The term
    **"efficient store"** starts too vague to test ("one that's just running well"), gets reframed
    once, becomes concrete, but the final reflection gets no reaction, so it ends up recorded but
    explicitly **not locked**, a realistic "requester ran out of time or patience" outcome.

## What this surfaces for e8

**Three genuine term conflicts or agreements, all from retained knowledge working as designed,
none of them a bug**: "stockout" agrees across Store Ops and Supply Chain; "active customer"
conflicts between Marketing and Finance; "on-time delivery" conflicts between Customer Experience
and Supply Chain, in the opposite direction from how "active customer" conflicted (Supply Chain is
the one disagreeing this time, not the one being disagreed with). A real overlap report needs to
show both directions, not just "term X has two definitions" without saying who said which one
first and who came second and disagreed.

**A conceptual overlap current retained knowledge cannot see at all**: "active customer"
(Marketing, interview 2) and "engaged member" (Loyalty, interview 7) are, in plain language, the
same underlying idea (a customer the business considers currently worth marketing to), described
by two different teams using two different words. `SqliteRetainedKnowledge.definition_for()`
matches on exact term text, so this pair produces no signal at all today, not a "doesn't match"
result, silence. This is the single most useful finding this dataset produces for e8's actual
design: overlap detection cannot be exact-string matching alone, or it will miss the overlaps that
matter most, the ones where two teams do not even realise they are discussing the same thing.
Whatever e8 becomes (a second reasoner pass over all locked definitions looking for conceptual
overlap, most likely) needs to be designed against this case specifically, not just against
literal term repeats.

**A dependency map is already implicit, not yet built**: across the ten interviews, the audience
and downstream-dependency answers alone name Store Ops, Marketing, Finance, Customer Experience,
Supply Chain, HR, Loyalty, regional store leadership, Data Governance and the executive team as
users or stakeholders of overlapping data. Nothing new needs to be collected to build the
dependency map layer 05's design already promised, this dataset is proof the ten interviews
already contain the edges; e8's job is querying what is already on the ledger, not gathering more.

**Not every interview needs to produce something**: interview 8 adds no new term at all, and
interview 10 locks nothing. Both are realistic and both need to render sensibly (a technical spec
with an empty semantic layer section, a readiness score reflecting an unresolved gap), which this
dataset exercises deliberately rather than by accident. Interview 8 also exercises
`run_interview`'s `if pending_terms` guard on the empty-queue side, the same guard whose missing
check caused a real regression once, see this document's neighbour in
`docs/architecture-decisions.md`: a fresh, direct reason to keep an empty-queue interview in any
future test data as well, not just a coincidence of this one.

**A sharp edge `SqliteRetainedKnowledge.definition_for()` already has, surfaced by this dataset,
not created by it**: it returns the most recently locked definition for a term, by interview
creation time, not the first one, and not some notion of which team is authoritative. Interview 3
locks its own, conflicting "active customer" definition after interview 2's, which means any
interview run after interview 3 that touched "active customer" again would see interview 3's
version as the prior definition, not interview 2's, purely because it was saved more recently, not
because it settled anything. Nothing in this dataset actually triggers that (no interview after 3
rechecks "active customer"), so it doesn't affect any assertion here, but it's a real design
question e8 (or a smaller fix to `definition_for()` itself) needs to answer honestly: recency and
authority are not the same thing, and today's implementation quietly conflates them.

## How this was built and verified

`examples/synthetic/` holds one script per interview (`interview_01_store_ops.py` through
`interview_10_executive.py`), each a scripted `RESPONSES` list against `StubReasoner`, exactly the
same pattern the five `examples/demo_*.py` scripts already use, chosen deliberately over any
data-driven or templated generator: this project's own regression (the unguarded `consolidate_terms`
call, see this document's neighbour in `docs/architecture-decisions.md`) was caused by an
assumption about control flow that looked right and wasn't, and the fix that actually caught it was
a real automated test, not a cleverer script. Ten explicit, readable scripts are more work to write
than one generator, and considerably less likely to hide the same kind of mistake.

`examples/synthetic/run_all.py` runs all ten in order against one fixture SQLite database
(`examples/synthetic/alderglen.db`, gitignored: it is generated output, not source, exactly like
`requirements_accelerator.db`), printing the readiness-relevant outcome of each (which term locked,
which competing-definition answer was given and against what prior definition) as it goes.

`tests/test_synthetic_dataset.py` is the actual proof, not the printed narration: it runs the full
set against a temporary database and asserts, in real pass/fail terms, every claim made above:
"stockout" locks in interview 1 and reports "matches" in interview 5; "active customer" locks in
interview 2 and interview 3's competing check comes back "doesn't match" against it; "on-time
delivery" locks in interview 4 and interview 5's competing check comes back "doesn't match" against
it in the other direction; interview 8 queues no term; interview 10's "efficient store" is recorded
but its `term_locked::efficient store` field is `False`. Run it the same way as the rest of the
suite:

```
python -m unittest discover -s tests
```

## Checked against a real reasoner, not just StubReasoner

Everything above ran against `StubReasoner`, which means every judgement call, including whether
an answer needed a redirect, is a script decision, not a model one. `examples/synthetic/
verify_against_claude_code_reasoner.py` runs interview 1 (the cleanest-designed one, no scripted
redirect) against the real `ClaudeCodeReasoner` instead, with the same requester answers, to check
the assumption actually holds against live model judgement. See
`docs/architecture-decisions.md`'s "Real ClaudeCodeReasoner run against synthetic interview 1"
entry for the first result: most of it matched, but the real model triggered an unscripted reframe
that invented a detail the requester never gave (a genuine finding against `reframe()`'s own
claim-integrity instruction), and `extract_terms()`/`consolidate_terms()` queued and kept three
terms instead of converging on "stockout", which may or may not be the wrong call. Needs the
`claude` CLI installed and logged in, and costs real usage: expect roughly 30 separate `claude -p`
calls for one interview.

That invention finding was fixed, not left parked: `docs/architecture-decisions.md`'s "Reframe
invention fix, and a second live run" entry covers the tightened `reframe()` prompt, the new
`tests/test_reframe_prompt.py` regression guard, and a second live run of this same script, whose
one triggered reframe stayed fully grounded in already-stated context with no invented specifics.
Treated as resolved-and-watched, on the honest basis that one clean rerun is a positive data point
against a nondeterministic model, not proof the failure mode can never recur.
