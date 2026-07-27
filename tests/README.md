# Testes

```bash
pip install -r requirements-dev.txt
python -m pytest                 # tudo (~20 s)
python -m pytest -m "not lento"  # pula os que varrem a base inteira (~5 s)
python -m pytest -v              # nome de cada caso
```

Rodam **fora do runtime do Streamlit**, direto contra a camada de dados. Não
precisam de servidor no ar. Precisam de `dados_dashboard/` populado — ou seja,
do ETL já executado.

## O que cada arquivo cobre

| Arquivo | Pergunta que responde |
|---|---|
| `test_invariantes.py` | O mesmo número, calculado por dois caminhos, bate? |
| `test_filtros.py` | Alguma combinação de filtro quebra ou produz taxa impossível? |
| `test_precomputo.py` | O agregado servido do arquivo é idêntico ao calculado? |
| `test_regressoes.py` | Os bugs que já aconteceram voltaram? |

### `test_invariantes.py` — a classe de erro mais cara

Num painel de vigilância, o erro caro não quebra a página: mostra um número
errado. Estes testes comparam rotas independentes até o mesmo valor:

- somar os 185 municípios reproduz exatamente as 12 regiões e as 4 macrorregiões;
- `mapa` e `detalhe_unidade` são SQL diferentes e têm que concordar;
- os filhos somam o pai em todo drill-down;
- `novos + retratamento + transferência + sem informação = total` — se um rótulo
  do SINAN mudar de grafia, ele sai silenciosamente dos buckets e a incidência
  despenca sem erro nenhum;
- a coorte fecha no denominador e as composições 100% fecham em 100%;
- a pirâmide etária perde exatamente os casos de sexo ignorado, nem um a mais.

### `test_regressoes.py` — bugs que já aconteceram

Cada teste trava um bug real:

- **NaN nos formatadores.** `int(x or 0)` não protege contra NaN — NaN é
  verdadeiro em Python. `sum()` do SQL devolve NULL sem linhas, vira NaN no
  pandas, passa pelo `or` e estoura no `int()`. Derrubava a página com filtros
  geográficos contraditórios.
- **Ausente ≠ zero.** `if df.duracao_mediana` escondia uma mediana legítima de
  0 dias — que é o valor mais comum nesta base.
- **Enrolamento dos anéis do GeoJSON.** O d3-geo (motor do Plotly) exige anel
  externo **horário**, convenção contrária à do RFC 7946. Com anéis
  anti-horários, 170 dos 185 municípios renderizavam como um retângulo cobrindo
  o mapa inteiro — sem nenhum erro no console.
- **Injeção na URL do Superset.** O campo é texto livre e vira atributo `src`
  de iframe.
- **Altura do mapa.** Tem que acompanhar a proporção do recorte.

### `test_precomputo.py`

Um pré-cômputo que diverge é pior que não ter pré-cômputo — o painel serve
número errado sem sinal nenhum. Cobre a igualdade com o cálculo ao vivo, a
invalidação automática quando os Parquets mudam, e a **ordenação determinística**
(regressão: `ORDER BY casos DESC` sem desempate fazia municípios empatados
trocarem de posição a cada refresh).

## Antes de um deploy

```bash
python etl/preparar_dados.py
python etl/baixar_populacao.py
python etl/precomputar.py
python -m pytest
```

Se `_agregados.json` estiver desatualizado, `test_precomputo.py` acusa em vez
de deixar o painel servir número velho.

## O que estes testes NÃO cobrem

- **Clique no polígono do mapa.** A automação de navegador não entrega eventos
  de mouse ao canvas do Plotly. Por isso o drill-down tem o seletor explícito
  como caminho principal — o clique é atalho, não a única via.
- **Layout e CSS.** Nada aqui olha pixel.
- **A aba Análise Livre com Superset real no ar.**
