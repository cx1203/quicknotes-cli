import json
import os
import unittest
from pathlib import Path


class QuickNotesCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(__file__).resolve().parent / "tmp"
        self.temp_dir.mkdir(exist_ok=True)
        self.db_path = self.temp_dir / "notes.json"
        if self.db_path.exists():
            self.db_path.unlink()
        os.environ["QUICKNOTES_DB"] = str(self.db_path)

        import importlib
        import app

        self.app = importlib.reload(app)

    def tearDown(self) -> None:
        os.environ.pop("QUICKNOTES_DB", None)
        if self.db_path.exists():
            self.db_path.unlink()

    def test_add_note_persists_data(self) -> None:
        note = self.app.add_note("Write tests")

        self.assertEqual(note.id, 1)
        saved = json.loads(self.db_path.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["text"], "Write tests")

    def test_search_is_case_insensitive(self) -> None:
        self.app.add_note("Draft README")
        self.app.add_note("Buy milk")

        matches = self.app.search_notes("readme")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].text, "Draft README")

    def test_remove_note_deletes_matching_id(self) -> None:
        self.app.add_note("First")
        self.app.add_note("Second")

        removed = self.app.remove_note(1)
        notes = self.app.list_notes()

        self.assertTrue(removed)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].id, 2)


if __name__ == "__main__":
    unittest.main()
