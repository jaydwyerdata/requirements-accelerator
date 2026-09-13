"""e8, Phase A (see docs/architecture-decisions.md's "e8 scope" entry): a planning-time report
over every interview already saved, not a per-interview output. Reads the same SQLite database
engine/storage.py writes to and adds nothing to the live interview path, so an interview stays as
fast and self-serve as it already is.

Everything here is a plain query over data engine/interview.py already recorded live: which
terms two or more interviews used and what each one said about it (layer 07's own
metric_definition, term_locked and competing_definition_check fields), and who each interview
named as a stakeholder for a term it locked (layer 00's blast_radius, layer 01's
audience_breadth, layer 05's downstream_dependencies, steward, decision_rights and
access_approver). No reasoner call, so nothing here can invent a connection between interviews
that isn't already on the ledger.

Deliberately narrow: this does not attempt to resolve "the regional merchandising lead" and
"regional merchandising" into one entity, and it does not catch a term two interviews mean the
same thing by under different words ("active customer" vs "engaged member"). Both are real,
both are out of scope for Phase A, see the architecture-decisions.md entry for why.
"""

from contextlib import closing
from dataclasses import dataclass, field
import json
import sqlite3

from .storage import ensure_schema

STAKEHOLDER_FIELDS = (
    "blast_radius", "audience_breadth", "downstream_dependencies",
    "steward", "decision_rights", "access_approver",
)


@dataclass
class TermOccurrence:
    interview_id: str
    created_at: str
    definition: str | None = None
    locked: bool | None = None
    competing_check: str | None = None


@dataclass
class TermGroup:
    term: str
    occurrences: list[TermOccurrence] = field(default_factory=list)

    @property
    def seen_by_multiple_interviews(self) -> bool:
        return len(self.occurrences) > 1


@dataclass
class StakeholderSnapshot:
    interview_id: str
    created_at: str
    values: dict[str, str]  # field name -> what that interview said, only fields it answered


@dataclass
class DependencyEntry:
    term: str
    snapshots: list[StakeholderSnapshot] = field(default_factory=list)


def _connect(db_path: str):
    ensure_schema(db_path)  # a report can be the first thing that touches a fresh file
    return closing(sqlite3.connect(db_path))


