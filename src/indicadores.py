"""
indicadores.py — agregações epidemiológicas (DuckDB → dicts pequenos)
═════════════════════════════════════════════════════════════════════
Toda função devolve agregados de poucos KB. Nenhum DataFrame de microdados
sobe para a sessão do Streamlit — é o que mantém o painel rápido mesmo com a
série completa (142 mil notificações, 2001–2025).

Regras de negócio, idênticas às do painel de Recife e do nacional:
  • Incidência usa SÓ casos novos (Caso Novo + Não Sabe + Pós-óbito).
  • Coorte (cura/abandono/óbito) tem denominador = casos ENCERRADOS —
    exclui transferidos e sem informação, que não têm desfecho conhecido.
  • Coinfecção HIV: denominador = testados (Positivo + Negativo).
  • Abandono soma Abandono + Abandono Primário (o SINAN separa os códigos).
  • Denominador populacional: IBGE por município/ano, somado no nível
    geográfico ativo.

Limitação assumida: PE não tem o SIM linkado neste painel (o Recife tem), então
óbito por TB vem do desfecho de encerramento do SINAN — sujeito a subnotificação.
Toda saída que usa esse número carrega `fonte_obitos = "SINAN"` para a UI avisar.
"""

from __future__ import annotations

from dataclasses import replace
from functools import wraps

import streamlit as st

from src import banco, precomputado
from src.constantes import (
    AGRAVOS, DESFECHOS_ABANDONO, DESFECHO_GRUPO, FAIXAS_ETARIAS,
    HIV_TESTADO, NIVEIS_GEO, POPULACOES, TIPOS_INCIDENCIA, TIPOS_RETRATAMENTO,
)
from src.filtros import Filtros

TTL = 3600

# ── Fragmentos SQL reutilizados ───────────────────────────────────────────────
_LISTA = lambda vals: ", ".join(f"'{v}'" for v in vals)  # noqa: E731

SQL_NOVO = f"tipo_entrada IN ({_LISTA(TIPOS_INCIDENCIA)})"
SQL_RETRAT = f"tipo_entrada IN ({_LISTA(TIPOS_RETRATAMENTO)})"
SQL_ENCERRADO = (
    "situacao_encerramento IS NOT NULL "
    "AND situacao_encerramento NOT IN ('Transferência', 'Não informado')"
)
SQL_ABANDONO = f"situacao_encerramento IN ({_LISTA(DESFECHOS_ABANDONO)})"
SQL_HIV_TESTADO = f"status_hiv IN ({_LISTA(HIV_TESTADO)})"

FONTE_OBITOS = "SINAN"


def _precomputa(nome: str):
    """Serve o agregado pronto do ETL quando existir; senão calcula ao vivo.

    Só a visão padrão está pré-computada, então na prática isto acelera o
    primeiro acesso e volta a ser transparente assim que o usuário filtra.
    Aplicar POR DENTRO do @st.cache_data: o cache continua sendo a primeira
    linha de defesa nos reruns seguintes.
    """
    def decorador(fn):
        @wraps(fn)
        def envolvido(f: Filtros, *args, **kwargs):
            pronto = precomputado.obter(nome, f, str(args[0]) if args else "")
            if pronto is not None:
                return pronto
            return fn(f, *args, **kwargs)
        return envolvido
    return decorador


def _num(valor, padrao=0):
    """None/NaN → padrão. NÃO use `valor or padrao` no lugar disto.

    `sum()` do SQL devolve NULL quando nenhuma linha casa, e o pandas traz isso
    como `float('nan')`. Só que NaN é *verdadeiro* em Python, então `nan or 0`
    devolve nan e o `int()` seguinte estoura com "cannot convert float NaN to
    integer". Foi assim que uma combinação geográfica contraditória (macro
    Agreste + município Recife) derrubava a página inteira.
    """
    if valor is None:
        return padrao
    try:
        if valor != valor:  # só NaN é diferente de si mesmo
            return padrao
    except TypeError:
        pass
    return valor


def _taxa(num, den, casas: int = 1) -> float:
    return round(100.0 * num / den, casas) if den else 0.0


def _coef(num, den, por: int = 100_000, casas: int = 1) -> float:
    return round(por * num / den, casas) if den else 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  Metadados — opções dos filtros (uma vez por processo)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=TTL, show_spinner=False)
def meta() -> dict:
    pronto = precomputado.obter("meta")
    if pronto is not None:
        return pronto
    return _meta_ao_vivo()


def _ano_parcial(anos: list[int]) -> int | None:
    """Detecta ano incompleto a partir do DADO, não por suposição.

    O painel nacional assume que o último ano é sempre parcial, porque lá o
    extrato é do ano corrente. Aqui isso seria falso: o extrato de PE vai até
    2025-12-31 e 2025 é um ano fechado, com os 12 meses e volume em linha com
    2023 e 2024. Marcar um ano fechado como "parcial" é pior que não marcar —
    desacredita o aviso quando ele for verdadeiro.

    Regra: o último ano é parcial se ainda está correndo, ou se não tem os 12
    meses de notificação.

    Ressalva que a regra não cobre: o SINAN recebe notificação retroativa, então
    mesmo um ano com 12 meses pode subir um pouco em extrações futuras.
    """
    if not anos:
        return None
    from datetime import date

    ultimo = max(anos)
    if ultimo >= date.today().year:
        return ultimo
    ultimo_mes = banco.escalar(
        "SELECT max(month(data_notificacao)) FROM tb WHERE ano_notificacao = ?",
        [ultimo],
    )
    return ultimo if (ultimo_mes or 12) < 12 else None


