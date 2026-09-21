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

**Feito em 21/set/2026 — `src/mapa_componente.py` + `src/componente_mapa/`.**
Um componente estático do Streamlit (`declare_component(path=...)`), sem
build nem npm: `index.html` carrega o bundle do deck.gl 9.3 e o módulo
`@deck.gl/json` (vendorados, porque a rede daqui bloqueia CDN e o painel
não pode depender disso), e `mapa.js` fala o protocolo de componente na mão
(`componentReady`, `setFrameHeight`, `setComponentValue`, escuta de
`streamlit:render`).

Como funciona:

- A `key` do componente é **estável** (`"mapa"`), então o iframe — e a
  instância do Deck dentro dele — sobrevive aos reruns. Cada render só chama
  `setProps`.
- O spec que chega é o mesmo JSON do pydeck (`Deck.to_json()`), convertido
  pelo `JSONConverter` do deck.gl — o `mapa.py` não mudou de linguagem.
- A camada de geografia ganhou `id="geografia"` e
  `transitions={"getFillColor": 450}`: trocar métrica, ano ou classificação
  **interpola a cor** dos polígonos em vez de trocar de vez.
- Quando o enquadramento pedido muda (macro, região, município, voltar), a
  câmera voa com `FlyToInterpolator` por 700 ms. O voo começa num
  `requestIdleCallback` (teto 350 ms), porque o `streamlit:render` chega no
  pico do redesenho da página e o laço de animação não ganha frame ali.
  Trocar de métrica não move a câmera, e quem arrastou não é puxado de volta.
- O clique volta como `{nonce, properties}`. O nonce muda a cada clique,
  inclusive no mesmo polígono, e `app.py` guarda o último tratado em
  `session_state` — é o que resolve o laço de rerun e o clique repetido que
  abre o detalhe, os dois problemas que a chave estável tinha no
  `st.pydeck_chart`.
- Roda do mouse desligada no `controller` (não mais pelo DOM, o
  `script_travar_zoom` ficou sem uso aqui); zoom pelos botões +/− do próprio
  componente, com transição de 300 ms.

**Medição:** no navegador embutido do app o `requestAnimationFrame` roda a
1 quadro/s (janela oculta), então o voo parece salto ali — falso negativo,
como todo teste de navegador nesta rede. Com frames de verdade a transição
foi observada em passos intermediários de zoom (5,91 → 6,57 → 6,69 → 6,85 →
6,91). Confira num navegador comum.

Para portar ao hansepe e ao RecifeTB: copiar `src/componente_mapa/` e
`src/mapa_componente.py`, dar `id` e `transitions` à camada em `mapa.py`, e
trocar o bloco do `st.pydeck_chart` no `app.py` pelo `desenhar` +
`alvo_do_clique` com nonce.
