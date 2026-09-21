# Painel de Monitoramento da Tuberculose — Pernambuco

Painel de vigilância da tuberculose do estado de Pernambuco, em Streamlit,
com recorte por **município**, **região de saúde** e **macrorregião de
saúde**. É o painel de monitoramento do Recife da equipe parceira
(`../RecifeTB`, reconstrução do Shiny/R deles) ampliado para o estado, sobre
o core da família Cenários+ (`../sinan`) e a geografia do `../hansepe`.

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
taxas.

Como cada número é calculado: [`docs/metodologia.md`](docs/metodologia.md).
O que a extração traz e onde diverge do Ministério da Saúde:
[`docs/contrato-dados.md`](docs/contrato-dados.md).

## Dados

A extração agregada do SINAN da equipe parceira — a mesma que serve o
painel nacional (`../sinan/data/parquet/dashboard`): `incidence`,
`incidence_0_14`, `sinan_landing`, `_cache_ts`, `cache_ts_sim_obitos`,
`piramides`, mais as malhas da SES-PE em `data/support/`. Nenhum dado
nominal entra no projeto. Os parquets não são versionados; aponte
`SINAN_DATA_DIR` ou crie a junção `data -> ../sinan/data`.

## Como rodar

```bash
../sinan/.venv/Scripts/python -m streamlit run app.py
pytest
```

Deploy na VM: [`docs/deploy.md`](docs/deploy.md) — porta 8504,
`/cenarios/tbpe/`, no lugar do painel da geração anterior.

## Estrutura

```
tbpe/
├── app.py                  # composição da tela
├── src/
│   ├── estado.py           # navegação PE → macro → região → município
│   ├── mapa.py, graficos.py, resiliencia.py
│   ├── data/               # escopo, leitura, kpis, canal, recortes, geo
│   ├── doencas/tuberculose.py
│   └── theme/              # a cara do painel em R
├── tests/                  # ~365 testes
├── docs/                   # metodologia, contrato de dados, deploy
└── assets/                 # bandeira de PE e marca
```

Fonte: SINAN e SIM/Ministério da Saúde; população IBGE. Hierarquia
geográfica: Secretaria Estadual de Saúde de Pernambuco.
