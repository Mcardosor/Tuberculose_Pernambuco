"""
app.py — Dashboard TB Pernambuco
════════════════════════════════
Um "frankenstein" deliberado dos três painéis da família Cenários+:

  • esqueleto  → dashboard-tb-recife (hero + KPIs fixos no topo + abas)
  • gráficos   → dashboard-tb-v3, o painel nacional (pirâmide etária, composição
                 100% de desfecho, heatmap, oportunidade do tratamento…)
  • mapa       → três níveis da hierarquia de saúde de PE, os mesmos do painel
                 Superset: município, região de saúde e macrorregião
  • Análise Livre → o próprio Apache Superset de PE, embutido

Rodar local:  python -m streamlit run app.py   →  http://localhost:8501
"""

from __future__ import annotations

import html
import os

import streamlit as st
import streamlit.components.v1 as components

from src import banco, graficos, indicadores, mapas, precomputado, styles
from src.constantes import (
    ANO_FIM, ANO_INICIO, COR_ABANDONO, COR_CURA, COR_HIV, COR_MASC, COR_OBITO,
    DENOMINADOR_MINIMO_TAXA, META_ABANDONO_OMS, NIVEIS_GEO, NIVEL_PADRAO,
    PLOTLY_CFG, fmt_dec, fmt_int,
)
from src.filtros import Filtros
from src.seguranca import url_segura

st.set_page_config(page_title="Dashboard TB | Pernambuco", page_icon="🩺", layout="wide")
styles.inject_css()
styles.navbar()


# ── Pré-aquecimento da conexão ────────────────────────────────────────────────
# A visão padrão vem inteira do `_agregados.json` gerado no ETL, então a primeira
# tela nem toca no DuckDB. O custo frio migrou para a PRIMEIRA interação com
# filtro — é ela que materializa as tabelas em memória. Esta thread faz isso em
# segundo plano enquanto o usuário lê o hero.
@st.cache_resource(show_spinner=False)
def _aquecer() -> bool:
    import threading

    def _fundo():
        try:
            banco.escalar("SELECT count(*) FROM tb")
        except Exception:
            pass  # aquecimento é best-effort: falhar aqui não pode derrubar a página

    threading.Thread(target=_fundo, daemon=True).start()
    return True


_aquecer()

if not precomputado.disponivel():
    st.sidebar.caption(
        "⚙️ Agregados pré-computados ausentes ou desatualizados — "
        "rode `python etl/precomputar.py`. O painel funciona normalmente, "
        "só carrega mais devagar."
    )

META = indicadores.meta()
ANOS = META["anos"]
ANO_PARCIAL = META["ano_parcial"]
ANOS_COMPLETOS = [a for a in ANOS if a != ANO_PARCIAL] or ANOS

# URL do Superset de PE — configurável por ambiente (produção usa a VM).
SUPERSET_URL = os.getenv(
    "SUPERSET_URL",
    "http://localhost:8590/superset/dashboard/tuberculose-pe/?standalone=1",
)

_MS = dict(label_visibility="collapsed", placeholder="Todos")


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — filtros (geografia em cascata: macro → região → município)
# ══════════════════════════════════════════════════════════════════════════════
def _preset_anos(anos: list[int]) -> None:
    st.session_state["f_anos"] = anos


def _limpar_geo_abaixo() -> None:
    """Ao mudar a macrorregião, as seleções de região/município ficam inválidas."""
    st.session_state["f_regioes"] = []
    st.session_state["f_municipios"] = []


def _limpar_municipios() -> None:
    st.session_state["f_municipios"] = []


