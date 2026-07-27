"""
Agregados pré-computados: têm que ser IDÊNTICOS ao cálculo ao vivo, e têm que
se invalidar sozinhos quando os Parquets mudam.

Um pré-cômputo que diverge é pior que não ter pré-cômputo: o painel serve número
errado sem nenhum sinal.
"""

from __future__ import annotations

import json
import os

import pytest

from conftest import sem_cache
from src import indicadores, precomputado
from src.constantes import PARQUET

pytestmark = pytest.mark.skipif(
    not precomputado.disponivel(),
    reason="sem _agregados.json — rode `python etl/precomputar.py`",
)


def _canonico(valor):
    """Compara na mesma forma que o JSON grava (tupla vira lista)."""
    return json.loads(json.dumps(
        valor, ensure_ascii=False,
        default=lambda o: o.item() if hasattr(o, "item") else list(o),
    ))


@pytest.mark.parametrize("nome", [
    "resumo", "serie_incidencia", "tendencia", "perfil",
    "clinico", "comorbidades", "novos_vs_retratamento",
])
def test_servido_e_identico_ao_calculado(padrao, nome):
    fn = getattr(indicadores, nome)
    assert _canonico(sem_cache(fn)(padrao)) == _canonico(fn(padrao)), nome


@pytest.mark.parametrize("nivel", ["municipio", "regiao_saude", "macro_saude"])
def test_mapa_servido_e_identico_ao_calculado(padrao, nivel):
    ao_vivo = sem_cache(indicadores.mapa)(padrao, nivel)
    servido = indicadores.mapa(padrao, nivel)
    assert _canonico(ao_vivo) == _canonico(servido)


def test_ordem_do_ranking_e_deterministica(padrao):
    """Duas execuções seguidas têm que devolver a MESMA ordem.

    Regressão: `ORDER BY casos DESC` sem desempate devolvia unidades empatadas
    em ordem arbitrária (dois municípios com 176 casos trocavam de lugar), o
    ranking mudava a cada refresh e o pré-cômputo não era reproduzível.
    """
    a = [d["id"] for d in sem_cache(indicadores.mapa)(padrao, "municipio")]
    b = [d["id"] for d in sem_cache(indicadores.mapa)(padrao, "municipio")]
    assert a == b

    empates = {}
    for d in sem_cache(indicadores.mapa)(padrao, "municipio"):
        empates.setdefault(d["casos"], []).append(d["id"])
    com_empate = [v for v in empates.values() if len(v) > 1]
    assert com_empate, "sem empates na base, o teste não estaria provando nada"
    for grupo in com_empate:
        assert grupo == sorted(grupo), "empate não desempatado por id"


def test_filtro_fora_do_precomputo_cai_no_calculo_ao_vivo(anos, meta):
    """Só a visão padrão é pré-computada; qualquer filtro tem que ir ao DuckDB."""
    from src.filtros import Filtros

    f = Filtros(anos=anos, macros=(meta["macros"][0],))
    assert precomputado.obter("resumo", f) is None
    assert indicadores.resumo(f)["total"] > 0


def test_store_se_invalida_quando_o_conteudo_do_parquet_muda():
    """Melhor recalcular do que servir número velho em painel de vigilância."""
    assert precomputado.disponivel()
    original = PARQUET.read_bytes()
    try:
        PARQUET.write_bytes(original + b"\x00")  # muda o conteúdo
        precomputado._store.cache_clear()
        assert not precomputado.disponivel()
        assert precomputado.obter("meta") is None
    finally:
        PARQUET.write_bytes(original)
        precomputado._store.cache_clear()
    assert precomputado.disponivel()


def test_mtime_sozinho_nao_invalida_o_store():
    """Copiar o arquivo (deploy) reescreve o mtime — e não pode invalidar nada.

    Regressão: a impressão digital usava mtime, então o `_agregados.json` nunca
    sobrevivia a um deploy. Na primeira subida para a VM o painel voltou a
    calcular tudo ao vivo sem ninguém perceber.
    """
    assert precomputado.disponivel()
    st = PARQUET.stat()
    original = (st.st_atime_ns, st.st_mtime_ns)
    try:
        os.utime(PARQUET, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
        precomputado._store.cache_clear()
        assert precomputado.disponivel(), "mtime novo não pode invalidar o store"
        assert precomputado.obter("meta") is not None
    finally:
        os.utime(PARQUET, ns=original)
        precomputado._store.cache_clear()


def test_fingerprint_do_arquivo_bate_com_os_parquets_atuais():
    gravado = json.loads(precomputado.ARQUIVO.read_text(encoding="utf-8"))["fingerprint"]
    assert gravado == precomputado.impressao_digital(), (
        "_agregados.json foi gerado de outra versão dos dados — "
        "rode `python etl/precomputar.py`"
    )
