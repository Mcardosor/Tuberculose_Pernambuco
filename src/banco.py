"""
banco.py — motor DuckDB sobre os dados de PE
════════════════════════════════════════════
O SQL do chamador referencia três tabelas: `tb` (SINAN de PE), `pop` (população
IBGE por município/ano) e `mun` (hierarquia geográfica).

**Uma única conexão em memória, viva pelo processo inteiro.** A primeira versão
abria uma conexão nova por consulta, lendo o Parquet do disco toda vez: um
`SELECT count(*)` custava 27 ms, dos quais praticamente tudo era abertura de
conexão e parsing do Parquet. Como uma seção faz ~10 consultas, eram ~280 ms de
puro overhead por tela. Materializando os dados como tabelas nativas na
inicialização, o custo por consulta cai para a agregação de verdade.

Os 142 mil registros ocupam poucos MB em memória — cabe folgado, e é o que
permite não fazer a projeção de colunas que o painel de Recife precisa fazer.

**Thread safety:** o Streamlit atende sessões em threads distintas e uma
`DuckDBPyConnection` não pode ser usada concorrentemente. Cada consulta pega um
`.cursor()` — conexão-filha independente sobre o MESMO banco em memória, que é o
padrão documentado do DuckDB para paralelismo.
"""

from __future__ import annotations

import os

import duckdb
import pandas as pd
import streamlit as st

from src.constantes import MUNICIPIOS_PARQUET, PARQUET, POP_PARQUET


def _threads() -> int:
    return min(os.cpu_count() or 2, 8)


@st.cache_resource(show_spinner="Carregando a base de PE…")
def conexao() -> duckdb.DuckDBPyConnection:
    """Conexão em memória com tb/pop/mun materializadas. Uma vez por processo."""
    con = duckdb.connect(":memory:")
    con.execute(f"SET threads = {_threads()}")
    for tabela, arquivo in (
        ("tb", PARQUET), ("pop", POP_PARQUET), ("mun", MUNICIPIOS_PARQUET)
    ):
        con.execute(
            f"CREATE TABLE {tabela} AS SELECT * FROM read_parquet('{arquivo.as_posix()}')"
        )
    return con


def query(sql: str, params: list | None = None) -> pd.DataFrame:
    """Roda SQL com as tabelas `tb`, `pop` e `mun` disponíveis."""
    cur = conexao().cursor()
    try:
        return cur.execute(sql, params or []).df()
    finally:
        cur.close()


def escalar(sql: str, params: list | None = None):
    """Primeira coluna da primeira linha — para contagens simples."""
    cur = conexao().cursor()
    try:
        linha = cur.execute(sql, params or []).fetchone()
    finally:
        cur.close()
    return linha[0] if linha else None


def anos_disponiveis() -> list[int]:
    df = query("SELECT DISTINCT ano_notificacao AS a FROM tb "
               "WHERE a IS NOT NULL ORDER BY a")
    return [int(a) for a in df["a"]]


def opcoes(coluna: str, excluir_vazios: bool = True) -> list[str]:
    """Valores distintos de uma coluna, ordenados por frequência (desc)."""
    df = query(f"SELECT {coluna} AS v, count(*) AS n FROM tb "
               f"WHERE v IS NOT NULL GROUP BY 1 ORDER BY n DESC")
    valores = [str(v) for v in df["v"]]
    if excluir_vazios:
        vazios = {"não informado", "nao informado", "ignorado"}
        valores = [v for v in valores if v.strip().lower() not in vazios]
    return valores


def hierarquia() -> pd.DataFrame:
    """Município → região de saúde → macrorregião (185 linhas)."""
    return query("SELECT * FROM mun ORDER BY municipio")
