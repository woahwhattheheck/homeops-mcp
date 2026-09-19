"""Durable MCP wiring and actual local HTTP/process restart checks."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import select
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
import urllib.error
import urllib.request

from homeops_relay.homeops import HomeOpsLedger, ValidationError
from homeops_relay.mcp_server import Dispatcher, MCP_PROTOCOL_VERSION, make_server
from homeops_relay.storage import SQLiteHomeOpsLedger, StorageError, UncertainCommitError


ROOT = Path(__file__).resolve().parents[1]


def intake(operation_id="http-intake"):
    return {
        "operation_id": operation_id, "title": "Fictional local observation",
        "area": "kitchen", "severity": "LOW",
        "details": "Synthetic test; no household or provider action.",
    }


def tool_message(name, args, request_id=2):
    return {"jsonrpc":"2.0", "id":request_id, "method":"tools/call", "params":{"name":name,"arguments":args}}


class DurableDispatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "journal.sqlite3"

    def test_durable_tools_list_advertises_required_operation_id(self):
        dispatcher = Dispatcher(durable_path=self.path)
        result = dispatcher.handle({"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}})
        tools = {tool["name"]:tool for tool in result["result"]["tools"]}
        self.assertIn("operation_id", tools["homeops.intake_issue"]["inputSchema"]["required"])
        self.assertNotIn("operation_id", tools["homeops.snapshot"]["inputSchema"]["properties"])
        args = intake()
        del args["operation_id"]
        response = dispatcher.handle(tool_message("homeops.intake_issue", args))
        self.assertTrue(response["result"]["isError"])
        self.assertEqual(dispatcher.ledger.inspect()["operation_count"], 0)

    def test_explicit_library_configuration_ignores_environment(self):
        unwanted = Path(self.temp.name) / "env-ignored.sqlite3"
        with mock.patch.dict(os.environ, {"HOMEOPS_DB_PATH":str(unwanted)}):
            dispatcher = Dispatcher()
            server = make_server("127.0.0.1", 0)
            try:
                self.assertIsInstance(dispatcher.ledger, HomeOpsLedger)
                self.assertIsInstance(server.dispatcher.ledger, HomeOpsLedger)
                self.assertFalse(unwanted.exists())
            finally:
                server.server_close()

    def test_ambiguous_ledger_and_path_fail_before_socket_bind(self):
        ledger = HomeOpsLedger()
        with self.assertRaises(ValidationError):
            Dispatcher(ledger, durable_path=self.path)
        with mock.patch("http.server.ThreadingHTTPServer.server_bind") as bind:
            with self.assertRaises(ValidationError):
                make_server("127.0.0.1", 0, ledger, durable_path=self.path)
            bind.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_storage_errors_are_structured_tool_errors(self):
        dispatcher = Dispatcher(durable_path=self.path)
        for error in (StorageError("stored journal invalid"), UncertainCommitError("retry the same operation_id")):
            with self.subTest(error=type(error).__name__):
                with mock.patch.object(dispatcher.ledger, "call_tool", side_effect=error):
                    response = dispatcher.handle(tool_message("homeops.intake_issue", intake()))
                self.assertNotIn("error", response)
                result = response["result"]
                self.assertTrue(result["isError"])
                payload = result["structuredContent"]
                self.assertEqual(payload["storage_error"], type(error).__name__)
                self.assertEqual(json.loads(result["content"][0]["text"]), payload)
                if isinstance(error, UncertainCommitError):
                    self.assertIs(payload["retry_with_same_operation_id"], True)
                else:
                    self.assertNotIn("retry_with_same_operation_id", payload)

    def test_changed_operation_reuse_is_a_tool_error_without_second_event(self):
        dispatcher = Dispatcher(durable_path=self.path)
        first = dispatcher.handle(tool_message("homeops.intake_issue", intake()))
        self.assertFalse(first["result"]["isError"])
        changed = {**intake(),"title":"Changed fictional observation"}
        result = dispatcher.handle(tool_message("homeops.intake_issue", changed))["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["storage_error"], "OperationConflictError")
        self.assertEqual(dispatcher.ledger.inspect()["event_count"], 1)


class HTTPClient:
    def __init__(self, test, base):
        self.test = test
        self.base = base
        self.session = None
        self.request_id = 10

    def request(self, payload, *, initialized=True):
        headers = {"Content-Type":"application/json", "Accept":"application/json, text/event-stream"}
        if initialized and self.session:
            headers.update({"MCP-Session-Id":self.session,"MCP-Protocol-Version":MCP_PROTOCOL_VERSION})
        request = urllib.request.Request(self.base+"/mcp", data=json.dumps(payload).encode(), headers=headers, method="POST")
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None, dict(response.headers.items())

    def ready(self):
        status, result, headers = self.request({
            "jsonrpc":"2.0", "id":1, "method":"initialize", "params":{
                "protocolVersion":MCP_PROTOCOL_VERSION,"capabilities":{},
                "clientInfo":{"name":"durable-independent-test","version":"1"},
            },
        }, initialized=False)
        self.test.assertEqual(status, 200)
        self.test.assertEqual(result["result"]["protocolVersion"], MCP_PROTOCOL_VERSION)
        self.session = headers["MCP-Session-Id"]
        status, result, _ = self.request({"jsonrpc":"2.0","method":"notifications/initialized","params":{}})
        self.test.assertEqual(status, 202)
        self.test.assertIsNone(result)
        return self

    def call(self, name, args):
        self.request_id += 1
        status, result, _ = self.request(tool_message(name,args,self.request_id))
        self.test.assertEqual(status, 200)
        self.test.assertNotIn("error", result)
        return result["result"]


class DurableHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "journal.sqlite3"
        self.server = make_server("127.0.0.1", 0, durable_path=self.path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def test_http_schema_retry_and_stored_original_response(self):
        client = HTTPClient(self,self.base).ready()
        status, listed, _ = client.request({"jsonrpc":"2.0","id":3,"method":"tools/list","params":{}})
        self.assertEqual(status, 200)
        tools = {tool["name"]:tool for tool in listed["result"]["tools"]}
        self.assertIn("operation_id", tools["homeops.intake_issue"]["inputSchema"]["required"])
        first = client.call("homeops.intake_issue", intake())
        self.assertFalse(first["isError"])
        second = client.call("homeops.intake_issue", intake("second-http"))
        self.assertFalse(second["isError"])
        replay = client.call("homeops.intake_issue", intake())
        self.assertEqual(replay, first)
        snapshot = client.call("homeops.snapshot", {})["structuredContent"]
        self.assertEqual(snapshot["event_count"], 2)
        self.assertEqual(snapshot["event_receipt"], second["structuredContent"]["receipt"])

    def test_http_health_corruption_returns_complete_503_json(self):
        HTTPClient(self,self.base).ready().call("homeops.intake_issue", intake())
        with sqlite3.connect(self.path) as con:
            con.execute("UPDATE operations SET response_json='{}' WHERE seq=1")
        with self.assertRaises(urllib.error.HTTPError) as failure:
            urllib.request.urlopen(self.base+"/healthz", timeout=5)
        response = failure.exception
        try:
            self.assertEqual(response.code, 503)
            payload = json.loads(response.read())
        finally:
            response.close()
        self.assertIs(payload["ok"], False)
        self.assertIn("storage_error", payload)
        self.assertIn("error", payload)

    def test_http_live_corruption_is_tool_error_without_journal_append(self):
        client = HTTPClient(self,self.base).ready()
        client.call("homeops.intake_issue", intake())
        with sqlite3.connect(self.path) as con:
            con.execute("UPDATE operations SET response_json='{}' WHERE seq=1")
        result = client.call("homeops.intake_issue", intake("new-http"))
        self.assertTrue(result["isError"])
        self.assertIn("storage_error", result["structuredContent"])
        with sqlite3.connect(self.path) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM operations").fetchone()[0], 1)


class DurableServerProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "process.sqlite3"

    def start(self):
        flags = ["-"+"O"*sys.flags.optimize] if sys.flags.optimize else []
        env = {**os.environ,"HOMEOPS_DB_PATH":str(self.path),"HOMEOPS_HOST":"127.0.0.1","HOMEOPS_PORT":"0"}
        process = subprocess.Popen([sys.executable,"-B",*flags,"-m","homeops_relay.mcp_server"], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.stop, process)
        readable, _, _ = select.select([process.stdout], [], [], 10)
        self.assertTrue(readable, "server did not announce startup")
        line = process.stdout.readline()
        match = re.search(r"http://127\.0\.0\.1:(\d+)/mcp", line)
        if not match:
            self.stop(process)
            self.fail(f"server startup did not announce a bound local port: {line!r}")
        return process, HTTPClient(self, f"http://127.0.0.1:{match.group(1)}").ready()

    @staticmethod
    def stop(process):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for stream in (process.stdout, process.stderr):
            if stream and not stream.closed:
                stream.close()

    def test_environment_configured_http_process_restart_preserves_retries(self):
        process, client = self.start()
        first = client.call("homeops.intake_issue", intake("process-intake"))
        self.assertFalse(first["isError"])
        original_session = client.session
        self.stop(process)
        process, restarted = self.start()
        self.assertNotEqual(restarted.session, original_session)
        replay = restarted.call("homeops.intake_issue", intake("process-intake"))
        self.assertEqual(replay, first)
        snapshot = restarted.call("homeops.snapshot", {})["structuredContent"]
        self.assertEqual(snapshot["event_count"], 1)
        self.assertEqual(snapshot["event_receipt"], first["structuredContent"]["receipt"])
        self.stop(process)
        restored = SQLiteHomeOpsLedger(self.path, create=False)
        self.assertEqual(restored.inspect()["operation_count"], 1)


if __name__ == "__main__":
    unittest.main()
