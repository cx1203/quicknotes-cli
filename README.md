# QuickNotes CLI

QuickNotes CLI is a tiny open-source command-line note manager written in Python.

It lets you:

- add timestamped notes
- list saved notes
- search notes by keyword
- remove notes by ID

## Features

- zero third-party dependencies
- stores data in a local JSON file
- works on Windows, macOS, and Linux

## Usage

Run commands with:

```bash
py app.py <command> [arguments]
```

Examples:

```bash
py app.py add "Buy milk"
py app.py add "Draft project README"
py app.py list
py app.py search README
py app.py remove 1
```

## Commands

- `add <text>`: create a note
- `list`: show all notes
- `search <keyword>`: find matching notes
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
