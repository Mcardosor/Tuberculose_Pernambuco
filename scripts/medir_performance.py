"""Quanto custa cada leitura do painel, sem o cache do Streamlit.

Mede o tempo real por consulta nos três recortes que a navegação oferece —
estado, região de saúde e município —, que é o que o usuário percorre ao
clicar no mapa. O cache do Streamlit fica de fora de propósito: o que interessa
aqui é o custo da primeira vez, que é o que ele sente.

Uso::

    python -m scripts.medir_performance

Os números entram em `docs/performance.md`; quando mudarem de forma relevante,
é ali que se atualiza.
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable
from dataclasses import replace

from src.data import canal, kpis, leitura, recortes
from src.data.escopo import Escopo

REPETICOES = 5

#: 2024 é o último ano fechado, que é onde o painel abre. Município: Recife.
ANO = 2024

_ESTADO = Escopo("TUBERCULOSE", ANO, "UF", uf="PE")
_REGIAO = replace(
    _ESTADO,
    municipios=tuple(recortes.municipios_de(macro=recortes.macros("PE")[0], uf="PE")),
)
_MUNICIPIO = Escopo("TUBERCULOSE", ANO, "MUN", uf="PE", mun="261160")

ESCOPOS = {
    "PE": _ESTADO,
    "macrorregião": _REGIAO,
    "Recife": _MUNICIPIO,
}

#: Só o que o painel realmente chama, na ordem da tela.
OPERACOES: dict[str, Callable[[Escopo], object]] = {
    "kpis.calcular (os 6 cards)": kpis.calcular,
    "valores_por_geografia (mapa)": lambda e: leitura.valores_por_geografia(e, "incid"),
    "ranking": lambda e: leitura.ranking(e, "incid"),
    "canal.montar": canal.montar,
    # Como o painel chama desde 30/set: dez anos, não a série inteira.
    "canal.epicurva (10 anos)": lambda e: canal.epicurva(e, ano_min=ANO - 9),
    "serie_anual": lambda e: leitura.serie_anual(e, "incid"),
    "piramide_completa": leitura.piramide_completa,
    "composicao (um tópico)": lambda e: leitura.composicao(e, "SITUA_ENCE"),
}


def cronometrar(fn: Callable[[Escopo], object], esc: Escopo) -> tuple[float, float]:
    """(mediana, pior) em milissegundos, descartando a primeira chamada.

    A primeira paga a leitura dos metadados do parquet, que o sistema de
    arquivos passa a guardar — contá-la mediria o disco frio, não a consulta.
    """
    fn(esc)
    tempos = []
    for _ in range(REPETICOES):
        inicio = time.perf_counter()
        fn(esc)
        tempos.append((time.perf_counter() - inicio) * 1000)
    return statistics.median(tempos), max(tempos)


def main() -> None:
    print(f"Tuberculose, {ANO}. Mediana de {REPETICOES} execuções, em ms.\n")
    largura = max(len(n) for n in OPERACOES)
    print(f"{'operação':<{largura}}" + "".join(f"{r:>22}" for r in ESCOPOS))

    totais = dict.fromkeys(ESCOPOS, 0.0)
    for nome, fn in OPERACOES.items():
        linha = f"{nome:<{largura}}"
        for rotulo, esc in ESCOPOS.items():
            try:
                mediana, pior = cronometrar(fn, esc)
            except Exception as erro:  # noqa: BLE001 — medição não pode derrubar
                linha += f"{'—':>14}{'':>8}"
                print(f"  ! {nome} em {rotulo}: {type(erro).__name__}")
                continue
            if not nome.startswith("kpis.calcular"):
                totais[rotulo] += mediana
            linha += f"{mediana:>14.1f}{pior:>8.1f}"
        print(linha)

    print(f"\n{'soma dos leitores':<{largura}}" + "".join(
        f"{totais[r]:>14.1f}{'':>8}" for r in ESCOPOS
    ))
    print("\n(cada célula: mediana / pior caso)")


if __name__ == "__main__":
    main()
