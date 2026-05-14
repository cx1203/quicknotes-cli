from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Note:
    id: int
    text: str
    created_at: str
    updated_at: str
    tags: list[str] = field(default_factory=list)
    pinned: bool = False
    archived: bool = False


class NoteStore:
    def __init__(self, db_path: Path | None = None) -> None:
        env_path = os.environ.get("QUICKNOTES_DB", "notes.json")
        self.db_path = db_path or Path(env_path)

    def load_notes(self) -> list[Note]:
        if not self.db_path.exists():
            return []
        data = json.loads(self.db_path.read_text(encoding="utf-8"))
        return [Note(**self._normalize_note(item)) for item in data]

    def save_notes(self, notes: list[Note]) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = [asdict(note) for note in notes]
        self.db_path.write_text(
            json.dumps(serialized, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _normalize_note(self, item: dict) -> dict:
        created_at = item.get("created_at", utc_now_iso())
        return {
            "id": item["id"],
            "text": item["text"],
            "created_at": created_at,
            "updated_at": item.get("updated_at", created_at),
            "tags": sorted(set(item.get("tags", []))),
            "pinned": item.get("pinned", False),
            "archived": item.get("archived", False),
        }


class NoteService:
    def __init__(self, store: NoteStore | None = None) -> None:
        self.store = store or NoteStore()

    def add_note(
        self,
        text: str,
        tags: list[str] | None = None,
        pinned: bool = False,
    ) -> Note:
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("note text is required")

        notes = self.store.load_notes()
        timestamp = utc_now_iso()
        note = Note(
            id=self._next_id(notes),
            text=cleaned_text,
            created_at=timestamp,
            updated_at=timestamp,
            tags=self._normalize_tags(tags or []),
            pinned=pinned,
        )
        notes.append(note)
        self.store.save_notes(notes)
        return note

    def list_notes(
        self,
        include_archived: bool = False,
        tag: str | None = None,
        sort_by: str = "created",
    ) -> list[Note]:
        notes = self.store.load_notes()
        filtered = self._filter_notes(notes, include_archived=include_archived, tag=tag)
        return self._sort_notes(filtered, sort_by)

    def search_notes(
        self,
        keyword: str,
        include_archived: bool = False,
        tag: str | None = None,
    ) -> list[Note]:
        lowered = keyword.strip().lower()
        if not lowered:
            raise ValueError("keyword is required")

        notes = self._filter_notes(
            self.store.load_notes(),
            include_archived=include_archived,
            tag=tag,
        )
        matched = [
            note
            for note in notes
            if lowered in note.text.lower()
            or any(lowered in note_tag.lower() for note_tag in note.tags)
        ]
        return self._sort_notes(matched, "updated")

    def update_note(
        self,
        note_id: int,
        text: str | None = None,
        tags: list[str] | None = None,
    ) -> Note | None:
        notes = self.store.load_notes()
        note = self._find_note(notes, note_id)
        if note is None:
            return None

        changed = False
        if text is not None:
            cleaned_text = text.strip()
            if not cleaned_text:
                raise ValueError("note text is required")
            note.text = cleaned_text
            changed = True
        if tags is not None:
            note.tags = self._normalize_tags(tags)
            changed = True

        if changed:
            note.updated_at = utc_now_iso()
            self.store.save_notes(notes)
        return note

    def remove_note(self, note_id: int) -> bool:
        notes = self.store.load_notes()
        remaining = [note for note in notes if note.id != note_id]
        if len(remaining) == len(notes):
            return False
        self.store.save_notes(remaining)
        return True

    def archive_note(self, note_id: int) -> Note | None:
        return self._set_archived(note_id, True)

    def restore_note(self, note_id: int) -> Note | None:
        return self._set_archived(note_id, False)

    def pin_note(self, note_id: int) -> Note | None:
        return self._set_pinned(note_id, True)

    def unpin_note(self, note_id: int) -> Note | None:
        return self._set_pinned(note_id, False)

    def export_notes(self, output_path: Path, include_archived: bool = True) -> Path:
        notes = self.list_notes(include_archived=include_archived, sort_by="updated")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix.lower() == ".txt":
            lines: list[str] = []
            for note in notes:
                tag_text = ", ".join(note.tags) if note.tags else "none"
                status = []
                if note.pinned:
                    status.append("pinned")
                if note.archived:
                    status.append("archived")
                status_text = ", ".join(status) if status else "active"
                lines.append(
                    f"[{note.id}] {note.text}\n"
                    f"  tags: {tag_text}\n"
                    f"  status: {status_text}\n"
                    f"  updated: {note.updated_at}"
                )
            output_path.write_text("\n\n".join(lines), encoding="utf-8")
            return output_path

        output_path.write_text(
            json.dumps([asdict(note) for note in notes], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_path

    def stats(self) -> dict[str, int]:
        notes = self.store.load_notes()
        archived = sum(1 for note in notes if note.archived)
        pinned = sum(1 for note in notes if note.pinned)
        active = len(notes) - archived
        tagged = sum(1 for note in notes if note.tags)
        return {
            "total": len(notes),
            "active": active,
            "archived": archived,
            "pinned": pinned,
            "tagged": tagged,
        }

    def _set_archived(self, note_id: int, archived: bool) -> Note | None:
        notes = self.store.load_notes()
        note = self._find_note(notes, note_id)
        if note is None:
            return None
        note.archived = archived
        note.updated_at = utc_now_iso()
        self.store.save_notes(notes)
        return note

    def _set_pinned(self, note_id: int, pinned: bool) -> Note | None:
        notes = self.store.load_notes()
        note = self._find_note(notes, note_id)
        if note is None:
            return None
        note.pinned = pinned
        note.updated_at = utc_now_iso()
        self.store.save_notes(notes)
        return note

    def _find_note(self, notes: list[Note], note_id: int) -> Note | None:
        for note in notes:
            if note.id == note_id:
                return note
        return None

    def _filter_notes(
        self,
        notes: list[Note],
        include_archived: bool,
        tag: str | None,
    ) -> list[Note]:
        filtered = notes
        if not include_archived:
            filtered = [note for note in filtered if not note.archived]
        if tag:
            lowered_tag = tag.lower()
            filtered = [
                note
                for note in filtered
                if any(existing.lower() == lowered_tag for existing in note.tags)
            ]
        return filtered

    def _sort_notes(self, notes: list[Note], sort_by: str) -> list[Note]:
        if sort_by == "updated":
            key_func = lambda note: note.updated_at
        else:
            key_func = lambda note: note.created_at

        return sorted(notes, key=lambda note: (not note.pinned, key_func(note), note.id))

    def _next_id(self, notes: list[Note]) -> int:
        return max((note.id for note in notes), default=0) + 1

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        normalized = {tag.strip().lower() for tag in tags if tag.strip()}
        return sorted(normalized)
