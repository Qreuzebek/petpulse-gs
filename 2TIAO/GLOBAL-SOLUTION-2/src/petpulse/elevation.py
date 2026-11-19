"""Cota do terreno por célula H3, com cache em SQLite.

Ordem de consulta:
1. cache `h3_elevation` no SQLite (evita chamadas repetidas → custo e latência);
2. Google Elevation API, se a variável GOOGLE_MAPS_API_KEY existir;
3. interpolação pelo inverso da distância a partir das cotas de referência das
   zonas (fallback offline, marcado como `fonte='referencia'`).
"""
import json
import math
import os
import sqlite3
import urllib.parse
import urllib.request

import h3

from .config import H3_RES, ZONAS

GOOGLE_URL = "https://maps.googleapis.com/maps/api/elevation/json"


def _google(lat: float, lng: float, key: str) -> float | None:
    q = urllib.parse.urlencode({"locations": f"{lat},{lng}", "key": key})
    try:
        with urllib.request.urlopen(f"{GOOGLE_URL}?{q}", timeout=5) as r:
            data = json.load(r)
        if data.get("status") == "OK":
            return float(data["results"][0]["elevation"])
    except Exception:
        return None
    return None


def _interpolada(lat: float, lng: float) -> float:
    num = den = 0.0
    for _, zlat, zlng, cota, _ in ZONAS:
        d = math.hypot(lat - zlat, lng - zlng) + 1e-6
        w = 1 / d ** 2
        num += w * cota
        den += w
    return round(num / den, 1)


def cota(conn: sqlite3.Connection, lat: float, lng: float) -> tuple[str, float, str]:
    cell = h3.latlng_to_cell(lat, lng, H3_RES)
    row = conn.execute("SELECT elev_m, fonte FROM h3_elevation WHERE h3=?", (cell,)).fetchone()
    if row:
        return cell, row[0], row[1]
    clat, clng = h3.cell_to_latlng(cell)
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    elev, fonte = (None, "")
    if key:
        elev = _google(clat, clng, key)
        fonte = "google"
    if elev is None:
        elev, fonte = _interpolada(clat, clng), "referencia"
    conn.execute("INSERT OR REPLACE INTO h3_elevation(h3, elev_m, fonte) VALUES (?,?,?)",
                 (cell, elev, fonte))
    return cell, elev, fonte
