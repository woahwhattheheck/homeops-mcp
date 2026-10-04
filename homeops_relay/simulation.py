from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .mcp_server import Dispatcher, MCP_PROTOCOL_VERSION


STATIC_FILE = Path(__file__).with_name("static") / "simulation.html"
MAX_BODY_BYTES = 16_384


class SimulationSession:
    """Stateful, local-only Alexa+ simulation backed by the real dispatcher."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> dict[str, Any]:
        self.dispatcher = Dispatcher()
        self.issue_id: str | None = None
        self.action_id: str | None = None
        self.view: dict[str, Any] = {
            "mode": "SIMULATED_ALEXA_PLUS",
            "external_effect": False,
            "stage": "ready",
            "message": "Ready for the fictional kitchen-leak walkthrough.",
        }
        initialized = self._rpc(
            1,
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "homeops-browser-simulation", "version": "1"},
            },
        )
        self.view["protocol_version"] = initialized["result"]["protocolVersion"]
        return self.payload()

    def _rpc(self, request_id: int, method: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self.dispatcher.handle(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        if response is None or "error" in response:
            message = "No response" if response is None else response["error"]["message"]
            raise ValueError(message)
        return response

    def _tool(self, request_id: int, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        response = self._rpc(
            request_id,
            "tools/call",
            {"name": name, "arguments": arguments},
        )["result"]
        if response.get("isError"):
            raise ValueError(response["structuredContent"].get("error", "Tool call failed"))
        return response["structuredContent"]

    def run_step(self, step: str, *, decision: str | None = None) -> dict[str, Any]:
        if step == "intake":
            if self.issue_id is not None:
                raise ValueError("Issue intake is already complete; reset to start over")
            issue = self._tool(
                2,
                "homeops.intake_issue",
                {
                    "title": "Water collecting under kitchen sink",
                    "area": "kitchen",
                    "severity": "HIGH",
                    "details": "Slow water leak appears after the faucet runs.",
                    "evidence": [
                        "photo:simulation/sink-cabinet.jpg",
                        "observation:dry when faucet is unused",
                    ],
                },
            )
            self.issue_id = issue["issue_id"]
            self.view.update(
                stage="intake",
                message="Captured the observation as evidence, not as a diagnosis.",
                issue=issue,
            )
        elif step == "quotes":
            issue_id = self._require_issue()
            if "quotes" in self.view:
                raise ValueError("Synthetic quotes are already recorded")
            quotes = [
                self._tool(
                    3,
                    "homeops.record_quote",
                    {
                        "issue_id": issue_id,
                        "provider": "Example Plumbing A",
                        "amount_minor": 24500,
                        "currency": "USD",
                        "scope": "Replace supply line if inspection confirms leak",
                        "source": "synthetic simulation quote",
                    },
                ),
                self._tool(
                    4,
                    "homeops.record_quote",
                    {
                        "issue_id": issue_id,
                        "provider": "Example Plumbing B",
                        "amount_minor": 31000,
                        "currency": "USD",
                        "scope": "Diagnostic visit plus approved supply-line repair",
                        "source": "synthetic simulation quote",
                    },
                ),
            ]
            self.view.update(
                stage="quotes",
                message="Recorded two caller-supplied synthetic quotes; neither is verified.",
                quotes=quotes,
            )
        elif step == "plan":
            issue_id = self._require_issue()
            if "quotes" not in self.view:
                raise ValueError("Record the synthetic quotes before requesting a plan")
            plan = self._tool(5, "homeops.propose_plan", {"issue_id": issue_id})
            self.view.update(
                stage="plan",
                message="Built a safety-first plan without selecting or contacting a provider.",
                plan=plan,
            )
        elif step == "request":
            issue_id = self._require_issue()
            if "plan" not in self.view:
                raise ValueError("Create the plan before proposing an action")
            if self.action_id is not None:
                raise ValueError("An action proposal already exists")
            action = self._tool(
                6,
                "homeops.request_action",
                {
                    "issue_id": issue_id,
                    "action_type": "CONTACT_PROVIDER",
                    "target": "Example Plumbing A",
                    "max_amount_minor": 24500,
                    "currency": "USD",
                    "note": "Ask for earliest diagnostic window; do not book automatically.",
                },
            )
            self.action_id = action["action_id"]
            self.view.update(
                stage="owner_review",
                message="Contact is only a proposal. No message, booking, or payment was sent.",
                action=action,
            )
        elif step == "decision":
            if self.action_id is None:
                raise ValueError("Create the action proposal before recording a decision")
            if "decision" in self.view:
                raise ValueError("The owner decision is already recorded; reset to try the other path")
            normalized = (decision or "").upper()
            if normalized not in {"APPROVE", "REJECT"}:
                raise ValueError("decision must be APPROVE or REJECT")
            result = self._tool(
                7,
                "homeops.record_owner_decision",
                {
                    "action_id": self.action_id,
                    "decision": normalized,
                    "evidence_note": "Owner selected this option in the local simulation.",
                },
            )
            message = (
                "Approval was recorded, but the provider was not contacted and nothing was executed."
                if normalized == "APPROVE"
                else "The proposal was rejected; no provider contact or other side effect occurred."
            )
            self.view.update(stage="decision", message=message, decision=result)
        elif step == "snapshot":
            if self.issue_id is None:
                raise ValueError("Run the scenario before requesting its receipt")
            snapshot = self._tool(8, "homeops.snapshot", {})
            verification = self.dispatcher.ledger.verify_events(
                self.dispatcher.ledger.export_events()
            )
            self.view.update(
                stage="receipt",
                message="The event chain replayed successfully; this is a local simulation receipt.",
                snapshot=snapshot,
                verification=verification,
            )
        else:
            raise ValueError("unknown simulation step")
        return self.payload()

    def _require_issue(self) -> str:
        if self.issue_id is None:
            raise ValueError("Capture the issue before continuing")
        return self.issue_id

    def payload(self) -> dict[str, Any]:
        return {
            **self.view,
            "event_count": len(self.dispatcher.ledger.events),
            "event_receipt": self.dispatcher.ledger.receipt,
        }


class SimulationHandler(BaseHTTPRequestHandler):
    session: SimulationSession
    server_version = "HomeOpsSimulation/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path not in {"/", "/index.html"}:
            self.send_error(404)
            return
        body = STATIC_FILE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path not in {"/api/reset", "/api/step"}:
            self._json_response(404, {"error": "not found"})
            return
        try:
            raw_length = self.headers.get("Content-Length", "0")
            length = int(raw_length)
            if length < 0 or length > MAX_BODY_BYTES:
                raise ValueError("request body is too large")
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("request body must be an object")
            if self.path == "/api/reset":
                payload = self.session.reset()
            else:
                payload = self.session.run_step(
                    str(body.get("step", "")),
                    decision=body.get("decision"),
                )
            self._json_response(200, payload)
        except (ValueError, json.JSONDecodeError) as exc:
            self._json_response(400, {"error": str(exc)})

    def _json_response(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


def smoke() -> dict[str, Any]:
    session = SimulationSession()
    session.run_step("intake")
    session.run_step("quotes")
    session.run_step("plan")
    pending = session.run_step("request")
    if pending["action"]["state"] != "PENDING_OWNER_REVIEW":
        raise AssertionError("action did not stop for owner review")
    approved = session.run_step("decision", decision="APPROVE")
    if approved["decision"]["state"] != "APPROVED_NOT_EXECUTED":
        raise AssertionError("approval truth ceiling changed")
    final = session.run_step("snapshot")
    if not final["verification"]["verified"] or final["snapshot"]["authority"]["external_effect"]:
        raise AssertionError("simulation receipt is not truthfully bounded")
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local HomeOps Relay Alexa+ browser simulation")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--smoke", action="store_true", help="run the complete scenario without starting a server")
    args = parser.parse_args()
    if args.smoke:
        result = smoke()
        print(
            json.dumps(
                {
                    "verified": result["verification"]["verified"],
                    "event_count": result["event_count"],
                    "action_state": result["decision"]["state"],
                    "external_effect": result["snapshot"]["authority"]["external_effect"],
                    "receipt": result["event_receipt"],
                },
                sort_keys=True,
            )
        )
        return
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("the simulation binds to loopback only")
    SimulationHandler.session = SimulationSession()
    server = ThreadingHTTPServer((args.host, args.port), SimulationHandler)
    print(f"HomeOps simulated Alexa+ experience: http://{args.host}:{server.server_port}")
    print("Synthetic data only; no provider contact, booking, purchase, or payment is executed.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
