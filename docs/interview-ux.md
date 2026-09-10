# Interview Interaction Design

Version 0.1, last revised 10 September 2026.

Defines how each Coaxing Protocol question gets answered on screen: free text, buttons, or
something between the two. This document assumes the Coaxing Protocol's questions and field names
as given, and its only job is to say what widget each one becomes. It exists because interview
length is the single biggest risk to a requester finishing, per the working rules, and every
question answered by a click instead of a paragraph is time saved without losing anything the
question needed.

## The vocabulary

Four interaction types cover every question in the protocol.

**Free text (FT).** A text area, no preset options. Used only where the answer is genuinely
unbounded, a story, a definition, a name nobody could predict in advance.

**Multi-choice (MC).** A small fixed set of buttons, no free text escape hatch, because the
question's own answer space is genuinely closed. `query_type` is the clearest case, the protocol
already phrases it as four named options.

**Hybrid (HYB).** Three or four preset chips covering the common cases, plus an always-visible
"something else" that opens a text box. This is the pattern that actually reconciles wanting a
multi-choice interview with questions that are genuinely open-ended: most answers cluster around a
handful of common responses, dimensions are usually time, location, product or team, exclusions are
usually tests, internal accounts or cancellations, so the common case is one click and the long tail
still gets a real answer instead of being forced into a box that doesn't fit. Three to four chips,
kept tight so the screen stays fast to scan rather than becoming its own small decision.

**Banded (BAND).** A multi-choice whose options represent points on a continuum rather than
distinct categories, freshness, history depth, volume. Used where the requester can recognise a
band far more easily than they could produce an exact figure, which is the same instinct behind
asking for grain as a spreadsheet row instead of a schema.

## Layer 00, the problem

All five stay free text. This is the one layer where narrative room matters most: the problem
statement, the current process, the activation use case and the acceptance criteria are each doing
real work in the requester's own words, and nothing here has a small enough answer space to
shortcut. The one split: how often it bites (BAND: daily, weekly, monthly, rarely) is separate from
who else it bites (FT, since role and team names aren't a fixed set).

## Layer 01, the decision

`query_type`: MC, how much, how many, which ones, has something changed, already phrased as options
in the protocol itself. `usage_pattern`: MC, on a schedule or when something feels wrong.
`audience_breadth`: FT for who else, MC yes, no, not sure for whether they're asking the same
question.

## Layer 02, shape of the answer

`primary_measure`: FT, naming a number is inherently open. `dimensions`: HYB, time, location,
product, team, plus something else, or none. `drill_through_required`: MC, yes, no, not sure.
`benchmark_comparison`: HYB, last year, a target, another team, plus something else or none.

## Layer 03, grain

`grain`: HYB, chips drawn straight from the protocol's own suggested examples, one customer, one
order, one day, plus something else. This was the one real judgement call in this layer: chips risk
anchoring the answer toward whichever option is the easiest click, on the single most consequential
field in the system. Decided in favour of chips anyway, because the alternative, a blank text box on
the hardest question in the interview, is the more common way this question fails, and the protocol
was already suggesting these exact examples in its own phrasing. `fan_out_risk` and
`cardinality_risk`: both MC, yes, no, not sure.

## Layer 04, source and truth

`source_systems`, `system_of_record`, `entry_latency`: all FT, system and role names aren't a
predictable set. `restatement_handling`: MC yes, no, not sure, with an optional free text follow-up
when the answer is yes.

## Layer 05, dependency and stewardship

Every field in this layer stays free text: which teams, who to go to, who settles disagreements,
where it flows next, which process stalls, who signs off. All of it is naming specific people,
teams or processes, none of it has a small enough set of common answers to chip, at least not until
enough interviews exist that the retained dependency map could plausibly suggest chips drawn from
prior answers, which is a future extension, not part of this version.

## Layer 06, time

`freshness_sla`: BAND, real-time, same day, next morning, weekly or slower. `schedule_alignment`:
HYB, month end, Monday morning, no particular moment, plus something else. `history_depth`: BAND,
this year only, last two to three years, five years or more, all available history.
`scd_requirement`: MC, what it looked like back then, or only how it looks now.

## Layer 07, definitions

Runs once per term, same widgets each pass. The definition itself: FT, a testable definition has to
be in the requester's own words or it isn't testable. The competing-definition check: MC either way,
when retained knowledge has a matching term, matches, doesn't match, not sure; with no match, worth
flagging, not a concern, not sure, a speculative question doesn't need a text box to be useful.
Exclusions: HYB, tests, internal accounts, cancellations, plus something else or none, straight from
the protocol's own text on what usually gets left out. Synonyms: FT, naming alternate words is
inherently open-ended.

## Layer 08, access and sensitivity

`row_level_security`: MC, everyone sees all of it, or only their own part. `data_classification`:
MC yes, no, not sure, with an optional free text follow-up when the answer is yes. `future_role_design`:
FT, naming who's likely to ask next isn't a predictable set.

## Layer 09, scale

`volume`: BAND, hundreds, thousands, millions, not sure, matching the protocol's own suggested
framing exactly. `growth_rate`: MC, yes, no, not sure.

## What this doesn't decide

This document says what widget each question becomes, not how those widgets are laid out on screen,
how progress through the nine layers is shown, or what the reflection checkpoints look like visually.
That's mockup work, not classification work, and it's next.
