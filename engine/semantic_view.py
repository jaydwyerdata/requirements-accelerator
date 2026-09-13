"""a1: the Snowflake semantic view adapter (see docs/architecture-decisions.md's "a1 scope"
entry). Turns one finished interview's captured requirements into a CREATE SEMANTIC VIEW
skeleton, the first platform-specific output CLAUDE.md names, aimed at Cortex Analyst and
Snowflake Intelligence.

Scoped narrowly, and deliberately: the interview never asks for physical schema, table names
or column names, by design, since a non-technical requester can't answer that. So this adapter
never invents a table or column reference, that would be exactly the kind of hollow,
undefendable claim CLAUDE.md's claim-integrity rule already rules out elsewhere (e8's
find_conceptual_overlaps has the same discipline, for a different reason). Every physical
reference in the generated DDL is an explicit TODO placeholder for a data engineer to fill in;
everything the interview actually captured, in business language, definitions, synonyms,
exclusions, is filled in for real.

One interview in, one semantic view out. Unlike e8's overlap_report.py, this is not a
cross-interview planning-time report, it is a per-interview adapter, matching CLAUDE.md's own
framing: "turns a finished interview's captured requirements into Snowflake DDL".

A stated, undisguised assumption this module makes, since the ledger doesn't record it
directly: the interview's primary_measure becomes the one METRICS entry, and every other
locked business term (layer 07) becomes a DIMENSIONS entry, a named category or segment, not a
further metric. Layer 07's own question ("what makes something count") is fundamentally about
membership in a category, not necessarily an aggregation, so DIMENSIONS is the more
conservative read, but it is a read, not something the ledger states outright. Flagged here and
in the generated file's header rather than left silent.

CREATE SEMANTIC VIEW syntax below was verified against Snowflake's own reference
(docs.snowflake.com/en/sql-reference/sql/create-semantic-view) and worked example
(docs.snowflake.com/en/user-guide/views-semantic/sql) on 13 September 2026, not recalled from
memory, per the same claim-integrity discipline this repo holds its own documentation to.
"""

from dataclasses import dataclass, field
import re

from .ledger import Ledger

TODO_TABLE = "TODO_PHYSICAL_TABLE"
TODO_KEY_COLUMN = "TODO_GRAIN_KEY_COLUMN"
TODO_EXPRESSION = "TODO_PHYSICAL_EXPRESSION"

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_QUOTE_RE = re.compile(r"['‘’]([^'‘’]{1,60})['‘’]")


def _slug(text: str) -> str:
    """A valid, unquoted SQL identifier from free text: lowercase, non-alphanumeric collapsed
    to a single underscore, trimmed. Used for the table alias and every dimension/metric name,
    since none of these exist as real identifiers until a data engineer maps them onto a
    physical schema."""
    slug = _SLUG_RE.sub("_", text.strip().lower()).strip("_")
    if not slug:
        slug = "unnamed"
    if slug[0].isdigit():
        slug = f"t_{slug}"
    return slug


def _extract_quoted(text: str) -> list[str]:
    """Only pulls phrases the requester actually put in quotes (docs/synthetic-dataset.md's
    two synonym answers both do this: "call it a 'stock risk' or a 'run-out'"). Never splits or
    guesses at unquoted prose, that would be inventing a synonym the requester didn't actually
    give as one."""
    return _QUOTE_RE.findall(text)


def _sql_escape(text: str) -> str:
    return text.replace("'", "''")


@dataclass
class SemanticEntry:
    name: str
    business_definition: str
    synonyms: list[str] = field(default_factory=list)
    note: str | None = None  # an exclusion, or other context worth keeping visible


@dataclass
class SemanticViewPlan:
    interview_id: str
    table_alias: str
    grain_text: str | None
    source_note: str | None
    primary_measure: SemanticEntry | None
    breakdown_dimensions: list[SemanticEntry]
    locked_term_dimensions: list[SemanticEntry]
    gaps: list[str]

    @property
    def all_dimensions(self) -> list[SemanticEntry]:
        return self.breakdown_dimensions + self.locked_term_dimensions


def build_semantic_view_plan(interview_id: str, ledger: Ledger) -> SemanticViewPlan:
    """Reads one interview's ledger (as Storage.load_interview returns it) and works out what
    it can and can't say. Never queries storage directly: a1 only needs one interview at a
    time, so the existing Ledger seam is enough, unlike e8's cross-interview queries."""
    gaps: list[str] = []

    primary_measure = None
    if ledger.is_missing("primary_measure"):
        gaps.append("primary_measure was never established: no METRICS entry generated.")
    else:
        text = str(ledger.get("primary_measure").value)
        primary_measure = SemanticEntry(name=_slug(text), business_definition=text)

    grain_text = None
    if ledger.is_missing("grain"):
        gaps.append("grain was never established: the PRIMARY KEY comment stays generic.")
    else:
        grain_text = str(ledger.get("grain").value)

    breakdown_dimensions: list[SemanticEntry] = []
    if not ledger.is_missing("dimensions"):
        raw = str(ledger.get("dimensions").value)
        if raw.strip().lower() not in ("none", "n/a", ""):
            for part in re.split(r",| and ", raw):
                part = part.strip()
                if part:
                    breakdown_dimensions.append(
                        SemanticEntry(name=_slug(part), business_definition=part)
                    )

    term_fields: dict[str, dict[str, object]] = {}
    for record in ledger.all():
        if "::" not in record.field_id:
            continue
        kind, term = record.field_id.split("::", 1)
        term_fields.setdefault(term, {})[kind] = record.value

    locked_term_dimensions: list[SemanticEntry] = []
    for term, data in term_fields.items():
        if not data.get("term_locked"):
            continue  # unlocked terms aren't settled, same rule engine/overlap.py already uses
        definition = str(data.get("metric_definition", ""))
        synonyms = _extract_quoted(str(data.get("synonyms", "")))
        exclusion = data.get("exclusion_filters")
        note = None
        if exclusion and str(exclusion).strip().lower() not in ("none", "n/a", ""):
            note = f"Excludes: {exclusion}"
        locked_term_dimensions.append(SemanticEntry(
            name=_slug(term), business_definition=definition, synonyms=synonyms, note=note,
        ))

    source_note = None
    if not ledger.is_missing("source_systems"):
        source_note = str(ledger.get("source_systems").value)

    return SemanticViewPlan(
        interview_id=interview_id,
        table_alias=_slug(interview_id),
        grain_text=grain_text,
        source_note=source_note,
        primary_measure=primary_measure,
        breakdown_dimensions=breakdown_dimensions,
        locked_term_dimensions=locked_term_dimensions,
        gaps=gaps,
    )


