"""
baixar_populacao.py — população IBGE por município de PE e ano
══════════════════════════════════════════════════════════════
Denominador das taxas de incidência e mortalidade nos três níveis geográficos
(município, região de saúde, macrorregião) — a agregação por região é feita
somando os municípios, então basta a série municipal.

Fontes (API SIDRA):
  - t/6579  Estimativas da população residente (anual, 2001–2021 e 2024)
  - t/4714  Censo 2022 — população residente

Anos sem estimativa publicada são preenchidos por interpolação linear entre os
anos conhecidos e extrapolação da última taxa de crescimento (o SINAN vai até
2025, o IBGE não). A coluna `estimado` marca esses anos para o dashboard poder
sinalizar.

Saída: dados_dashboard/pop_pe.parquet  (codigo_ibge, ano, populacao, estimado)

Rodar:  python etl/baixar_populacao.py
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "dados_dashboard" / "pop_pe.parquet"

# n6/in n3 26 = todos os municípios (n6) contidos na UF 26 (Pernambuco)
URL_ESTIMATIVAS = "https://apisidra.ibge.gov.br/values/t/6579/n6/in%20n3%2026/v/9324/p/all"
URL_CENSO_2022 = "https://apisidra.ibge.gov.br/values/t/4714/n6/in%20n3%2026/v/93/p/2022"

ANO_MIN, ANO_MAX = 2001, 2026


def sidra(url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "cenarios-tb-pe/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dados = json.loads(r.read().decode("utf-8"))
    return dados[1:]  # a primeira linha do SIDRA é o cabeçalho descritivo


def coletar() -> pd.DataFrame:
    linhas = []
    for url in (URL_ESTIMATIVAS, URL_CENSO_2022):
        for reg in sidra(url):
            valor = reg["V"]
            if valor in ("...", "-", "..", "X"):
                continue
            linhas.append({
                "codigo_ibge": int(reg["D1C"]),
                "ano": int(reg["D3C"]),
                "populacao": int(valor),
            })
    df = pd.DataFrame(linhas)
    # Censo 2022 tem precedência sobre estimativa do mesmo ano, se houver
    return df.drop_duplicates(subset=["codigo_ibge", "ano"], keep="last")


def completar_serie(df: pd.DataFrame) -> pd.DataFrame:
    """Interpola anos faltantes e extrapola os posteriores ao último dado do IBGE."""
    anos = list(range(ANO_MIN, ANO_MAX + 1))
    saida = []
    for codigo, g in df.groupby("codigo_ibge"):
        serie = g.set_index("ano")["populacao"].reindex(anos)
        conhecidos = serie.dropna()
        if conhecidos.empty:
            continue
        cheia = serie.interpolate(method="linear", limit_area="inside")

        # extrapolação: mantém a taxa média de crescimento dos últimos 5 anos
        ult_ano = int(conhecidos.index.max())
        base = conhecidos.loc[ult_ano]
        ref_ano = max(int(conhecidos.index.min()), ult_ano - 5)
        n = max(ult_ano - ref_ano, 1)
        taxa = (base / conhecidos.loc[ref_ano]) ** (1 / n) if conhecidos.loc[ref_ano] else 1.0
        for a in anos:
            if pd.isna(cheia.loc[a]):
                cheia.loc[a] = base * (taxa ** (a - ult_ano)) if a > ult_ano else conhecidos.iloc[0]

        for a in anos:
            saida.append({
                "codigo_ibge": int(codigo),
                "ano": a,
                "populacao": int(round(cheia.loc[a])),
                "estimado": a not in conhecidos.index,
            })
    return pd.DataFrame(saida)


def main() -> None:
    print("Baixando população municipal de PE no SIDRA…")
    bruto = coletar()
    print(f"  {len(bruto):,} observações · {bruto.codigo_ibge.nunique()} municípios · "
          f"{bruto.ano.min()}–{bruto.ano.max()}".replace(",", "."))

    df = completar_serie(bruto)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(SAIDA, index=False, compression="zstd")

    pe = df.groupby("ano")["populacao"].sum()
    print(f"\n  pop_pe.parquet · {df.codigo_ibge.nunique()} municípios × {df.ano.nunique()} anos")
    print(f"  PE {pe.index.min()}: {pe.iloc[0]:,}  →  {pe.index.max()}: {pe.iloc[-1]:,}".replace(",", "."))
    print(f"  anos estimados por interpolação/extrapolação: "
          f"{sorted(df[df.estimado].ano.unique())}")


if __name__ == "__main__":
    main()
