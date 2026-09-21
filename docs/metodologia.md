# Metodologia — o que o painel mostra e como calcula

Referência para quem lê o painel. Cada número da tela vem de uma das regras
abaixo; onde há mais de uma definição possível, a escolhida e o motivo estão
escritos. As fórmulas vivem em `src/data/kpis.py`; o que a extração traz, e
onde diverge do Ministério da Saúde, em [`contrato-dados.md`](contrato-dados.md).

## Fonte e cobertura

- **SINAN** (notificações de tuberculose, residentes em Pernambuco), na
  extração agregada da equipe parceira — a mesma que serve o painel nacional
  (`../sinan/data`). Anos 2010–2024 com 12 meses; 2025 tem 8 meses na série
  mensal e é marcado como incompleto na tela.
- **SIM** para óbitos e mortalidade (`cache_ts_sim_obitos`): o campo de
  óbito do agregado do SINAN é zero para tuberculose. O SIM fecha um ano
  depois do SINAN — no ano corrente o card de mortalidade fica vazio.
- **População** por município e ano: a que vem no próprio agregado
  (`pop_total`, `pop_0_14_total`), estimativas do IBGE.
- **Geografia**: 185 municípios (Fernando de Noronha inclusive), 12 regiões
  de saúde e 4 macrorregiões de saúde, das malhas da SES-PE
  (`data/support/`).
- **Recorte por residência**, não por notificação — regra do boletim
  estadual. A série mensal (`_cache_ts`) é por notificação, e por isso a soma
  dos meses fica a poucos por cento da tabela anual.

## Os seis indicadores

Todos são do **ano selecionado** e do **território selecionado** (o estado,
uma macrorregião, uma região de saúde ou um município). A seta compara com o
ano anterior no mesmo território. Quando o território é uma região, cada
indicador é recalculado da **soma** dos municípios — nunca da média das
taxas municipais.

| Card | Numerador | Denominador | Observação |
|---|---|---|---|
| Incidência /100 mil | casos novos (`casos_total` do `incidence`, já filtrado a caso novo) | população | |
| Casos novos | idem | — | |
| Mortalidade /100 mil | óbitos do SIM com TB como causa básica | população | vazio no ano corrente |
| Interrupção do tratamento | `SITUA_ENCE = 2` (abandono) | todos os encerramentos | regra do painel em R; pelo MS (abandono + primário, sem os não avaliados) sobe ~4 pontos — `contrato-dados.md`, armadilha 4 |
| HIV positivo na testagem | positivos | positivos + negativos | positividade entre os **testados**; "não realizado" e "em andamento" ficam de fora |
| Cura | `SITUA_ENCE = 1` | todos os encerramentos | denominador da Tabela 9 do Boletim de TB; aproximação de coorte, porque o tratamento leva ~6 meses |

Os três cards de proporção mostram sob o valor a fração de onde saíram
("2.621 de 4.350"), e os dois números são os da mesma leitura — não uma
segunda conta dos mesmos dados.

## Mapa

Coroplético por **município**, **região de saúde** ou **macrorregião**
(seletor "Nível do mapa"), sem mapa-base — só os polígonos de PE, como no
painel em R —, para as quatro métricas que descem a município: incidência,
casos, mortalidade e cura. Interrupção e HIV não pintam o mapa porque a
fonte (`sinan_landing`) é lida uma geografia por vez.

Clicar num polígono abre o território, e **tudo** na tela segue: os seis
cards, o canal, a epicurva, a pirâmide, os tópicos. Dentro de uma macro o
mapa mostra só as regiões de saúde dela; dentro de uma região, só os
municípios dela. "Voltar" sobe um nível; "Ver Pernambuco inteiro" reseta.

### As três classificações de cor

| Método | Como corta | Para que serve |
|---|---|---|
| **Quebras naturais** | Jenks sobre a série do ano — agrupa parecidos, separa diferentes | ver o desenho do ano |
| **Quintis** | um quinto dos territórios em cada classe | "este município está no quinto superior" |
| **Escala fixa** | cortes declarados no pack, iguais todo ano | comparar dois anos; a única em que a legenda se lê em voz alta |

Cortes da escala fixa (`CORTES_FIXOS` em `src/doencas/tuberculose.py`),
medidos no próprio dado de 2024:

| Métrica | Cortes | Âncora |
|---|---|---|
| Incidência /100 mil | 0 · 20 · 40 · 55 · 110 | 40 = Brasil (40,4); 55 = PE (55,0); 20 e 110 = metade e dobro |
| Mortalidade /100 mil | 0 · 1 · 2,2 · 5 · 10 | 2,2 ≈ Brasil; 5 = PE (4,98); metade e dobro |
| Casos novos | 0 · 5 · 10 · 25 · 50 · 100 | degraus redondos; contagem não tem âncora epidemiológica |
| Cura (%) | 0 · 40 · 60 · 75 · 85 | 85 % = meta do Plano Nacional pelo Fim da TB e da OMS |

A última classe é aberta ("≥ 55") e só ganha o degrau seguinte quando há
território nele: com as 4 macros (máximo 74) a legenda para em "≥ 55"; com
os 185 municípios (máximo 445) aparece "≥ 110 — dobro de PE". A legenda traz
o **N** de cada classe.

## Evolução temporal

- **Canal endêmico** (meses do ano): incidência mensal do ano contra a faixa
  Q1–Q3 dos **cinco** anos anteriores (o painel em R usa três — a decisão
  está em `src/data/canal.py`). Funciona em qualquer recorte; num município
  pequeno a linha oscila, e o gráfico continua honesto, só mais ruidoso.
- **Todos os anos**: incidência anual desde 2010 no recorte, do `incidence`.
- **Epicurva**: casos por mês desde 2010, sempre embaixo, com o ano
  selecionado em destaque.

## Ranking

Os territórios do recorte atual ordenados pela métrica do mapa, com as
mesmas cores da legenda. Clicar numa barra destaca o território no mapa (ou
abre a macro/região). Municípios com menos de 5 encerramentos não entram no
ranking de cura nem são pintados no mapa — base pequena demais para
percentual.

## Pirâmide etária

Casos do ano e território por sexo e faixa etária (`piramides`), em
contagem ou por 100 mil habitantes da faixa.

## Tópicos de interesse

Distribuição percentual de cada variável da ficha de tuberculose no recorte,
do `sinan_landing` (`sexo = 'TOTAL'`). São 22 variáveis curadas em cinco
grupos; 10 abrem de saída. Códigos com o mesmo rótulo somam numa categoria
só — `SITUA_ENCE` vem reagrupado em Favorável/Desfavorável/Não avaliado.
Abaixo de 5 registros o percentual não é publicável e só a contagem aparece.

## O que fica de fora, e por quê

- **Coorte fechada de desfecho**, **contatos examinados** e **cultura em
  retratamento** por município: exigem microdado, ou datasets que desçam a
  município. Os dois indicadores de programa existem no sinan só em UF/BR.
- **Agravos: drogas e tabagismo**: o RecifeTB os tem porque lê o microdado
  de Recife; a extração agregada não os traz.
