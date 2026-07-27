"""
constantes.py — Dashboard TB Pernambuco
═══════════════════════════════════════
Domínio (regras epidemiológicas) + UI (tema claro Cenários+).

Herda a paleta e os helpers do painel nacional (dashboard-tb-v3) e as regras de
negócio do painel municipal (dashboard-tb-recife). A novidade daqui é a
hierarquia geográfica de PE em três níveis (NIVEIS_GEO).

Sem imports de streamlit/pandas — importável em milissegundos.
"""

from pathlib import Path

# ── Caminhos ──────────────────────────────────────────────────────────────────
RAIZ = Path(__file__).resolve().parents[1]
PASTA_DADOS = RAIZ / "dados_dashboard"

PARQUET = PASTA_DADOS / "pe_tb_sinan.parquet"
POP_PARQUET = PASTA_DADOS / "pop_pe.parquet"
MUNICIPIOS_PARQUET = PASTA_DADOS / "municipios_pe.parquet"

GEOJSON = {
    "municipio": PASTA_DADOS / "municipios_pe.geojson",
    "regiao_saude": PASTA_DADOS / "regioes_saude_pe.geojson",
    "macro_saude": PASTA_DADOS / "macro_saude_pe.geojson",
}

ANO_INICIO, ANO_FIM = 2001, 2025
UF = "PE"
UF_NOME = "Pernambuco"

# ══════════════════════════════════════════════════════════════════════════════
#  Hierarquia geográfica de PE — os três níveis do mapa
# ══════════════════════════════════════════════════════════════════════════════
# Fonte: shapefiles da Secretaria Estadual de Saúde de PE, que já trazem
# NomeRegSau/NomeMacro por município (sem necessidade de join espacial).
#
#   coluna     → coluna do parquet que identifica a unidade
#   id_geo     → propriedade `id` do GeoJSON correspondente
#   rotulo     → nome exibido no botão
NIVEIS_GEO: dict[str, dict] = {
    "municipio": {
        "rotulo": "Município",
        "icone": "🏘️",
        "coluna": "codigo_ibge",
        "nome": "municipio",
        "plural": "municípios",
        "n": 185,
    },
    "regiao_saude": {
        "rotulo": "Região de Saúde",
        "icone": "🏥",
        "coluna": "regiao_saude",
        "nome": "regiao_saude",
        "plural": "regiões de saúde",
        "n": 12,
    },
    "macro_saude": {
        "rotulo": "Macrorregião",
        "icone": "🗺️",
        "coluna": "macro_saude",
        "nome": "macro_saude",
        "plural": "macrorregiões de saúde",
        "n": 4,
    },
}

NIVEL_PADRAO = "municipio"

# ══════════════════════════════════════════════════════════════════════════════
#  Regras epidemiológicas (idênticas ao Recife e ao painel nacional)
# ══════════════════════════════════════════════════════════════════════════════

# Incidência: só casos novos. Caderno de Indicadores do MS.
TIPOS_INCIDENCIA = ("Caso Novo", "Não Sabe", "Pós-óbito")

# Retratamento — dinâmica e taxa de cura distintas, nunca somado aos novos.
TIPOS_RETRATAMENTO = ("Recidiva", "Reingresso após Abandono")

# Coorte: o denominador exclui quem ainda não tem desfecho conhecido.
DESFECHOS_NAO_ENCERRADOS = ("Transferência", "Não informado")

# Abandono = abandono + abandono primário (o SINAN separa os dois códigos).
DESFECHOS_ABANDONO = ("Abandono", "Abandono Primário")

META_ABANDONO_OMS = 5.0   # %  — acima disso há risco de TB resistente
META_CURA_OMS = 85.0      # %

# Coinfecção HIV: denominador = testados, não o total de casos.
HIV_TESTADO = ("Positivo", "Negativo")

# Rótulos que representam ausência de informação (unificados na exibição)
ROTULOS_VAZIOS = ("Não informado", "Nao informado", "Ignorado", "", None)

AGRAVOS = {
    "agravo_aids": "AIDS/HIV",
    "agravo_alcoolismo": "Alcoolismo",
    "agravo_diabetes": "Diabetes",
    "agravo_doenca_mental": "Doença Mental",
    "agravo_drogas_ilicitas": "Drogas Ilícitas",
    "agravo_tabagismo": "Tabagismo",
}

POPULACOES = {
    "populacao_privada_liberdade": "Privada de Liberdade",
    "populacao_situacao_rua": "Situação de Rua",
    "populacao_imigrante": "Imigrante",
    "profissional_saude": "Profissional de Saúde",
    "beneficiario_governo": "Beneficiário Prog. Social",
}

DESFECHO_GRUPO = {
    "Cura": "Cura",
    "Abandono": "Interrupção",
    "Abandono Primário": "Interrupção",
    "Óbito por TB": "Óbito",
    "Óbito por outras causas": "Óbito",
    "Transferência": "Não avaliado",
    "Mudança de Esquema": "Não avaliado",
    "TB-DR": "Não avaliado",
    "Falência": "Não avaliado",
    "Não informado": "Não avaliado",
}

FAIXAS_ETARIAS = (
    "0-4", "5-9", "10-14", "15-19", "20-29", "30-39",
    "40-49", "50-59", "60-69", "70-79", "80+",
)

# ══════════════════════════════════════════════════════════════════════════════
#  UI — tema claro Cenários+
# ══════════════════════════════════════════════════════════════════════════════
COR_PRIMARIA = "#2B7BB9"
COR_DESTAQUE = "#E07B54"
COR_CURA = "#2ea043"
COR_OBITO = "#da3633"
COR_ABANDONO = "#d29922"
COR_HIV = "#8250df"
COR_MASC = "#2B7BB9"
COR_FEM = "#d6409f"
COR_NEUTRO = "#8b949e"