def _meta_ao_vivo() -> dict:
    anos = banco.anos_disponiveis()
    hier = banco.hierarquia()
    return {
        "anos": anos,
        "ano_parcial": _ano_parcial(anos),
        "hierarquia": hier.to_dict("records"),
        "macros": sorted(hier["macro_saude"].unique()),
        "opcoes": {
            "sexo": banco.opcoes("sexo"),
            "formas": banco.opcoes("forma"),
            "racas": banco.opcoes("raca_cor"),
            "entradas": banco.opcoes("tipo_entrada"),
            "hiv": banco.opcoes("status_hiv", excluir_vazios=False),
        },
        "agravos": AGRAVOS,
        "vulneraveis": POPULACOES,
        "total_base": int(banco.escalar("SELECT count(*) FROM tb")),
    }


def regioes_de(macros: tuple[str, ...]) -> list[str]:
    """Regiões de saúde contidas nas macrorregiões (cascata do filtro)."""
    hier = meta()["hierarquia"]
    alvo = [h for h in hier if not macros or h["macro_saude"] in macros]
    return sorted({h["regiao_saude"] for h in alvo})


def municipios_de(macros: tuple[str, ...], regioes: tuple[str, ...]) -> list[str]:
    """Municípios contidos no recorte de macro/região (cascata do filtro)."""
    hier = meta()["hierarquia"]
    alvo = [
        h for h in hier
        if (not macros or h["macro_saude"] in macros)
        and (not regioes or h["regiao_saude"] in regioes)
    ]
    return sorted(h["municipio"] for h in alvo)


