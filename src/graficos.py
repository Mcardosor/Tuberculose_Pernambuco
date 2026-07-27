"""
graficos.py — construtores Plotly (tema claro Cenários+)
════════════════════════════════════════════════════════
Portados do painel nacional (dashboard-tb-v3), mais os gráficos de coorte e
incidência do painel de Recife.

Contrato: nenhuma função recebe microdados. Todas recebem os agregados pequenos
do src/indicadores.py (listas de dicts) e só montam a figura.
"""

from __future__ import annotations

import plotly.graph_objects as go

from src.constantes import (
    COR_ABANDONO, COR_CURA, COR_FEM, COR_HIV, COR_MASC, COR_OBITO,
    COR_PRIMARIA, GRAFICO_BASE, H_MEDIUM, H_SMALL,
    META_ABANDONO_OMS, META_CURA_OMS, fmt_dec, fmt_int, tb_color_map,
)

_LEGENDA = GRAFICO_BASE["legend"]


def _layout(fig: go.Figure, altura: int, **extra) -> go.Figure:
    fig.update_layout(**{**GRAFICO_BASE, **extra}, height=altura)
    return fig


def _legenda_h(y: float = 1.12, x: float = 0.0) -> dict:
    return dict(orientation="h", y=y, x=x, **_LEGENDA)


# ══════════════════════════════════════════════════════════════════════════════
#  Categóricos básicos
# ══════════════════════════════════════════════════════════════════════════════
def donut(contagens: list[dict], altura: int = H_SMALL,
          max_cat: int | None = None) -> go.Figure:
    """Rosca com o total no centro. contagens = [{'label','valor'}] em ordem desc."""
    dados = contagens[:max_cat] if max_cat else contagens
    labels = [d["label"] for d in dados]
    valores = [d["valor"] for d in dados]
    cores = tb_color_map(labels)
    total = sum(d["valor"] for d in contagens)

    fig = go.Figure(go.Pie(
        labels=labels, values=valores, hole=0.62,
        marker=dict(colors=[cores[l] for l in labels],
                    line=dict(color="#ffffff", width=2)),
        textinfo="percent", textfont=dict(size=11.5),
        customdata=[fmt_int(v) for v in valores],
        hovertemplate="<b>%{label}</b><br>%{customdata} casos · %{percent}<extra></extra>",
        sort=False,
    ))
    fig.add_annotation(
        text=f"<b>{fmt_int(total)}</b><br>"
             "<span style='font-size:11px;color:#57606a'>casos</span>",
        showarrow=False, font=dict(size=19, color="#24292f"),
    )
    return _layout(fig, altura,
                   legend=dict(orientation="h", yanchor="top", y=-0.05,
                               x=0.5, xanchor="center", **_LEGENDA))


def bar_h(contagens: list[dict], altura: int = H_SMALL, cor: str = COR_PRIMARIA,
          pct_total: int | None = None, cores: list[str] | None = None,
          texto: list[str] | None = None) -> go.Figure:
    """Barras horizontais (ranking).

    `texto` sobrescreve o rótulo de cada barra — usado para mostrar a taxa junto
    do seu denominador (`92,0%  (n=200)`), sem o que não dá para julgar se o
    número tem peso.
    """
    dados = list(reversed(contagens))
    valores = [d["valor"] for d in dados]
    if texto is not None:
        texto = list(reversed(texto))
    elif pct_total:
        texto = [f"{fmt_int(v)}  ({fmt_dec(v / pct_total * 100)}%)" for v in valores]
    else:
        texto = [fmt_int(v) for v in valores]
    fig = go.Figure(go.Bar(
        x=valores, y=[d["label"] for d in dados], orientation="h",
        marker=dict(color=list(reversed(cores)) if cores else cor, cornerradius=5,
                    line=dict(color="#ffffff", width=1)),
        text=texto, textposition="outside",
        textfont=dict(size=11, color="#57606a"), cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
    ))
    fig = _layout(fig, altura)
    fig.update_layout(margin=dict(l=10, r=95, t=10, b=10))
    return fig


