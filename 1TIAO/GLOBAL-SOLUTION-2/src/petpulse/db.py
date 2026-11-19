"""Modelo relacional (SQLite) do PetPulse."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS dog (
    dog_id     INTEGER PRIMARY KEY,
    nome       TEXT NOT NULL,
    porte      TEXT NOT NULL CHECK (porte IN ('PEQUENO','MÉDIO','GRANDE','GIGANTE')),
    altura_cm  REAL NOT NULL,
    sexo       TEXT NOT NULL,
    peso_kg    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS telemetry (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    dog_id        INTEGER NOT NULL REFERENCES dog(dog_id),
    zona          TEXT NOT NULL,
    lat           REAL NOT NULL,
    lng           REAL NOT NULL,
    h3            TEXT NOT NULL,
    kgf           REAL NOT NULL,
    newton        INTEGER NOT NULL,
    faixa         TEXT NOT NULL CHECK (faixa IN ('FROUXA','TRACAO','TRANCO')),
    elev_sensor_m REAL NOT NULL,
    z_cm          REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tel_h3_ts ON telemetry(h3, ts);
CREATE TABLE IF NOT EXISTS h3_elevation (
    h3     TEXT PRIMARY KEY,
    elev_m REAL NOT NULL,
    fonte  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cluster_snapshot (
    janela_ini   TEXT NOT NULL,
    cluster_id   INTEGER NOT NULL,
    zona         TEXT NOT NULL,
    h3           TEXT NOT NULL,
    n_caes       INTEGER NOT NULL,
    tracao_media REAL NOT NULL,
    pico_kgf     REAL NOT NULL,
    z_medio_cm   REAL NOT NULL,
    z_min_cm     REAL NOT NULL,
    z_max_cm     REAL NOT NULL,
    cota_m       REAL NOT NULL,
    dbm          INTEGER NOT NULL,
    PRIMARY KEY (janela_ini, cluster_id)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn
