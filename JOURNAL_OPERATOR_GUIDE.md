# HomeOps durable journal operator guide

The optional SQLite journal retains HomeOps events and operation IDs across server restarts. Durable mode, the journal CLI and the journal rehearsal require **Python 3.11 or newer**, including SQLite connection limit support. The original ephemeral server retains its Python 3.10 minimum. The original domain engine and proposal-only behavior remain in place. A recorded owner `APPROVE` still produces `APPROVED_NOT_EXECUTED`; it does not contact a provider or execute a purchase, visit or payment. Original project authorship remains in the repository history and existing source.

## Start with durable storage

From the repository directory, use an explicit database path:

```sh
HOMEOPS_DB_PATH=/tmp/homeops-example.sqlite python -B -m homeops_relay.mcp_server
```

Without `HOMEOPS_DB_PATH`, the existing in-memory server mode remains available. Its records do not survive process termination. Durable storage does not preserve HTTP sessions: after restarting, initialize a new MCP session and send the initialized notification before making tool calls. The existing protocol and transport lifecycle still apply.

In durable mode, each of the four mutating tools requires an `operation_id`: `homeops.intake_issue`, `homeops.record_quote`, `homeops.request_action` and `homeops.record_owner_decision`. Use 1–128 ASCII characters matching `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}`. Supply the same ID and the same tool arguments when retrying an operation. An exact retry returns its original domain response, including its historical receipt, without adding an event. Reusing that ID with changed arguments is a conflict. Read-only tools do not accept operation IDs.

The current journal receipt can be newer than the receipt in a retried historical response. Read `homeops.snapshot` to obtain the current state. If a storage error explicitly reports `retry_with_same_operation_id: true`, retain the original request and ID when retrying; inventing a new ID would describe a new operation.

## Inspect, export, back up and restore

These commands operate on an existing valid journal. Input inspection never creates a missing database. Output paths must be new, and their parent directories must already exist.

```sh
python -B -m homeops_relay.journal_cli inspect /tmp/homeops-example.sqlite
python -B -m homeops_relay.journal_cli export /tmp/homeops-example.sqlite --output /tmp/homeops-events.json
python -B -m homeops_relay.journal_cli backup /tmp/homeops-example.sqlite --output /tmp/homeops-backup.sqlite
python -B -m homeops_relay.journal_cli restore /tmp/homeops-backup.sqlite --output /tmp/homeops-restored.sqlite
```

| Command | Retained information and use |
|---|---|
| `inspect` | Validated journal schema, event count, operation count, current event receipt and snapshot digest |
| `export` | One coherent event sequence and the domain snapshot reconstructed from those events; suitable for reading and original-engine replay |
| `backup` | Validated SQLite copy containing both domain events and operation IDs with their retained responses |
| `restore` | Validates an existing backed-up journal and copies it to a new SQLite destination, preserving retry behavior |

The JSON event export is **not a durable retry-journal backup**. It declares `retry_operations_included: false` and `restore_supported: false`. Replaying its domain events cannot recover operation IDs or their original retry responses. Use a SQLite backup for the restore command.

Restore writes a separate database. To use it, stop the old server and start a server with `HOMEOPS_DB_PATH` pointing to that new file; then initialize a new MCP session. Retain the original and backup when evaluating a restore. No automatic switch of a running server is performed by the CLI.

Successful commands print JSON and exit 0. Validation, storage and output failures print a contained error and exit 2. Existing output files are preserved. An interrupted export can leave a newly created partial file; its existence alone does not prove successful completion, so retain the command result. Prefer the SQLite backup workflow for retry recovery.

Receipts and snapshot digests describe logical state. A backup's SQLite file bytes need not equal the live database's bytes, especially when a live database has journal files. Compare validated counts, receipt and snapshot digest through `inspect`; do not infer that a copied event export preserves durable operations.

## Run the fictional process rehearsal

Use Python 3.11 or newer and choose a new output directory for each mode:

```sh
python -B -m homeops_relay.rehearse_journal --output-dir /tmp/homeops-rehearsal-normal
python -B -O -m homeops_relay.rehearse_journal --output-dir /tmp/homeops-rehearsal-optimized
```

The scenario supplies a fictional sticking-drawer observation and a fictional unverified quote, proposes provider contact, and records an owner decision without executing it. It stops and restarts the actual loopback server process, retries all four operations, submits one changed retry, backs up and restores the journal, restarts from the restored database, retries the decision and appends one new fictional issue. It also checks that the original and backup remain at the earlier state and that rejected output overwrites preserve retained bytes. The supplied quote amount is a fictional record value, not an estimate or recommendation.

The output retains server commands and logs, CLI argument vectors/stdout/stderr/exits, and HTTP request/response bodies. Session header values are not retained; records indicate whether session headers were sent or received. `rehearsal.json` is written only after the expected results have been observed. Failed runs can leave logs and partial artifacts without that completion record. The script terminates only the server child processes it starts.

[JOURNAL_EXECUTION.md](JOURNAL_EXECUTION.md) records the actual accepted results and source identities. This local process rehearsal does not claim Alexa integration, browser behavior, remote deployment, hosted CI, provider contact or external execution.
