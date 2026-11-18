#!/usr/bin/env bash
# Soge.dk API — curl examples.
# Get a key (free tier) at https://soge.dk/pricing
set -euo pipefail

API="https://soge.dk/api/v1"
: "${SOGE_API_KEY:?Set SOGE_API_KEY=your_key first}"

echo "# Health (no key needed)"
curl -s "$API/health"; echo

echo "# Vehicle by plate or VIN (free)"
curl -s -H "X-API-KEY: $SOGE_API_KEY" "$API/vehicles/AB12345"; echo

echo "# Company search by CVR / name / text (free)"
curl -s -H "X-API-KEY: $SOGE_API_KEY" "$API/companies/novo%20nordisk?page=1&size=5"; echo

echo "# Companies at an address (free)"
curl -s -H "X-API-KEY: $SOGE_API_KEY" "$API/companies-at-address?postnr=1050"; echo

echo "# Premium: inspection history (paid plan)"
curl -s -H "X-API-KEY: $SOGE_API_KEY" "$API/koretoj/AB12345/inspections"; echo

echo "# Premium: company financials (paid plan)"
curl -s -H "X-API-KEY: $SOGE_API_KEY" "$API/cvr/25052943/financials"; echo
