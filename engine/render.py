"""Renders the two output documents from the ledger, per docs/output-template.md and
docs/readiness-scoring.md.

Now that the interview covers all ten layers, including layer 07's per-term loop, this renders the
full shape both documents are meant to have: a readiness block, then layers 00 through 09
field by field, a definitions subsection keyed by term, and a reporting specification
appendix whenever a primary measure exists.

An unlocked layer 07 term is treated as a blocking gap, the same tier as
query_type/primary_measure/grain/source_systems. This matches docs/readiness-scoring.md's own
blocking list directly: an unlocked term is its fifth named condition alongside those four
fields, so this module isn't extending beyond that document, it's carrying out what the document
already specifies.
"""

from .ledger import Ledger, ProvenanceState, Owner, owner_for

LAYER_FIELDS = {
    "00": ["problem_statement", "current_process", "frequency", "blast_radius",
           "activation_use_case", "acceptance_criteria"],
    "01": ["query_type", "usage_pattern", "audience_breadth"],
    "02": ["primary_measure", "dimensions", "drill_through_required", "benchmark_comparison"],
    "03": ["grain", "fan_out_risk", "cardinality_risk"],
    "04": ["source_systems", "system_of_record", "entry_latency", "restatement_handling"],
    "05": ["downstream_dependencies", "steward", "decision_rights", "onward_flows",
           "criticality_tier", "access_approver"],
    "06": ["freshness_sla", "schedule_alignment", "history_depth", "scd_requirement"],
    "08": ["row_level_security", "data_classification", "future_role_design"],
    "09": ["volume", "growth_rate"],
    # layer 07 has no fixed field list - it's a loop over queued terms, rendered separately
    # in the Definitions subsection, per docs/output-template.md.
}

LAYER_NAMES = {
    "00": "Layer 00: the problem",
    "01": "Layer 01: query shape",
    "02": "Layer 02: the measure",
    "03": "Layer 03: grain",
    "04": "Layer 04: source and trust",
    "05": "Layer 05: stewardship and dependencies",
    "06": "Layer 06: freshness and history",
    "08": "Layer 08: access and sensitivity",
    "09": "Layer 09: scale",
}

ALL_FIELDS = [field_id for fields in LAYER_FIELDS.values() for field_id in fields]

BLOCKING_FIELDS = {"query_type", "primary_measure", "grain", "source_systems"}

GAP_REASONS = {
    "query_type": "what kind of answer is wanted hasn't been established",
    "primary_measure": "the number this is actually about hasn't been named",
    "grain": "what one row represents hasn't been established",
    "source_systems": "where this data actually lives hasn't been established",
}

# Plain-language phrasing for the business ask's "what happens next" beat. Only fields the
# requester themselves owns belong here - a gap the data team can close on its own (like
# source_systems) is never surfaced to the requester, per docs/output-template.md.
GAP_PLAIN_LANGUAGE = {
    "query_type": "we'd still like to nail down exactly what kind of answer you're after",
    "primary_measure": "we'd still like to name the one number this is actually about",
    "grain": "we'd still like to agree on what one row of this actually represents",
}


def _terms_in_ledger(ledger: Ledger) -> list[str]:
    terms: list[str] = []
    for record in ledger.all():
        if "::" in record.field_id:
            term = record.field_id.split("::", 1)[1]
            if term not in terms:
                terms.append(term)
    return terms


def render_business_ask(ledger: Ledger) -> str:
    problem = ledger.get("problem_statement")
    if problem is None or problem.state == ProvenanceState.MISSING:
        return "(no business ask yet: the problem hasn't been understood)"

    process = ledger.get("current_process")
    activation = ledger.get("activation_use_case")
    acceptance = ledger.get("acceptance_criteria")

    lines = ["THE BUSINESS ASK", ""]
    lines.append("What we understood:")
    lines.append(f"  {problem.value}")
    if process is not None:
        lines.append(f"  Today, this is handled by: {process.value}")
    lines.append("")
    lines.append("What you're trying to solve:")
    if activation is not None:
        lines.append(f"  {activation.value}")
    if acceptance is not None:
        lines.append(f"  You'll know it's fixed when: {acceptance.value}")
    lines.append("")
    lines.append("What happens next:")

    requester_gaps = []
    for field_id in ("query_type", "primary_measure", "grain"):
        record = ledger.get(field_id)
        if record is None or record.state == ProvenanceState.MISSING:
            requester_gaps.append(GAP_PLAIN_LANGUAGE[field_id])
    for term in _terms_in_ledger(ledger):
        locked = ledger.get(f"term_locked::{term}")
        if locked is None or not locked.value:
            requester_gaps.append(f"we'd still like to pin down exactly what \"{term}\" means")

    if requester_gaps:
        for gap in requester_gaps:
            lines.append(f"  {gap}")
    else:
        lines.append("  This is ready to size and build.")
    return "\n".join(lines)


