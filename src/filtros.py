"""
filtros.py — estado dos filtros como valor imutável
═══════════════════════════════════════════════════
Um `Filtros` é hasheável (tuplas, não listas), então serve direto como chave de
`@st.cache_data` e de `lru_cache`: dois reruns com os mesmos filtros reaproveitam
o agregado já calculado no DuckDB.

Tupla vazia = "todos" (nenhuma cláusula é adicionada ao WHERE).

A hierarquia geográfica é em cascata: macro → região de saúde → município.
Filtrar por macrorregião já restringe as regiões e municípios disponíveis, mas
os três podem ser combinados livremente (o WHERE simplesmente soma as condições).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Filtros:
    anos: tuple[int, ...] = ()
    macros: tuple[str, ...] = ()
    regioes: tuple[str, ...] = ()
    municipios: tuple[str, ...] = ()
    sexo: tuple[str, ...] = ()
    formas: tuple[str, ...] = ()
    racas: tuple[str, ...] = ()
    entradas: tuple[str, ...] = ()
    hiv: tuple[str, ...] = ()
    vuln: tuple[str, ...] = field(default=())
    agravos: tuple[str, ...] = field(default=())

    @property
    def ano_ref(self) -> int | None:
        """Ano mais recente selecionado — referência dos KPIs pontuais."""
        return max(self.anos) if self.anos else None

    @property
    def tem_recorte_geo(self) -> bool:
        return bool(self.macros or self.regioes or self.municipios)

    def where_sql(self) -> tuple[str, list]:
        """Monta o WHERE e os parâmetros posicionais. Sempre retorna algo verdadeiro."""
        clausulas: list[str] = ["1=1"]
        params: list = []

        def _in(coluna: str, valores: tuple) -> None:
            if valores:
                marcadores = ", ".join("?" for _ in valores)
                clausulas.append(f"{coluna} IN ({marcadores})")
                params.extend(valores)

        _in("ano_notificacao", self.anos)
        _in("macro_saude", self.macros)
        _in("regiao_saude", self.regioes)
        _in("municipio", self.municipios)
        _in("sexo", self.sexo)
        _in("forma", self.formas)
        _in("raca_cor", self.racas)
        _in("tipo_entrada", self.entradas)
        _in("status_hiv", self.hiv)

        # Vulnerabilidades e comorbidades são flags Sim/Não — combinam em AND
        # ("apenas pacientes que sejam X e Y"), igual ao painel nacional.
        for coluna in self.vuln + self.agravos:
            clausulas.append(f"{coluna} = 'Sim'")

        return " AND ".join(clausulas), params

    def where_geo_sql(self, alias: str = "m") -> tuple[str, list]:
        """WHERE só com o recorte geográfico — usado no denominador populacional.

        A população não pode ser filtrada por sexo, raça ou comorbidade: o IBGE
        só dá o total residente. Por isso o denominador usa apenas a geografia,
        e a UI avisa quando há filtros de perfil ativos (a taxa deixa de ser uma
        incidência populacional e vira "casos daquele perfil por 100 mil hab.").
        """
        clausulas: list[str] = ["1=1"]
        params: list = []
        for coluna, valores in (
            ("macro_saude", self.macros),
            ("regiao_saude", self.regioes),
            ("municipio", self.municipios),
        ):
            if valores:
                clausulas.append(f"{alias}.{coluna} IN ({', '.join('?' for _ in valores)})")
                params.extend(valores)
        return " AND ".join(clausulas), params

    @property
    def filtros_de_perfil_ativos(self) -> bool:
        """Há filtro que afeta o numerador mas não o denominador populacional?"""
        return bool(self.sexo or self.formas or self.racas or self.entradas
                    or self.hiv or self.vuln or self.agravos)

    def rotulo_geo(self) -> str:
        """Descrição curta do recorte geográfico, para hero e legendas."""
        if self.municipios:
            return (self.municipios[0] if len(self.municipios) == 1
                    else f"{len(self.municipios)} municípios")
        if self.regioes:
            return (f"Região de Saúde de {self.regioes[0]}" if len(self.regioes) == 1
                    else f"{len(self.regioes)} regiões de saúde")
        if self.macros:
            return (f"Macrorregião {self.macros[0]}" if len(self.macros) == 1
                    else f"{len(self.macros)} macrorregiões")
        return "Pernambuco"
