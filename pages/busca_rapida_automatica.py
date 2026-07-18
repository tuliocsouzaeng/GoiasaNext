# -*- coding: utf-8 -*-
"""
app.py
------
Exemplo de app Streamlit integrando:
  - matching.py (motor multi-categoria)
  - purchase_parser.py (upload da lista de compra)
  - sap_loader_gsheets.py (catalogo SAP vindo do Google Drive/Sheets)

Adapte nomes/paths/secrets ao seu projeto real.
"""

from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from busca_rapida.matching import CATEGORY_REGISTRY, match_items
from busca_rapida.purchase_parser import parse_excel_or_csv, parse_pdf
from busca_rapida.sap_catalog import get_sap_catalog

# _________________________ Checa se login foi feito ______________________________

if not st.session_state.get("authenticated", False):
    st.warning("Você precisa fazer login para acessar esta página.")
    st.switch_page("index.py")  # Redireciona para a tela de login
# _________________ #

st.set_page_config(page_title="Correlacao de Materiais SAP", layout="wide")
st.title("Correlacao de materiais a comprar x cadastro SAP")

# --------------------------------------------------------------------------
# 1) Catalogo SAP -- carregado 1x (modulo sap_catalog.py) e reaproveitado
#    por todas as paginas do app, incluindo a busca manual.
# --------------------------------------------------------------------------

col_a, col_b = st.columns([3, 1])
with col_b:
    if st.button("Atualizar catalogo SAP"):
        get_sap_catalog.clear()  # limpa o cache_resource e forca reload

sap_df = get_sap_catalog()
st.caption(f"Catalogo SAP carregado: {len(sap_df):,} materiais.".replace(",", "."))

# --------------------------------------------------------------------------
# 2) Escolha da categoria + upload da lista de compra
# --------------------------------------------------------------------------

categoria = st.selectbox(
    "Categoria do material",
    options=["auto"] + list(CATEGORY_REGISTRY.keys()),
    format_func=lambda k: {
        "auto": "Detectar automaticamente (recomendado p/ listas mistas)",
        "tubulacao": "Forcar: Tubulacao (tubos, conexoes, flanges, juntas)",
        "estrutura_metalica": "Forcar: Estrutura metalica (perfis, chapas, cantoneiras)",
        "equipamentos": "Forcar: Equipamentos (bombas, redutores, motores)",
    }.get(k, k),
)

if categoria in ("estrutura_metalica", "equipamentos"):
    st.warning(
        "Esta categoria ainda esta em fase de ajuste (os extratores foram "
        "escritos sem uma amostra real do SAP para essa familia de "
        "materiais). Trate as sugestoes com cautela extra ate validarmos "
        "com dados reais."
    )

uploaded = st.file_uploader(
    "Lista de materiais a comprar (Excel/CSV recomendado; PDF suportado com layout fixo)",
    type=["xlsx", "csv", "pdf"],
)

if uploaded is not None:
    if uploaded.name.lower().endswith(".pdf"):
        purchase_items = parse_pdf(uploaded)
    else:
        purchase_items = parse_excel_or_csv(uploaded)

    st.success(f"{len(purchase_items)} itens lidos da lista de compra.")

    with st.spinner("Correlacionando com o catalogo SAP..."):
        result_df = match_items(purchase_items, sap_df, category=categoria)

    if categoria == "auto":
        rascunho = result_df[result_df["Categoria"].isin(["estrutura_metalica", "equipamentos"])]
        if not rascunho.empty:
            st.warning(
                f"{len(rascunho)} item(ns) foram classificados automaticamente em "
                "categorias ainda em ajuste (estrutura metalica / equipamentos). "
                "Revise essas linhas com atencao extra."
            )
        nao_identificados = result_df[result_df["Categoria"] == "Nao identificada"]
        if not nao_identificados.empty:
            st.info(
                f"{len(nao_identificados)} item(ns) nao tiveram o tipo de peca "
                "reconhecido por nenhum perfil e foram marcados para classificacao manual."
            )

    # ---------------------------------------------------------------------
    # 3) Resumo visual
    # ---------------------------------------------------------------------
    order = ["Alta", "Media", "Baixa", "Criar Material"]

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Itens totais", len(result_df))
        st.metric(
            "Precisam de material novo",
            int((result_df["Confianca"] == "Criar Material").sum()),
        )

    with col2:
        counts = result_df["Confianca"].value_counts().reindex(order, fill_value=0).reset_index()
        counts.columns = ["Confianca", "Quantidade"]
        color_map = {
            "Alta": "#4CAF50", "Media": "#FFA726",
            "Baixa": "#EF5350", "Criar Material": "#9E9E9E",
        }
        fig = px.bar(
            counts, x="Confianca", y="Quantidade", color="Confianca",
            color_discrete_map=color_map, text="Quantidade",
        )
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------------------
    # 4) Tabela filtravel
    # ---------------------------------------------------------------------
    filtro = st.multiselect("Filtrar por confianca", options=order, default=order)
    st.dataframe(
        result_df[result_df["Confianca"].isin(filtro)],
        use_container_width=True,
        height=500,
    )

    # ---------------------------------------------------------------------
    # 5) Download do resultado
    # ---------------------------------------------------------------------
    buffer = BytesIO()
    result_df.to_excel(buffer, index=False, engine="openpyxl")
    st.download_button(
        "Baixar planilha de correlacao (.xlsx)",
        data=buffer.getvalue(),
        file_name=f"correlacao_materiais_sap_{categoria}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("Envie a lista de materiais para iniciar a correlacao.")
