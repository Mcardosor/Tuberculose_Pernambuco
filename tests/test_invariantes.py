"""
Invariantes epidemiológicos — o mesmo número calculado por caminhos diferentes
tem que bater.

É a classe de erro mais cara num painel de vigilância: nada quebra, o painel só
mostra um número errado. Cada teste aqui compara duas rotas independentes até o
mesmo valor.
"""

from __future__ import annotations

import pytest

from conftest import sem_cache
from src import banco, indicadores


# ── Composição dos buckets ────────────────────────────────────────────────────
def test_tipos_de_entrada_cobrem_o_total(resumo_padrao):
    """Casos novos + retratamento + transferência + sem informação = total.

    Se um rótulo do SINAN mudar de grafia (ex.: 'Reingresso após Abandono'),
    ele cai silenciosamente fora dos dois buckets e a incidência despenca sem
    nenhum erro. Este teste é o alarme.
    """
    q = banco.query("""
        SELECT count(*) tot,
          count(*) FILTER (WHERE tipo_entrada IN ('Caso Novo','Não Sabe','Pós-óbito')) novos,
          count(*) FILTER (WHERE tipo_entrada IN ('Recidiva','Reingresso após Abandono')) retrat,
          count(*) FILTER (WHERE tipo_entrada = 'Transferência') transf,
          count(*) FILTER (WHERE tipo_entrada = 'Não informado'
                            OR tipo_entrada IS NULL) ni
        FROM tb
    """).iloc[0]
    assert int(q.novos + q.retrat + q.transf + q.ni) == int(q.tot)
    assert resumo_padrao["novos"] == int(q.novos)


def test_encerrados_excluem_transferidos_e_sem_informacao(resumo_padrao):
    """Denominador da coorte = total menos quem não tem desfecho conhecido."""
    fora = banco.escalar("""
        SELECT count(*) FROM tb
        WHERE situacao_encerramento IS NULL
           OR situacao_encerramento IN ('Transferência', 'Não informado')
    """)
    assert resumo_padrao["total"] - int(fora) == resumo_padrao["encerrados"]


def test_coorte_fecha_no_denominador(padrao, resumo_padrao):
    dados, denominador = sem_cache(indicadores.coorte)(padrao)
    assert denominador == resumo_padrao["encerrados"]
    assert sum(d["valor"] for d in dados) == denominador
    assert abs(sum(d["pct"] for d in dados) - 100) <= 1.0


# ── Coerência entre níveis geográficos ────────────────────────────────────────
@pytest.mark.parametrize("nivel", ["municipio", "regiao_saude", "macro_saude"])
def test_mapa_soma_o_total(padrao, resumo_padrao, nivel):
    dados = sem_cache(indicadores.mapa)(padrao, nivel)
    assert sum(d["casos"] for d in dados) == resumo_padrao["total"]


def test_agregacao_dos_municipios_reproduz_regiao_e_macro(padrao, meta):
    """Somar os 185 municípios tem que dar exatamente as 12 regiões e 4 macros.

    Pega erro de hierarquia (município no lugar errado, alias de grafia quebrado).
    """
    por_nome = {x["nome"]: x["casos"] for x in sem_cache(indicadores.mapa)(padrao, "municipio")}
    hier = {h["municipio"]: h for h in meta["hierarquia"]}

    faltantes = [n for n in por_nome if n not in hier]
    assert not faltantes, f"municípios fora da hierarquia: {faltantes}"

    esperado_reg: dict[str, int] = {}
    esperado_macro: dict[str, int] = {}
    for nome, casos in por_nome.items():
        h = hier[nome]
        esperado_reg[h["regiao_saude"]] = esperado_reg.get(h["regiao_saude"], 0) + casos
        esperado_macro[h["macro_saude"]] = esperado_macro.get(h["macro_saude"], 0) + casos

    for x in sem_cache(indicadores.mapa)(padrao, "regiao_saude"):
        assert x["casos"] == esperado_reg.get(x["nome"], 0), f"região {x['nome']}"
    for x in sem_cache(indicadores.mapa)(padrao, "macro_saude"):
        assert x["casos"] == esperado_macro.get(x["nome"], 0), f"macro {x['nome']}"


