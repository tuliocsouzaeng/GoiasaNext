# -*- coding: utf-8 -*-
"""
pages/busca_manual.py
----------------------
Busca manual, progressiva, sobre o catalogo SAP -- para conferencia
humana. O usuario digita um termo, o sistema filtra; digita outro, o
filtro anterior continua valendo e o novo se soma (E logico). Cada
termo pode ser removido individualmente sem apagar os outros.

Reaproveita o MESMO catalogo (mesmo cache) da pagina de correlacao
automatica, via sap_catalog.get_sap_catalog().
"""

from io import BytesIO

import pandas as pd
import streamlit as st

from busca_rapida.matching import norm
from busca_rapida.sap_catalog import get_sap_catalog

# _________________________ Checa se login foi feito ______________________________

if not st.session_state.get("authenticated", False):
    st.warning("Você precisa fazer login para acessar esta página.")
    st.switch_page("index.py")  # Redireciona para a tela de login
# _____________________________________________________________________________

st.set_page_config(page_title="Busca manual - Catalogo SAP", layout="wide")
st.title("Busca manual no catalogo SAP")
st.caption(
    "Digite um termo e aperte Enter para adicionar um filtro. Cada filtro "
    "novo se soma aos anteriores (E logico) -- ex: 'parafuso' + '2\"' mostra "
    "so os itens que tem as duas coisas na descricao."
)

sap_df = get_sap_catalog()

# --------------------------------------------------------------------------
# Estado dos filtros (precisa de session_state -- o Streamlit reexecuta o
# script inteiro a cada interacao, entao sem isso os filtros anteriores
# se perderiam a cada novo termo digitado).
# --------------------------------------------------------------------------

if "filtros_busca_manual" not in st.session_state:
    st.session_state.filtros_busca_manual = []


def _adicionar_filtro():
    termo = st.session_state.get("_novo_filtro_input", "").strip()
    if termo and termo not in st.session_state.filtros_busca_manual:
        st.session_state.filtros_busca_manual.append(termo)
    st.session_state._novo_filtro_input = ""


def _remover_filtro(termo):
    st.session_state.filtros_busca_manual.remove(termo)


def _limpar_filtros():
    st.session_state.filtros_busca_manual = []


# --------------------------------------------------------------------------
# Entrada de novo termo
# --------------------------------------------------------------------------

st.text_input(
    "Novo termo de busca",
    key="_novo_filtro_input",
    placeholder='ex: parafuso, 2", A105...',
    on_change=_adicionar_filtro,
)

# --------------------------------------------------------------------------
# Chips dos filtros ativos (cada um removivel individualmente)
# --------------------------------------------------------------------------

if st.session_state.filtros_busca_manual:
    st.write("**Filtros ativos:**")
    chip_cols = st.columns(len(st.session_state.filtros_busca_manual) + 1)
    for i, termo in enumerate(st.session_state.filtros_busca_manual):
        with chip_cols[i]:
            st.button(
                f"{termo}  ✕",
                key=f"chip_{i}_{termo}",
                on_click=_remover_filtro,
                args=(termo,),
                help="Clique para remover este filtro",
            )
    with chip_cols[-1]:
        st.button("Limpar tudo", on_click=_limpar_filtros, type="secondary")
else:
    st.info("Nenhum filtro ativo -- digite um termo acima para comecar.")

st.divider()

# --------------------------------------------------------------------------
# Aplica os filtros (AND) sobre a coluna normalizada (sem acento/maiuscula)
# --------------------------------------------------------------------------

resultado = sap_df
for termo in st.session_state.filtros_busca_manual:
    termo_norm = norm(termo.upper())
    resultado = resultado[resultado["_desc_norm"].str.contains(termo_norm, regex=False, na=False)]

total = len(resultado)
st.subheader(f"{total:,} resultado(s)".replace(",", "."))

if total == 0 and st.session_state.filtros_busca_manual:
    st.warning("Nenhum material encontrado com esses termos combinados.")
elif total > 0:
    LIMITE_EXIBICAO = 500
    exibir = resultado[["codigo", "descricao"]].rename(
        columns={"codigo": "Código", "descricao": "Descrição"}
    )

    if total > LIMITE_EXIBICAO:
        st.caption(
            f"Mostrando os primeiros {LIMITE_EXIBICAO} de {total} -- "
            "refine a busca com mais um termo para reduzir a lista, "
            "ou baixe o resultado completo em Excel abaixo."
        )
        exibir_mostrada = exibir.head(LIMITE_EXIBICAO)
    else:
        exibir_mostrada = exibir

    evento = st.dataframe(
        exibir_mostrada,
        use_container_width=True,
        height=450,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    linhas_selecionadas = evento.selection["rows"] if evento is not None else []
    if linhas_selecionadas:
        linha = exibir_mostrada.iloc[linhas_selecionadas[0]]
        st.markdown("**Item selecionado:**")
        st.code(str(linha["Codigo"]), language=None)
        st.write(linha["Descricao"])

    # Download do resultado completo (nao so o que esta na tela)
    buffer = BytesIO()
    resultado[["codigo", "descricao"]].rename(
        columns={"codigo": "Codigo", "descricao": "Descricao"}
    ).to_excel(buffer, index=False, engine="openpyxl")
    st.download_button(
        "Baixar resultado filtrado (.xlsx)",
        data=buffer.getvalue(),
        file_name="busca_manual_sap.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
