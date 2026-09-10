# Interview Branching and Skip Logic

Version 0.1, last revised 10 September 2026.

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

## The layer loop

Layers run 00 through 09 in order. Inside each layer, every question follows the same recipe unless
noted as an exception below:

1. If the layer has a gate, run it. Only layer 00 has one.
2. For each question, check its precondition against the ledger.
   - No precondition, and the target field is missing: ask it live, write the answer as stated,
     source interview plus layer and question reference.
   - Precondition met, and the field already holds an inferred value: do not ask it fresh, but queue
     it for the layer's reflection step rather than trusting it silently.
   - Precondition not met: skip the question, but see "not applicable" below before treating that as
     nothing happening.
3. At the end of the layer, reflect back everything the ledger holds for it, in the requester's own
   language. Explicit confirmation promotes every inferred row from this layer to stated, confirmed
   by reflection. Explicit correction overwrites the value, tagged stated, their correction, and
   keeps the original inferred value in the record rather than deleting it. No reaction, moving past
   the reflection without engaging it, changes nothing: the field stays inferred, because silence is
   not confirmation.

Most layers run this recipe with no further complication: every question in them is independent of
the others in the same layer, so they all get asked unless the ledger already answers them. Three
layers do not.

## Exception: layer 00's gate and redirect

Layer 00's gate runs regardless of whether its fields came from seed intake or a live answer:
nothing skips validation just because it already has a value. The first question, what is happening
today that should not be, additionally loops back with a clarifying follow-up whenever the answer
reads as a solution in disguise rather than a problem, "I need a dashboard that..." rather than a
description of what is wrong. This is a redirect, not a skip: the question is asked again in a
different shape rather than abandoned. Capped at two redirects. If the second attempt still does not
land a genuine problem statement, the tool accepts what it has and moves on, and the spec carries the
tension forward flagged as unresolved rather than either looping indefinitely or quietly treating a
feature request as a problem statement.

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

**The definition question loops on vagueness.** If the answer to what makes something count is not
testable against an actual row of data, "recently" or "engaged" with no boundary, back-of-house
redirects for the concrete version before accepting it, the same shape as layer 00's redirect. A
definition nobody could check against a real row is a gap wearing the costume of an answer.

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
