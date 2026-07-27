"""
seguranca.py — validação de entrada que vira HTML
═════════════════════════════════════════════════
Fica separado do app.py de propósito: `app.py` não é importável sem subir o
Streamlit, e o que não é importável não é testável.
"""

from __future__ import annotations

from urllib.parse import urlparse


def url_segura(bruta: str | None) -> str | None:
    """Devolve a URL se for http(s) bem formada; None caso contrário.

    A URL do Superset é digitada pelo usuário e acaba dentro do atributo `src`
    de um iframe. Sem esta checagem:
      - `javascript:alert(1)` executaria ao carregar o quadro;
      - `data:text/html,<script>…` idem;
      - um valor com aspas fecharia o atributo e injetaria outro (`onload=`).

    Escape de aspas continua sendo obrigatório no ponto de uso — isto aqui só
    garante o esquema e a presença de host.
    """
    try:
        partes = urlparse((bruta or "").strip())
    except ValueError:
        return None
    if partes.scheme not in ("http", "https") or not partes.netloc:
        return None
    return partes.geturl()