@pytest.mark.parametrize("nivel", ["macro_saude", "regiao_saude"])
def test_mapa_e_drill_down_concordam(padrao, nivel):
    """`mapa` e `detalhe_unidade` são SQL diferentes — têm que dar o mesmo número."""
    for u in sem_cache(indicadores.mapa)(padrao, nivel)[:5]:
        d = sem_cache(indicadores.detalhe_unidade)(padrao, nivel, u["nome"])
        k = d["kpis"]
        assert u["casos"] == k["total"], f"{nivel}/{u['nome']}: casos"
        assert abs(u["cura_pct"] - k["cura_pct"]) <= 0.05, f"{nivel}/{u['nome']}: cura"
        assert abs(u["abandono_pct"] - k["abandono_pct"]) <= 0.05, f"{nivel}/{u['nome']}: abandono"
        assert abs(u["hiv_pct"] - k["hiv_pct"]) <= 0.05, f"{nivel}/{u['nome']}: hiv"


@pytest.mark.parametrize("nivel", ["macro_saude", "regiao_saude"])
def test_drill_down_filhos_somam_o_pai(padrao, nivel):
    for u in sem_cache(indicadores.mapa)(padrao, nivel)[:5]:
        d = sem_cache(indicadores.detalhe_unidade)(padrao, nivel, u["nome"])
        assert sum(x["casos"] for x in d["filhos"]) == d["kpis"]["total"], u["nome"]


# ── Séries temporais ──────────────────────────────────────────────────────────
def test_series_somam_os_totais(padrao, resumo_padrao):
    serie = sem_cache(indicadores.serie_incidencia)(padrao)
    assert sum(x["novos"] for x in serie) == resumo_padrao["novos"]

    nvr = sem_cache(indicadores.novos_vs_retratamento)(padrao)
    assert sum(x["novos"] for x in nvr) == resumo_padrao["novos"]

    t = sem_cache(indicadores.tendencia)(padrao)
    assert sum(x["casos"] for x in t["anual"]) == resumo_padrao["total"]


# ── Composições percentuais ───────────────────────────────────────────────────
def test_stacked100_fecha_em_cem(padrao):
    perfil = sem_cache(indicadores.perfil)(padrao)
    clinico = sem_cache(indicadores.clinico)(padrao)
    for dp, rotulo in ((perfil["desfecho_por_raca"], "raça"),
                       (clinico["desfecho_por_hiv"], "HIV")):
        assert dp["categorias"], f"{rotulo}: nenhuma categoria"
        for cat in dp["categorias"]:
            soma = sum(dp["pct"][cat].values())
            assert abs(soma - 100) <= 0.35, f"{rotulo}/{cat} soma {soma}"


def test_piramide_perde_apenas_sexo_ignorado(padrao, resumo_padrao):
    """A pirâmide exclui sexo ignorado — a perda tem que ser exatamente essa."""
    p = sem_cache(indicadores.perfil)(padrao)
    na_piramide = sum(p["piramide_casos"]["masculino"]) + sum(p["piramide_casos"]["feminino"])
    elegiveis = banco.escalar(
        "SELECT count(*) FROM tb WHERE idade_anos IS NOT NULL "
        "AND sexo IN ('Masculino','Feminino')"
    )
    assert na_piramide == int(elegiveis)
    assert na_piramide <= resumo_padrao["total"]


# ── Denominador populacional ──────────────────────────────────────────────────
def test_populacao_usa_pessoas_ano(padrao, anos):
    """Série de N anos → denominador é a soma dos N anos, não a de um só.

    Dividir por um ano só inflaria a incidência proporcionalmente ao número
    de anos selecionados.

    O limite superior é N × população do ano de referência (não N × exatamente,
    porque a população cresceu ao longo da série e os anos antigos são menores
    que o de referência).
    """
    n = len(anos)
    pop = sem_cache(indicadores.populacao)(padrao)
    assert pop["anos"] == n
    assert pop["pessoas_ano"] > pop["pop_ano_ref"], "não somou os anos"
    assert pop["pessoas_ano"] < pop["pop_ano_ref"] * n, "somou anos demais"
    # a média anual tem que ser uma população plausível de PE
    media_anual = pop["pessoas_ano"] / n
    assert 7_000_000 < media_anual < 10_000_000, media_anual


def test_ano_parcial_e_detectado_e_nao_presumido(meta):
    """O último ano só é 'parcial' se estiver correndo ou não tiver 12 meses.

    Regressão: a regra foi copiada do painel nacional como "o último ano é
    sempre parcial" e marcava 2025 — ano fechado, com os 12 meses — como
    incompleto, exibindo aviso falso.
    """
    from datetime import date

    ultimo = max(meta["anos"])
    meses = banco.escalar(
        "SELECT count(DISTINCT month(data_notificacao)) FROM tb WHERE ano_notificacao = ?",
        [ultimo],
    )
    esperado = ultimo if (ultimo >= date.today().year or int(meses) < 12) else None
    assert meta["ano_parcial"] == esperado
