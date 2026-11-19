"""Análise exploratória da base simulada → figuras em docs/img e tabela-resumo.

Uso (a partir de src/):  python -m petpulse.eda
"""
import json
import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .config import DB_PATH, ROOT

IMG = ROOT / "docs" / "img"
INK, GRAF, ACO, NEV = "#0E0F10", "#2A2C2F", "#6B6F75", "#C9CCD0"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": INK, "axes.labelcolor": INK,
                     "xtick.color": GRAF, "ytick.color": GRAF, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    tel = pd.read_sql("SELECT t.*, d.porte FROM telemetry t JOIN dog d USING(dog_id)", conn,
                      parse_dates=["ts"])
    snap = pd.read_sql("SELECT * FROM cluster_snapshot", conn, parse_dates=["janela_ini"])
    resumo = {}

    # 1. distribuição de tração
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.hist(tel["kgf"], bins=60, color=GRAF)
    for x in (2.5, 8):
        ax.axvline(x, color=INK, ls="--", lw=1)
    ax.set_xlabel("Tração na guia (kgf)")
    ax.set_ylabel("Leituras")
    ax.set_title("Distribuição da tração · faixas Frouxa | Tração | Tranco", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(IMG / "eda_tracao.png"); plt.close(fig)
    resumo["faixas_pct"] = (tel["faixa"].value_counts(normalize=True) * 100).round(1).to_dict()

    # 2. demanda por hora
    por_hora = tel.groupby(tel["ts"].dt.hour)["dog_id"].nunique()
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.bar(por_hora.index, por_hora.values, color=[INK if h == 18 else ACO for h in por_hora.index])
    ax.set_xlabel("Hora do dia"); ax.set_ylabel("Cães distintos")
    ax.set_title("Cães em passeio por hora (pico às 18h)", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(IMG / "eda_hora.png"); plt.close(fig)
    resumo["pico_hora"] = int(por_hora.idxmax())

    # 3. eixo Z por porte
    ordem = ["PEQUENO", "MÉDIO", "GRANDE", "GIGANTE"]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.boxplot([tel.loc[tel["porte"] == p, "z_cm"] for p in ordem], labels=ordem,
               patch_artist=True, boxprops=dict(facecolor=NEV, color=INK),
               medianprops=dict(color=INK), flierprops=dict(markersize=2, markeredgecolor=ACO))
    ax.set_ylabel("Z (cm)")
    ax.set_title("Altura medida no eixo Z por porte", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(IMG / "eda_eixo_z.png"); plt.close(fig)
    resumo["z_mediana_por_porte"] = tel.groupby("porte")["z_cm"].median().round(1).to_dict()

    # 4. DBM por zona ao longo do dia
    fig, ax = plt.subplots(figsize=(7, 3.4))
    tons = [INK, GRAF, ACO, "#9DA1A6", NEV, "#4A4D52"]
    piv = snap.groupby([snap["janela_ini"].dt.strftime("%H:%M"), "zona"])["dbm"].max().unstack()
    for (z, cor) in zip(piv.columns, tons):
        ax.plot(piv.index, piv[z], label=z.split("·")[0].strip(), color=cor, lw=1.6)
    ax.set_xticks(piv.index[::8]); ax.set_ylabel("Índice DBM (0–100)")
    ax.legend(fontsize=7, frameon=False, ncol=2)
    ax.set_title("Índice DBM por zona (só clusters com k ≥ 3)", loc="left", fontsize=10)
    fig.tight_layout(); fig.savefig(IMG / "eda_dbm.png"); plt.close(fig)

    tabela = (snap.groupby("zona").agg(janelas=("dbm", "size"), caes_max=("n_caes", "max"),
                                       tracao_media=("tracao_media", "mean"), pico_kgf=("pico_kgf", "max"),
                                       dbm_max=("dbm", "max"), cota_m=("cota_m", "mean"))
              .round(1).sort_values("dbm_max", ascending=False))
    tabela.to_csv(ROOT / "data" / "resumo_zonas.csv")
    resumo["leituras"] = int(len(tel)); resumo["caes"] = int(tel["dog_id"].nunique())
    resumo["clusters_publicos"] = int(len(snap))
    (ROOT / "data" / "resumo_eda.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2))
    print(tabela.to_string()); print(json.dumps(resumo, ensure_ascii=False))


if __name__ == "__main__":
    main()