# ══════════════════════════════════════════════════════════════════════════════
#  População (denominador)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=TTL, show_spinner=False)
def populacao(f: Filtros) -> dict:
    """População-ano do recorte geográfico: soma de habitantes × anos selecionados.

    Somar os anos (pessoas-ano) é o denominador correto quando o numerador é o
    total de casos de vários anos — dividir pela população de um ano só
    inflaria a taxa proporcionalmente ao número de anos.
    """
    where_geo, p_geo = f.where_geo_sql("m")
    anos = f.anos or tuple(meta()["anos"])
    marcadores = ", ".join("?" for _ in anos)
    df = banco.query(
        f"""
        SELECT sum(p.populacao) AS pessoas_ano,
               sum(CASE WHEN p.ano = ? THEN p.populacao ELSE 0 END) AS pop_ano_ref
        FROM pop p JOIN mun m USING (codigo_ibge)
        WHERE {where_geo} AND p.ano IN ({marcadores})
        """,
        [max(anos)] + p_geo + list(anos),
    )
    linha = df.iloc[0]
    return {
        # recorte geográfico vazio (ex.: filtros contraditórios) → sum() é NULL
        "pessoas_ano": int(_num(linha.pessoas_ano)),
        "pop_ano_ref": int(_num(linha.pop_ano_ref)),
        "anos": len(anos),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  KPIs do topo
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=TTL, show_spinner="Calculando indicadores…")
@_precomputa("resumo")
def resumo(f: Filtros) -> dict:
    where, params = f.where_sql()
    df = banco.query(
        f"""
        SELECT
            count(*)                                                   AS total,
            count(*) FILTER ({SQL_NOVO})                               AS novos,
            count(*) FILTER ({SQL_ENCERRADO})                          AS encerrados,
            count(*) FILTER ({SQL_ENCERRADO} AND situacao_encerramento = 'Cura')      AS cura,
            count(*) FILTER ({SQL_ENCERRADO} AND {SQL_ABANDONO})                      AS abandono,
            count(*) FILTER (WHERE situacao_encerramento = 'Óbito por TB')            AS obitos_tb,
            count(*) FILTER ({SQL_ENCERRADO} AND {SQL_NOVO})           AS enc_novo,
            count(*) FILTER ({SQL_ENCERRADO} AND {SQL_NOVO}
                             AND situacao_encerramento = 'Cura')       AS cura_novo,
            count(*) FILTER ({SQL_ENCERRADO} AND {SQL_RETRAT})         AS enc_retrat,
            count(*) FILTER ({SQL_ENCERRADO} AND {SQL_RETRAT}
                             AND situacao_encerramento = 'Cura')       AS cura_retrat,
            count(*) FILTER ({SQL_HIV_TESTADO})                        AS hiv_testado,
            count(*) FILTER (WHERE status_hiv = 'Positivo')            AS hiv_pos,
            count(DISTINCT municipio)                                  AS municipios
        FROM tb WHERE {where}
        """,
        params,
    ).iloc[0]

    pop = populacao(f)
    return {
        "total": int(df.total),
        "novos": int(df.novos),
        "encerrados": int(df.encerrados),
        "municipios": int(df.municipios),
        "incidencia": _coef(df.novos, pop["pessoas_ano"]),
        "mortalidade": _coef(df.obitos_tb, pop["pessoas_ano"]),
        "obitos_tb": int(df.obitos_tb),
        "taxa_cura": _taxa(df.cura, df.encerrados),
        "taxa_cura_novo": _taxa(df.cura_novo, df.enc_novo),
        "taxa_cura_retrat": _taxa(df.cura_retrat, df.enc_retrat),
        "taxa_abandono": _taxa(df.abandono, df.encerrados),
        "taxa_obito": _taxa(df.obitos_tb, df.encerrados),
        "hiv_pct": _taxa(df.hiv_pos, df.hiv_testado),
        "hiv_cobertura": _taxa(df.hiv_testado, df.total),
        "hiv_pos": int(df.hiv_pos),
        "pop": pop,
        "fonte_obitos": FONTE_OBITOS,
        "total_base": meta()["total_base"],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  MAPA — agregação em qualquer um dos três níveis geográficos
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=TTL, show_spinner="Agregando o mapa…")
@_precomputa("mapa")
def mapa(f: Filtros, nivel: str) -> list[dict]:
    """Uma linha por unidade do nível (município / região de saúde / macrorregião).

    Devolve TODAS as unidades do recorte, inclusive as sem notificação no
    período — senão o mapa fica com buracos brancos que parecem erro de
    geometria em vez de "zero casos".
    """
    cfg = NIVEIS_GEO[nivel]
    col = cfg["coluna"]

    where, params = f.where_sql()
    where_geo, p_geo = f.where_geo_sql("m")
    anos = f.anos or tuple(meta()["anos"])
    marcadores = ", ".join("?" for _ in anos)

    # `unidades` garante a moldura completa; `casos` e `pops` entram por LEFT JOIN.
    df = banco.query(
        f"""
        WITH unidades AS (
            SELECT DISTINCT m.{col} AS id, m.{col} AS nome FROM mun m WHERE {where_geo}
        ),
        casos AS (
            SELECT
                {col} AS id,
                count(*)                                              AS casos,
                count(*) FILTER ({SQL_NOVO})                          AS novos,
                count(*) FILTER ({SQL_ENCERRADO})                     AS encerrados,
                count(*) FILTER ({SQL_ENCERRADO} AND situacao_encerramento = 'Cura') AS cura,
                count(*) FILTER ({SQL_ENCERRADO} AND {SQL_ABANDONO})  AS abandono,
                count(*) FILTER (WHERE situacao_encerramento = 'Óbito por TB')       AS obitos,
                count(*) FILTER ({SQL_HIV_TESTADO})                   AS hiv_testado,
                count(*) FILTER (WHERE status_hiv = 'Positivo')       AS hiv_pos
            FROM tb WHERE {where} GROUP BY 1
        ),
        pops AS (
            SELECT m.{col} AS id, sum(p.populacao) AS pessoas_ano
            FROM pop p JOIN mun m USING (codigo_ibge)
            WHERE {where_geo} AND p.ano IN ({marcadores})
            GROUP BY 1
        )
        SELECT
            u.id, u.nome,
            coalesce(c.casos, 0)       AS casos,
            coalesce(c.novos, 0)       AS novos,
            coalesce(c.encerrados, 0)  AS encerrados,
            coalesce(c.cura, 0)        AS cura,
            coalesce(c.abandono, 0)    AS abandono,
            coalesce(c.obitos, 0)      AS obitos,
            coalesce(c.hiv_testado, 0) AS hiv_testado,
            coalesce(c.hiv_pos, 0)     AS hiv_pos,
            coalesce(pp.pessoas_ano, 0) AS pessoas_ano
        FROM unidades u
        LEFT JOIN casos c USING (id)
        LEFT JOIN pops  pp USING (id)
        -- o desempate por id é obrigatório: sem ele o DuckDB devolve unidades
        -- empatadas em ordem arbitrária, o ranking troca de posição a cada
        -- refresh e o arquivo pré-computado deixa de ser reproduzível
        ORDER BY casos DESC, u.id
        """,
        p_geo + params + p_geo + list(anos),
    )

    # Nome legível: no nível município o id é o código IBGE, não serve de rótulo.
    if nivel == "municipio":
        nomes = {int(h["codigo_ibge"]): h["municipio"] for h in meta()["hierarquia"]}
    else:
        nomes = {}

    saida = []
    for r in df.itertuples(index=False):
        saida.append({
            "id": str(int(r.id)) if nivel == "municipio" else str(r.id),
            # fallback para o código: melhor mostrar "2611606" do que "None"
            "nome": (nomes.get(int(r.id)) or str(int(r.id))) if nivel == "municipio"
                    else str(r.nome),
            "casos": int(r.casos),
            "novos": int(r.novos),
            "populacao": int(r.pessoas_ano),
            "incidencia": _coef(r.novos, r.pessoas_ano),
            "mortalidade": _coef(r.obitos, r.pessoas_ano),
            "cura_pct": _taxa(r.cura, r.encerrados),
            "abandono_pct": _taxa(r.abandono, r.encerrados),
            "obito_pct": _taxa(r.obitos, r.encerrados),
            "hiv_pct": _taxa(r.hiv_pos, r.hiv_testado),
            "encerrados": int(r.encerrados),
        })
    return saida


