# -*- coding: utf-8 -*-
"""
pages/busca_manual.py
----------------------
Busca manual, progressiva, sobre o catalogo SAP -- para conferencia
humana. Cada termo digitado no multiselect vira um filtro que se soma
aos anteriores (E logico); cada um pode ser removido individualmente
clicando no "x" do proprio chip.

Reaproveita o MESMO catalogo (mesmo cache) da pagina de correlacao
automatica, via sap_catalog.get_sap_catalog().

Observacao: accept_new_options exige Streamlit >= 1.45 aprox. Se a sua
versao instalada for anterior a isso, veja o comentario no final do
arquivo com a alternativa (text_input + chips manuais).
"""

from io import BytesIO

import re

import streamlit as st

from busca_rapida.matching import norm
from busca_rapida.sap_catalog import get_sap_catalog

st.set_page_config(page_title="Busca manual - Catálogo SAP", layout="wide")
st.title("Busca manual no catálogo SAP")

st.caption(
    "Digite um termo e aperte Enter para adicionar um filtro. Cada filtro "
    "novo se soma aos anteriores (E logico) -- ex: 'parafuso' + '2\"' mostra "
    "so os itens que tem as duas coisas na descrição. Clique no 'x' de um "
    "filtro para removê-lo sem afetar os demais.\n\n"
    "Dentro de UM filtro, separe alternativas com vírgula, ';', 'ou' ou '|' "
    "para um OU -- ex: o filtro `tubo ou tubulacao` acha qualquer um dos "
    "dois; combinado com outro filtro `P11, P22, 10\"` (que também é um OU "
    "entre si), o resultado final é (tubo OU tubulação) E (P11 OU P22 OU 10\")."
)

sap_df = get_sap_catalog()

# --------------------------------------------------------------------------
# Entrada dos filtros: multiselect com accept_new_options=True funciona como
# um campo de "tags" -- cada termo novo digitado + Enter vira um chip
# removivel individualmente, sem precisar simular isso na mao.
# --------------------------------------------------------------------------

filtros = st.multiselect(
    "Termos de busca",
    options=[],
    accept_new_options=True,
    max_selections=8,
    placeholder='Digite um termo e aperte Enter (ex: parafuso, 2", A105...)',
    key="filtros_busca_manual",
)

st.divider()

# --------------------------------------------------------------------------
# Aplica os filtros. Dentro de cada filtro, as alternativas separadas por
# virgula/;/ou/| formam um OU (regex de alternancia); entre filtros
# diferentes continua sendo E (cada um filtra o resultado do anterior).
# --------------------------------------------------------------------------

_SEPARADOR_ALTERNATIVAS = re.compile(r"\s*(?:,|;|\bou\b|\|)\s*", re.IGNORECASE)


def _construir_regex_alternativas(termo: str) -> str:
    alternativas = [a.strip() for a in _SEPARADOR_ALTERNATIVAS.split(termo) if a.strip()]
    alternativas_norm = [re.escape(norm(a.upper())) for a in alternativas]
    return "|".join(alternativas_norm)


resultado = sap_df
for termo in filtros:
    padrao = _construir_regex_alternativas(termo)
    if padrao:
        resultado = resultado[resultado["_desc_norm"].str.contains(padrao, regex=True, na=False)]

total = len(resultado)

if not filtros:
    st.caption(
        f"Nenhum filtro ativo -- mostrando todo o catalogo ({total:,} "
        "materiais). Digite um termo acima para restringir.".replace(",", ".")
    )

st.subheader(f"{total:,} resultado(s)".replace(",", "."))

if total == 0:
    st.warning("Nenhum material encontrado com esses termos combinados.")
else:
    LIMITE_EXIBICAO = 500
    exibir = resultado[["codigo", "descricao"]].rename(
        columns={"codigo": "Codigo", "descricao": "Descricao"}
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

# --------------------------------------------------------------------------
# Alternativa caso sua versao do Streamlit seja anterior a accept_new_options
# (aprox. < 1.45): trocar o bloco do multiselect acima por um text_input +
# lista em session_state, adicionando um termo por vez com on_change e
# removendo individualmente com um st.button por chip. Essa foi a versao
# original desta pagina antes desta atualizacao -- me avise se precisar
# dela de volta.
# --------------------------------------------------------------------------
