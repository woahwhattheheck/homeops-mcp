"""Portable owner handoffs derived from one validated domain event sequence."""
from __future__ import annotations

from collections import Counter
from html import escape
import re
from typing import Any, Iterable

from .homeops import HomeOpsLedger, ValidationError


def _amount(value: int | None, currency: str) -> str:
    if value is None:
        return "No amount cap recorded"
    # The domain accepts arbitrary currency codes, without an exponent registry.
    # Preserve integer minor units rather than assume every currency has cents.
    return f"{value:,} minor units ({currency})"


def _blocks(ledger: HomeOpsLedger, snapshot: dict[str, Any], issues: list[dict[str, Any]]):
    events = ledger.export_events()
    receipts = {
        (event["kind"], event["payload"].get("issue_id", ""),
         event["payload"].get("quote_id", event["payload"].get("action_id", ""))): event["hash"]
        for event in events
    }
    reviews = {event["payload"]["action_id"]: event for event in events
               if event["kind"] == "ACTION_REVIEWED"}
    for position, issue in enumerate(issues, 1):
        issue_id = issue["issue_id"]
        yield "issue", (f"issue-{position}", issue["title"])
        yield "fields", [("Issue", issue_id), ("Area", issue["area"]),
                         ("Severity", issue["severity"]), ("State", issue["state"])]
        yield "paragraph", issue["details"]
        yield "heading", "Evidence references"
        evidence = issue["evidence"]
        yield "list", evidence or ["No evidence references recorded."]
        yield "fields", [("Intake receipt", receipts[("ISSUE_INTAKE", issue_id, "")])]
        yield "heading", "Diagnostic plan"
        plan = ledger.propose_plan(issue_id=issue_id)
        yield "ordered", plan["steps"]
        yield "fields", [("Plan digest", plan["plan_digest"]), ("Plan source receipt", plan["source_receipt"])]
        yield "heading", "Recorded quotes"
        quotes = {quote["quote_id"]: quote for quote in snapshot["quotes"] if quote["issue_id"] == issue_id}
        if not quotes:
            yield "paragraph", "No quotes recorded."
        for planned_quote in plan["quotes"]:
            quote = quotes[planned_quote["quote_id"]]
            yield "subheading", quote["provider"]
            yield "fields", [("Quote", quote["quote_id"]),
                             ("Amount", _amount(quote["amount_minor"], quote["currency"])),
                             ("Scope", quote["scope"]), ("Source", quote["source"]),
                             ("Verification", quote["verification"]),
                             ("Receipt", receipts[("QUOTE_RECORDED", issue_id, quote["quote_id"])])]
        if quotes:
            yield "paragraph", "Quotes retain their supplied scopes and currencies. Price ordering does not establish equivalent work or a recommended provider."
        yield "heading", "Action proposals and owner decisions"
        actions = [action for action in snapshot["actions"] if action["issue_id"] == issue_id]
        if not actions:
            yield "paragraph", "No action proposals recorded."
        for action in actions:
            yield "subheading", f"{action['action_type']} — {action['state']}"
            yield "fields", [("Action", action["action_id"]), ("Target", action["target"]),
                             ("Amount cap", _amount(action["max_amount_minor"], action["currency"])),
                             ("Proposal note", action["note"] or "No note recorded"),
                             ("External effect", "None; this journal does not execute actions"),
                             ("Request receipt", receipts[("ACTION_REQUESTED", issue_id, action["action_id"])])]
            review = reviews.get(action["action_id"])
            if review is None:
                yield "paragraph", "Owner decision pending."
            else:
                yield "fields", [("Recorded decision", review["payload"]["decision"]),
                                 ("Decision evidence note", review["payload"]["evidence_note"]),
                                 ("Decision receipt", review["hash"])]


def _markdown_text(value: Any) -> str:
    text = escape(str(value), quote=False)
    text = re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", text)
    return text.replace("\n", "  \n")


