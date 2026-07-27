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


@pytest.fixture(scope="session")
def meta() -> dict:
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
    from src import precomputado
    estado = "presente" if precomputado.disponivel() else "AUSENTE/desatualizado"
    return f"agregados pré-computados: {estado}"
