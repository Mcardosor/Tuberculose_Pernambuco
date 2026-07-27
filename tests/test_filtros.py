"""
Combinações de filtro — inclusive as degeneradas.

Exercita o caminho real do app (agregações + construção das figuras) para cada
combinação. O objetivo não é conferir valores, é garantir que nada explode e que
nenhuma taxa sai do intervalo possível.

Foi este arquivo que pegou o crash de `int(NaN)` com filtros geográficos
contraditórios.
"""

from __future__ import annotations

import pytest

from conftest import sem_cache
from src import graficos, indicadores, mapas
from src.filtros import Filtros

NIVEIS = ("municipio", "regiao_saude", "macro_saude")


def _combinacoes(anos, meta):
    macros = meta["macros"]
    return {
        "serie completa": Filtros(anos=anos),
        "ano único mais recente": Filtros(anos=(max(anos),)),
        "ano único mais antigo": Filtros(anos=(min(anos),)),
        "anos não contíguos": Filtros(anos=(min(anos), 2010, max(anos))),
        "uma macrorregião": Filtros(anos=anos, macros=(macros[0],)),
        "todas as macrorregiões": Filtros(anos=anos, macros=tuple(macros)),
        "município grande": Filtros(anos=anos, municipios=("Recife",)),
        "município minúsculo": Filtros(anos=anos, municipios=("Ingazeira",)),
        "município + ano único": Filtros(anos=(max(anos),), municipios=("Recife",)),
        "só mulheres": Filtros(anos=anos, sexo=("Feminino",)),
        "indígena": Filtros(anos=anos, racas=("Indigena",)),
        "HIV positivo": Filtros(anos=anos, hiv=("Positivo",)),
        "extrapulmonar": Filtros(anos=anos, formas=("Extrapulmonar",)),
        "toda vulnerabilidade em AND": Filtros(anos=anos, vuln=tuple(meta["vulneraveis"])),
        "toda comorbidade em AND": Filtros(anos=anos, agravos=tuple(meta["agravos"])),
        "geo contraditório": Filtros(anos=anos, macros=("Agreste",), municipios=("Recife",)),
        "geo redundante": Filtros(anos=anos, macros=("Metropolitana",),
                                  regioes=("Recife",), municipios=("Recife", "Olinda")),
        "recorte quase vazio": Filtros(anos=(min(anos),), municipios=("Ingazeira",),
                                       sexo=("Feminino",), hiv=("Positivo",)),
    }


@pytest.fixture(scope="module")
def combinacoes(anos, meta):
    return _combinacoes(anos, meta)


def _ids(anos, meta):
    return list(_combinacoes(anos, meta))