def render_report(events: Iterable[dict[str, Any]], *, output_format: str = "html",
                  issue_id: str | None = None) -> tuple[str, dict[str, Any]]:
    """Validate once, then render the retained snapshot, plans and decision notes."""
    if output_format not in {"html", "markdown"}:
        raise ValidationError("report format must be html or markdown")
    ledger = HomeOpsLedger.replay(events)
    snapshot = ledger.snapshot()
    issues = snapshot["issues"]
    if issue_id is not None:
        issues = [issue for issue in issues if issue["issue_id"] == issue_id]
        if not issues:
            raise ValidationError("unknown issue_id")
    selected_ids = {issue["issue_id"] for issue in issues}
    selected_actions = [action for action in snapshot["actions"] if action["issue_id"] in selected_ids]
    states = Counter(action["state"] for action in selected_actions)
    summary = {
        "schema": "homeops-relay-owner-report/v1",
        "format": output_format,
        "issue_id": issue_id,
        "included_issue_count": len(issues),
        "total_issue_count": len(snapshot["issues"]),
        "event_count": snapshot["event_count"],
        "receipt": ledger.receipt,
        "snapshot_digest": snapshot["snapshot_digest"],
        "external_effect": False,
    }
    scope = "All issues" if issue_id is None else f"One issue: {issue_id}"
    metadata = [("Scope", scope), ("Included issues", f"{len(issues)} of {len(snapshot['issues'])}"),
                ("Pending owner review", states["PENDING_OWNER_REVIEW"]),
                ("Approved, not executed", states["APPROVED_NOT_EXECUTED"]),
                ("Rejected", states["REJECTED"]), ("Journal events", snapshot["event_count"]),
                ("Journal receipt", ledger.receipt), ("Snapshot digest", snapshot["snapshot_digest"])]
    explanation = ("This handoff records observations, caller-supplied quotes, diagnostic suggestions and owner decisions. "
                   "No provider contact, scheduling, purchase or payment is executed. "
                   "Receipts and the snapshot digest identify the complete retained journal at export time, including when one issue is selected.")
    blocks = [("paragraph", explanation), ("fields", metadata)]
    if not issues:
        blocks.append(("paragraph", "No issues have been recorded."))
    blocks.extend(_blocks(ledger, snapshot, issues))
    if output_format == "markdown":
        lines = ["# HomeOps owner handoff", ""]
        for kind, value in blocks:
            if kind == "issue":
                lines.extend([f"## {_markdown_text(value[1])}", ""])
            elif kind in {"heading", "subheading"}:
                lines.extend([f"{'###' if kind == 'heading' else '####'} {_markdown_text(value)}", ""])
            elif kind == "fields":
                for label, text in value:
                    lines.extend([f"**{label}:** {_markdown_text(text)}", ""])
            elif kind in {"list", "ordered"}:
                for index, text in enumerate(value, 1):
                    prefix = f"{index}." if kind == "ordered" else "-"
                    lines.append(f"{prefix} {_markdown_text(text)}")
                lines.append("")
            else:
                lines.extend([_markdown_text(value), ""])
        return "\n".join(lines), summary

    def html_text(value: Any) -> str:
        return escape(str(value)).replace("\n", "<br>")

    parts = ['<!doctype html><html lang="en"><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             '<title>HomeOps owner handoff</title>',
             '<style>body{font:16px/1.55 system-ui,sans-serif;color:#172b36;background:#f3f6f7;margin:0}'
             'main{max-width:960px;margin:auto;padding:2rem}h1,h2,h3,h4{line-height:1.25}'
             'h2{border-top:3px solid #26747d;padding-top:1.5rem;margin-top:2.5rem}'
             'h4{margin-bottom:.6rem}dl{display:grid;grid-template-columns:minmax(9rem,1fr) 3fr;gap:.4rem 1rem;'
             'background:white;padding:1rem;border-radius:.5rem}dt{font-weight:650}dd{margin:0;overflow-wrap:anywhere}'
             'li{margin:.45rem 0}a{color:#145d68}nav{padding:1rem;background:#e1eff1;border-radius:.5rem}'
             '@media(max-width:600px){main{padding:1rem}dl{display:block}dd{margin-bottom:.8rem}}'
             '@media print{body{background:white}main{max-width:none;padding:0}nav{display:none}h2,h3,h4{break-after:avoid}dl{break-inside:avoid}}'
             '</style><main><h1>HomeOps owner handoff</h1>']
    if issues:
        parts.append('<nav aria-label="Issues"><strong>Issues in this handoff</strong><ul>')
        for position, issue in enumerate(issues, 1):
            parts.append(f'<li><a href="#issue-{position}">{html_text(issue["title"])}</a></li>')
        parts.append('</ul></nav>')
    for kind, value in blocks:
        if kind == "issue":
            parts.append(f'<h2 id="{value[0]}">{html_text(value[1])}</h2>')
        elif kind in {"heading", "subheading"}:
            tag = "h3" if kind == "heading" else "h4"
            parts.append(f'<{tag}>{html_text(value)}</{tag}>')
        elif kind == "fields":
            parts.append('<dl>' + ''.join(f'<dt>{label}</dt><dd>{html_text(text)}</dd>' for label, text in value) + '</dl>')
        elif kind in {"list", "ordered"}:
            tag = "ol" if kind == "ordered" else "ul"
            parts.append(f'<{tag}>' + ''.join(f'<li>{html_text(text)}</li>' for text in value) + f'</{tag}>')
        else:
            parts.append(f'<p>{html_text(value)}</p>')
    parts.append('</main></html>')
    return "\n".join(parts) + "\n", summary
