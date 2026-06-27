# Soge.dk MCP server

Give your AI agent direct access to Danish open data — **vehicles** (DMR/Motorregister) and
**companies** (CVR/Virk) — through the [Model Context Protocol](https://modelcontextprotocol.io).

It's a thin async wrapper over the public [Soge API](https://soge.dk/api/v1/docs). Your
`X-API-KEY` authenticates every call, so **the same key and plan meter both REST and MCP usage**.

## Install

Requires Python ≥ 3.10.

```bash
pip install soge-mcp          # from PyPI (once published)
# or from a checkout:
pip install /path/to/mcp_server
```

This installs a `soge-mcp` command.

Get an API key at **https://soge.dk/pricing** (free tier available).

## Configure your client

### Claude Desktop — `claude_desktop_config.json`
(macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "soge": {
      "command": "soge-mcp",
      "env": { "SOGE_API_KEY": "your_key_here" }
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add --transport stdio --env SOGE_API_KEY=your_key_here soge -- soge-mcp
```

### Cursor — `.cursor/mcp.json`

```json
{
  "mcpServers": {
    "soge": {
      "command": "soge-mcp",
      "env": { "SOGE_API_KEY": "your_key_here" }
    }
  }
}
```

Restart the client; the **soge** tools appear.

## Tools

| Tool | Plan | What it does |
|------|------|--------------|
| `search_vehicle(identifier)` | any | Vehicle by plate or VIN — specs, fuel/EV, green tax, status |
| `search_company(query, page, size)` | any | CVR/Virk company search by number, name or free text |
| `companies_at_address(vejkode, husnr, postnr)` | any | Companies registered at an address |
| `check_health()` | none | API health probe (no key needed) |
| `vehicle_inspections(identifier)` | **paid** | Official syn history: odometer, defects, station, PDFs |
| `vehicle_insurance(identifier)` | **paid** | Insurer + status + history + block/seizure flag |
| `vehicle_odometer(vin)` | **paid** | Odometer history + rollback-fraud detection |
| `vehicle_recalls(identifier)` | **paid** | Safety recalls matched to make/model |
| `company_ownership(cvr)` | **paid** | Ownership / control graph |
| `company_financials(cvr)` | **paid** | Annual-report figures, 2-year comparison |
| `person_companies(enheds_nummer)` | **paid** | Every company a person is involved in |
| `person_bankruptcies(enheds_nummer)` | **paid** | Serial-bankruptcy radar |

Premium tools return a clear "requires a paid plan" message on the free tier.

## Hosting it remotely (optional)

```bash
SOGE_MCP_TRANSPORT=streamable-http SOGE_MCP_HOST=0.0.0.0 SOGE_MCP_PORT=8000 soge-mcp
# serves the MCP endpoint at http://<host>:8000/mcp
```

## Environment variables

| Var | Default | Purpose |
|-----|---------|---------|
| `SOGE_API_KEY` | — | Your API key (required for data tools) |
| `SOGE_API_BASE` | `https://soge.dk` | API origin |
| `SOGE_MCP_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `SOGE_MCP_HOST` / `SOGE_MCP_PORT` | `127.0.0.1` / `8000` | streamable-http bind |

## License

MIT
