# HomeOps Devpost submission fields

This is an evidence-bound drafting aid, not a submitted form or a statement that the entrant has joined the hackathon, accepted its rules, selected these categories, or confirmed eligibility. The entrant must review every field and supply their own subjective experience before using it.

Official rules rechecked **2026-10-05 UTC**: https://amazonappdev2026.devpost.com/rules

## Source-backed project facts

| Field | Verified fact |
| --- | --- |
| Project | HomeOps Relay |
| Repository | https://github.com/woahwhattheheck/homeops-mcp |
| Repository visibility | Public |
| Detected license | Apache-2.0 |
| Repository created | 2026-09-18 00:48:46 UTC, within the 2026-08-31 through 2026-10-23 submission period |
| GitHub username | `woahwhattheheck` |
| Candidate primary track | Alexa+ |
| Safest demonstrated entry path | Rules-permitted simulated Alexa+ experience |
| Recorded demo | 97.68-second local browser simulation with burned-in English captions |
| Live Alexa+ integration | Not demonstrated or claimed |
| External effects | None; provider contact, scheduling, purchase and payment remain false |

The repository also contains a self-hosted MCP implementation of protocol version `2025-11-25` over Streamable HTTP. The completed video demonstrates the simulation path, not live Alexa+ or the full MCP storyboard. Do not change the selected entry path without reconciling the final video, description and testing instructions.

## Required Product Feedback draft

The rules ask which tools, APIs and SDKs were used, what worked, what needs work, the onboarding experience, and whether the entrant would build with them again. The wording below separates observed repository facts from entrant-only judgments.

### Which developer tools, APIs and SDKs did you use, and for what?

Evidence-backed candidate wording:

> HomeOps Relay uses the open Model Context Protocol specification version 2025-11-25 over Streamable HTTP for its self-hosted tool server. The runtime is Python and the standard library; optional durable history uses Python's built-in SQLite interface. The submitted demonstration follows the rules' simulated Alexa+ path and runs the real local dispatcher and event ledger in a browser experience. Playwright, Chromium and FFmpeg were used only to capture the reproducible demo video and add its English caption band. We did not use or claim a live Alexa+ device, Alexa+ account integration, AWS runtime service, payment API or provider API.

Entrant check: remove any tool that was not part of the final submission and add any later tool, API, SDK or service actually used.

### What worked well?

Observed facts that may support the entrant's answer:

- The versioned MCP lifecycle and transport rules were concrete enough to implement a local `initialize` → `notifications/initialized` → `tools/list` / `tools/call` flow with session and protocol-version validation.
- The permitted simulation path allowed the product experience to exercise the real dispatcher and ledger without pretending that a local browser was Alexa+.
- A dependency-light Python runtime supported deterministic local tests, replay receipts and an optional durable SQLite journal.
- The completed simulation recording retained 14 loopback interactions, both decision branches and two verified five-event chains with zero browser external requests.

Entrant-only confirmation: describe what *you* found effective. Do not present the bullets above as personal experience unless they match it.

### What needs work?

Evidence-backed candidate wording:

> A concise official end-to-end example for the JSON-response form of Streamable HTTP would reduce integration ambiguity. The server had to coordinate initialization, the initialized notification, session identifiers, protocol-version headers, dual JSON/event-stream Accept negotiation and the optional GET/SSE boundary. A minimal reference client showing that complete sequence would make first implementation and conformance checking faster.

Boundary to retain:

> This project did not run on live Alexa+ or use an Amazon developer account, so it does not provide observed feedback about Alexa+ device onboarding, certification, production deployment or reliability.

Entrant check: add only limitations and workarounds personally observed; do not invent platform failures.

### How was onboarding from zero to hello world?

Evidence-backed local path:

1. Clone the public repository.
2. Run the standard-library test suite.
3. Start `python -m homeops_relay.simulation`.
4. Open the loopback URL and complete the fictional kitchen-leak walkthrough.

This describes repository onboarding, not Alexa+ account or device onboarding. The entrant must add their own experience and timing if requested.

### Would you build with these devices and services again?

Entrant-only answer required. A bounded candidate is:

