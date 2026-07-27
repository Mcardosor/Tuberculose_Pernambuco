"""
styles.py — CSS global e helpers de HTML (navbar, hero, KPI cards, footer)
══════════════════════════════════════════════════════════════════════════
Mesma identidade visual dos outros painéis Cenários+ (nacional, Recife,
hanseníase): light mode por padrão, dark mode via botão flutuante que injeta
um <style> no frame pai e persiste a escolha no localStorage.

As regras de Folium do painel de Recife foram removidas — aqui todo mapa é
Plotly, então o que precisa de tratamento no dark mode são os SVGs do Plotly.
"""

import streamlit as st
import streamlit.components.v1 as components

_CSS = """
<style>
  [data-testid="stAppViewContainer"] { background-color: #f6f8fa; }
  [data-testid="stSidebar"]          { background-color: #ffffff; }
  [data-testid="stSidebar"] *        { color: #24292f !important; }

  .stDeployButton { display: none !important; }

  [data-testid="stButton"] button[kind="primary"] {
    background-color: #2B7BB9 !important; border-color: #2B7BB9 !important; color: #fff !important;
  }
  [data-testid="stButton"] button[kind="primary"]:hover {
    background-color: #1a5c8a !important; border-color: #1a5c8a !important;
  }

  [data-testid="stPills"] button {
    background-color: transparent !important; border: 1px solid #d0d7de !important;
    color: #24292f !important; border-radius: 999px !important;
    font-size: 12px !important; font-weight: 500 !important;
    transition: background .15s, border-color .15s, color .15s !important;
  }
  [data-testid="stPills"] button:hover {
    background-color: rgba(43,123,185,.06) !important;
    border-color: rgba(43,123,185,.35) !important; color: #1a3a5c !important;
  }
  [data-testid="stPills"] button[aria-checked="true"] {
    background-color: rgba(43,123,185,.12) !important;
    border-color: rgba(43,123,185,.35) !important;
    color: #1a3a5c !important; font-weight: 600 !important;
  }

  /* ── Navegação principal: o segmented control vira barra de seções ───────── */
  [data-testid="stSegmentedControl"] > div {
    gap: 4px !important; background: rgba(0,0,0,.02); padding: 6px;
    border-radius: 12px; border: 1px solid #d0d7de;
    display: flex !important; flex-wrap: wrap !important;
  }
  [data-testid="stSegmentedControl"] button {
    background: transparent !important; border: 1px solid transparent !important;
    border-radius: 8px !important; color: #57606a !important;
    font-size: 13px !important; font-weight: 600 !important;
    padding: 9px 16px !important; flex: 1 1 auto !important;
    justify-content: center !important;
    transition: background .15s, border-color .15s, color .15s, transform .1s !important;
  }
  [data-testid="stSegmentedControl"] button:hover {
    background: rgba(0,0,0,.04) !important; border-color: #d0d7de !important;
    color: #24292f !important; transform: translateY(-1px);
  }
  [data-testid="stSegmentedControl"] button[aria-checked="true"] {
    background: rgba(224,123,84,.12) !important;
    border-color: rgba(224,123,84,.32) !important;
    color: #1a3a5c !important; font-weight: 700 !important;
    box-shadow: 0 2px 8px rgba(224,123,84,.12) !important;
  }

  [data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background-color: rgba(43,123,185,.12) !important;
    border: 1px solid rgba(43,123,185,.35) !important;
    color: #1a3a5c !important; border-radius: 999px !important;
    font-size: 12px !important; font-weight: 600 !important;
  }
  [data-testid="stMultiSelect"] span[data-baseweb="tag"] span,
  [data-testid="stMultiSelect"] span[data-baseweb="tag"] button { color: #1a3a5c !important; }

  h1, h2, h3                { color: #1a3a5c; }
  p, span, label            { color: #24292f; }
  [data-testid="stCaption"] { color: #57606a; }
  hr                        { border-color: #d0d7de; }

  /* ── KPI Cards ───────────────────────────────────────────────────────────── */
  .kpi-card {
    --accent: #2B7BB9;
    border-radius: 14px; border: 1px solid #d0d7de;
    background: linear-gradient(160deg, #ffffff 0%, #f6f8fa 100%);
    box-shadow: 0 2px 8px rgba(0,0,0,.08); overflow: hidden; position: relative;
    transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
    margin-bottom: 4px;
  }
  .kpi-card:hover {
    border-color: #2B7BB9; box-shadow: 0 8px 24px rgba(43,123,185,.15);
    transform: translateY(-2px);
  }
  .kpi-inner {
    display: flex; align-items: center; gap: 10px; padding: 12px 13px;
    position: relative; z-index: 1; min-width: 0;
  }
  .kpi-bar   { width: 4px; height: 44px; border-radius: 999px; background: var(--accent); flex: 0 0 auto; }
  .kpi-body  { flex: 1 1 auto; min-width: 0; }
  /* min-width:0 em toda a cadeia flex é o que impede o texto de quebrar
     letra por letra quando 5 cards dividem uma tela estreita */
  .kpi-label {
    font-size: 10px; font-weight: 700; color: #57606a; text-transform: uppercase;
    letter-spacing: .5px; margin-bottom: 2px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .kpi-value {
    /* acompanha a largura disponível em vez de estourar o card */
    font-size: clamp(17px, 1.55vw, 23px);
    font-weight: 900; color: #1a3a5c; letter-spacing: -.5px; line-height: 1.1;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .kpi-sub {
    display: block; font-size: 10.5px; font-weight: 600; color: #57606a;
    margin-top: 3px; line-height: 1.3;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .kpi-sub.alert { color: #cf222e; }
  .kpi-icon {
    width: 32px; height: 32px; border-radius: 999px; background: rgba(0,0,0,.03);
    border: 1px solid #d0d7de; display: flex; align-items: center;
    justify-content: center; flex: 0 0 auto; font-size: 14px;
  }
  /* abaixo de ~1150px o ícone é a primeira coisa a sair — o número importa mais */
  @media (max-width: 1150px) { .kpi-icon { display: none; } }

  /* ── Hero ────────────────────────────────────────────────────────────────── */
  /* Compacto de propósito: hero + KPIs + navegação precisam caber acima da
     dobra para o mapa começar visível numa tela de 900px. */
  .hero {
    position: relative; padding: 18px 26px 16px; margin: -10px 0 14px;
    border-radius: 16px;
    background: linear-gradient(135deg, #ffffff 0%, #eaf2fb 60%, #d4e8f6 100%);
    border: 1px solid #d0d7de; box-shadow: 0 2px 8px rgba(0,0,0,.08); overflow: hidden;
  }
  .hero::before {
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #E07B54 0%, #2B7BB9 50%, #1a7f37 100%);
  }
  .hero-title {
    font-size: 26px; font-weight: 900; color: #1a3a5c; letter-spacing: -.7px;
    line-height: 1.15; margin: 0 0 4px; display: flex; align-items: center; gap: 10px;
  }
  .hero-emoji { font-size: 28px; filter: drop-shadow(0 2px 8px rgba(43,123,185,.25)); }
  .hero-subtitle {
    font-size: 13px; color: #57606a; margin: 0 0 11px;
    font-weight: 500; max-width: 820px; line-height: 1.45;
  }
  .hero-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
  .hero-badge {
    display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px;
    border-radius: 999px; font-size: 11px; font-weight: 700; letter-spacing: .3px;
    background: rgba(0,0,0,.04); border: 1px solid #d0d7de; color: #24292f;
    text-transform: uppercase;
  }
  .hero-badge.accent  { background: rgba(43,123,185,.08); border-color: rgba(43,123,185,.3); color: #2B7BB9; }
  .hero-badge.success { background: rgba(26,127,55,.08);  border-color: rgba(26,127,55,.3);  color: #1a7f37; }
  .hero-badge.warn    { background: rgba(248,81,73,.10);  border-color: rgba(248,81,73,.35); color: #c93026; }
  .hero-badge .dot    { width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: .8; }

  /* ── Navbar Cenários+ ────────────────────────────────────────────────────── */
  .cenarios-bar {
    background: #2B7BB9; padding: 8px 24px; margin: .5rem -1rem 1.5rem;
    display: flex; align-items: center; gap: 8px;
  }
  .cenarios-bar-logo  { font-size: 1.1rem; font-weight: 800; color: #fff; letter-spacing: -.3px; }
  .cenarios-bar-logo span { color: #E07B54; }
  .cenarios-bar-sep   { color: rgba(255,255,255,.4); margin: 0 6px; }
  .cenarios-bar-title { font-size: .85rem; font-weight: 500; color: rgba(255,255,255,.85); }

  /* ── Layout ──────────────────────────────────────────────────────────────── */
  .block-container { padding-top: 1.2rem !important; padding-bottom: 3rem !important; max-width: 1400px; }
  hr, [data-testid="stDivider"] {
    margin: 1.4rem 0 1.1rem !important; border: none !important; height: 1px !important;
    background: linear-gradient(90deg, transparent, #d0d7de 20%, #d0d7de 80%, transparent) !important;
  }
  h2 { font-size: 20px !important; font-weight: 700 !important; color: #1a3a5c !important;
       margin: .25rem 0 1rem !important; padding-bottom: .5rem !important; letter-spacing: -.3px !important; }
  /* Títulos de gráfico com barrinha de acento à esquerda — dá hierarquia
     visual sem precisar de mais um nível de caixa. */
  h3 {
    font-size: 15px !important; font-weight: 700 !important; color: #1a3a5c !important;
    margin: .4rem 0 .1rem !important; letter-spacing: -.2px !important;
    padding-left: 10px !important; position: relative !important;
  }
  h3::before {
    content: ""; position: absolute; left: 0; top: .18em; bottom: .18em;
    width: 3px; border-radius: 999px; background: #E07B54; opacity: .75;
  }
  /* legenda logo abaixo do título cola no título, não flutua no meio */
  h3 + [data-testid="stCaptionContainer"] { margin: 0 0 .5rem 10px !important; }

  /* ── Tabs ────────────────────────────────────────────────────────────────── */
  .stTabs { margin-top: 1rem; }
  .stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: rgba(0,0,0,.02); padding: 6px;
    border-radius: 12px; border: 1px solid #d0d7de; flex-wrap: wrap !important;
  }
  .stTabs [data-baseweb="tab"] {
    padding: 8px 14px !important; border-radius: 8px !important;
    font-weight: 600 !important; font-size: 13px !important; color: #57606a;
    white-space: nowrap; flex: 1 1 auto !important; text-align: center !important;
    border: 1px solid transparent !important;
    transition: background .15s, border-color .15s, color .15s, transform .1s !important;
  }
  .stTabs [data-baseweb="tab"]:hover {
    background: rgba(0,0,0,.04) !important; border-color: #d0d7de !important;
    color: #24292f !important; transform: translateY(-1px);
  }
  .stTabs [aria-selected="true"] {
    background: rgba(224,123,84,.1) !important; border-color: rgba(224,123,84,.3) !important;
    color: #1a3a5c !important; box-shadow: 0 2px 8px rgba(224,123,84,.1) !important;
  }
  .stTabs [data-baseweb="tab-panel"] { padding-top: 1.25rem; }

  [data-testid="stExpander"] {
    border: 1px solid #d0d7de !important; border-radius: 12px !important;
    background: #fff !important; margin-top: 1rem;
  }
  [data-testid="stSidebar"] [data-testid="stExpander"] {
    background: transparent !important; border: 1px solid #d0d7de !important; margin-bottom: .5rem;
  }

  /* ── Superset embutido na Análise Livre ──────────────────────────────────── */
  .superset-frame {
    border-radius: 12px; border: 1px solid #d0d7de; overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
  }

  /* ── Responsividade ──────────────────────────────────────────────────────── */
  @media (max-width: 768px) {
    .hero          { padding: 18px 16px 16px !important; }
    .hero-title    { font-size: 20px !important; }
    .hero-emoji    { font-size: 24px !important; }
    .hero-subtitle { font-size: 12px; margin-bottom: 10px; }
    .hero-badge    { font-size: 10px !important; padding: 3px 8px !important; }
    [data-testid="column"] { min-width: calc(50% - .5rem) !important; flex: 0 0 calc(50% - .5rem) !important; }
    .kpi-value { font-size: 18px !important; }
    .stTabs [data-baseweb="tab"] { font-size: 11px !important; padding: 6px 8px !important; }
    .block-container { padding-left: .5rem !important; padding-right: .5rem !important; }
  }
  @media (max-width: 480px) {
    [data-testid="column"] { min-width: 100% !important; flex: 0 0 100% !important; }
    .hero-title { font-size: 17px !important; }
  }
</style>
"""

