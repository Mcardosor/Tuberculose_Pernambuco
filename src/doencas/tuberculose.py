"""Pacote de configuração da Tuberculose — Pernambuco.

Segue o padrão de *disease pack* do projeto original: o core é único e cada
doença é só configuração. Cores, rótulos e ordem dos KPIs vêm daqui.

É o pack do RecifeTB ampliado para o estado: mesmos KPIs, mesmas métricas de
mapa, mesmas variáveis de composição — só muda o que é de Recife (âncoras da
escala fixa e as duas variáveis que só existem no microdado de lá).

**A paleta é híbrida, por decisão de 28/ago/2026.** O cromo institucional é o
do painel de origem em R, para que quem usa o painel da equipe parceira
reconheça o novo de imediato. As cores de **métrica** seguem a família
Cenários: incidência ocre, óbito vermelho, cura verde — a decisão 6 do painel
nacional, "cor é por métrica, não por doença", que existe para o leitor não
reaprender a legenda a cada painel.
"""

from __future__ import annotations

from ..theme import cores

DOENCA = "TUBERCULOSE"
TITULO = "Tuberculose"

#: Cor por **métrica**, não por doença. As rampas do mapa saem daqui.
CORES = {
    # --- Cromo: identidade do painel de origem em R -------------------------
    # Só vestem cabeçalho, faixa e elementos de marca — nunca um dado.
    "primary": "#12346B",
    "secondary": "#1E73BE",
    "accent": "#4A8EFF",
    # --- Métricas: semântica da família ------------------------------------
    "casos": "#C1440A",
    "obitos": "#DC2626",
    "cura": "#16A34A",
    "cura_pct": "#16A34A",
    # Cinza médio e não quase-preto: `pop` em #111827 dava 2,4:1 de contraste
    # no tema escuro. Não é exibido como card hoje, mas a rampa do mapa usa a
    # cor da métrica.
    "pop": "#6B7280",
    "incid": "#92400E",
    # Herda o azul da família, e ele **colide com o cromo institucional**:
    # `#1D4ED8` e `#12346B` são ambos azuis. Fica assim até a medição de
    # contraste com o mapa de pé; a correção sai de lá com número, não do
    # olho. Se ceder, cede o cromo: a semântica de métrica é compartilhada
    # entre painéis, a identidade não.
    "mortalidade": "#1D4ED8",
    "letalidade": "#6D28D9",
    "hiv_pos_pct": "#BE185D",
    "interrupcao_trat_pct": "#B45309",
    "casos_0_14": "#B45309",
    "taxa_det_0_14": "#92400E",
}

ROTULOS = {
    "casos": "Casos novos",
    "obitos": "Óbitos",
    "cura": "Curas",
    "cura_pct": "Proporção de cura (%)",
    "pop": "População",
    "incid": "Incidência (por 100 mil hab.)",
    "mortalidade": "Taxa de mortalidade (por 100 mil hab.)",
    "letalidade": "Letalidade (%)",
    "casos_0_14": "Casos de 0 a 14 anos",
    "taxa_det_0_14": "Taxa de detecção 0–14 (por 100 mil hab.)",
    "hiv_pos_pct": "HIV positivo na testagem (%)",
    "interrupcao_trat_pct": "Interrupção de tratamento (%)",
}

#: Quais KPIs aparecem e em que ordem — os seis da faixa do RecifeTB.
LAYOUT_KPI = (
    "incid",
    "casos",
    "mortalidade",
    "interrupcao_trat_pct",
    "hiv_pos_pct",
    "cura_pct",
)

#: Fração exibida sob o valor do card. Os dois campos precisam sair da mesma
#: fonte, ou a conta mostrada não dá a porcentagem mostrada — ver o comentário
#: de `cura_encerrada` em `kpis.py`.
FRACAO_KPI = {
    "cura_pct": ("cura_encerrada", "encerramentos"),
    "interrupcao_trat_pct": ("interrupcoes", "interrupcao_base"),
    "hiv_pos_pct": ("hiv_positivos", "hiv_testados"),
}

#: Métricas oferecidas no mapa.
#:
#: `cura_pct` e não `cura`: coroplético pinta **área**, e área não tem relação
#: com população. Com a contagem crua, Recife ficaria no tom mais escuro por
#: ser Recife — o mapa de curas seria, na prática, um mapa de população.
#: Proporção é comparável entre lugares de tamanhos diferentes, que é a razão
#: de existir de um coroplético. A contagem continua no card, com denominador.
#:
#: `interrupcao_trat_pct` e `hiv_pos_pct` ficam de fora: vêm do
#: `sinan_landing`, que o leitor consulta uma geografia por vez — serve para o
#: card, não para pintar 185 municípios de uma vez.
METRICAS_MAPA = ("incid", "casos", "mortalidade", "cura_pct")


