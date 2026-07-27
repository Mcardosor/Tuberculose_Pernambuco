"""
mapas.py — coropléticos de PE em três níveis geográficos
════════════════════════════════════════════════════════
Município (185) · Região de Saúde (12) · Macrorregião de Saúde (4).

Plotly puro com GeoJSON local, como no painel nacional: o servidor manda a
geometria uma vez (cacheada por processo) e o browser desenha. Sem Folium, sem
tiles externos, sem st_folium — foi o que tirou o mapa do v1 dos 30–40 s.

Escala de cor: os dados de PE são muito assimétricos (a Região Metropolitana
concentra 82% das notificações). Uma escala linear pintaria quase tudo da cor
mais clara, então usamos quantis da distribuição observada — mesma preocupação
que no painel Superset de PE, onde isso foi resolvido com break_points manuais.
"""

from __future__ import annotations

import json
from functools import lru_cache

import plotly.graph_objects as go

from src.constantes import (
    GEOJSON, GRAFICO_BASE, NIVEIS_GEO,
    SEQ_ABANDONO, SEQ_CASOS, SEQ_CURA, SEQ_INCIDENCIA,
    fmt_dec, fmt_int,
)

# ── Métricas oferecidas no seletor do mapa ────────────────────────────────────
METRICAS = {
    "casos": {
        "rotulo": "Casos notificados",
        "escala": SEQ_CASOS,
        "formato": fmt_int,
        "sufixo": "",
    },
    "incidencia": {
        "rotulo": "Incidência /100 mil",
        "escala": SEQ_INCIDENCIA,
        "formato": fmt_dec,
        "sufixo": " /100 mil",
    },
    "abandono_pct": {
        "rotulo": "Abandono %",
        "escala": SEQ_ABANDONO,
        "formato": fmt_dec,
        "sufixo": "%",
    },
    "cura_pct": {
        "rotulo": "Cura %",
        "escala": SEQ_CURA,
        "formato": fmt_dec,
        "sufixo": "%",
    },
}

@lru_cache(maxsize=3)
def geojson(nivel: str) -> dict:
    """GeoJSON do nível, carregado uma vez por processo."""
    return json.loads(GEOJSON[nivel].read_text(encoding="utf-8"))


# ── Enquadramento ─────────────────────────────────────────────────────────────
# `geo.fitbounds="locations"` é ignorado nesta versão do Plotly: o mapa fica com
# lonaxis [-180,180] e PE vira um ponto de 5 px no meio do mundo. Então o
# enquadramento é calculado aqui e passado como lonaxis/lataxis explícitos.
# Efeito colateral bem-vindo: ao filtrar por uma região, o mapa dá zoom nela.

@lru_cache(maxsize=3)
def _bbox_por_id(nivel: str) -> dict[str, tuple[float, float, float, float]]:
    """(lon_min, lat_min, lon_max, lat_max) de cada feição do nível."""
    caixas = {}
    for feat in geojson(nivel)["features"]:
        lon_min = lat_min = float("inf")
        lon_max = lat_max = float("-inf")

        def _percorre(coords):
            nonlocal lon_min, lat_min, lon_max, lat_max
            if coords and isinstance(coords[0], (int, float)):
                lon, lat = coords[0], coords[1]
                lon_min, lon_max = min(lon_min, lon), max(lon_max, lon)
                lat_min, lat_max = min(lat_min, lat), max(lat_max, lat)
            else:
                for c in coords:
                    _percorre(c)

        _percorre(feat["geometry"]["coordinates"])
        caixas[str(feat["id"])] = (lon_min, lat_min, lon_max, lat_max)
    return caixas


