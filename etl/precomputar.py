"""
precomputar.py — gera os agregados da visão padrão
══════════════════════════════════════════════════
Calcula, no build, tudo que a primeira tela do painel precisa e grava em
`dados_dashboard/_agregados.json`. Em execução o app lê esse arquivo em vez de
consultar o DuckDB, então o primeiro acesso depois de um deploy não paga o custo
frio nem depende de thread de aquecimento.

**Não** tenta cobrir o espaço de filtros — ele é combinatório (anos × macro ×
região × município × sexo × raça × HIV × vulnerabilidades × comorbidades).
Pré-computa só a visão padrão (PE inteiro, série completa, sem filtro de perfil),
que é o que todo acesso vê antes de mexer em qualquer coisa. Qualquer filtro cai
no DuckDB, que responde em dezenas de milissegundos.

Rode SEMPRE depois de `preparar_dados.py` / `baixar_populacao.py` — o arquivo
guarda a impressão digital dos Parquets e se invalida sozinho se eles mudarem,
mas aí o ganho some até você regerar.

Rodar:  python etl/precomputar.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src import indicadores, precomputado  # noqa: E402
from src.constantes import NIVEIS_GEO  # noqa: E402
from src.filtros import Filtros  # noqa: E402


def _json_ok(obj):
    """Converte escalares numpy/pandas que o json não serializa sozinho."""
    if hasattr(obj, "item"):
        return obj.item()
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(f"não serializável: {type(obj).__name__}")


def main() -> None:
    # Começa do zero: com o store antigo no lugar, as funções devolveriam o
    # valor pré-computado anterior e o arquivo novo seria só uma cópia do velho.
    if precomputado.ARQUIVO.exists():
        precomputado.ARQUIVO.unlink()
    precomputado._store.cache_clear()

    meta = indicadores._meta_ao_vivo()
    padrao = Filtros(anos=tuple(meta["anos"]))

    print(f"Visão padrão: {meta['anos'][0]}–{meta['anos'][-1]} · Pernambuco inteiro · "
          "sem filtro de perfil\n")

    tarefas = [
        ("meta", None, "", lambda: meta),
        ("resumo", padrao, "", lambda: indicadores.resumo(padrao)),
        ("serie_incidencia", padrao, "", lambda: indicadores.serie_incidencia(padrao)),
        ("tendencia", padrao, "", lambda: indicadores.tendencia(padrao)),
        ("perfil", padrao, "", lambda: indicadores.perfil(padrao)),
        ("clinico", padrao, "", lambda: indicadores.clinico(padrao)),
        ("comorbidades", padrao, "", lambda: indicadores.comorbidades(padrao)),
        ("novos_vs_retratamento", padrao, "",
         lambda: indicadores.novos_vs_retratamento(padrao)),
    ]
    for nivel in NIVEIS_GEO:
        tarefas.append(
            ("mapa", padrao, nivel, lambda n=nivel: indicadores.mapa(padrao, n))
        )

    agregados: dict[str, object] = {}
    total_ms = 0.0
    for nome, filtros, extra, calcular in tarefas:
        t0 = time.perf_counter()
        valor = calcular()
        ms = (time.perf_counter() - t0) * 1000
        total_ms += ms
        agregados[precomputado.chave(nome, filtros, extra)] = valor
        rotulo = f"{nome}({extra})" if extra else nome
        print(f"  {rotulo:26s} {ms:7.1f} ms")

    # round-trip pelo json aqui, e não só na gravação, para uma chave problemática
    # estourar com nome e não virar um arquivo corrompido lá na frente
    texto = json.dumps(agregados, ensure_ascii=False, default=_json_ok)
    destino = precomputado.gravar(json.loads(texto))

    print(f"\n  {len(agregados)} agregados · {total_ms:.0f} ms de cálculo evitados "
          f"por processo")
    print(f"  {destino.relative_to(RAIZ)} · {destino.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