#: Métricas em que uma queda é boa. `cura` fica de fora de propósito.
BOM_SE_CAI = frozenset(
    {"casos", "obitos", "incid", "mortalidade", "letalidade",
     "casos_0_14", "taxa_det_0_14", "hiv_pos_pct", "interrupcao_trat_pct"}
)

#: Métricas exibidas com casas decimais.
TAXAS = frozenset(
    {"incid", "mortalidade", "letalidade", "taxa_det_0_14",
     "hiv_pos_pct", "interrupcao_trat_pct", "cura_pct"}
)

#: Paletas explícitas do mapa, herdadas do original. Quando existem, têm
#: precedência sobre a rampa gerada a partir da cor da métrica.
PALETA_MAPA = {
    "casos": (
        "#F5A878", "#EF8450", "#E56028", "#D04010",
        "#B82E08", "#921800", "#5E0C00",
    ),
    "incid": (
        "#E8B87A", "#D49040", "#BA7018", "#9A5210",
        "#7A3808", "#5C2404", "#3A1400",
    ),
}


def cor(metrica: str) -> str:
    return CORES.get(metrica, CORES["secondary"])


#: Cortes da **escala fixa** do mapa, por métrica.
#:
#: Só esta classificação torna dois anos comparáveis: as quebras naturais e os
#: quintis recalculam os limites a partir do próprio ano, então a régua muda
#: debaixo do mapa.
#:
#: **Cada corte tem uma âncora, e ela está escrita aqui.** Escala fixa com
#: números escolhidos no olho é pior que quebra natural: fixa o arbítrio. O que
#: a âncora compra é a legenda poder ser lida em voz alta — "acima do dobro de
#: Pernambuco" diz algo; "acima de 110" não.
#:
#: Medidas em 2024, do próprio dataset (`incidence`, nível UF e BR; óbitos
#: do SIM): Brasil 40,4 por 100 mil; Pernambuco 55,0. Mortalidade: Brasil
#: ~2,2; Pernambuco 4,98. Nos 185 municípios de 2024 a incidência cai em
#: 68 · 70 · 13 · 28 · 6 por classe — nenhuma fica vazia.
CORTES_FIXOS = {
    # metade do Brasil (20) · Brasil (40) · PE (55) · 2× PE (110)
    "incid": (0, 20, 40, 55, 110),
    # Contagem não tem âncora epidemiológica: são degraus redondos, escolhidos
    # para separar o município de dezenas do de centenas.
    "casos": (0, 5, 10, 25, 50, 100),
    # metade do Brasil (1) · Brasil (2,2) · PE (5) · 2× PE (10)
    "mortalidade": (0, 1, 2.2, 5, 10),
    # **Aqui a âncora é oficial**: a meta de cura do Plano Nacional pelo Fim da
    # Tuberculose e da OMS é de 85%. Os degraus abaixo dela são os patamares
    # que o programa costuma reportar.
    "cura_pct": (0, 40, 60, 75, 85),
}


#: Nome de cada classe da escala fixa, na ordem dos cortes — é o que a
#: legenda mostra ao lado do número, para a faixa poder ser lida em voz alta.
NOMES_FIXOS = {
    "incid": ("baixa", "abaixo do Brasil", "entre Brasil e PE", "acima de PE", "dobro de PE"),
    "mortalidade": ("baixa", "abaixo do Brasil", "entre Brasil e PE", "acima de PE", "dobro de PE"),
    "cura_pct": ("crítica", "baixa", "intermediária", "perto da meta", "meta OMS"),
}


def cortes_fixos(metrica: str) -> tuple[float, ...] | None:
    """Cortes declarados da métrica, ou ``None`` quando não há.

    Sem cortes, `mapa.escala` cai em quebras naturais em vez de estourar:
    mapa sem cor por falta de configuração é pior que mapa classificado de
    outro jeito.
    """
    return CORTES_FIXOS.get(metrica)


def nomes_fixos(metrica: str) -> tuple[str, ...] | None:
    return NOMES_FIXOS.get(metrica)


#: Rótulos curtos, para controles onde o nome inteiro não cabe.
#:
#: O painel de origem põe o rótulo inteiro e deixa o CSS cortar — vira
#: "Taxa de mort..." e "Interrupcao d...", que não identificam a métrica.
#: Aqui o nome é curto **de verdade**, e o completo continua acessível no
#: tooltip do card, junto com a descrição.
#:
#: A unidade fica no rótulo das taxas de propósito: um "55,0" sem "por
#: 100 mil" ao lado é um número sem grandeza.
ROTULOS_CURTOS = {
    "incid": "Incidência /100 mil",
    "casos": "Casos novos",
    "mortalidade": "Mortalidade /100 mil",
    "interrupcao_trat_pct": "Interrupção do tratamento",
    "hiv_pos_pct": "HIV positivo na testagem",
    "cura_pct": "Cura",
}


