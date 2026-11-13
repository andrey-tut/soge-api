"""Soge.dk MCP server.

Exposes Denmark's vehicle (DMR/Motorregister) and company (CVR/Virk) datasets to MCP-capable
AI clients (Claude Desktop/Code, Cursor, …) as a small set of well-described tools. It is a
thin, async client over the public Soge REST API at https://soge.dk/api/v1 — authentication,
per-plan quotas and billing are all enforced server-side via your X-API-KEY. MCP traffic
self-identifies via the X-Soge-Client header and is metered on its own (smaller) monthly
quota per plan, separate from your REST quota — see https://soge.dk/pricing.

Configuration (environment variables):
  SOGE_API_KEY    your Soge API key (https://soge.dk/pricing). Required for every data tool;
                  `check_health` works without it.
  SOGE_API_BASE   API origin (default https://soge.dk).
  SOGE_MCP_TRANSPORT   "stdio" (default) or "streamable-http".
  SOGE_MCP_HOST / SOGE_MCP_PORT   bind address for streamable-http (default 127.0.0.1:8000).

Run:  soge-mcp           (stdio — the usual local install)
      SOGE_MCP_TRANSPORT=streamable-http soge-mcp     (hosted/remote)
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from urllib.parse import quote

import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from . import __version__

API_BASE = (os.environ.get("SOGE_API_BASE") or "https://soge.dk").rstrip("/")
_CLIENT_ID = f"soge-mcp/{__version__}"


@dataclass
class AppCtx:
    """Shared resources for the server's lifetime."""
    http: httpx.AsyncClient


@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[AppCtx]:
    """Open ONE pooled httpx client for the whole process (per-call clients would defeat
    connection reuse). The API key is attached here so every tool inherits it."""
    headers = {
        "Accept": "application/json",
        "User-Agent": _CLIENT_ID,
        "X-Soge-Client": _CLIENT_ID,  # backend meters MCP traffic on its own quota via this
    }
    key = (os.environ.get("SOGE_API_KEY") or "").strip()
    if key:
        headers["X-API-KEY"] = key
    async with httpx.AsyncClient(base_url=API_BASE, headers=headers, timeout=25.0) as http:
        yield AppCtx(http=http)


