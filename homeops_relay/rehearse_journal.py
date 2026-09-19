"""Exercise fictional HomeOps journal persistence through real server processes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "2025-11-25"


class RehearsalError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RehearsalError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def rehearse(output: Path) -> dict:
    if sys.version_info < (3, 11):
        raise RehearsalError("durable journal rehearsal requires Python 3.11 or newer")
    output = output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    commands_dir = output / "commands"
    commands_dir.mkdir()
    http_dir = output / "http"
    http_dir.mkdir()
    python = [sys.executable, "-B"] + (["-O"] if sys.flags.optimize else [])
    source_files = ["homeops_relay/homeops.py", "homeops_relay/storage.py",
                    "homeops_relay/mcp_server.py", "homeops_relay/journal_cli.py",
                    "homeops_relay/rehearse_journal.py"]
    source_pins = {name: digest(ROOT / name) for name in source_files}
    commands = []
    processes = []
    requests = []
    active = None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def cli(label: str, args: list[str], expected: int = 0) -> dict | None:
        command = python + ["-m", "homeops_relay.journal_cli"] + args
        run = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=30)
        stem = f"{len(commands)+1:02d}-{label}"
        (commands_dir / f"{stem}.stdout.txt").write_bytes(run.stdout)
        (commands_dir / f"{stem}.stderr.txt").write_bytes(run.stderr)
        row = {"label": label, "argv": command, "command": shlex.join(command),
               "cwd": str(ROOT), "exit_code": run.returncode, "expected_exit_code": expected,
               "stdout": run.stdout.decode("utf-8", errors="replace"),
               "stderr": run.stderr.decode("utf-8", errors="replace")}
        save(commands_dir / f"{stem}.json", row)
        commands.append(row)
        require(run.returncode == expected, f"{label}: expected exit {expected}, got {run.returncode}")
        return json.loads(run.stdout) if run.returncode == 0 else None

    def start(label: str, database: Path) -> dict:
        nonlocal active
        environment = {"HOMEOPS_HOST": "127.0.0.1", "HOMEOPS_PORT": "0",
                       "HOMEOPS_DB_PATH": str(database), "PYTHONDONTWRITEBYTECODE": "1"}
        command = python + ["-m", "homeops_relay.mcp_server"]
        stdout_path = output / f"{label}-server.stdout.txt"
        stderr_path = output / f"{label}-server.stderr.txt"
        stdout_handle = stdout_path.open("xb")
        stderr_handle = stderr_path.open("xb")
        process = subprocess.Popen(command, cwd=ROOT, env={**os.environ, **environment},
                                   stdout=stdout_handle, stderr=stderr_handle)
        row = {"label": label, "argv": command, "command": shlex.join(command),
               "cwd": str(ROOT), "environment_overrides": environment,
               "pid": process.pid, "stdout_file": stdout_path.name,
               "stderr_file": stderr_path.name}
        active = {"process": process, "handles": [stdout_handle, stderr_handle], "row": row}
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            text = stdout_path.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"http://127\.0\.0\.1:(\d+)/mcp", text)
            if match:
                row["endpoint"] = match.group(0)
                return {"label": label, "endpoint": match.group(0), "session": None}
            require(process.poll() is None, f"{label}: server exited before readiness; inspect server logs")
            time.sleep(0.05)
        raise RehearsalError(f"{label}: server readiness timed out")

    def stop() -> None:
        nonlocal active
        if active is None:
            return
        process = active["process"]
        row = active["row"]
        if process.poll() is None:
            row["stop_requested"] = "terminate after completed HTTP checks"
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            row["forced_kill_after_timeout"] = True
            process.kill()
            process.wait(timeout=5)
        row["exit_code"] = process.returncode
        for handle in active["handles"]:
            handle.close()
        processes.append(row)
        save(output / f"{row['label']}-process.json", row)
        active = None

    def rpc(connection: dict, label: str, payload: dict, expected_status: int = 200) -> dict | None:
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if connection["session"]:
            headers["MCP-Session-Id"] = connection["session"]
            headers["MCP-Protocol-Version"] = PROTOCOL
        request = urllib.request.Request(connection["endpoint"], data=json.dumps(payload).encode(),
                                         headers=headers, method="POST")
        try:
            with opener.open(request, timeout=5) as response:
                status, raw = response.status, response.read()
                session = response.headers.get("MCP-Session-Id")
        except urllib.error.HTTPError as exc:
            status, raw, session = exc.code, exc.read(), None
        body = json.loads(raw) if raw else None
        row = {"label": label, "server": connection["label"], "request": payload,
               "http_status": status, "response": body,
               "session_header_sent": connection["session"] is not None,
               "session_header_received": session is not None}
        save(http_dir / f"{len(requests)+1:02d}-{label}.json", row)
        requests.append(row)
        require(status == expected_status, f"{label}: unexpected HTTP status {status}")
        if session:
            connection["session"] = session
        return body

    def ready(connection: dict) -> None:
        body = rpc(connection, "initialize", {"jsonrpc": "2.0", "id": len(requests)+1,
                   "method": "initialize", "params": {"protocolVersion": PROTOCOL,
                   "capabilities": {}, "clientInfo": {"name": "fictional-journal-rehearsal", "version": "1"}}})
        require(body["result"]["protocolVersion"] == PROTOCOL and bool(connection["session"]),
                "initialize did not establish the expected protocol/session")
        rpc(connection, "initialized", {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, 202)

    def call(connection: dict, label: str, name: str, arguments: dict, error: bool = False) -> dict:
        body = rpc(connection, label, {"jsonrpc": "2.0", "id": len(requests)+1,
                   "method": "tools/call", "params": {"name": name, "arguments": arguments}})
        require("result" in body and body["result"]["isError"] is error,
                f"{label}: unexpected MCP result")
        return body["result"]["structuredContent"]

    def snapshot(connection: dict, label: str) -> dict:
        value = call(connection, label, "homeops.snapshot", {})
        require(all(flag is False for flag in value["authority"].values()),
                "snapshot claimed an external effect")
        return value

    database = output / "working.sqlite"
    backup = output / "backup.sqlite"
    restored = output / "restored.sqlite"
    exported = output / "events.json"
    operations = []
    try:
        first = start("initial", database)
        ready(first)
        intake_args = {"operation_id": "DEMO-ISSUE-001", "title": "Fictional drawer sticks",
                       "area": "Fictional cabinet", "severity": "LOW",
                       "details": "Synthetic observation: an empty drawer catches halfway open.",
                       "evidence": ["fixture:drawer-observation-001"]}
        intake = call(first, "intake", "homeops.intake_issue", intake_args)
        operations.append(("homeops.intake_issue", intake_args, intake))
        quote_args = {"operation_id": "DEMO-QUOTE-001", "issue_id": intake["issue_id"],
                      "provider": "FICTIONAL-PROVIDER-01", "amount_minor": 4500, "currency": "USD",
                      "scope": "Fictional drawer alignment inspection", "source": "fixture:unverified-quote-001"}
        quote = call(first, "quote", "homeops.record_quote", quote_args)
        operations.append(("homeops.record_quote", quote_args, quote))
        plan = call(first, "plan", "homeops.propose_plan", {"issue_id": intake["issue_id"]})
        require(plan["authority"]["external_effect"] is False, "plan claimed external execution")
        action_args = {"operation_id": "DEMO-ACTION-001", "issue_id": intake["issue_id"],
                       "action_type": "CONTACT_PROVIDER", "target": "FICTIONAL-PROVIDER-01",
                       "note": "Demonstration proposal only; no contact is sent.",
                       "max_amount_minor": 4500, "currency": "USD"}
        action = call(first, "action", "homeops.request_action", action_args)
        require(action["state"] == "PENDING_OWNER_REVIEW" and action["external_effect"] is False,
                "action did not remain a proposal")
        operations.append(("homeops.request_action", action_args, action))
        decision_args = {"operation_id": "DEMO-DECISION-001", "action_id": action["action_id"],
                         "decision": "APPROVE", "evidence_note": "Fictional owner decision recorded for the rehearsal; no execution."}
        decision = call(first, "decision", "homeops.record_owner_decision", decision_args)
        require(decision["state"] == "APPROVED_NOT_EXECUTED" and decision["external_effect"] is False,
                "recorded decision claimed execution")
        operations.append(("homeops.record_owner_decision", decision_args, decision))
        original_snapshot = snapshot(first, "original-snapshot")
        require(original_snapshot["event_count"] == 4, "expected four original domain events")
        stop()

        restarted = start("restarted", database)
        ready(restarted)
        require(snapshot(restarted, "restarted-snapshot") == original_snapshot,
                "restart changed the domain snapshot")
        for index, (name, args, response) in enumerate(operations, 1):
            require(call(restarted, f"retry-{index}", name, args) == response,
                    f"retry {index} did not return its original payload")
        require(snapshot(restarted, "after-retries") == original_snapshot,
                "exact retries appended or changed state")
        conflict = call(restarted, "changed-retry", "homeops.record_quote",
                        {**quote_args, "amount_minor": 4600}, error=True)
        require(bool(conflict.get("error")), "changed retry did not report its conflict")
        require(snapshot(restarted, "after-changed-retry") == original_snapshot,
                "changed retry altered persisted state")
        stop()

        original_inspect = cli("inspect-original", ["inspect", str(database)])
        require(original_inspect["event_count"] == 4 and original_inspect["operation_count"] == 4,
                "journal must retain four events and four operation IDs")
        cli("export-events", ["export", str(database), "--output", str(exported)])
        event_export = json.loads(exported.read_text(encoding="utf-8"))
        require(event_export["snapshot"] == original_snapshot and
                event_export["retry_operations_included"] is False and event_export["restore_supported"] is False,
                "event-only export misrepresented durable retry recovery")
        cli("backup", ["backup", str(database), "--output", str(backup)])
        cli("restore", ["restore", str(backup), "--output", str(restored)])
        restored_inspect = cli("inspect-restored", ["inspect", str(restored)])
        require(restored_inspect == original_inspect, "restored journal facts differ from backup point")

        restored_server = start("restored", restored)
        ready(restored_server)
        require(snapshot(restored_server, "restored-snapshot") == original_snapshot,
                "restored server did not reproduce the backup snapshot")
        require(call(restored_server, "restored-decision-retry", "homeops.record_owner_decision", decision_args) == decision,
                "restore lost the operation ID or its historical response")
        require(snapshot(restored_server, "restored-after-retry") == original_snapshot,
                "restored decision retry added an event")
        continued = call(restored_server, "continued-intake", "homeops.intake_issue",
                         {**intake_args, "operation_id": "DEMO-ISSUE-002",
                          "title": "Fictional second drawer observation"})
        continued_snapshot = snapshot(restored_server, "continued-snapshot")
        require(continued_snapshot["event_count"] == 5 and continued_snapshot["event_receipt"] != original_snapshot["event_receipt"],
                "restored journal did not accept one new operation")
        stop()

        require(cli("inspect-original-again", ["inspect", str(database)]) == original_inspect,
                "working on the restored journal altered the original")
        require(cli("inspect-backup-again", ["inspect", str(backup)]) == original_inspect,
                "working on the restored journal altered the backup")
        continued_inspect = cli("inspect-continued", ["inspect", str(restored)])
        require(continued_inspect["event_count"] == 5 and continued_inspect["operation_count"] == 5,
                "continued journal must retain five events and operation IDs")
        backup_hash, export_hash = digest(backup), digest(exported)
        cli("backup-existing-rejected", ["backup", str(database), "--output", str(backup)], expected=2)
        cli("export-existing-rejected", ["export", str(database), "--output", str(exported)], expected=2)
        require(digest(backup) == backup_hash and digest(exported) == export_hash,
                "rejected overwrite changed a retained file")
        require(all(digest(ROOT/name) == value for name, value in source_pins.items()),
                "source bytes changed during the rehearsal")
        result = {"schema": "homeops-journal-rehearsal/v1", "ok": True,
                  "fictional": True, "python_optimized": bool(sys.flags.optimize),
                  "source_files_sha256": source_pins, "commands": commands,
                  "server_processes": processes, "http_records": len(requests),
                  "original_journal": original_inspect, "restored_at_backup_point": restored_inspect,
                  "continued_journal": continued_inspect, "original_snapshot": original_snapshot,
                  "continued_snapshot": continued_snapshot, "changed_retry_error": conflict,
                  "original_operation_responses": [response for _, _, response in operations],
                  "continued_operation_response": continued,
                  "exact_retries_preserved_original_payloads": True,
                  "restored_decision_retry_preserved_original_payload": True,
                  "rejected_output_overwrites_preserved_bytes": True,
                  "event_export_supports_retry_restore": False,
                  "browser_or_alexa_execution": False}
        save(output / "rehearsal.json", result)
        return result
    finally:
        stop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = rehearse(args.output_dir)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"homeops rehearsal: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "cli_commands": len(result["commands"]),
                      "server_processes": len(result["server_processes"]),
                      "http_records": result["http_records"],
                      "python_optimized": result["python_optimized"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
