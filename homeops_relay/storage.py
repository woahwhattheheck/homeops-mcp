"""Optional local SQLite custody for the unchanged HomeOps domain ledger.

This journal detects inconsistent retained state; it does not authenticate a
database or protect it from somebody who can replace all of its contents.
Use a local filesystem with SQLite locking and keep backups with the same care
as the original household evidence. No external action is performed here.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time
from typing import Any

from .homeops import HomeOpsLedger, MAX_EVENTS, ValidationError

SCHEMA = "homeops-relay-storage/v1"
APPLICATION_ID = 0x484F5053
SCHEMA_VERSION = 1
MAX_REQUEST_BYTES = 65_536
MAX_RETAINED_BYTES = 64 * 1024 * 1024
MAX_DATABASE_BYTES = 128 * 1024 * 1024
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 20_000
MAX_ROW_BYTES = 3 * MAX_REQUEST_BYTES
MUTATING_TOOLS = frozenset({
    "homeops.intake_issue", "homeops.record_quote", "homeops.request_action",
    "homeops.record_owner_decision",
})
READ_TOOLS = frozenset({"homeops.propose_plan", "homeops.snapshot"})
_OPERATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_TABLE_SQL = (
    "CREATE TABLE operations (seq INTEGER PRIMARY KEY, "
    "operation_id TEXT NOT NULL UNIQUE, request_json TEXT NOT NULL, "
    "event_json TEXT NOT NULL, response_json TEXT NOT NULL)"
)


class StorageError(ValidationError):
    """Retained storage cannot safely serve the requested operation."""


class OperationConflictError(StorageError):
    """An operation ID was already committed with a different request."""


class UncertainCommitError(StorageError):
    """Commit acknowledgement failed; retry the identical operation ID."""


def _canonical(value: Any) -> str:
    """Validate and detach ordinary finite JSON without coercing key types."""
    seen: set[int] = set()
    nodes = 0

    def visit(obj: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            raise ValidationError("JSON structure exceeds the storage bound")
        if type(obj) is str:
            try:
                obj.encode("utf-8")
            except UnicodeError as exc:
                raise ValidationError("JSON strings must be valid Unicode") from exc
        elif obj is None or type(obj) in (bool, int):
            pass
        elif type(obj) is float:
            if not math.isfinite(obj):
                raise ValidationError("JSON numbers must be finite")
        elif type(obj) in (dict, list):
            identity = id(obj)
            if identity in seen:
                raise ValidationError("JSON must not contain cycles")
            seen.add(identity)
            if type(obj) is dict:
                for key, item in obj.items():
                    if type(key) is not str:
                        raise ValidationError("JSON object keys must be strings")
                    visit(key, depth + 1)
                    visit(item, depth + 1)
            else:
                for item in obj:
                    visit(item, depth + 1)
            seen.remove(identity)
        else:
            raise ValidationError("value is not ordinary JSON")

    visit(value, 0)
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(",", ":"))
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise ValidationError("value cannot be represented as bounded JSON") from exc


def _decode(text: Any) -> Any:
    if type(text) is not str:
        raise StorageError("stored JSON must be text")

    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise StorageError("stored JSON contains duplicate keys")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise StorageError("stored JSON contains a non-finite number")

    try:
        obj = json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)
        if _canonical(obj) != text:
            raise StorageError("stored JSON is not canonical")
        return obj
    except StorageError:
        raise
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError) as exc:
        raise StorageError("stored JSON is invalid") from exc


def _operation_id(value: Any) -> str:
    if type(value) is not str or _OPERATION_ID.fullmatch(value) is None:
        raise ValidationError("operation_id must be 1..128 ASCII letters, digits, '.', '_', ':' or '-', starting with a letter or digit")
    return value


class SQLiteHomeOpsLedger:
    """A connection-per-operation adapter; the original ledger is replayed.

    Successful mutations store the canonical supplied command, one resulting
    event and its original response in one SQLite transaction. Mutation retries
    compare supplied JSON values (including explicit defaults), not normalized
    domain values. Object-key ordering is immaterial; omitted and supplied
    defaults remain different requests.
    """

    def __init__(self, path: str | os.PathLike[str], *, create: bool = True,
                 timeout: float = 5.0) -> None:
        if not hasattr(sqlite3.Connection, "setlimit") or not hasattr(sqlite3, "SQLITE_LIMIT_LENGTH"):
            raise StorageError("durable storage requires Python 3.11 or later with SQLite runtime limits")
        if type(create) is not bool:
            raise ValidationError("create must be boolean")
        if type(timeout) not in (int, float) or not 0 < timeout <= 60 or not math.isfinite(timeout):
            raise ValidationError("timeout must be a finite number in (0, 60]")
        try:
            self.path = Path(path).absolute()
        except (TypeError, ValueError, OSError) as exc:
            raise StorageError("invalid database path") from exc
        self.timeout = float(timeout)
        if not self.path.parent.is_dir():
            raise StorageError("database parent directory must already exist")
        try:
            if not self.path.exists():
                if not create:
                    raise StorageError("database does not exist")
                self._create()
            self.inspect()
        except StorageError:
            raise
        except (OSError, sqlite3.Error) as exc:
            raise StorageError("could not open the local journal") from exc

    def _create(self) -> None:
        # Publish only a complete, closed schema. A concurrent creator either
        # wins the exclusive link or opens that already complete database.
        descriptor, name = tempfile.mkstemp(prefix=".homeops-new-", suffix=".sqlite", dir=self.path.parent)
        os.close(descriptor)
        temporary = Path(name)
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(str(temporary), timeout=self.timeout, isolation_level=None)
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(_TABLE_SQL)
            conn.execute(f"PRAGMA application_id={APPLICATION_ID}")
            conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            conn.commit()
            conn.close()
            conn = None
            try:
                os.link(temporary, self.path)
            except FileExistsError:
                pass
        finally:
            if conn is not None:
                conn.close()
            temporary.unlink(missing_ok=True)

    def _connect(self, *, readonly: bool = False) -> sqlite3.Connection:
        try:
            if not self.path.is_file() or self.path.stat().st_size > MAX_DATABASE_BYTES:
                raise StorageError("database is absent, not a file, or exceeds the size bound")
            # A domain read may need SQLite's automatic hot-journal rollback
            # after a crashed writer. mode=rw permits that recovery but cannot
            # create a missing file; query_only below still forbids read SQL
            # from changing domain rows. The local database must be writable.
            conn = sqlite3.connect(self.path.as_uri() + "?mode=rw",
                                   uri=True, timeout=self.timeout, isolation_level=None)
            try:
                conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_ROW_BYTES + 16_384)
                conn.execute("PRAGMA trusted_schema=OFF")
                if readonly:
                    conn.execute("PRAGMA query_only=ON")
                else:
                    if conn.execute("PRAGMA journal_mode").fetchone()[0].lower() != "delete":
                        raise StorageError("journal requires SQLite DELETE journal mode")
                    conn.execute("PRAGMA synchronous=FULL")
                return conn
            except BaseException:
                conn.close()
                raise
        except StorageError:
            raise
        except (sqlite3.Error, OSError, ValueError) as exc:
            raise StorageError("could not connect to the local journal") from exc

    def _load(self, conn: sqlite3.Connection) -> tuple[HomeOpsLedger, dict[str, tuple[str, str]], int]:
        if conn.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID or conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
            raise StorageError("unrecognized journal schema or version")
        expected = [
            ("index", "sqlite_autoindex_operations_1", "operations", None),
            ("table", "operations", "operations", _TABLE_SQL),
        ]
        objects = conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name").fetchall()
        if objects != expected:
            raise StorageError("journal schema differs from the supported schema")
        if conn.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise StorageError("SQLite integrity check failed")
        count, retained = conn.execute(
            "SELECT count(*),coalesce(sum(length(CAST(request_json AS BLOB)) + "
            "length(CAST(event_json AS BLOB)) + length(CAST(response_json AS BLOB))),0) FROM operations"
        ).fetchone()
        if count > MAX_EVENTS or retained > MAX_RETAINED_BYTES:
            raise StorageError("retained journal exceeds the supported bound")
        ledger = HomeOpsLedger()
        operations: dict[str, tuple[str, str]] = {}
        events: list[dict[str, Any]] = []
        rows = conn.execute("SELECT seq,operation_id,request_json,event_json,response_json FROM operations ORDER BY seq")
        for expected_seq, row in enumerate(rows, 1):
            seq, op_id, request_text, event_text, response_text = row
            if type(seq) is not int or seq != expected_seq:
                raise StorageError("journal operation sequence is not contiguous")
            try:
                _operation_id(op_id)
            except ValidationError as exc:
                raise StorageError("invalid retained operation ID") from exc
            if op_id in operations:
                raise StorageError("duplicate retained operation ID")
            if any(type(value) is not str for value in (request_text, event_text, response_text)):
                raise StorageError("journal payloads must be text")
            if len(request_text.encode("utf-8")) > MAX_REQUEST_BYTES or sum(len(value.encode("utf-8")) for value in (request_text, event_text, response_text)) > MAX_ROW_BYTES:
                raise StorageError("retained operation exceeds its size bound")
            request = _decode(request_text)
            event = _decode(event_text)
            response = _decode(response_text)
            if type(request) is not dict or set(request) != {"name", "arguments"} or request["name"] not in MUTATING_TOOLS or type(request["arguments"]) is not dict or "operation_id" in request["arguments"]:
                raise StorageError("invalid retained command")
            try:
                replayed_response = ledger.call_tool(request["name"], request["arguments"])
                if _canonical(replayed_response) != response_text or _canonical(ledger.events[-1]) != event_text:
                    raise StorageError("stored command, event and response do not agree")
            except StorageError:
                raise
            except (ValidationError, TypeError, KeyError, UnicodeError, IndexError) as exc:
                raise StorageError("retained command cannot be replayed") from exc
            # Retain exactly the checked rows. Never trust just an independently
            # valid event chain when its supplied command/response has drifted.
            events.append(event)
            operations[op_id] = (request_text, response_text)
        try:
            replayed = HomeOpsLedger.replay(events)
            if replayed.snapshot() != ledger.snapshot():
                raise StorageError("command and event replay disagree")
        except StorageError:
            raise
        except (ValidationError, TypeError, KeyError, UnicodeError) as exc:
            raise StorageError("retained event chain is invalid") from exc
        return replayed, operations, retained

    @staticmethod
    def _rollback(conn: sqlite3.Connection) -> None:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass

    def call_tool(self, name: Any, arguments: Any) -> dict[str, Any]:
        if type(name) is not str or name not in MUTATING_TOOLS | READ_TOOLS:
            raise ValidationError("unknown tool")
        if type(arguments) is not dict:
            raise ValidationError("tool arguments must be an object")
        # Detach before any transaction so caller mutation cannot alter either
        # the committed request or the domain invocation behind its digest.
        supplied_text = _canonical(arguments)
        if len(supplied_text.encode("utf-8")) > MAX_REQUEST_BYTES:
            raise ValidationError("request exceeds the storage byte bound")
        supplied = json.loads(supplied_text)
        if name in READ_TOOLS:
            if "operation_id" in supplied:
                raise ValidationError("read-only tools do not accept operation_id")
            return self._read(lambda ledger: ledger.call_tool(name, supplied))
        if "operation_id" not in supplied:
            raise ValidationError("durable mutations require operation_id")
        op_id = _operation_id(supplied.pop("operation_id"))
        request_text = _canonical({"name": name, "arguments": supplied})
        if len(request_text.encode("utf-8")) > MAX_REQUEST_BYTES:
            raise ValidationError("request exceeds the storage byte bound")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            ledger, operations, retained = self._load(conn)
            if op_id in operations:
                original_request, original_response = operations[op_id]
                if original_request != request_text:
                    raise OperationConflictError("operation_id already belongs to a different request")
                # A retry makes no write, and retains the original response even
                # when newer commands have changed the current ledger receipt.
                conn.rollback()
                return _decode(original_response)
            if len(operations) >= MAX_EVENTS:
                raise StorageError("event limit reached")
            response = ledger.call_tool(name, supplied)
            response_text = _canonical(response)
            event_text = _canonical(ledger.events[-1])
            row_size = sum(len(value.encode("utf-8")) for value in (request_text, event_text, response_text))
            if row_size > MAX_ROW_BYTES or retained + row_size > MAX_RETAINED_BYTES:
                raise StorageError("journal byte limit reached")
            conn.execute("INSERT INTO operations(seq,operation_id,request_json,event_json,response_json) VALUES (?,?,?,?,?)",
                         (len(operations) + 1, op_id, request_text, event_text, response_text))
            try:
                conn.commit()
            except Exception as exc:
                # A commit call can fail after durable commit. Never substitute
                # a new operation ID or assert rollback from this observation.
                raise UncertainCommitError("commit acknowledgement is uncertain; retry the identical request with the same operation_id") from exc
            return json.loads(response_text)
        except (StorageError, ValidationError):
            self._rollback(conn)
            raise
        except (sqlite3.Error, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
            self._rollback(conn)
            raise StorageError("journal operation failed before a confirmed commit") from exc
        finally:
            conn.close()

    def _read(self, project: Any) -> Any:
        conn = self._connect(readonly=True)
        try:
            conn.execute("BEGIN")
            ledger, _operations, _retained = self._load(conn)
            result = project(ledger)
            conn.rollback()
            return result
        except (StorageError, ValidationError):
            self._rollback(conn)
            raise
        except (sqlite3.Error, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
            self._rollback(conn)
            raise StorageError("could not validate a consistent journal snapshot") from exc
        finally:
            conn.close()

    @property
    def receipt(self) -> str:
        return self._read(lambda ledger: ledger.receipt)

    def snapshot(self) -> dict[str, Any]:
        return self._read(lambda ledger: ledger.snapshot())

    def export_events(self) -> list[dict[str, Any]]:
        return self._read(lambda ledger: ledger.export_events())

    def inspect(self) -> dict[str, Any]:
        def project(ledger: HomeOpsLedger) -> dict[str, Any]:
            snapshot = ledger.snapshot()
            return {"schema": SCHEMA, "event_count": snapshot["event_count"],
                    "operation_count": snapshot["event_count"], "receipt": ledger.receipt,
                    "snapshot_digest": snapshot["snapshot_digest"]}
        return self._read(project)

    def backup(self, destination: str | os.PathLike[str]) -> dict[str, Any]:
        """Create an independent SQLite snapshot, preserving durable retry IDs."""
        try:
            target = Path(destination).absolute()
        except (TypeError, ValueError, OSError) as exc:
            raise StorageError("invalid backup path") from exc
        source = self._connect(readonly=True)
        copy: sqlite3.Connection | None = None
        created = False
        try:
            source.execute("BEGIN")
            ledger, _operations, _retained = self._load(source)
            descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
            created = True
            copy = sqlite3.connect(target.as_uri() + "?mode=rw", uri=True,
                                   timeout=self.timeout, isolation_level=None)
            deadline = time.monotonic() + self.timeout

            def progress(_status: int, _remaining: int, _total: int) -> None:
                if time.monotonic() >= deadline:
                    raise StorageError("backup exceeded its timeout; retry to a new destination")

            source.backup(copy, pages=256, progress=progress,
                          sleep=min(0.05, self.timeout))
            copy.close()
            copy = None
            source.rollback()
            result = SQLiteHomeOpsLedger(target, create=False, timeout=self.timeout).inspect()
            if result["receipt"] != ledger.receipt:
                raise StorageError("backup does not match the source snapshot")
            return {**result, "destination": str(target)}
        except (StorageError, ValidationError):
            if copy is not None:
                copy.close()
                copy = None
            if created:
                target.unlink(missing_ok=True)
            raise
        except (sqlite3.Error, OSError, ValueError) as exc:
            if copy is not None:
                copy.close()
                copy = None
            if created:
                target.unlink(missing_ok=True)
            raise StorageError("backup failed; destination must be a new file in an existing directory") from exc
        finally:
            if copy is not None:
                copy.close()
            source.close()

    @classmethod
    def tool_definitions(cls) -> list[dict[str, Any]]:
        definitions = HomeOpsLedger.tool_definitions()
        for definition in definitions:
            if definition["name"] in MUTATING_TOOLS:
                schema = definition["inputSchema"]
                schema["properties"]["operation_id"] = {
                    "type": "string", "minLength": 1, "maxLength": 128,
                    "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
                    "description": "Stable durable mutation ID; reuse with the identical request after interruption.",
                }
                schema["required"].append("operation_id")
        return definitions

    def close(self) -> None:
        """No persistent connection is held by this adapter."""

    def __enter__(self) -> "SQLiteHomeOpsLedger":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()
