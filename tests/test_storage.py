"""Independent durability contracts exercised against the real local journal."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from homeops_relay.homeops import HomeOpsLedger, ValidationError
from homeops_relay import storage
from homeops_relay.storage import (
    OperationConflictError,
    SQLiteHomeOpsLedger,
    StorageError,
    UncertainCommitError,
)


ROOT = Path(__file__).resolve().parents[1]
INTAKE = "homeops.intake_issue"


def issue_args(operation_id="intake-1", **changes):
    result = {
        "operation_id": operation_id,
        "title": "Fictional sink leak",
        "area": "kitchen",
        "severity": "HIGH",
        "details": "Synthetic observation for the local journal test.",
        "evidence": ["synthetic:photo-1"],
    }
    result.update(changes)
    return result


def python_command(code, *args):
    # Children execute in the same optimization mode as the actual test runner.
    flags = ["-" + "O" * sys.flags.optimize] if sys.flags.optimize else []
    return [sys.executable, "-B", *flags, "-c", code, *map(str, args)]


WORKER = r"""
import json,sys
from homeops_relay.storage import SQLiteHomeOpsLedger
request=json.loads(sys.stdin.readline())
try:
    ledger=SQLiteHomeOpsLedger(sys.argv[1],create=False,timeout=10)
    result=ledger.call_tool(request['name'],request['args'])
    print(json.dumps({'result':result,'optimize':sys.flags.optimize},sort_keys=True))
except Exception as exc:
    print(json.dumps({'error':type(exc).__name__,'message':str(exc),'optimize':sys.flags.optimize}))
