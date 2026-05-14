from __future__ import annotations

import argparse
from pathlib import Path

from quicknotes.core import Note, NoteService


def parse_tags(raw_tags: str | None) -> list[str]:
    if not raw_tags:
        return []
    return [tag.strip() for tag in raw_tags.split(",") if tag.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quicknotes",
        description="Manage local notes from the command line.",
    )
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Create a note")
    add_parser.add_argument("text", nargs="+", help="Note text")
    add_parser.add_argument("--tags", help="Comma-separated tags")
    add_parser.add_argument("--pin", action="store_true", help="Pin the note")

    list_parser = subparsers.add_parser("list", help="List notes")
    list_parser.add_argument("--all", action="store_true", help="Include archived notes")
    list_parser.add_argument("--tag", help="Filter by a single tag")
    list_parser.add_argument(
        "--sort",
        choices=["created", "updated"],
        default="created",
        help="Sort notes by timestamp",
    )

    search_parser = subparsers.add_parser("search", help="Search notes")
    search_parser.add_argument("keyword", help="Keyword to search")
    search_parser.add_argument("--all", action="store_true", help="Include archived notes")
    search_parser.add_argument("--tag", help="Filter by a single tag")

    edit_parser = subparsers.add_parser("edit", help="Edit a note")
    edit_parser.add_argument("id", type=int, help="Numeric note ID")
    edit_parser.add_argument("text", nargs="+", help="Updated note text")
    edit_parser.add_argument("--tags", help="Replace tags with a comma-separated list")

    remove_parser = subparsers.add_parser("remove", help="Delete a note")
    remove_parser.add_argument("id", type=int, help="Numeric note ID")

    archive_parser = subparsers.add_parser("archive", help="Archive a note")
    archive_parser.add_argument("id", type=int, help="Numeric note ID")

    restore_parser = subparsers.add_parser("restore", help="Restore an archived note")
    restore_parser.add_argument("id", type=int, help="Numeric note ID")

    pin_parser = subparsers.add_parser("pin", help="Pin a note")
    pin_parser.add_argument("id", type=int, help="Numeric note ID")

    unpin_parser = subparsers.add_parser("unpin", help="Unpin a note")
    unpin_parser.add_argument("id", type=int, help="Numeric note ID")

    stats_parser = subparsers.add_parser("stats", help="Show note statistics")
    stats_parser.add_argument("--all", action="store_true", help="Reserved for future use")

    export_parser = subparsers.add_parser("export", help="Export notes to a file")
    export_parser.add_argument("path", help="Output path ending in .json or .txt")
    export_parser.add_argument("--active-only", action="store_true", help="Export active notes only")

    return parser


def format_note(note: Note) -> str:
    tags = f" tags={','.join(note.tags)}" if note.tags else ""
    flags = []
    if note.pinned:
        flags.append("pinned")
    if note.archived:
        flags.append("archived")
    status = f" [{' | '.join(flags)}]" if flags else ""
    return f"[{note.id}] {note.text}{tags}{status}\n  created={note.created_at} updated={note.updated_at}"


def print_notes(notes: list[Note]) -> int:
    if not notes:
        print("No notes found.")
        return 0
    for note in notes:
        print(format_note(note))
    return 0


def print_stats(stats: dict[str, int]) -> int:
    print("QuickNotes stats")
    print(f"  total: {stats['total']}")
    print(f"  active: {stats['active']}")
    print(f"  archived: {stats['archived']}")
    print(f"  pinned: {stats['pinned']}")
    print(f"  tagged: {stats['tagged']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    service = NoteService()

    try:
        if args.command == "add":
            note = service.add_note(
                text=" ".join(args.text),
                tags=parse_tags(args.tags),
                pinned=args.pin,
            )
            print(f"Added note #{note.id}.")
            return 0

        if args.command == "list":
            notes = service.list_notes(
                include_archived=args.all,
                tag=args.tag,
                sort_by=args.sort,
            )
            return print_notes(notes)

        if args.command == "search":
            notes = service.search_notes(
                keyword=args.keyword,
                include_archived=args.all,
                tag=args.tag,
            )
            return print_notes(notes)

        if args.command == "edit":
            note = service.update_note(
                note_id=args.id,
                text=" ".join(args.text),
                tags=parse_tags(args.tags) if args.tags is not None else None,
            )
            if note is None:
                print(f"Note #{args.id} not found.")
                return 1
            print(f"Updated note #{note.id}.")
            return 0

        if args.command == "remove":
            if service.remove_note(args.id):
                print(f"Removed note #{args.id}.")
                return 0
            print(f"Note #{args.id} not found.")
            return 1

        if args.command == "archive":
            note = service.archive_note(args.id)
            if note is None:
                print(f"Note #{args.id} not found.")
                return 1
            print(f"Archived note #{note.id}.")
            return 0

        if args.command == "restore":
            note = service.restore_note(args.id)
            if note is None:
                print(f"Note #{args.id} not found.")
                return 1
            print(f"Restored note #{note.id}.")
            return 0

        if args.command == "pin":
            note = service.pin_note(args.id)
            if note is None:
                print(f"Note #{args.id} not found.")
                return 1
            print(f"Pinned note #{note.id}.")
            return 0

        if args.command == "unpin":
            note = service.unpin_note(args.id)
            if note is None:
                print(f"Note #{args.id} not found.")
                return 1
            print(f"Unpinned note #{note.id}.")
            return 0

        if args.command == "stats":
            return print_stats(service.stats())

        if args.command == "export":
            target = Path(args.path)
            exported = service.export_notes(
                output_path=target,
                include_archived=not args.active_only,
            )
            print(f"Exported notes to {exported}.")
            return 0
    except ValueError as exc:
        print(f"Error: {exc}.")
        return 1

    parser.print_help()
    return 1