TB_COLORS = {
    "Cura": COR_CURA,
    "Óbito por TB": COR_OBITO,
    "Óbito por outras causas": "#8957e5",
    "Abandono": COR_ABANDONO,
    "Abandono Primário": "#bb8009",
    "Falência": "#f85149",
    "TB-DR": "#cf222e",
    "Transferência": "#1f6feb",
    "Mudança de Esquema": "#e8871e",
    "Em acompanhamento": "#388bfd",
    "Interrupção": COR_ABANDONO,
    "Óbito": COR_OBITO,
    "Não avaliado": COR_NEUTRO,
    # Testes / status
    "Positivo": COR_OBITO, "Negativo": COR_CURA,
    "Positiva": COR_OBITO, "Negativa": COR_CURA,
    "Em andamento": COR_ABANDONO,
    "Não realizado": COR_HIV, "Não realizada": COR_HIV,
    "Não se aplica": "#54aeff",
    "Detectável sensível à Rifampicina": COR_ABANDONO,
    "Detectável resistente à Rifampicina": COR_OBITO,
    "Não detectável": COR_CURA,
    "Inconclusivo": "#bf91f3",
    # Sexo
    "Masculino": COR_MASC, "Feminino": COR_FEM,
    # Sim/não
    "Sim": COR_OBITO, "Não": COR_CURA,
    "Ignorado": COR_NEUTRO, "Não informado": "#afb8c1",
    # Raça/cor
    "Branca": "#54aeff", "Preta": COR_HIV, "Parda": "#bf91f3",
    "Amarela": "#d4a72c", "Indígena": COR_CURA, "Indigena": COR_CURA,
    # Forma clínica
    "Pulmonar": COR_MASC, "Extrapulmonar": COR_HIV,
    "Pulmonar + Extrapulmonar": "#bf91f3",
    # Tipo de entrada
    "Caso Novo": COR_CURA, "Recidiva": COR_ABANDONO,
    "Reingresso após Abandono": "#e8871e", "Não Sabe": COR_NEUTRO,
    "Pós-óbito": "#a40e26",
    # Macrorregiões de saúde de PE
    "Metropolitana": COR_PRIMARIA, "Agreste": "#2ea043",
    "Sertao Pernambucano": "#e8871e", "Vale S.Francisco/Araripe": COR_HIV,
}

CORES = ["#2B7BB9", "#8250df", "#2ea043", "#d29922", "#d6409f",
         "#54aeff", "#bf91f3", "#e8871e"]


def tb_color_map(labels) -> dict:
    """Mapeia rótulos para as cores semânticas de TB (fallback determinístico)."""
    mapa, idx = {}, 0
    for lbl in labels:
        if lbl in TB_COLORS:
            mapa[lbl] = TB_COLORS[lbl]
        else:
            mapa[lbl] = CORES[idx % len(CORES)]
            idx += 1
    return mapa


# Escalas sequenciais dos mapas
SEQ_CASOS = ["#eaf4fc", "#a5d6ff", "#58a6ff", "#2B7BB9", "#1a4a80", "#12325c"]
SEQ_INCIDENCIA = ["#fff7ec", "#fdd49e", "#fc8d59", "#e34a33", "#b30000", "#7f0000"]
SEQ_ABANDONO = ["#fffbea", "#ffe8a3", "#ffc93c", "#d29922", "#9a6d00", "#6b4b00"]
SEQ_CURA = ["#f0fff4", "#b7f5c5", "#5fd67f", "#2ea043", "#1a7f37", "#0f5323"]

H_SMALL, H_MEDIUM, H_LARGE = 300, 380, 480

PLOTLY_CFG = {"scrollZoom": False, "displayModeBar": False}

GRAFICO_BASE = dict(
    font=dict(family="Inter, -apple-system, system-ui, sans-serif",
              color="#24292f", size=12),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(gridcolor="#eef1f5", linecolor="#d0d7de",
               tickfont=dict(color="#57606a", size=11)),
    yaxis=dict(gridcolor="#eef1f5", linecolor="#d0d7de",
               tickfont=dict(color="#57606a", size=11)),
    legend=dict(bgcolor="rgba(255,255,255,.95)", bordercolor="#d0d7de",
                borderwidth=1, font=dict(color="#24292f", size=11)),
    hoverlabel=dict(bgcolor="rgba(255,255,255,.98)", bordercolor="#d0d7de",
                    font=dict(color="#24292f", size=12.5, family="Inter, sans-serif")),
    margin=dict(l=10, r=10, t=10, b=10),
)


# ── Helpers de formatação (pt-BR) ─────────────────────────────────────────────
def _finito(v, padrao=0):
    """None/NaN/infinito → padrão.

    `v or padrao` não serve: NaN é verdadeiro em Python, então passa direto e
    estoura no `int()`. Como estes formatadores são usados em todo KPI e rótulo,
    um NaN vindo de uma agregação vazia derrubaria a página inteira.
    """
    if v is None:
        return padrao
    try:
        if v != v or v in (float("inf"), float("-inf")):
            return padrao
    except TypeError:
        return padrao
    return v


def fmt_int(v) -> str:
    return f"{int(round(_finito(v))):,}".replace(",", ".")


def fmt_dec(v, casas: int = 1) -> str:
    return f"{_finito(v):.{casas}f}".replace(".", ",")


def pct(valor, total) -> str:
    return f"{valor / total * 100:.1f}%".replace(".", ",") if total else "—"
