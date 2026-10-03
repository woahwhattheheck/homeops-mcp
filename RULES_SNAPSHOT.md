# Amazon Build, Ship, Shape — planning rules snapshot

Initially captured **2026-09-17 UTC**; entry-path facts refreshed from the official rules on **2026-10-03 UTC**. This planning summary does not replace the live rules.

## First-party sources

- Event overview: https://amazonappdev2026.devpost.com/
- Official rules: https://amazonappdev2026.devpost.com/rules
- Resources: https://amazonappdev2026.devpost.com/resources
- MCP documentation referenced by Amazon: https://modelcontextprotocol.io/docs/latest/getting-started/intro
- MCP 2025-11-25 Streamable HTTP: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- MCP 2025-11-25 lifecycle: https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle

## Bound facts used by HomeOps Relay

| Fact | Captured state |
| --- | --- |
| Submission period | 2026-08-31 10:15 PT → **2026-10-23 12:00 PT** |
| Format | Online / public Devpost hackathon |
| Alexa+ eligible artifact | Working Agent Skill, self-hosted MCP server, or the rules' clearly demonstrated simulated Alexa+ experience |
| MCP route floor | **2025-11-25 or later** |
| Transport | **Streamable HTTP**; this carrier implements POST JSON response mode, secure session IDs, protocol-version headers, Origin checks, and the allowed 405 response for optional GET/SSE |
| Runtime proof | Alexa+/Bee/Ring repository must actually use required track technology at runtime unless using the Alexa+ simulated-experience exception |
| Repo | Functional source/assets/instructions: public licensed GitHub repository or private repository shared with the specified judges |
| Video | Public YouTube/Vimeo, under 3 minutes; English or English translation |
| Product feedback | Required for each tool, API or SDK used; friction logs are optional |
| Alexa+ cash | $25,000 first / $15,000 second / $4,000 third |
| Mini challenge | AWS Builder $5,000 cash; Open Source $5,000 cash (subject to its rules) |
| Judging | Tech implementation, design, potential impact, quality of idea |

## Submission gates intentionally not crossed by this carrier

- Devpost Join / terms acceptance
- participant or organization eligibility attestation
- live Alexa+ or developer account access
- remote public deployment / DNS / TLS
- AWS credit request or spend
- demo video publication
- final Devpost submission
- prize, award, payment, or revenue assertion

Re-read the live rules immediately before any registration or submission action because competition terms and platform requirements can change.
