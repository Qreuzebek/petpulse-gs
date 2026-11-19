"""Constantes do PetPulse (WARNED).

Todas as zonas e cotas abaixo formam a BASE DE DEMONSTRAÇÃO da POC.
Coordenadas são de locais reais de São Paulo; as cotas de terreno são valores
de referência compatíveis com a Google Elevation API e ficam em cache por H3.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # .../GLOBAL-SOLUTION-2
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "petpulse.db"
WEB_DATA = ROOT / "src" / "web" / "data"

H3_RES = 10            # ~66 m de aresta, ~15.000 m² por célula
TTL_MIN = 15           # janela deslizante de telemetria
K_MIN = 3              # k-anonymity: cluster precisa de >= K_MIN cães distintos
DBSCAN_EPS_M = 45      # raio de vizinhança do DBSCAN, em metros
KGF_TO_N = 9.80665

# Faixas de guia (kgf)
GUIA_FROUXA = 2.5
GUIA_TRANCO = 8.0

# Portes (altura de referência em cm)
PORTES = {"PEQUENO": 28, "MÉDIO": 46, "GRANDE": 62, "GIGANTE": 78}

# Zonas de demonstração: (nome, lat, lng, cota_terreno_m, peso_popularidade)
ZONAS = [
    ("Parque Ibirapuera · Portão 7", -23.58438, -46.64939, 752.1, 1.00),
    ("Praça Pereira Coutinho",        -23.58690, -46.67420, 762.8, 0.55),
    ("Parque do Povo · Setor Sul",    -23.58560, -46.68690, 748.9, 0.60),
    ("Praça Cidade de Milão",         -23.59020, -46.67230, 756.1, 0.45),
    ("Boulevard Afonso Braz",         -23.59140, -46.66930, 768.5, 0.40),
    ("Rua Brazópolis · Vila Nova Conceição", -23.57941, -46.66087, 763.3, 0.30),
]
