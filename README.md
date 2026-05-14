# QuickNotes CLI

QuickNotes CLI is a lightweight open-source note manager written in Python with both a command-line interface and a local web UI.

It lets you:

- add timestamped notes
- edit saved notes
- list saved notes with sorting and tag filters
- search notes by keyword
- archive and restore notes
- pin important notes
- remove notes by ID
- export notes to JSON or text

## Features

- zero third-party dependencies
- stores data in a local JSON file
- tags, pinning, archiving, and note statistics
- modular code structure with service, CLI, and web layers
- works on Windows, macOS, and Linux

## Web Interface

Start the local web app with:

```bash
py app.py web
```

Then open:

```text
http://127.0.0.1:8000
```

The web interface supports:

- creating notes
- editing text and tags inline
- pinning and archiving from the browser
- searching and filtering
- viewing live statistics

## Usage

Run commands with:

```bash
py app.py <command> [arguments]
```

Examples:

```bash
py app.py add "Buy milk" --tags personal,errands --pin
py app.py add "Draft project README" --tags work,docs
py app.py list --sort updated
py app.py search README --tag docs
py app.py edit 2 "Draft polished project README" --tags work,docs,priority
py app.py archive 1
py app.py restore 1
py app.py stats
py app.py export notes-export.txt --active-only
py app.py web --port 8080
py app.py remove 1
```

## Commands

- `add <text> [--tags a,b] [--pin]`: create a note
- `list [--all] [--tag tag] [--sort created|updated]`: show notes
- `search <keyword> [--all] [--tag tag]`: find matching notes
- `edit <id> <text> [--tags a,b]`: update a note
- `archive <id>`: archive a note
- `restore <id>`: restore an archived note
- `pin <id>`: pin a note
- `unpin <id>`: unpin a note
- `stats`: show aggregate note statistics
- `export <path> [--active-only]`: export notes to `.json` or `.txt`
- `web [--host 127.0.0.1] [--port 8000]`: run the local web interface
- `remove <id>`: delete a note by numeric ID

## Data file

Notes are stored in `notes.json` in the project directory by default.

You can override the path with:

```bash
set QUICKNOTES_DB=custom-notes.json
py app.py list
```

## Testing

```bash
py -m unittest discover -s tests
```

## License

MIT
