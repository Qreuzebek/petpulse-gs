"""Testes da POC PetPulse. Rodar a partir de src/:  python -m pytest -q"""
import sqlite3

import h3
import numpy as np
import pandas as pd
import pytest

from petpulse import db
from petpulse.clustering import agrega_clusters, dbscan
from petpulse.elevation import cota
from petpulse.physics import (clima_comportamental, compensa_barometro, faixa_guia,
                              indice_dbm, kgf_to_n, porte_por_altura, z_cao_cm)
from petpulse.simulate import gerar


# ---------- física ----------
@pytest.mark.parametrize("kgf,n", [(3.4, 33), (13.6, 133), (18.3, 179)])
def test_kgf_para_newton_igual_a_ui(kgf, n):
    assert kgf_to_n(kgf) == n


@pytest.mark.parametrize("kgf,faixa", [(1.0, "FROUXA"), (2.5, "TRACAO"), (8.0, "TRACAO"), (8.1, "TRANCO")])
def test_faixas_de_guia(kgf, faixa):
    assert faixa_guia(kgf) == faixa


def test_eixo_z_formula():
    assert z_cao_cm(752.71, 752.10) == pytest.approx(61.0, abs=0.1)
    # inclinação de 60° reduz a altura projetada pela metade
    assert z_cao_cm(752.71, 752.10, inclinacao_graus=60) == pytest.approx(30.5, abs=0.1)


def test_filtro_barometrico_reduz_ruido():
    rng = np.random.default_rng(0)
    bruto = list(752.71 + rng.normal(0, 0.10, 200))
    assert abs(compensa_barometro(bruto) - 752.71) < 0.10


@pytest.mark.parametrize("z,porte", [(27, "PEQUENO"), (47, "MÉDIO"), (61, "GRANDE"), (80, "GIGANTE")])
def test_porte_por_altura(z, porte):
    assert porte_por_altura(z) == porte


def test_dbm_logaritmico_monotono_e_limitado():
    a = indice_dbm(3, 3, 30)
    b = indice_dbm(13, 13.6, 70)
    c = indice_dbm(500, 50, 300)
    assert 0 < a < b <= 100 and c == 100
    assert indice_dbm(0, 10, 10) == 0
    # compressão log: dobrar a intensidade NÃO dobra o índice
    assert indice_dbm(20, 10, 50) < 2 * indice_dbm(10, 10, 50)
    assert clima_comportamental(50) == 0.5


# ---------- DBSCAN + k-anonymity ----------
def _caes(pontos):
    return pd.DataFrame([{"dog_id": i, "lat": la, "lng": ln, "zona": "Z", "kgf_medio": 4.0,
                          "kgf_pico": 9.0, "z_medio": 46, "z_min": 40, "z_max": 70, "faixa": "TRACAO"}
                         for i, (la, ln) in enumerate(pontos)])


def test_dbscan_agrupa_vizinhos_e_isola_distante():
    pts = [(-23.58438, -46.64939), (-23.58440, -46.64945), (-23.58435, -46.64930),
           (-23.60000, -46.70000)]
    rot = dbscan(_caes(pts))
    assert rot[0] == rot[1] == rot[2] != -1
    assert rot[3] == -1


def test_k_anonymity_oculta_isolados_e_grupos_pequenos():
    pts = [(-23.58438, -46.64939), (-23.58440, -46.64945), (-23.58435, -46.64930),  # 3 → público
           (-23.60000, -46.70000)]                                                   # isolado
    caes = _caes(pts)
    publicos, ocultos = agrega_clusters(caes, dbscan(caes), lambda a, b: ("x", 750.0, "teste"))
    assert len(publicos) == 1 and publicos[0]["n_caes"] == 3
    assert ocultos == 1
    # com k=4 o mesmo grupo de 3 é ocultado inteiro
    publicos4, ocultos4 = agrega_clusters(caes, dbscan(caes, k_min=3), lambda a, b: ("x", 750.0, "t"), k_min=4)
    assert publicos4 == [] and ocultos4 == 4


def test_cluster_publico_nao_expoe_ids():
    caes = _caes([(-23.58438, -46.64939), (-23.58440, -46.64945), (-23.58435, -46.64930)])
    publicos, _ = agrega_clusters(caes, dbscan(caes), lambda a, b: ("x", 750.0, "t"))
    assert "dog_id" not in publicos[0] and "dog_ids" not in publicos[0]


# ---------- banco + cache de elevação ----------
def test_cache_h3_de_elevacao(tmp_path, monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    conn = db.connect(tmp_path / "t.db")
    cell1, e1, f1 = cota(conn, -23.58438, -46.64939)
    cell2, e2, _ = cota(conn, -23.58438, -46.64939)
    assert cell1 == cell2 == h3.latlng_to_cell(-23.58438, -46.64939, 10)
    assert e1 == e2 and f1 == "referencia"
    assert conn.execute("SELECT COUNT(*) FROM h3_elevation").fetchone()[0] == 1
    assert 745 < e1 < 770


def test_schema_rejeita_faixa_invalida(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    conn.execute("INSERT INTO dog VALUES (1,'THOR','GRANDE',61,'Macho Castr.',30)")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO telemetry(ts,dog_id,zona,lat,lng,h3,kgf,newton,faixa,elev_sensor_m,z_cm)"
                     " VALUES ('t',1,'z',0,0,'h',1,1,'MUITO_FORTE',0,0)")


# ---------- simulação ----------
def test_simulacao_reprodutivel_e_com_pico_18h():
    c1, t1 = gerar(n_caes=100, seed=7)
    c2, t2 = gerar(n_caes=100, seed=7)
    assert t1 == t2
    horas = pd.to_datetime(pd.DataFrame(t1)["ts"]).dt.hour.value_counts()
    assert horas.idxmax() in (17, 18, 19)