#: Ícone de cada KPI, como no painel de origem — um glifo redondo à direita
#: do card. SVG inline (traço em `currentColor`) para herdar a cor da métrica
#: sem arquivo nem fonte de ícones; 24×24, viewBox do Lucide.
ICONES_KPI = {
    # velocímetro: taxa
    "incid": '<path d="M12 14l3.5-5"/><path d="M4 18a8 8 0 1 1 16 0"/>',
    # pulso: contagem de casos
    "casos": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    # linha em queda: mortalidade
    "mortalidade": '<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/>',
    # círculo cortado: interrupção
    "interrupcao_trat_pct": '<circle cx="12" cy="12" r="9"/><path d="M5.5 5.5l13 13"/>',
    # porcentagem: positividade
    "hiv_pos_pct": '<path d="M19 5L5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    # check em círculo: cura
    "cura_pct": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
}


def icone(metrica: str) -> str:
    """Miolo do SVG do ícone da métrica, ou vazio quando não há."""
    return ICONES_KPI.get(metrica, "")


def rotulo(metrica: str) -> str:
    return ROTULOS.get(metrica, metrica)


def rotulo_curto(metrica: str) -> str:
    """Nome enxuto para botão; cai no completo quando não há versão curta."""
    return ROTULOS_CURTOS.get(metrica, rotulo(metrica))


def rampa_mapa(metrica: str) -> list[str]:
    """Rampa de 7 tons para o mapa.

    Usa a paleta explícita quando a métrica tem uma; senão deriva da cor base.
    """
    explicita = PALETA_MAPA.get(metrica)
    return list(explicita) if explicita else cores.rampa(cor(metrica))


#: Rótulos que o ``sinan_dict`` não traz. Para a TB o dicionário cobre tudo
#: que a composição exibe; fica vazio, e o leitor usa o `valor_lbl` da fonte.
ROTULOS_VALORES: dict[str, dict[str, str]] = {}

#: Variáveis cujos valores são números e devem ser ordenados como tal. Na TB
#: nenhuma das expostas é numérica — `NU_COMU_EX` fica de fora justamente
#: por isso (ver `VARIAVEIS`).
VARIAVEIS_NUMERICAS: frozenset[str] = frozenset()


#: Variáveis do SINAN oferecidas no painel de composição, agrupadas.
#:
#: Só entram as que dá para rotular com segurança — errar o nome de uma
#: variável de saúde é pior que omiti-la.
#:
#: Ficam de fora, de propósito:
#: - ``NU_COMU_EX`` (contatos examinados): numérica, com centenas de valores
#:   distintos; viraria uma parede de barras.
#: - ``BACILOSC_1``..``BACILOSC_6``: baciloscopia de acompanhamento mês a mês,
#:   redundante com ``BACILOSC_E``.
#: - ``MUN_TRANSF``, ``NDUPLIC_N``: controle do sistema.
#: - ``IN_VINCULA``: rótulos ambíguos ("vinculado"/"não vinculado") sem
#:   documentação que permita explicar ao usuário o que está sendo contado.
#: - ``AGRAVDROGA`` e ``AGRAVTABAC``: o RecifeTB as expõe porque tem o
#:   microdado; a extração agregada do sinan não as traz.
#: - ``DOENCA_TRA``: em Recife parou de ser preenchida em 2015; no estado
#:   vale conferir antes de devolver.
VARIAVEIS: dict[str, dict[str, str]] = {
    "Perfil": {
        "CS_RACA": "Raça/cor",
        "CS_ESCOL_N": "Escolaridade",
        "CS_GESTANT": "Gestante",
    },
    "Populações específicas": {
        "POP_RUA": "População em situação de rua",
        "POP_LIBER": "População privada de liberdade",
        "POP_IMIG": "População imigrante",
        "POP_SAUDE": "Profissional de saúde",
        "BENEF_GOV": "Beneficiário de programa do governo",
    },
    "Agravos associados": {
        "AGRAVAIDS": "Agravo: aids",
        "AGRAVALCOO": "Agravo: alcoolismo",
        "AGRAVDIABE": "Agravo: diabetes",
        "AGRAVDOENC": "Agravo: doença mental",
        "AGRAVOUTRA": "Agravo: outro",
    },
    "Clínica e diagnóstico": {
        "FORMA": "Forma clínica",
        "HIV": "Coinfecção HIV",
        "BACILOSC_E": "Baciloscopia de escarro",
        "CULTURA_ES": "Cultura de escarro",
        "RAIOX_TORA": "Raio-X de tórax",
        "HISTOPATOL": "Histopatologia",
    },
    "Tratamento e desfecho": {
        # No SINAN o campo é o tipo de *entrada* — as categorias são "Caso
        # novo", "Pós-óbito", "Não sabe". O painel em R chama de "Tipo de
        # tratamento", que descreve mal o que está ali.
        "TRATAMENTO": "Tipo de entrada",
        "TRATSUP_AT": "Tratamento diretamente observado",
        "SITUA_ENCE": "Situação de encerramento",
        "TRANSF": "Transferência",
    },
}


