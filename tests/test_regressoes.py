"""
Regressões pontuais — cada teste aqui trava um bug que já aconteceu.

Não são casos hipotéticos: todos derrubaram a página ou renderizaram errado em
algum momento do desenvolvimento.
"""

from __future__ import annotations

import html
import json

import pytest

from src.constantes import GEOJSON, fmt_dec, fmt_int
from src.indicadores import _num
from src.seguranca import url_segura


# ── NaN nos formatadores ──────────────────────────────────────────────────────
# `x or 0` NÃO protege contra NaN: NaN é verdadeiro em Python, passa direto pelo
# `or` e estoura no `int()`. Como fmt_int/fmt_dec aparecem em todo KPI, rótulo e
# hover, um NaN vindo de agregação vazia derrubava a página inteira.
@pytest.mark.parametrize("valor", [None, float("nan"), float("inf"), float("-inf")])
def test_formatadores_absorvem_valores_nao_finitos(valor):
    assert fmt_int(valor) == "0"
    assert fmt_dec(valor) == "0,0"


def test_formatadores_mantem_o_padrao_pt_br():
    assert fmt_int(1234567) == "1.234.567"
    assert fmt_int(0) == "0"
    assert fmt_dec(0) == "0,0"
    assert fmt_dec(12.36) == "12,4"
    assert fmt_dec(51.94) == "51,9"
    # Evite casos como 12.35 aqui: em binário ele é 12.3499…, então arredonda
    # para 12,3. Não é bug de formatação, é representação de float — mas vira
    # teste instável se você não souber.


@pytest.mark.parametrize("valor,esperado", [
    (None, 0), (float("nan"), 0), (0, 0), (0.0, 0), (5, 5), (-3.2, -3.2),
])
def test_num_trata_ausencia_sem_confundir_com_zero(valor, esperado):
    assert _num(valor) == esperado


def test_num_distingue_ausente_de_zero():
    """Zero é um valor legítimo — só None/NaN podem virar o padrão.

    Regressão: `if df.duracao_mediana` escondia uma mediana real de 0 dias,
    que é exatamente o valor mais comum nesta base.
    """
    assert _num(0.0, None) == 0.0
    assert _num(None, None) is None
    assert _num(float("nan"), None) is None


# ── Injeção na URL do Superset ────────────────────────────────────────────────
@pytest.mark.parametrize("entrada", [
    "javascript:alert(document.cookie)",
    "data:text/html,<script>alert(1)</script>",
    'x" onload="alert(1)',
    "//evil.com/x",
    "ftp://arquivo.local/x",
    "http://",
    "",
    "   ",
    None,
])
def test_url_perigosa_e_recusada(entrada):
    assert url_segura(entrada) is None


@pytest.mark.parametrize("entrada", [
    "http://localhost:8590/superset/dashboard/tuberculose-pe/?standalone=1",
    "https://telessaude.unb.br/superset",
])
def test_url_legitima_e_aceita(entrada):
    assert url_segura(entrada) == entrada


def test_url_aceita_nao_escapa_do_atributo_src():
    """Mesmo passando na validação, aspas têm que ser escapadas no HTML."""
    aceita = url_segura('http://ok" onload="alert(1)')
    assert aceita is not None
    renderizado = html.escape(aceita, quote=True)
    assert '"' not in renderizado and "<" not in renderizado


# ── Geometria dos mapas ───────────────────────────────────────────────────────
def _area_assinada(anel) -> float:
    return sum(anel[i][0] * anel[i + 1][1] - anel[i + 1][0] * anel[i][1]
               for i in range(len(anel) - 1)) / 2


@pytest.mark.parametrize("nivel", ["municipio", "regiao_saude", "macro_saude"])
def test_aneis_externos_sao_horarios(nivel):
    """O d3-geo (motor do Plotly) exige anel externo HORÁRIO — convenção
    contrária à do RFC 7946.

    Regressão: com anéis anti-horários, 170 dos 185 municípios renderizavam
    como um retângulo cobrindo o mapa inteiro (o d3 entende o complemento: "o
    globo menos este polígono"). O mapa ficava de uma cor só, sem erro nenhum
    no console.
    """
    gj = json.loads(GEOJSON[nivel].read_text(encoding="utf-8"))
    for feicao in gj["features"]:
        g = feicao["geometry"]
        poligonos = (g["coordinates"] if g["type"] == "MultiPolygon"
                     else [g["coordinates"]])
        for aneis in poligonos:
            assert _area_assinada(aneis[0]) < 0, (
                f"{nivel}/{feicao['id']}: anel externo anti-horário — "
                "o mapa vai renderizar invertido"
            )
            for buraco in aneis[1:]:
                assert _area_assinada(buraco) > 0, f"{nivel}/{feicao['id']}: buraco invertido"


