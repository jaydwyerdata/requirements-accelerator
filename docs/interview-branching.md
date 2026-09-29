# Interview Branching and Skip Logic

Version 0.2, last revised 11 September 2026.

Defines the control flow that runs the interview: what gets asked, what gets skipped, and why.
This document assumes the Coaxing Protocol (the question bank) and the Provenance Model (the field
states) as given, and its only job is to decide, turn by turn, which question runs next. It does
not define the readiness score or gap ownership, and it does not define how the two output
documents get rendered: both are separate work and this hands off to them rather than absorbing
them.

## The field ledger

Everything below operates on one structure: a table with a row per field, holding its value, the
layer it belongs to, its provenance state (stated, inferred, assumed or missing, per the Provenance
Model), its source, and, for missing fields, who owns closing the gap. This is the same record
shape the Provenance Model's worked example already sketched, generalised from an illustration into
the actual object the engine reads and writes. The field list itself is fixed by the appendix below,
one entry per thing the Coaxing Protocol's "where each layer lands" section names.

Every decision in this document reduces to a query against that ledger: is this field's value
already known, and if not, is it safe to ask for it yet.

## Seed intake

Before layer 00 opens, the requester has the option to drop in notes or a reference document.
This is never a gate and never framed as preparation they are expected to have done: most people do
not know what they need until they are talking it through, so the interview has to work identically
well starting from nothing. If nothing is supplied, this phase is a no-op and the layer loop opens
on an empty ledger.

Whatever is supplied gets scanned once against the field list. A value it appears to answer is
written to the ledger as inferred, source seed intake, never stated. A value extracted from a
document is reasoning the tool did, not an answer the requester gave, which is exactly what
inferred already means; it just happens to be inferred from text instead of from a different
question. It only becomes stated once it survives the reflection step at the relevant layer
boundary, the same as any other inference. Any ambiguous business term the source text uses gets
queued for layer 07 exactly as a term overheard live would be. A definition sitting in a document is
a draft to confirm, not a fact to inherit: the nuance behind a term, what exactly counted, whether it
is still accurate, lives in the person, not the page.

Seed intake does not actually end once layer 00 opens; see "Live inference" below for the same scan
run continuously against everything the requester says from that point on, not just against
whatever they supplied up front.

## The layer loop

Layers run 00 through 09 in order. Inside each layer, every question follows the same recipe unless
noted as an exception below:

1. If the layer has a gate, run it. Only layer 00 has one.
2. For each question, check its precondition against the ledger, then check whether anything the
   requester has already said, live, resolves it before asking it fresh. See "Live inference".
   - No precondition, nothing already resolves it, and the target field is missing: ask it live.
     What comes back is not written to the ledger automatically; see "Classifying a reply" for what
     happens between hearing it and recording it.
   - Precondition met, and the field already holds an inferred value, whether from seed intake or
     live inference: do not ask it fresh, but queue it for the layer's reflection step rather than
     trusting it silently.
   - Precondition not met: skip the question, but see "not applicable" below before treating that as
     nothing happening.
3. At the end of the layer, reflect back everything the ledger holds for it, in the requester's own
   language. Explicit confirmation promotes every inferred row from this layer to stated, confirmed
   by reflection. Explicit correction is recorded as a layer-level note, tagged stated, their
   correction, rather than rewriting any one field: a free-text correction doesn't say which field
   it concerns, so the inferred fields a wrong reflection was correcting stay inferred rather than
   being promoted on the strength of a reflection just flagged as wrong. Field-level correction is
   a known gap against this rule, tracked in `engine/interview.py`'s own `reflect_and_promote`
   docstring. No reaction, moving past the reflection without engaging it, changes nothing: the
   field stays inferred, because silence is not confirmation.

Most layers run this recipe with no further complication: every question in them is independent of
the others in the same layer, so they all get asked unless the ledger already answers them. Three
layers do not.

## Live inference: seed intake never really ends

Seed intake's scan, does this text already answer one of the fields on the list, is not a one-time
step that stops mattering once layer 00 opens. It runs again before every question, this time
against everything the requester has said live so far in this interview, not only against whatever
they supplied before it started. If an earlier answer already resolves the question about to be
asked, it is written to the ledger as inferred, source pointing at the earlier answer and the layer
that produced it, and folded into the current layer's reflection instead of being asked again in
its literal form.

