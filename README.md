# Painel de Monitoramento da Tuberculose — Pernambuco

[![CI](https://github.com/Mcardosor/Tuberculose_Pernambuco/actions/workflows/ci.yml/badge.svg)](https://github.com/Mcardosor/Tuberculose_Pernambuco/actions/workflows/ci.yml)

Painel de vigilância da tuberculose do estado de Pernambuco, em Streamlit,
com recorte por **município**, **região de saúde** e **macrorregião de
saúde**. No ar em <https://painel.cenarios.unb.br/cenarios/tbpe/>.

É o painel de monitoramento do Recife da equipe parceira (`../RecifeTB`,
reconstrução do Shiny/R deles) ampliado para o estado, sobre o core da
família Cenários+ (`../sinan`) e a geografia do `../hansepe`. Os números
seguem o Boletim Epidemiológico; a cara segue o painel em R.

## Conteúdo

- **Seis indicadores** do ano e território selecionados, com variação contra
  o ano anterior e a fração de onde cada proporção sai: incidência, casos
  novos, mortalidade, interrupção de tratamento, HIV positivo na testagem e
  proporção de cura.
- **Mapa** clicável (município → região de saúde → macrorregião), com três
  classificações de cor: quebras naturais, quintis e uma **escala fixa**
  ancorada no Brasil (40 por 100 mil), em Pernambuco (55) e na meta de cura
  de 85 % da OMS — a única que deixa dois anos comparáveis.
- **Evolução temporal**: canal endêmico, série anual e epicurva mensal
  desde 2010.
- **Ranking**, **pirâmide etária** e **tópicos de interesse** (22 variáveis
  da ficha do SINAN, 10 abertas de saída).

Tudo responde ao recorte: clicar numa macrorregião ou região de saúde muda
os seis cards e todos os gráficos, somando os municípios e recalculando as
taxas. E tudo **transiciona**: a câmera do mapa voa para o recorte novo, as
cores dos polígonos interpolam, e cada barra e linha dos gráficos desliza
para o valor novo em vez de ser redesenhada.

Como cada número é calculado: [`docs/metodologia.md`](docs/metodologia.md).
O que a extração traz e onde diverge do Ministério da Saúde:
[`docs/contrato-dados.md`](docs/contrato-dados.md).

## Como é feito

Streamlit redesenha a tela a cada interação, e isso não dá transição. O
mapa e os gráficos são **componentes próprios** — um iframe cada, com a
instância do deck.gl ou do ECharts viva entre reruns, recebendo só os dados
novos:

- [`src/mapa_componente.py`](src/mapa_componente.py) +
  [`src/componente_mapa/`](src/componente_mapa/) — o mapa. O spec do pydeck
  vai para o iframe, que chama `setProps` na instância viva: voo da câmera
  (`FlyToInterpolator`) e interpolação de cor. Clique volta com nonce.
- [`src/grafico_componente.py`](src/grafico_componente.py) +
  [`src/componente_grafico/`](src/componente_grafico/) — os gráficos, como
  opções ECharts: ranking, tópicos de interesse, canal endêmico, série
  anual, epicurva e pirâmide.

Os bundles (deck.gl 9.3, ECharts 5.6) vão vendorados: o painel não depende
de CDN. A história de como se chegou aqui, o que foi tentado antes e como
portar para outro painel está em [`docs/mapa-clique.md`](docs/mapa-clique.md).

## Dados

A extração agregada do SINAN da equipe parceira — a mesma que serve o
painel nacional (`../sinan/data/parquet/dashboard`): `incidence`,
`incidence_0_14`, `sinan_landing`, `_cache_ts`, `cache_ts_sim_obitos`,
`piramides`, mais as malhas da SES-PE em `data/support/`. Nenhum dado
nominal entra no projeto. Os parquets **não são versionados**; aponte
`SINAN_DATA_DIR` ou crie a junção `data -> ../sinan/data`.

## Como rodar

```bash
../sinan/.venv/Scripts/python -m streamlit run app.py
pytest                       # ~390 testes com os dados; ~80 sem eles
ruff check --select F app.py src tests
```

Sem os dados, `pytest` roda só o que não depende deles e diz o que pulou —
é o que o CI faz. Deploy na VM: [`docs/deploy.md`](docs/deploy.md) — porta
8504, `/cenarios/tbpe/`.

## Estrutura

```
tbpe/
├── app.py                        # composição da tela
├── src/
│   ├── estado.py                 # navegação PE → macro → região → município
│   ├── mapa.py                   # pydeck: camadas, escalas, legenda
│   ├── mapa_componente.py        # o mapa como componente vivo
│   ├── componente_mapa/          # deck.gl vendorado + protocolo do Streamlit
│   ├── grafico_componente.py     # os gráficos como opções ECharts
│   ├── componente_grafico/       # ECharts vendorado + protocolo do Streamlit
│   ├── data/                     # escopo, leitura, kpis, canal, recortes, geo
│   ├── doencas/tuberculose.py    # o pack: KPIs, cortes, variáveis, rótulos
│   └── theme/                    # a cara do painel em R
├── tests/
├── docs/                         # metodologia, contrato de dados, deploy, componentes
└── assets/                       # bandeira de PE e marca
```

Fonte: SINAN e SIM/Ministério da Saúde; população IBGE. Hierarquia
geográfica: Secretaria Estadual de Saúde de Pernambuco.
