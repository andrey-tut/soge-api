# Soge.dk API & MCP — Danish open data for developers and AI agents

[![API docs](https://img.shields.io/badge/docs-Swagger%20UI-2563eb)](https://andrey-tut.github.io/soge-api/)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.0.3-6ba539?logo=openapiinitiative&logoColor=white)](./openapi.yaml)
[![MCP](https://img.shields.io/badge/MCP-server-1a1a1a?logo=anthropic&logoColor=white)](#mcp-server-for-ai-agents)
[![Free tier](https://img.shields.io/badge/free%20tier-100%20calls%2Fmo-22c55e)](https://soge.dk/pricing)
[![License](https://img.shields.io/badge/examples-MIT-blue)](./LICENSE)

One REST API for Danish public data — **vehicles** (DMR / Motorregister), **companies**
(CVR / Virk), **addresses** (DAWA-compatible) and **phone** lookups. Plus an
[**MCP server**](#mcp-server-for-ai-agents) so AI agents (Claude, Cursor, …) can query the same
data directly.

> 📖 **Interactive docs (Swagger UI):** https://andrey-tut.github.io/soge-api/
> This repo holds the public OpenAPI spec, client examples and the MCP server. The backend code is
> private — nothing here exposes server internals.

## Quick start

1. Get an API key (free tier, no card): **https://soge.dk/pricing**
2. Send it in the `X-API-KEY` header.

```bash
export SOGE_API_KEY=your_key

# Health — no key required
curl https://soge.dk/api/v1/health

# Vehicle by plate or VIN
curl -H "X-API-KEY: $SOGE_API_KEY" https://soge.dk/api/v1/vehicles/AB12345

# Company search by CVR / name / text
curl -H "X-API-KEY: $SOGE_API_KEY" "https://soge.dk/api/v1/companies/novo%20nordisk?size=5"
```

Runnable examples: [`examples/`](./examples) — [curl](./examples/curl.sh) ·
[Python](./examples/python_example.py) · [JavaScript](./examples/javascript_example.js).

## Endpoints

Base URL: `https://soge.dk/api/v1` · Auth: `X-API-KEY` header · full spec: [`openapi.yaml`](./openapi.yaml)

| Method & path | Plan | Description |
|---|---|---|
| `GET /health` | none | Service health (no key) |
| `GET /vehicles/{identifier}` | free | Vehicle by plate or VIN — specs, fuel/EV, green tax, status |
| `GET /companies/{query}` | free | Company search by CVR / name / text (`page`, `size`) |
| `GET /companies-at-address` | free | Companies at an address (`vejkode`, `husnr`, `postnr`) |
| `GET /koretoj/{identifier}/inspections` | **paid** | Inspection (syn) history: odometer, defects, station, PDFs |
| `GET /koretoj/{identifier}/insurance` | **paid** | Insurer, status, history, block/seizure flag |
| `GET /koretoj/{vin}/odometer` | **paid** | Odometer history + rollback-fraud detection |
| `GET /koretoj/{identifier}/recalls` | **paid** | Safety recalls matched to make/model |
| `GET /cvr/{cvr}/ownership` | **paid** | Ownership / control graph |
| `GET /cvr/{cvr}/financials` | **paid** | Annual-report figures, 2-year comparison |
| `GET /cvr/person/{enhedsNummer}/companies` | **paid** | Every company a person is involved in |
| `GET /cvr/person/{enhedsNummer}/bankruptcies` | **paid** | Serial-bankruptcy radar |

Errors use `{ "error": "...", "code": <int> }`. Rate limits are tiered by plan (`429` on excess).

## MCP server for AI agents

Give Claude / Cursor / any [MCP](https://modelcontextprotocol.io) client direct access to this data.
The MCP server is a thin wrapper over the REST API above — **the same `X-API-KEY` and plan meter both**.

```bash
pip install soge-mcp          # see ./mcp for source
```

**Claude Code:**
```bash
claude mcp add --transport stdio --env SOGE_API_KEY=your_key soge -- soge-mcp
```

**Claude Desktop / Cursor** (`claude_desktop_config.json` / `.cursor/mcp.json`):
```json
{ "mcpServers": { "soge": { "command": "soge-mcp", "env": { "SOGE_API_KEY": "your_key" } } } }
```

Tools: `search_vehicle`, `search_company`, `companies_at_address`, `check_health` (free) and
`vehicle_inspections`, `vehicle_insurance`, `vehicle_odometer`, `vehicle_recalls`,
`company_ownership`, `company_financials`, `person_companies`, `person_bankruptcies` (paid).
Full setup & options: [`mcp/README.md`](./mcp).

## Links

- Interactive docs (Swagger UI): https://andrey-tut.github.io/soge-api/
- Pricing & API keys: https://soge.dk/pricing
- Website: https://soge.dk
- `llms.txt`: https://soge.dk/llms.txt

## License

Client examples, the OpenAPI spec and the MCP server in this repo are **MIT** (see [LICENSE](./LICENSE)).
The underlying data is sourced from official Danish registries (DMR, CVR) and served via soge.dk.