"""


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "journal.sqlite3"
        self.ledger = SQLiteHomeOpsLedger(self.path)

    def call_issue(self, operation_id="intake-1", **changes):
        return self.ledger.call_tool(INTAKE, issue_args(operation_id, **changes))

    def assert_empty(self):
        info = self.ledger.inspect()
        self.assertEqual(info["event_count"], 0)
        self.assertEqual(info["operation_count"], 0)
        self.assertEqual(self.ledger.export_events(), [])

    def run_workers(self, requests):
        processes = [
            subprocess.Popen(
                python_command(WORKER, self.path), cwd=ROOT,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True,
            )
            for _ in requests
        ]
        try:
            # Release every process before collecting any result.
            for proc, request in zip(processes, requests):
                proc.stdin.write(json.dumps(request) + "\n")
                proc.stdin.close()
                proc.stdin = None
            results = []
            for proc in processes:
                stdout, stderr = proc.communicate(timeout=30)
                self.assertEqual(proc.returncode, 0, stderr)
                result = json.loads(stdout)
                self.assertEqual(result["optimize"], sys.flags.optimize)
                results.append(result)
            return results
        finally:
            for proc in processes:
                if proc.poll() is None:
                    proc.kill()
                    proc.communicate(timeout=5)

    def test_empty_journal_matches_original_domain(self):
        original = HomeOpsLedger()
        self.assertEqual(self.ledger.snapshot(), original.snapshot())
        self.assertEqual(self.ledger.receipt, original.receipt)
        info = self.ledger.inspect()
        self.assertIsInstance(info["schema"], str)
        self.assertEqual(info["snapshot_digest"], original.snapshot()["snapshot_digest"])
        self.assert_empty()

    def test_four_mutation_journey_matches_domain_and_replays_after_restart(self):
        domain = HomeOpsLedger()
        first_args = issue_args()
        first = self.ledger.call_tool(INTAKE, first_args)
        self.assertEqual(first, domain.call_tool(INTAKE, {k:v for k,v in first_args.items() if k != "operation_id"}))
        commands = [
            ("homeops.record_quote", {
                "issue_id": first["issue_id"], "provider": "Fictional Provider",
                "amount_minor": 24000, "scope": "Inspection", "source": "synthetic",
            }),
            ("homeops.request_action", {
                "issue_id": first["issue_id"], "action_type": "CONTACT_PROVIDER",
                "target": "Fictional Provider", "note": "Proposal only",
            }),
        ]
        receipts = [(INTAKE, first_args, first)]
        for index, (name, args) in enumerate(commands, 2):
            durable = {**args, "operation_id": f"journey-{index}"}
            result = self.ledger.call_tool(name, durable)
            self.assertEqual(result, domain.call_tool(name, args))
            receipts.append((name, durable, result))
        decision = {
            "action_id": receipts[-1][2]["action_id"], "decision": "APPROVE",
            "evidence_note": "Synthetic owner decision; no action executed.",
        }
        name = "homeops.record_owner_decision"
        durable = {**decision, "operation_id": "journey-4"}
        result = self.ledger.call_tool(name, durable)
        self.assertEqual(result, domain.call_tool(name, decision))
        receipts.append((name, durable, result))
        restarted = SQLiteHomeOpsLedger(self.path, create=False)
        for name, args, original in receipts:
            self.assertEqual(restarted.call_tool(name, args), original)
        self.assertEqual(restarted.snapshot(), domain.snapshot())
        self.assertEqual(restarted.export_events(), domain.export_events())
        self.assertEqual(restarted.inspect()["operation_count"], 4)
        self.assertEqual(result["state"], "APPROVED_NOT_EXECUTED")
        self.assertTrue(all(value is False for value in restarted.snapshot()["authority"].values()))

    def test_old_retry_returns_original_response_after_later_event(self):
        first = self.call_issue()
        later = self.call_issue("intake-2", title="Second fictional observation")
        replay = self.call_issue()
        self.assertEqual(replay, first)
        self.assertNotEqual(replay["receipt"], later["receipt"])
        self.assertEqual(self.ledger.inspect()["event_count"], 2)

    def test_canonical_mapping_order_is_an_exact_retry(self):
        args = issue_args()
        first = self.ledger.call_tool(INTAKE, args)
        self.assertEqual(self.ledger.call_tool(INTAKE, dict(reversed(list(args.items())))), first)
        self.assertEqual(self.ledger.inspect()["event_count"], 1)

    def test_changed_reuse_rejects_without_append_even_when_domain_normalizes_same(self):
        self.call_issue()
        before = self.ledger.snapshot()
        for change in ({"title":"Different"}, {"severity":"high"}, {"evidence":None}):
            with self.subTest(change=change):
                with self.assertRaises(OperationConflictError):
                    self.call_issue(**change)
                self.assertEqual(self.ledger.snapshot(), before)

    def test_operation_id_is_global_across_mutation_names(self):
        first = self.call_issue()
        with self.assertRaises(OperationConflictError):
            self.ledger.call_tool("homeops.record_quote", {
                "operation_id":"intake-1", "issue_id":first["issue_id"],
                "provider":"Fictional", "amount_minor":10, "scope":"Inspection",
            })
        self.assertEqual(self.ledger.inspect()["event_count"], 1)

    def test_mutations_require_valid_operation_ids(self):
        for value in (None, "", " space", "slash/id", "ü", "x"*129, True, 12):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    self.call_issue(value)
        missing = issue_args()
        del missing["operation_id"]
        with self.assertRaises(ValidationError):
            self.ledger.call_tool(INTAKE, missing)
        self.assert_empty()
        self.call_issue("A0._:-")
        self.call_issue("x"*128)
        self.assertEqual(self.ledger.inspect()["event_count"], 2)

    def test_reads_reject_operation_ids_and_do_not_add_operations(self):
        first = self.call_issue()
        for name, args in [
            ("homeops.snapshot", {}),
            ("homeops.propose_plan", {"issue_id":first["issue_id"]}),
        ]:
            with self.subTest(name=name):
                self.ledger.call_tool(name, args)
                with self.assertRaises(ValidationError):
                    self.ledger.call_tool(name, {**args,"operation_id":"read-1"})
        self.assertEqual(self.ledger.inspect()["operation_count"], 1)

    def test_domain_failure_does_not_consume_retry_key(self):
        with self.assertRaises(ValidationError):
            self.call_issue(severity="NOT_A_SEVERITY")
        self.assert_empty()
        self.call_issue()
        self.assertEqual(self.ledger.inspect()["operation_count"], 1)

    def test_request_size_depth_cycles_and_nonfinite_fail_without_append(self):
        nested = []
        for _ in range(40):
            nested = [nested]
        cycle = []
        cycle.append(cycle)
        variants = [
            issue_args(details="x"*65536),
            issue_args(evidence=nested), issue_args(evidence=cycle),
            issue_args(details=float("nan")),
            issue_args(details="\ud800"),
        ]
        for index, args in enumerate(variants):
            with self.subTest(index=index):
                with self.assertRaises(ValidationError):
                    self.ledger.call_tool(INTAKE, args)
                self.assert_empty()

    def test_returned_values_are_detached_from_persisted_journal(self):
        first = self.call_issue()
        expected = copy.deepcopy(first)
        first["state"] = "tampered by caller"
        snapshot = self.ledger.snapshot()
        snapshot["issues"][0]["title"] = "caller changed a copy"
        events = self.ledger.export_events()
        events[0]["payload"]["title"] = "caller changed event copy"
        self.assertEqual(self.call_issue(), expected)
        self.assertNotEqual(self.ledger.snapshot()["issues"][0]["title"], snapshot["issues"][0]["title"])

    def test_two_existing_instances_reload_each_call(self):
        other = SQLiteHomeOpsLedger(self.path, create=False)
        self.call_issue()
        self.assertEqual(other.snapshot(), self.ledger.snapshot())
        other.call_tool(INTAKE, issue_args("from-other"))
        self.assertEqual(self.ledger.inspect()["event_count"], 2)
        self.call_issue("third")
        self.assertEqual(other.inspect()["event_count"], 3)

    def test_process_restart_recovers_exact_response(self):
        response = self.run_workers([{"name":INTAKE,"args":issue_args()}])[0]
        self.assertNotIn("error", response)
        self.assertEqual(self.call_issue(), response["result"])
        self.assertEqual(self.ledger.inspect()["event_count"], 1)

    def test_concurrent_process_distinct_operations_form_one_contiguous_chain(self):
        results = self.run_workers([
            {"name":INTAKE,"args":issue_args(f"parallel-{i}",title=f"Fictional {i}")}
            for i in range(6)
        ])
        self.assertTrue(all("result" in result for result in results), results)
        events = self.ledger.export_events()
        self.assertEqual([event["seq"] for event in events], list(range(1,7)))
        self.assertEqual(HomeOpsLedger.verify_events(events)["receipt"], self.ledger.receipt)
        self.assertEqual(len({result["result"]["issue_id"] for result in results}), 6)
        self.assertEqual(self.ledger.inspect()["operation_count"], 6)

    def test_concurrent_process_exact_retries_append_once(self):
        results = self.run_workers([{"name":INTAKE,"args":issue_args()} for _ in range(6)])
        self.assertTrue(all("result" in result for result in results), results)
        self.assertTrue(all(result["result"] == results[0]["result"] for result in results))
        self.assertEqual(self.ledger.inspect()["event_count"], 1)
        self.assertEqual(self.ledger.inspect()["operation_count"], 1)

    def test_concurrent_process_changed_reuse_has_one_winner(self):
        results = self.run_workers([
            {"name":INTAKE,"args":issue_args(title="Fictional first")},
            {"name":INTAKE,"args":issue_args(title="Fictional second")},
        ])
        self.assertEqual(sum("result" in result for result in results), 1, results)
        self.assertEqual([result["error"] for result in results if "error" in result], ["OperationConflictError"])
        self.assertEqual(self.ledger.inspect()["event_count"], 1)

    def test_locked_writer_fails_without_success_or_append_then_retry_works(self):
        ledger = SQLiteHomeOpsLedger(self.path, create=False, timeout=0.05)
        blocker = sqlite3.connect(self.path, isolation_level=None)
        try:
            blocker.execute("BEGIN IMMEDIATE")
            with self.assertRaises(StorageError):
                ledger.call_tool(INTAKE, issue_args())
        finally:
            blocker.rollback()
            blocker.close()
        self.assert_empty()
        ledger.call_tool(INTAKE, issue_args())
        self.assertEqual(ledger.inspect()["event_count"], 1)

    def test_commit_exception_before_commit_rolls_back_and_same_key_can_retry(self):
        real_connect = self.ledger._connect
        class BeforeCommit:
            def __init__(self, con): self.con = con
            def __getattr__(self, name): return getattr(self.con, name)
            def commit(self): raise sqlite3.OperationalError("injected commit boundary failure")
        def connect(*, readonly=False):
            con = real_connect(readonly=readonly)
            return con if readonly else BeforeCommit(con)
        with mock.patch.object(self.ledger, "_connect", side_effect=connect):
            with self.assertRaises(UncertainCommitError):
                self.call_issue()
        self.assert_empty()
        self.call_issue()
        self.assertEqual(self.ledger.inspect()["event_count"], 1)

    def test_commit_exception_after_real_commit_is_uncertain_and_retry_deduplicates(self):
        real_connect = self.ledger._connect
        class AfterCommit:
            def __init__(self, con): self.con = con
            def __getattr__(self, name): return getattr(self.con, name)
            def commit(self):
                self.con.commit()
                raise sqlite3.OperationalError("injected response loss after commit")
        def connect(*, readonly=False):
            con = real_connect(readonly=readonly)
            return con if readonly else AfterCommit(con)
        with mock.patch.object(self.ledger, "_connect", side_effect=connect):
            with self.assertRaises(UncertainCommitError):
                self.call_issue()
        self.assertEqual(self.ledger.inspect()["event_count"], 1)
        replay = self.call_issue()
        self.assertEqual(replay["receipt"], self.ledger.receipt)
        self.assertEqual(self.ledger.inspect()["operation_count"], 1)

    def test_process_exit_immediately_after_commit_recovers_same_response(self):
        code = r'''
import json,os,sys
from homeops_relay.storage import SQLiteHomeOpsLedger
ledger=SQLiteHomeOpsLedger(sys.argv[1],create=False)
real_connect=ledger._connect
class ExitAfterCommit:
    def __init__(self,con): self.con=con
    def __getattr__(self,name): return getattr(self.con,name)
    def commit(self):
        self.con.commit()
        os._exit(73)
def connect(*,readonly=False):
    con=real_connect(readonly=readonly)
    return con if readonly else ExitAfterCommit(con)
ledger._connect=connect
ledger.call_tool('homeops.intake_issue',json.loads(sys.argv[2]))
raise RuntimeError('response escaped the commit cut')
'''
        proc = subprocess.run(python_command(code, self.path, json.dumps(issue_args())), cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 73, proc.stderr)
        self.assertEqual(proc.stdout, "")
        expected = HomeOpsLedger().call_tool(INTAKE, {k:v for k,v in issue_args().items() if k != "operation_id"})
        restarted = SQLiteHomeOpsLedger(self.path, create=False)
        self.assertEqual(restarted.call_tool(INTAKE, issue_args()), expected)
        self.assertEqual(restarted.inspect()["event_count"], 1)

    def test_create_false_missing_path_and_empty_file_are_refused(self):
        missing = self.root / "missing.sqlite3"
        with self.assertRaises(StorageError):
            SQLiteHomeOpsLedger(missing, create=False)
        self.assertFalse(missing.exists())
        empty = self.root / "empty.sqlite3"
        empty.touch()
        with self.assertRaises(StorageError):
            SQLiteHomeOpsLedger(empty)
        self.assertEqual(empty.read_bytes(), b"")

    def test_missing_runtime_limit_api_refused_before_database_creation(self):
        missing = self.root / "runtime-unavailable.sqlite3"
        with mock.patch.object(storage.sqlite3, "Connection", object):
            with self.assertRaisesRegex(StorageError, "Python 3.11"):
                SQLiteHomeOpsLedger(missing)
        self.assertFalse(missing.exists())

    def test_invalid_timeout_including_huge_integer_is_contained_before_creation(self):
        for index, value in enumerate((10**10000, float("nan"), float("inf"), True, 0, -1, 61, "5")):
            with self.subTest(case=index):
                missing = self.root / f"invalid-timeout-{index}.sqlite3"
                with self.assertRaises(ValidationError):
                    SQLiteHomeOpsLedger(missing, timeout=value)
                self.assertFalse(missing.exists())

    def test_foreign_schema_and_changed_version_are_refused(self):
        foreign = self.root / "foreign.sqlite3"
        with sqlite3.connect(foreign) as con:
            con.execute("CREATE TABLE unrelated(value TEXT)")
            con.execute("INSERT INTO unrelated VALUES('preserve me')")
        before = foreign.read_bytes()
        with self.assertRaises(StorageError):
            SQLiteHomeOpsLedger(foreign)
        self.assertEqual(foreign.read_bytes(), before)
        with sqlite3.connect(self.path) as con:
            con.execute("PRAGMA user_version=999")
        with self.assertRaises(StorageError):
            self.ledger.snapshot()

    def test_corrupt_event_response_request_and_sequence_are_each_refused(self):
        self.call_issue()
        mutations = [
            ("event_json", lambda raw: {**json.loads(raw),"hash":"0"*64}),
            ("response_json", lambda raw: {**json.loads(raw),"state":"INVENTED"}),
            ("request_json", lambda raw: {
                **json.loads(raw),
                "arguments": {**json.loads(raw)["arguments"], "title":"Different retained command"},
            }),
        ]
        for column, transform in mutations:
            with self.subTest(column=column):
                target = self.root / (column + ".sqlite3")
                self.ledger.backup(target)
                with sqlite3.connect(target) as con:
                    raw = con.execute(f"SELECT {column} FROM operations WHERE seq=1").fetchone()[0]
                    replacement = json.dumps(transform(raw), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                    con.execute(f"UPDATE operations SET {column}=? WHERE seq=1", (replacement,))
                with self.assertRaises(StorageError):
                    SQLiteHomeOpsLedger(target, create=False)
        with sqlite3.connect(self.path) as con:
            con.execute("UPDATE operations SET seq=2 WHERE seq=1")
        with self.assertRaises(StorageError):
            self.ledger.inspect()

    def test_duplicate_stored_json_keys_are_refused(self):
        self.call_issue()
        with sqlite3.connect(self.path) as con:
            raw = con.execute("SELECT response_json FROM operations WHERE seq=1").fetchone()[0]
            value = json.loads(raw)
            duplicated = raw[:-1] + ',"receipt":' + json.dumps(value["receipt"]) + '}'
            con.execute("UPDATE operations SET response_json=? WHERE seq=1", (duplicated,))
        with self.assertRaises(StorageError):
            self.ledger.snapshot()

    def test_live_corruption_is_reloaded_before_retry_or_new_write(self):
        self.call_issue()
        with sqlite3.connect(self.path) as con:
            con.execute("UPDATE operations SET response_json='{}' WHERE seq=1")
        for args in (issue_args(), issue_args("new-op")):
            with self.subTest(operation=args["operation_id"]):
                with self.assertRaises(StorageError):
                    self.ledger.call_tool(INTAKE, args)
        with sqlite3.connect(self.path) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM operations").fetchone()[0], 1)

    def test_retained_event_count_above_ten_thousand_refused_before_replay(self):
        # Deliberately invalid retained data must hit the bounded-count refusal
        # before attempting to decode/replay an unbounded row set.
        with sqlite3.connect(self.path) as con:
            con.executemany(
                "INSERT INTO operations VALUES (?,?,?,?,?)",
                ((index, f"oversized-{index}", "{}", "{}", "{}") for index in range(1,10002)),
            )
        with self.assertRaisesRegex(StorageError, "bound"):
            self.ledger.inspect()

    def test_retained_bytes_above_sixty_four_mib_refused_before_json_decode(self):
        # Construct the actual retained-byte boundary, not a lowered production
        # constant. Each individual text is bounded; their total is 67.5 MiB.
        payload = "x" * 65536
        with sqlite3.connect(self.path) as con:
            con.executemany(
                "INSERT INTO operations VALUES (?,?,?,?,?)",
                ((index, f"oversized-{index}", payload, payload, payload) for index in range(1,361)),
            )
        with self.assertRaisesRegex(StorageError, "bound"):
            self.ledger.inspect()

    def test_backup_restore_keeps_retry_journal_and_is_independent(self):
        response = self.call_issue()
        target = self.root / "backup.sqlite3"
        info = self.ledger.backup(target)
        restored = SQLiteHomeOpsLedger(target, create=False)
        self.assertEqual(info["receipt"], self.ledger.receipt)
        self.assertEqual(info["event_count"], 1)
        self.assertEqual(Path(info["destination"]), target)
        self.assertEqual(restored.call_tool(INTAKE, issue_args()), response)
        self.assertEqual(restored.snapshot(), self.ledger.snapshot())
        restored.call_tool(INTAKE, issue_args("restored-only"))
        self.assertEqual(restored.inspect()["event_count"], 2)
        self.assertEqual(self.ledger.inspect()["event_count"], 1)

    def test_backup_never_overwrites_existing_destination_or_source(self):
        self.call_issue()
        target = self.root / "existing.sqlite3"
        target.write_bytes(b"foreign preserved bytes")
        with self.assertRaises(StorageError):
            self.ledger.backup(target)
        self.assertEqual(target.read_bytes(), b"foreign preserved bytes")
        before = self.ledger.snapshot()
        with self.assertRaises(StorageError):
            self.ledger.backup(self.path)
        self.assertEqual(self.ledger.snapshot(), before)

    def test_backup_destination_contention_respects_timeout_and_cleans_owned_file(self):
        self.call_issue()
        target = self.root / "blocked-backup.sqlite3"
        code = r'''
import json,sqlite3,sys,time
from pathlib import Path
from unittest.mock import patch
from homeops_relay.storage import SQLiteHomeOpsLedger,StorageError
ledger=SQLiteHomeOpsLedger(sys.argv[1],create=False,timeout=.05)
destination=Path(sys.argv[2])
before=ledger.inspect()
real=sqlite3.connect
held=[]
def connecting(database,*args,**kwargs):
    conn=real(database,*args,**kwargs)
    if str(database).startswith(destination.as_uri()) and not held:
        blocker=real(str(destination),isolation_level=None)
        blocker.execute('BEGIN EXCLUSIVE')
        held.append(blocker)
    return conn
started=time.monotonic()
error=None
try:
    with patch('homeops_relay.storage.sqlite3.connect',side_effect=connecting):
        try: ledger.backup(destination)
        except StorageError as exc: error=type(exc).__name__
finally:
    for blocker in held:
        blocker.rollback()
        blocker.close()
print(json.dumps({'error':error,'elapsed':time.monotonic()-started,
                  'destination_exists':destination.exists(),
                  'source_unchanged':ledger.inspect()==before,
                  'optimize':sys.flags.optimize}))
'''
        result = subprocess.run(python_command(code, self.path, target), cwd=ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual(observed["error"], "StorageError")
        self.assertLess(observed["elapsed"], 1.5)
        self.assertFalse(observed["destination_exists"])
        self.assertTrue(observed["source_unchanged"])
        self.assertEqual(observed["optimize"], sys.flags.optimize)

    def test_durable_tool_schemas_change_only_mutation_operation_ids(self):
        original = {tool["name"]:tool for tool in HomeOpsLedger.tool_definitions()}
        durable = {tool["name"]:tool for tool in self.ledger.tool_definitions()}
        self.assertEqual(set(original), set(durable))
        mutations = {INTAKE,"homeops.record_quote","homeops.request_action","homeops.record_owner_decision"}
        for name in original:
            schema = durable[name]["inputSchema"]
            if name in mutations:
                self.assertIn("operation_id", schema["properties"])
                self.assertIn("operation_id", schema["required"])
            else:
                self.assertEqual(schema, original[name]["inputSchema"])
        # Advertising durable tools must not modify shared ephemeral definitions.
        self.assertEqual({tool["name"]:tool for tool in HomeOpsLedger.tool_definitions()}, original)


if __name__ == "__main__":
    unittest.main()
