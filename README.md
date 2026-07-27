# Dashboard TB · Pernambuco

Painel de vigilância epidemiológica da tuberculose do estado de Pernambuco, com
recorte por **município**, **região de saúde** e **macrorregião de saúde**.

É um híbrido deliberado dos três painéis da família Cenários+:

| Peça | Origem |
|---|---|
| Estrutura (hero, KPIs fixos no topo, seções, tema) | [`dashboard-tb-recife`](../dashboard-tb-recife) |
| Gráficos (pirâmide etária, composição 100% de desfecho, heatmap, oportunidade do tratamento, tendência) | [`dashboard-tb-v3`](../dashboard-tb-v3) — painel nacional |
| Hierarquia geográfica e a aba de análise livre | [`dashboard-tb-pe`](../dashboard-tb-pe) — painel Superset de PE |

## Conteúdo

- **Mapa** — coroplético nos três níveis geográficos, alternados por botão, com
  métrica selecionável (casos, incidência, cura %, abandono %), ranking lateral,
  drill-down para o nível de baixo e tabela completa.
- **Epidemiologia** — incidência e mortalidade por 100 mil, coorte de desfecho,
  casos novos × retratamento, sazonalidade mensal contra a média histórica e
  indicadores clínicos ao longo do tempo com as metas da OMS.
- **Perfil & Clínico** — sexo, raça/cor, forma clínica, pirâmide etária de casos
  e de óbitos, desfecho × raça e × HIV, diagnóstico (baciloscopia, TRM-TB) e
  oportunidade do tratamento.
- **Comorbidades** — agravos associados, populações vulneráveis, desfecho por
  vulnerabilidade e heatmap por macrorregião.
- **Análise Livre** — o Apache Superset de PE embutido.

## Regras de negócio

As mesmas dos outros painéis da família — documentadas em `src/indicadores.py`:

- **Incidência** usa só casos novos (Caso Novo + Não Sabe + Pós-óbito).
- **Coorte** (cura/abandono/óbito) tem denominador = casos **encerrados**;
  exclui transferidos e sem informação, que não têm desfecho conhecido.
- **Abandono** soma Abandono + Abandono Primário (o SINAN separa os códigos).
- **Coinfecção HIV**: denominador = testados (Positivo + Negativo), não o total.
- **Recorte por residência**, não por notificação — regra do boletim
  epidemiológico estadual.
- **Denominador populacional**: IBGE por município e ano, somado no nível
  geográfico ativo. Séries de vários anos usam pessoas-ano.

### Limitações conhecidas

- **Não há linkage com o SIM.** Diferente do painel de Recife, o óbito por TB
  aqui vem do campo de encerramento do SINAN, sujeito a subnotificação. A subida
  da série de mortalidade reflete sobretudo a melhora do preenchimento desse
  campo ao longo dos anos.
- **Filtros de perfil distorcem a incidência**: o numerador é o subgrupo
  filtrado, mas o IBGE só fornece a população total. A interface avisa quando
  isso acontece.
- **Ano parcial é detectado, não presumido.** O painel nacional assume que o
  último ano é sempre parcial — verdade lá, porque o extrato é do ano corrente.
  No extrato de PE isso seria falso: 2025 é um ano fechado, com os 12 meses e
  7.463 casos, em linha com 2023 (7.454) e 2024 (7.442). `_ano_parcial()` marca
  o último ano só se ele ainda estiver correndo ou não tiver os 12 meses. Marcar
  ano fechado como parcial desacredita o aviso quando ele for verdadeiro.
  Ressalva: o SINAN aceita notificação retroativa, então mesmo um ano com 12
  meses pode subir um pouco em extrações futuras.
- **2007, 2010, 2023 e 2026** não têm estimativa populacional publicada pelo
  IBGE — são interpolados/extrapolados, marcados na coluna `estimado`.

## Dados

142.365 notificações com residência em PE, 2001–2025, 185 municípios com 100% de
match na hierarquia de região/macrorregião de saúde.

```bash
python etl/preparar_dados.py     # SINAN (residência PE) + hierarquia + GeoJSONs
python etl/baixar_populacao.py   # população IBGE por município e ano (SIDRA)
python etl/precomputar.py        # agregados da visão padrão — rode SEMPRE por último
```

O primeiro script lê os parquets do painel nacional
(`../dashboard-tb-v3/dados_dashboard/tuberculose_*_tratado.parquet`) e os
shapefiles da SES-PE (`../Pernanbuco/shapefiles/`).

### Gotcha dos GeoJSONs: ordem de enrolamento

O d3-geo — motor dos mapas do Plotly — trata polígonos como esféricos e usa a
convenção **contrária** à do RFC 7946: o anel externo tem de ser **horário**.
Com anéis anti-horários, 170 dos 185 municípios renderizavam como um retângulo
cobrindo o mapa inteiro ("o globo menos este município"). O `preparar_dados.py`
rebobina todos os anéis; não troque essa função por um rewind "padrão GeoJSON".

Na mesma linha: `geo.fitbounds="locations"` é ignorado nesta versão do Plotly, e
por isso `src/mapas.py` calcula o enquadramento (`lonaxis`/`lataxis`) e a altura
a partir da geometria do recorte.

## Performance

Medido nesta máquina, sem cache do Streamlit (mediana de 5 execuções):

