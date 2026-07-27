# Criando um gráfico no Superset — passo a passo

Guia para quem nunca usou. Ao final você terá um gráfico salvo, feito com os
dados reais de tuberculose de Pernambuco.

**Onde:** https://painel.cenarios.unb.br/cenarios/tbpe → aba **🔬 Análise Livre**
→ botão **Entrar com GitHub**.

> Uma janelinha do GitHub abre para o login. Ela fecha sozinha e o Superset
> aparece na própria página. Se preferir uma aba separada, use **↗ Abrir em
> outra aba**.

---

## O vocabulário, em três palavras

Antes de clicar em qualquer coisa, três termos que o Superset usa o tempo todo:

| Termo | O que é | No nosso caso |
|---|---|---|
| **Conjunto de dados** | a tabela com os dados | `tuberculose_pe` — uma linha por notificação |
| **Dimensão** | por onde você quer *separar* | município, ano, sexo, raça/cor |
| **Métrica** | o que você quer *contar ou somar* | `Casos` |

A frase que resume qualquer gráfico:

> **quero ver [MÉTRICA] separada por [DIMENSÃO]**

*Casos por município. Casos por ano. Casos por sexo.* Sempre esse formato.

---

## Exercício: casos de TB por macrorregião de saúde

### 1 · Novo gráfico

No menu de cima: **Gráficos** → botão **+ Gráfico** (canto direito).

### 2 · Escolha os dados e o tipo

- **Escolha um conjunto de dados:** digite `tuberculose_pe` e selecione
- **Escolha o tipo de gráfico:** clique em **Barra** (ícone de barras)
- Botão **Criar novo gráfico**

### 3 · Monte a pergunta

A tela tem três partes: fontes à esquerda, controles no meio, resultado à direita.

No meio, preencha:

- **Dimensões** → clique em *Solte uma coluna aqui* → escolha **`macro_saude`**
- **Métricas** → clique em *Solte uma métrica aqui* → aba **Métricas salvas** →
  escolha **`Casos`**

### 4 · Veja o resultado

Botão **Criar gráfico** (embaixo, à direita).

Devem aparecer 4 barras — as quatro macrorregiões de saúde de PE. A
**Metropolitana** domina, com cerca de 80% das notificações do estado.

### 5 · Salve

Botão **Salvar** (canto superior direito) → dê um nome, por exemplo
*Casos por macrorregião — teste* → **Salvar**.

Pronto. Está em **Gráficos**, e pode ser adicionado a qualquer painel depois.

---

## Variações para experimentar

Trocando **uma coisa** de cada vez, você cobre quase tudo que se faz no dia a dia:

| Quero ver… | Dimensão | Tipo de gráfico |
|---|---|---|
| Evolução ao longo do tempo | `ano_notificacao` | Linha |
| Ranking de municípios | `municipio` | Barra |
| Distribuição por sexo | `sexo` | Pizza |
| Desfecho do tratamento | `situacao_encerramento` | Pizza ou Barra |
| Forma clínica | `forma` | Pizza |
| Perfil racial | `raca_cor` | Barra |
| Cruzamento de duas variáveis | `sexo` + `raca_cor` | Barra empilhada |

Para cruzar duas variáveis, basta arrastar **duas** colunas para *Dimensões*.

---

## Filtrar (recortar os dados)

No painel do meio existe a caixa **Filtros**. Alguns exemplos úteis:

- só um ano → `ano_notificacao` **igual a** `2025`
- só a capital → `municipio` **igual a** `Recife`
- só quem tem HIV → `status_hiv` **igual a** `Positivo`
- últimos anos → `ano_notificacao` **maior ou igual a** `2020`

Filtro **muda os números**, não só a visualização. Se você filtrar por 2025 e
somar as barras, vai dar os casos de 2025 — não os 142.365 do total.

---

## Três armadilhas comuns

**1. O gráfico não aparece e a tela pede "valores obrigatórios".**
Falta a métrica ou a dimensão. Todo gráfico precisa de pelo menos uma métrica.

**2. Um município aparece com 100% de cura.**
Cuidado com **denominador pequeno**. Município que encerrou 2 casos e curou os 2
mostra 100%, e isso não significa desempenho melhor que outro com 180 de 200
curados. Antes de comparar percentuais, olhe quantos casos existem — o painel
principal já esconde taxas com menos de 20 casos encerrados justamente por isso.

**3. Somar percentuais.**
Percentual não se soma nem se tira média entre municípios. Se precisar do valor
do estado, calcule sobre o total: some os numeradores e os denominadores
separadamente.

---

## O que os dados são (e o que não são)

- **142.365 notificações**, 2001–2025, de residentes em Pernambuco
- Recorte por **residência do paciente**, não por onde foi notificado — é a
  regra do boletim epidemiológico estadual
- Cada linha é **uma notificação**, não uma pessoa: quem adoeceu duas vezes
  aparece duas vezes
- **Óbito por TB** vem do campo de encerramento do SINAN, não do SIM. A série
  cresce ao longo dos anos sobretudo porque o preenchimento melhorou, não
  porque a mortalidade explodiu

---

## Se algo der errado

| Sintoma | O que fazer |
|---|---|
| Tela pedindo login de novo | a sessão expirou; entre pelo botão do GitHub |
| "DB engine Error" | avise a equipe técnica — é a conexão com o banco |
| Gráfico vazio | provavelmente um filtro exclui tudo; limpe os filtros |
| Perdi meu gráfico | menu **Gráficos** lista tudo que você salvou |

Nada do que se faz aqui altera os dados nem os painéis dos outros — criar,
editar e apagar gráficos é seguro para explorar.
