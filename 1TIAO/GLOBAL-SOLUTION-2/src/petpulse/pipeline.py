"""Pipeline completo: simula → grava no SQLite → DBSCAN por janela TTL → exporta JSON.

Uso:  python -m petpulse.pipeline   (a partir de src/)
"""
import json
from datetime import datetime, timedelta

import h3
import pandas as pd

from . import db
from .clustering import agrega_clusters, dbscan, ultima_posicao
from .config import DATA_DIR, DB_PATH, H3_RES, K_MIN, TTL_MIN, WEB_DATA, ZONAS
from .elevation import cota
from .simulate import gerar


def carregar(conn, caes, tele):
    conn.execute("DELETE FROM telemetry")
    conn.execute("DELETE FROM dog")
    conn.executemany("INSERT INTO dog VALUES (:dog_id,:nome,:porte,:altura_cm,:sexo,:peso_kg)", caes)
    for t in tele:
        t["h3"] = h3.latlng_to_cell(t["lat"], t["lng"], H3_RES)
    conn.executemany(
        "INSERT INTO telemetry(ts,dog_id,zona,lat,lng,h3,kgf,newton,faixa,elev_sensor_m,z_cm) "
        "VALUES (:ts,:dog_id,:zona,:lat,:lng,:h3,:kgf,:newton,:faixa,:elev_sensor_m,:z_cm)", tele)
    conn.commit()


def snapshots(conn, inicio: datetime, fim: datetime, passo_min: int = 15):
    df = pd.read_sql("SELECT * FROM telemetry", conn, parse_dates=["ts"])
    conn.execute("DELETE FROM cluster_snapshot")
    resultado = []
    t = inicio
    while t <= fim:
        janela = df[(df["ts"] > t - timedelta(minutes=TTL_MIN)) & (df["ts"] <= t)]
        caes = ultima_posicao(janela)
        rot = dbscan(caes)
        publicos, ocultos = agrega_clusters(caes, rot, lambda a, b: cota(conn, a, b))
        for c in publicos:
            conn.execute("INSERT INTO cluster_snapshot VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                         (t.isoformat(), c["cluster_id"], c["zona"], c["h3"], c["n_caes"],
                          c["tracao_media_kgf"], c["pico_kgf"], c["z_medio_cm"], c["z_min_cm"],
                          c["z_max_cm"], c["cota_m"], c["dbm"]))
        resultado.append({"t": t.strftime("%H:%M"), "caes_ativos": int(len(caes)),
                          "ocultos": ocultos, "clusters": publicos})
        t += timedelta(minutes=passo_min)
    conn.commit()
    return resultado


def main():
    caes, tele = gerar()
    conn = db.connect(DB_PATH)
    carregar(conn, caes, tele)
    dia = datetime(2026, 11, 18)
    snaps = snapshots(conn, dia + timedelta(hours=6), dia + timedelta(hours=22))
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(caes).to_csv(DATA_DIR / "dogs_simulados.csv", index=False)
    pd.DataFrame(tele).to_csv(DATA_DIR / "telemetria_simulada.csv", index=False)
    payload = {
        "aviso": "BASE SIMULADA DE DEMONSTRAÇÃO (POC acadêmica) — não são cães reais.",
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "k_min": K_MIN, "ttl_min": TTL_MIN, "h3_res": H3_RES,
        "zonas": [{"nome": n, "lat": la, "lng": ln, "cota_m": c} for n, la, ln, c, _ in ZONAS],
        "snapshots": snaps,
    }
    (WEB_DATA / "snapshots.json").write_text(json.dumps(payload, ensure_ascii=False))
    n_pub = sum(len(s["clusters"]) for s in snaps)
    print(f"{len(caes)} cães · {len(tele)} leituras · {len(snaps)} janelas · "
          f"{n_pub} clusters públicos · banco em {DB_PATH.name}")


if __name__ == "__main__":
    main()