@st.cache_data(ttl=TTL, show_spinner=False)
def detalhe_unidade(f: Filtros, nivel: str, unidade: str) -> dict:
    """Drill-down: ao clicar num polígono, o que há dentro dele.

    Município é folha da hierarquia (não tem sub-nível) — nesse caso devolve a
    série anual em vez de uma lista de filhos.
    """
    cfg = NIVEIS_GEO[nivel]
    col = cfg["coluna"]
    where, params = f.where_sql()

    filho = {"macro_saude": "regiao_saude", "regiao_saude": "municipio"}.get(nivel)

    cab = banco.query(
        f"""
        SELECT
            count(*) AS total,
            count(*) FILTER ({SQL_NOVO})      AS novos,
            count(*) FILTER ({SQL_ENCERRADO}) AS encerrados,
            count(*) FILTER ({SQL_ENCERRADO} AND situacao_encerramento = 'Cura') AS cura,
            count(*) FILTER ({SQL_ENCERRADO} AND {SQL_ABANDONO})                 AS abandono,
            count(*) FILTER (WHERE situacao_encerramento = 'Óbito por TB')       AS obitos,
            count(*) FILTER ({SQL_HIV_TESTADO})              AS hiv_testado,
            count(*) FILTER (WHERE status_hiv = 'Positivo')  AS hiv_pos
        FROM tb WHERE {where} AND CAST({col} AS VARCHAR) = ?
        """,
        params + [unidade],
    ).iloc[0]

    filhos = []
    if filho:
        df = banco.query(
            f"""
            SELECT {filho} AS nome,
                   count(*) AS casos,
                   count(*) FILTER ({SQL_ENCERRADO}) AS encerrados,
                   count(*) FILTER ({SQL_ENCERRADO} AND situacao_encerramento = 'Cura') AS cura,
                   count(*) FILTER ({SQL_ENCERRADO} AND {SQL_ABANDONO}) AS abandono
            FROM tb WHERE {where} AND CAST({col} AS VARCHAR) = ?
            GROUP BY 1 ORDER BY casos DESC, nome
            """,
            params + [unidade],
        )
        filhos = [
            {"nome": r.nome, "casos": int(r.casos),
             "cura_pct": _taxa(r.cura, r.encerrados),
             "abandono_pct": _taxa(r.abandono, r.encerrados)}
            for r in df.itertuples(index=False)
        ]

    serie = banco.query(
        f"""
        SELECT ano_notificacao AS ano, count(*) AS casos
        FROM tb WHERE {where} AND CAST({col} AS VARCHAR) = ?
        GROUP BY 1 ORDER BY 1
        """,
        params + [unidade],
    )

    return {
        "kpis": {
            "total": int(cab.total),
            "novos": int(cab.novos),
            "encerrados": int(cab.encerrados),
            "cura_pct": _taxa(cab.cura, cab.encerrados),
            "abandono_pct": _taxa(cab.abandono, cab.encerrados),
            "obito_pct": _taxa(cab.obitos, cab.encerrados),
            "hiv_pct": _taxa(cab.hiv_pos, cab.hiv_testado),
        },
        "filhos": filhos,
        "rotulo_filho": NIVEIS_GEO[filho]["rotulo"].lower() if filho else None,
        "plural_filho": NIVEIS_GEO[filho]["plural"] if filho else None,
        "serie": [{"ano": int(r.ano), "casos": int(r.casos)}
                  for r in serie.itertuples(index=False)],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Séries temporais
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=TTL, show_spinner=False)
@_precomputa("serie_incidencia")
def serie_incidencia(f: Filtros) -> list[dict]:
    """Coeficiente anual — numerador e denominador do MESMO ano.

    Ignora o filtro de anos de propósito: a série histórica completa é o valor
    do gráfico; os anos selecionados aparecem destacados na figura.
    """
    where, params = f.where_sql()
    where_geo, p_geo = f.where_geo_sql("m")
    df = banco.query(
        f"""
        WITH casos AS (
            SELECT ano_notificacao AS ano,
                   count(*) FILTER ({SQL_NOVO}) AS novos,
                   count(*) FILTER (WHERE situacao_encerramento = 'Óbito por TB') AS obitos
            FROM tb WHERE {where} GROUP BY 1
        ),
        pops AS (
            SELECT p.ano, sum(p.populacao) AS pop
            FROM pop p JOIN mun m USING (codigo_ibge)
            WHERE {where_geo} GROUP BY 1
        )
        SELECT c.ano, c.novos, c.obitos, pops.pop
        FROM casos c JOIN pops USING (ano) ORDER BY c.ano
        """,
        params + p_geo,
    )
    return [
        {"ano": int(r.ano), "novos": int(r.novos), "obitos": int(r.obitos),
         "populacao": int(r.pop),
         "incidencia": _coef(r.novos, r.pop),
         "mortalidade": _coef(r.obitos, r.pop)}
        for r in df.itertuples(index=False)
    ]


