"""Gráficos ECharts como componente próprio — para a transição existir.

O Altair redesenha do zero a cada rerun: o Vega-Lite não anima entre dois
estados. Este módulo serve `src/componente_grafico/` (ECharts 5 vendorado)
como componente estático: o iframe e a instância do gráfico ficam vivos
entre reruns, e cada render é um `setOption` — o ECharts interpola o que
mudou (barra crescendo, barra trocando de posição, linha se redesenhando).

A migração é gráfico a gráfico. O `graficos.py` Altair continua valendo
para o que ainda não passou; o que passou tem aqui uma função que devolve a
**opção** ECharts (um dict), e o `app.py` a entrega a :func:`desenhar`.

Regras da opção, para a animação funcionar:

- todo item de dado leva ``name``: é por ele que o ECharts casa o item
  antigo com o novo e anima a diferença;
- a série leva ``id`` fixo, pelo mesmo motivo;
- o clique volta como ``{"nonce", "name", "chave"}``, com nonce novo a cada
  clique (mesma regra do mapa — `mapa_componente`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit.components.v1 as components

from .theme import componentes as ui
from .theme import tokens

DIRETORIO = Path(__file__).resolve().parent / "componente_grafico"

#: Durações da animação, em ms. Mais curtas que o voo do mapa (700): o
#: gráfico é secundário na leitura e não pode terminar depois dele.
ANIMACAO_ENTRADA_MS = 500
ANIMACAO_ATUALIZACAO_MS = 550

#: Fonte e tamanhos do tema do Altair (`graficos.tema`), para os dois
#: conviverem sem parecer duas famílias.
_FONTE_PX = 12
_COR_EIXO = "rgba(128,128,128,.35)"
_COR_GRADE = "rgba(128,128,128,.18)"

_componente = components.declare_component("grafico_echarts", path=str(DIRETORIO))


def desenhar(option: dict, *, altura: int, key: str):
    """Renderiza a opção ECharts e devolve o último clique (ou ``None``).

    A ``key`` é estável por gráfico — é ela que mantém a instância viva.
    """
    return _componente(
        option=json.dumps(option, ensure_ascii=False, default=_serializar),
        altura=int(altura),
        key=key,
        default=None,
    )


def _serializar(valor):
    """Números do numpy/pandas viram números; o resto, texto."""
    try:
        import numpy as np

        if isinstance(valor, np.generic):
            return valor.item()
    except ImportError:  # pragma: no cover
        pass
    if valor is pd.NA or (isinstance(valor, float) and valor != valor):
        return None
    return str(valor)


def alvo_do_clique(evento, nonce_visto: str | None) -> tuple[str | None, str | None]:
    """``(chave clicada, nonce)`` se o evento é novo; ``(None, None)`` se não."""
    if not isinstance(evento, dict):
        return None, None
    nonce = evento.get("nonce")
    if not nonce or nonce == nonce_visto:
        return None, None
    chave = evento.get("chave")
    if chave in (None, ""):
        chave = evento.get("name")
    return (str(chave) if chave not in (None, "") else None), nonce


def _base() -> dict:
    """O que todo gráfico ECharts daqui compartilha: fonte, animação, eixo."""
    return {
        "animationDuration": ANIMACAO_ENTRADA_MS,
        "animationDurationUpdate": ANIMACAO_ATUALIZACAO_MS,
        "animationEasingUpdate": "cubicOut",
        "textStyle": {"fontFamily": tokens.FONTE, "fontSize": _FONTE_PX},
        "tooltip": {
            "trigger": "item",
            "backgroundColor": "rgba(17,24,39,.96)",
            "borderWidth": 0,
            "textStyle": {"color": "#fff", "fontSize": _FONTE_PX},
        },
    }


def ranking(
    dados: pd.DataFrame,
    *,
    rotulo: str,
    cor: str,
    escala=None,
    selecionado: str | None = None,
    largura_rotulo: int = 150,
) -> dict:
    """Barras horizontais das maiores geografias, clicáveis — em ECharts.

    Mesmas decisões do `graficos.ranking` Altair: horizontal, cor por classe
    do mapa quando há ``escala`` (a barra é da cor do polígono), legenda
    desligada porque a do mapa vale para os dois. O que muda é o que o
    ECharts dá de graça: ao mudar recorte, ano ou métrica, cada barra
    **desliza** para o valor e a posição novos, casada pelo nome.

    ``dados`` tem ``chave``, ``nome`` e ``valor``. A barra ``selecionado``
    (chave) fica opaca e as demais recuam — o destaque do mapa e do ranking
    é o mesmo.
    """
    opt = _base()
    if dados.empty:
        opt.update({
            "title": {
                "text": "Sem dados para ranquear neste recorte",
                "left": "center", "top": "middle",
                "textStyle": {"fontSize": _FONTE_PX, "fontWeight": "normal"},
            },
        })
        return opt

    ordenado = dados.sort_values(["valor", "nome"], ascending=[True, True])
    if escala is not None:
        from . import mapa

        classes = mapa.classificar(ordenado["valor"], escala)
        cores = [escala.cores.get(c, cor) for c in classes]
    else:
        cores = [cor] * len(ordenado)

    itens = []
    for (chave, nome, valor), tom in zip(
        ordenado[["chave", "nome", "valor"]].itertuples(index=False), cores, strict=True
    ):
        recuado = selecionado is not None and str(chave) != str(selecionado)
        itens.append({
            "name": str(nome),
            "value": None if pd.isna(valor) else float(valor),
            "chave": str(chave),
            "itemStyle": {"color": tom, "opacity": 0.55 if recuado else 1.0},
        })

    opt.update({
        "grid": {"left": largura_rotulo + 8, "right": 16, "top": 8, "bottom": 40},
        "xAxis": {
            "type": "value",
            "name": rotulo,
            "nameLocation": "middle",
            "nameGap": 26,
            "nameTextStyle": {"fontSize": _FONTE_PX},
            "axisLine": {"lineStyle": {"color": _COR_EIXO}},
            "axisTick": {"lineStyle": {"color": _COR_EIXO}},
            "splitLine": {"lineStyle": {"color": _COR_GRADE}},
            "axisLabel": {"fontSize": _FONTE_PX},
        },
        "yAxis": {
            "type": "category",
            "data": [i["name"] for i in itens],
            "axisLine": {"lineStyle": {"color": _COR_EIXO}},
            "axisTick": {"show": False},
            "axisLabel": {
                "fontSize": _FONTE_PX,
                "width": largura_rotulo,
                "overflow": "truncate",
            },
        },
        "series": [{
            "id": "ranking",
            "type": "bar",
            "data": itens,
            "barCategoryGap": "28%",
            "itemStyle": {"borderRadius": [0, 3, 3, 0]},
            "emphasis": {"itemStyle": {"opacity": 1.0}},
            "cursor": "pointer",
        }],
    })
    # O formato pt-BR (vírgula, uma casa) é montado no JavaScript a partir
    # deste rótulo: um `formatter` de texto do ECharts não formata número.
    opt["tooltip"]["rotuloValor"] = rotulo
    opt["tooltip"]["casas"] = 1
    return opt


def composicao(
    dados: pd.DataFrame,
    *,
    rotulo: str,
    cor: str,
    largura_rotulo: int = 220,
    ordem_dos_dados: bool = False,
) -> dict:
    """Distribuição de uma variável do SINAN, em barras horizontais — ECharts.

    Mesmas decisões do `graficos.composicao` Altair: percentual quando a base
    sustenta e contagem quando não (a decisão vem de `leitura.composicao`),
    ordem por frequência salvo variável numérica, o nome da variável como
    título. Ao mudar o recorte, cada categoria desliza para o valor novo —
    casada pelo nome —, e as dez do painel trocam juntas.

    O tooltip vem pronto de cada item (``tooltip``, HTML), formatado em
    pt-BR aqui: o ECharts não formata número por texto.
    """
    opt = _base()
    opt["title"] = {
        "text": rotulo,
        "left": 0,
        "top": 0,
        "textStyle": {"fontSize": 13, "fontWeight": 600},
    }
    if dados.empty:
        opt["title"] = {
            "text": "Sem registro desta variável no recorte",
            "left": "center", "top": "middle",
            "textStyle": {"fontSize": _FONTE_PX, "fontWeight": "normal"},
        }
        return opt

    base = dados.copy()
    percentual = "pct" in base.columns and base["pct"].notna().any()
    base["valor"] = pd.to_numeric(base["pct"] if percentual else base["n"], errors="coerce")
    titulo_x = "% dos casos" if percentual else "Casos"

    if not ordem_dos_dados:
        base = base.sort_values("valor", ascending=False)
    # Eixo de categoria cresce de baixo para cima: o primeiro da lista fica
    # embaixo, então a ordem de leitura se inverte aqui.
    base = base.iloc[::-1]

    itens = []
    for linha in base.itertuples(index=False):
        n = getattr(linha, "n", None)
        pct = getattr(linha, "pct", None)
        partes = [f"<b>{linha.categoria}</b>", f"Casos: <b>{ui.formatar_inteiro(None if pd.isna(n) else float(n))}</b>"]
        if percentual and pct is not None and not pd.isna(pct):
            partes.append(f"% dos casos: <b>{ui.formatar_decimal(float(pct), 1)}</b>")
        itens.append({
            "name": str(linha.categoria),
            "value": None if pd.isna(linha.valor) else float(linha.valor),
            "tooltip": "<br/>".join(partes),
        })

    opt.update({
        "grid": {"left": largura_rotulo + 8, "right": 16, "top": 34, "bottom": 40},
        "xAxis": {
            "type": "value",
            "name": titulo_x,
            "nameLocation": "middle",
            "nameGap": 26,
            "nameTextStyle": {"fontSize": _FONTE_PX},
            "splitNumber": 5,
            "axisLine": {"lineStyle": {"color": _COR_EIXO}},
            "axisTick": {"lineStyle": {"color": _COR_EIXO}},
            "splitLine": {"lineStyle": {"color": _COR_GRADE}},
            "axisLabel": {"fontSize": _FONTE_PX},
        },
        "yAxis": {
            "type": "category",
            "data": [i["name"] for i in itens],
            "axisLine": {"lineStyle": {"color": _COR_EIXO}},
            "axisTick": {"show": False},
            "axisLabel": {
                "fontSize": _FONTE_PX,
                "width": largura_rotulo,
                "overflow": "truncate",
            },
        },
        "series": [{
            "id": "composicao",
            "type": "bar",
            "data": itens,
            "barCategoryGap": "30%",
            "itemStyle": {"color": cor, "borderRadius": [0, 2, 2, 0]},
        }],
    })
    return opt
