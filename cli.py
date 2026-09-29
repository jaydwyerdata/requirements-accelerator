"""Requirements Accelerator, v1 script. No UI: run this from a terminal.

python cli.py

Covers all nine layers (00 through 09), including layer 07's per-term definition loop, and
persists every interview to a local SQLite file (requirements_accelerator.db, gitignored - it's
runtime data, not source) so later interviews can check a term's retained definition against
real prior interviews rather than nothing. Every judgement call goes to ClaudeCodeReasoner (e4):
a real Claude Code CLI subprocess, not a person at the keyboard. Decided and implemented, see
docs/architecture-decisions.md, including what that needs from the environment it runs in
(the `claude` CLI installed and logged in).

Also delivers the two finished documents to disk (e2/a2, engine/delivery.py), not just the
terminal: DEFAULT_BUSINESS_ASK_DIR and DEFAULT_TECHNICAL_SPEC_DIR under delivered/, gitignored,
same category as the SQLite file. Point those two folders at a synced location instead (a
OneDrive- or SharePoint-synced directory on this machine) to get finished documents there with
no integration or tenant configuration; see engine/delivery.py for why they stay two separate
folders rather than one.

e13: the terminal printout below still comes from engine/render.py's plain-text renderers, since
a terminal has no use for a Word document. What gets delivered to disk is different: the
letterheaded .docx documents from engine/docx_render.py, built separately from the same ledger.
"""

import uuid

from engine.ledger import Ledger
from engine.knowledge import SqliteRetainedKnowledge
from engine.storage import SqliteStorage
from engine.reasoner import ClaudeCodeReasoner
from engine.interview import run_interview
from engine.render import render_business_ask, render_technical_spec
from engine.docx_render import render_business_ask_docx, render_technical_spec_docx
from engine.delivery import deliver_documents

DB_PATH = "requirements_accelerator.db"


def main():
    print("Requirements Accelerator (v1)")
    print("=" * 60)
    print()

    ledger = Ledger()
    reasoner = ClaudeCodeReasoner()
    knowledge = SqliteRetainedKnowledge(DB_PATH)
    run_interview(ledger, reasoner, knowledge)

    interview_id = str(uuid.uuid4())
    storage = SqliteStorage(DB_PATH)
    storage.save_interview(interview_id, ledger)

    business_ask = render_business_ask(ledger)
    technical_spec = render_technical_spec(ledger)

    print()
    print("=" * 60)
    print()
    print(business_ask)
    print()
    print(technical_spec)

    delivered = deliver_documents(
        interview_id,
        render_business_ask_docx(ledger, interview_id),
        render_technical_spec_docx(ledger, interview_id),
    )
    print()
    print("=" * 60)
    print(f"Business ask saved to: {delivered['business_ask']}")
    print(f"Technical spec saved to: {delivered['technical_spec']}")


if __name__ == "__main__":
    main()
