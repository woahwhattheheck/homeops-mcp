"""Inspect, export, back up or restore an existing HomeOps SQLite journal."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from .homeops import HomeOpsLedger, ValidationError
from .storage import SQLiteHomeOpsLedger


def _new_destination(value: str) -> Path:
    path = Path(value)
    if path.exists() or path.is_symlink():
        raise ValidationError("output must be a new path; existing destinations are preserved")
    if not path.parent.is_dir():
        raise ValidationError("output parent directory must already exist")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "export", "backup", "restore"):
        command = commands.add_parser(name)
        command.add_argument("database", help="existing SQLite journal or backup")
        if name != "inspect":
            command.add_argument("--output", required=True, help="new destination path")
    args = parser.parse_args(argv)
    try:
        destination = _new_destination(args.output) if args.command != "inspect" else None
        ledger = SQLiteHomeOpsLedger(args.database, create=False)
        if args.command == "inspect":
            result = ledger.inspect()
        elif args.command == "export":
            # Derive every exported fact from this single retained event sequence.
            # Separate reads of live snapshot/inspect could span another commit.
            events = ledger.export_events()
            replay = HomeOpsLedger.replay(events)
            snapshot = replay.snapshot()
            result = {
                "schema": "homeops-relay-event-export/v1",
                "retry_operations_included": False,
                "restore_supported": False,
                "event_count": len(events),
                "receipt": replay.receipt,
                "snapshot_digest": snapshot["snapshot_digest"],
                "events": events,
                "snapshot": snapshot,
            }
            encoded = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2,
                                  allow_nan=False) + "\n").encode("utf-8")
            with destination.open("xb") as handle:
                handle.write(encoded)
            result = {key: value for key, value in result.items()
                      if key not in {"events", "snapshot"}}
            result["destination"] = str(destination)
        else:
            # A restore is a validated SQLite backup into a fresh destination.
            # Event-only export cannot preserve operation IDs or retry responses.
            result = ledger.backup(destination)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
    except (ValidationError, OSError, sqlite3.Error, ValueError) as exc:
        print(f"homeops journal: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
