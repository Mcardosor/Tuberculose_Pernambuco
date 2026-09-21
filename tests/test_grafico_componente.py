"""O componente ECharts: o que o Python promete ao JavaScript."""

from __future__ import annotations

import json

import pandas as pd

from src import grafico_componente as gc


def test_arquivos_do_componente_existem() -> None:
    for nome in ("index.html", "grafico.js", "echarts.min.js"):
        assert (gc.DIRETORIO / nome).is_file(), nome


def _tabela() -> pd.DataFrame:
    return pd.DataFrame({
        "chave": ["261160", "260790", "261070"],
        "nome": ["Recife", "Jaboatão dos Guararapes", "Olinda"],
        "valor": [101.3, 60.2, 75.0],
    })


def test_ranking_ordena_do_maior_no_topo_e_leva_nome_e_chave() -> None:
    """Eixo de categoria do ECharts cresce de baixo para cima: o maior tem
    de ser o último da lista para ficar no topo. `name` é o que casa o item
    entre dois renders (é a animação); `chave` é o que navega."""
    opt = gc.ranking(_tabela(), rotulo="Incidência", cor="#92400E")
    nomes = opt["yAxis"]["data"]
    assert nomes == ["Jaboatão dos Guararapes", "Olinda", "Recife"]
    itens = opt["series"][0]["data"]
    assert [i["name"] for i in itens] == nomes
    assert [i["chave"] for i in itens] == ["260790", "261070", "261160"]
    assert opt["series"][0]["id"] == "ranking"


def test_ranking_destaca_o_selecionado_e_recua_os_outros() -> None:
    opt = gc.ranking(_tabela(), rotulo="x", cor="#000", selecionado="261160")
    por_nome = {i["name"]: i["itemStyle"]["opacity"] for i in opt["series"][0]["data"]}
    assert por_nome["Recife"] == 1.0
    assert por_nome["Olinda"] == 0.55


def test_ranking_usa_a_cor_da_classe_do_mapa() -> None:
    from src import mapa

    escala = mapa.escala(_tabela()["valor"], ["#111111", "#222222", "#333333"], metodo="NATURAL")
    opt = gc.ranking(_tabela(), rotulo="x", cor="#000", escala=escala)
    cores = {i["itemStyle"]["color"] for i in opt["series"][0]["data"]}
    assert cores <= set(escala.cores.values())


def test_ranking_vazio_tem_recado_e_nao_estoura() -> None:
    opt = gc.ranking(pd.DataFrame(columns=["chave", "nome", "valor"]), rotulo="x", cor="#000")
    assert "Sem dados" in opt["title"]["text"]
    assert "series" not in opt


def test_opcao_serializa_com_numeros_do_numpy() -> None:
    import numpy as np

    tabela = _tabela().assign(valor=np.array([1, 2, 3], dtype=np.int64))
    texto = json.dumps(gc.ranking(tabela, rotulo="x", cor="#000"), default=gc._serializar)
    assert '"value": 3.0' in texto


def test_clique_novo_navega_e_repetido_nao() -> None:
    ev = {"nonce": "a-1", "name": "Recife", "chave": "261160"}
    assert gc.alvo_do_clique(ev, None) == ("261160", "a-1")
    assert gc.alvo_do_clique(ev, "a-1") == (None, None)
    assert gc.alvo_do_clique({"nonce": "a-2", "name": "Agreste"}, "a-1") == ("Agreste", "a-2")
    assert gc.alvo_do_clique(None, None) == (None, None)
