"""Where finished documents go once an interview completes: a2 on the build tracker.

Per CLAUDE.md: "Delivery is the thinnest layer... Writing finished documents to a synced folder
is the default, because it reaches SharePoint or OneDrive without any integration, credentials
or tenant configuration. Anything richer is an adapter added later, and delivery must never
block the build." This is exactly that and nothing more: two folders on disk, one file each, no
upload, no API call, no auth. No adapter interface either, on purpose: there is only one
implementation so far, and building an abstraction for a future second one now would be exactly
the speculative scope CLAUDE.md's build discipline warns against ("one tool finished beats three
started"). If a richer delivery mechanism is ever needed, this is the one function that changes.

Two folders, not one, and both required rather than one optional: the business ask is written
for the requester and is fine to land somewhere shared, a synced team folder included; the
technical spec is internal only, per every design doc that touches it ("The requester never sees
the technical spec", docs/output-template.md and CLAUDE.md both say so). Writing both into the
same folder would make that separation trivially easy to break by accident the moment that
folder is a shared or synced one, so `deliver_documents` always takes two destination paths and
never defaults one to the other; DEFAULT_BUSINESS_ASK_DIR and DEFAULT_TECHNICAL_SPEC_DIR below
are deliberately two different local folders, not the same folder twice, so picking up the
defaults can't recreate the mistake either.

e13: both documents moved from plain-text .md files to letterheaded .docx files (see
docs/architecture-decisions.md's e13 entry for the full reasoning, and docs/output-template.md's
Word template addendum for the structure). This module stays free of any direct python-docx
import on purpose, the same dependency-isolation reasoning CLAUDE.md and engine/cortex_reasoner.py
already apply to snowflake.snowpark: it accepts anything with a `.save(path)` method (a
python-docx Document, in practice, built by engine/docx_render.py) rather than importing docx
itself, so this thinnest-layer module never needs to know what a "document" actually is.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

# Local, gitignored, runtime output, not source, same category as requirements_accelerator.db.
# Callers are free to point at real synced folders instead (a OneDrive- or SharePoint-synced
# directory on the machine running this, for instance); these are just a working default so
# cli.py and app.py don't each have to invent one.
DEFAULT_BUSINESS_ASK_DIR = "delivered/business-ask"
DEFAULT_TECHNICAL_SPEC_DIR = "delivered/technical-spec"


class SavesToPath(Protocol):
    """The one thing this module needs from a "document": something that can write itself to a
    path. A python-docx Document satisfies this without this module ever importing docx; see the
    module docstring."""

    def save(self, path) -> None: ...


def _timestamp_slug() -> str:
    # Microsecond resolution: two documents delivered from the same process in the same second
    # (a fast test loop, a batch re-delivery) still get distinct, chronologically sortable names.
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def deliver_documents(
    interview_id: str,
    business_ask: SavesToPath,
    technical_spec: SavesToPath,
    business_ask_dir: str | Path = DEFAULT_BUSINESS_ASK_DIR,
    technical_spec_dir: str | Path = DEFAULT_TECHNICAL_SPEC_DIR,
) -> dict[str, Path]:
    """Saves the two rendered documents as Word (.docx) files, one per folder, each named with a
    UTC timestamp and the interview id so they sort chronologically and never collide with a
    different interview's files. Creates each destination folder if it doesn't already exist.

    business_ask and technical_spec are anything with a `.save(path)` method, in practice the
    Document objects engine/docx_render.py's render_business_ask_docx/render_technical_spec_docx
    build; this function never constructs or inspects one itself.

    Returns {"business_ask": path, "technical_spec": path} so the caller (cli.py, app.py) can
    tell the requester or the data team where to find them, rather than the documents only ever
    existing as something printed to a terminal or rendered in a browser tab that closes.
    """
    stamp = _timestamp_slug()
    short_id = interview_id[:8]

    business_ask_path = Path(business_ask_dir) / f"{stamp}_{short_id}_business-ask.docx"
    technical_spec_path = Path(technical_spec_dir) / f"{stamp}_{short_id}_technical-spec.docx"

    business_ask_path.parent.mkdir(parents=True, exist_ok=True)
    technical_spec_path.parent.mkdir(parents=True, exist_ok=True)

    business_ask.save(str(business_ask_path))
    technical_spec.save(str(technical_spec_path))

    return {"business_ask": business_ask_path, "technical_spec": technical_spec_path}