@st.cache_data(ttl=TTL, show_spinner=False)
@_precomputa("tendencia")
def tendencia(f: Filtros) -> dict:
    """Sazonalidade mensal do ano de referência contra a média histórica."""
    where, params = f.where_sql()
    ano_ref = f.ano_ref or max(meta()["anos"])

    # Sem o filtro de anos — a média histórica precisa de toda a série.
    where_h, params_h = replace(f, anos=()).where_sql()

    mensal = banco.query(
        f"""
        SELECT month(data_notificacao) AS mes,
               count(*) FILTER (WHERE ano_notificacao = ?) AS casos_ano,
               count(*) FILTER (WHERE ano_notificacao < ?) AS casos_hist,
               count(DISTINCT ano_notificacao) FILTER (WHERE ano_notificacao < ?) AS n_anos
        FROM tb WHERE {where_h} AND data_notificacao IS NOT NULL
        GROUP BY 1 ORDER BY 1
        """,
        [ano_ref, ano_ref, ano_ref] + params_h,
    )
    meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
             "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    por_mes = {int(r.mes): r for r in mensal.itertuples(index=False)}

    anual = banco.query(
        f"SELECT ano_notificacao AS ano, count(*) AS casos FROM tb "
        f"WHERE {where_h} GROUP BY 1 ORDER BY 1",
        params_h,
    )

    # Indicadores clínicos ao longo do tempo (série completa, sem filtro de ano)
    ind = banco.query(
        f"""
        SELECT ano_notificacao AS ano,
               100.0 * count(*) FILTER (WHERE status_hiv = 'Positivo')
                     / nullif(count(*) FILTER ({SQL_HIV_TESTADO}), 0)        AS hiv,
               100.0 * count(*) FILTER ({SQL_ENCERRADO} AND situacao_encerramento = 'Cura')
                     / nullif(count(*) FILTER ({SQL_ENCERRADO}), 0)          AS cura,
               100.0 * count(*) FILTER ({SQL_ENCERRADO} AND {SQL_ABANDONO})
                     / nullif(count(*) FILTER ({SQL_ENCERRADO}), 0)          AS abandono,
               100.0 * count(*) FILTER (WHERE situacao_encerramento = 'Óbito por TB')
                     / nullif(count(*) FILTER ({SQL_ENCERRADO}), 0)          AS obito,
               100.0 * count(*) FILTER ({SQL_HIV_TESTADO})
                     / nullif(count(*), 0)                                   AS cobertura_hiv
        FROM tb WHERE {where_h} GROUP BY 1 ORDER BY 1
        """,
        params_h,
    )

    total_ano = int(anual[anual.ano == ano_ref].casos.sum())
    hist = anual[anual.ano < ano_ref]
    media_hist = float(hist.casos.mean()) if len(hist) else 0.0

    return {
        "ano": ano_ref,
        "mensal": {
            "meses": meses,
            "casos": [int(por_mes[m].casos_ano) if m in por_mes else 0
                      for m in range(1, 13)],
            "media_hist": [
                round(por_mes[m].casos_hist / por_mes[m].n_anos, 1)
                if m in por_mes and por_mes[m].n_anos else None
                for m in range(1, 13)
            ],
        },
        "anual": [{"ano": int(r.ano), "casos": int(r.casos)}
                  for r in anual.itertuples(index=False)],
        "kpis": {
            "total_ano": total_ano,
            "media_anual_hist": round(media_hist),
            "variacao_pct": (round(100.0 * (total_ano - media_hist) / media_hist, 1)
                             if media_hist else None),
        },
        "indicadores": {
            "anos": [int(a) for a in ind.ano],
            "series": {
                "Coinfecção HIV (%)": [_arredonda(v) for v in ind.hiv],
                "Cobertura de testagem HIV (%)": [_arredonda(v) for v in ind.cobertura_hiv],
                "Taxa de cura (%)": [_arredonda(v) for v in ind.cura],
                "Taxa de abandono (%)": [_arredonda(v) for v in ind.abandono],
                "Óbito por TB (%)": [_arredonda(v) for v in ind.obito],
            },
        },
    }


def _arredonda(v):
    return None if v is None or v != v else round(float(v), 1)


# ══════════════════════════════════════════════════════════════════════════════
#  Perfil sociodemográfico
# ══════════════════════════════════════════════════════════════════════════════
def _contagens(colunas: list[str], f: Filtros) -> dict[str, list[dict]]:
    """Contagem por categoria de VÁRIAS colunas numa varredura só.

    Um `GROUP BY` por coluna significaria uma varredura da tabela por coluna.
    Com UNION ALL o DuckDB lê os dados uma vez e devolve tudo junto — na prática
    reduz a seção de perfil de ~10 consultas para 1.
    """
    where, params = f.where_sql()
    blocos = " UNION ALL ".join(
        f"SELECT '{c}' AS campo, coalesce(CAST({c} AS VARCHAR), 'Não informado') AS label, "
        f"count(*) AS valor FROM tb WHERE {where} GROUP BY 2"
        for c in colunas
    )
    # desempate por label: mantém a ordem estável entre execuções
    df = banco.query(f"{blocos} ORDER BY campo, valor DESC, label",
                     params * len(colunas))

    saida: dict[str, list[dict]] = {c: [] for c in colunas}
    for r in df.itertuples(index=False):
        saida[str(r.campo)].append({"label": str(r.label), "valor": int(r.valor)})
    return saida


def _contagem(coluna: str, f: Filtros) -> list[dict]:
    return _contagens([coluna], f)[coluna]