def term_groups(db_path: str) -> list[TermGroup]:
    """Every term that at least one interview ran layer 07 against, in the order each
    interview touched it. A term with more than one occurrence is exactly the overlap
    signal e8 exists to surface: what each interview said it means, and whether the
    interview that came later thought it matched.
    """
    groups: dict[str, TermGroup] = {}
    order: list[str] = []

    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT i.id, i.created_at, fr.field_id, fr.value
            FROM field_records fr
            JOIN interviews i ON i.id = fr.interview_id
            WHERE fr.field_id LIKE 'metric_definition::%'
               OR fr.field_id LIKE 'term_locked::%'
               OR fr.field_id LIKE 'competing_definition_check::%'
            ORDER BY i.created_at
            """
        ).fetchall()

    by_interview_term: dict[tuple[str, str], TermOccurrence] = {}
    created_at_by_interview: dict[str, str] = {}

    for interview_id, created_at, field_id, value_json in rows:
        kind, term = field_id.split("::", 1)
        created_at_by_interview[interview_id] = created_at
        key = (interview_id, term)
        if key not in by_interview_term:
            by_interview_term[key] = TermOccurrence(interview_id=interview_id, created_at=created_at)
            if term not in groups:
                groups[term] = TermGroup(term=term)
                order.append(term)
        occurrence = by_interview_term[key]
        value = json.loads(value_json)
        if kind == "metric_definition":
            occurrence.definition = value
        elif kind == "term_locked":
            occurrence.locked = value
        elif kind == "competing_definition_check":
            occurrence.competing_check = value

    for term in order:
        occurrences = [
            occurrence for (interview_id, t), occurrence in by_interview_term.items() if t == term
        ]
        occurrences.sort(key=lambda o: o.created_at)
        groups[term].occurrences = occurrences

    return [groups[term] for term in order]


def dependency_view(db_path: str) -> list[DependencyEntry]:
    """For every term at least one interview locked, every locking interview's own stakeholder
    answers, verbatim, in the order those interviews ran. Deliberately not resolved into named
    entities across interviews: shows what was said, not a graph of what it means. See this
    module's docstring for why that resolution is out of scope here.
    """
    with _connect(db_path) as conn:
        locked_rows = conn.execute(
            """
            SELECT i.id, i.created_at, fr.field_id, fr.value
            FROM field_records fr
            JOIN interviews i ON i.id = fr.interview_id
            WHERE fr.field_id LIKE 'term_locked::%'
            ORDER BY i.created_at
            """
        ).fetchall()

        locked_interview_ids = {
            interview_id for interview_id, _created_at, _field_id, value_json in locked_rows
            if json.loads(value_json)
        }
        if not locked_interview_ids:
            return []

        placeholders = ", ".join("?" for _ in locked_interview_ids)
        stakeholder_rows = conn.execute(
            f"""
            SELECT interview_id, field_id, value
            FROM field_records
            WHERE interview_id IN ({placeholders})
              AND field_id IN ({", ".join("?" for _ in STAKEHOLDER_FIELDS)})
            """,
            (*locked_interview_ids, *STAKEHOLDER_FIELDS),
        ).fetchall()

    stakeholders_by_interview: dict[str, dict[str, str]] = {}
    for interview_id, field_id, value_json in stakeholder_rows:
        stakeholders_by_interview.setdefault(interview_id, {})[field_id] = json.loads(value_json)

    entries: dict[str, DependencyEntry] = {}
    order: list[str] = []
    for interview_id, created_at, field_id, value_json in locked_rows:
        if not json.loads(value_json):
            continue
        term = field_id.split("::", 1)[1]
        if term not in entries:
            entries[term] = DependencyEntry(term=term)
            order.append(term)
        entries[term].snapshots.append(
            StakeholderSnapshot(
                interview_id=interview_id,
                created_at=created_at,
                values=stakeholders_by_interview.get(interview_id, {}),
            )
        )

    return [entries[term] for term in order]


def locked_term_definitions(groups: list[TermGroup]) -> dict[str, str]:
    """One definition per locked term, for Phase B's semantic pass. Where more than one
    interview locked the same term, uses the most recently locked one, the same recency
    convention SqliteRetainedKnowledge.definition_for already uses, with the same caveat:
    recency, not authority, decides which definition this is."""
    definitions: dict[str, str] = {}
    for group in groups:
        locked = [o for o in group.occurrences if o.locked]
        if locked:
            definitions[group.term] = locked[-1].definition  # occurrences are created_at order
    return definitions


def render_conceptual_overlaps(groups: list[list[str]]) -> str:
    """Phase B's output: a flag to review, never an asserted fact, same as retained knowledge's
    own competing-definition check. Kept separate from render_report since it needs a live
    reasoner call and Phase A's report does not."""
    lines = ["POSSIBLE SAME-CONCEPT TERMS (unconfirmed, worth a human review)", ""]
    if not groups:
        lines.append("Nothing flagged this run.")
        return "\n".join(lines)
    for group in groups:
        lines.append("  " + " / ".join(f'"{t}"' for t in group))
    return "\n".join(lines)


def render_report(groups: list[TermGroup], dependencies: list[DependencyEntry]) -> str:
    """Plain-text rendering, for a human reading this at planning time, not a requester. No
    interpretation added beyond what the ledger already recorded."""
    lines: list[str] = []

    lines.append("TERM OVERLAP")
    lines.append("")
    overlapping = [g for g in groups if g.seen_by_multiple_interviews]
    if not overlapping:
        lines.append("No term has been checked by more than one interview yet.")
    for grp in overlapping:
        lines.append(f'"{grp.term}"')
        for occ in grp.occurrences:
            locked_note = "locked" if occ.locked else "not locked"
            check_note = f", competing check: {occ.competing_check!r}" if occ.competing_check else ""
            lines.append(f"  {occ.interview_id} ({locked_note}){check_note}")
            lines.append(f"    {occ.definition}")
        lines.append("")

    single_occurrence = [g for g in groups if not g.seen_by_multiple_interviews]
    if single_occurrence:
        lines.append("Terms seen by only one interview so far (nothing to compare yet):")
        for grp in single_occurrence:
            occ = grp.occurrences[0]
            locked_note = "locked" if occ.locked else "not locked"
            lines.append(f'  "{grp.term}" ({occ.interview_id}, {locked_note})')
        lines.append("")

    lines.append("DEPENDENCY VIEW (locked terms only)")
    lines.append("")
    if not dependencies:
        lines.append("No term has locked yet.")
    for entry in dependencies:
        lines.append(f'"{entry.term}"')
        for snap in entry.snapshots:
            lines.append(f"  {snap.interview_id}")
            for field_name in STAKEHOLDER_FIELDS:
                if field_name in snap.values:
                    lines.append(f"    {field_name.replace('_', ' ')}: {snap.values[field_name]}")
        lines.append("")

    return "\n".join(lines)
