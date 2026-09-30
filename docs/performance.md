# Performance

Medido em 30/set/2026, com tuberculose, no `data/` deste painel, já com a
janela de dez anos que entrou no mesmo dia. Reproduzir com:

```bash
python -m scripts.medir_performance
```

Antes deste dia o arquivo trazia a linha de base de agosto, feita quando o
mapa era `st.pydeck_chart` e os gráficos eram Altair. Desde 21/set os dois são
componentes próprios (deck.gl e ECharts), e as medições precisavam ser
refeitas.

## O alvo

**300 ms por interação.** É o tempo entre o clique e a tela nova: abaixo disso
a resposta é percebida como imediata, e acima começa a parecer que travou.

Vale para a **primeira** vez. O `st.cache_data` guarda cada leitura por 24
horas, então repetir o mesmo recorte custa quase nada.

## Quanto custa cada leitura

Mediana de cinco execuções, em milissegundos, sem o cache do Streamlit, em
2024 — o último ano fechado, que é onde o painel abre.

| Operação | PE | macrorregião | Recife |
|---|---:|---:|---:|
| `canal.epicurva` (10 anos) | 216 | 377 | 218 |
| `canal.montar` | 141 | 235 | 144 |
| `composicao` (um tópico) | 14 | 21 | 17 |
| `piramide_completa` | 14 | 18 | 16 |
| `ranking` | 8 | 7 | 7 |
| `serie_anual` | 7 | 16 | 10 |
| `valores_por_geografia` (o mapa) | 3 | 3 | 3 |
| **soma dos leitores** | **404** | **677** | **414** |
| `kpis.calcular` (os 6 cards) | 23 | 38 | 30 |

Somar a coluna superestima o que o usuário espera — os leitores são cacheados
separadamente e um clique não invalida todos —, mas serve de teto. E o teto
**ainda passa dos 300 ms**, em qualquer recorte.

## O problema está concentrado em dois gráficos

`canal.epicurva` e `canal.montar` somam **357 ms em PE e 612 ms numa
macrorregião**: 88% do custo do painel. Todo o resto junto não chega a 50 ms.

**A janela de anos, aplicada em 30/set, já cortou um terço disso.** Antes a
epicurva varria de 2010 até o ano selecionado; agora o padrão é dez anos, que
é o recorte do Boletim. Medido:

| janela | PE | macrorregião |
|---|---:|---:|
| 15 anos | 344 ms | 586 ms |
| **10 anos (padrão)** | **228 ms** | **385 ms** |
| 5 anos | 112 ms | 190 ms |

O custo é linear no número de anos, e a razão é que a epicurva monta a série
com **uma consulta por ano**.

**O que ainda a deixa cara.** Mesmo em dez anos, ela custa 216 ms aqui contra
93 ms no painel de hanseníase. A diferença é o `serie_mensal` daqui: ele tira
a população da região do `incidence`, e não do `_cache_ts`, porque este só tem
linha para município com caso no mês — sem isso, a incidência de uma região
sairia errada. É uma consulta a mais por ano, e ela se multiplica pelos dez.

O conserto seria buscar a população de todos os anos numa consulta só, em vez
de uma por ano. Vale 100 ms em PE e quase 200 na macrorregião, e não muda
número nenhum na tela — é a próxima coisa a fazer aqui, se performance voltar
à mesa.

A macrorregião é o pior recorte porque lê a partição `MUN` com uma lista de
municípios no `IN (...)`, pagando por vários onde o estado paga por um
agregado pronto. É o preço de o escopo atravessar a tela inteira.

## O mapa

| | |
|---|---|
| Payload de PE, 185 municípios | **0,12 MB** |
| Montar o `deck` (geometria + cores + tooltip) | 221 ms |
| Ler os valores do mapa | 3 ms |

O teto de payload está preso por teste. Com 0,12 MB há folga larga — a malha
vem simplificada e as coordenadas arredondadas.

Os 221 ms de montagem acontecem uma vez por recorte e ficam em cache. O clique
que só muda a cor não paga isso: o componente interpola no navegador, sem
refazer o deck.

## O que a suíte prende

`tests/test_performance.py` guarda o que mantém o tempo baixo, sem medir tempo
— tempo varia com a máquina e o teste falharia por motivo errado:

- nenhuma variável do SINAN é lida duas vezes no mesmo `kpis.calcular`;
- o teto de payload do mapa continua existindo.

## O que não foi medido

- Vários usuários simultâneos.
- O tempo de renderização no navegador, separado do tempo de servidor.