def render_sidebar() -> Filtros:
    with st.sidebar:
        st.markdown("## 🩺 TB · Pernambuco")

        # ── Período ───────────────────────────────────────────────────────────
        st.caption("📅 Ano de notificação")
        c1, c2 = st.columns(2)
        c1.button("Último ano", width="stretch",
                  on_click=_preset_anos, args=([max(ANOS_COMPLETOS)],))
        c2.button("Últimos 5", width="stretch",
                  on_click=_preset_anos, args=(ANOS_COMPLETOS[-5:],))
        c1.button("Últimos 10", width="stretch",
                  on_click=_preset_anos, args=(ANOS_COMPLETOS[-10:],))
        c2.button("Série completa", width="stretch",
                  on_click=_preset_anos, args=(list(ANOS),))

        st.session_state.setdefault("f_anos", list(ANOS))
        anos = st.multiselect("Anos", options=list(reversed(ANOS)),
                              key="f_anos", label_visibility="collapsed")
        if not anos:
            anos = list(ANOS)
        if ANO_PARCIAL in anos:
            st.caption(f"⚠️ {ANO_PARCIAL}: dados parciais "
                       "(atraso de notificação do SINAN).")

        # ── Geografia em cascata ──────────────────────────────────────────────
        st.caption("📍 Hierarquia de saúde")
        macros = st.multiselect("Macrorregião", options=META["macros"],
                                key="f_macros", on_change=_limpar_geo_abaixo, **_MS)
        regioes = st.multiselect("Região de Saúde",
                                 options=indicadores.regioes_de(tuple(macros)),
                                 key="f_regioes", on_change=_limpar_municipios, **_MS)
        municipios = st.multiselect(
            "Município",
            options=indicadores.municipios_de(tuple(macros), tuple(regioes)),
            key="f_municipios", **_MS,
        )

        # ── Perfil ────────────────────────────────────────────────────────────
        with st.expander("👤 Perfil do paciente"):
            sexo = st.multiselect("Sexo", META["opcoes"]["sexo"], key="f_sexo", **_MS)
            forma = st.multiselect("Forma clínica", META["opcoes"]["formas"],
                                   key="f_formas", **_MS)
            raca = st.multiselect("Raça/cor", META["opcoes"]["racas"],
                                  key="f_racas", **_MS)

        with st.expander("🏥 Perfil clínico"):
            entrada = st.multiselect("Tipo de entrada", META["opcoes"]["entradas"],
                                     key="f_entradas", **_MS)
            hiv = st.multiselect("Status HIV", META["opcoes"]["hiv"], key="f_hiv", **_MS)

        with st.expander("⚠️ Populações vulneráveis"):
            st.caption("Incluir apenas pacientes que sejam:")
            vuln = [c for c, rot in META["vulneraveis"].items()
                    if st.checkbox(rot, key=f"f_v_{c}")]

        with st.expander("💊 Comorbidades"):
            st.caption("Incluir apenas pacientes com:")
            agravos = [c for c, rot in META["agravos"].items()
                       if st.checkbox(rot, key=f"f_a_{c}")]

        st.divider()
        if st.button("🔄 Limpar cache", width="stretch"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()

    return Filtros(
        anos=tuple(sorted(set(anos))),
        macros=tuple(sorted(macros)),
        regioes=tuple(sorted(regioes)),
        municipios=tuple(sorted(municipios)),
        sexo=tuple(sorted(sexo)),
        formas=tuple(sorted(forma)),
        racas=tuple(sorted(raca)),
        entradas=tuple(sorted(entrada)),
        hiv=tuple(sorted(hiv)),
        vuln=tuple(sorted(vuln)),
        agravos=tuple(sorted(agravos)),
    )


F = render_sidebar()

try:
    R = indicadores.resumo(F)
except Exception as erro:  # noqa: BLE001 — a mensagem precisa chegar ao usuário
    st.error(f"Erro ao carregar dados: {erro}")
    st.info("Rode `python etl/preparar_dados.py` e `python etl/baixar_populacao.py` "
            "para gerar os arquivos em `dados_dashboard/`.")
    st.stop()

if not R["total"]:
    st.warning("Nenhum caso corresponde aos filtros selecionados. "
               "Amplie o recorte na barra lateral.")
    st.stop()

with st.sidebar:
    st.metric("Registros filtrados", fmt_int(R["total"]),
              f"de {fmt_int(R['total_base'])} "
              f"({fmt_dec(100 * R['total'] / R['total_base'])}%)",
              delta_color="off")
    st.caption("Fonte: SINAN NET · Ministério da Saúde")


# ══════════════════════════════════════════════════════════════════════════════
#  HERO + KPIs
# ══════════════════════════════════════════════════════════════════════════════
_label_anos = (f"{min(F.anos)}–{max(F.anos)}" if len(F.anos) > 1 else str(F.anos[0]))
_badges = [
    (_label_anos, "accent"),
    (f"{fmt_int(R['total'])} casos notificados", ""),
    (f"{R['municipios']} municípios com casos", ""),
    ("Fonte: SINAN · residência", ""),
]
if ANO_PARCIAL in F.anos:
    _badges.append((f"{ANO_PARCIAL} parcial", "warn"))

styles.hero(
    titulo=f"Tuberculose · {F.rotulo_geo()}",
    subtitulo=(
        "Vigilância epidemiológica da tuberculose em Pernambuco por município, "
        "região de saúde e macrorregião de saúde. Recorte por residência do "
        f"paciente — a mesma regra do boletim epidemiológico estadual ({ANO_INICIO}–{ANO_FIM})."
    ),
    badges=_badges,
)

_abandono_alto = R["taxa_abandono"] > META_ABANDONO_OMS
styles.kpi_row([
    {"label": "Incidência", "value": fmt_dec(R["incidencia"]),
     "sub": f"/100 mil · {fmt_int(R['novos'])} casos novos",
     "icon": "📈", "accent": COR_MASC},
    {"label": "Cura (casos novos)", "value": f"{fmt_dec(R['taxa_cura_novo'])}%",
     "sub": f"retratamento {fmt_dec(R['taxa_cura_retrat'])}%",
     "icon": "✅", "accent": COR_CURA},
    {"label": "Abandono", "value": f"{fmt_dec(R['taxa_abandono'])}%",
     "sub": ("⚠ acima da meta OMS (5%)" if _abandono_alto else "dentro da meta OMS"),
     "icon": "⚠️", "accent": COR_ABANDONO, "alert": _abandono_alto},
    {"label": "Coinfecção HIV", "value": f"{fmt_dec(R['hiv_pct'])}%",
     "sub": f"entre testados · cobertura {fmt_dec(R['hiv_cobertura'])}%",
     "icon": "🧬", "accent": COR_HIV},
    {"label": "Óbitos por TB (SINAN)", "value": fmt_int(R["obitos_tb"]),
     "sub": f"{fmt_dec(R['taxa_obito'])}% dos encerrados",
     "icon": "⚰️", "accent": COR_OBITO},
])

if F.filtros_de_perfil_ativos:
    st.caption(
        "ℹ️ Com filtros de perfil ativos, a **incidência** deixa de ser populacional: "
        "o numerador é o subgrupo filtrado, mas o denominador continua sendo toda a "
        "população residente (o IBGE não estratifica por essas variáveis)."
    )

st.divider()

# Navegação por segmented control, não st.tabs.
#
# O painel de Recife usa abas, mas ele não tem filtros na sidebar. Aqui tem, e o
# st.tabs traz dois problemas sérios nesse cenário:
#   1. a aba selecionada volta para a primeira a cada rerun — ou seja, mexer em
#      qualquer filtro jogaria o usuário de volta ao Mapa;
#   2. o Streamlit executa o corpo de TODAS as abas em todo rerun, mesmo as
#      invisíveis — 5 seções de consultas em vez de 1.
# Com o segmented control só a seção ativa roda e a escolha sobrevive ao rerun.
# É a mesma correção adotada no painel nacional (v3).
_SECOES = [
    "🗺️  Mapa", "📊  Epidemiologia", "👤  Perfil & Clínico",
    "⚠️  Comorbidades", "🔬  Análise Livre",
]
secao = st.segmented_control("Seções", _SECOES, key="_secao",
                             default=_SECOES[0], label_visibility="collapsed")
st.write("")


# ══════════════════════════════════════════════════════════════════════════════
#  1 · MAPA — três níveis geográficos (fragment: trocar nível não recarrega tudo)
# ══════════════════════════════════════════════════════════════════════════════
@st.fragment
def secao_mapa(f: Filtros) -> None:
    st.session_state.setdefault("_nivel", NIVEL_PADRAO)

    # O clique no mapa é gravado numa chave própria e só depois copiado para a
    # do selectbox: o Streamlit proíbe escrever na chave de um widget já criado
    # no mesmo run, e o clique acontece DEPOIS que o selectbox foi desenhado.
    if st.session_state.get("_unidade_clique"):
        st.session_state["_unidade_sel"] = st.session_state.pop("_unidade_clique")

    # ── Linha 1: os três botões de nível geográfico ───────────────────────────
    st.caption("**Agregar o mapa por:**")
    cols = st.columns([1.3, 1.3, 1.3, 3])
    for col, (chave, cfg_botao) in zip(cols, NIVEIS_GEO.items()):
        ativo = st.session_state["_nivel"] == chave
        if col.button(f"{cfg_botao['icone']} {cfg_botao['rotulo']}", width="stretch",
                      type="primary" if ativo else "secondary",
                      key=f"btn_nivel_{chave}"):
            st.session_state["_nivel"] = chave
            # a unidade selecionada não existe no novo nível
            st.session_state["_unidade_sel"] = "—"
            st.rerun(scope="fragment")

    nivel = st.session_state["_nivel"]
    cfg = NIVEIS_GEO[nivel]

    dados = indicadores.mapa(f, nivel)
    com_casos = [d for d in dados if d["casos"]]

    # ── Linha 2: métrica plotada e drill-down, ambos rotulados ────────────────
    # Sem rótulo visível estas duas caixas viram adivinhação — uma controla a
    # COR do mapa, a outra abre um painel de detalhe. São coisas bem diferentes.
    c_metrica, c_detalhe, _ = st.columns([2, 2, 2])

    rotulo_metrica = c_metrica.selectbox(
        "Métrica do mapa", [m["rotulo"] for m in mapas.METRICAS.values()],
        key="_metrica",
        help="Define a cor do mapa e a ordenação do ranking ao lado.",
    )
    metrica = next(k for k, m in mapas.METRICAS.items()
                   if m["rotulo"] == rotulo_metrica)

    unidade = None
    if nivel != "municipio":
        opcoes = ["—"] + [d["nome"] for d in com_casos]
        if st.session_state.get("_unidade_sel", "—") not in opcoes:
            st.session_state["_unidade_sel"] = "—"
        escolha = c_detalhe.selectbox(
            f"Abrir detalhe de uma {cfg['rotulo'].lower()}", opcoes,
            key="_unidade_sel",
            help=("Abre um painel abaixo do mapa com os indicadores dessa unidade. "
                  "Não altera o resto do painel — para restringir tudo (KPIs do topo, "
                  "gráficos, outras seções) use os filtros da barra lateral."),
        )
        unidade = None if escolha == "—" else escolha

    st.caption(
        f"{len(com_casos)} de {len(dados)} {cfg['plural']} com notificação no recorte"
        + (" · clique num polígono do mapa faz o mesmo que o seletor de detalhe"
           if nivel != "municipio"
           else " · o município é o nível mais fino da hierarquia")
    )

    # A altura vem da geometria do recorte (PE inteiro é largo e baixo; um
    # município isolado é quase quadrado) — o ranking acompanha para as duas
    # colunas terminarem na mesma linha.
    altura = mapas.altura_sugerida(nivel, [d["id"] for d in dados])

    col_mapa, col_rank = st.columns([3, 2])

    with col_mapa:
        fig = mapas.figura(dados, nivel, metrica, altura=altura)
        evento = st.plotly_chart(
            fig, width="stretch", config=PLOTLY_CFG,
            on_select="rerun" if nivel != "municipio" else "ignore",
            selection_mode="points", key=f"mapa_{nivel}_{metrica}",
        )
        if nivel != "municipio":
            clicado = mapas.id_clicado(evento, dados)
            if clicado and clicado != unidade:
                st.session_state["_unidade_clique"] = clicado
                st.rerun(scope="fragment")
        # A legenda tem que descrever a escala REALMENTE usada — antes ela
        # dizia "quantis" mesmo nas taxas, que são lineares.
        st.caption(
            ("Escala em quantis (a Região Metropolitana concentra a maior parte "
             "dos casos, o que achataria uma escala linear)"
             if mapas.usa_quantis(metrica)
             else f"Escala linear · cinza = menos de {DENOMINADOR_MINIMO_TAXA} "
                  "casos encerrados, taxa não exibida")
            + " · contornos: SES-PE."
        )

    with col_rank:
        st.markdown(f"**{rotulo_metrica} — ranking por {cfg['rotulo'].lower()}**")

        # Taxa só entra no ranking com denominador suficiente. Sem isso, um
        # município que encerrou 2 casos e curou os 2 lidera com "100%" acima
        # de um que curou 180 de 200 — é ruído, não desempenho.
        elegiveis = [d for d in com_casos if mapas.tem_base(d, metrica)]
        excluidos = len(com_casos) - len(elegiveis)
        top = sorted(elegiveis, key=lambda d: d[metrica], reverse=True)

        # Cabem ~26 px por barra na altura do mapa; nos níveis de região e
        # macro a lista inteira cabe, no de município mostramos o topo.
        limite = min(len(top), max(6, altura // 26))
        campo_den = mapas.METRICAS[metrica]["denominador"]
        fmt_metrica = mapas.METRICAS[metrica]["formato"]
        sufixo = mapas.METRICAS[metrica]["sufixo"]

        if top:
            st.plotly_chart(
                graficos.bar_h(
                    [{"label": d["nome"], "valor": d[metrica]} for d in top[:limite]],
                    altura=altura,
                    cor="#e8871e" if metrica != "cura_pct" else COR_CURA,
                    # com denominador ao lado do número, dá para julgar o peso
                    texto=[f"{fmt_metrica(d[metrica])}{sufixo}"
                           + (f"  (n={fmt_int(d[campo_den])})" if campo_den else "")
                           for d in top[:limite]],
                ),
                width="stretch", config=PLOTLY_CFG, key=f"rank_{nivel}_{metrica}",
            )
        else:
            st.info(f"Nenhum(a) {cfg['rotulo'].lower()} com pelo menos "
                    f"{DENOMINADOR_MINIMO_TAXA} casos encerrados neste recorte.")

        legendas = []
        if len(top) > limite:
            legendas.append(f"Top {limite} de {len(top)}")
        if excluidos:
            legendas.append(
                f"{excluidos} {cfg['plural']} fora do ranking e em cinza no mapa "
                f"(menos de {DENOMINADOR_MINIMO_TAXA} casos encerrados — a taxa "
                "seria ruído)"
            )
        if legendas:
            st.caption(" · ".join(legendas) + ". Lista completa na tabela abaixo.")

    if unidade:
        st.divider()
        _drill_down(f, nivel, unidade)

    with st.expander(f"📋 Tabela — todos os {cfg['plural']} ({len(dados)})"):
        st.dataframe(
            [
                {
                    cfg["rotulo"]: d["nome"],
                    "Casos": d["casos"],
                    "Casos novos": d["novos"],
                    "Incidência /100 mil": d["incidencia"],
                    "Cura %": d["cura_pct"],
                    "Abandono %": d["abandono_pct"],
                    "Óbito TB %": d["obito_pct"],
                    "HIV+ %": d["hiv_pct"],
                }
                for d in dados
            ],
            width="stretch", height=360, hide_index=True,
        )


def _drill_down(f: Filtros, nivel: str, unidade: str) -> None:
    """O que há dentro do polígono clicado — um nível abaixo na hierarquia."""
    d = indicadores.detalhe_unidade(f, nivel, unidade)
    k = d["kpis"]

    cab, fechar = st.columns([5, 1])
    cab.subheader(f"📍 {unidade}")
    cab.caption(f"{fmt_int(k['total'])} notificações · taxas de coorte sobre "
                f"{fmt_int(k['encerrados'])} casos encerrados")
    if fechar.button("✕ Fechar", key="fechar_unidade", width="stretch"):
        st.session_state["_unidade_clique"] = "—"
        st.rerun(scope="fragment")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cura", f"{fmt_dec(k['cura_pct'])}%", help="Meta OMS: ≥ 85%.")
    m2.metric(("🔴" if k["abandono_pct"] >= META_ABANDONO_OMS else "🟢") + " Abandono",
              f"{fmt_dec(k['abandono_pct'])}%", help="Meta OMS: < 5%.")
    m3.metric("Óbito por TB", f"{fmt_dec(k['obito_pct'])}%",
              help="Desfecho SINAN sobre casos encerrados.")
    m4.metric("HIV+", f"{fmt_dec(k['hiv_pct'])}%", help="Entre os casos testados.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Casos por {d['rotulo_filho']}**")
        st.plotly_chart(
            graficos.bar_h([{"label": x["nome"], "valor": x["casos"]}
                            for x in d["filhos"][:15]],
                           altura=max(280, min(len(d["filhos"]), 15) * 30)),
            width="stretch", config=PLOTLY_CFG, key=f"drill_bar_{unidade}",
        )
    with c2:
        st.markdown("**Série anual**")
        st.plotly_chart(
            graficos.anual(d["serie"], ano_destaque=max(f.anos)),
            width="stretch", config=PLOTLY_CFG, key=f"drill_serie_{unidade}",
        )


# ══════════════════════════════════════════════════════════════════════════════
#  2 · EPIDEMIOLOGIA — incidência, coorte, sazonalidade, tendência
# ══════════════════════════════════════════════════════════════════════════════
def secao_epidemiologia(f: Filtros) -> None:
    serie = indicadores.serie_incidencia(f)
    coorte, encerrados = indicadores.coorte(f)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Incidência por 100 mil habitantes", help=(
            "**Fonte:** SINAN-TB · **Numerador:** casos novos (Caso Novo + Não Sabe "
            "+ Pós-óbito)  \n**Denominador:** população IBGE do recorte no ano  \n"
            "**Cálculo:** coeficiente anual por 100 mil habitantes.  \n"
            "*A série mostra todos os anos; os anos filtrados aparecem destacados.*"))
        st.plotly_chart(graficos.linha_incidencia(serie, anos_destaque=f.anos),
                        width="stretch", config=PLOTLY_CFG)
    with c2:
        st.subheader("Desfecho dos casos encerrados", help=(
            "**Fonte:** SINAN-TB (situação de encerramento)  \n"
            f"**Denominador:** {fmt_int(encerrados)} casos encerrados  \n"
            "**Exclui:** transferidos e sem informação — não têm desfecho conhecido  \n"
            "**Metodologia:** coorte (MS/OMS)."))
        st.plotly_chart(graficos.barras_desfecho(coorte),
                        width="stretch", config=PLOTLY_CFG)

    st.divider()
    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Casos novos × retratamento por ano", help=(
            "**Casos novos:** Caso Novo + Não Sabe + Pós-óbito  \n"
            "**Retratamento:** Recidiva + Reingresso após abandono  \n"
            "*Mantidos separados: têm dinâmicas e taxas de cura distintas.*"))
        st.plotly_chart(graficos.barras_novos_retratamento(
            indicadores.novos_vs_retratamento(f)),
            width="stretch", config=PLOTLY_CFG)
    with c4:
        st.subheader("Mortalidade por 100 mil habitantes", help=(
            "**Fonte:** desfecho de encerramento do SINAN (`Óbito por TB`).  \n"
            "⚠️ Diferente do painel de Recife, aqui **não há linkage com o SIM** — "
            "a mortalidade real tende a ser maior que a registrada no SINAN."))
        st.plotly_chart(
            graficos.linha_incidencia(serie, chave="mortalidade",
                                      anos_destaque=f.anos, cor=COR_OBITO,
                                      rotulo_numerador="óbitos por TB"),
            width="stretch", config=PLOTLY_CFG)
        st.caption(
            "⚠️ A subida ao longo da série reflete sobretudo a melhora do "
            "preenchimento do campo de encerramento no SINAN, não só aumento real "
            "de mortalidade. Para a série oficial é preciso o linkage com o SIM."
        )

    st.divider()
    t = indicadores.tendencia(f)
    k = t["kpis"]

    ka, kb, kc = st.columns(3)
    if k["variacao_pct"] is None:
        ka.metric("Tendência vs histórico", "➡️ Sem histórico")
    else:
        v = k["variacao_pct"]
        rotulo = "⬆️ Para mais" if v > 5 else ("⬇️ Para menos" if v < -5 else "➡️ Estável")
        ka.metric("Tendência vs histórico", rotulo,
                  f"{v:+.1f}% vs {ANO_INICIO}–{t['ano'] - 1}", delta_color="inverse")
    kb.metric(f"Total {t['ano']}", fmt_int(k["total_ano"]), "casos notificados",
              delta_color="off")
    kc.metric("Média anual histórica", fmt_int(k["media_anual_hist"]),
              f"casos/ano · {ANO_INICIO}–{t['ano'] - 1}", delta_color="off")
    if t["ano"] == ANO_PARCIAL:
        st.caption(
            f"⚠️ O ano de referência é {ANO_PARCIAL}, que ainda recebe notificações — "
            "a comparação com a média histórica está subestimada. Para uma leitura "
            f"fechada, tire {ANO_PARCIAL} do filtro de anos."
        )

    c5, c6 = st.columns(2)
    with c5:
        st.subheader(f"Casos por mês — {t['ano']} vs média histórica", help=(
            "Barras acima da linha pontilhada indicam meses com mais casos "
            "que o padrão histórico do recorte."))
        st.plotly_chart(graficos.mensal(t["mensal"], t["ano"]),
                        width="stretch", config=PLOTLY_CFG)
    with c6:
        st.subheader(f"Evolução anual — {ANO_INICIO}–{max(ANOS)}", help=(
            "Total de notificações por ano; a barra vermelha destaca o ano "
            "de referência (o mais recente entre os filtrados)."))
        st.plotly_chart(graficos.anual(t["anual"], t["ano"]),
                        width="stretch", config=PLOTLY_CFG)

    st.divider()
    st.subheader("Indicadores clínicos ao longo do tempo", help=(
        "Séries calculadas sobre toda a base do recorte geográfico, "
        "independentemente do filtro de anos. As linhas pontilhadas marcam "
        "as metas da OMS quando o indicador correspondente está selecionado."))
    sel = st.multiselect(
        "Indicadores", options=list(t["indicadores"]["series"].keys()),
        default=["Coinfecção HIV (%)", "Taxa de cura (%)", "Taxa de abandono (%)"],
        label_visibility="collapsed",
    )
    if sel:
        st.plotly_chart(graficos.indicadores(t["indicadores"], sel, t["ano"]),
                        width="stretch", config=PLOTLY_CFG)


