"""
preparar_dados.py — monta a base do Dashboard TB Pernambuco
═══════════════════════════════════════════════════════════
Entrada:
  - Parquets do SINAN nacional (dashboard-tb-v3/dados_dashboard/tuberculose_*_tratado.parquet)
  - Shapefiles da SES-PE em GeoJSON (Pernanbuco/shapefiles/*.geojson)

Saída (dados_dashboard/):
  - pe_tb_sinan.parquet     SINAN com residência em PE + município/região/macro de saúde
  - municipios_pe.parquet   hierarquia município → região → macrorregião (denominadores)
  - municipios_pe.geojson   185 municípios, id = código IBGE
  - regioes_saude_pe.geojson    12 regiões de saúde, id = nome
  - macro_saude_pe.geojson       4 macrorregiões de saúde, id = nome

Recorte por RESIDÊNCIA (uf_residencia), não por notificação — regra do boletim
epidemiológico oficial do estado, igual ao dashboard-tb-recife.

Rodar:  python etl/preparar_dados.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "dados_dashboard"

CENARIOS = RAIZ.parent
SINAN_GLOB = str(CENARIOS / "dashboard-tb-v3" / "dados_dashboard" / "tuberculose_*_tratado.parquet")
GEO_DIR = CENARIOS / "Pernanbuco" / "shapefiles"

GEO_MUNICIPIOS = GEO_DIR / "PE MODIF.geojson"
GEO_REGIOES = GEO_DIR / "PERGSAUDE MODIF.geojson"
GEO_MACRO = GEO_DIR / "PEMacSAUD MODIF.geojson"

# Três municípios têm grafia diferente entre o SINAN e o shapefile da SES-PE.
# Com estes aliases o match é 100% (185/185). Documentado em dashboard-tb-pe.
ALIASES = {
    "LAGOA DE ITAENGA": "LAGOA DO ITAENGA",
    "BELEM DO SAO FRANCISCO": "BELEM DE SAO FRANCISCO",
    "IGUARACY": "IGUARACI",
}


def _area_assinada(anel: list) -> float:
    """Área com sinal (shoelace). Positiva = anti-horário."""
    total = 0.0
    for i in range(len(anel) - 1):
        x1, y1 = anel[i][0], anel[i][1]
        x2, y2 = anel[i + 1][0], anel[i + 1][1]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def rebobina(geometria: dict) -> dict:
    """Padroniza a ordem de enrolamento dos anéis para o que o Plotly espera.

    O d3-geo — motor dos mapas do Plotly — trata polígonos como ESFÉRICOS e usa
    a convenção CONTRÁRIA à do RFC 7946: o anel externo tem de ser **horário**.
    Com um anel anti-horário ele entende o complemento da área — o polígono vira
    "o globo inteiro menos este município" e pinta o mapa todo de uma cor só.

    Os geojsons da SES-PE vêm com enrolamento misto, então aqui todos os anéis
    externos são forçados a horário e os buracos a anti-horário.

    Verificado empiricamente no navegador: com anéis anti-horários, 170 dos 185
    municípios renderizavam como um retângulo cobrindo o mapa inteiro; invertidos,
    os 185 desenham corretamente.
    """
    def _corrige_poligono(aneis: list) -> list:
        corrigidos = []
        for i, anel in enumerate(aneis):
            anti_horario = _area_assinada(anel) > 0
            externo = i == 0
            # externo quer horário; buraco quer anti-horário
            if (externo and anti_horario) or (not externo and not anti_horario):
                anel = list(reversed(anel))
            corrigidos.append(anel)
        return corrigidos

    tipo = geometria["type"]
    coords = geometria["coordinates"]
    if tipo == "Polygon":
        return {"type": tipo, "coordinates": _corrige_poligono(coords)}
    if tipo == "MultiPolygon":
        return {"type": tipo, "coordinates": [_corrige_poligono(p) for p in coords]}
    return geometria


def normaliza(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s.upper().strip())
    return ALIASES.get(s, s)


def carrega_hierarquia() -> list[dict]:
    """Município → região de saúde → macrorregião, direto dos atributos do shapefile.

    Não precisa de join espacial: o shapefile já traz NomeRegSau/NomeMacro por município.
    """
    gj = json.loads(GEO_MUNICIPIOS.read_text(encoding="utf-8"))
    return [
        {
            "municipio_norm": normaliza(f["properties"]["Name"]),
            "municipio": f["properties"]["Name"],
            "codigo_ibge": int(f["properties"]["City"]),
            "regiao_saude": f["properties"]["NomeRegSau"],
            "macro_saude": f["properties"]["NomeMacro"],
        }
        for f in gj["features"]
    ]


def escreve_geojson_municipios(hierarquia: list[dict]) -> None:
    """GeoJSON dos municípios com `id` = código IBGE (featureidkey do Plotly)."""
    gj = json.loads(GEO_MUNICIPIOS.read_text(encoding="utf-8"))
    feats = []
    for f in gj["features"]:
        p = f["properties"]
        feats.append({
            "type": "Feature",
            "id": str(int(p["City"])),
            "properties": {
                "codigo_ibge": int(p["City"]),
                "municipio": p["Name"],
                "regiao_saude": p["NomeRegSau"],
                "macro_saude": p["NomeMacro"],
            },
            "geometry": rebobina(f["geometry"]),
        })
    _dump(SAIDA / "municipios_pe.geojson", feats)
    print(f"  municipios_pe.geojson       {len(feats):>4} feições")


def escreve_geojson_nivel(origem: Path, chave: str, campo: str, arquivo: str) -> None:
    """GeoJSON de região/macrorregião — polígonos já dissolvidos no shapefile."""
    gj = json.loads(origem.read_text(encoding="utf-8"))
    feats = [
        {
            "type": "Feature",
            "id": f["properties"][chave],
            "properties": {campo: f["properties"][chave]},
            "geometry": rebobina(f["geometry"]),
        }
        for f in gj["features"]
    ]
    _dump(SAIDA / arquivo, feats)
    print(f"  {arquivo:<27} {len(feats):>4} feições")


def _dump(destino: Path, feats: list[dict]) -> None:
    """Grava uma feição por linha.

    Estes arquivos são versionados. Em linha única, qualquer regeneração vira
    "1 linha alterada" no diff e não dá para ver o que mudou; com uma feição por
    linha, o diff aponta exatamente quais municípios mudaram de geometria.
    Continua sendo JSON válido e o custo em bytes é o dos '\\n'.
    """
    corpo = ",\n".join(json.dumps(f, ensure_ascii=False) for f in feats)
    destino.write_text(
        '{"type": "FeatureCollection", "features": [\n' + corpo + "\n]}",
        encoding="utf-8",
    )


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)

    hierarquia = carrega_hierarquia()
    print(f"Hierarquia: {len(hierarquia)} municípios, "
          f"{len({h['regiao_saude'] for h in hierarquia})} regiões de saúde, "
          f"{len({h['macro_saude'] for h in hierarquia})} macrorregiões")

    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    con.execute("""
        CREATE TABLE hierarquia (
            municipio_norm VARCHAR, municipio VARCHAR, codigo_ibge INTEGER,
            regiao_saude VARCHAR, macro_saude VARCHAR
        )
    """)
    con.executemany(
        "INSERT INTO hierarquia VALUES (?, ?, ?, ?, ?)",
        [(h["municipio_norm"], h["municipio"], h["codigo_ibge"],
          h["regiao_saude"], h["macro_saude"]) for h in hierarquia],
    )

    aliases_sql = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in ALIASES.items())
    con.execute(f"""
        CREATE TABLE pe AS
        SELECT
            s.* EXCLUDE (municipio_norm),
            h.municipio, h.codigo_ibge, h.regiao_saude, h.macro_saude
        FROM (
            SELECT
                s.*,
                CASE upper(strip_accents(trim(s.municipio_residencia)))
                    {aliases_sql}
                    ELSE upper(strip_accents(trim(s.municipio_residencia)))
                END AS municipio_norm
            FROM read_parquet('{SINAN_GLOB}', union_by_name = true) s
            WHERE upper(strip_accents(trim(s.uf_residencia))) = 'PERNAMBUCO'
        ) s
        LEFT JOIN hierarquia h USING (municipio_norm)
    """)

    total = con.execute("SELECT count(*) FROM pe").fetchone()[0]
    match = con.execute(
        "SELECT round(100.0 * count(*) FILTER (WHERE regiao_saude IS NOT NULL) / count(*), 2) FROM pe"
    ).fetchone()[0]
    anos = con.execute("SELECT min(ano_notificacao), max(ano_notificacao) FROM pe").fetchone()
    print(f"\nSINAN residência PE: {total:,} registros · {anos[0]}–{anos[1]}".replace(",", "."))
    print(f"Match município → região de saúde: {match}%")

    sem_match = con.execute("""
        SELECT municipio_residencia, count(*) AS casos FROM pe
        WHERE regiao_saude IS NULL GROUP BY 1 ORDER BY casos DESC LIMIT 20
    """).fetchdf()
    if len(sem_match):
        print("\n⚠ Municípios sem match (revisar normalização):")
        print(sem_match.to_string(index=False))

    destino = SAIDA / "pe_tb_sinan.parquet"
    con.execute(f"COPY pe TO '{destino}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"\n  pe_tb_sinan.parquet         {destino.stat().st_size / 1e6:.1f} MB")

    con.execute(
        f"COPY (SELECT municipio, codigo_ibge, regiao_saude, macro_saude FROM hierarquia) "
        f"TO '{SAIDA / 'municipios_pe.parquet'}' (FORMAT PARQUET)"
    )
    print(f"  municipios_pe.parquet       {len(hierarquia)} municípios")

    escreve_geojson_municipios(hierarquia)
    escreve_geojson_nivel(GEO_REGIOES, "NomeRegSau", "regiao_saude", "regioes_saude_pe.geojson")
    escreve_geojson_nivel(GEO_MACRO, "NomeMacro", "macro_saude", "macro_saude_pe.geojson")

    con.close()
    print("\nOK")


if __name__ == "__main__":
    main()
