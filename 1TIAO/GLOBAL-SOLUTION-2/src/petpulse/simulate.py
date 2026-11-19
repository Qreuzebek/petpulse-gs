"""Gerador da BASE SIMULADA de telemetria (Regra 8: dados de demonstração).

Gera cães (perfis) e leituras do CLIP-01 ao longo de um dia, concentradas nas
zonas de demonstração, com pico às 18h. Semente fixa para reprodutibilidade.
"""
import math
import random
from datetime import datetime, timedelta

from .config import PORTES, ZONAS
from .physics import faixa_guia, kgf_to_n

SEXOS = ["Macho Castr.", "Macho Inteiro", "Fêmea Castr.", "Fêmea Inteira"]
NOMES = ["THOR", "LUNA", "BOB", "MEL", "NINA", "MAX", "PIPOCA", "FRIDA", "ZECA", "AMORA",
         "TOBY", "BELINHA", "OZZY", "LOLA", "FAROFA", "JUJUBA"]


def _curva_horaria(h: float) -> float:
    """Demanda relativa de passeios por hora: picos às 7h e às 18h."""
    return 0.15 + math.exp(-((h - 7) ** 2) / 2.5) * 0.6 + math.exp(-((h - 18) ** 2) / 2.0)


def gerar_caes(n: int, rng: random.Random) -> list[dict]:
    caes = []
    for i in range(n):
        porte = rng.choices(list(PORTES), weights=[3, 4, 4, 1])[0]
        altura = PORTES[porte] + rng.gauss(0, 3)
        caes.append({
            "dog_id": 8000 + i,
            "nome": rng.choice(NOMES),
            "porte": porte,
            "altura_cm": round(altura, 1),
            "sexo": rng.choice(SEXOS),
            "peso_kg": round({"PEQUENO": 7, "MÉDIO": 16, "GRANDE": 30, "GIGANTE": 50}[porte]
                             * rng.uniform(0.8, 1.2), 1),
        })
    return caes


def gerar_telemetria(caes: list[dict], dia: datetime, rng: random.Random,
                     passeios_por_cao: int = 2) -> list[dict]:
    """Cada passeio = 20–40 leituras a cada 30 s numa zona."""
    horas = [h / 4 for h in range(5 * 4, 23 * 4)]
    pesos_h = [_curva_horaria(h) for h in horas]
    pesos_z = [z[4] for z in ZONAS]
    linhas = []
    for cao in caes:
        for _ in range(passeios_por_cao):
            hora = rng.choices(horas, weights=pesos_h)[0]
            zona = rng.choices(ZONAS, weights=pesos_z)[0]
            nome_z, lat0, lng0, cota, _ = zona
            t = dia + timedelta(hours=hora, minutes=rng.uniform(0, 14))
            lat, lng = lat0 + rng.gauss(0, 0.00035), lng0 + rng.gauss(0, 0.00035)
            base_kgf = cao["peso_kg"] * rng.uniform(0.08, 0.30)
            for _ in range(rng.randint(20, 40)):
                lat += rng.gauss(0, 0.00004)
                lng += rng.gauss(0, 0.00004)
                kgf = max(0.2, rng.gauss(base_kgf, base_kgf * 0.35))
                if rng.random() < 0.04:  # tranco eventual
                    kgf += rng.uniform(6, 12)
                salto = rng.uniform(10, 30) if rng.random() < 0.03 else 0.0
                z = cao["altura_cm"] + rng.gauss(0, 4) + salto
                elev_sensor = cota + z / 100 + rng.gauss(0, 0.05)  # ruído barométrico bruto
                linhas.append({
                    "ts": t.isoformat(timespec="seconds"),
                    "dog_id": cao["dog_id"],
                    "zona": nome_z,
                    "lat": round(lat, 6),
                    "lng": round(lng, 6),
                    "kgf": round(kgf, 2),
                    "newton": kgf_to_n(kgf),
                    "faixa": faixa_guia(kgf),
                    "elev_sensor_m": round(elev_sensor, 3),
                    "z_cm": round(z, 1),
                })
                t += timedelta(seconds=30)
    return linhas


def gerar(n_caes: int = 600, seed: int = 2026) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    caes = gerar_caes(n_caes, rng)
    tele = gerar_telemetria(caes, datetime(2026, 11, 18), rng)
    return caes, tele