@pytest.mark.lento
@pytest.mark.parametrize("nome", [
    "serie completa", "ano único mais recente", "ano único mais antigo",
    "anos não contíguos", "uma macrorregião", "todas as macrorregiões",
    "município grande", "município minúsculo", "município + ano único",
    "só mulheres", "indígena", "HIV positivo", "extrapulmonar",
    "toda vulnerabilidade em AND", "toda comorbidade em AND",
    "geo contraditório", "geo redundante", "recorte quase vazio",
])
def test_combinacao_nao_quebra_e_e_coerente(combinacoes, nome):
    f = combinacoes[nome]
    r = sem_cache(indicadores.resumo)(f)

    # Recorte vazio é resultado legítimo (o app mostra aviso e para) — mas
    # chegar até aqui sem exceção já é o que este teste garante.
    if r["total"] == 0:
        return

    assert r["novos"] <= r["total"]
    assert r["encerrados"] <= r["total"]
    assert r["incidencia"] >= 0
    for campo in ("taxa_cura", "taxa_abandono", "taxa_cura_novo",
                  "taxa_cura_retrat", "hiv_pct", "hiv_cobertura"):
        assert 0 <= r[campo] <= 100, f"{campo} fora de 0–100: {r[campo]}"

    for nivel in NIVEIS:
        dados = sem_cache(indicadores.mapa)(f, nivel)
        assert sum(d["casos"] for d in dados) == r["total"], f"mapa/{nivel}"
        for metrica in mapas.METRICAS:
            mapas.figura(dados, nivel, metrica)
        assert mapas.altura_sugerida(nivel, [d["id"] for d in dados]) > 0

    serie = sem_cache(indicadores.serie_incidencia)(f)
    graficos.linha_incidencia(serie)
    graficos.linha_incidencia(serie, chave="mortalidade")

    t = sem_cache(indicadores.tendencia)(f)
    graficos.mensal(t["mensal"], t["ano"])
    graficos.anual(t["anual"], t["ano"])
    graficos.indicadores(t["indicadores"], list(t["indicadores"]["series"]))

    p = sem_cache(indicadores.perfil)(f)
    graficos.donut(p["sexo"])
    graficos.bar_v(p["raca_cor"])
    graficos.stacked100(p["desfecho_por_raca"])
    graficos.piramide(p["piramide_casos"])
    graficos.piramide(p["piramide_obitos"])

    c = sem_cache(indicadores.clinico)(f)
    graficos.donut(c["status_hiv"])
    graficos.coinfeccao_geo(c["coinfeccao_geo"])
    graficos.indicadores(c["coorte_por_tipo"], ["Caso novo", "Retratamento"])
    if c["tempo_tratamento"]:
        graficos.hist_tempo(c["tempo_tratamento"])

    cm = sem_cache(indicadores.comorbidades)(f)
    graficos.bar_h(cm["agravos"], pct_total=cm["total"])
    graficos.heatmap(cm["heatmap"])
    if cm["desfecho_por_vulneravel"]["categorias"]:
        graficos.stacked100(cm["desfecho_por_vulneravel"])

    coorte, _ = sem_cache(indicadores.coorte)(f)
    graficos.barras_desfecho(coorte)
    graficos.barras_novos_retratamento(sem_cache(indicadores.novos_vs_retratamento)(f))


@pytest.mark.lento
def test_todos_os_municipios_individualmente(anos, meta):
    """Cada um dos 185 municípios como filtro único.

    É onde aparecem os N pequenos: municípios com menos de 50 casos, zero
    encerrados num ano, nenhum caso em população vulnerável.
    """
    for h in meta["hierarquia"]:
        f = Filtros(anos=anos, municipios=(h["municipio"],))
        r = sem_cache(indicadores.resumo)(f)
        assert r["total"] >= 0
        if r["total"]:
            assert 0 <= r["taxa_cura"] <= 100, h["municipio"]
            dados = sem_cache(indicadores.mapa)(f, "municipio")
            assert sum(d["casos"] for d in dados) == r["total"], h["municipio"]


def test_recorte_geografico_vazio_nao_estoura(anos):
    """Regressão: `int(x or 0)` estourava com NaN quando o geo não casava nada.

    `sum()` do SQL devolve NULL sem linhas → NaN no pandas → e NaN é *verdadeiro*
    em Python, então o `or 0` não protegia e o `int()` derrubava a página.
    """
    f = Filtros(anos=anos, macros=("Agreste",), municipios=("Recife",))
    pop = sem_cache(indicadores.populacao)(f)
    assert pop["pessoas_ano"] == 0
    assert pop["pop_ano_ref"] == 0

    r = sem_cache(indicadores.resumo)(f)
    assert r["total"] == 0
    assert r["incidencia"] == 0


def test_filtros_sao_hashaveis_e_servem_de_chave_de_cache(anos):
    """`Filtros` é frozen — é o que permite usá-lo como chave de @st.cache_data."""
    a = Filtros(anos=anos, macros=("Agreste",))
    b = Filtros(anos=anos, macros=("Agreste",))
    assert a == b and hash(a) == hash(b)
    assert len({a, b}) == 1


def test_where_sql_usa_parametros_e_nao_interpolacao(anos):
    """Valores de filtro entram como parâmetro, nunca concatenados no SQL."""
    f = Filtros(anos=anos, municipios=("Recife'; DROP TABLE tb; --",))
    where, params = f.where_sql()
    assert "DROP TABLE" not in where
    assert "Recife'; DROP TABLE tb; --" in params
