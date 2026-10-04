# HomeOps Relay — Alexa+ MCP for the Amazon Build, Ship, Shape Hackathon

HomeOps Relay turns a spoken household problem into an evidence-linked maintenance case, deterministic diagnostic plan, quote comparison, and **owner-gated** action proposal. It is designed for the Alexa+ track as a self-hosted Model Context Protocol server using **MCP protocol version `2025-11-25` over Streamable HTTP**.

The differentiator is not another single-turn home-maintenance chatbot. HomeOps Relay maintains a tamper-evident state chain across sessions/workflows and separates three things agents often blur together: *what the household observed*, *what a provider claimed*, and *what an owner actually authorized*. Contacting a provider, scheduling, purchasing, warranty filing, payment, or any other real-world side effect is permanently outside this demo server; the MCP surface can create and review proposals, not execute them.

## Competition fit

Checked against the [official Amazon/Devpost rules](https://amazonappdev2026.devpost.com/rules) on **2026-10-03 UTC**:

- Submission deadline: **2026-10-23 12:00 PM Pacific**.
- Alexa+ accepts a working Agent Skill or a **self-hosted MCP server implementing spec `2025-11-25` or later over Streamable HTTP**. The rules also allow a clearly labelled simulated Alexa+ experience.
- Submit functional source through a public licensed repository or the rules' private judge-sharing option, plus a working demo, a public video under three minutes, and product feedback. This repository uses the public-source route.
- Alexa+ track cash prizes are **$25,000 / $15,000 / $4,000**; a qualifying primary-track project can also compete for the **$5,000 Open Source** mini challenge.
- Judging emphasizes technical implementation, design, potential impact, and quality of the idea.

The planning snapshot and primary-source links are in [`RULES_SNAPSHOT.md`](RULES_SNAPSHOT.md). Nothing in this repository is a registration, submission, eligibility, award, or payment claim.

## Architecture

```text
Alexa+ / MCP client
       |
       | JSON-RPC 2.0 over POST /mcp
       v
+----------------------+      +--------------------------+
| Streamable HTTP MCP  | ---> | HomeOps deterministic    |
| protocol 2025-11-25  |      | event / receipt ledger   |
+----------------------+      +--------------------------+
                                        |
             +--------------------------+--------------------------+
             |                          |                          |
        issue intake               quote intake              plan + action
      observations only       caller-supplied/unverified      proposals only
                                                                   |
                                                        PENDING_OWNER_REVIEW
                                                                   |
                                                        APPROVED_NOT_EXECUTED
```

The hash chain is replayable: each event binds its sequence, semantic kind, exact payload, and predecessor receipt. `HomeOpsLedger.verify_events()` reconstructs the state and fails on mutation, reordering, unknown semantics, duplicate IDs, non-integer money, or invalid transitions.

An optional SQLite journal now retains commands, their original responses and the same domain events across process restarts. It reconstructs state through the existing ledger. A mutation returns success only after its transaction commits. Concurrent processes using the same local database serialize writes, while each read uses one consistent database snapshot. Without durable configuration, the original in-memory library and server mode remain available.

## MCP tools

| Tool | Purpose | External effect |
| --- | --- | --- |
| `homeops.intake_issue` | Capture issue, severity, area, detail, evidence refs | none |
| `homeops.record_quote` | Record caller-supplied provider quote in integer minor units | none |
| `homeops.propose_plan` | Create deterministic diagnostic + quote comparison plan | none |
| `homeops.request_action` | Create provider/schedule/purchase/warranty proposal | none |
| `homeops.record_owner_decision` | Record approval/rejection evidence | **still none** |
| `homeops.snapshot` | Return state + tamper-evident receipt | none |

## Run locally

The original in-memory mode requires Python 3.10+ and the standard library only. The optional SQLite journal requires Python 3.11+ for the connection's runtime size-limit API; unsupported durable startup reports a contained error before creating a database.

```bash
git clone https://github.com/woahwhattheheck/homeops-mcp.git
cd homeops-mcp
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
python -m homeops_relay.demo
python -m homeops_relay.simulation
python -m homeops_relay.mcp_server
```

### Local simulated Alexa+ experience

Run `python -m homeops_relay.simulation`, then open `http://127.0.0.1:8765`. The clearly labelled browser experience exercises the real `Dispatcher` and `HomeOpsLedger` through a fictional kitchen-leak story: evidence intake, two synthetic quotes, a deterministic plan, a provider-contact proposal, an explicit owner approve/reject choice, and a replay-verifiable receipt.

The action must stop at `PENDING_OWNER_REVIEW`. Approval becomes `APPROVED_NOT_EXECUTED`; rejection becomes `REJECTED`. Neither path contacts a provider, books a visit, purchases anything, or pays anyone. For a bounded non-interactive source check, run:

```bash
python -m homeops_relay.simulation --smoke
```

#### Relationship to the existing Hearthline entry

The owner also has a separate Hearthline Alexa+ project. Hearthline's browser simulator demonstrates routine versus irreversible mission execution, unknown-outcome reconciliation, idempotent command replay, and a prepared-not-purchased shopping path. HomeOps Relay is narrower and differently grounded: it keeps a maintenance case ledger that separates household observations, synthetic provider quotes, diagnostic recommendations, and owner decisions. It has no provider-write or execution path; approval remains `APPROVED_NOT_EXECUTED`.

Because the competition requires multiple entries to be unique and substantially different, the entrant must either select one project or ensure the final HomeOps story, video, feedback, and submission preserve this distinct maintenance-evidence/quote-provenance scope. This repository does not establish that organizer decision.

The server binds `127.0.0.1:8000` by default. Its MCP endpoint is `http://127.0.0.1:8000/mcp`; health is `/healthz`. It implements the `2025-11-25` handshake lifecycle: successful `initialize` returns a cryptographically random `MCP-Session-Id`; the client sends `notifications/initialized`; subsequent calls require both that session ID and `MCP-Protocol-Version: 2025-11-25`. POST transport requests must advertise both `application/json` and `text/event-stream` in `Accept`, as required by Streamable HTTP. This implementation chooses JSON responses and intentionally returns 405 to the optional GET/SSE listener.

For an intentional remote deployment, set `HOMEOPS_HOST=0.0.0.0` together with `HOMEOPS_ALLOW_REMOTE_BIND=1`, terminate TLS/authentication in a trusted production reverse proxy, and explicitly set `HOMEOPS_ALLOWED_ORIGINS` for browser origins. The handler rejects non-local `Origin` headers by default, caps request bodies, rejects duplicate JSON keys/non-finite numbers, rate-limits tool calls per session, and serializes append-only ledger mutation across concurrent HTTP workers.

## Demo story

### Retain history across restarts

With Python 3.11 or newer, choose a new database path inside an existing local directory:

```sh
HOMEOPS_DB_PATH=/tmp/homeops-demo.sqlite python -B -m homeops_relay.mcp_server
```

Restart with the same path to recover the retained journal. `HOMEOPS_DB_PATH` applies to the command-line server; library callers use `make_server(..., durable_path=...)` or `Dispatcher(durable_path=...)` explicitly. HTTP sessions are still process-local: initialize a fresh session after a restart. Session IDs are not durable operation IDs.

The configured `tools/list` schemas require `operation_id` for `homeops.intake_issue`, `homeops.record_quote`, `homeops.request_action` and `homeops.record_owner_decision`. For example, add `"operation_id": "drawer-intake-001"` to a fictional intake's arguments. Read-only `snapshot` and `propose_plan` retain their original arguments. An operation ID is 1–128 ASCII letters, digits, dots, underscores, colons or hyphens, beginning with a letter or digit.

Retain each mutation's operation ID and exact argument values. Retrying the same tool and canonical JSON arguments returns its original committed response, including its historical receipt, without another event. Reusing that ID with different content returns an error. An omitted default and an explicitly supplied default are different requests; JSON object key order is immaterial. To inspect the latest state after a retry, call `homeops.snapshot`.

If the commit result is uncertain, the MCP tool error includes `storage_error: "UncertainCommitError"` and `retry_with_same_operation_id: true`. A lost HTTP response can likewise follow a committed operation. Retry the identical request with the same ID; an interruption alone does not establish rollback. The journal does not execute the external actions described in a proposal or recorded decision.

Use the operator commands to inspect, export or copy a consistent database:

```sh
python -B -m homeops_relay.journal_cli inspect /tmp/homeops-demo.sqlite
python -B -m homeops_relay.journal_cli export /tmp/homeops-demo.sqlite --output /tmp/new-homeops-events.json
python -B -m homeops_relay.journal_cli report /tmp/homeops-demo.sqlite --output /tmp/new-homeops-handoff.html
python -B -m homeops_relay.journal_cli report /tmp/homeops-demo.sqlite --format markdown --output /tmp/new-homeops-handoff.md
python -B -m homeops_relay.journal_cli backup /tmp/homeops-demo.sqlite --output /tmp/new-homeops-backup.sqlite
python -B -m homeops_relay.journal_cli restore /tmp/new-homeops-backup.sqlite --output /tmp/new-homeops-restored.sqlite
```

Backup and restore retain the command/response retry history; the event export is for inspection and domain replay, and is not a replacement for a full journal backup. Destinations must be new. Use a local filesystem with working SQLite locking and keep the database and its transient journal files together while a process is running. Do not copy a live database file with a plain filesystem copy. The database and backups retain the supplied text in plaintext; the demonstration uses fictional records.

`report` creates a portable owner handoff from one validated event sequence. Open the self-contained HTML locally or print it, or use Markdown in a case note. Each issue includes its observations and evidence references, the canonical diagnostic plan, quotes with their exact scope/source/currency, and action proposals with pending or recorded owner decisions and decision evidence notes. Amounts remain integer minor units; the report does not assume currency precision or equate different quote scopes. Approval remains `APPROVED_NOT_EXECUTED`.

Use `--issue-id ISS-...` with an exact ID from `export` to share one issue. The displayed receipt and snapshot digest still identify the complete journal read, and the report states its issue scope. The command prints those identities and included counts as JSON. Reports contain supplied household text in plaintext, retain evidence references without fetching them, add no domain events or operations, and are not backups. HTML has no scripts or remote resources.

Even inspection needs a writable database and directory so SQLite can recover an interrupted transaction. Logical read commands do not add domain events or operations. A process crash before commit can leave a rollback journal; keep it with the database and let the adapter perform SQLite recovery rather than deleting it.

The completed fictional restart/retry/backup journey, actual execution and storage limits are documented in [JOURNAL_OPERATOR_GUIDE.md](JOURNAL_OPERATOR_GUIDE.md) and [JOURNAL_EXECUTION.md](JOURNAL_EXECUTION.md). Each accepted normal and optimized rehearsal used three real server processes, 25 HTTP exchanges and ten CLI commands. The independent full suite passed all 79 methods in both modes: 36 original tests and 43 additional storage/server tests. [JOURNAL_TEST_EXECUTION.md](JOURNAL_TEST_EXECUTION.md) retains the complete logs and tested source identities, including actual interrupted-write recovery and concurrent-process checks. These results are local execution, not hosted-CI or Alexa acceptance.

This feature completes [the existing durable-journal issue #2](https://github.com/woahwhattheheck/homeops-mcp/issues/2), preserving Z-Obsidian-6F2C's design and the original HomeOps product and competition lineage.

### Original in-memory demonstration

`python -m homeops_relay.demo` runs an entirely synthetic kitchen-leak flow:

1. record a leak observation and evidence references;
2. record two synthetic quotes;
3. produce an evidence-linked plan;
4. request a provider-contact action without executing it;
5. export a deterministic snapshot and verify the full event chain.

The submission storyboard in [`DEVPOST_SUBMISSION.md`](DEVPOST_SUBMISSION.md) turns the same flow into a voice-first <3 minute demo without inventing Alexa runtime evidence before an actual deployment exists.

## Truth / authority ceiling

- No provider contact, booking, purchase, payment, claim filing, account mutation, or home-system control is implemented.
- A recorded quote is explicitly `CALLER_SUPPLIED_UNVERIFIED`.
- `APPROVE` means `APPROVED_NOT_EXECUTED`; it does not authorize or prove an external side effect.
- MCP transport hardening is part of the product: lifecycle/session checks, protocol-version pinning, Origin validation, request limits, per-session tool-call limiting, and deterministic JSON-only responses.
- No AWS/Alexa/Devpost credential is stored here.
- Final entrant identity, eligibility, Devpost registration, live Alexa+ integration, deployment, video, and submission remain separate owner/account actions.

## License

HomeOps Relay is licensed under Apache-2.0; see [`LICENSE`](LICENSE).