@st.cache_data(ttl=TTL, show_spinner=False)
@_precomputa("perfil")
def perfil(f: Filtros) -> dict:
    c = _contagens(["sexo", "raca_cor", "forma", "tipo_entrada",
                    "situacao_encerramento", "escolaridade"], f)
    return {
        "sexo": c["sexo"],
        "raca_cor": c["raca_cor"],
        "forma": c["forma"],
        "tipo_entrada": c["tipo_entrada"],
        "desfecho": c["situacao_encerramento"],
        # reaproveita a contagem acima em vez de repetir a consulta
        "desfecho_grupo": _desfecho_agrupado(c["situacao_encerramento"]),
        "desfecho_por_raca": _desfecho_por(f, "raca_cor"),
        "piramide_casos": _piramide(f),
        "piramide_obitos": _piramide(f, "situacao_encerramento = 'Óbito por TB'"),
        "escolaridade": c["escolaridade"],
    }


def _desfecho_agrupado(bruto: list[dict]) -> list[dict]:
    """Os 10 desfechos do SINAN colapsados em 4 grupos de coorte."""
    acumulado: dict[str, int] = {}
    for item in bruto:
        grupo = DESFECHO_GRUPO.get(item["label"], "Não avaliado")
        acumulado[grupo] = acumulado.get(grupo, 0) + item["valor"]
    ordem = ["Cura", "Interrupção", "Óbito", "Não avaliado"]
    return [{"label": g, "valor": acumulado[g]} for g in ordem if g in acumulado]


def _desfecho_por(f: Filtros, coluna: str) -> dict:
    """Composição 100% dos grupos de desfecho dentro de cada categoria."""
    where, params = f.where_sql()
    df = banco.query(
        f"""
        SELECT coalesce({coluna}, 'Não informado') AS categoria,
               coalesce(situacao_encerramento, 'Não informado') AS desfecho,
               count(*) AS n
        FROM tb WHERE {where} GROUP BY 1, 2
        """,
        params,
    )
    grupos = ["Cura", "Interrupção", "Óbito", "Não avaliado"]
    totais: dict[str, int] = {}
    matriz: dict[str, dict[str, int]] = {}
    for r in df.itertuples(index=False):
        cat = str(r.categoria)
        g = DESFECHO_GRUPO.get(str(r.desfecho), "Não avaliado")
        matriz.setdefault(cat, {}).setdefault(g, 0)
        matriz[cat][g] += int(r.n)
        totais[cat] = totais.get(cat, 0) + int(r.n)

    # (-total, nome) desempata por nome em vez de depender da ordem do dict
    categorias = sorted(totais, key=lambda c: (-totais[c], c))
    return {
        "categorias": categorias,
        "grupos": grupos,
        "n": totais,
        "pct": {
            c: {g: round(100.0 * matriz[c].get(g, 0) / totais[c], 1) for g in grupos}
            for c in categorias
        },
    }


def _piramide(f: Filtros, extra: str | None = None) -> dict:
    where, params = f.where_sql()
    if extra:
        where = f"{where} AND {extra}"
    df = banco.query(
        f"""
        SELECT
            CASE
                WHEN idade_anos < 5  THEN '0-4'    WHEN idade_anos < 10 THEN '5-9'
                WHEN idade_anos < 15 THEN '10-14'  WHEN idade_anos < 20 THEN '15-19'
                WHEN idade_anos < 30 THEN '20-29'  WHEN idade_anos < 40 THEN '30-39'
                WHEN idade_anos < 50 THEN '40-49'  WHEN idade_anos < 60 THEN '50-59'
                WHEN idade_anos < 70 THEN '60-69'  WHEN idade_anos < 80 THEN '70-79'
                ELSE '80+'
            END AS faixa,
            sexo,
            count(*) AS n
        FROM tb WHERE {where} AND idade_anos IS NOT NULL AND sexo IN ('Masculino', 'Feminino')
        GROUP BY 1, 2
        """,
        params,
    )
    m = {f_: 0 for f_ in FAIXAS_ETARIAS}
    fem = {f_: 0 for f_ in FAIXAS_ETARIAS}
    for r in df.itertuples(index=False):
        (m if r.sexo == "Masculino" else fem)[str(r.faixa)] += int(r.n)
    return {
        "faixas": list(FAIXAS_ETARIAS),
        "masculino": [m[f_] for f_ in FAIXAS_ETARIAS],
        "feminino": [fem[f_] for f_ in FAIXAS_ETARIAS],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Clínico & diagnóstico
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=TTL, show_spinner=False)
@_precomputa("clinico")
def clinico(f: Filtros) -> dict:
    c = _contagens(["status_hiv", "baciloscopia_primeira_amostra", "teste_molecular",
                    "cultura_escarro", "tratamento_supervisionado"], f)
    return {
        "status_hiv": c["status_hiv"],
        "baciloscopia": c["baciloscopia_primeira_amostra"],
        "teste_molecular": c["teste_molecular"],
        "cultura": c["cultura_escarro"],
        "tratamento_supervisionado": c["tratamento_supervisionado"],
        "desfecho_por_hiv": _desfecho_por(f, "status_hiv"),
        "coinfeccao_geo": _coinfeccao_geo(f),
        "tempo_tratamento": _tempo_tratamento(f),
        "coorte_por_tipo": _coorte_por_tipo(f),
    }


