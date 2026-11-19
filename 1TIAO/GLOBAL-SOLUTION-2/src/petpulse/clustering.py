"""DBSCAN geoespacial + k-anonymity + agregação por H3."""
from collections import Counter

import h3
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from .config import DBSCAN_EPS_M, H3_RES, K_MIN
from .physics import indice_dbm, porte_por_altura

R_TERRA_M = 6_371_000


def ultima_posicao(janela: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por cão: posição mais recente e estatísticas da janela TTL."""
    g = janela.sort_values("ts").groupby("dog_id")
    return pd.DataFrame({
        "lat": g["lat"].last(),
        "lng": g["lng"].last(),
        "zona": g["zona"].last(),
        "kgf_medio": g["kgf"].mean(),
        "kgf_pico": g["kgf"].max(),
        "z_medio": g["z_cm"].median(),
        "z_min": g["z_cm"].min(),
        "z_max": g["z_cm"].max(),
        "faixa": g["faixa"].agg(lambda s: s.value_counts().idxmax()),
    }).reset_index()


def dbscan(caes: pd.DataFrame, eps_m: float = DBSCAN_EPS_M, k_min: int = K_MIN) -> np.ndarray:
    """Rótulos DBSCAN com métrica haversine. -1 = ruído/isolado."""
    if caes.empty:
        return np.array([], dtype=int)
    coords = np.radians(caes[["lat", "lng"]].to_numpy())
    model = DBSCAN(eps=eps_m / R_TERRA_M, min_samples=k_min, metric="haversine",
                   algorithm="ball_tree")
    return model.fit_predict(coords)


def agrega_clusters(caes: pd.DataFrame, rotulos: np.ndarray, cota_fn,
                    k_min: int = K_MIN) -> tuple[list[dict], int]:
    """Agrega clusters e aplica k-anonymity.

    Retorna (clusters_publicos, n_ocultos). Cães isolados (rótulo -1) e clusters
    com menos de k_min cães distintos NUNCA saem deste módulo (LGPD OCULTO).
    """
    caes = caes.assign(cluster=rotulos)
    ocultos = int((caes["cluster"] == -1).sum())
    publicos = []
    for cid, grupo in caes[caes["cluster"] >= 0].groupby("cluster"):
        if grupo["dog_id"].nunique() < k_min:
            ocultos += len(grupo)
            continue
        lat, lng = grupo["lat"].mean(), grupo["lng"].mean()
        cell, cota_m, fonte = cota_fn(lat, lng)
        cells = {h3.latlng_to_cell(a, b, H3_RES) for a, b in zip(grupo["lat"], grupo["lng"])}
        tracao = float(grupo["kgf_medio"].mean())
        z_min, z_max = float(grupo["z_min"].min()), float(grupo["z_max"].max())
        faixas = Counter(grupo["faixa"])
        portes = Counter(porte_por_altura(z) for z in grupo["z_medio"])
        dbm = indice_dbm(len(grupo), tracao, z_max - z_min)
        publicos.append({
            "cluster_id": int(cid),
            "zona": grupo["zona"].mode().iat[0],
            "lat": round(lat, 6), "lng": round(lng, 6),
            "h3": cell, "h3_adj": len(cells - {cell}),
            "cells": sorted(cells),
            "n_caes": int(len(grupo)),
            "tracao_media_kgf": round(tracao, 1),
            "pico_kgf": round(float(grupo["kgf_pico"].max()), 1),
            "z_medio_cm": round(float(grupo["z_medio"].mean()), 0),
            "z_min_cm": round(z_min, 0), "z_max_cm": round(z_max, 0),
            "cota_m": cota_m, "cota_fonte": fonte,
            "dbm": dbm,
            "faixas": {k: faixas.get(k, 0) for k in ("FROUXA", "TRACAO", "TRANCO")},
            "portes": {k: portes.get(k, 0) for k in ("PEQUENO", "MÉDIO", "GRANDE", "GIGANTE")},
        })
    return publicos, ocultos