| | Antes | Depois |
|---|---:|---:|
| `SELECT count(*)` | 27,6 ms | **0,4 ms** |
| Seção Perfil | 347 ms | **55 ms** |
| Seção Clínico | 333 ms | **90 ms** |
| Seção Comorbidades | 296 ms | **68 ms** |
| Tela mais pesada (topo + Perfil & Clínico) | 751 ms | **196 ms** |

E os agregados da primeira tela nem são calculados em execução — vêm prontos do
ETL (`etl/precomputar.py` → `dados_dashboard/_agregados.json`, 85 KB):

| Seção (visão padrão) | Ao vivo | Servido do arquivo |
|---|---:|---:|
| `resumo` | 920 ms* | **2,0 ms** |
| `clinico` | 125 ms | **2,2 ms** |
| `comorbidades` | 82 ms | **0,9 ms** |
| `mapa` (3 níveis) | 47 ms cada | **~1,5 ms** cada |

<sub>*inclui a materialização da base no DuckDB, paga uma vez por processo.</sub>

Quatro mudanças explicam o ganho:

1. **Uma conexão DuckDB em memória por processo** (`src/banco.py`), com tb/pop/mun
   materializadas na inicialização. Antes cada consulta abria conexão e reparseava
   o Parquet — 27 ms de overhead × ~10 consultas por seção. Cada consulta usa um
   `.cursor()` da conexão compartilhada, que é o padrão thread-safe do DuckDB.
2. **Contagens em lote** (`_contagens`): as 6 distribuições categóricas da seção de
   perfil viram um `UNION ALL` — uma varredura em vez de seis. A contagem de
   desfecho, que era feita duas vezes, é reaproveitada.
3. **Agregados pré-computados no ETL** (`src/precomputado.py`). Só a **visão
   padrão** — PE inteiro, série completa, sem filtro de perfil — porque o espaço
   de filtros é combinatório e não dá para cobrir. Qualquer filtro cai no DuckDB.
   O arquivo guarda a impressão digital dos Parquets e **se auto-invalida** se
   eles mudarem: melhor recalcular do que servir número velho em painel de
   vigilância. Se o arquivo faltar ou estiver velho, a sidebar avisa e o painel
   segue funcionando normalmente, só mais devagar.
4. **Pré-aquecimento em thread de fundo** que materializa a conexão DuckDB — com
   o pré-cômputo, o custo frio migrou da primeira tela para a primeira interação
   com filtro.

> **Ordenação determinística.** O pré-cômputo revelou que `ORDER BY casos DESC`
> sem desempate devolvia unidades empatadas em ordem arbitrária — dois municípios
> com 176 casos trocavam de posição entre execuções. Todas as consultas que
> alimentam ranking agora têm critério de desempate explícito. Sem isso, o
> ranking mudava a cada refresh e o arquivo pré-computado não era reproduzível.

Somado a isso: `@st.cache_data` em toda a camada de agregação (o `Filtros` é
`frozen`, então serve de chave de cache) e navegação por `segmented_control`, que
executa só a seção ativa.

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest                 # 84 casos, ~20 s
python -m pytest -m "not lento"  # ~5 s
```

Rodam fora do runtime do Streamlit, direto contra a camada de dados. Cobrem
invariantes epidemiológicos (o mesmo número por caminhos diferentes), ~18
combinações de filtro incluindo as degeneradas, igualdade entre pré-computado e
cálculo ao vivo, e regressões pontuais. Detalhes em [tests/README.md](tests/README.md).

Rode depois do ETL e antes de todo deploy — `test_precomputo.py` acusa se
`_agregados.json` estiver desatualizado.

## Como rodar

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

### Superset na Análise Livre

A URL vem da variável `SUPERSET_URL` (padrão: `http://localhost:8590`). O
Superset bloqueia embed por padrão; para liberar, defina no serviço do
[`dashboard-tb-pe`](../dashboard-tb-pe):

```bash
SUPERSET_FRAME_ANCESTORS="http://localhost:8512 https://painel.cenarios.unb.br"
```

Sem essa variável o iframe fica em branco e o botão "Abrir em nova aba" é o
caminho alternativo.

## Estrutura

```
dashboard-tb-pernambuco/
├── app.py                  # hero, KPIs, navegação e as 5 seções
├── etl/
│   ├── preparar_dados.py   # SINAN + hierarquia + GeoJSONs (com rebobinagem)
│   ├── baixar_populacao.py # população IBGE por município/ano
│   └── precomputar.py      # agregados da visão padrão → _agregados.json
├── tests/                  # pytest — ver tests/README.md
└── src/
    ├── banco.py            # conexão DuckDB única (tb / pop / mun em memória)
    ├── precomputado.py     # leitura do store + invalidação por fingerprint
    ├── seguranca.py        # validação da URL que vira iframe
    ├── filtros.py          # estado imutável dos filtros → WHERE + chave de cache
    ├── indicadores.py      # agregações epidemiológicas
    ├── mapas.py            # coropléticos dos três níveis
    ├── graficos.py         # construtores Plotly
    └── styles.py           # CSS, hero, KPI cards, dark mode
```

Fonte: SINAN NET, Ministério da Saúde. Hierarquia geográfica: Secretaria
Estadual de Saúde de Pernambuco.