def _coinfeccao_geo(f: Filtros) -> list[dict]:
    """Positividade de HIV por região de saúde — % entre os testados."""
    where, params = f.where_sql()
    df = banco.query(
        f"""
        SELECT regiao_saude AS nome,
               count(*) FILTER ({SQL_HIV_TESTADO})            AS testado,
               count(*) FILTER (WHERE status_hiv = 'Positivo') AS pos
        FROM tb WHERE {where} AND regiao_saude IS NOT NULL
        GROUP BY 1 HAVING testado > 0 ORDER BY 100.0 * pos / testado DESC, nome
        """,
        params,
    )
    return [{"nome": str(r.nome), "uf": str(r.nome), "n_testado": int(r.testado),
             "pct": _taxa(r.pos, r.testado)}
            for r in df.itertuples(index=False)]


def _tempo_tratamento(f: Filtros) -> dict | None:
    """Oportunidade: dias entre diagnóstico e início do tratamento.

    O SINAN frequentemente registra início = data do diagnóstico (mediana 0),
    o que não significa atendimento imediato — a UI explicita isso.
    """
    where, params = f.where_sql()
    df = banco.query(
        f"""
        WITH t AS (
            SELECT
                date_diff('day', data_diagnostico, data_inicio_tratamento) AS dias,
                date_diff('day', data_inicio_tratamento, data_encerramento) AS duracao
            FROM tb
            WHERE {where}
              AND data_diagnostico IS NOT NULL AND data_inicio_tratamento IS NOT NULL
        )
        SELECT
            count(*)                                        AS n,
            median(dias)                                    AS mediana_inicio,
            100.0 * count(*) FILTER (WHERE dias <= 7)  / count(*) AS pct_ate_7d,
            100.0 * count(*) FILTER (WHERE dias > 30)  / count(*) AS pct_acima_30d,
            median(duracao) FILTER (WHERE duracao BETWEEN 0 AND 1095) AS duracao_mediana,
            count(*) FILTER (WHERE dias <= 0)               AS b0,
            count(*) FILTER (WHERE dias BETWEEN 1 AND 7)    AS b1,
            count(*) FILTER (WHERE dias BETWEEN 8 AND 14)   AS b2,
            count(*) FILTER (WHERE dias BETWEEN 15 AND 30)  AS b3,
            count(*) FILTER (WHERE dias BETWEEN 31 AND 60)  AS b4,
            count(*) FILTER (WHERE dias BETWEEN 61 AND 180) AS b5,
            count(*) FILTER (WHERE dias > 180)              AS b6
        FROM t WHERE dias BETWEEN -30 AND 3650
        """,
        params,
    ).iloc[0]

    if not df.n:
        return None
    faixas = ["Mesmo dia", "1–7 dias", "8–14 dias", "15–30 dias",
              "31–60 dias", "61–180 dias", ">180 dias"]
    return {
        "n": int(df.n),
        "mediana_inicio": float(_num(df.mediana_inicio)),
        "pct_ate_7d": round(float(_num(df.pct_ate_7d)), 1),
        "pct_acima_30d": round(float(_num(df.pct_acima_30d)), 1),
        # `if df.duracao_mediana` esconderia uma mediana legítima de 0 dias;
        # o que precisa ser testado é ausência (NULL/NaN), não falsidade
        "duracao_mediana": (None if _num(df.duracao_mediana, None) is None
                            else float(df.duracao_mediana)),
        "histograma": [
            {"faixa": faixa, "casos": int(getattr(df, f"b{i}"))}
            for i, faixa in enumerate(faixas)
        ],
    }


