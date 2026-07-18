# -*- coding: utf-8 -*-
"""
sap_catalog.py
--------------
Ponto unico de carregamento do catalogo SAP, para ser importado por
qualquer pagina do app (busca automatica, busca manual, futuras
paginas). Como o cache do Streamlit (@st.cache_resource) e' associado
a funcao (modulo + nome), todas as paginas que importarem
`get_sap_catalog` daqui compartilham o MESMO catalogo carregado em
memoria -- ele so e' lido do Drive uma vez, mesmo que o usuario
navegue entre paginas diferentes.
"""

import streamlit as st
    
from busca_rapida.sap_loader_gsheets import load_sap_catalog_from_sheets
# from sap_loader_drive_xlsx import load_sap_catalog_from_drive_xlsx  # alternativa


SAP_SHEET_KEY = "17XBKbKa02MtUlVOYOCxA2to9SOsZyoyunQ9IAnXJSYY"
SAP_WORKSHEET_NAME = "QConsulta"

@st.cache_resource(show_spinner="Carregando catalogo SAP do Drive...")
def get_sap_catalog():
    creds = os.getenv("GOOGLE_REDE_CREDS")
    return load_sap_catalog_from_sheets(
        creds=creds,
        sheet_key=SAP_SHEET_KEY,
        worksheet_name=SAP_WORKSHEET_NAME,
    )
