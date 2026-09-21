# Drill-down por clique no mapa — investigação

O item 3.2 do cronograma pede navegação `BR → UF → município` por clique no
mapa. Este documento registra o que já foi descartado, para a próxima
tentativa não repetir o caminho.

## O que funciona hoje

O mapa renderiza e reage à métrica ativa, com escala em quebras naturais e legenda.
A navegação existe e usa a mesma máquina de estados (`src/estado.py`) que o
clique vai usar — só que acionada pelos seletores da barra lateral.

## O que está bloqueado

**`px.choropleth_map` (maplibre) não emite `plotly_click`.**

Verificado das duas formas:

- clique real, pela automação do navegador, no ponto exato do polígono
  (confirmado com `elementFromPoint` devolvendo o canvas do maplibre e
  `queryRenderedFeatures` devolvendo a camada `plotly-trace-layer-*-fill`);
- clique sintético, despachando `mousedown`/`mouseup`/`click` no canvas.

Nenhum dos dois dispara `plotly_click`, `plotly_selected` ou
`plotly_selecting`. Sem evento no Plotly, o `on_select` do Streamlit não tem
o que reportar.

**`px.choropleth` (SVG) emite clique, mas não enquadra.**

A versão SVG renderiza os 27 polígonos como `path.choroplethlocation`, com o
dado acessível em `__data__.loc` — ou seja, o clique seria trivial de mapear.
Mas `fitbounds="locations"` não surte efeito no cliente: a área do mapa fica
com 153px de altura útil, os polígonos saem em escala mundial e o fundo da
geo é preenchido. Tentado com e sem `basemap_visible`, e com `update_geos` em
vez de `geo=` no `update_layout` — este último era um erro real de minha
parte, porque passar o dicionário inteiro sobrescreve o enquadramento, mas
corrigi-lo não resolveu o problema de fundo.

## Resolvido: pydeck

Funciona. Verificado no navegador com cliques reais: clicar num estado navega
para ele e o mapa redesenha com os municípios; clicar num município navega
para ele. Em cada passo, a trilha, os seletores da barra lateral, os KPIs e a
legenda acompanham.

O evento do `st.pydeck_chart` traz a feição inteira, com as propriedades — a
chave sai de `properties.cod_mun6` ou `properties.uf`. A extração é tolerante
a formato inesperado de propósito: o payload é detalhe interno do Streamlit e
já mudou entre versões, então uma mudança futura faz o mapa deixar de navegar,
não a página cair.

A legenda passou a ser HTML, já que o deck.gl não desenha uma. Mesmo padrão
dos cards de KPI.

## O caminho descartado (mantido como registro)

**pydeck.** `st.pydeck_chart` tem `on_select` nativo (verificado na assinatura)
e o `GeoJsonLayer` do deck.gl tem *picking* por GPU, que é o mecanismo de
clique mais confiável dos três. A geometria já está em GeoParquet simplificado
e o `pydeck` já vem instalado com o Streamlit, então não há dependência nova.

O custo é a legenda: o deck.gl não desenha uma, e ela teria de ser construída
em HTML — o que já é o padrão do projeto para os cards de KPI, então há
precedente.

## Alternativa, se o pydeck também falhar

Manter o mapa como visualização e mover a navegação para uma lista clicável ao
lado dele, com os mesmos botões reais usados nos cards de KPI. Perde a
paridade com o original, e por isso é a última opção — mas é a única que não
depende de evento de terceiros.

## Transição — o que falta para o mapa "deslizar" entre um clique e outro

Pedido de 20/set/2026: a troca de enquadramento ao clicar (estado → macro →
região → município) é seca, e queremos uma transição que os olhos acompanhem.

**O que já foi tentado e não serve:**

- `transition_duration` + `FlyToInterpolator` no `ViewState` do pydeck: o
  pydeck emite os dois, mas o Streamlit **recria o contêiner e o canvas do
  deck a cada rerun** — medido no navegador, inclusive com `key` estável. Sem
  instância anterior não há câmera de onde partir (`src/mapa.py`, comentário
  no `ViewState`).
- Fade/escala de entrada em CSS: com o canvas nascendo transparente sobre o
  branco a cada rerun, virou piscada em toda interação, não só na navegação.
  Removido em 24/ago/2026 (`src/theme/componentes.py`, "O mapa não anima").

**O caminho que resta:** um componente próprio (`st.components.v1.html` com
deck.gl por CDN, ou um componente bidirecional) que **mantenha a instância do
deck viva** entre reruns e receba só o novo `viewState` e os novos dados. Aí
`flyTo` e a transição de cor dos polígonos (`transitions` do `GeoJsonLayer`)
funcionam de verdade. O clique volta pelo componente, não pelo `on_select`
do `st.pydeck_chart`. Custo estimado: um a dois dias, mais JS para a equipe
manter; e o `script_travar_zoom` deixa de ser necessário, porque o controle
passa a ser nosso. Testar aqui primeiro e portar para hansepe e RecifeTB —
os três têm o mesmo `mapa.py`.