# ══════════════════════════════════════════════════════════════════════════════
#  3 · PERFIL & CLÍNICO
# ══════════════════════════════════════════════════════════════════════════════
def secao_perfil(f: Filtros) -> None:
    p = indicadores.perfil(f)
    c = indicadores.clinico(f)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Por sexo")
        st.caption("Historicamente a TB afeta mais homens — em PE são ~2 casos "
                   "masculinos para cada feminino.")
        st.plotly_chart(graficos.donut(p["sexo"]), width="stretch", config=PLOTLY_CFG)
    with c2:
        st.subheader("Forma clínica")
        st.caption("Pulmonar transmite pelo ar — maior risco de contágio. "
                   "Extrapulmonar atinge outros órgãos.")
        st.plotly_chart(graficos.donut(p["forma"]), width="stretch", config=PLOTLY_CFG)

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Tipo de entrada")
        st.caption("Caso novo: primeiro diagnóstico. Recidiva: adoeceu de novo após "
                   "cura. Reingresso: voltou após abandono.")
        st.plotly_chart(graficos.bar_h(p["tipo_entrada"]),
                        width="stretch", config=PLOTLY_CFG)
    with c4:
        st.subheader("Por raça/cor")
        st.caption("A TB afeta desproporcionalmente populações negras e indígenas.")
        st.plotly_chart(graficos.bar_v(p["raca_cor"]),
                        width="stretch", config=PLOTLY_CFG)

    st.divider()
    st.subheader("Desfecho × raça/cor", help=(
        "Cada coluna soma 100%. Diferenças refletem desigualdades no acesso e na "
        "qualidade do cuidado, não diferenças biológicas."))
    st.plotly_chart(graficos.stacked100(p["desfecho_por_raca"]),
                    width="stretch", config=PLOTLY_CFG)

    st.divider()
    pi1, pi2 = st.columns(2)
    with pi1:
        st.subheader("Pirâmide etária — casos")
        st.caption("🟠 Faixas abaixo de 15 anos (público prioritário) destacadas.")
        st.plotly_chart(graficos.piramide(p["piramide_casos"]),
                        width="stretch", config=PLOTLY_CFG)
    with pi2:
        st.subheader("Pirâmide etária — óbitos por TB")
        st.caption("Desfecho SINAN, por faixa etária e sexo.")
        st.plotly_chart(graficos.piramide(p["piramide_obitos"]),
                        width="stretch", config=PLOTLY_CFG)

    st.divider()
    d1, d2, d3 = st.columns(3)
    with d1:
        st.subheader("Status HIV")
        st.plotly_chart(graficos.donut(c["status_hiv"]),
                        width="stretch", config=PLOTLY_CFG)
    with d2:
        st.subheader("Baciloscopia — 1ª amostra")
        st.plotly_chart(graficos.donut(c["baciloscopia"]),
                        width="stretch", config=PLOTLY_CFG)
    with d3:
        st.subheader("Teste molecular (TRM-TB)")
        st.plotly_chart(graficos.donut(c["teste_molecular"], max_cat=6),
                        width="stretch", config=PLOTLY_CFG)

    e1, e2 = st.columns([2, 3])
    with e1:
        st.subheader("Desfecho × status HIV")
        st.caption("Cada coluna soma 100%. HIV+ tende a menor cura e maior óbito.")
        st.plotly_chart(graficos.stacked100(c["desfecho_por_hiv"]),
                        width="stretch", config=PLOTLY_CFG)
    with e2:
        st.subheader("Coinfecção TB-HIV por região de saúde")
        st.caption("% de positivos entre os testados — não é quantidade absoluta.")
        st.plotly_chart(graficos.coinfeccao_geo(c["coinfeccao_geo"]),
                        width="stretch", config=PLOTLY_CFG)

    st.divider()
    st.subheader("Taxa de cura por tipo de entrada", help=(
        "Coorte fechada. Denominador: casos encerrados. Meta OMS: ≥ 85% de cura."))
    st.plotly_chart(
        graficos.indicadores(c["coorte_por_tipo"], ["Caso novo", "Retratamento"]),
        width="stretch", config=PLOTLY_CFG)

    st.divider()
    st.subheader("⏱️ Oportunidade do tratamento")
    st.caption("Tempo entre diagnóstico e início do tratamento — começar em ≤7 dias "
               "interrompe a cadeia de transmissão mais cedo.")
    tt = c["tempo_tratamento"]
    if tt is None:
        st.info("Datas insuficientes para calcular o tempo de tratamento no recorte.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        mediana = tt["mediana_inicio"]
        m1.metric("Início do tratamento (mediana)",
                  f"{mediana:.0f} " + ("dia" if round(mediana) == 1 else "dias"),
                  help=(f"Sobre {fmt_int(tt['n'])} casos com as duas datas válidas. "
                        "Mediana 0 costuma significar que o SINAN registrou início "
                        "= data do diagnóstico, não atendimento imediato."))
        m2.metric("Início em ≤ 7 dias", f"{fmt_dec(tt['pct_ate_7d'])}%",
                  help="Início oportuno.")
        m3.metric("Início tardio (> 30 dias)", f"{fmt_dec(tt['pct_acima_30d'])}%",
                  help="Atraso preocupante.")
        if tt["duracao_mediana"] is not None:
            m4.metric("Duração do tratamento (mediana)",
                      f"{tt['duracao_mediana']:.0f} dias",
                      help="Esquema básico esperado: ~180 dias.")
        st.plotly_chart(graficos.hist_tempo(tt), width="stretch", config=PLOTLY_CFG)


# ══════════════════════════════════════════════════════════════════════════════
#  4 · COMORBIDADES & VULNERABILIDADES
# ══════════════════════════════════════════════════════════════════════════════
def secao_comorbidades(f: Filtros) -> None:
    d = indicadores.comorbidades(f)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Comorbidades associadas")
        st.caption("Diabéticos têm risco ~3× maior de desenvolver TB. "
                   "Percentual sobre o total filtrado.")
        st.plotly_chart(
            graficos.bar_h(d["agravos"], altura=360, cor=COR_HIV,
                           pct_total=d["total"]),
            width="stretch", config=PLOTLY_CFG)
    with c2:
        st.subheader("Populações vulneráveis")
        st.caption("Situação de rua: risco até 56× maior. "
                   "Privados de liberdade: até 28×.")
        for p in d["populacoes"]:
            st.metric(p["label"], fmt_int(p["valor"]),
                      f"{fmt_dec(p['pct'])}% do total", delta_color="off")

    st.divider()
    st.subheader("Desfecho × populações vulneráveis", help=(
        "Cada barra soma 100% dentro do seu grupo. Um mesmo caso pode pertencer a "
        "mais de uma população, então as barras não somam o total de casos."))
    if d["desfecho_por_vulneravel"]["categorias"]:
        st.plotly_chart(graficos.stacked100(d["desfecho_por_vulneravel"]),
                        width="stretch", config=PLOTLY_CFG)
    else:
        st.info("Nenhum caso em população vulnerável no recorte selecionado.")

    st.divider()
    st.subheader("Comorbidades por macrorregião de saúde")
    st.caption("% de casos com cada comorbidade em cada macrorregião — "
               "células mais quentes indicam maior concentração.")
    st.plotly_chart(graficos.heatmap(d["heatmap"]),
                    width="stretch", config=PLOTLY_CFG)


# ══════════════════════════════════════════════════════════════════════════════
#  5 · ANÁLISE LIVRE — Apache Superset de PE embutido
# ══════════════════════════════════════════════════════════════════════════════
def secao_analise_livre() -> None:
    st.subheader("Análise livre no Apache Superset")
    st.markdown(
        "Exploração ad-hoc dos microdados de PE no **Superset** — a mesma instância "
        "usada na entrega do painel estadual. Ali dá para montar gráficos novos, "
        "cruzar variáveis e salvar dashboards próprios, sem passar por este painel."
    )

    col_url, col_abrir = st.columns([4, 1])
    url = col_url.text_input(
        "URL do Superset", value=SUPERSET_URL, label_visibility="collapsed",
        help="Definida pela variável de ambiente SUPERSET_URL. "
             "Em produção aponta para a instância na VM.",
    )

    # A URL é texto livre digitado pelo usuário e vai parar dentro de um atributo
    # HTML. Sem validação, algo como `x" onload="…` fecharia o atributo e injetaria
    # script na própria página; e um `javascript:` no src executaria direto.
    # Por isso: só http/https passam, e o valor é escapado antes de virar HTML.
    url_ok = url_segura(url)
    if url_ok is None:
        st.error("URL inválida — informe um endereço `http://` ou `https://`.")
        return

    col_abrir.link_button("↗ Abrir em nova aba", url_ok, width="stretch")

    st.caption(
        "⚠️ O Superset bloqueia embed por padrão (Content Security Policy). Se o "
        "quadro abaixo aparecer em branco, é isso: libere este domínio em "
        "`SUPERSET_FRAME_ANCESTORS` no `superset_config.py` do projeto "
        "`dashboard-tb-pe`, ou use o botão de abrir em nova aba."
    )

    components.html(
        f'<iframe class="superset-frame" src="{html.escape(url_ok, quote=True)}" '
        f'width="100%" height="860" frameborder="0" allow="fullscreen"></iframe>',
        height=880,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  RENDER
# ══════════════════════════════════════════════════════════════════════════════
if secao == _SECOES[1]:
    secao_epidemiologia(F)
elif secao == _SECOES[2]:
    secao_perfil(F)
elif secao == _SECOES[3]:
    secao_comorbidades(F)
elif secao == _SECOES[4]:
    secao_analise_livre()
else:
    secao_mapa(F)

styles.footer()
