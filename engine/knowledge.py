"""The retained-knowledge seam: what layer 07 checks a term against before asking whether a
prior definition still matches.

Per CLAUDE.md, recalled knowledge enters a new interview as a question, never as an answer.
This module only ever answers "is there a prior definition to ask about", it never supplies
one as a fact. NoRetainedKnowledge is the honest placeholder for when nothing's wired up: it
always says there's nothing on file. SqliteRetainedKnowledge is the real thing, now that e3
(storage, decided in docs/architecture-decisions.md to be SQLite) exists: it reads the same
database engine/storage.py's SqliteStorage writes to.
"""

from abc import ABC, abstractmethod
import json
import sqlite3

from .storage import ensure_schema


class RetainedKnowledge(ABC):
    @abstractmethod
    def definition_for(self, term: str) -> str | None:
        """A prior interview's definition of this term, if one is on file. None if not."""


class NoRetainedKnowledge(RetainedKnowledge):
    """No storage wired up. Always reports nothing on file."""

    def definition_for(self, term: str) -> str | None:
        return None


class SqliteRetainedKnowledge(RetainedKnowledge):
    """Backed by the SQLite file e3's storage seam writes to. Looks across every interview on
    file for this exact term and returns the most recent one that locked - cleared a concrete
    definition, an explicit exclusions answer, and reflection confirmation, per
    docs/interview-branching.md's three lock conditions. A term that came up but never locked
    doesn't count: an unlocked definition is exactly the kind of thing layer 07 exists to catch
    in the first place, not something a later interview should quietly inherit as settled fact.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path
        ensure_schema(self._db_path)  # a lookup can be the very first thing that touches the file

    def definition_for(self, term: str) -> str | None:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT fr.value
                FROM field_records fr
                JOIN interviews i ON i.id = fr.interview_id
                WHERE fr.field_id = ?
                  AND EXISTS (
                      SELECT 1 FROM field_records locked
                      WHERE locked.interview_id = fr.interview_id
                        AND locked.field_id = ?
                        AND locked.value = 'true'
                  )
                ORDER BY i.created_at DESC
                LIMIT 1
                """,
                (f"metric_definition::{term}", f"term_locked::{term}"),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])