#: As que abrem de saída — as do RecifeTB, menos as duas que só o microdado
#: de Recife tem. Conjunto inicial, não limite: as demais seguem no seletor.
#:
#: Ordem de leitura, não alfabética: desfecho e clínica primeiro, que é o que
#: a vigilância olha; perfil e populações específicas depois.
VARIAVEIS_DESTAQUE = (
    "SITUA_ENCE",
    "FORMA",
    "HIV",
    "TRATAMENTO",
    "CS_RACA",
    "AGRAVALCOO",
    "AGRAVAIDS",
    "POP_RUA",
    "POP_LIBER",
    "POP_SAUDE",
)


def variaveis_planas() -> dict[str, str]:
    """``código -> rótulo``, na ordem dos grupos."""
    return {c: r for grupo in VARIAVEIS.values() for c, r in grupo.items()}


def grupo_da(codigo: str) -> str:
    """Grupo a que a variável pertence, para agrupar o seletor."""
    for grupo, itens in VARIAVEIS.items():
        if codigo in itens:
            return grupo
    return "Outras"


#: Explicação de cada KPI, mostrada ao passar o cursor.
#:
#: O que se explica aqui é sobretudo o **denominador**, que é onde mora a
#: ambiguidade: "Interrupção de tratamento (%)" não diz percentual sobre o
#: quê, e a resposta muda o número em quase quatro pontos. Os textos saem das
#: fórmulas em `src/data/kpis.py` — mudou lá, muda aqui.
DESCRICOES = {
    "incid": (
        "Casos novos por 100 mil habitantes, por município de residência. "
        "Permite comparar lugares de tamanhos diferentes."
    ),
    "casos": "Total de casos novos notificados no ano, por município de residência.",
    "obitos": "Óbitos com a doença como causa básica, vindos do SIM.",
    "cura": "Encerramentos por cura no ano.",
    "cura_pct": (
        "Encerramentos por cura sobre todos os encerramentos — o denominador "
        "da Tabela 9 do Boletim de TB 2026, o mesmo do card de interrupção. "
        "Fica ~1,7 ponto acima do que o boletim publica, porque o "
        "denominador do MS inclui casos sem encerramento preenchido, que o "
        "dado agregado que recebemos não traz. "
        "É aproximação de coorte: o tratamento leva cerca de seis meses, "
        "então parte dos casos de um ano só encerra no seguinte."
    ),
    "pop": "População estimada do recorte.",
    "mortalidade": (
        "Óbitos por 100 mil habitantes. A fonte é o SIM, não o SINAN — "
        "`casos_obitos` do dataset de incidência é zero para tuberculose. "
        "O SIM fecha um ano depois do SINAN: no ano corrente o card fica vazio."
    ),
    "letalidade": "Óbitos como percentual dos casos: dos que adoeceram, quantos morreram.",
    "casos_0_14": "Casos novos em menores de 15 anos.",
    "taxa_det_0_14": "Casos de 0 a 14 anos por 100 mil habitantes dessa faixa.",
    "hiv_pos_pct": (
        "Percentual de HIV positivo entre os **testados** — o denominador é "
        "positivos mais negativos. Quem não fez o teste ou está em andamento "
        "fica de fora, então isto mede positividade, não cobertura de testagem."
    ),
    "interrupcao_trat_pct": (
        "Percentual de abandono sobre **todos os encerramentos**, incluindo os "
        "não avaliados. Reproduz a regra do painel em R. Pelo critério do "
        "Ministério da Saúde — somando abandono primário e tirando os não "
        "avaliados do denominador — o valor sobe cerca de 4 pontos. "
        "Ver docs/contrato-dados.md."
    ),
}


def descricao(metrica: str) -> str | None:
    return DESCRICOES.get(metrica)


#: Indicadores de qualidade do programa. Os dois datasets existem no sinan
#: (`indicadores_tb_contatos`, `indicadores_tb_cultura_retratamento`), mas
#: o painel é por município e eles não descem a esse nível. Ficam desligados
#: até a extração trazê-los.
INDICADORES_PROGRAMA = ()
