# CLAUDE.md

Guidance for Claude Code when working in this repository.

Painel de monitoramento da **tuberculose de Pernambuco**, em Streamlit.
É o **RecifeTB ampliado para o estado**: a mesma tela do painel em R da
equipe parceira (cabeçalho com bandeira, faixa de seis KPIs, mapa à esquerda
e abas à direita, tópicos de interesse embaixo), com a navegação
PE → macrorregião → região de saúde → município do hansepe. Não há painel de
origem de TB-PE a reproduzir: **os números seguem o Boletim Epidemiológico;
a cara segue o painel em R** (decisão de 20/set/2026).

Herda o core do painel nacional (`../sinan`: leitores, `Escopo`,
`recortes.py`), a geografia e a composição de tela do hansepe (`estado.py`,
`mapa.py` com três classificações, `graficos.py`, `canal.py`, `theme/`) e o
pack de doença do RecifeTB (`src/doencas/tuberculose.py`). Segue
`../sinan/docs/como-fazer.md`.

Substitui o `tbpe` da geração anterior (Superset + `dados_dashboard/`), que
ficou em `../tbpe-superset` e ainda tem o remoto do GitHub
(`Mcardosor/Tuberculose_Pernambuco`).

Documentação, código, commits e comentários em português.

## Comandos

Ambiente: o `.venv` do painel nacional, `../sinan/.venv` (Python 3.13). Os
dados são a extração do sinan: em dev, `data/` é uma **junção** para
`../sinan/data` (`New-Item -ItemType Junction`); em produção, volume.

```bash
streamlit run app.py                       # aplicação (porta 8501)
pytest                                     # suíte (~365 testes, ~70 s)
pytest tests/test_aplicacao.py -q          # ponta a ponta com AppTest
ruff check --select F app.py src tests     # código morto

docker compose up -d --build               # porta 8504, /cenarios/tbpe/
```

Config de dev do navegador: `../.claude/launch.json` tem `tbpe` na 8516.

## Arquitetura

**Fluxo:** `app.py` (página única) → `src/estado.py` (`Navegacao`, topo em
PE) → `src/data/*` → `src/mapa.py` e `src/graficos.py`.

- **`src/data/escopo.py`** — `Escopo(doenca, ano, nivel, uf, mun,
  municipios)`. `municipios` é a lista de uma macrorregião ou região de
  saúde: com ela, `particao_e_filtro_geo` manda os leitores à partição
  `MUN` com `geo_id IN (...)`. É o que faz **tudo** na tela seguir o clique
  no mapa.
- **`src/data/leitura.py`** — `incidencia`, `incidencia_0_14` e `obitos_sim`
  **somam** a partição `MUN` quando há `municipios`; por isso `kpis.calcular`
  serve o estado, a região e o município com a mesma função (o hansepe
  precisava de `calcular_regiao`). `serie_mensal` tira a população da região
  do `incidence`, não do `_cache_ts` — este só tem linha para município com
  caso no mês. `composicao` soma códigos com o mesmo rótulo (`SITUA_ENCE`
  vem reagrupado em Favorável/Desfavorável/Não avaliado).
- **`src/data/kpis.py`** — `calcular` com os seis KPIs e a fração de cada
  proporção (`hiv_positivos/hiv_testados`, `interrupcoes/interrupcao_base`,
  `cura_encerrada/encerramentos`), como no RecifeTB.
- **`src/doencas/tuberculose.py`** — o pack: 6 KPIs, `CORTES_FIXOS`
  ancorados em Brasil (40) e PE (55) por 100 mil e na meta de cura de 85 %,
  `NOMES_FIXOS` para a legenda, 22 variáveis curadas, 10 em destaque.
- **`src/mapa.py`** — pydeck (o spec vai ao componente próprio); camada
  `geografia` com `transitions`; `QUARTIL` são **quintis** (`QUANTIS = 5`);
  `alvo_do_clique` lê `cod_mun6`, `regiao`, `uf`. A escala fixa abre a
  última classe: com 4 macros e máximo 74, a legenda mostra "≥ 55", não
  "≥ 110" — a classe do dobro de PE só aparece quando há valor nela.
- **`app.py`** abre no **último ano fechado** (`_ano_inicial`: 12 meses no
  `_cache_ts`), não no último ano do seletor — 2025 tem 8 meses e abria com
  96 casos e incidência 1,00.

## Armadilhas

- **Módulos importados não recarregam** no Streamlit: editou `src/`,
  reinicie o servidor.
- **O mapa é componente próprio** (`src/mapa_componente.py` +
  `src/componente_mapa/`), não `st.pydeck_chart`: é o que mantém o deck vivo
  entre reruns e dá a transição (voo da câmera + interpolação de cor). A
  `key` é estável de propósito; o clique volta com nonce e `app.py` guarda o
  último em `session_state`. Bundles do deck.gl 9.3 vendorados (CDN
  bloqueado na rede). Detalhes e medição: `docs/mapa-clique.md`.
- **O ranking é ECharts** (`src/grafico_componente.py` +
  `src/componente_grafico/`, ECharts 5.6 vendorado), pelo mesmo motivo: o
  Altair não anima entre dois estados. A migração é gráfico a gráfico; o
  `graficos.py` Altair continua valendo para os demais. Regras: todo item
  leva `name` (é o que casa e anima), série com `id` fixo, clique com nonce.
- **Animação não se mede no navegador embutido do app**: ele roda a 1
  frame/s quando a janela está oculta e o voo vira salto. Falso negativo.
- **`interrupcao_trat_pct` e `hiv_pos_pct` não pintam o mapa**: vêm do
  `sinan_landing`, uma geografia por vez.
- **O SIM para em 2024**: `obitos_sim` e `componentes_municipais` toleram a
  partição ausente; no ano corrente o card de mortalidade fica vazio.
- **Ano parcial se detecta** (`meses_com_dado`), não se presume.
- `AGRAVDROGA` e `AGRAVTABAC` existem no RecifeTB porque lá há microdado; a
  extração agregada não as traz — não as devolva ao pack sem conferir.
- As do sinan continuam valendo: glob na raiz de dataset, `sexo='TOTAL'`,
  6 dígitos de município, `valor` com espaço, `except Exception` nunca
  `BaseException`, não importar `app.py` em teste.

## Estado

Montado em 20/set/2026 a partir do hansepe, com agregados. Sem microdado, o
que fica de fora: coorte fechada de desfecho, contatos examinados e cultura
em retratamento por município (`INDICADORES_PROGRAMA` vazio). Deploy:
`docs/deploy.md`.