def _coorte_por_tipo(f: Filtros) -> dict:
    """Taxa de cura por ano, separada em caso novo × retratamento."""
    where, params = f.where_sql()
    df = banco.query(
        f"""
        SELECT ano_notificacao AS ano,
               100.0 * count(*) FILTER ({SQL_NOVO} AND situacao_encerramento = 'Cura')
                     / nullif(count(*) FILTER ({SQL_NOVO} AND {SQL_ENCERRADO}), 0) AS novo,
               100.0 * count(*) FILTER ({SQL_RETRAT} AND situacao_encerramento = 'Cura')
                     / nullif(count(*) FILTER ({SQL_RETRAT} AND {SQL_ENCERRADO}), 0) AS retrat
        FROM tb WHERE {where} GROUP BY 1 ORDER BY 1
        """,
        params,
    )
    return {
        "anos": [int(a) for a in df.ano],
        "series": {
            "Caso novo": [_arredonda(v) for v in df.novo],
            "Retratamento": [_arredonda(v) for v in df.retrat],
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Comorbidades & vulnerabilidades
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=TTL, show_spinner=False)
@_precomputa("comorbidades")
def comorbidades(f: Filtros) -> dict:
    where, params = f.where_sql()
    colunas = list(AGRAVOS) + list(POPULACOES)
    sel = ", ".join(f"count(*) FILTER (WHERE {c} = 'Sim') AS {c}" for c in colunas)
    linha = banco.query(
        f"SELECT count(*) AS total, {sel} FROM tb WHERE {where}", params
    ).iloc[0]
    total = int(linha.total)

    agravos = sorted(
        [{"label": rot, "valor": int(getattr(linha, col))} for col, rot in AGRAVOS.items()],
        key=lambda d: d["valor"], reverse=True,
    )
    populacoes = sorted(
        [{"label": rot, "valor": int(getattr(linha, col)),
          "pct": _taxa(getattr(linha, col), total)}
         for col, rot in POPULACOES.items()],
        key=lambda d: d["valor"], reverse=True,
    )

    return {
        "total": total,
        "agravos": agravos,
        "populacoes": populacoes,
        "heatmap": _heatmap_agravos(f),
        "desfecho_por_vulneravel": _desfecho_por_vulneravel(f),
    }


def _heatmap_agravos(f: Filtros) -> dict:
    """% de casos com cada comorbidade, por macrorregião de saúde."""
    where, params = f.where_sql()
    sel = ", ".join(
        f"100.0 * count(*) FILTER (WHERE {c} = 'Sim') / nullif(count(*), 0) AS {c}"
        for c in AGRAVOS
    )
    df = banco.query(
        f"SELECT macro_saude AS geo, {sel} FROM tb "
        f"WHERE {where} AND macro_saude IS NOT NULL GROUP BY 1 ORDER BY 1",
        params,
    )
    geos = [str(g) for g in df.geo]
    rotulos = list(AGRAVOS.values())
    # nullif(count,0) no SQL vira NULL/NaN quando a macro não tem casos —
    # sem _num viraria NaN no JSON e célula quebrada no heatmap
    valores = [
        [x, y, round(float(_num(getattr(r, col))), 1)]
        for y, col in enumerate(AGRAVOS)
        for x, r in enumerate(df.itertuples(index=False))
    ]
    return {"geos": geos, "agravos": rotulos, "valores": valores}


def _desfecho_por_vulneravel(f: Filtros) -> dict:
    """Composição de desfecho em cada população vulnerável (uma barra por grupo).

    Não é um GROUP BY: um caso pode pertencer a mais de uma população, então
    cada grupo é contado com seu próprio filtro e as barras não somam o total.
    """
    where, params = f.where_sql()
    grupos = ["Cura", "Interrupção", "Óbito", "Não avaliado"]
    categorias, totais, pcts = [], {}, {}

    for col, rotulo in POPULACOES.items():
        df = banco.query(
            f"SELECT coalesce(situacao_encerramento, 'Não informado') AS d, count(*) AS n "
            f"FROM tb WHERE {where} AND {col} = 'Sim' GROUP BY 1",
            params,
        )
        acumulado = {g: 0 for g in grupos}
        for r in df.itertuples(index=False):
            acumulado[DESFECHO_GRUPO.get(str(r.d), "Não avaliado")] += int(r.n)
        total = sum(acumulado.values())
        if not total:
            continue
        categorias.append(rotulo)
        totais[rotulo] = total
        pcts[rotulo] = {g: round(100.0 * acumulado[g] / total, 1) for g in grupos}

    return {"categorias": categorias, "grupos": grupos, "n": totais, "pct": pcts}


# ══════════════════════════════════════════════════════════════════════════════
#  Coorte de desfecho (visão do painel de Recife)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=TTL, show_spinner=False)
def coorte(f: Filtros, tipo: str = "todos") -> tuple[list[dict], int]:
    """Distribuição do desfecho entre os casos encerrados. Retorna (dados, denominador)."""
    where, params = f.where_sql()
    extra = {"novo": f" AND {SQL_NOVO}", "retrat": f" AND {SQL_RETRAT}"}.get(tipo, "")
    df = banco.query(
        f"SELECT situacao_encerramento AS label, count(*) AS valor "
        f"FROM tb WHERE {where} AND {SQL_ENCERRADO}{extra} "
        f"GROUP BY 1 ORDER BY valor DESC, label",
        params,
    )
    total = int(df.valor.sum()) if len(df) else 0
    dados = [
        {"label": str(r.label), "valor": int(r.valor),
         "pct": _taxa(r.valor, total)}
        for r in df.itertuples(index=False)
    ]
    return dados, total


@st.cache_data(ttl=TTL, show_spinner=False)
@_precomputa("novos_vs_retratamento")
def novos_vs_retratamento(f: Filtros) -> list[dict]:
    where, params = f.where_sql()
    df = banco.query(
        f"""
        SELECT ano_notificacao AS ano,
               count(*) FILTER ({SQL_NOVO})   AS novos,
               count(*) FILTER ({SQL_RETRAT}) AS retratamento
        FROM tb WHERE {where} GROUP BY 1 ORDER BY 1
        """,
        params,
    )
    return [{"ano": int(r.ano), "novos": int(r.novos),
             "retratamento": int(r.retratamento)}
            for r in df.itertuples(index=False)]


# ══════════════════════════════════════════════════════════════════════════════
#  Microdados para a Análise Livre / exportação
# ══════════════════════════════════════════════════════════════════════════════
def amostra_para_analise(f: Filtros, limite: int = 200_000):
    """DataFrame decodificado do recorte atual — Análise Livre e download CSV."""
    where, params = f.where_sql()
    return banco.query(f"SELECT * FROM tb WHERE {where} LIMIT {limite}", params)
