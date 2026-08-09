"""
conftest.py — infraestrutura compartilhada dos testes
═════════════════════════════════════════════════════
Os testes rodam FORA do runtime do Streamlit. Isso é proposital: exercitam a
camada de dados diretamente, sem servidor. O Streamlit emite um aviso
("No runtime found") que é inofensivo e está silenciado no pytest.ini.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src import indicadores  # noqa: E402
from src.filtros import Filtros  # noqa: E402


def sem_cache(fn):
    """Desce até a função real, atravessando @st.cache_data e @_precomputa.

    Sem isto, um teste poderia passar lendo o `_agregados.json` em vez de
    exercitar o SQL — que é justamente o que ele deveria estar verificando.
    """
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


# ── Microdado ausente: pular, não estourar ───────────────────────────────────
# `pe_tb_sinan.parquet` são 142 mil notificações individuais e nunca entram no
# repositório (ver .gitignore). Sem esse porteiro, um clone limpo — o CI, ou
# alguém que acabou de clonar — colhe 40 ERROS de IOException do DuckDB em vez
# de um resultado legível. Erro quer dizer "a suíte está quebrada"; o que
# acontece aqui é outra coisa: os dados não estão à mão.
DADOS = RAIZ / "dados_dashboard"
_MICRODADO = ("pe_tb_sinan.parquet", "pop_pe.parquet", "municipios_pe.parquet")


def _microdado_faltando() -> list[str]:
    return [nome for nome in _MICRODADO if not (DADOS / nome).exists()]


@pytest.fixture(scope="session")
def base() -> None:
    """Porteiro dos testes que tocam a base. Depender desta fixture (direta ou
    indiretamente, via `meta`) é o que faz o teste pular em vez de estourar."""
    faltando = _microdado_faltando()
    if faltando:
        pytest.skip(
            "microdado ausente (" + ", ".join(faltando) + ") — rode etl/preparar_dados.py"
        )


@pytest.fixture(scope="session")
def meta(base) -> dict:
    return indicadores.meta()


@pytest.fixture(scope="session")
def anos(meta) -> tuple[int, ...]:
    return tuple(meta["anos"])


@pytest.fixture(scope="session")
def padrao(anos) -> Filtros:
    """Visão padrão do painel: PE inteiro, série completa, sem filtro de perfil."""
    return Filtros(anos=anos)


@pytest.fixture(scope="session")
def resumo_padrao(padrao) -> dict:
    return sem_cache(indicadores.resumo)(padrao)


def pytest_report_header(config):
    faltando = _microdado_faltando()
    if faltando:
        return (
            "microdado: AUSENTE — os testes de base vão pular.\n"
            "           faltando: " + ", ".join(faltando)
        )
    from src import precomputado
    estado = "presente" if precomputado.disponivel() else "AUSENTE/desatualizado"
    return f"microdado: presente | agregados pré-computados: {estado}"