def render_readiness_block(ledger: Ledger) -> str:
    non_missing = 0
    blocking_gaps: list[tuple[str, str, Owner]] = []
    workable_gaps = []

    for field_id in ALL_FIELDS:
        record = ledger.get(field_id)
        if record is not None and record.state != ProvenanceState.MISSING:
            non_missing += 1
            continue
        if field_id in BLOCKING_FIELDS:
            blocking_gaps.append((field_id, GAP_REASONS.get(field_id, "not yet established"),
                                   owner_for(field_id)))
        else:
            workable_gaps.append(field_id)

    total_fields = len(ALL_FIELDS)
    for term in _terms_in_ledger(ledger):
        total_fields += 1
        locked = ledger.get(f"term_locked::{term}")
        if locked is not None and locked.value:
            non_missing += 1
        else:
            reason = locked.note if (locked is not None and locked.note) else "not yet locked"
            blocking_gaps.append((f"term: {term}", reason, owner_for("metric_definition")))

    completion = round(100 * non_missing / total_fields) if total_fields else 0
    status = "not ready to size" if blocking_gaps else "ready to size"

    lines = ["READINESS", ""]
    lines.append(f"Status: {status}")
    lines.append(f"Completion: {completion}% ({non_missing}/{total_fields} fields)")
    lines.append("")
    if blocking_gaps:
        lines.append(f"Blocking gaps ({len(blocking_gaps)}):")
        for field_id, reason, owner in blocking_gaps:
            lines.append(f"  - {field_id}: {reason} (owner: {owner.value})")
        lines.append("")
    lines.append(f"Workable gaps not yet collected: {len(workable_gaps)}")
    return "\n".join(lines)


def render_field_line(ledger: Ledger, field_id: str) -> str:
    record = ledger.get(field_id)
    if record is None or record.state == ProvenanceState.MISSING:
        owner = owner_for(field_id)
        return f"  - {field_id}: MISSING (owner: {owner.value})"
    line = f"  - {field_id}: {record.value} [{record.state.name.lower()}, source: {record.source}]"
    if record.note:
        line += f" -- {record.note}"
    return line


def render_definitions_section(ledger: Ledger) -> str:
    terms = _terms_in_ledger(ledger)
    if not terms:
        return "DEFINITIONS\n\n  (no ambiguous terms surfaced)"
    lines = ["DEFINITIONS", ""]
    for term in terms:
        definition = ledger.get(f"metric_definition::{term}")
        competing = ledger.get(f"competing_definition_check::{term}")
        exclusions = ledger.get(f"exclusion_filters::{term}")
        synonyms = ledger.get(f"synonyms::{term}")
        locked = ledger.get(f"term_locked::{term}")
        status = "locked" if (locked is not None and locked.value) else "not locked"
        lines.append(f"\"{term}\" -- {status}")
        if definition is not None:
            lines.append(f"  Definition: {definition.value}")
        if exclusions is not None:
            lines.append(f"  Excludes: {exclusions.value}")
        if synonyms is not None:
            lines.append(f"  Also called: {synonyms.value}")
        if competing is not None:
            lines.append(f"  Competing definition check: {competing.value}")
        if locked is not None and not locked.value and locked.note:
            lines.append(f"  Gap: {locked.note}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_reporting_spec(ledger: Ledger) -> str:
    primary_measure = ledger.get("primary_measure")
    if primary_measure is None or primary_measure.state == ProvenanceState.MISSING:
        return ""

    dimensions = ledger.get("dimensions")
    drill = ledger.get("drill_through_required")
    grain = ledger.get("grain")
    benchmark = ledger.get("benchmark_comparison")
    freshness = ledger.get("freshness_sla")
    schedule = ledger.get("schedule_alignment")
    rls = ledger.get("row_level_security")

    terms = _terms_in_ledger(ledger)
    filter_parts = []
    for term in terms:
        exclusions = ledger.get(f"exclusion_filters::{term}")
        if exclusions is not None:
            filter_parts.append(f"{term}: {exclusions.value}")
    filters_text = "; ".join(filter_parts) if filter_parts else "not established"

    refresh_text = freshness.value if freshness is not None else "not established"
    if schedule is not None and str(schedule.value).strip().lower() not in ("", "none"):
        refresh_text += f", aligned to {schedule.value}"

    lines = ["REPORTING SPECIFICATION", ""]
    lines.append(f"Measure: {primary_measure.value}")
    lines.append(f"Dimensions: {dimensions.value if dimensions is not None else 'not established'}")
    lines.append(f"Drill path: {drill.value if drill is not None else 'not established'} "
                 f"(grain: {grain.value if grain is not None else 'not established'})")
    lines.append(f"Comparison basis: {benchmark.value if benchmark is not None else 'not established'}")
    lines.append(f"Filters: {filters_text}")
    lines.append(f"Refresh cadence: {refresh_text}")
    lines.append(f"Row-level security: {rls.value if rls is not None else 'not established'}")
    return "\n".join(lines)


def render_technical_spec(ledger: Ledger) -> str:
    lines = [render_readiness_block(ledger), ""]
    for layer_id, fields in LAYER_FIELDS.items():
        lines.append(LAYER_NAMES[layer_id])
        for field_id in fields:
            lines.append(render_field_line(ledger, field_id))
        lines.append("")
    lines.append(render_definitions_section(ledger))
    lines.append("")
    reporting = render_reporting_spec(ledger)
    if reporting:
        lines.append(reporting)
    return "\n".join(lines).rstrip()
