# -*- coding: utf-8 -*-
"""
sap_loader_gsheets.py
----------------------
Carrega o catalogo SAP a partir de uma planilha do Google Sheets (via
gspread/service account), no mesmo formato que matching.load_sap_catalog()
produz a partir de um Excel -- ou seja, e um substituto direto (drop-in).

Uso (dentro do app Streamlit, com cache):

    import streamlit as st
    from sap_loader_gsheets import load_sap_catalog_from_sheets

    @st.cache_resource(show_spinner="Carregando catalogo SAP do Drive...")
    def get_sap_catalog():
        creds = dict(st.secrets["GOOGLE_SHEETS_CREDS"])  # nunca hardcode
        return load_sap_catalog_from_sheets(
            creds=creds,
            sheet_key="SEU_SHEET_KEY_AQUI",
            worksheet_name="Catalogo_SAP",
            code_col="MAT_CdsMaterial",
            desc_col="MAT_DssDecricao",
        )

    sap_df = get_sap_catalog()

Onde colocar as credenciais no Render:
    Painel do serviço -> Environment -> adicionar uma env var (ex:
    GOOGLE_SHEETS_CREDS_JSON) com o JSON da service account colado como
    string. No codigo: json.loads(os.environ["GOOGLE_SHEETS_CREDS_JSON"]).
    Em Streamlit local, o equivalente e o arquivo .streamlit/secrets.toml
    (que NAO deve ir para o Git).
"""

from __future__ import annotations

import json
import os

import gspread
import pandas as pd

from busca_rapida.matching import norm


def _get_credentials_dict(creds) -> dict:
    """Aceita: dict ja pronto, string JSON, ou None (busca em env var)."""
    if creds is None:
        raw = os.environ.get("GOOGLE_SHEETS_CREDS_JSON")
        if raw is None:
            raise RuntimeError(
                "Nenhuma credencial fornecida e a env var "
                "GOOGLE_SHEETS_CREDS_JSON nao esta definida."
            )
        return json.loads(raw)
    if isinstance(creds, str):
        return json.loads(creds)
    return creds


def _dedupe_columns(header: list) -> list:
    """Replica o comportamento do pandas.read_excel para cabecalhos
    duplicados: 'MAT_DssDecricao' repetido vira
    'MAT_DssDecricao', 'MAT_DssDecricao.1', 'MAT_DssDecricao.2', ...
    Sem isso, renomear uma coluna duplicada afeta todas as copias e
    df["descricao"] deixa de ser uma Series (vira DataFrame)."""
    seen = {}
    result = []
    for name in header:
        if name not in seen:
            seen[name] = 0
            result.append(name)
        else:
            seen[name] += 1
            result.append(f"{name}.{seen[name]}")
    return result


def load_sap_catalog_from_sheets(
    creds,
    sheet_key: str,
    worksheet_name: str,
    code_col: str = "MAT_CdsMaterial",
    desc_col: str = "MAT_DssDecricao",
) -> pd.DataFrame:
    """
    creds: dict/str JSON com a service account (ou None para ler de
           GOOGLE_SHEETS_CREDS_JSON no ambiente).
    sheet_key: o ID da planilha (o mesmo padrao que voce ja usa em
           `planilha = gc.open_by_key("...")`).
    worksheet_name: nome da aba com o catalogo SAP.

    Retorna um DataFrame com colunas: codigo, descricao, _desc_norm
    -- o mesmo formato que matching.load_sap_catalog() gera a partir
    do Excel, entao match_items() funciona sem nenhuma mudanca.
    """
    info = _get_credentials_dict(creds)
    gc = gspread.service_account_from_dict(info)
    planilha = gc.open_by_key(sheet_key)
    aba = planilha.worksheet(worksheet_name)

    # get_all_values() traz listas cruas -- muito mais rapido que
    # get_all_records() para planilhas grandes (nao ha inferencia de
    # tipo/validacao de cabecalho linha a linha).
    valores = aba.get_all_values()
    if not valores:
        raise ValueError(f"A aba '{worksheet_name}' esta vazia.")

    header, *rows = valores
    header = _dedupe_columns(header)
    df = pd.DataFrame(rows, columns=header)

    if code_col not in df.columns or desc_col not in df.columns:
        raise ValueError(
            f"Colunas '{code_col}'/'{desc_col}' nao encontradas. "
            f"Colunas disponiveis: {list(df.columns)}"
        )

    df = df.rename(columns={code_col: "codigo", desc_col: "descricao"})
    df["_desc_norm"] = df["descricao"].astype(str).str.upper().apply(norm)
    return df
