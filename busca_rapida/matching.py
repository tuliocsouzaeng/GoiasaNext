# -*- coding: utf-8 -*-
"""
matching.py
-----------
Correlaciona uma lista de materiais a comprar (tubos, conexoes, flanges,
juntas, parafusos etc.) com o catalogo de materiais ja cadastrados no SAP,
usando extracao de atributos tecnicos (diametro, grade de material,
schedule/espessura, classe de pressao) e pontuacao por aderencia.

Nao usa nenhum modelo de IA/LLM -- e 100% regras + regex + pandas.
Pode ser importado por um app Streamlit, um script batch, uma API, etc.

Uso basico:
    import pandas as pd
    from matching import load_sap_catalog, match_items

    sap_df = load_sap_catalog("sap_export.xlsx")
    purchase_items = [
        {
            "item": 103,
            "desc": 'TUBO 1/2", SCH XXS, EXTREMIDADE PLANA, SEM COSTURA, '
                    'ASME B36.10 M, ASTM A335 GR P11',
            "un": "m",
            "qtd": 0.1,
            "fluido": "Vapor Media (VM)",
        },
        ...
    ]
    result_df = match_items(purchase_items, sap_df)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

# --------------------------------------------------------------------------
# Normalizacao de texto
# --------------------------------------------------------------------------

_ACCENTS = str.maketrans(
    "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
    "AAAAAEEEEIIIIOOOOOUUUUC",
)


def norm(s: str) -> str:
    """Remove acentos e normaliza para maiusculas (nao muda pontuacao)."""
    if not isinstance(s, str):
        s = str(s)
    return s.translate(_ACCENTS)


# --------------------------------------------------------------------------
# Extracao de atributos a partir da descricao do item a comprar
# --------------------------------------------------------------------------

_SIZE_RE = re.compile(r'(\d+(?:[.,]\d+/\d+)?(?:/\d+)?)\s*"')
_DN_RE = re.compile(r'DN\.?\s*(\d+(?:[.,]\d+/\d+)?(?:/\d+)?)\s*"?')

_GRADE_PATTERNS = [
    r"GR\s*P\s*11\b", r"GR\s*P\s*22\b", r"GR\s*F\s*11\b", r"GR\s*F\s*22\b",
    r"GR\s*WP\s*11\b", r"GR\s*WP\s*22\b", r"\bWPB\b", r"GR\s*B\s*16\b",
    r"GR\s*B\s*7\b", r"GR\s*B\s*60\b", r"GR\s*2H\b", r"GR\s*4\b", r"GR\s*B\b",
]
_ASTM_RE = re.compile(r"A\s?(335|182|234|106|53|105|193|194|672)")


def extract_type(desc_norm: str) -> str | None:
    """Classifica o item pelo tipo de peca (primeira palavra-chave reconhecida)."""
    d = desc_norm.upper()
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


def _norm_size(s: str) -> str:
    return s.replace(",", ".").strip()


def extract_sizes(desc_norm: str) -> set[str]:
    sizes = set()
    for m in _SIZE_RE.finditer(desc_norm):
        sizes.add(_norm_size(m.group(1)))
    for m in _DN_RE.finditer(desc_norm):
        sizes.add(_norm_size(m.group(1)))
    return sizes


def extract_grade(desc_norm: str) -> tuple[list[str], list[str]]:
    d = desc_norm.upper()
    grades = []
    for pat in _GRADE_PATTERNS:
        m = re.search(pat, d)
        if m:
            grades.append(re.sub(r"\s+", "", m.group(0)))
    astm = ["A" + a for a in _ASTM_RE.findall(d)]
    return grades, astm


def extract_schedule(desc_norm: str) -> list[str]:
    d = desc_norm.upper()
    scheds = []
    if "XXS" in d:
        scheds.append("XXS")
    m = re.search(r"SCH\s*(\d+)", d)
    if m:
        scheds.append("SCH" + m.group(1))
    if re.search(r"\bSTD\b", d):
        scheds.append("STD")
    return scheds


def extract_rating(desc_norm: str) -> list[str]:
    d = desc_norm.upper()
    return list(set(re.findall(r"(\d{3,4})\s*LBS?", d)))


def extract_thickness(desc_norm: str) -> str | None:
    m = re.search(r"(\d+,\d+)\s*MM", desc_norm.upper())
    return m.group(1) if m else None


@dataclass
class ItemAttributes:
    typ: str | None
    sizes: set[str]
    grades: list[str]
    astm: list[str]
    scheds: list[str]
    ratings: list[str]
    thickness: str | None


def extract_attributes(desc: str) -> ItemAttributes:
    d = norm(desc.upper())
    return ItemAttributes(
        typ=extract_type(d),
        sizes=extract_sizes(d),
        grades=extract_grade(d)[0],
        astm=extract_grade(d)[1],
        scheds=extract_schedule(d),
        ratings=extract_rating(d),
        thickness=extract_thickness(d),
    )


# --------------------------------------------------------------------------
# Filtro/pontuacao contra o catalogo SAP
# --------------------------------------------------------------------------

TYPE_REGEX = {
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

# Descricoes de kits/conjuntos de equipamento sao longas e cheias de numeros
# soltos -> geram falsos positivos. Filtramos por tamanho e por termos de
# equipamento que nao fazem sentido para peca de tubulacao avulsa.
_MAX_DESC_LEN = 200
_BLACKLIST = re.compile(
    r"\bSKID\b|\bCONJUNTO\b|\bMOTOR\b|\bBOMBA\b|\bMOTOREDUTOR\b|\bREDUTOR\b"
)


def _sap_has_size(row_desc: str, size: str) -> bool:
    s = size.replace(".", r"[.\s]")
    pattern = r"(?<![\d.,/])" + s + r"(?![\d,./])"
    return re.search(pattern, row_desc) is not None


def _sap_has_rating(row_desc: str, rating: str) -> bool:
    pattern = r"(?<!\d)" + re.escape(rating) + r"(?!\d)"
    return re.search(pattern, row_desc) is not None


def _score_row(row_desc: str, attrs: ItemAttributes) -> int | None:
    """Retorna a pontuacao de aderencia, ou None se um atributo obrigatorio
    (diametro / grade / classe de pressao, quando presentes na compra) nao bater."""
    score = 0

    matched_sizes = sum(1 for s in attrs.sizes if _sap_has_size(row_desc, s))
    if attrs.sizes and matched_sizes == 0:
        return None
    score += matched_sizes * 3

    if attrs.grades:
        g_match = any(
            g.replace(" ", "") in row_desc.replace(" ", "") for g in attrs.grades
        )
        if not g_match:
            return None
        score += 4
    elif attrs.astm:
        if any(a in row_desc for a in attrs.astm):
            score += 2

    if attrs.ratings:
        if not any(_sap_has_rating(row_desc, r) for r in attrs.ratings):
            return None
        score += 4

    for sch in attrs.scheds:
        if sch.replace("SCH", "SCH ") in row_desc or sch in row_desc:
            score += 2

    if attrs.thickness and attrs.thickness in row_desc:
        score += 2

    return score


def _classify_confidence(best_desc_norm: str, attrs: ItemAttributes) -> str:
    """Confianca = fracao dos atributos DISPONIVEIS na compra que o melhor
    candidato realmente satisfaz (nao e so a pontuacao bruta)."""
    total = 0
    hit = 0
    if attrs.sizes:
        total += 1
        if all(_sap_has_size(best_desc_norm, s) for s in attrs.sizes):
            hit += 1
    if attrs.grades or attrs.astm:
        total += 1
        ok = (
            any(g.replace(" ", "") in best_desc_norm.replace(" ", "") for g in attrs.grades)
            if attrs.grades
            else any(a in best_desc_norm for a in attrs.astm)
        )
        if ok:
            hit += 1
    if attrs.ratings:
        total += 1
        if any(_sap_has_rating(best_desc_norm, r) for r in attrs.ratings):
            hit += 1
    if attrs.scheds:
        total += 1
        if any(
            (s.replace("SCH", "SCH ") in best_desc_norm or s in best_desc_norm)
            for s in attrs.scheds
        ):
            hit += 1
    if attrs.thickness:
        total += 1
        if attrs.thickness in best_desc_norm:
            hit += 1

    if total == 0:
        return "Baixa"
    ratio = hit / total
    if ratio >= 0.999:
        return "Alta"
    elif ratio >= 0.5:
        return "Media"
    return "Baixa"


# --------------------------------------------------------------------------
# API publica
# --------------------------------------------------------------------------

def load_sap_catalog(
    path_or_buffer,
    code_col: str = "MAT_CdsMaterial",
    desc_col: str = "MAT_DssDecricao",
) -> pd.DataFrame:
    """Le o export do SAP (xlsx) e prepara a coluna de descricao normalizada
    usada internamente pelo matcher. Chame isso UMA VEZ e reuse o DataFrame
    (em Streamlit, dentro de uma funcao com @st.cache_resource)."""
    df = pd.read_excel(path_or_buffer)
    df = df.rename(columns={code_col: "codigo", desc_col: "descricao"})
    df["_desc_norm"] = (
        df["descricao"].astype(str).str.upper().apply(norm)
    )
    return df


def match_items(
    purchase_items: list[dict],
    sap_df: pd.DataFrame,
    top_n: int = 3,
) -> pd.DataFrame:
    """
    purchase_items: lista de dicts com pelo menos as chaves:
        item, desc, un, qtd, fluido   (fluido e opcional)
    sap_df: retorno de load_sap_catalog()

    Retorna um DataFrame pronto para exibir/exportar, com colunas:
        Item, Descricao, Un, Quantidade, Fluido,
        Codigo SAP sugerido, Descricao SAP correspondente,
        Confianca, Alternativas, Observacao
    """
    codes = sap_df["codigo"].tolist()
    descs = sap_df["_desc_norm"].tolist()
    raw_descs = sap_df["descricao"].tolist()
    n = len(sap_df)

    rows = []
    for it in purchase_items:
        attrs = extract_attributes(it["desc"])
        type_re = TYPE_REGEX.get(attrs.typ)

        candidates = []
        for i in range(n):
            rd = descs[i]
            if len(rd) > _MAX_DESC_LEN:
                continue
            if type_re and not type_re.search(rd):
                continue
            if _BLACKLIST.search(rd):
                continue
            sc = _score_row(rd, attrs)
            if sc is not None:
                candidates.append((sc, codes[i], raw_descs[i]))

        candidates.sort(key=lambda x: -x[0])
        top = candidates[:top_n]

        if top:
            best_score, best_code, best_desc = top[0]
            best_desc_norm = norm(str(best_desc).upper())
            confianca = _classify_confidence(best_desc_norm, attrs)
            alternativas = " | ".join(f"{c} - {d}" for _, c, d in top[1:3])
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
                "Codigo SAP sugerido": codigo_sugerido,
                "Descricao SAP correspondente": descricao_sap,
                "Confianca": confianca,
                "Alternativas": alternativas,
                "Observacao": observacao,
            }
        )

    return pd.DataFrame(rows)
