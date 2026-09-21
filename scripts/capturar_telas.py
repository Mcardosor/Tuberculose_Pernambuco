"""Captura as telas do README em alta resolução, com Chromium headless.

Precisa do servidor de dev no ar (`streamlit run app.py`, ou o `tbpe` do
`launch.json` na 8516) e do Playwright (`pip install playwright &&
playwright install chromium` — não é dependência do painel, só desta
captura). Gera `docs/img/painel.png`, `recorte.png` e `topicos.png`.

    python -m scripts.capturar_telas [http://localhost:8516/]
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

DESTINO = Path(__file__).resolve().parents[1] / "docs" / "img"
RECORTE = {"x": 24, "y": 0, "width": 1392, "height": 1000}
SEM_CABECALHO = 'header[data-testid="stHeader"]{display:none!important}'
ROLAR = "document.querySelector('[data-testid=\"stMain\"]').scrollTo(0, %d)"


async def main(url: str) -> None:
    from playwright.async_api import async_playwright

    DESTINO.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        navegador = await p.chromium.launch()
        pagina = await navegador.new_page(
            viewport={"width": 1440, "height": 1040}, device_scale_factor=2, color_scheme="light"
        )
        await pagina.goto(url, wait_until="networkidle", timeout=120_000)
        await pagina.wait_for_timeout(10_000)

        async def foto(nome: str, rolagem: int) -> None:
            await pagina.add_style_tag(content=SEM_CABECALHO)
            await pagina.evaluate(ROLAR % rolagem)
            await pagina.wait_for_timeout(1_800)
            await pagina.screenshot(path=str(DESTINO / nome), clip=RECORTE)
            print("gravado", DESTINO / nome)

        await foto("painel.png", 60)

        # Uma macrorregião aberta pelo clique no mapa (Metropolitana).
        quadro = next(f for f in pagina.frames if "mapa_deck" in (f.url or ""))
        xy = await quadro.evaluate(
            "() => window.__mapa.getViewports()[0].project([-35.1, -8.0])"
        )
        iframe = await pagina.query_selector('iframe[src*="mapa_deck"]')
        caixa = await iframe.bounding_box()
        await pagina.mouse.click(caixa["x"] + xy[0], caixa["y"] + xy[1])
        await pagina.wait_for_timeout(9_000)
        await foto("recorte.png", 60)
        await foto("topicos.png", 1650)
        await navegador.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8516/"))
