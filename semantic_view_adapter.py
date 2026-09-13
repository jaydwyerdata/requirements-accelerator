"""a1: turns one finished interview into a Snowflake CREATE SEMANTIC VIEW skeleton, the first
platform-specific output CLAUDE.md names. Run this on demand against a completed interview, not
part of the live interview path.

python semantic_view_adapter.py --list [db_path]
python semantic_view_adapter.py <interview_id> [db_path]

Defaults to requirements_accelerator.db, the same file cli.py writes to. See
engine/semantic_view.py and docs/architecture-decisions.md's "a1 scope" entry for what this
does and does not attempt: it never invents a physical table or column reference, since the
interview it reads never asks for one.
"""

import sys

from engine.semantic_view import build_semantic_view_plan, render_semantic_view_sql
from engine.storage import SqliteStorage

DEFAULT_DB_PATH = "requirements_accelerator.db"


def main():
    args = sys.argv[1:]

    if not args or args[0] == "--list":
        db_path = args[1] if len(args) > 1 else DEFAULT_DB_PATH
        storage = SqliteStorage(db_path)
        entries = storage.list_interviews()
        if not entries:
            print("No interviews on file.")
            return
        for entry in entries:
            print(f"{entry['id']}  (created {entry['created_at']})")
        return

    interview_id = args[0]
    db_path = args[1] if len(args) > 1 else DEFAULT_DB_PATH

    storage = SqliteStorage(db_path)
    ledger = storage.load_interview(interview_id)
    if ledger is None:
        print(f"No interview on file with id {interview_id!r}. Run with --list to see what's there.")
        return

    plan = build_semantic_view_plan(interview_id, ledger)
    print(render_semantic_view_sql(plan))


if __name__ == "__main__":
    main()