_DARK_CSS = """
  [data-theme="dark"] [data-testid="stAppViewContainer"] { background-color: #0d1117 !important; }
  [data-theme="dark"] [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d !important; }
  [data-theme="dark"] [data-testid="stSidebar"] * { color: #e6edf3 !important; }
  [data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3 { color: #79c0ff !important; }
  [data-theme="dark"] p, [data-theme="dark"] span, [data-theme="dark"] label { color: #e6edf3 !important; }
  [data-theme="dark"] [data-testid="stCaption"] { color: #8b949e !important; }
  [data-theme="dark"] hr, [data-theme="dark"] [data-testid="stDivider"] { background: linear-gradient(90deg, transparent, #30363d, transparent) !important; }
  [data-theme="dark"] .kpi-card { background: linear-gradient(160deg, #1c2128 0%, #161b22 100%) !important; border-color: #30363d !important; box-shadow: 0 2px 8px rgba(0,0,0,.4) !important; }
  [data-theme="dark"] .kpi-label { color: #8b949e !important; }
  [data-theme="dark"] .kpi-value { color: #79c0ff !important; }
  [data-theme="dark"] .kpi-sub   { color: #8b949e !important; }
  [data-theme="dark"] .kpi-icon  { background: rgba(255,255,255,.04) !important; border-color: #30363d !important; }
  [data-theme="dark"] .hero { background: linear-gradient(135deg, #161b22 0%, #1c2128 60%, #1c2840 100%) !important; border-color: #30363d !important; }
  [data-theme="dark"] .hero-title { color: #e6edf3 !important; }
  [data-theme="dark"] .hero-subtitle { color: #8b949e !important; }
  [data-theme="dark"] .hero-badge { background: rgba(255,255,255,.04) !important; border-color: #30363d !important; color: #8b949e !important; }
  [data-theme="dark"] .hero-badge.accent { color: #58a6ff !important; }
  [data-theme="dark"] .hero-badge.success { color: #3fb950 !important; }
  [data-theme="dark"] .stTabs [data-baseweb="tab-list"] { background: rgba(255,255,255,.03) !important; border-color: #30363d !important; }
  [data-theme="dark"] .stTabs [data-baseweb="tab"] { color: #8b949e !important; }
  [data-theme="dark"] .stTabs [data-baseweb="tab"]:hover { background: rgba(255,255,255,.06) !important; border-color: #30363d !important; color: #e6edf3 !important; }
  [data-theme="dark"] .stTabs [aria-selected="true"] { background: rgba(224,123,84,.12) !important; border-color: rgba(224,123,84,.3) !important; color: #e6edf3 !important; }
  [data-theme="dark"] [data-testid="stExpander"] { background: #161b22 !important; border-color: #30363d !important; }
  [data-theme="dark"] [data-testid="stButton"] button { background-color: #21262d !important; border-color: #30363d !important; color: #e6edf3 !important; }
  [data-theme="dark"] [data-testid="stButton"] button[kind="primary"] { background-color: #2B7BB9 !important; border-color: #2B7BB9 !important; color: #fff !important; }
  [data-theme="dark"] [data-testid="stDownloadButton"] button { background-color: #21262d !important; border-color: #30363d !important; color: #e6edf3 !important; }
  [data-theme="dark"] [data-baseweb="select"] > div:first-child, [data-theme="dark"] [data-baseweb="input"] > div { background-color: #21262d !important; border-color: #30363d !important; }
  [data-theme="dark"] [data-baseweb="select"] input, [data-theme="dark"] [data-baseweb="input"] input { color: #e6edf3 !important; background-color: transparent !important; }
  [data-theme="dark"] [data-baseweb="menu"] { background-color: #21262d !important; border-color: #30363d !important; }
  [data-theme="dark"] [data-baseweb="menu"] li { color: #e6edf3 !important; }
  [data-theme="dark"] [data-baseweb="menu"] li:hover { background-color: #30363d !important; }
  [data-theme="dark"] .superset-frame { border-color: #30363d !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .legend .bg { fill: #161b22 !important; stroke: #30363d !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .legend text { fill: #e6edf3 !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .xtick text, [data-theme="dark"] .js-plotly-plot .plotly .ytick text { fill: #8b949e !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .gridlayer path { stroke: #21262d !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .zerolinelayer path { stroke: #30363d !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .annotation-text { fill: #e6edf3 !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .hoverlayer .hovertext rect { fill: #21262d !important; stroke: #30363d !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .hoverlayer .hovertext path { fill: #21262d !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .hoverlayer .hovertext text { fill: #e6edf3 !important; }
  [data-theme="dark"] #_tb_theme_btn { background: rgba(22,27,34,.9) !important; border-color: #30363d !important; color: #e6edf3 !important; }
"""