def _render_entry(alias: str, entry: SemanticEntry) -> str:
    comment_parts = [entry.business_definition]
    if entry.note:
        comment_parts.append(entry.note)
    comment = ". ".join(p.strip().rstrip(".") for p in comment_parts if p.strip())
    lines = [f"    {alias}.{entry.name} AS {TODO_EXPRESSION}  -- fill in against the real schema"]
    if entry.synonyms:
        synonym_list = ", ".join(f"'{_sql_escape(s)}'" for s in entry.synonyms)
        lines.append(f"      WITH SYNONYMS = ({synonym_list})")
    lines.append(f"      COMMENT = '{_sql_escape(comment)}'")
    return "\n".join(lines)


def render_semantic_view_sql(plan: SemanticViewPlan) -> str:
    """Renders the plan as CREATE SEMANTIC VIEW DDL, or, if Snowflake's own syntax requirement
    can't be met yet (at least one DIMENSIONS or METRICS entry), an honest explanation instead
    of DDL known to be invalid."""
    header = [
        f"-- Snowflake semantic view scaffold for interview '{plan.interview_id}'.",
        "-- Generated by a1 (engine/semantic_view.py), not hand-written.",
        "--",
        "-- Every physical table and column reference below is an explicit TODO placeholder,",
        "-- never invented: the interview that produced this never asks for physical schema,",
        "-- by design, so this adapter has nothing real to put there. Fill in every TODO",
        "-- against the actual warehouse before running this.",
        "--",
        "-- Stated assumption, not verified against the interview directly: the primary",
        "-- measure becomes the one METRICS entry, every other locked business term becomes a",
        "-- DIMENSIONS entry (a named category, not a further metric). See",
        '-- docs/architecture-decisions.md\'s "a1 scope" entry for the reasoning.',
    ]
    if plan.source_note:
        header.append(f"--\n-- Where the requester said this data lives today: {plan.source_note}")
    if plan.gaps:
        header.append("--\n-- Gaps carried over from the interview itself:")
        for gap in plan.gaps:
            header.append(f"--   - {gap}")

    all_dimensions = plan.all_dimensions
    if not all_dimensions and not plan.primary_measure:
        header.append("--")
        header.append("-- No semantic view generated: Snowflake requires at least one DIMENSIONS")
        header.append("-- or METRICS entry, and this interview hasn't established a primary")
        header.append("-- measure or locked a single business term yet. Re-run once it has.")
        return "\n".join(header)

    view_name = f"{plan.table_alias}_semantic_view"
    grain_comment = plan.grain_text or "not established by the interview"
    table_source = plan.source_note or "wherever this data actually lives"

    body = [
        "",
        f"CREATE OR REPLACE SEMANTIC VIEW {view_name}",
        "  TABLES (",
        f"    {plan.table_alias} AS {TODO_TABLE}  -- the table or view backing: {table_source}",
        f"      PRIMARY KEY ({TODO_KEY_COLUMN})",
        f"      COMMENT = 'One row = {_sql_escape(grain_comment)}, as stated in the interview.'",
        "  )",
        "",
        "  -- No FACTS clause: this adapter only produces aggregate METRICS from the",
        "  -- interview's primary measure and locked terms, never a row-level numeric",
        "  -- expression, since the interview doesn't capture one.",
        "",
    ]

    if all_dimensions:
        body.append("  DIMENSIONS (")
        body.append(",\n".join(_render_entry(plan.table_alias, d) for d in all_dimensions))
        body.append("  )")
    else:
        body.append("  -- No DIMENSIONS generated: no breakdown and no locked term on file yet.")
    body.append("")

    if plan.primary_measure:
        body.append("  METRICS (")
        body.append(_render_entry(plan.table_alias, plan.primary_measure))
        body.append("  )")
    else:
        body.append("  -- No METRICS generated: primary_measure was never established.")
    body.append("")

    body.append(
        f"  COMMENT = 'Scaffold generated from interview {_sql_escape(plan.interview_id)}. "
        f"Replace every TODO before use.'"
    )
    body.append(";")

    return "\n".join(header + body)