This was missing from the first live run: layer 04 asked "where do you look today when you need
this" after layer 00 had already been told, in more detail, "I log into the CRM, create five
reports looking at customers in different regions." Nothing was wrong about layer 04's question in
isolation, it is a fair question the first time it is genuinely unanswered, the gap was that the
tool never checked whether it already had the answer before asking it again. Live inference is that
check, run continuously rather than once.

This does not replace asking; it only removes questions the requester has already answered without
being asked twice. A question genuinely not yet covered by anything said so far is still asked in
full, live, per the plain recipe above.

## Classifying a reply: answer, clarifying question, or don't know

Not every reply to a live question is a value ready to store. Three shapes are possible: a genuine
answer, the requester asking back what the question means, or the requester saying, in whatever
words, that they do not know. Before this revision, only two places in the interview tried to catch
any of this at all, layer 00's redirect and layer 07's vagueness check, and both reused one fixed
follow-up string regardless of what the requester had actually said or why. Everywhere else, a
reply was written to the ledger exactly as typed. That is how "I don't understand what you mean",
typed in answer to layer 02's primary measure question, ended up stated as the answer and carried
all the way through to the reporting specification in the final document. It was not a vagueness
problem and not a missing-value problem: it was a real reply the tool never checked was an answer
at all.

Every question now runs this check before anything is written to the ledger:

1. The reply is classified as an answer, a clarifying question, or a don't-know (not sure, don't
   know, a blank, or anything in that family).
2. An answer is written to the ledger as stated, per the plain recipe.
3. A clarifying question or a don't-know is not written to the ledger. Instead the requester gets a
   different way into the same question, grounded in what the ledger already holds at that point,
   not a restatement of the field's technical purpose and never inventing detail the requester has
   not actually given. For the primary measure example, a second attempt should draw on what layer
   00 already established, checking CRM reports against invoices for revenue by region, rather than
   asking the same generic question again.
4. Capped at the same two attempts as before, but the reason for the cap has changed. It is not
   there to bound how many calls a judgement costs; a deliberate choice for this project, cost is
   not the constraint it would be if this ran against metered billing rather than an existing
   subscription. It is there because past a certain point a requester who has said don't know twice,
   to two genuinely different framings of the question, does not know, and the honest response is to
   record that as a named gap for the right owner to close, not keep circling a question they cannot
   answer. If both attempts are exhausted without a real answer, the field is recorded exactly as
   the plain recipe already does when a redirect exhausts: stated, whatever was actually said last,
   flagged in a note as unresolved after two attempts, so the gap carries forward honestly instead
   of a wrong value hardening into fact.

This generalises, and replaces, what used to be two separate bespoke loops. Layer 00's redirect and
layer 07's vagueness check are now this same mechanism applied to one question each, not two
different pieces of logic that happen to look similar. See the exceptions below for what, if
anything, still makes those two layers different once the reframe mechanism itself is shared.

Exactly how a reframe is produced, and how a reply is told apart from a real answer, is a Reasoner
interface question and belongs in `docs/architecture-decisions.md` alongside the rest of the model
provider seam, not here. This document only fixes what has to be true of the control flow: every
question checks before it stores, and a non-answer gets a genuinely different attempt, not a
repeated one.

## Exception: layer 00's gate

Layer 00's gate runs regardless of whether its fields came from seed intake or a live answer:
nothing skips validation just because it already has a value. What made this an exception before,
the redirect loop when an answer reads as a solution in disguise rather than a problem, is now just
this layer's field going through the shared mechanism in "Classifying a reply" above: a solution
in disguise is treated the same as a don't-know, a non-answer that earns a different attempt at the
question rather than being accepted as-is. What remains genuinely special to layer 00 is the gate
itself, that it always runs, never skipped by a ledger value already being present.

## Exception: "not applicable" is inferred, not missing

Layer 02's drill-through question and layer 04's system-of-record question both have real
preconditions, no dimensions named means nothing to drill into, only one source system named means
nothing to reconcile against. When a precondition like this fails, the field does not go to missing.
Missing means a gap someone has to close, and there is nothing to close here: the tool reached a
conclusion by reasoning from a different answer, which is precisely what inferred already means. The
field is written as inferred, value not applicable, source pointing at whichever earlier answer made
it inapplicable, and it goes through the same reflection step as any other inference rather than
being assumed silently. A skip decision is still a decision, and it still gets shown back to the
requester before it is trusted.

The rarely-asked questions across every layer follow a related but distinct rule: they are never
skipped for feeling awkward or unnecessary, because that is exactly the oversight the flag exists to
prevent. They can still resolve to not applicable when their precondition is genuinely absent, as
with layer 04's system-of-record question above. The difference is what is doing the skipping: a
structural precondition can skip a rarely-asked question, a sense that it is not worth asking cannot.

