"""e8: a planning-time report over every interview already saved, not part of the live
interview path. Run this on demand, not per interview.

python overlap_report.py [db_path]
python overlap_report.py [db_path] --semantic

Defaults to requirements_accelerator.db, the same file cli.py writes to. Phase A (the default)
is pure queries over data already on the ledger, no reasoner call, no usage cost. --semantic adds
Phase B: one batched ClaudeCodeReasoner call across every locked term's definition, looking for
terms that describe the same idea under different words (retained knowledge's exact-string
matching can't catch this on its own, see docs/synthetic-dataset.md's "active customer" /
"engaged member" case). Off by default since it's a real model call, not free and not
deterministic; its output is always a flag to review, never asserted as fact. See engine/overlap.py
and docs/architecture-decisions.md's "e8 scope" entry for the reasoning behind both.
"""

import sys

from engine.overlap import (
    term_groups, dependency_view, render_report,
    locked_term_definitions, render_conceptual_overlaps,
)

DEFAULT_DB_PATH = "requirements_accelerator.db"


def main():
    args = sys.argv[1:]
    semantic = "--semantic" in args
    positional = [a for a in args if a != "--semantic"]
    db_path = positional[0] if positional else DEFAULT_DB_PATH

    groups = term_groups(db_path)
    dependencies = dependency_view(db_path)
    print(render_report(groups, dependencies))

    if semantic:
        from engine.reasoner import ClaudeCodeReasoner

        print()
        definitions = locked_term_definitions(groups)
        overlaps = ClaudeCodeReasoner(timeout_seconds=120).find_conceptual_overlaps(definitions)
        print(render_conceptual_overlaps(overlaps))


if __name__ == "__main__":
    main()
