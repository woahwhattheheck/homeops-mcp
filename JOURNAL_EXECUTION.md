# HomeOps durable journal execution record

**Observed 19 September 2026:** the normal and real optimized operator rehearsals both passed on their first execution. Each run started three actual server child processes, retained 25 HTTP request/response records and executed ten journal CLI commands. No product source was changed or accepted proof rerun while writing this record.

## Actual invocation and evidence

The following top-level commands ran from `/workspace/scratch/02152e3a5897/homeops`:

```sh
python -B -m homeops_relay.rehearse_journal --output-dir /workspace/scratch/02152e3a5897/homeops-rehearsal-normal-v1
python -B -O -m homeops_relay.rehearse_journal --output-dir /workspace/scratch/02152e3a5897/homeops-rehearsal-optimized-v1
```

Both exited 0. Every child Python process inherited `-B`; every optimized-run child also received an actual `-O` argument. Child commands used `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python`. Durable operation requires Python 3.11 or newer; the original ephemeral mode retains its Python 3.10 floor. This execution is not a Python-version compatibility matrix.

| Retained completion record | SHA256 |
|---|---|
| `homeops-rehearsal-normal-v1/rehearsal.json` | `cb8efa74e0b522c96bd4332d53e73c38361c7a62d97a88b67b02cb55e73805d0` |
| `homeops-rehearsal-optimized-v1/rehearsal.json` | `cb211c200ebd4c2bf59e35af10dfdaa8b6d5e3f9384a6d644e484a4618b94cb4` |

Each run retains three `*-process.json` records with literal command, PID, working directory, environment overrides, endpoint, intentional stop request and observed exit. Server stdout/stderr are retained separately. The 25 HTTP records under `http/` include request/response bodies, status codes and whether session headers were present. Actual session tokens are not retained. The ten command records under `commands/` include full argument vectors, rendered commands, stdout, stderr and actual/expected exits, alongside the raw output files.

## Fictional journey and observed state

| Stage | Observed result in both modes |
|---|---|
| Initial process: issue, quote, contact proposal, recorded decision | Four events and four operation records. Quote remained `CALLER_SUPPLIED_UNVERIFIED`; decision state was `APPROVED_NOT_EXECUTED`. |
| Restart same journal with fresh MCP session | Current snapshot exactly equalled the original snapshot. All four exact retries returned their original payloads, including historical receipts, without adding events. |
| Retry quote operation ID with amount changed from 4500 to 4600 minor units | HTTP 200 with MCP tool error `OperationConflictError`: `operation_id already belongs to a different request`. Snapshot and event count remained unchanged. |
| Inspect, event export, SQLite backup and restore | Inspect reported four events/four operations. Event export reproduced the snapshot and explicitly excluded retry recovery. Restored SQLite journal inspection exactly matched the original. |
| Start a process on the restored journal and retry recorded decision | Same historical decision payload returned; snapshot unchanged, still four events. |
| Add one new fictional issue to the restored journal | Restored journal advanced to five events/five operations and a new receipt. Original and backup remained at the four-event state. |
| Attempt to overwrite retained backup and JSON export | Both CLI commands exited 2. Hashes of the existing backup and export were unchanged. |

The fictional drawer observation, provider label and supplied quote are demonstration records. The supplied amount is not an estimate or recommendation. No provider was contacted. All five snapshot authority fields (`external_effect`, `provider_contact`, `scheduling`, `purchase`, `payment`) remained false.

The exact original responses preserved across restart were:

| Mutation | Retained ID | State | Historical receipt |
|---|---|---|---|
| Issue intake | `ISS-0001-30d4fa6bcb` | `OPEN` | `da5535cd4545f0033bfb5975884aee5a853597c2538eaca1cf743a0469f273a8` |
| Quote record | `QTE-0002-f1fefdb10a` | `RECORDED_UNVERIFIED` | `7127a8b259521b503021ad6846be7f47f7fa2ea9954427e43f38df1c50cc4c80` |
| Action proposal | `ACT-0003-a76e2edf21` | `PENDING_OWNER_REVIEW` | `ef15b2c08f6d77016d53c2d26c24ffbe44184344c3b22e8fa549fd880fce0f47` |
| Owner decision | `ACT-0003-a76e2edf21` | `APPROVED_NOT_EXECUTED` | `707f35d835798fff80bab06fc55d025d72f90ec2735d0d85ccb3062cfb7f074f` |

Historical response receipts are expected to differ from the current four-event receipt. The retry contract preserves the response from the original operation; current state is read through the snapshot or inspect interfaces.

## Logical identities across restart and restore

