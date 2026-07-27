"""Local backup of the SQLite database.

Copies backend/cubebot.db into backend/backups/ with a timestamped
filename, then prunes old backups beyond a retention count.

This is a plain `shutil.copy2` file copy, not SQLite's online backup
API (`sqlite3.Connection.backup()`). That's fine for this project:
single-admin, low-traffic, no heavy concurrent writes while the copy
runs. A busier production DB under concurrent write load should
switch to the `sqlite3` backup API instead, which safely copies a
live database without risking a torn/corrupt snapshot.

Usage:
  .venv/Scripts/python.exe scripts/backup_db.py
  .venv/Scripts/python.exe scripts/backup_db.py --keep 14

Retention count can also be set via the BACKUP_RETENTION_COUNT env
var; the --keep flag takes precedence when both are given.
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "cubebot.db"
BACKUPS_DIR = BACKEND_DIR / "backups"

DEFAULT_RETENTION_COUNT = 30
FILENAME_PREFIX = "cubebot_"
FILENAME_SUFFIX = ".db"


def backup_filename(now: datetime) -> str:
    return f"{FILENAME_PREFIX}{now.strftime('%Y%m%d_%H%M%S')}{FILENAME_SUFFIX}"


def select_backups_to_prune(filenames: list[str], keep: int) -> list[str]:
    """Given existing backup filenames and a retention count, return the
    filenames that should be deleted (the oldest ones beyond `keep`).

    Filenames are assumed to sort correctly by timestamp lexicographically,
    i.e. named like cubebot_YYYYMMDD_HHMMSS.db.
    """
    if keep < 0:
        keep = 0

    ordered = sorted(filenames)

    if len(ordered) <= keep:
        return []

    return ordered[: len(ordered) - keep]


def main():
    parser = argparse.ArgumentParser(description="Back up cubebot.db to backend/backups/.")
    parser.add_argument(
        "--keep",
        type=int,
        default=None,
        help="Number of most recent backups to retain (default 30, or BACKUP_RETENTION_COUNT env var).",
    )
    args = parser.parse_args()

    if args.keep is not None:
        keep = args.keep
    else:
        keep = int(os.environ.get("BACKUP_RETENTION_COUNT", DEFAULT_RETENTION_COUNT))

    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return 1

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    filename = backup_filename(datetime.now())
    destination = BACKUPS_DIR / filename

    shutil.copy2(DB_PATH, destination)
    print(f"Backed up {DB_PATH} -> {destination}")

    existing_names = [p.name for p in BACKUPS_DIR.glob(f"{FILENAME_PREFIX}*{FILENAME_SUFFIX}")]
    to_prune = select_backups_to_prune(existing_names, keep)

    for name in to_prune:
        (BACKUPS_DIR / name).unlink()
        print(f"Pruned old backup: {name}")

    remaining = len(existing_names) - len(to_prune)
    print(f"Retention: keeping {remaining} of {len(existing_names)} backup(s) (keep={keep}).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
