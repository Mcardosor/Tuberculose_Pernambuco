# Performance

Medido em 30/set/2026, com tuberculose, no `data/` deste painel. Reproduzir
com:

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
| `canal.epicurva` (2010–2024) | 329 | 585 | 328 |
| `canal.montar` | 153 | 254 | 154 |
| `composicao` (um tópico) | 16 | 21 | 18 |
| `piramide_completa` | 15 | 19 | 16 |
| `ranking` | 9 | 8 | 9 |
| `serie_anual` | 8 | 16 | 9 |
| `valores_por_geografia` (o mapa) | 3 | 3 | 3 |
| **soma dos leitores** | **533** | **906** | **535** |
| `kpis.calcular` (os 6 cards) | 26 | 46 | 34 |

Somar a coluna superestima o que o usuário espera — os leitores são cacheados
separadamente e um clique não invalida todos —, mas serve de teto. E o teto
**passa muito dos 300 ms**, em qualquer recorte.

## O problema está concentrado em dois gráficos

`canal.epicurva` e `canal.montar` somam **482 ms em PE e 839 ms numa
macrorregião**: 90% do custo do painel. Todo o resto junto não chega a 60 ms.

Duas razões se somam:

**A epicurva monta quinze anos, um ano por consulta.** Ela varre de 2010 até o
ano selecionado, e cada ano é uma ida ao `_cache_ts`. O painel de hanseníase
resolveu isso com um seletor de janela — 5, 10 ou 15 anos, abrindo em 10 — e
lá a mesma operação custa 93 ms. **É a mudança de maior efeito disponível
aqui**, e não é otimização: dez anos é o recorte que o Boletim publica.

**A série mensal daqui é mais cara que a da hanseníase.** `serie_mensal` tira
a população da região do `incidence`, e não do `_cache_ts`, porque este só tem
linha para município com caso no mês — sem isso, a incidência de uma região
sairia errada. É uma consulta a mais por ano, e ela se multiplica pelos quinze
anos da epicurva.

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