def _extremos(nivel: str, ids: list[str]) -> tuple[float, float, float, float]:
    """Bounding box das unidades visíveis, já com folga aplicada."""
    caixas = _bbox_por_id(nivel)
    visiveis = [caixas[i] for i in ids if i in caixas] or list(caixas.values())

    lon_min = min(c[0] for c in visiveis)
    lat_min = min(c[1] for c in visiveis)
    lon_max = max(c[2] for c in visiveis)
    lat_max = max(c[3] for c in visiveis)

    # Folga proporcional, com um mínimo para não colar um município só na borda.
    folga_lon = max((lon_max - lon_min) * 0.04, 0.12)
    folga_lat = max((lat_max - lat_min) * 0.04, 0.12)
    return (lon_min - folga_lon, lat_min - folga_lat,
            lon_max + folga_lon, lat_max + folga_lat)


def _enquadramento(nivel: str, ids: list[str]) -> dict:
    """Layout do eixo geográfico ajustado às unidades visíveis."""
    lon0, lat0, lon1, lat1 = _extremos(nivel, ids)
    return dict(
        visible=False,
        bgcolor="rgba(0,0,0,0)",
        projection_type="mercator",
        lonaxis=dict(range=[lon0, lon1]),
        lataxis=dict(range=[lat0, lat1]),
    )


# Largura de referência da coluna do mapa (3/5 do container de 1400px, com
# folga para o padding do Streamlit). Só serve para escolher a altura.
_LARGURA_REF = 760


def altura_sugerida(nivel: str, ids: list[str]) -> int:
    """Altura que evita faixas vazias acima e abaixo do mapa.

    O Plotly ajusta o eixo geográfico para caber nos dois sentidos, então uma
    altura fixa em cima de uma geometria larga e baixa (PE inteiro tem
    proporção ~2,7:1) desperdiça metade do gráfico. Aqui a altura é derivada da
    proporção real do recorte: PE inteiro fica achatado, um município isolado
    fica alto.
    """
    lon0, lat0, lon1, lat1 = _extremos(nivel, ids)
    proporcao = (lon1 - lon0) / max(lat1 - lat0, 1e-6)
    return max(320, min(640, round(_LARGURA_REF / proporcao) + 40))


def _colorscale(cores: list[str]) -> list[list]:
    n = len(cores) - 1
    return [[i / n, c] for i, c in enumerate(cores)]


def _escala_quantis(valores: list[float], n_ticks: int = 6):
    """Reposiciona os valores pela distribuição acumulada (ECDF).

    Os dados de PE são extremamente assimétricos: Recife sozinho tem ~35% das
    notificações do estado, e a maioria dos municípios fica em dezenas de casos.
    Numa escala linear isso pinta 180 dos 185 municípios da cor mais clara e o
    mapa não informa nada.

    Aqui cada unidade recebe como cor a sua POSIÇÃO na distribuição (0 = menor,
    1 = maior), o que distribui as cores por igual. O valor real continua no
    hover, e a colorbar é rotulada com valores reais nas posições certas — ou
    seja, a legenda continua legível em casos/percentual, não em "quantil".

    É o mesmo remédio dos `break_points` manuais usados no painel Superset de PE,
    só que derivado dos dados em vez de calibrado à mão.

    Devolve (z_plotado, tickvals, ticktext_valores) ou None se não compensar.
    """
    limpos = [v for v in valores if v is not None]
    if len(limpos) < n_ticks or min(limpos) == max(limpos):
        return None

    ordenados = sorted(limpos)
    total = len(ordenados)

    def _posicao(v: float) -> float:
        # fração de unidades com valor menor — ECDF por busca binária
        lo, hi = 0, total
        while lo < hi:
            meio = (lo + hi) // 2
            if ordenados[meio] < v:
                lo = meio + 1
            else:
                hi = meio
        return lo / (total - 1)

    z = [_posicao(v) if v is not None else None for v in valores]

    # Ticks: valores reais nos percentis 0, 20, 40, 60, 80, 100
    passo = (total - 1) / (n_ticks - 1)
    reais, posicoes = [], []
    for i in range(n_ticks):
        v = ordenados[round(i * passo)]
        if reais and v == reais[-1]:
            continue  # percentis empatados (muitos zeros) — não repete o tick
        reais.append(v)
        posicoes.append(_posicao(v))
    return z, posicoes, reais


