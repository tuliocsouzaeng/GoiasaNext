# -*- coding: utf-8 -*-
"""
matching.py (v2 - multi-categoria)
-----------------------------------
Motor de correlacao generico: cada categoria de material (tubulacao,
estrutura metalica, bombas/redutores, ...) e um "CategoryProfile" com:
  - um jeito de reconhecer o TIPO da peca dentro da categoria (regex)
  - uma funcao que extrai atributos tecnicos da descricao (dimensao,
    grade de material, norma, etc.)
  - uma lista negra de termos que indicam "isso e outra coisa" (kits,
    conjuntos, etc.)

O motor de pontuacao (quantos atributos batem entre o item a comprar e a
linha do SAP) e o MESMO para todas as categorias -- so muda o que cada
categoria considera "atributo relevante". Isso e o que te permite
escalar sem reescrever a logica central toda vez.

Continua sem nenhuma IA/LLM: e tudo regex + regras + pandas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

import pandas as pd

# --------------------------------------------------------------------------
# Normalizacao de texto (comum a todas as categorias)
# --------------------------------------------------------------------------

_ACCENTS = str.maketrans(
    "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
    "AAAAAEEEEIIIIOOOOOUUUUC",
)


def norm(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    return s.translate(_ACCENTS)


# --------------------------------------------------------------------------
# Estrutura generica de atributo + motor de pontuacao
# --------------------------------------------------------------------------

@dataclass
class Attribute:
    """Um atributo extraido do item a comprar, a ser conferido no SAP.

    name: rotulo (so para debug/relatorio)
    values: lista de valores encontrados (ex: ["8", "4"] para uma reducao 8"x4")
    mandatory: se True, uma linha do SAP que nao contenha NENHUM desses
               valores e descartada (nao vira candidata).
    weight: pontos somados quando o atributo bate.
    matcher: funcao (row_desc_norm, value) -> bool
    """
    name: str
    values: list
    mandatory: bool
    weight: int
    matcher: Callable[[str, str], bool]

    def satisfied_by(self, row_desc: str) -> bool:
        return any(self.matcher(row_desc, v) for v in self.values)


@dataclass
class CategoryProfile:
    name: str
    type_regex: dict
    blacklist: re.Pattern
    extract_type: Callable[[str], object]
    extract_attributes: Callable[[str], list]
    max_desc_len: int = 200


def _score_row(row_desc: str, attributes: list) -> int:
    score = 0
    for attr in attributes:
        if not attr.values:
            continue
        hit = attr.satisfied_by(row_desc)
        if attr.mandatory and not hit:
            return None
        if hit:
            score += attr.weight
    return score


def _classify_confidence(row_desc: str, attributes: list) -> str:
    relevant = [a for a in attributes if a.values]
    if not relevant:
        return "Baixa"
    hits = sum(1 for a in relevant if a.satisfied_by(row_desc))
    ratio = hits / len(relevant)
    if ratio >= 0.999:
        return "Alta"
    elif ratio >= 0.5:
        return "Media"
    return "Baixa"


def _generic_size_matcher(row_desc: str, size: str) -> bool:
    s = size.replace(".", r"[.\s]")
    pattern = r"(?<![\d.,/])" + s + r"(?![\d,./])"
    return re.search(pattern, row_desc) is not None


def _generic_token_matcher(row_desc: str, token: str) -> bool:
    return token.replace(" ", "") in row_desc.replace(" ", "")


def _generic_number_matcher(row_desc: str, num: str) -> bool:
    pattern = r"(?<!\d)" + re.escape(num) + r"(?!\d)"
    return re.search(pattern, row_desc) is not None


# ==========================================================================
# CATEGORIA: TUBULACAO  (validado com dados reais)
# ==========================================================================

_SIZE_RE = re.compile(r'(\d+(?:[.,]\d+/\d+)?(?:/\d+)?)\s*"')
_DN_RE = re.compile(r'DN\.?\s*(\d+(?:[.,]\d+/\d+)?(?:/\d+)?)\s*"?')
_GRADE_PATTERNS = [
    r"GR\s*P\s*11\b", r"GR\s*P\s*22\b", r"GR\s*F\s*11\b", r"GR\s*F\s*22\b",
    r"GR\s*WP\s*11\b", r"GR\s*WP\s*22\b", r"\bWPB\b", r"GR\s*B\s*16\b",
    r"GR\s*B\s*7\b", r"GR\s*B\s*60\b", r"GR\s*2H\b", r"GR\s*4\b", r"GR\s*B\b",
]
_ASTM_RE = re.compile(r"A\s?(335|182|234|106|53|105|193|194|672)")

_TUBULACAO_TYPE_REGEX = {
    "TUBO": re.compile(r"\bTUBO\b"),
    "COTOVELO": re.compile(r"\bCOTOVELO\b"),
    "CURVA": re.compile(r"\bCURVA\b"),
    "REDUCAO": re.compile(r"\bREDU[CÇ][AÃ]O\b|\bREDUCAO\b|\bREDUÇÃO\b"),
    "FLANGE": re.compile(r"\bFLANGE\b"),
    "CAP": re.compile(r"\bCAP\b"),
    "MEIA LUVA": re.compile(r"\bMEIA\s+LUVA\b"),
    "LUVA": re.compile(r"(?<!MEIA )\bLUVA\b"),
    "COLAR": re.compile(r"\bCOLAR\b"),
    "TEE": re.compile(r"\bTEE?\b"),
    "JUNTA ESPIRALADA": re.compile(r"\bJUNTA\s+ESPIRAL\w*\b|\bJUNTA\s+METALIC\w*\b"),
    "JUNTA": re.compile(r"\bJUNTA\b"),
    "PARAFUSO ESTOJO": re.compile(
        r"\bPARAFUSO\s+ESTOJO\b|\bPARAFUSO\s+PRISIONEIRO\b|\bTIRANTE\b"
    ),
}
_TUBULACAO_BLACKLIST = re.compile(
    r"\bSKID\b|\bCONJUNTO\b|\bMOTOR\b|\bBOMBA\b|\bMOTOREDUTOR\b|\bREDUTOR\b"
)


def _tubulacao_extract_type(d: str):
    if d.startswith("TUBO"):
        return "TUBO"
    if d.startswith("COTOVELO"):
        return "COTOVELO"
    if d.startswith("CURVA"):
        return "CURVA"
    if "REDUCAO" in d:
        return "REDUCAO"
    if d.startswith("FLANGE"):
        return "FLANGE"
    if d.startswith("CAP"):
        return "CAP"
    if d.startswith("MEIA LUVA"):
        return "MEIA LUVA"
    if d.startswith("LUVA"):
        return "LUVA"
    if "COLAR" in d:
        return "COLAR"
    if d.startswith("TEE"):
        return "TEE"
    if "JUNTA ESPIRAL" in d:
        return "JUNTA ESPIRALADA"
    if d.startswith("JUNTA"):
        return "JUNTA"
    if d.startswith("PARAFUSO ESTOJO"):
        return "PARAFUSO ESTOJO"
    return None


def _tubulacao_extract_attributes(d: str) -> list:
    sizes = {m.group(1).replace(",", ".") for m in _SIZE_RE.finditer(d)}
    sizes |= {m.group(1).replace(",", ".") for m in _DN_RE.finditer(d)}

    grades = []
    for pat in _GRADE_PATTERNS:
        m = re.search(pat, d)
        if m:
            grades.append(re.sub(r"\s+", "", m.group(0)))
    astm = ["A" + a for a in _ASTM_RE.findall(d)]

    scheds = []
    if "XXS" in d:
        scheds.append("XXS")
    m = re.search(r"SCH\s*(\d+)", d)
    if m:
        scheds.append("SCH" + m.group(1))
    if re.search(r"\bSTD\b", d):
        scheds.append("STD")

    ratings = list(set(re.findall(r"(\d{3,4})\s*LBS?", d)))

    thickness = None
    mt = re.search(r"(\d+,\d+)\s*MM", d)
    if mt:
        thickness = mt.group(1)

    return [
        Attribute("diametro", sorted(sizes), mandatory=True, weight=3, matcher=_generic_size_matcher),
        Attribute("grade", grades, mandatory=True, weight=4, matcher=_generic_token_matcher),
        Attribute("astm", [] if grades else astm, mandatory=False, weight=2, matcher=_generic_token_matcher),
        Attribute("classe_pressao", ratings, mandatory=True, weight=4, matcher=_generic_number_matcher),
        Attribute("schedule", scheds, mandatory=False, weight=2, matcher=_generic_token_matcher),
        Attribute("espessura_mm", [thickness] if thickness else [], mandatory=False, weight=2, matcher=_generic_token_matcher),
    ]


TUBULACAO = CategoryProfile(
    name="tubulacao",
    type_regex=_TUBULACAO_TYPE_REGEX,
    blacklist=_TUBULACAO_BLACKLIST,
    extract_type=_tubulacao_extract_type,
    extract_attributes=_tubulacao_extract_attributes,
)


# ==========================================================================
# CATEGORIA: ESTRUTURA METALICA  (rascunho -- AJUSTAR com amostra real do SAP)
# ==========================================================================
# Perfis tipicos: perfil W, perfil U/C, cantoneira (L), chapa, tubo
# estrutural retangular/quadrado, barra chata/redonda. Atributos tipicos:
# designacao do perfil (ex: "W 200X22,5", "U 100X50X17X3", "L 3X3X1/4"),
# grade de aco estrutural (A36, A572 GR50, A588), espessura de chapa.
#
# ISTO E UM PONTO DE PARTIDA. Antes de usar em producao, faca o mesmo que
# fizemos para tubulacao: pegue ~20 descricoes reais de estrutura metalica
# do seu SAP e ajuste os regex abaixo contra elas.

_PERFIL_RE = re.compile(
    r"\b(W|U|C|L|HP)\s*(\d+[.,]?\d*)\s*[Xx]\s*(\d+[.,]?\d*)(?:\s*[Xx]\s*(\d+[.,]?\d*))?"
)
_CHAPA_ESP_RE = re.compile(r"CHAPA.*?(\d+[.,]?\d*)\s*(MM|\")")
_ACO_GRADE_RE = re.compile(r"\bA\s?(36|572|588|500)\b|\bGR\s?(36|50|60)\b")

_ESTRUTURA_TYPE_REGEX = {
    "PERFIL": re.compile(r"\bPERFIL\b|\bVIGA\b"),
    "CANTONEIRA": re.compile(r"\bCANTONEIRA\b"),
    "CHAPA": re.compile(r"\bCHAPA\b"),
    "TUBO ESTRUTURAL": re.compile(r"\bTUBO\b.*\b(QUADRAD|RETANGULAR)\w*\b"),
    "BARRA": re.compile(r"\bBARRA\s+(CHATA|REDONDA)\b"),
    "PARAFUSO": re.compile(r"\bPARAFUSO\b"),
}
_ESTRUTURA_BLACKLIST = re.compile(r"\bSKID\b|\bCONJUNTO\b|\bMOTOR\b|\bBOMBA\b")


def _estrutura_extract_type(d: str):
    if "PERFIL" in d or "VIGA" in d:
        return "PERFIL"
    if "CANTONEIRA" in d:
        return "CANTONEIRA"
    if "CHAPA" in d:
        return "CHAPA"
    if "TUBO" in d and ("QUADRAD" in d or "RETANGULAR" in d):
        return "TUBO ESTRUTURAL"
    if "BARRA" in d:
        return "BARRA"
    # "PARAFUSO ESTOJO"/"PARAFUSO PRISIONEIRO" sao vocabulario de tubulacao
    # (parafuso-prisioneiro para flange), nao de estrutura metalica --
    # exclui explicitamente para nao roubar esses itens do perfil correto.
    if d.startswith("PARAFUSO") and "ESTOJO" not in d and "PRISIONEIRO" not in d:
        return "PARAFUSO"
    return None


def _estrutura_extract_attributes(d: str) -> list:
    perfil_designacoes = []
    for m in _PERFIL_RE.finditer(d):
        perfil_designacoes.append("".join(g for g in m.groups() if g))

    chapa_esp = [m.group(1) for m in _CHAPA_ESP_RE.finditer(d)]

    grades = []
    for m in _ACO_GRADE_RE.finditer(d):
        grades.append("".join(g for g in m.groups() if g))

    return [
        Attribute("designacao_perfil", perfil_designacoes, mandatory=True, weight=4, matcher=_generic_token_matcher),
        Attribute("espessura_chapa", chapa_esp, mandatory=True, weight=3, matcher=_generic_size_matcher),
        Attribute("grade_aco", grades, mandatory=False, weight=2, matcher=_generic_token_matcher),
    ]


ESTRUTURA_METALICA = CategoryProfile(
    name="estrutura_metalica",
    type_regex=_ESTRUTURA_TYPE_REGEX,
    blacklist=_ESTRUTURA_BLACKLIST,
    extract_type=_estrutura_extract_type,
    extract_attributes=_estrutura_extract_attributes,
)


# ==========================================================================
# CATEGORIA: EQUIPAMENTOS (bombas, redutores, motores)  (rascunho)
# ==========================================================================
# Diferenca importante: bombas/redutores/motores normalmente sao ativos
# especificos (com TAG, fabricante, modelo), nao commodities de catalogo
# como tubo/conexao. A correlacao por atributo dimensional tende a nao
# funcionar bem aqui -- o mais confiavel costuma ser casar por
# FABRICANTE + MODELO, e mesmo assim tratar como sugestao de baixa
# confianca por padrao (equipamento critico merece conferencia manual
# sempre, mesmo com match "perfeito" de texto).

_TAG_RE = re.compile(r"\bTAG\s*[:\-]?\s*([A-Z0-9\-]+)\b")
_MODELO_RE = re.compile(r"\bMODELO\s*[:\-]?\s*([A-Z0-9\-\/]+)\b")
_FABRICANTES_CONHECIDOS = [
    "WEG", "KSB", "SIEMENS", "SEW", "FALK", "FLENDER", "GRUNDFOS", "IMBIL",
    "SULZER", "NETZSCH", "MONO",
]

_EQUIP_TYPE_REGEX = {
    "BOMBA": re.compile(r"\bBOMBA\b"),
    "REDUTOR": re.compile(r"\bREDUTOR\b|\bMOTOREDUTOR\b"),
    "MOTOR": re.compile(r"\bMOTOR\b"),
}
_EQUIP_BLACKLIST = re.compile(r"(?!)")  # nunca casa -- nada bloqueado por padrao


def _equip_extract_type(d: str):
    if "BOMBA" in d:
        return "BOMBA"
    if "REDUTOR" in d:
        return "REDUTOR"
    if "MOTOR" in d:
        return "MOTOR"
    return None


def _equip_extract_attributes(d: str) -> list:
    tags = _TAG_RE.findall(d)
    modelos = _MODELO_RE.findall(d)
    fabricantes = [f for f in _FABRICANTES_CONHECIDOS if f in d]

    return [
        Attribute("tag", tags, mandatory=False, weight=5, matcher=_generic_token_matcher),
        Attribute("modelo", modelos, mandatory=False, weight=4, matcher=_generic_token_matcher),
        Attribute("fabricante", fabricantes, mandatory=bool(fabricantes),
                  weight=3, matcher=_generic_token_matcher),
    ]


EQUIPAMENTOS = CategoryProfile(
    name="equipamentos",
    type_regex=_EQUIP_TYPE_REGEX,
    blacklist=_EQUIP_BLACKLIST,
    extract_type=_equip_extract_type,
    extract_attributes=_equip_extract_attributes,
)

# Ao criar uma nova categoria, so precisa: 1) escrever as funcoes
# extract_type/extract_attributes de acordo com o vocabulario real do SAP
# para aquela familia de materiais, e 2) registrar aqui.
CATEGORY_REGISTRY = {
    "tubulacao": TUBULACAO,
    "estrutura_metalica": ESTRUTURA_METALICA,
    "equipamentos": EQUIPAMENTOS,
}

# Ordem de prioridade para deteccao automatica: perfis mais especificos
# primeiro. Ex: um item "TUBO QUADRADO..." bate tanto no regex generico
# de TUBULACAO (\bTUBO\b) quanto no de ESTRUTURA_METALICA (TUBO + QUADRADO),
# entao checamos estrutura_metalica antes -- ela so "aceita" o item se as
# condicoes extras (quadrado/retangular) baterem, entao nao ha risco de
# ela roubar um tubo de tubulacao comum.
CATEGORY_PRIORITY = ["equipamentos", "estrutura_metalica", "tubulacao"]


def detect_category(desc: str) -> str | None:
    """Tenta identificar a categoria de um item a partir da sua descricao,
    testando os perfis registrados em ordem de especificidade. Retorna
    None se nenhum perfil reconhecer o tipo da peca (o item devera ser
    tratado manualmente / marcado para revisao)."""
    d = norm(desc.upper())
    for cat_name in CATEGORY_PRIORITY:
        profile = CATEGORY_REGISTRY[cat_name]
        if profile.extract_type(d) is not None:
            return cat_name
    return None


# --------------------------------------------------------------------------
# API publica
# --------------------------------------------------------------------------

def load_sap_catalog(
    path_or_buffer,
    code_col: str = "MAT_CdsMaterial",
    desc_col: str = "MAT_DssDecricao",
) -> pd.DataFrame:
    df = pd.read_excel(path_or_buffer)
    df = df.rename(columns={code_col: "codigo", desc_col: "descricao"})
    df["_desc_norm"] = df["descricao"].astype(str).str.upper().apply(norm)
    return df


def match_items(
    purchase_items: list,
    sap_df: pd.DataFrame,
    category: str = "auto",
    top_n: int = 3,
) -> pd.DataFrame:
    """
    purchase_items: lista de dicts com pelo menos: item, desc, un, qtd
                    (fluido/categoria extra, opcional)
    category: "auto" (detecta a categoria de CADA item automaticamente,
              recomendado para listas com materiais variados), ou uma
              chave fixa de CATEGORY_REGISTRY ("tubulacao",
              "estrutura_metalica", "equipamentos") para forcar todos os
              itens a usarem o mesmo perfil.
    """
    if category != "auto" and category not in CATEGORY_REGISTRY:
        raise ValueError(
            f"Categoria '{category}' nao registrada. "
            f"Opcoes: 'auto', {list(CATEGORY_REGISTRY)}"
        )

    codes = sap_df["codigo"].tolist()
    descs = sap_df["_desc_norm"].tolist()
    raw_descs = sap_df["descricao"].tolist()
    n = len(sap_df)

    rows = []
    for it in purchase_items:
        d = norm(it["desc"].upper())

        item_category = category
        if category == "auto":
            item_category = detect_category(it["desc"])
            if item_category is None:
                # Nenhum perfil reconheceu o tipo da peca -- nao da para
                # buscar no SAP com seguranca, entao ja cai em "Criar
                # Material" sinalizando que precisa de categoria manual.
                rows.append(
                    {
                        "Item": it.get("item"),
                        "Descricao": it["desc"],
                        "Un": it.get("un", ""),
                        "Quantidade": it.get("qtd", ""),
                        "Fluido": it.get("fluido", ""),
                        "Categoria": "Nao identificada",
                        "Codigo SAP sugerido": "Criar Material",
                        "Descricao SAP correspondente": "",
                        "Confianca": "Criar Material",
                        "Alternativas": "",
                        "Observacao": (
                            "Tipo de peca nao reconhecido por nenhum perfil "
                            "cadastrado; classificar manualmente."
                        ),
                    }
                )
                continue

        profile = CATEGORY_REGISTRY[item_category]
        typ = profile.extract_type(d)
        attrs = profile.extract_attributes(d)
        type_re = profile.type_regex.get(typ)

        candidates = []
        for i in range(n):
            rd = descs[i]
            if len(rd) > profile.max_desc_len:
                continue
            if type_re and not type_re.search(rd):
                continue
            if profile.blacklist.search(rd):
                continue
            sc = _score_row(rd, attrs)
            if sc is not None:
                candidates.append((sc, codes[i], raw_descs[i]))

        candidates.sort(key=lambda x: -x[0])
        top = candidates[:top_n]

        if top:
            _, best_code, best_desc = top[0]
            best_desc_norm = norm(str(best_desc).upper())
            confianca = _classify_confidence(best_desc_norm, attrs)
            alternativas = " | ".join(f"{c} - {d2}" for _, c, d2 in top[1:3])
            observacao = "" if confianca == "Alta" else "Revisar antes de aprovar."
            codigo_sugerido = best_code
            descricao_sap = best_desc
        else:
            confianca = "Criar Material"
            alternativas = ""
            observacao = "Nenhum material equivalente encontrado no SAP; solicitar cadastro."
            codigo_sugerido = "Criar Material"
            descricao_sap = ""

        rows.append(
            {
                "Item": it.get("item"),
                "Descricao": it["desc"],
                "Un": it.get("un", ""),
                "Quantidade": it.get("qtd", ""),
                "Fluido": it.get("fluido", ""),
                "Categoria": item_category,
                "Codigo SAP sugerido": codigo_sugerido,
                "Descricao SAP correspondente": descricao_sap,
                "Confianca": confianca,
                "Alternativas": alternativas,
                "Observacao": observacao,
            }
        )

    return pd.DataFrame(rows)
