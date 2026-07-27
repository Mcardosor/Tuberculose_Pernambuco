"""
precomputado.py — agregados prontos, gerados no ETL
═══════════════════════════════════════════════════
O espaço de filtros é combinatório (anos × macro × região × município × sexo ×
raça × HIV × vulnerabilidades × comorbidades), então pré-computar "tudo" é
impossível. O que compensa é a **visão padrão** — PE inteiro, série completa,
sem filtro de perfil — que é a primeira tela de todo acesso, mais o `meta()`,
que não depende de filtro nenhum.

Qualquer filtro que o usuário aplique não encontra chave aqui e cai no DuckDB,
que já responde em dezenas de milissegundos.

**Proteção contra dado velho:** o arquivo guarda a impressão digital dos
Parquets (nome, tamanho e mtime). Se qualquer um mudar, o store inteiro é
ignorado e tudo volta a ser calculado ao vivo — melhor recalcular do que servir
número desatualizado em painel de vigilância. Rode `python etl/precomputar.py`
depois de todo `preparar_dados.py`.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

from src.constantes import MUNICIPIOS_PARQUET, PARQUET, POP_PARQUET, PASTA_DADOS
from src.filtros import Filtros

ARQUIVO = PASTA_DADOS / "_agregados.json"
FONTES = (PARQUET, POP_PARQUET, MUNICIPIOS_PARQUET)


def impressao_digital() -> dict[str, list]:
    """Identidade dos Parquets de origem — invalida o store quando mudam."""
    return {
        p.name: [p.stat().st_size, p.stat().st_mtime_ns] if p.exists() else None
        for p in FONTES
    }


def chave(nome: str, f: Filtros | None = None, extra: str = "") -> str:
    """Chave estável para (função, filtros, argumento extra)."""
    if f is None:
        assinatura = "-"
    else:
        # asdict + sort_keys garante a mesma string para os mesmos filtros
        assinatura = json.dumps(asdict(f), sort_keys=True, ensure_ascii=False)
    return f"{nome}|{extra}|{assinatura}"


@lru_cache(maxsize=1)
def _store() -> dict:
    if not ARQUIVO.exists():
        return {}
    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if dados.get("fingerprint") != impressao_digital():
        return {}  # Parquets mudaram desde a geração — não confiar
    return dados.get("agregados", {})


def obter(nome: str, f: Filtros | None = None, extra: str = ""):
    """Agregado pronto, ou None se esta combinação não foi pré-computada."""
    return _store().get(chave(nome, f, extra))


def disponivel() -> bool:
    return bool(_store())


def gravar(agregados: dict) -> Path:
    """Usado só pelo etl/precomputar.py."""
    ARQUIVO.write_text(
        json.dumps(
            {"fingerprint": impressao_digital(), "agregados": agregados},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _store.cache_clear()
    return ARQUIVO
