# Provenance Model

Version 0.1, last revised 10 September 2026.

Defines how every field in the technical spec is marked, so that nothing the tool outputs can be
mistaken for something it does not actually know. This document exists because of the claim
integrity rule in `CLAUDE.md`: the tool never invents a requirement, and a plausible guess
presented as fact is the worst possible output because it survives review by looking reasonable.
Provenance is how that rule gets enforced field by field rather than staying a good intention.

This document defines what tag applies to a piece of data and why. It does not define the
interview flow (`docs/coaxing-protocol.md`) or the readiness score and gap ownership rules
(`CLAUDE.md`), though it feeds both.

## The four states

Every field in the technical spec carries exactly one of these. No field is left untagged,
including fields that feel too obvious to need one. A requester's own name is stated the same way
a grain declaration is stated: the rule is mechanical, not judged case by case, because a system
that decides tagging is optional for "obvious" fields is a system that will eventually skip it for
a field that mattered.

**Stated.** The requester answered this, directly, in this interview. The purest state, and the
only one that needs no further scrutiny before it is treated as a requirement.

**Inferred.** Back of house derived this from an answer to a different question. Layer 05 of the
Coaxing Protocol is the clearest example: nobody is asked who owns the data, but stewardship is
inferred from who the requester says they go to when the numbers look wrong. Inferred fields are
requirements the tool has reasoned its way to, not requirements the requester handed over, and that
distinction has to survive into the spec.

**Assumed.** An engineering default, applied by back of house because the field sits outside what
the interview asks about at all. Freshness defaulting to nightly batch when nothing in the
conversation implied otherwise is assumed. Retention defaulting to the organisation's standard
window is assumed. An assumed field is never a business fact and never gets described as one: it is
a placeholder the data team is expected to confirm or override, flagged exactly so it does not
quietly harden into a decision nobody made. (Status, 7 October 2026: the state is defined and
rendered, but the current interview applies no defaults, so no field is ever set to assumed yet.)

**Missing.** Nothing established a value and no default applies. Recorded as a gap, which is where
this document hands off to the gap ownership rule defined in `docs/readiness-scoring.md`: a missing field
is attributed to whoever can close it, the requester or the data team, using the same attribution
the readiness score reports. Provenance does not compute that attribution twice; a missing tag
carries the same owner the readiness score already assigned.

## Precedence

**Stated overrides inferred. Inferred overrides assumed. Assumed overrides missing.** A field only
sits in a weaker state because nothing stronger was ever established for it. The moment a stronger
signal arrives, the field is retagged and the value replaced. This is the mechanism that keeps
assumed from ever becoming a silent substitute for asking: if the interview later touches the
territory an assumption covered, the assumption is gone, not merely annotated.

Nothing moves in the other direction. An inferred field is never downgraded to assumed, and a
stated field is never downgraded at all short of the requester explicitly changing their answer.

## Inference and the reflection rule

`CLAUDE.md` requires the front-of-house persona to reflect understanding back at each layer
boundary and let the requester correct it. That reflection is the only mechanism that can promote
an inferred field to stated, and it only does so on an explicit reaction.

If the requester actively confirms the reflected summary, every inferred field it covered is
retagged stated, confirmed by reflection, with a note recording which layer boundary the
confirmation happened at. If the requester corrects it, the correction is recorded as stated, in their words, as one note for
the whole layer, and the original inferences stay in the record unchanged rather than deleted, since
a wrong inference is itself useful evidence about how the back-of-house reasoning is performing.
Attaching a correction to the single field it changes is a known gap, not yet built.

Silence is not confirmation. If a requester simply proceeds past a reflection without reacting to
it, the field stays inferred. An interview that does not capture an explicit reaction has not
established agreement, and treating forward progress as agreement would be exactly the kind of
invented certainty this whole model exists to prevent.

## Recall and lineage

Recalled knowledge enters a new interview as a question, never as an answer, per the retained
knowledge principle in `CLAUDE.md`. What happens to the field once the requester responds depends
on which way they answer, but the state is stated either way. What differs is the lineage attached
to it.

**If the requester agrees** with a recalled prior definition, the field is tagged stated. A lineage
pointer back to the interview that first established it is designed but not yet built. This is not the same as treating
the two answers as one fact with two witnesses: the current interview's stated value is its own
record, the pointer just lets overlap detection find the earlier one.

**If the requester disagrees**, the field is still tagged stated for this interview, their own
definition, and the disagreement itself is retained as a signal, exactly as `CLAUDE.md` describes:
either outcome from a recall question is worth more than a silent assumption, because a conflict
nobody had noticed is more valuable output than a false sense of consistency. Neither definition is
edited to match the other. Both stand, each stated by the interview that produced it.

A lineage pointer is metadata about where a value came from, not a claim that two people meant the
same thing. `CLAUDE.md` is explicit that equivalence between two requesters' language is never
assumed, and provenance lineage does not change that: it records that a comparison happened and
what its outcome was, nothing stronger.

## What a tagged field looks like

The technical spec renders each field with its value, its state, and enough provenance to audit it
without re-running the interview. The records below are illustrative: in code a field record holds
its value, state, source, owner and a free-text note, which carries detail such as reflection
confirmation.

```
field:      grain
value:      one row per policy renewal event
state:      stated
source:     interview 2026-09-14-jkr, layer 03, Q1

field:      steward
value:      Priya (finance ops)
state:      inferred
source:     derived from "who do you go to when the numbers look wrong", layer 05
reflected:  confirmed at layer 05 boundary, interview 2026-09-14-jkr

field:      freshness_sla
value:      nightly batch
state:      assumed
source:     no freshness question triggered; organisation default applied
flag:       confirm with data team before build

field:      history_depth
value:      (none)
state:      missing
owner:      requester
reason:     interview abandoned before layer 06
```

The exact field list is fixed by the Coaxing Protocol's "where each layer lands" section; this is
the record shape every one of those fields is stored in, not a new set of fields to design.

## Where provenance is visible

Provenance is a technical-spec concept only. The business ask stays plain language, describing what
was understood and what happens next, with no stated, inferred, assumed or missing labels anywhere
in it. This follows directly from the two-persona rule in `CLAUDE.md`: front of house never
explains its reasoning to the requester, and a provenance tag is reasoning made visible. Showing a
requester that their answer was "inferred" or that a field is "assumed" would also invite exactly
the implementation debate `CLAUDE.md` says the business ask exists to avoid.

The technical spec's readers, a data engineer, a BI developer and a data lead, are the entire
audience for this machinery, and it is written at the terse, unexplained level appropriate to that
audience.

## Why this exists

A spec with no provenance model looks identical whether every field was carefully established or
half of it was quietly guessed. That is the specific failure this document closes: not accuracy in
general, but the difference between a wrong answer that is visibly wrong and a wrong answer wearing
the same formatting as everything the requester actually said.
