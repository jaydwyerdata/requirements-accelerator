"""The Coaxing Protocol, encoded as data, layer by layer.

Question text is copied verbatim from docs/coaxing-protocol.md. Choice lists (for MC, HYB and
BAND questions) come from docs/interview-ux.md, which is the actual widget-classification
authority; the protocol's own phrasing is illustrative, not always the literal option set. This
module is the only place that text should live in code; the interview engine just walks it.
"""

from dataclasses import dataclass


@dataclass
class Question:
    field_id: str
    prompt: str
    layer: str
    choices: list[str] | None = None  # shown as a hint; the CLI still accepts free text
    gated: bool = False  # True only for layer 00's problem statement
    inferred: bool = False  # True if the answer is recorded as inferred, not stated
    # (layer 05's steward and decision_rights: the question is asked live, but the field is
    # the back-of-house's read on the answer, not the answer itself, so it's inferred per
    # docs/interview-branching.md, and only promoted to stated by reflection like any other
    # inference)


MAX_REDIRECT_ATTEMPTS = 2  # layer 00's gate, and layer 07's vagueness loop, share this cap


LAYER_00_QUESTIONS = [
    Question("problem_statement", "What's happening today that shouldn't be?", "00", gated=True),
    Question("current_process", "Walk me through what you do today when you need this.", "00"),
    Question("frequency", "How often does this bite you?", "00",
              choices=["daily", "weekly", "monthly", "rarely"]),
    Question("blast_radius", "And who else does it bite?", "00"),
    Question("activation_use_case", "If this were fixed, what would you do differently on Monday?", "00"),
    Question("acceptance_criteria", "How would you know it worked?", "00"),
]

LAYER_01_QUESTIONS = [
    Question("query_type", "What are you actually asking: how much, how many, which ones, or has "
              "something changed?", "01",
              choices=["how much", "how many", "which ones", "has something changed"]),
    Question("usage_pattern", "Do you check this on a schedule, or go looking when something feels "
              "wrong?", "01", choices=["on a schedule", "when something feels wrong"]),
    Question("audience_breadth", "Who else will look at this, and are they asking the same "
              "question?", "01"),
]

LAYER_02_QUESTIONS = [
    Question("primary_measure", "If I put this on one slide, what's the number in the middle?", "02"),
    Question("dimensions", "What would you want to break that number down by?", "02",
              choices=["time", "location", "product", "team", "something else", "none"]),
    Question("drill_through_required", "Would you ever click a total to see what's inside it?", "02",
              choices=["yes", "no", "not sure"]),
    Question("benchmark_comparison", "Is there anything you'd compare it against: last year, a "
              "target, another team?", "02",
              choices=["last year", "a target", "another team", "something else", "none"]),
]

LAYER_03_QUESTIONS = [
    Question("grain", "If I handed you a spreadsheet of this, what would one row be: one customer, "
              "one order, one day?", "03",
              choices=["one customer", "one order", "one day", "something else"]),
    Question("fan_out_risk", "Could the same one show up on more than one row?", "03",
              choices=["yes", "no", "not sure"]),
    Question("cardinality_risk", "Does one of these ever belong to more than one of those at the "
              "same time?", "03", choices=["yes", "no", "not sure"]),
]

LAYER_04_QUESTIONS = [
    Question("source_systems", "Where do you look today when you need this?", "04"),
    Question("system_of_record", "If two systems showed different numbers, which would you "
              "believe?", "04"),
    Question("entry_latency", "Who types this in, and when in the process?", "04"),
    Question("restatement_handling", "Does anyone go back and correct it after the fact?", "04",
              choices=["yes", "no", "not sure"]),
]

LAYER_05_QUESTIONS = [
    Question("downstream_dependencies", "Which teams would notice if this stopped updating?", "05"),
    Question("steward", "Who do you go to when the numbers look wrong?", "05", inferred=True),
    Question("decision_rights", "If two people disagreed about what this should say, who'd settle "
              "it?", "05", inferred=True),
    Question("onward_flows", "Once you've got this, where does it go next?", "05"),
    Question("criticality_tier", "Which process stalls if this is late or wrong?", "05"),
    Question("access_approver", "Who'd need to sign off on someone new seeing this?", "05"),
]

LAYER_06_QUESTIONS = [
    Question("freshness_sla", "How fresh does this need to be: good enough this morning, or right "
              "this second?", "06",
              choices=["real-time", "same day", "next morning", "weekly or slower"]),
    Question("schedule_alignment", "Is there a moment when this matters most: month end, Monday "
              "morning?", "06", choices=["month end", "Monday morning", "something else", "none"]),
    Question("history_depth", "How far back do you need to see?", "06",
              choices=["this year only", "last two to three years", "five years or more",
                       "all available history"]),
    Question("scd_requirement", "Do you need to see what it looked like back then, or only how it "
              "looks now?", "06",
              choices=["what it looked like back then", "only how it looks now"]),
]

# Layer 07 runs this set once per term queued, not once total. See engine/interview.py.
LAYER_07_QUESTIONS = [
    Question("metric_definition", "When you say \"{term}\", what makes something count?", "07"),
    Question("competing_definition_check", "Would the finance team define that the same way?", "07"),
    Question("exclusion_filters", "Is there anything that shouldn't count: tests, internal "
              "accounts, cancellations?", "07",
              choices=["tests", "internal accounts", "cancellations", "something else", "none"]),
    Question("synonyms", "What do you call this? Does anyone call it something else?", "07"),
]

LAYER_08_QUESTIONS = [
    Question("row_level_security", "Should everyone looking at this see all of it, or only their "
              "own part?", "08", choices=["everyone sees all of it", "only their own part"]),
    Question("data_classification", "Is any of this personal or sensitive: names, pay, anything "
              "you'd not want widely shared?", "08", choices=["yes", "no", "not sure"]),
    Question("future_role_design", "Who's likely to ask for this next?", "08"),
]

LAYER_09_QUESTIONS = [
    Question("volume", "Roughly how many of these are we talking about: hundreds, thousands, "
              "millions?", "09", choices=["hundreds", "thousands", "millions", "not sure"]),
    Question("growth_rate", "Is that number growing fast?", "09", choices=["yes", "no", "not sure"]),
]
