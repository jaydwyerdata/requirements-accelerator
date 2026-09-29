"""Tests for engine/delivery.py (a2): writing the two finished documents to disk as .docx files.
Builds minimal real python-docx Document objects as fixtures (delivery.py doesn't import docx
itself, but its tests are free to, since proving the save-and-reopen round trip is the whole
point), calls deliver_documents, then reopens the saved files to check they actually landed.
tempfile.TemporaryDirectory() per test, no engine dependency beyond the delivery module and
python-docx, since delivery itself stays the thinnest possible layer per CLAUDE.md.
"""

import os
import tempfile
import unittest
from pathlib import Path

from docx import Document

from engine.delivery import deliver_documents


def _doc(marker: str) -> Document:
    doc = Document()
    doc.add_paragraph(marker)
    return doc


def _first_paragraph_text(path: Path) -> str:
    return Document(str(path)).paragraphs[0].text


class DeliverDocumentsTest(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self.business_ask_dir = os.path.join(self._tmp_dir.name, "business-ask")
        self.technical_spec_dir = os.path.join(self._tmp_dir.name, "technical-spec")

    def test_writes_each_document_to_its_own_folder_with_its_own_content(self):
        delivered = deliver_documents(
            "interview-1234", _doc("the business ask text"), _doc("the technical spec text"),
            self.business_ask_dir, self.technical_spec_dir,
        )
        self.assertEqual(_first_paragraph_text(delivered["business_ask"]),
                          "the business ask text")
        self.assertEqual(_first_paragraph_text(delivered["technical_spec"]),
                          "the technical spec text")
        # Never the same folder, even if a caller passed the same content to both: the two
        # destination directories are what keeps the requester-facing and internal-only
        # documents apart, not anything about the content itself.
        self.assertEqual(delivered["business_ask"].parent, Path(self.business_ask_dir))
        self.assertEqual(delivered["technical_spec"].parent, Path(self.technical_spec_dir))

    def test_creates_destination_folders_that_do_not_yet_exist(self):
        self.assertFalse(os.path.isdir(self.business_ask_dir))
        self.assertFalse(os.path.isdir(self.technical_spec_dir))
        deliver_documents(
            "interview-1234", _doc("ask"), _doc("spec"),
            self.business_ask_dir, self.technical_spec_dir,
        )
        self.assertTrue(os.path.isdir(self.business_ask_dir))
        self.assertTrue(os.path.isdir(self.technical_spec_dir))

    def test_two_deliveries_never_collide(self):
        first = deliver_documents(
            "interview-aaaa", _doc("ask one"), _doc("spec one"),
            self.business_ask_dir, self.technical_spec_dir,
        )
        second = deliver_documents(
            "interview-bbbb", _doc("ask two"), _doc("spec two"),
            self.business_ask_dir, self.technical_spec_dir,
        )
        self.assertNotEqual(first["business_ask"], second["business_ask"])
        self.assertNotEqual(first["technical_spec"], second["technical_spec"])
        # Both files from both deliveries still exist and hold their own content, not each
        # other's - a collision would silently overwrite an earlier interview's documents.
        self.assertEqual(_first_paragraph_text(first["business_ask"]), "ask one")
        self.assertEqual(_first_paragraph_text(second["business_ask"]), "ask two")

    def test_filenames_carry_the_interview_id_for_traceability(self):
        interview_id = "abcdef12-3456-7890-abcd-ef1234567890"
        delivered = deliver_documents(
            interview_id, _doc("ask"), _doc("spec"),
            self.business_ask_dir, self.technical_spec_dir,
        )
        # A short, recognisable prefix of the id (the first 8 characters, matching a real
        # uuid4's first hyphen-delimited group), not the whole UUID, so the filename stays
        # readable while still tracing back to a specific interview.
        short_id = interview_id[:8]
        self.assertIn(short_id, delivered["business_ask"].name)
        self.assertIn(short_id, delivered["technical_spec"].name)
        self.assertIn("business-ask", delivered["business_ask"].name)
        self.assertIn("technical-spec", delivered["technical_spec"].name)
        self.assertTrue(delivered["business_ask"].name.endswith(".docx"))
        self.assertTrue(delivered["technical_spec"].name.endswith(".docx"))


if __name__ == "__main__":
    unittest.main()
