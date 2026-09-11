"""The storage seam (e3): where an interview's field ledger persists across runs, and where
cross-interview data comes from. Decided in docs/architecture-decisions.md: SQLite via Python's
stdlib `sqlite3`, one local file, zero external dependency, so the eventual Streamlit in
Snowflake port isn't fighting a fussier runtime over a dependency that was never necessary. The
storage interface is what lets that port swap a local file for a Snowflake table without the
engine noticing, the same way the reasoner interface lets e4 swap in a real model call.

v1 scope: persisting a ledger and loading it back, plus the schema the retained-knowledge seam
(engine/knowledge.py's SqliteRetainedKnowledge) queries against. The README also names overlap
detection between requests and a dependency map ("who is affected if this changes") as goals for
this same data. Both are real, both are deferred rather than guessed at here: a useful overlap
query needs some actual interviews on file to see what "overlap" should even mean in practice
(same primary_measure? same source system? same term?), and building that against zero real data
would be exactly the kind of hollow feature CLAUDE.md's claim-integrity rule warns against.
Tracked as its own backlog item (e8) rather than folded into this one.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import sqlite3

from .ledger import Ledger, ProvenanceState


def ensure_schema(db_path: str) -> None:
    """Creates the two tables if they don't exist yet. Shared by SqliteStorage and
    SqliteRetainedKnowledge so a fresh database file works no matter which one touches it
    first (e.g. a term lookup before anything's ever been saved)."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interviews (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS field_records (
                interview_id TEXT NOT NULL,
                field_id TEXT NOT NULL,
                layer TEXT NOT NULL,
                value TEXT NOT NULL,
                state TEXT NOT NULL,
                source TEXT NOT NULL,
                owner TEXT NOT NULL,
                note TEXT NOT NULL,
                PRIMARY KEY (interview_id, field_id),
                FOREIGN KEY (interview_id) REFERENCES interviews(id)
            )
            """
        )


class Storage(ABC):
    @abstractmethod
    def save_interview(self, interview_id: str, ledger: Ledger) -> None:
        """Persists every field currently in the ledger under this interview's id. Safe to call
        more than once for the same id: replaces what's there field by field rather than
        duplicating it, so an in-progress interview can be saved after every layer, not only
        once at the very end."""

    @abstractmethod
    def load_interview(self, interview_id: str) -> Ledger | None:
        """The ledger as it was last saved under this id, or None if nothing's on file."""

    @abstractmethod
    def list_interviews(self) -> list[dict]:
        """One entry per interview on file: id, when it was created, and its primary_measure if
        it has one, as a human-scannable index. Not a query interface in its own right."""


class SqliteStorage(Storage):
    """The real implementation. One file, its schema created on first use if it isn't there."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        ensure_schema(self._db_path)

    def save_interview(self, interview_id: str, ledger: Ledger) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO interviews (id, created_at) VALUES (?, ?) "
                "ON CONFLICT(id) DO NOTHING",
                (interview_id, datetime.now(timezone.utc).isoformat()),
            )
            for record in ledger.all():
                conn.execute(
                    """
                    INSERT INTO field_records
                        (interview_id, field_id, layer, value, state, source, owner, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(interview_id, field_id) DO UPDATE SET
                        layer = excluded.layer, value = excluded.value, state = excluded.state,
                        source = excluded.source, owner = excluded.owner, note = excluded.note
                    """,
                    (
                        interview_id, record.field_id, record.layer,
                        json.dumps(record.value), record.state.name,
                        record.source, record.owner.value, record.note,
                    ),
                )

    def load_interview(self, interview_id: str) -> Ledger | None:
        with sqlite3.connect(self._db_path) as conn:
            exists = conn.execute(
                "SELECT 1 FROM interviews WHERE id = ?", (interview_id,)
            ).fetchone()
            if exists is None:
                return None
            rows = conn.execute(
                "SELECT field_id, layer, value, state, source, note FROM field_records "
                "WHERE interview_id = ?",
                (interview_id,),
            ).fetchall()

        ledger = Ledger()
        for field_id, layer, value_json, state_name, source, note in rows:
            # ledger.set() recomputes ownership from field_id itself (a pure function of the
            # field id, see owner_for() in ledger.py), so the stored owner column is read back
            # as a record of what it was, not trusted as an input here.
            ledger.set(field_id, layer, json.loads(value_json), ProvenanceState[state_name],
                       source=source, note=note)
        return ledger

    def list_interviews(self) -> list[dict]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, created_at FROM interviews ORDER BY created_at"
            ).fetchall()
            summaries = []
            for interview_id, created_at in rows:
                measure_row = conn.execute(
                    "SELECT value FROM field_records WHERE interview_id = ? AND field_id = ?",
                    (interview_id, "primary_measure"),
                ).fetchone()
                measure = json.loads(measure_row[0]) if measure_row is not None else None
                summaries.append({
                    "id": interview_id,
                    "created_at": created_at,
                    "primary_measure": measure,
                })
        return summaries
