from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from quicknotes.core import NoteService


STATIC_DIR = Path(__file__).resolve().parent.parent / "web"


def json_response(handler: BaseHTTPRequestHandler, payload: dict | list, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def text_response(
    handler: BaseHTTPRequestHandler,
    body: str,
    status: int = 200,
    content_type: str = "text/plain; charset=utf-8",
) -> None:
    raw = body.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def load_static(name: str) -> bytes:
    return (STATIC_DIR / name).read_bytes()


class QuickNotesWebHandler(BaseHTTPRequestHandler):
    service = NoteService()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_static("index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/styles.css":
            self._serve_static("styles.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._serve_static("app.js", "application/javascript; charset=utf-8")
            return
        if parsed.path == "/api/notes":
            params = parse_qs(parsed.query)
            notes = self.service.list_notes(
                include_archived=params.get("all", ["false"])[0].lower() == "true",
                tag=params.get("tag", [None])[0],
                sort_by=params.get("sort", ["updated"])[0],
            )
            json_response(self, [note.to_dict() for note in notes])
            return
        if parsed.path == "/api/stats":
            json_response(self, self.service.stats())
            return
        if parsed.path == "/api/search":
            params = parse_qs(parsed.query)
            keyword = params.get("q", [""])[0]
            try:
                notes = self.service.search_notes(
                    keyword=keyword,
                    include_archived=params.get("all", ["false"])[0].lower() == "true",
                    tag=params.get("tag", [None])[0],
                )
            except ValueError as exc:
                json_response(self, {"error": str(exc)}, status=400)
                return
            json_response(self, [note.to_dict() for note in notes])
            return
        text_response(self, "Not Found", status=404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/notes":
            payload = self._read_json()
            if payload is None:
                return
            try:
                note = self.service.add_note(
                    text=payload.get("text", ""),
                    tags=payload.get("tags", []),
                    pinned=bool(payload.get("pinned", False)),
                )
            except ValueError as exc:
                json_response(self, {"error": str(exc)}, status=400)
                return
            json_response(self, note.to_dict(), status=201)
            return

        if parsed.path.startswith("/api/notes/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) != 4:
                text_response(self, "Not Found", status=404)
                return
            try:
                note_id = int(parts[2])
            except ValueError:
                json_response(self, {"error": "invalid note id"}, status=400)
                return
            action = parts[3]
            if action == "archive":
                note = self.service.archive_note(note_id)
            elif action == "restore":
                note = self.service.restore_note(note_id)
            elif action == "pin":
                note = self.service.pin_note(note_id)
            elif action == "unpin":
                note = self.service.unpin_note(note_id)
            else:
                text_response(self, "Not Found", status=404)
                return
            if note is None:
                json_response(self, {"error": "note not found"}, status=404)
                return
            json_response(self, note.to_dict())
            return

        text_response(self, "Not Found", status=404)

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/notes/"):
            text_response(self, "Not Found", status=404)
            return
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 3:
            text_response(self, "Not Found", status=404)
            return
        try:
            note_id = int(parts[2])
        except ValueError:
            json_response(self, {"error": "invalid note id"}, status=400)
            return
        payload = self._read_json()
        if payload is None:
            return
        try:
            note = self.service.update_note(
                note_id=note_id,
                text=payload.get("text"),
                tags=payload.get("tags"),
            )
        except ValueError as exc:
            json_response(self, {"error": str(exc)}, status=400)
            return
        if note is None:
            json_response(self, {"error": "note not found"}, status=404)
            return
        json_response(self, note.to_dict())

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/notes/"):
            text_response(self, "Not Found", status=404)
            return
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 3:
            text_response(self, "Not Found", status=404)
            return
        try:
            note_id = int(parts[2])
        except ValueError:
            json_response(self, {"error": "invalid note id"}, status=400)
            return
        removed = self.service.remove_note(note_id)
        if not removed:
            json_response(self, {"error": "note not found"}, status=404)
            return
        json_response(self, {"ok": True})

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _serve_static(self, filename: str, content_type: str) -> None:
        try:
            body = load_static(filename)
        except FileNotFoundError:
            text_response(self, "Not Found", status=404)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            json_response(self, {"error": "invalid content length"}, status=400)
            return None
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            json_response(self, {"error": "invalid json body"}, status=400)
            return None
        if not isinstance(payload, dict):
            json_response(self, {"error": "json body must be an object"}, status=400)
            return None
        return payload


def run_web_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), QuickNotesWebHandler)
    print(f"QuickNotes Web running at http://{host}:{port}")
    server.serve_forever()
