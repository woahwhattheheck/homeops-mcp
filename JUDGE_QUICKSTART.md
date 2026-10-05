# HomeOps Relay — judge quickstart

This is a compact, account-free path through the rules-permitted simulated Alexa+ experience. It uses fictional household data, binds only to loopback, and performs no provider contact, booking, purchase or payment.

## 60-second source check

Requirements: Git and Python 3.10 or newer. The simulation uses the Python standard library and requires no package installation.

```sh
git clone https://github.com/woahwhattheheck/homeops-mcp.git
cd homeops-mcp
python -B -m homeops_relay.simulation --smoke
```

The command prints one JSON object. Verify these stable fields:

```json
{
  "action_state": "APPROVED_NOT_EXECUTED",
  "event_count": 5,
  "external_effect": false,
  "receipt": "<64 lowercase hexadecimal characters>",
  "verified": true
}
```

The receipt value identifies that run and is not expected to be a fixed constant. A zero exit plus the fields above shows that the actual dispatcher accepted the fictional issue and quotes, stopped provider contact for owner review, recorded approval without execution, replayed the five-event chain and verified its receipt.

## Two-minute browser walkthrough

Start the loopback-only simulator:

```sh
python -B -m homeops_relay.simulation
```

Open the printed URL, normally `http://127.0.0.1:8765`, then use the controls in order:

1. **Capture observation** — creates a fictional evidence-linked kitchen-leak case.
2. **Add two synthetic quotes** — retains provider, source, amount, scope and caller-supplied/unverified status.
3. **Build a safety-first plan** — compares the different scopes and prices without selecting a provider.
4. **Propose provider contact** — must stop at `PENDING_OWNER_REVIEW`.
5. Choose **Approve proposal** or **Reject proposal**.
   - Approve must become `APPROVED_NOT_EXECUTED`.
   - Reject must become `REJECTED`.
6. **Verify receipt** — must display `VERIFIED`, a receipt and a snapshot digest.

At the receipt stage, the page offers an HTML owner handoff and a replayable JSON event export. Neither file authorizes or proves an external action. Use **Reset fictional scenario** to run the other decision branch. Stop the local server with Ctrl-C.

A normal page refresh reads the same in-process state. The state is not durable across a process restart unless the separate SQLite journal mode is configured.

## Submission evidence map

| Review question | Repository evidence |
| --- | --- |
| Is there a working simulated experience? | `homeops_relay/simulation.py` and `homeops_relay/static/simulation.html` |
| Is the simulation a real source path rather than a canned video? | The browser calls the real `Dispatcher` and `HomeOpsLedger`; the smoke path exercises the same session code |
| Is there a completed demo? | `docs/demo/2026-10-04/homeops-simulation.mp4` |
| Is the demo under three minutes and in English? | `docs/demo/2026-10-04/manifest.json`: 97.68 seconds, English captions, silent audio |
| Can the recording be audited? | Transcript, SRT, source pin, screenshots, 14 loopback interactions and file hashes are in `docs/demo/2026-10-04/` |
| Are approve and reject both demonstrated? | Recording manifest retains verified five-event chains for both branches |
| Does approval execute anything? | No. The state is `APPROVED_NOT_EXECUTED`; every external-effect authority field remains false |
| Is there an MCP implementation? | `homeops_relay/mcp_server.py`, implementing protocol `2025-11-25` over Streamable HTTP |
| Is durable history available? | `homeops_relay/storage.py`, `JOURNAL_OPERATOR_GUIDE.md`, `JOURNAL_EXECUTION.md` and `JOURNAL_TEST_EXECUTION.md` |
| Are setup and submission fields available? | `README.md`, `DEVPOST_SUBMISSION.md` and `SUBMISSION_FIELDS.md` |
| Is the project licensed? | Public Apache-2.0 `LICENSE` detected by GitHub |

## Optional focused verification

Run the repository's maintained unit tests:

```sh
python -B -m unittest discover -s tests -v
python -B -O -m unittest discover -s tests -v
```

The retained source-bound execution record reports 79 passing tests in both normal and optimized modes on Python 3.12.14 at the documented historical pins. The commands above are for a fresh reviewer run; this quickstart does not claim that writing documentation reran them.

For the durable restart/retry/backup journey, follow `JOURNAL_OPERATOR_GUIDE.md`. For the full MCP transport setup and security boundaries, follow `README.md`.

## Truth and submission boundary

| Item | Current evidence |
| --- | --- |
| Local simulated Alexa+ experience | Implemented and recorded |
| Public YouTube/Vimeo URL | Still requires the existing authorized uploader |
| Live Alexa+ device/account integration | Not demonstrated |
| Public remote MCP endpoint | Not deployed |
| Provider contact, booking, purchase or payment | Not implemented or performed |
| Devpost registration, terms acceptance and submission | Entrant-only external actions |
| Eligibility or substantially-different ruling | Not established by this repository |
| Prize, award or payment | None claimed |

This file is judge-facing repository documentation. It is not a contest entry, an acceptance of rules, a testing credential, a deployment, or evidence of an award.
