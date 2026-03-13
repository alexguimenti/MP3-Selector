# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Windows-only Python tool that selects a random subset of MP3 files from a music library, respecting per-artist limits and total size caps. Outputs either copied files or `.lnk` shortcuts. Includes a tkinter GUI and a CLI version.

## Running

```bash
# GUI (recommended)
python mp3_selector_gui.py

# CLI (hardcoded config at top of file)
python mp3_selector.py

# Create .m3u playlist from shortcuts
python create_playlist.py

# Build Windows executable
pyinstaller mp3_selector_gui.spec
```

## Dependencies

```bash
pip install mutagen pywin32
```

tkinter is included with standard Python on Windows. `pywin32` provides `win32com.client` for `.lnk` shortcut creation/resolution.

## Architecture

Three standalone scripts, no shared module:

- **`mp3_selector.py`** — CLI entry point. Runs top-level on import (no `if __name__` guard). Config is hardcoded at the top of the file. Uses `unicodedata` normalization for artist matching. Selection algorithm: artists with >=6 songs get `songs_per_artist` random picks (Group 1), artists with <=5 songs contribute 10% of Group 1's count (Group 2).
- **`mp3_selector_gui.py`** — tkinter GUI. Duplicates most logic from `mp3_selector.py` with GUI-specific adaptations (progress bars, stop flag, `root.update_idletasks()`). Runs the main process in a separate thread via `threading.Thread`. Uses `IntVar`/`StringVar` for all config. The GUI version's `select_songs_based_on_artist_count` takes first N songs (no randomization), unlike the CLI version which uses `random.sample`.
- **`create_playlist.py`** — Resolves `.lnk` files in a hardcoded folder to build an `.m3u` playlist.

## Key Implementation Details

- **Cache system**: JSON files stored in `cache/` at project root, keyed by `abs(hash(folder)) % 10^8`. Cache invalidation checks folder modification time and verifies all file paths still exist.
- **Parallel processing**: `ThreadPoolExecutor` for both metadata extraction and file copying. GUI version defaults to 20 workers for listing, CLI to 4.
- **Song data structure**: `{"path": str, "artist": str, "title": str}` — artist is always lowercased. CLI version also runs `normalize_text()` (strips accents via NFKD).
- **GUI threading**: Main process runs in a background thread; GUI updates via `root.update_idletasks()`. Global `stop_flag` enables cancellation.
- **Shortcut creation**: CLI uses `win32com.client.Dispatch("WScript.Shell")` per file; GUI uses `os.symlink` instead — these behave differently on Windows.

## Known Code Duplication

`mp3_selector.py` and `mp3_selector_gui.py` share duplicated logic for cache management, file listing, grouping, selection, and copying. The implementations diverge in subtle ways (randomization, normalization, shortcut method, worker counts).