@pytest.mark.parametrize("nivel", ["municipio", "regiao_saude", "macro_saude"])
def test_geojson_esta_dentro_de_pernambuco(nivel):
    """Coordenadas em lon/lat WGS84, dentro da caixa de PE.

    Pega shapefile em CRS projetado (UTM), que renderizaria um mapa vazio.
    """
    gj = json.loads(GEOJSON[nivel].read_text(encoding="utf-8"))
    for feicao in gj["features"]:
        coords = feicao["geometry"]["coordinates"]
        while not isinstance(coords[0], (int, float)):
            coords = coords[0]
        lon, lat = coords[0], coords[1]
        assert -42 <= lon <= -32, f"{nivel}/{feicao['id']}: longitude {lon} fora de PE"
        assert -10 <= lat <= -6, f"{nivel}/{feicao['id']}: latitude {lat} fora de PE"


def test_ids_do_geojson_casam_com_os_dados(padrao):
    """Se o id não casar, o Plotly desenha o contorno sem cor nenhuma."""
    from conftest import sem_cache
    from src import indicadores

    for nivel in ("municipio", "regiao_saude", "macro_saude"):
        gj = json.loads(GEOJSON[nivel].read_text(encoding="utf-8"))
        ids_geo = {str(f["id"]) for f in gj["features"]}
        ids_dados = {d["id"] for d in sem_cache(indicadores.mapa)(padrao, nivel)}
        assert ids_dados <= ids_geo, (
            f"{nivel}: sem geometria para {sorted(ids_dados - ids_geo)[:5]}"
        )


# ── Taxa com denominador pequeno ──────────────────────────────────────────────
def test_taxa_exige_denominador_minimo():
    """Taxa com base minúscula não pode entrar no ranking.

    Regressão: filtrando um único ano, 47 dos 185 municípios empatavam em
    "100% de cura" — 33 deles com 3 ou menos casos encerrados. Um município que
    curou 2 de 2 liderava acima de um que curou 180 de 200.
    """
    from src import mapas
    from src.constantes import DENOMINADOR_MINIMO_TAXA

    pequeno = {"encerrados": DENOMINADOR_MINIMO_TAXA - 1, "cura_pct": 100.0}
    grande = {"encerrados": DENOMINADOR_MINIMO_TAXA, "cura_pct": 72.0}

    assert not mapas.tem_base(pequeno, "cura_pct")
    assert not mapas.tem_base(pequeno, "abandono_pct")
    assert mapas.tem_base(grande, "cura_pct")

    # contagem não tem denominador — nunca é suprimida
    assert mapas.tem_base(pequeno, "casos")
    assert mapas.tem_base(pequeno, "incidencia")


def test_escala_de_quantis_so_nas_contagens():
    """A legenda descreve a escala usada; taxa é linear, contagem é por quantil.

    Regressão: a legenda dizia "escala em quantis" em todas as métricas,
    inclusive nas taxas, que são lineares.
    """
    from src import mapas

    assert mapas.usa_quantis("casos")
    assert mapas.usa_quantis("incidencia")
    assert not mapas.usa_quantis("cura_pct")
    assert not mapas.usa_quantis("abandono_pct")


def test_unidades_sem_base_continuam_no_mapa(padrao):
    """Suprimir a TAXA não pode significar sumir com o município do mapa."""
    from conftest import sem_cache
    from src import indicadores, mapas
    from src.filtros import Filtros

    f = Filtros(anos=(max(padrao.anos),))  # um ano só: muitos denominadores pequenos
    dados = sem_cache(indicadores.mapa)(f, "municipio")
    sem_base = [d for d in dados if not mapas.tem_base(d, "cura_pct")]
    assert sem_base, "um ano só deveria produzir municípios com base insuficiente"

    fig = mapas.figura(dados, "municipio", "cura_pct")
    desenhados = sum(len(t.locations) for t in fig.data)
    assert desenhados == len(dados), "toda unidade tem que aparecer no mapa"
    assert len(fig.data) == 2, "esperava camada colorida + camada cinza"


# ── Enquadramento do mapa ─────────────────────────────────────────────────────
def test_altura_do_mapa_acompanha_a_proporcao_do_recorte():
    """PE inteiro é largo e baixo (~2,7:1) e pede mapa achatado; um município
    isolado é quase quadrado e pede mapa alto.

    Regressão: com altura fixa, metade do gráfico ficava em faixas vazias.
    """
    from src import mapas

    gj = json.loads(GEOJSON["municipio"].read_text(encoding="utf-8"))
    todos = [str(f["id"]) for f in gj["features"]]
    estado = mapas.altura_sugerida("municipio", todos)
    um_so = mapas.altura_sugerida("municipio", [todos[0]])
    assert estado < um_so, "recorte largo deveria render mapa mais baixo"
    assert 320 <= estado <= 640 and 320 <= um_so <= 640
