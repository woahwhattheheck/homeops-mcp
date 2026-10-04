# HomeOps Relay — submission / demo packet

This is a **ready-to-fill** packet. It is not proof that the project has been joined to Devpost or submitted.

## One-line pitch

**HomeOps Relay gives Alexa+ an evidence-aware household maintenance memory: it captures what happened, compares repair options without laundering vendor claims into truth, and turns next steps into tamper-evident owner-gated action proposals.**

## Why it is not a basic MCP wrapper

A household problem evolves across hours or days: symptoms change, quotes arrive from different providers, and the high-risk step is often not answering a question but deciding what may happen next. HomeOps Relay provides an explicit state machine and cryptographic replay receipt instead of treating every voice turn as isolated chat context.

Core product properties:

- state persists semantically across tool calls;
- evidence, provider claims, and owner decisions are separate data classes;
- money is integer minor units, never float authority;
- quote ordering is deterministic but does not auto-select a provider;
- safety-first diagnostic plans are bounded and reviewable;
- vendor contact / scheduling / purchasing / warranty work is *proposed*, never silently executed;
- every mutation extends a replay-verifiable SHA-256 event chain.

## Suggested <3 minute demo

**0:00–0:20 — problem**  
“Alexa, there is water collecting under the kitchen sink when I run the faucet.” Show `homeops.intake_issue` creating an evidence-linked case.

**0:20–0:50 — memory + reasoning**  
Add one photo reference and two synthetic provider quotes. Ask for the plan. Show that water-specific safety/documentation steps are present and that both quotes remain marked caller-supplied/unverified.

**0:50–1:25 — agentic workflow without unsafe autonomy**  
Ask: “Contact the lower quote and get the earliest diagnostic slot.” Show `homeops.request_action` returning `PENDING_OWNER_REVIEW`, not sending anything. Explain that approval is a separate recorded event and still does not equal execution.

**1:25–1:55 — evidence receipt**  
Show `homeops.snapshot` and the current event receipt. Mutate one exported event in a terminal copy and run verification; show the hash mismatch.

**1:55–2:25 — Alexa+/MCP implementation**  
Show initialize negotiating `2025-11-25`, `tools/list`, and a live `POST /mcp` request. Mention Streamable HTTP and Origin validation.

**2:25–2:50 — impact**  
Explain the broader product: maintenance histories that survive across turns, compare options without losing provenance, and keep a human in control of expensive or safety-relevant actions.

**2:50–3:00 — close**  
“HomeOps Relay gives an ambient agent memory, provenance, and brakes — the three things a real household workflow needs after the first answer.”

## Working local browser simulation

The repository now includes a clearly labelled simulated Alexa+ experience that uses the real deterministic dispatcher and ledger instead of a canned transcript:

```bash
python -m homeops_relay.simulation
# open http://127.0.0.1:8765
```

The guided flow covers fictional kitchen-leak intake, two synthetic quotes, the plan, a contact proposal that stops at `PENDING_OWNER_REVIEW`, an owner approve or reject choice, and the replay-verifiable receipt. Approval is displayed as `APPROVED_NOT_EXECUTED`; every screen states that no provider, booking, purchase, or payment is executed. `python -m homeops_relay.simulation --smoke` exercises the same real source without a browser.

This is working local simulation evidence only. It is not a public demo video, a live Alexa+ integration, Devpost registration, rules acceptance, submission, sponsor acceptance, or prize claim.

## Final submission checklist

- [ ] Re-read current official rules and deadline.
- [ ] Devpost account has joined the correct hackathon under the intended entrant identity.
- [ ] Eligibility / team facts are truthful and complete.
- [ ] Choose and accurately demonstrate the MCP/Agent Skill route or the permitted simulated-experience route. This server's local MCP execution does not establish live Alexa+ integration or a completed simulation demo.
- [ ] For the MCP route, document the endpoint and validate it with a real MCP client. Retain non-secret runtime evidence; label any actual Alexa+ integration separately.
- [ ] Provide the exact public licensed repository or use the rules' private judge-sharing option. This project currently uses public Apache-2.0 source.
- [ ] Public English YouTube/Vimeo demo is <3 minutes.
- [ ] Description accurately distinguishes synthetic fixtures from live integration.
- [ ] Pre-existing/third-party assets, if any are later incorporated, are disclosed and license-compatible.
- [ ] Include required product feedback; add an optional friction log grounded in observed use.
- [ ] Submit exactly once, preserve provider receipt, and do not claim award/payment before organizer evidence.
