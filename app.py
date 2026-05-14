from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(os.environ.get("QUICKNOTES_DB", "notes.json"))


@dataclass
class Note:
    id: int
    text: str
    created_at: str


def load_notes() -> list[Note]:
    if not DB_PATH.exists():
        return []
    data = json.loads(DB_PATH.read_text(encoding="utf-8"))
    return [Note(**item) for item in data]


def save_notes(notes: list[Note]) -> None:
    DB_PATH.write_text(
        json.dumps([asdict(note) for note in notes], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def next_id(notes: list[Note]) -> int:
    return max((note.id for note in notes), default=0) + 1


def add_note(text: str) -> Note:
    notes = load_notes()
    note = Note(
        id=next_id(notes),
        text=text.strip(),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    notes.append(note)
    save_notes(notes)
    return note


def list_notes() -> list[Note]:
    return load_notes()


def search_notes(keyword: str) -> list[Note]:
    lowered = keyword.lower()
    return [note for note in load_notes() if lowered in note.text.lower()]


def remove_note(note_id: int) -> bool:
    notes = load_notes()
    remaining = [note for note in notes if note.id != note_id]
    if len(remaining) == len(notes):
        return False
    save_notes(remaining)
    return True


def print_notes(notes: list[Note]) -> int:
    if not notes:
        print("No notes found.")
        return 0
    for note in notes:
        print(f"[{note.id}] {note.text} ({note.created_at})")
    return 0


def usage() -> int:
    print("Usage:")
    print("  py app.py add <text>")
    print("  py app.py list")
    print("  py app.py search <keyword>")
    print("  py app.py remove <id>")
    return 1


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return usage()

    command = argv[1].lower()

    if command == "add":
        if len(argv) < 3 or not " ".join(argv[2:]).strip():
            print("Error: note text is required.")
            return 1
        note = add_note(" ".join(argv[2:]))
        print(f"Added note #{note.id}.")
        return 0

    if command == "list":
        return print_notes(list_notes())

    if command == "search":
        if len(argv) != 3:
            print("Error: keyword is required.")
            return 1
        return print_notes(search_notes(argv[2]))

    if command == "remove":
        if len(argv) != 3:
            print("Error: numeric note ID is required.")
            return 1
        try:
            note_id = int(argv[2])
        except ValueError:
            print("Error: note ID must be a number.")
            return 1
        if remove_note(note_id):
            print(f"Removed note #{note_id}.")
            return 0
        print(f"Note #{note_id} not found.")
        return 1

    return usage()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
