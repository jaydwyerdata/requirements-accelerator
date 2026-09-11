"""Requirements Accelerator, v1 script. No UI: run this from a terminal.

python cli.py

Covers all nine layers (00 through 09), including layer 07's per-term definition loop, and
persists every interview to a local SQLite file (requirements_accelerator.db, gitignored - it's
runtime data, not source) so later interviews can check a term's retained definition against
real prior interviews rather than nothing. Every judgement call goes to ClaudeCodeReasoner (e4):
a real Claude Code CLI subprocess, not a person at the keyboard. Decided and implemented, see
docs/architecture-decisions.md, including what that needs from the environment it runs in
(the `claude` CLI installed and logged in).
"""

import uuid

from engine.ledger import Ledger
from engine.knowledge import SqliteRetainedKnowledge
from engine.storage import SqliteStorage
from engine.reasoner import ClaudeCodeReasoner
from engine.interview import run_interview
from engine.render import render_business_ask, render_technical_spec

DB_PATH = "requirements_accelerator.db"


def main():
    print("Requirements Accelerator (v1)")
    print("=" * 60)
    print()

    ledger = Ledger()
    reasoner = ClaudeCodeReasoner()
    knowledge = SqliteRetainedKnowledge(DB_PATH)
    run_interview(ledger, reasoner, knowledge)

    storage = SqliteStorage(DB_PATH)
    storage.save_interview(str(uuid.uuid4()), ledger)

    print()
    print("=" * 60)
    print()
    print(render_business_ask(ledger))
    print()
    print(render_technical_spec(ledger))


if __name__ == "__main__":
    main()
