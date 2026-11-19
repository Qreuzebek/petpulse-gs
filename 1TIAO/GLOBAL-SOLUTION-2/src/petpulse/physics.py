"""Física do CLIP-01: força na guia, eixo Z e índice DBM."""
import math

from .config import GUIA_FROUXA, GUIA_TRANCO, KGF_TO_N, PORTES


def kgf_to_n(kgf: float) -> int:
    """Converte kgf em Newtons, arredondando como a UI (3.4 kgf -> 33 N)."""
    return int(round(kgf * KGF_TO_N))


def faixa_guia(kgf: float) -> str:
    """Classifica a tração: FROUXA (<2.5), TRACAO (2.5–8) ou TRANCO (>8)."""
    if kgf < GUIA_FROUXA:
        return "FROUXA"
    if kgf <= GUIA_TRANCO:
        return "TRACAO"
    return "TRANCO"


def z_cao_cm(elev_sensor_m: float, google_elev_m: float, offset_montagem_cm: float = 0.0,
             inclinacao_graus: float = 0.0) -> float:
    """Z_cão = (Elevação_Sensor − GoogleElev(lat,lng)) × 100, em cm.

    - offset_montagem_cm: distância do sensor até a cernelha (coleira ~ +0, peitoral ~ -4).
    - inclinacao_graus: ângulo do CLIP-01 medido pela IMU; projeta a altura na vertical.
    """
    z = (elev_sensor_m - google_elev_m) * 100.0
    z = z * math.cos(math.radians(inclinacao_graus)) + offset_montagem_cm
    return round(z, 1)


def compensa_barometro(leituras_m: list[float], alpha: float = 0.2) -> float:
    """Filtro exponencial (EMA) para reduzir o ruído do barômetro (~±10 cm)."""
    if not leituras_m:
        raise ValueError("sem leituras")
    ema = leituras_m[0]
    for v in leituras_m[1:]:
        ema = alpha * v + (1 - alpha) * ema
    return ema


def porte_por_altura(z_cm: float) -> str:
    """Escolhe o porte cuja altura de referência está mais próxima."""
    return min(PORTES, key=lambda p: abs(PORTES[p] - z_cm))


def indice_dbm(n_caes: int, tracao_media_kgf: float, amplitude_z_cm: float,
               ref_max: float = 40 * 18 * 1.0) -> int:
    """Índice DBM (Densidade·Biomecânica·Movimento), 0–100.

    NÃO é o dBm de radiofrequência (10·log10(P/1 mW)). É uma métrica própria da
    POC, inspirada em decibéis: comprime em escala logarítmica a intensidade
    I = n_cães × tração_média(kgf) × (amplitude_Z em metros), evitando que uma
    zona muito cheia sature a escala linear.

        DBM = 100 × log10(1 + I) / log10(1 + I_ref)

    I_ref padrão: 40 cães × 18 kgf × 1,0 m de amplitude.
    """
    if n_caes <= 0:
        return 0
    intensidade = n_caes * max(tracao_media_kgf, 0) * max(amplitude_z_cm, 0) / 100.0
    valor = 100 * math.log10(1 + intensidade) / math.log10(1 + ref_max)
    return int(round(min(max(valor, 0), 100)))


def clima_comportamental(dbm: int) -> float:
    """Posição contínua 0..1 no EIXO X NEUTRO (0 = TRANQUILA, 0.5 = HARMONIA, 1 = AGITADA).

    Sem rótulos punitivos: é só uma régua.
    """
    return round(dbm / 100.0, 3)