## Exception: layer 07 runs as a loop, not a pass

Layer 07 does not ask its four questions once. It runs them once per ambiguous business term the
interview has picked up anywhere so far, from seed intake or from any layer up to this point. If no
such term surfaced, which would be unusual, layer 07 runs zero times. Three further rules apply
inside each pass, on top of the shared recipe:

**The definition question is where "Classifying a reply" matters most.** A definition nobody could
check against a real row, "recently" or "engaged" with no boundary, is a don't-know wearing the
costume of an answer, and gets the same reframe treatment as any other non-answer, not a special
vagueness loop of its own. This used to be layer 07's own bespoke logic; it no longer is.

**The competing-definition question checks retained knowledge before it is asked.** If this exact
term has a recorded definition from a prior interview, the question becomes concrete: does this
match what a previous requester meant by it. No match, it stays generic, surfacing the possibility of
a future conflict even with nothing yet to compare against. Same question, two different bodies,
chosen by what the ledger of prior interviews already knows.

**The exclusions question always offers two or three example categories**, drawn from the protocol's
own text: tests, internal accounts, cancellations. Left fully open, people default to "no, nothing,"
because naming edge cases unprompted is hard, and this is the question the protocol itself flags as
the usual root cause of a disputed number later. The tradeoff is real: examples can anchor an answer
toward the categories offered instead of the requester's own. It is accepted here because the
alternative, a false "nothing excluded" that surfaces as a dispute after the build, is worse.

A term does not count as locked, available to the technical spec as an authoritative definition,
until it clears all three: a concrete testable definition, an explicit exclusions answer, and
layer-boundary reflection confirming it. Short of that it stays a named gap rather than something the
spec quietly treats as settled.

**The term queue itself needs a dedup pass before layer 07 opens.** Terms are currently collected by
calling `extract_terms` once per layer, independently, with dedup by exact string match only. The
first live run against a real interview surfaced what that misses: "trends" and "product trends"
queued as two separate terms, so did "opportunities" and "growth opportunities", both genuine
overlaps a person would recognise instantly and a string comparison cannot. The same run also
queued "last week", a comparison period already captured in full by `benchmark_comparison`, and
"dimensions", the interview's own field name rather than a business concept two departments could
define differently. Eleven terms queued from one interview, several of them redundant or not
actually ambiguous business terms at all, is what made layer 07 feel endless rather than thorough.

The fix is a single pass over the whole candidate queue, once, after collection and before layer 07
opens, rather than the current per-layer collection with no visibility into what has already been
queued. That pass needs to catch near-duplicates a string match cannot, and needs to recognise a
term that is already fully answered by a structured field elsewhere in the ledger. The exact
mechanism, and whether the total queue should also be capped outright, is an implementation decision
for `engine/interview.py` and `engine/reasoner.py`, not specified here: this document commits to the
outcome, one pass, deduplicated, before the loop starts, not to a particular algorithm for it.

## Abandonment

If the requester stops at any point, the loop stops with them. Whatever the ledger holds stands as
is: nothing gets backfilled, nothing gets assumed to finish the picture. The rows already marked
missing were always going to be gaps: an interview that ends early just means more of them, not a
different kind of output.

## Handoff

Once the loop ends, whether by finishing layer 09 or by the requester stopping early, this document's
job is done. What happens to the ledger next, scoring it for readiness, attributing its gaps, and
rendering the two output documents, belongs to the output template and readiness scoring work, not
here.

## Appendix: field list by layer

- **00**: problem_statement, current_process, frequency, blast_radius, activation_use_case,
  acceptance_criteria
- **01**: query_type, usage_pattern, audience_breadth
- **02**: primary_measure, dimensions, drill_through_required, benchmark_comparison
- **03**: grain, fan_out_risk, cardinality_risk
- **04**: source_systems, system_of_record, entry_latency, restatement_handling
- **05**: downstream_dependencies, steward (inferred only, never asked directly), decision_rights
  (inferred only, never asked directly), onward_flows, criticality_tier, access_approver
- **06**: freshness_sla, schedule_alignment, history_depth, scd_requirement
- **07**: metric_definition, competing_definition_check, exclusion_filters, synonyms, each keyed by
  term and repeated once per term queued
- **08**: row_level_security, data_classification, future_role_design
- **09**: volume, growth_rate