def bar_v(contagens: list[dict], altura: int = H_SMALL) -> go.Figure:
    """Barras verticais com cores semânticas por rótulo."""
    labels = [d["label"] for d in contagens]
    cores = tb_color_map(labels)
    fig = go.Figure(go.Bar(
        x=labels, y=[d["valor"] for d in contagens],
        marker=dict(color=[cores[l] for l in labels], cornerradius=6),
        text=[fmt_int(d["valor"]) for d in contagens], textposition="outside",
        textfont=dict(size=11, color="#57606a"), cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>%{text} casos<extra></extra>",
    ))
    return _layout(fig, altura)


def stacked100(dp: dict, altura: int = H_MEDIUM) -> go.Figure:
    """Barras 100% empilhadas. dp = {'categorias','grupos','n','pct'}."""
    categorias, grupos = dp["categorias"], dp["grupos"]
    cores = tb_color_map(grupos)
    fig = go.Figure()
    for g in grupos:
        fig.add_bar(
            name=g, x=categorias,
            y=[dp["pct"][c].get(g, 0) for c in categorias],
            marker=dict(color=cores[g], line=dict(color="#ffffff", width=1)),
            customdata=[fmt_int(dp["n"].get(c, 0)) for c in categorias],
            hovertemplate=(f"<b>%{{x}}</b> · %{{customdata}} casos<br>{g}: "
                           "<b>%{y:.1f}%</b><extra></extra>"),
        )
    fig = _layout(fig, altura, barmode="stack", legend=_legenda_h())
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  Incidência e coorte (herdados do painel de Recife)
# ══════════════════════════════════════════════════════════════════════════════
def linha_incidencia(serie: list[dict], chave: str = "incidencia",
                     anos_destaque: tuple[int, ...] = (),
                     altura: int = H_MEDIUM, cor: str = COR_PRIMARIA,
                     rotulo_numerador: str = "casos novos") -> go.Figure:
    """Coeficiente anual por 100 mil. Anos filtrados aparecem com marcador maior."""
    anos = [s["ano"] for s in serie]
    valores = [s[chave] for s in serie]
    destaque = set(anos_destaque)
    tamanhos = [9 if a in destaque else 5 for a in anos] if destaque else [6] * len(anos)

    # o numerador exibido no hover acompanha a métrica plotada
    campo_num = "obitos" if chave == "mortalidade" else "novos"
    numeradores = [s.get(campo_num, s["novos"]) for s in serie]

    fig = go.Figure(go.Scatter(
        x=anos, y=valores, mode="lines+markers",
        line=dict(color=cor, width=2.6, shape="spline"),
        marker=dict(size=tamanhos, color=cor,
                    line=dict(color="#ffffff", width=1.5)),
        customdata=[[fmt_int(n), fmt_int(s["populacao"])]
                    for n, s in zip(numeradores, serie)],
        hovertemplate=("<b>%{x}</b><br>%{y:.1f} /100 mil<br>"
                       f"%{{customdata[0]}} {rotulo_numerador} · "
                       "pop. %{customdata[1]}<extra></extra>"),
        fill="tozeroy",
        fillcolor="rgba(218,54,51,.07)" if chave == "mortalidade"
                  else "rgba(43,123,185,.08)",
    ))
    return _layout(fig, altura)


def barras_desfecho(coorte: list[dict], altura: int = H_MEDIUM) -> go.Figure:
    """Distribuição do desfecho entre os casos encerrados, com % no rótulo."""
    labels = [d["label"] for d in coorte]
    cores = tb_color_map(labels)
    fig = go.Figure(go.Bar(
        x=labels, y=[d["valor"] for d in coorte],
        marker=dict(color=[cores[l] for l in labels], cornerradius=6),
        text=[f"{fmt_dec(d['pct'])}%" for d in coorte],
        textposition="outside", textfont=dict(size=11, color="#57606a"),
        cliponaxis=False,
        customdata=[fmt_int(d["valor"]) for d in coorte],
        hovertemplate="<b>%{x}</b><br>%{customdata} casos · %{text}<extra></extra>",
    ))
    return _layout(fig, altura)


def barras_novos_retratamento(serie: list[dict], altura: int = H_MEDIUM) -> go.Figure:
    """Casos novos × retratamento por ano — dinâmicas e taxas de cura distintas."""
    anos = [str(s["ano"]) for s in serie]
    fig = go.Figure()
    fig.add_bar(name="Casos novos", x=anos, y=[s["novos"] for s in serie],
                marker=dict(color=COR_CURA, cornerradius=4),
                hovertemplate="<b>%{x}</b><br>%{y} casos novos<extra></extra>")
    fig.add_bar(name="Retratamento", x=anos, y=[s["retratamento"] for s in serie],
                marker=dict(color=COR_ABANDONO, cornerradius=4),
                hovertemplate="<b>%{x}</b><br>%{y} retratamentos<extra></extra>")
    return _layout(fig, altura, barmode="stack", legend=_legenda_h())