mcp = FastMCP(
    "soge",
    lifespan=_lifespan,
    host=os.environ.get("SOGE_MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("SOGE_MCP_PORT", "8000")),
    instructions=(
        "Danish open-data lookup: vehicles (by plate/VIN) and companies (by CVR/name), plus premium "
        "history endpoints (inspections, insurance, odometer-fraud, recalls, ownership graph, company "
        "financials, person dossiers). Use search_vehicle / search_company to find an entity, then the "
        "premium tools for depth. Premium tools need a paid Soge plan."
    ),
)


def _enc(seg: str) -> str:
    """URL-encode a single path segment (httpx does not encode path parts)."""
    return quote(str(seg).strip(), safe="")


async def _get(ctx: Context, path: str, params: dict | None = None) -> dict:
    """GET `path` on the Soge API and map HTTP failures to clean, client-visible ToolErrors."""
    http: httpx.AsyncClient = ctx.request_context.lifespan_context.http
    try:
        r = await http.get(path, params={k: v for k, v in (params or {}).items() if v is not None})
    except httpx.RequestError as e:
        raise ToolError(f"Could not reach the Soge API ({API_BASE}): {e}") from e

    if r.status_code == 401:
        raise ToolError("Invalid or missing API key. Set SOGE_API_KEY — get one at https://soge.dk/pricing")
    if r.status_code == 403:
        raise ToolError("This endpoint requires a paid Soge plan. Upgrade at https://soge.dk/pricing")
    if r.status_code == 404:
        raise ToolError("Not found in the Danish registries for that identifier.")
    if r.status_code == 429:
        retry = r.headers.get("Retry-After")
        raise ToolError(
            "Rate limit / quota exceeded on your plan"
            + (f" — retry after {retry}s." if retry else ". Try again shortly or upgrade your plan.")
        )
    if r.status_code >= 400:
        msg = None
        try:
            msg = ((r.json() or {}).get("error") or {}).get("message")
        except Exception:
            pass
        raise ToolError(msg or f"Soge API error (HTTP {r.status_code}).")
    try:
        return r.json()
    except Exception as e:
        raise ToolError("Soge API returned a non-JSON response.") from e


# ───────────────────────── Core lookups (all plans) ─────────────────────────

@mcp.tool()
async def search_vehicle(identifier: str, ctx: Context) -> dict:
    """Look up a Danish vehicle by registration number (license plate, e.g. "AB12345") or VIN
    (stelnummer). Returns the full record: make/model/variant, first registration, technical
    specs, fuel/EV data, green owner-tax, colour, status and a kilometre/inspection summary.
    Use this first; then the premium vehicle_* tools for inspection/insurance/odometer history."""
    return await _get(ctx, f"/api/v1/vehicles/{_enc(identifier)}")


@mcp.tool()
async def search_company(query: str, ctx: Context, page: int = 1, size: int = 20) -> dict:
    """Search Danish companies in the CVR/Virk register by CVR number, company name, or free text.
    Returns paginated hits with CVR, name, status (active/closed/bankrupt), industry and address.
    `size` is capped at 100. Use company_financials / company_ownership for paid deep data."""
    return await _get(ctx, f"/api/v1/companies/{_enc(query)}",
                      {"page": max(page, 1), "size": min(max(size, 1), 100)})


@mcp.tool()
async def companies_at_address(vejkode: str, husnr: str, postnr: str, ctx: Context,
                               kommunekode: str | None = None) -> dict:
    """Companies registered at a structured Danish address (vejkode + husnr + postnr, optional
    kommunekode). Returns each company with a deep-link to its Soge profile."""
    return await _get(ctx, "/api/v1/companies-at-address",
                      {"vejkode": vejkode, "husnr": husnr, "postnr": postnr, "kommunekode": kommunekode})


@mcp.tool()
async def check_health(ctx: Context) -> dict:
    """Check that the Soge API is reachable and healthy. No API key required."""
    return await _get(ctx, "/api/v1/health")


# ───────────────────────── Premium "moat" tools (paid plan) ─────────────────────────

@mcp.tool()
async def vehicle_inspections(identifier: str, ctx: Context) -> dict:
    """[Paid plan] Official inspection (syn) history for a vehicle (plate or VIN): exact odometer
    per inspection, pass/fail conclusion, defect codes, inspecting station, plus PDF/photo URLs.
    Source: eSyn / Færdselsstyrelsen."""
    return await _get(ctx, f"/api/v1/koretoj/{_enc(identifier)}/inspections")


@mcp.tool()
async def vehicle_insurance(identifier: str, ctx: Context) -> dict:
    """[Paid plan] Current insurer + Aktiv/Ophørt status, full insurance history, and any
    block/seizure flag for a vehicle (plate or VIN). Sourced live from the Danish Motorregister."""
    return await _get(ctx, f"/api/v1/koretoj/{_enc(identifier)}/insurance")


@mcp.tool()
async def vehicle_odometer(vin: str, ctx: Context) -> dict:
    """[Paid plan] Odometer history with rollback-fraud detection for a vehicle (VIN recommended).
    The killer used-car-history check — flags implausible mileage drops."""
    return await _get(ctx, f"/api/v1/koretoj/{_enc(vin)}/odometer")


@mcp.tool()
async def vehicle_recalls(identifier: str, ctx: Context) -> dict:
    """[Paid plan] Official safety recalls (tilbagekaldelser) matched to a vehicle's make/model:
    defect text, recall code, case number and date. Model-level, not per-VIN."""
    return await _get(ctx, f"/api/v1/koretoj/{_enc(identifier)}/recalls")


@mcp.tool()
async def company_ownership(cvr: str, ctx: Context) -> dict:
    """[Paid plan] Ownership / control graph for a company by CVR: real owners, subsidiaries and
    related entities."""
    return await _get(ctx, f"/api/v1/cvr/{_enc(cvr)}/ownership")


@mcp.tool()
async def company_financials(cvr: str, ctx: Context) -> dict:
    """[Paid plan] Annual-report headline figures for a company by CVR (revenue, profit, equity,
    assets) with a two-year comparison. Source: official regnskaber."""
    return await _get(ctx, f"/api/v1/cvr/{_enc(cvr)}/financials")


@mcp.tool()
async def person_companies(enheds_nummer: int, ctx: Context) -> dict:
    """[Paid plan] The person dossier: every company a CVR participant (by enhedsnummer) is or was
    involved in, with their role. Get the enhedsnummer from company_ownership / search results."""
    return await _get(ctx, f"/api/v1/cvr/person/{_enc(enheds_nummer)}/companies")


@mcp.tool()
async def person_bankruptcies(enheds_nummer: int, ctx: Context) -> dict:
    """[Paid plan] Serial-bankruptcy radar: companies tied to a person (by enhedsnummer) that went
    bankrupt — a fast due-diligence red-flag check."""
    return await _get(ctx, f"/api/v1/cvr/person/{_enc(enheds_nummer)}/bankruptcies")


# ───────────────── Site-parity endpoints (API_SITE_PARITY.md, 0425d40) ─────────────────

@mcp.tool()
async def vehicle_full_report(identifier: str, ctx: Context, include_live: bool = True) -> dict:
    """[Paid plan] The whole soge.dk vehicle page in ONE call (plate or VIN): core DMR data,
    equipment, syn, fuels, powertrain/lifecycle, green-tax & next-syn calculators, model fault &
    fleet stats, plus live enrichments (insurance, DMR-kerne, inspections, recalls, liens).
    include_live=False skips the slower live sources."""
    return await _get(ctx, f"/api/v1/koretoj/{_enc(identifier)}/full",
                      {"include_live": "false" if not include_live else None})


@mcp.tool()
async def vehicle_valuations(identifier: str, ctx: Context) -> dict:
    """[Paid plan] Official DMR valuation history (vurderinger) for a vehicle (plate or VIN) —
    the assessed values behind registration tax."""
    return await _get(ctx, f"/api/v1/koretoj/{_enc(identifier)}/valuations")


@mcp.tool()
async def vehicle_liens(identifier: str, ctx: Context) -> dict:
    """[Paid plan] Car debt / liens registered against a vehicle (Bilbogen / Tinglysning) — is it
    pledged as loan security? Plate or VIN. Not found = no lien data for that vehicle."""
    return await _get(ctx, f"/api/v1/koretoj/{_enc(identifier)}/liens")


@mcp.tool()
async def vehicle_dmr(identifier: str, ctx: Context) -> dict:
    """[Paid plan] Full DMR-kerne record for a vehicle (plate or VIN): battery capacity, electric
    range, measured consumption, extra equipment, the registry's next-inspection date, leasing
    period, block/seizure status."""
    return await _get(ctx, f"/api/v1/koretoj/{_enc(identifier)}/dmr")


@mcp.tool()
async def vehicle_ev_specs(identifier: str, ctx: Context) -> dict:
    """EV/PHEV battery capacity, electric range and consumption for a vehicle (plate or VIN),
    matched by make/model/variant. Not found for pure-combustion vehicles."""
    return await _get(ctx, f"/api/v1/koretoj/{_enc(identifier)}/ev-specs")


@mcp.tool()
async def vehicle_safety_alerts(identifier: str, ctx: Context) -> dict:
    """EU Safety Gate (RAPEX) alerts matched to a vehicle's make/model (plate or VIN) — brand-level
    product-safety warnings, distinct from manufacturer recalls (vehicle_recalls)."""
    return await _get(ctx, f"/api/v1/koretoj/{_enc(identifier)}/safety-alerts")


@mcp.tool()
async def vehicle_tax(identifier: str, ctx: Context, lang: str = "en") -> dict:
    """Danish green owner-tax (grøn ejerafgift / CO2-afgift) and the next periodic-inspection
    schedule for a vehicle (plate or VIN) — the figures the site's calculators show.
    lang: en | da | uk."""
    return await _get(ctx, f"/api/v1/koretoj/{_enc(identifier)}/tax", {"lang": lang})


@mcp.tool()
async def model_stats(make: str, model: str, ctx: Context) -> dict:
    """Per-model aggregates for a make/model (e.g. "BMW", "3-serie"): fleet size, age, fuel and
    colour mix, average mileage, and the inspection-fault profile (top defects, fail rate)."""
    return await _get(ctx, f"/api/v1/models/{_enc(make)}/{_enc(model)}/stats")


@mcp.tool()
async def company_network(cvr: str, ctx: Context, depth: int = 2) -> dict:
    """[Paid plan] Multi-degree company network by CVR — owners, management, founders and shared
    phone/email/domain links, with status colours and a risk summary. A cold company may answer
    with a pending status and retry_after: call again after that many seconds."""
    return await _get(ctx, f"/api/v1/cvr/{_enc(cvr)}/network", {"depth": depth})


@mcp.tool()
async def companies_by_phone(phone: str, ctx: Context) -> dict:
    """Reverse phone lookup in CVR: every company (or production unit) that registered this exact
    Danish phone number, its status, and whether the number is still registered to it."""
    return await _get(ctx, f"/api/v1/cvr/phone/{_enc(phone)}")


@mcp.tool()
async def cvr_stats(ctx: Context) -> dict:
    """CVR corpus totals: number of Danish companies, new registrations today and this week,
    and companies changed today."""
    return await _get(ctx, "/api/v1/cvr/stats")


@mcp.tool()
async def reviews(target_type: str, target_id: str, ctx: Context) -> dict:
    """Approved user reviews plus the aggregate rating for a company or a vehicle model.
    target_type: "company" (target_id = CVR) or "vehicle_model" (target_id as on soge.dk)."""
    return await _get(ctx, f"/api/v1/reviews/{_enc(target_type)}/{_enc(target_id)}")


def main() -> None:
    """Console-script entry point (`soge-mcp`)."""
    transport = (os.environ.get("SOGE_MCP_TRANSPORT") or "stdio").strip().lower()
    if transport not in ("stdio", "streamable-http"):
        transport = "stdio"
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
