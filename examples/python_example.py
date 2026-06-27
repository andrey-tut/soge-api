#!/usr/bin/env python3
"""Soge.dk API — minimal Python client (stdlib only).

    export SOGE_API_KEY=your_key   # https://soge.dk/pricing  (free tier)
    python python_example.py
"""
import os
import json
import urllib.parse
import urllib.request

API = "https://soge.dk/api/v1"
KEY = os.environ.get("SOGE_API_KEY")


def get(path, params=None, auth=True):
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    if auth:
        if not KEY:
            raise SystemExit("Set SOGE_API_KEY first (https://soge.dk/pricing)")
        req.add_header("X-API-KEY", KEY)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


if __name__ == "__main__":
    print("health   :", get("/health", auth=False))
    print("vehicle  :", get("/vehicles/AB12345"))
    print("company  :", get("/companies/" + urllib.parse.quote("novo nordisk"), {"size": 5}))
    print("at-addr  :", get("/companies-at-address", {"postnr": "1050"}))
    # Premium (needs a paid plan):
    # print("syn    :", get("/koretoj/AB12345/inspections"))
    # print("finance:", get("/cvr/25052943/financials"))