def piramide(p: dict, altura: int = 420) -> go.Figure:
    """Pirâmide etária. p = {'faixas','masculino','feminino'}."""
    faixas = p["faixas"]
    jovem = {"0-4", "5-9", "10-14"}  # público prioritário do MS
    cor_m = ["#e8871e" if f in jovem else COR_MASC for f in faixas]
    cor_f = ["#d4a72c" if f in jovem else COR_FEM for f in faixas]
    max_v = max(p["masculino"] + p["feminino"] + [1])

    fig = go.Figure()
    fig.add_bar(
        name="Masculino", y=faixas, x=[-v for v in p["masculino"]], orientation="h",
        marker=dict(color=cor_m, cornerradius=4),
        customdata=[fmt_int(v) for v in p["masculino"]],
        hovertemplate="<b>%{y} anos</b> · Masculino<br>%{customdata} casos<extra></extra>",
    )
    fig.add_bar(
        name="Feminino", y=faixas, x=p["feminino"], orientation="h",
        marker=dict(color=cor_f, cornerradius=4),
        customdata=[fmt_int(v) for v in p["feminino"]],
        hovertemplate="<b>%{y} anos</b> · Feminino<br>%{customdata} casos<extra></extra>",
    )
    fig = _layout(fig, altura, barmode="overlay", legend=_legenda_h(1.1))
    ticks = [-max_v, -max_v // 2, 0, max_v // 2, max_v]
    fig.update_xaxes(range=[-max_v * 1.08, max_v * 1.08], tickvals=ticks,
                     ticktext=[fmt_int(abs(t)) for t in ticks])
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  Recortes geográficos internos
# ══════════════════════════════════════════════════════════════════════════════
def coinfeccao_geo(lista: list[dict], altura: int = H_MEDIUM) -> go.Figure:
    """Positividade HIV por região de saúde — % entre os testados."""
    fig = go.Figure(go.Bar(
        x=[e["nome"] for e in lista], y=[e["pct"] for e in lista],
        marker=dict(color=[e["pct"] for e in lista],
                    colorscale=[[0, "#a5d6ff"], [0.5, COR_HIV], [1, COR_OBITO]],
                    cornerradius=4, showscale=False),
        customdata=[fmt_int(e["n_testado"]) for e in lista],
        text=[fmt_dec(e["pct"]) for e in lista],
        textposition="outside", textfont=dict(size=10, color="#57606a"),
        cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>HIV+: <b>%{y:.1f}%</b><br>"
                      "%{customdata} testados<extra></extra>",
    ))
    fig = _layout(fig, altura)
    fig.update_yaxes(ticksuffix="%")
    fig.update_xaxes(tickangle=-35)
    return fig


def heatmap(hm: dict, altura: int = 340) -> go.Figure:
    """% de casos com cada comorbidade por macrorregião. hm = {'geos','agravos','valores'}."""
    matriz = [[None] * len(hm["geos"]) for _ in hm["agravos"]]
    for x, y, v in hm["valores"]:
        matriz[y][x] = v
    fig = go.Figure(go.Heatmap(
        z=matriz, x=hm["geos"], y=hm["agravos"],
        colorscale=[[0, "#f6f8fa"], [0.35, "#a5d6ff"], [0.65, COR_PRIMARIA], [1, COR_OBITO]],
        xgap=2, ygap=2,
        hovertemplate="<b>%{x}</b> · %{y}<br><b>%{z:.1f}%</b> dos casos<extra></extra>",
        colorbar=dict(thickness=10, ticksuffix="%",
                      tickfont=dict(size=10, color="#57606a"), outlinewidth=0),
    ))
    return _layout(fig, altura)


# ══════════════════════════════════════════════════════════════════════════════
#  Oportunidade do tratamento e tendência
# ══════════════════════════════════════════════════════════════════════════════
def hist_tempo(tt: dict, altura: int = H_SMALL) -> go.Figure:
    """Histograma do tempo diagnóstico → início do tratamento."""
    h = tt["histograma"]
    cores = [COR_CURA, COR_CURA, COR_CURA, COR_ABANDONO,
             COR_ABANDONO, "#f85149", "#f85149"]
    fig = go.Figure(go.Bar(
        x=[b["faixa"] for b in h], y=[b["casos"] for b in h],
        marker=dict(color=cores[: len(h)], cornerradius=6),
        text=[fmt_int(b["casos"]) for b in h], textposition="outside",
        textfont=dict(size=11, color="#57606a"), cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>%{text} casos<extra></extra>",
    ))
    return _layout(fig, altura)


def mensal(m: dict, ano: int, altura: int = H_MEDIUM) -> go.Figure:
    """Casos por mês no ano de referência contra a média histórica mensal."""
    fig = go.Figure()
    fig.add_bar(
        name=f"Casos {ano}", x=m["meses"], y=m["casos"],
        marker=dict(color="#e8871e", cornerradius=6),
        text=[fmt_int(v) for v in m["casos"]], textposition="outside",
        textfont=dict(size=10, color="#57606a"), cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>%{text} casos<extra></extra>",
    )
    if any(v is not None for v in m["media_hist"]):
        fig.add_scatter(
            name="Média histórica mensal", x=m["meses"], y=m["media_hist"],
            mode="lines+markers",
            line=dict(color=COR_PRIMARIA, dash="dash", width=2),
            marker=dict(size=6),
            hovertemplate="<b>%{x}</b><br>média histórica: %{y:,.0f}<extra></extra>",
        )
    return _layout(fig, altura, legend=_legenda_h())


def anual(serie: list[dict], ano_destaque: int, chave: str = "casos",
          altura: int = H_MEDIUM, cor: str = COR_PRIMARIA,
          cor_destaque: str = COR_OBITO) -> go.Figure:
    """Barras por ano com o ano de referência destacado."""
    fig = go.Figure(go.Bar(
        x=[str(s["ano"]) for s in serie], y=[s[chave] for s in serie],
        marker=dict(color=[cor_destaque if s["ano"] == ano_destaque else cor
                           for s in serie], cornerradius=4),
        customdata=[fmt_int(s[chave]) for s in serie],
        hovertemplate="<b>%{x}</b><br>%{customdata} casos<extra></extra>",
    ))
    return _layout(fig, altura)


_CORES_IND = [COR_CURA, COR_ABANDONO, COR_HIV, COR_PRIMARIA, COR_FEM,
              "#e8871e", COR_OBITO, "#54aeff", "#bf91f3"]

# Linhas de meta desenhadas quando o indicador correspondente está selecionado
_METAS = {
    "Taxa de abandono (%)": (META_ABANDONO_OMS, "meta OMS < 5%", COR_ABANDONO),
    "Taxa de cura (%)": (META_CURA_OMS, "meta OMS ≥ 85%", COR_CURA),
}


def indicadores(ind: dict, selecionados: list[str], ano_ref: int | None = None,
                altura: int = 420) -> go.Figure:
    """Séries percentuais ao longo dos anos. ind = {'anos','series'}."""
    fig = go.Figure()
    visiveis = [s for s in selecionados if s in ind["series"]]
    for i, nome in enumerate(visiveis):
        fig.add_scatter(
            name=nome, x=ind["anos"], y=ind["series"][nome], mode="lines+markers",
            line=dict(width=2.4, color=_CORES_IND[i % len(_CORES_IND)], shape="spline"),
            marker=dict(size=5),
            hovertemplate=f"<b>%{{x}}</b> · {nome}<br><b>%{{y:.1f}}%</b><extra></extra>",
        )
    for nome in visiveis:
        if nome in _METAS:
            valor, texto, cor = _METAS[nome]
            fig.add_hline(y=valor, line_dash="dot", line_color=cor, opacity=0.6,
                          annotation_text=texto,
                          annotation_font=dict(color=cor, size=10))
    if ano_ref and ano_ref in ind["anos"]:
        fig.add_vline(x=ano_ref, line_dash="dash", line_color=COR_OBITO, opacity=0.4)

    fig = _layout(fig, altura, legend=_legenda_h(1.14))
    fig.update_yaxes(ticksuffix="%")
    return fig