| State | Events / operations | Receipt | Snapshot digest |
|---|---|---|---|
| Original and restarted | 4 / 4 | `707f35d835798fff80bab06fc55d025d72f90ec2735d0d85ccb3062cfb7f074f` | `3a2132e3ea370dc06df86d3bb8d2979fcded1d77c7fc5d91f344fbc92428737d` |
| Restored at backup point | 4 / 4 | `707f35d835798fff80bab06fc55d025d72f90ec2735d0d85ccb3062cfb7f074f` | `3a2132e3ea370dc06df86d3bb8d2979fcded1d77c7fc5d91f344fbc92428737d` |
| Restored after one new operation | 5 / 5 | `e22cf6ee511c2bc8bd67f77da58d5f451ff368b66090d53bde43cb5cfdc4486e` | `927f903e9922d2c764dcf22bcdaeefa47de82f08ca1c1582964d8ae909d4337f` |

The retained normal and optimized runs were compared after execution: original/restored/continued inspection facts, original/continued snapshots, all four original operation responses and the continued-operation response matched exactly. This is a logical-state comparison, not a claim of SQLite database-file byte equality. Each complete rehearsal record differs because it retains its own paths and optimization arguments.

## CLI results

| Command record | Normal exit | Optimized exit |
|---|---:|---:|
| `inspect-original` | 0 | 0 |
| `export-events` | 0 | 0 |
| `backup` | 0 | 0 |
| `restore` | 0 | 0 |
| `inspect-restored` | 0 | 0 |
| `inspect-original-again` | 0 | 0 |
| `inspect-backup-again` | 0 | 0 |
| `inspect-continued` | 0 | 0 |
| `backup-existing-rejected` | 2 | 2 |
| `export-existing-rejected` | 2 | 2 |

The eight successful CLI calls produced JSON. The two expected failures were existing-destination refusals. The event export had schema `homeops-relay-event-export/v1`, `retry_operations_included: false` and `restore_supported: false`. Restore used the full SQLite backup, preserving operation IDs and original responses. It did not reconstruct retry state from an event-only export.

## Exact source identities

Both operator records bind these source bytes. The original domain engine is retained.

| File | Git blob | SHA256 |
|---|---|---|
| `homeops_relay/homeops.py` | `6eb76d4bf4a1bedd211afbf715ea17018a3d7ad4` | `08848754c376e24f7bbd4b279dae918bb8468a2184078794984bebab06ea95da` |
| `homeops_relay/journal_cli.py` | `ed5c2701b25639fb2ea2e03ba7bb48f5266a34c9` | `1a1d986e6070cd902d176af94fd96842afa5ad04242bbbc3278aa55e29c51dec` |
| `homeops_relay/mcp_server.py` | `1edc1723736129beb84de348400ca3999383e92e` | `a5a2529b1c4cb0db4b426a35840d44e83c16f46813d60b0a7c1f45ea27e9a445` |
| `homeops_relay/rehearse_journal.py` | `fad9e7aa8941f787bd759f6528759c0e8e9d99bf` | `f85ed7997fff7a02bb69378cf3fa88dd9181b8c470378a1dd8335692fe679104` |
| `homeops_relay/storage.py` | `f49957091ba8bc10f2c2f4500b8fd833f29e8e2a` | `dd27ee20108f5f3ab5f7ea150e878729059aaabc98c0935af60e156da794c0d8` |

## Execution scope

The actual server processes bound loopback addresses with OS-assigned ports and followed the existing initialize/initialized lifecycle. Each was deliberately terminated after its completed HTTP checks, with recorded exit `-15` (SIGTERM); these are intentional process stops, not unexplained test failures. The restarted and restored processes created fresh sessions.

This rehearsal demonstrates persistence after those completed operations, idempotent retry behavior, coherent export, backup/restore, isolated continuation and rejected-overwrite preservation. It does not alone establish recovery from an in-flight interrupted write. [JOURNAL_TEST_EXECUTION.md](JOURNAL_TEST_EXECUTION.md) separately retains all 79 normal and 79 optimized test results, including real process interruption, hot-journal recovery and concurrent writers. Source-review evidence is separate from this operator proof. No browser, Alexa runtime, external deployment or hosted-CI success is claimed. No external household action, contact, booking, purchase or payment occurred.

The database and directory must permit SQLite rollback recovery even for logical inspection; pending journal files must be preserved. Logical read queries do not append domain events. [JOURNAL_OPERATOR_GUIDE.md](JOURNAL_OPERATOR_GUIDE.md) records exact storage bounds, timeout behavior and primary SQLite implementation references.