> Yes for the open MCP interface and local simulated-experience workflow because they supported a stateful, testable household-maintenance flow. I did not evaluate a live Alexa+ device or production service integration, so I would not generalize this answer to those untested surfaces.

Use this only if it accurately reflects the entrant's view.

## Optional friction logs

These are source-backed observations. The entrant decides whether they are relevant enough to submit.

### Friction 1 — complete Streamable HTTP lifecycle

| Prompt | Draft |
| --- | --- |
| Task attempted | Implement and locally validate the MCP 2025-11-25 JSON-response lifecycle. |
| Steps | Initialize; preserve the returned session ID; send the initialized notification; include the session and protocol headers; negotiate both required Accept media types; call tools; treat GET/SSE as optional. |
| Expected | One compact reference sequence for a minimal JSON-only server and client. |
| Actual | The required behavior was distributed across lifecycle and transport rules, so the project assembled focused dispatcher and HTTP checks for the complete sequence. |
| Severity | Medium — implementation friction, not a runtime outage. |
| Workaround | Pin the protocol version and retain focused lifecycle, header, Origin and transport tests. |
| Actionable suggestion | Publish one official copyable JSON-response round trip that includes every header and the allowed optional-GET behavior. |

### Friction 2 — preserving an in-progress simulated walkthrough

| Prompt | Draft |
| --- | --- |
| Task attempted | Reload the local simulation page while retaining the current reviewer walkthrough and downloadable receipts. |
| Steps | Complete part of the fictional flow, refresh the browser page, then inspect the state and downloads. |
| Expected | A page reload would read the current same-process state; Reset would remain the explicit restart action. |
| Actual | The original startup path reset the scenario. |
| Severity | Medium — it could discard prepared review evidence, with no external effect or data outside the local process. |
| Workaround | Before the fix, replay the walkthrough. |
| Resolution | PR #17 added a read-only current-state endpoint and preserved Reset as the explicit restart action. |
| Actionable suggestion | Make read-versus-reset lifecycle actions explicit in simulator starter templates. |

Evidence: https://github.com/woahwhattheheck/homeops-mcp/pull/17

## Optional Open Source mini-challenge fields

The rules allow a new public open-source project made during the hackathon window alongside a primary-track submission. Category selection remains the entrant's decision.

- Contribution URL: https://github.com/woahwhattheheck/homeops-mcp
- Project repository URL: https://github.com/woahwhattheheck/homeops-mcp
- GitHub username: `woahwhattheheck`
- Detected license: Apache-2.0
- Repository creation timestamp: 2026-09-18 00:48:46 UTC
- Meaningful feature contribution: https://github.com/woahwhattheheck/homeops-mcp/pull/3
- Working simulated-experience contribution: https://github.com/woahwhattheheck/homeops-mcp/pull/10
- Reproducible captioned-demo contribution: https://github.com/woahwhattheheck/homeops-mcp/pull/12

Ready-to-edit description:

> HomeOps Relay is a new public Apache-2.0 Python project created during the hackathon window. It implements an evidence-first household-maintenance MCP server and a rules-permitted simulated Alexa+ experience. The durable-history contribution adds exact operation retries, restart recovery, concurrent-writer handling, bounded SQLite storage, backup/restore tools and focused regression coverage. The browser simulation exercises the real dispatcher and ledger rather than a canned transcript, and its reproducible 97.68-second recording retains the transcript, captions, source pin, HTTP interactions and verified receipt chains. The project matters because household maintenance unfolds across sessions and expensive decisions: it keeps observations, caller-supplied provider claims and owner authorization separate while refusing to equate approval with execution.

Entrant check: select the mini-challenge only if the final primary-track submission and ownership facts satisfy the live rules. The repository evidence does not itself establish eligibility or acceptance.

## Remaining entrant-only gates

- Choose HomeOps or confirm that HomeOps and Hearthline are unique and substantially different.
- Confirm entrant/team eligibility, representation and ownership facts.
- Confirm the final primary track and any mini challenge.
- Add personal Product Feedback judgments and any later tools actually used.
- Publish the existing video through the authorized account and verify it while signed out.
- Join, accept the rules and submit through Devpost.
- Preserve the provider receipt.

No advertised prize is awarded by preparing these fields.
