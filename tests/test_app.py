import json
import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock


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
        import quicknotes.cli
        import quicknotes.core
        import quicknotes.web

        self.cli = importlib.reload(quicknotes.cli)
        self.core = importlib.reload(quicknotes.core)
        self.web = importlib.reload(quicknotes.web)
        self.service = self.core.NoteService()

    def tearDown(self) -> None:
        os.environ.pop("QUICKNOTES_DB", None)
        if self.db_path.exists():
            self.db_path.unlink()

    def test_add_note_persists_data(self) -> None:
        note = self.service.add_note("Write tests", tags=["dev", "testing"], pinned=True)

        self.assertEqual(note.id, 1)
        saved = json.loads(self.db_path.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["text"], "Write tests")
        self.assertEqual(saved[0]["tags"], ["dev", "testing"])
        self.assertTrue(saved[0]["pinned"])

    def test_search_is_case_insensitive(self) -> None:
        self.service.add_note("Draft README", tags=["docs"])
        self.service.add_note("Buy milk", tags=["personal"])

        matches = self.service.search_notes("readme")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].text, "Draft README")

    def test_remove_note_deletes_matching_id(self) -> None:
        self.service.add_note("First")
        self.service.add_note("Second")

        removed = self.service.remove_note(1)
        notes = self.service.list_notes()

        self.assertTrue(removed)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].id, 2)

    def test_archive_hides_note_from_default_list(self) -> None:
        self.service.add_note("Visible")
        self.service.add_note("Archive me")

        self.service.archive_note(2)
        visible_notes = self.service.list_notes()
        all_notes = self.service.list_notes(include_archived=True)

        self.assertEqual([note.id for note in visible_notes], [1])
        self.assertEqual(len(all_notes), 2)

    def test_pin_places_note_first_in_listing(self) -> None:
        self.service.add_note("Second note")
        self.service.add_note("Important note")

        self.service.pin_note(2)
        notes = self.service.list_notes()

        self.assertEqual(notes[0].id, 2)
        self.assertTrue(notes[0].pinned)

    def test_update_note_replaces_text_and_tags(self) -> None:
        self.service.add_note("Old text", tags=["draft"])

        updated = self.service.update_note(1, text="New text", tags=["final", "docs"])

        self.assertIsNotNone(updated)
        self.assertEqual(updated.text, "New text")
        self.assertEqual(updated.tags, ["docs", "final"])

    def test_stats_counts_active_archived_and_pinned_notes(self) -> None:
        self.service.add_note("One", tags=["alpha"])
        self.service.add_note("Two", pinned=True)
        self.service.archive_note(1)

        stats = self.service.stats()

        self.assertEqual(
            stats,
            {"total": 2, "active": 1, "archived": 1, "pinned": 1, "tagged": 1},
        )

    def test_export_writes_text_snapshot(self) -> None:
        self.service.add_note("Ship release", tags=["work"], pinned=True)
        export_path = self.temp_dir / "notes-export.txt"

        self.service.export_notes(export_path)

        content = export_path.read_text(encoding="utf-8")
        self.assertIn("Ship release", content)
        self.assertIn("pinned", content)

    def test_cli_stats_command_prints_summary(self) -> None:
        self.service.add_note("First", tags=["x"])
        self.service.add_note("Second", pinned=True)
        buffer = StringIO()

        with redirect_stdout(buffer):
            exit_code = self.cli.main(["stats"])

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("QuickNotes stats", output)
        self.assertIn("total: 2", output)

    def test_cli_edit_command_updates_note(self) -> None:
        self.service.add_note("Initial")
        buffer = StringIO()

        with redirect_stdout(buffer):
            exit_code = self.cli.main(["edit", "1", "Updated", "copy", "--tags", "docs,final"])
        notes = self.service.list_notes()

        self.assertEqual(exit_code, 0)
        self.assertEqual(notes[0].text, "Updated copy")
        self.assertEqual(notes[0].tags, ["docs", "final"])

    def test_cli_web_command_invokes_server(self) -> None:
        with mock.patch("quicknotes.cli.run_web_server") as mocked_server:
            exit_code = self.cli.main(["web", "--host", "0.0.0.0", "--port", "9000"])

        self.assertEqual(exit_code, 0)
        mocked_server.assert_called_once_with(host="0.0.0.0", port=9000)

    def test_web_handler_exposes_stats_api(self) -> None:
        self.service.add_note("Alpha", tags=["work"])

        handler = self.web.QuickNotesWebHandler
        handler.service = self.service

        class DummySocket:
            def makefile(self, *args, **kwargs):
                return None

        from io import BytesIO

        request_bytes = b"GET /api/stats HTTP/1.1\r\nHost: localhost\r\n\r\n"
        response_stream = BytesIO()
        request_stream = BytesIO(request_bytes)

        request_handler = handler.__new__(handler)
        request_handler.rfile = request_stream
        request_handler.wfile = response_stream
        request_handler.raw_requestline = request_stream.readline()
        request_handler.error_code = request_handler.error_message = None
        request_handler.client_address = ("127.0.0.1", 12345)
        request_handler.server = None
        request_handler.connection = DummySocket()

        self.assertTrue(request_handler.parse_request())
        request_handler.do_GET()

        body = response_stream.getvalue().split(b"\r\n\r\n", 1)[1]
        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["total"], 1)


if __name__ == "__main__":
    unittest.main()