# O botão vive no frame pai (fora do iframe do componente), por isso o JS.
_THEME_TOGGLE_JS = """
<script>
(function() {
  var KEY = 'tb_pe_dash_theme';
  var p = window.parent;

  function applyTheme(t) {
    p.document.documentElement.setAttribute('data-theme', t);
    p.localStorage.setItem(KEY, t);
    var btn = p.document.getElementById('_tb_theme_btn');
    if (btn) {
      btn.innerHTML = t === 'dark' ? '☀️' : '🌙';
      btn.title = t === 'dark' ? 'Modo claro' : 'Modo escuro';
    }
  }

  function toggle() {
    var cur = p.document.documentElement.getAttribute('data-theme') || 'light';
    applyTheme(cur === 'dark' ? 'light' : 'dark');
  }

  function ensureStyle() {
    if (p.document.getElementById('_tb_dark_css')) return;
    var s = p.document.createElement('style');
    s.id = '_tb_dark_css';
    s.textContent = DARK_CSS_PLACEHOLDER;
    p.document.head.appendChild(s);
  }

  function ensureButton() {
    if (p.document.getElementById('_tb_theme_btn')) return;
    var btn = p.document.createElement('button');
    btn.id = '_tb_theme_btn';
    btn.onclick = toggle;
    var saved = p.localStorage.getItem(KEY) || 'light';
    btn.innerHTML = saved === 'dark' ? '☀️' : '🌙';
    btn.title = saved === 'dark' ? 'Modo claro' : 'Modo escuro';
    btn.style.cssText = [
      'position:fixed','top:8px','z-index:9999999',
      'width:32px','height:32px','border-radius:8px',
      'border:1px solid rgba(0,0,0,.15)','background:rgba(255,255,255,.92)',
      'backdrop-filter:blur(8px)','cursor:pointer',
      'font-size:18px','line-height:1','padding:0',
      'box-shadow:0 1px 4px rgba(0,0,0,.15)',
      'transition:transform .12s,background .2s',
      'display:flex','align-items:center','justify-content:center'
    ].join(';');
    function _pos() {
      var vw = p.document.documentElement.clientWidth || p.innerWidth;
      btn.style.left = Math.max(0, vw - 122) + 'px';
    }
    _pos();
    p.addEventListener('resize', _pos);
    btn.onmouseover = function() { btn.style.transform = 'scale(1.1)'; };
    btn.onmouseout  = function() { btn.style.transform = 'scale(1)'; };
    p.document.body.appendChild(btn);
  }

  function init() {
    ensureStyle();
    applyTheme(p.localStorage.getItem(KEY) || 'light');
    ensureButton();
  }

  if (p.document.readyState === 'complete') { init(); }
  else { p.addEventListener('load', init); }

  new p.MutationObserver(ensureButton).observe(p.document.body, { childList: true });
})();
</script>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    dark = _DARK_CSS.replace("\n", " ").replace("'", "\\'").replace('"', '\\"')
    components.html(_THEME_TOGGLE_JS.replace("DARK_CSS_PLACEHOLDER", f"'{dark}'"),
                    height=1, scrolling=False)


def navbar(titulo: str = "Dashboard TB | Pernambuco") -> None:
    st.markdown(
        f"""
        <div class="cenarios-bar">
          <span class="cenarios-bar-logo">Cenários<span>+</span></span>
          <span class="cenarios-bar-sep">|</span>
          <span class="cenarios-bar-title">{titulo}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hero(titulo: str, subtitulo: str, badges: list[tuple[str, str]],
         emoji: str = "🩺") -> None:
    """badges = [(texto, classe)] onde classe ∈ {'', 'accent', 'success', 'warn'}."""
    chips = "".join(
        f'<span class="hero-badge {cls}"><span class="dot"></span>{txt}</span>'
        for txt, cls in badges
    )
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-title"><span class="hero-emoji">{emoji}</span>{titulo}</div>
          <div class="hero-subtitle">{subtitulo}</div>
          <div class="hero-badges">{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _kpi_html(label, value, sub, icon, accent, alert=False) -> str:
    cls = "kpi-sub alert" if alert else "kpi-sub"
    sub_html = f'<span class="{cls}">{sub}</span>' if sub else ""
    return (
        f'<div class="kpi-card" style="--accent:{accent};"><div class="kpi-inner">'
        f'<div class="kpi-bar"></div><div class="kpi-body">'
        f'<div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>{sub_html}'
        f'</div><div class="kpi-icon">{icon}</div></div></div>'
    )


def kpi_row(cards: list[dict]) -> None:
    """Cada card: {label, value, sub?, icon, accent?, alert?}."""
    for col, c in zip(st.columns(len(cards)), cards):
        col.markdown(
            _kpi_html(c["label"], c["value"], c.get("sub", ""), c["icon"],
                      c.get("accent", "#2B7BB9"), c.get("alert", False)),
            unsafe_allow_html=True,
        )


def footer() -> None:
    st.markdown(
        """
        <div style="background:#2B7BB9;color:rgba(255,255,255,.85);
                    padding:18px 32px;margin:3rem -1rem -3rem;
                    font-size:.85rem;font-weight:500;
                    display:flex;align-items:center;gap:6px;">
          <strong style="color:#fff;font-weight:800;">Cenários<span style="color:#E07B54;">+</span></strong>
          &mdash; Fonte: SINAN NET · Ministério da Saúde. Hierarquia geográfica:
          Secretaria Estadual de Saúde de Pernambuco.
        </div>
        """,
        unsafe_allow_html=True,
    )
