# ─────────────────────────────────────────────────────────
# watcher.py
# Runs in the background and auto-ingests any new or
# modified file in your notes folder.
#
# You write a note in Obsidian → save it → it's immediately
# searchable in the memory engine. You do nothing extra.
#
# Usage:
#   python watcher.py                    ← watch WATCH_FOLDER
#   python watcher.py /path/to/folder    ← watch a custom folder
#
# Keep this running in a terminal in the background.
# ─────────────────────────────────────────────────────────

import sys
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config import WATCH_FOLDER, SUPPORTED_EXTENSIONS
from ingest import ingest_file, get_collection


# ── File Event Handler ────────────────────────────────────

class MemoryIngester(FileSystemEventHandler):
    """
    Responds to file system events in the watched folder.

    Handles:
      on_created  — new file dropped in folder
      on_modified — existing file saved/changed

    Ignores:
      Directories, temp files, unsupported file types,
      and rapid duplicate events (debouncing).
    """

    def __init__(self):
        self.collection = get_collection()
        # Track recently processed files to avoid double-firing
        # (many editors save twice in quick succession)
        self._recently_processed = {}

    def should_process(self, path: str) -> bool:
        """
        Check if this file should be processed.
        Filters out temp files and unsupported types.
        Also debounces — ignores the same file within 2 seconds.
        """
        p = Path(path)

        # Skip directories
        if p.is_dir():
            return False

        # Skip hidden files and editor temp files
        # (e.g. .obsidian, .DS_Store, ~file.tmp, file.swp)
        if p.name.startswith(".") or p.name.startswith("~"):
            return False
        if p.suffix in [".tmp", ".swp", ".swx", ".lock"]:
            return False

        # Only process supported file types
        if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return False

        # Debounce: skip if we processed this file in the last 2 seconds
        now = time.time()
        last = self._recently_processed.get(path, 0)
        if now - last < 2.0:
            return False

        self._recently_processed[path] = now
        return True

    def on_created(self, event):
        """Called when a new file is created."""
        if not event.is_directory and self.should_process(event.src_path):
            print(f"\n📝 New file: {Path(event.src_path).name}")
            ingest_file(event.src_path, collection=self.collection)

    def on_modified(self, event):
        """Called when a file is modified."""
        if not event.is_directory and self.should_process(event.src_path):
            print(f"\n✏️  Modified: {Path(event.src_path).name}")
            ingest_file(event.src_path, collection=self.collection)

    def on_moved(self, event):
        """Called when a file is renamed or moved."""
        if not event.is_directory and self.should_process(event.dest_path):
            print(f"\n↔️  Moved/renamed: {Path(event.dest_path).name}")
            ingest_file(event.dest_path, collection=self.collection)


# ── Main ──────────────────────────────────────────────────

def start_watching(folder_path: str):
    """Start watching a folder for file changes."""
    folder = Path(folder_path)

    if not folder.exists():
        print(f"✗ Folder not found: {folder_path}")
        print(f"  Create the folder first, then run watcher.py again.")
        print(f"  Or update WATCH_FOLDER in config.py")
        sys.exit(1)

    print(f"👁️  Watching: {folder.resolve()}")
    print(f"   Supported types: {', '.join(SUPPORTED_EXTENSIONS)}")
    print(f"   Press Ctrl+C to stop\n")

    handler = MemoryIngester()
    observer = Observer()
    observer.schedule(handler, str(folder), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping watcher...")
        observer.stop()

    observer.join()
    print("Watcher stopped.")


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else WATCH_FOLDER
    start_watching(folder)
