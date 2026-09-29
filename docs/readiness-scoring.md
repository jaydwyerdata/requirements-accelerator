# Readiness Scoring and Gap Attribution

Version 0.1, last revised 10 September 2026.

Defines how the ledger becomes the readiness block that leads every technical spec: a status, a
completion score, and a named, owned list of what's still missing. This document assumes the field
ledger and its states as given (Provenance Model), the fixed field list as given (Interview
Branching and Skip Logic), and that this block renders first in the spec (Output Template and
Renderer). Its only job is to say how the numbers and the ownership get decided.

## Status and score are two different things

"Readiness is a score, not a gate," per the working rules, but a single completion percentage would
lie. A request ninety percent complete with grain still missing isn't ninety percent ready, it isn't
ready at all: the whole model hangs off that one field. So this renders as two separate things, not
one blended number.

**Status** is ready to size or not ready, decided entirely by whether any blocking field is still
missing. Binary, and it never gets softened by how complete everything else is.

**Completion score** is the percentage of this request's applicable fields that are non-missing,
stated, inferred or assumed all count, only missing does not. This gives a real sense of depth, and
it can sit at eighty-seven percent and still carry a not-ready status if the missing thirteen
percent includes something load-bearing. The two numbers are read together, never one standing in
for the other: "87% complete, not ready to size, missing grain" is the honest sentence this is
supposed to produce.

Not a hard gate even at not ready: nothing here stops a team from choosing to start exploratory work
on a not-ready request. What it stops is not knowing, which is the actual failure this was built
against, a blocking issue surfacing only after the work is already prioritised, because the gap
existed but nothing said so loudly enough to be seen before the commitment was made. That's why this
block renders first in the spec rather than as a footnote: a status nobody reads because it's at the
bottom is the same as not having one.

## Severity: blocking or workable

Every field carries one of two severities, decided once here rather than re-judged per request.

**Blocking.** Missing any of these means not ready, regardless of the completion score:

- `query_type`, layer 01, can't size without knowing what kind of answer is wanted
- `primary_measure`, layer 02, don't know the number
- `grain`, layer 03, the whole model hangs off this
- `source_systems`, layer 04, can't scope without knowing where it comes from
- any layer 07 term that hasn't cleared all three lock conditions (a concrete definition, an
  explicit exclusions answer, reflection confirmation), since an unresolved definition is how a
  number ends up disputed after the build, not a detail to defer

**Workable.** Everything else: `problem_statement`, `current_process`, `frequency`,
`blast_radius`, `activation_use_case`, `acceptance_criteria`, `usage_pattern`,
`audience_breadth`, `dimensions`, `drill_through_required`, `benchmark_comparison`,
`fan_out_risk`, `cardinality_risk`, `system_of_record`, `entry_latency`,
`restatement_handling`, the whole of layer 05, `freshness_sla`, `schedule_alignment`,
`history_depth`, `scd_requirement`, `row_level_security`, `data_classification`,
`future_role_design`, `volume`, `growth_rate`. Real gaps, all named, none of them stop sizing from
starting.

A field resolved as not applicable, per the branching document's rule, is inferred, not missing, and
never appears in the gap list at all: it isn't a gap, it's a conclusion the interview already
reached.

## Ownership

**The rule.** A gap belongs to the team when a data engineer could reasonably determine the answer
by examining the source systems or existing governance metadata, without needing the requester's
intent or judgement. Everything else, anything about what the requester wants, means, or knows
about their own process, belongs to the requester. Most of the interview is intent and definition,
so most gaps default to the requester.

**Team-owned**, the short explicit list: `source_systems` (where it lives), `fan_out_risk` and
`cardinality_risk` (how the tables relate), `volume` and `growth_rate` (rough sizing). These are the
cases a data engineer can close by looking, not by asking.

**Everything else defaults to the requester**, including most of the blocking list: `grain` and
`primary_measure` need the requester's own framing, no amount of source investigation substitutes
for it. `source_systems` is the one blocking field the team can close on its own if the requester
genuinely can't answer it, which is exactly why it's in both the blocking list and the team-owned
list at once, load-bearing and closable without going back to the stakeholder.

## Rendering a named gap

Each missing field renders as its plain-language consequence, not its field name, drawing on the
Coaxing Protocol's own reveals text rather than inventing new copy for the same idea twice:

```
gap:      grain
severity: blocking
owner:    requester
reason:   what one row represents hasn't been established
```

```
gap:      volume
severity: workable
owner:    team
reason:   rough sizing not yet confirmed, checkable from the source directly
```

The status line for the request these belong to reads not ready to size, eighty-seven percent
complete, one blocking gap.