def figura(dados: list[dict], nivel: str, metrica: str = "casos",
           altura: int | None = None) -> go.Figure:
    """Coroplético do nível ativo.

    `dados` = saída de indicadores.mapa(f, nivel) — uma linha por unidade,
    inclusive as sem casos. O clique é tratado pelo chamador via on_select.
    """
    cfg = METRICAS.get(metrica, METRICAS["casos"])
    fmt = cfg["formato"]
    valores = [d[metrica] for d in dados]
    ids = [d["id"] for d in dados]
    if altura is None:
        altura = altura_sugerida(nivel, ids)

    hover = [
        f"<b>{d['nome']}</b><br>"
        f"Casos: <b>{fmt_int(d['casos'])}</b>"
        + (f" · novos: <b>{fmt_int(d['novos'])}</b>" if d["novos"] != d["casos"] else "")
        + f"<br>Incidência: <b>{fmt_dec(d['incidencia'])}</b> /100 mil"
        + f"<br>Cura: <b>{fmt_dec(d['cura_pct'])}%</b> · "
          f"Abandono: <b>{fmt_dec(d['abandono_pct'])}%</b>"
        + f"<br>Óbito por TB: <b>{fmt_dec(d['obito_pct'])}%</b> · "
          f"HIV+: <b>{fmt_dec(d['hiv_pct'])}%</b>"
        + (f"<br><span style='color:#8b949e'>população {fmt_int(d['populacao'])} pessoas-ano</span>"
           if d["populacao"] else "")
        + ("" if nivel == "municipio"
           else "<br><span style='color:#8b949e'>clique para detalhar</span>")
        for d in dados
    ]

    # Nas contagens e na incidência a distribuição é muito concentrada e pede a
    # escala por quantis; cura% e abandono% já são bem distribuídos e ficam mais
    # fáceis de ler numa escala linear.
    z = valores
    ticks = None
    if metrica in ("casos", "incidencia"):
        transformado = _escala_quantis(valores)
        if transformado:
            z, posicoes, reais = transformado
            ticks = (posicoes, [fmt(v) for v in reais])

    choropleth = dict(
        geojson=geojson(nivel),
        featureidkey="id",
        locations=ids,
        z=z,
        colorscale=_colorscale(cfg["escala"]),
        marker_line_color="#ffffff",
        marker_line_width=0.6 if nivel == "municipio" else 1.4,
        customdata=hover,
        hovertemplate="%{customdata}<extra></extra>",
        colorbar=dict(
            title=dict(text=cfg["rotulo"], side="right",
                       font=dict(size=10, color="#57606a")),
            thickness=10, len=0.6, x=0.99, y=0.5,
            tickfont=dict(size=10, color="#57606a"),
            outlinewidth=0,
        ),
        selected=dict(marker=dict(opacity=1.0)),
        unselected=dict(marker=dict(opacity=0.55)),
    )

    if ticks:
        choropleth["colorbar"]["tickvals"] = ticks[0]
        choropleth["colorbar"]["ticktext"] = ticks[1]

    fig = go.Figure(go.Choropleth(**choropleth))
    fig.update_layout(
        **{k: v for k, v in GRAFICO_BASE.items()
           if k not in ("xaxis", "yaxis", "margin")},
        geo=_enquadramento(nivel, ids),
        height=altura,
        margin=dict(l=0, r=0, t=0, b=0),
        clickmode="event+select",
        dragmode=False,
    )
    return fig


def id_clicado(evento, dados: list[dict]) -> str | None:
    """Extrai o id da unidade clicada do evento de seleção do st.plotly_chart."""
    if not evento or not getattr(evento, "selection", None):
        return None
    pontos = evento.selection.points or []
    if not pontos:
        return None
    p = pontos[0]
    if p.get("location") is not None:
        return str(p["location"])
    indice = p.get("point_index")
    return dados[indice]["id"] if indice is not None and indice < len(dados) else None


def nome_do_nivel(nivel: str) -> str:
    return NIVEIS_GEO[nivel]["rotulo"]
