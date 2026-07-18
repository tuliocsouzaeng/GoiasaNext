# -*- coding: utf-8 -*-
"""
purchase_parser.py
-------------------
Converte a lista de materiais a comprar (upload do usuario) no formato
de dicionarios que matching.match_items() espera.

Recomendacao: peca para a lista de compras vir em Excel/CSV com colunas
fixas (Item, Descricao, Un, Quantidade, Fluido) em vez de PDF. Extrair
tabelas de PDF de forma robusta e o ponto mais fragil do pipeline -- o
layout muda de fornecedor para fornecedor, de revisao para revisao do
documento, etc. Se o PDF for sempre gerado pelo mesmo sistema com o
mesmo layout, da para automatizar (exemplo abaixo com pdfplumber), mas
exige ajuste fino e revisao cada vez que o layout mudar.
"""

from __future__ import annotations

import re
import pandas as pd


def parse_excel_or_csv(uploaded_file) -> list[dict]:
    """Caminho recomendado: Excel/CSV com colunas Item, Descricao, Un,
    Quantidade, Fluido (nomes de coluna flexiveis, ver `_COLUMN_ALIASES`)."""
    if uploaded_file.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.columns = [c.strip() for c in df.columns]
    colmap = _match_columns(df.columns)

    items = []
    for _, row in df.iterrows():
        desc = str(row[colmap["desc"]]).strip()
        if not desc or desc.lower() == "nan":
            continue
        items.append(
            {
                "item": row.get(colmap.get("item"), None),
                "desc": desc,
                "un": row.get(colmap.get("un"), ""),
                "qtd": row.get(colmap.get("qtd"), ""),
                "fluido": row.get(colmap.get("fluido"), ""),
            }
        )
    return items


_COLUMN_ALIASES = {
    "item": ["item", "item nº", "nº"],
    "desc": ["descricao", "descrição", "desc"],
    "un": ["un.", "un", "unidade"],
    "qtd": ["quantidade", "qtd", "qtd."],
    "fluido": ["fluido", "spec", "sistema"],
}


def _match_columns(columns) -> dict:
    lower = {c.lower(): c for c in columns}
    colmap = {}
    for key, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower:
                colmap[key] = lower[alias]
                break
    if "desc" not in colmap:
        raise ValueError(
            "Nao encontrei uma coluna de descricao. Colunas disponiveis: "
            f"{list(columns)}"
        )
    return colmap


# --------------------------------------------------------------------------
# Caminho alternativo: extrair de um PDF com layout fixo (ex: uma linha por
# item, comecando com o numero do item). Ajuste o regex ITEM_LINE_RE ao
# layout real do seu PDF antes de usar em producao.
# --------------------------------------------------------------------------

ITEM_LINE_RE = re.compile(
    r"^(?P<item>\d+)\s+(?P<desc>.+?)\s+"
    r"(?P<un>m|pç|pc)\s+(?P<qtd>[\d.,]+)\s+"
    r"(?P<peso_un>[\d.,]+)\s+(?P<peso_tot>[\d.,]+)\s+(?P<spec>\S+.*)$"
)


def parse_pdf(uploaded_file, fluido_por_pagina: dict[int, str] | None = None) -> list[dict]:
    """Extrai itens de um PDF linha a linha usando pdfplumber.
    fluido_por_pagina: {indice_da_pagina: nome_do_fluido}, se cada pagina do
    PDF corresponder a um sistema diferente (como no caso Vapor Media /
    Vapor Escape / Vapor 67).

    ATENCAO: isso e um ponto de partida, nao uma solucao generica. Teste
    contra os seus PDFs reais e ajuste ITEM_LINE_RE / a logica de juncao de
    linhas quebradas (descricoes longas que ocupam 2 linhas no PDF)."""
    import pdfplumber

    items = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            fluido = (fluido_por_pagina or {}).get(page_idx, "")
            text = page.extract_text() or ""
            buffer = ""
            for line in text.split("\n"):
                buffer = f"{buffer} {line}".strip() if buffer else line
                m = ITEM_LINE_RE.match(buffer)
                if m:
                    items.append(
                        {
                            "item": int(m.group("item")),
                            "desc": m.group("desc").strip(),
                            "un": m.group("un"),
                            "qtd": m.group("qtd").replace(",", "."),
                            "fluido": fluido,
                        }
                    )
                    buffer = ""
    return items
