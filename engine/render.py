"""Renders the two output documents from the ledger, per docs/output-template.md and
docs/readiness-scoring.md.

v1 scope: only layer 00 has run, so this renders what those two documents would look like
if the interview stopped right after the problem is understood. Layers 01-09 render blank
in this slice; the layer 07 term-locking rule for blocking gaps is not implemented yet
either, since no terms have been surfaced by a one-layer run. Both are e5 follow-up slices.
"""

from .ledger import Ledger, ProvenanceState, Owner

# The full field list from docs/interview-branching.md's appendix. Anything not yet asked
# renders as a missing, named gap, which is the point: readiness is honest about scope not
# yet covered, not just about what layer 00 happened to collect.
ALL_FIELDS = [
    "problem_statement", "current_process", "frequency", "blast_radius",
    "activation_use_case", "acceptance_criteria",
    "query_type", "usage_pattern", "audience_breadth",
    "primary_measure", "dimensions", "drill_through_required", "benchmark_comparison",
    "grain", "fan_out_risk", "cardinality_risk",
    "source_systems", "system_of_record", "entry_latency", "restatement_handling",
    "downstream_dependencies", "steward", "decision_rights", "onward_flows",
    "criticality_tier", "access_approver",
    "freshness_sla", "schedule_alignment", "history_depth", "scd_requirement",
    "metric_definition", "competing_definition_check", "exclusion_filters", "synonyms",
    "row_level_security", "data_classification", "future_role_design",
    "volume", "growth_rate",
]

# From docs/readiness-scoring.md. The layer 07 "any unlocked term" blocking rule isn't
# implemented yet, since v1 doesn't surface layer 07 terms at all.
BLOCKING_FIELDS = {"query_type", "primary_measure", "grain", "source_systems"}

GAP_REASONS = {
    "query_type": "what kind of answer is wanted hasn't been established",
    "primary_measure": "the number this is actually about hasn't been named",
    "grain": "what one row represents hasn't been established",
    "source_systems": "where this data actually lives hasn't been established",
}


def render_business_ask(ledger: Ledger) -> str:
    problem = ledger.get("problem_statement")
    process = ledger.get("current_process")
    activation = ledger.get("activation_use_case")
    acceptance = ledger.get("acceptance_criteria")

    if problem is None:
        return "(no business ask yet: the problem hasn't been understood)"

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
    lines.append("  We'll work through the rest of the detail needed to size and build this.")
    return "\n".join(lines)


def render_readiness_block(ledger: Ledger) -> str:
    non_missing = 0
    blocking_gaps = []
    workable_gaps = []

    for field_id in ALL_FIELDS:
        record = ledger.get(field_id)
        if record is not None and record.state != ProvenanceState.MISSING:
            non_missing += 1
            continue
        if field_id in BLOCKING_FIELDS:
            blocking_gaps.append(field_id)
        else:
            workable_gaps.append(field_id)

    completion = round(100 * non_missing / len(ALL_FIELDS))
    status = "not ready to size" if blocking_gaps else "ready to size"

    lines = ["READINESS", ""]
    lines.append(f"Status: {status}")
    lines.append(f"Completion: {completion}% ({non_missing}/{len(ALL_FIELDS)} fields)")
    lines.append("")
    if blocking_gaps:
        lines.append(f"Blocking gaps ({len(blocking_gaps)}):")
        for field_id in blocking_gaps:
            reason = GAP_REASONS.get(field_id, "not yet established")
            lines.append(f"  - {field_id}: {reason} (owner: requester)")
        lines.append("")
    lines.append(f"Workable gaps not yet collected: {len(workable_gaps)} "
                  f"(expected this early, layers 01-09 haven't run yet)")
    return "\n".join(lines)
