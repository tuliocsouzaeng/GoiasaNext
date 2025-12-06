import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from utils.data_loader import load_csv


# _________________________ Checa se login foi feito ______________________________

if not st.session_state.get("authenticated", False):
    st.warning("Você precisa fazer login para acessar esta página.")
    st.switch_page("index.py")  # Redireciona para a tela de login

# _________________________ Importação dos Dados ______________________________

#transmissores = pd.read_csv("data/transmissores.csv", sep=";", encoding="utf-8")
transmissores = load_csv("data/transmissores.csv.enc", sep=";", encoding="utf-8")

transmissores["ANO FABR."] = (
    pd.to_numeric(transmissores["ANO FABR."], errors="coerce")
    .astype("Int64")
)

# _________________________ Aplicação de Filtros _____________________________

# Seção expansível para filtros
with st.expander("Abrir Filtros"):
    setor_selecionado = st.multiselect("Selecione o Setor", transmissores["SETOR"].dropna().unique().tolist())
    fornecedor_selecionado = st.multiselect("Selecione o Fornecedor", transmissores["FORNECEDOR"].dropna().unique().tolist())
    #criticidade_selecionada = st.multiselect("Selecione a Criticidade", tanques["CRITICIDADE"].dropna().unique().tolist())
    equipamento_selecionado = st.multiselect("Selecione o Equipamento", transmissores["TAG"].dropna().unique().tolist())
    modelo_selecionado = st.multiselect("Selecione o Modelo", transmissores["TIPO/MODELO"].dropna().unique().tolist())
    descricao_selecionada = st.multiselect("Selecione a Descrição", transmissores["DESCRICAO"].dropna().unique().tolist())
    anofab_selecionado = st.multiselect("Selecione o Ano de Fabricação", transmissores["ANO FABR."].dropna().unique().tolist())

# Aplicar os filtros ao DataFrame
transmissores_filtrados = transmissores.copy()

if setor_selecionado:
    transmissores_filtrados = transmissores_filtrados[transmissores_filtrados["SETOR"].isin(setor_selecionado)]
if fornecedor_selecionado:
    transmissores_filtrados = transmissores_filtrados[transmissores_filtrados["FORNECEDOR"].isin(fornecedor_selecionado)]
if equipamento_selecionado:
    transmissores_filtrados = transmissores_filtrados[transmissores_filtrados["TAG"].isin(equipamento_selecionado)]
if modelo_selecionado:
    transmissores_filtrados = transmissores_filtrados[transmissores_filtrados["TIPO/MODELO"].isin(modelo_selecionado)]
if descricao_selecionada:
    transmissores_filtrados = transmissores_filtrados[transmissores_filtrados["DESCRICAO"].isin(descricao_selecionada)]
if anofab_selecionado:
    transmissores_filtrados = transmissores_filtrados[transmissores_filtrados["ANO FABR."].isin(anofab_selecionado)]


# _______________ Geração de Informações ________________________

# Remove duplicatas por TAG (mantém a primeira ocorrência de cada TAG)
transmissores_unicos = transmissores_filtrados.drop_duplicates(subset='TAG')

# Calcular o Total de Transmissores
total_transmissores = transmissores["TAG"].nunique()

# Calcular o Total de Transmissores Filtrados
total_transmissores_filtrados = transmissores_filtrados["TAG"].nunique()

# Contar a quantidade de equipamentos por setor
transmissores_filtrados['SETOR'] = transmissores_filtrados['SETOR'].fillna('Desconhecido')
setor_count = transmissores_filtrados['SETOR'].value_counts().reset_index()
setor_count.columns = ['SETOR', 'Quantidade']


# Contar a quantidade de equipamentos por Fornecedor
transmissores_filtrados['FORNECEDOR'] = transmissores_filtrados['FORNECEDOR'].fillna('Desconhecido')
fornecedor_count = transmissores_filtrados['FORNECEDOR'].value_counts().reset_index()
fornecedor_count.columns = ['FORNECEDOR', 'Quantidade']

# Contar a quantidade de equipamentos por Tipo/Modelo
transmissores_filtrados['TIPO/MODELO'] = transmissores_filtrados['TIPO/MODELO'].fillna('Desconhecido')
modelo_count = transmissores_filtrados['TIPO/MODELO'].value_counts().reset_index()
modelo_count.columns = ['TIPO/MODELO', 'Quantidade']

# Contar a quantidade de equipamentos por ANO FABR.
#transmissores_filtrados['ANO FABR.'] = transmissores_filtrados['ANO FABR.'].fillna('Desconhecido')
anofab_count = transmissores_filtrados['ANO FABR.'].value_counts(dropna=False).reset_index()
anofab_count.columns = ['ANO FABR.', 'Quantidade']
# Substituir NA por 'Desconhecido' APENAS PARA O GRÁFICO
anofab_count['ANO FABR.'] = anofab_count['ANO FABR.'].astype("string").fillna("Desconhecido")

# _________________ Criação da Página ___________________________

# Linha 1
l1c1, l1c2 = st.columns(2)

# Linha 2
l2c1 = st.columns(1)[0]

# Linha 3
l3c1, l3c2 = st.columns(2)

# Linha 4
l4c1 = st.columns(1)[0]

# Linha 5
l5c1 = st.columns(1)[0]

# __________________ Visualização das Informações ______________
# Início Linha 1
with l1c1:
    st.subheader("Métricas")
    st.metric("Total de Equipamentos", total_transmissores)

with l1c2:
    # Criar o gráfico de donut
    fig_donut = px.pie(
        names=["Selecionados", "Não Selecionados"],
        values=[total_transmissores_filtrados, total_transmissores - total_transmissores_filtrados],
        #title="Percentual de Equipamentos Selecionados",
        hole=0.7,  # Criando o buraco no centro (donut)
        color_discrete_sequence=["#A5D6A7","#2E7D32"],  # Cor para 'Filtrados' e 'Não Filtrados'
    )

    fig_donut.update_layout(
        width = 300,  # Ajuste o tamanho conforme necessário
        height = 300,  # Ajuste o tamanho conforme necessário
    )

    # Exibir o gráfico
    st.plotly_chart(fig_donut)

# Linha 2
with l2c1:
    if not transmissores_filtrados.empty and 'SETOR' in transmissores_filtrados.columns:
        # Gráfico de barras para Setor
        fig_setor = px.bar(setor_count, x='SETOR', y='Quantidade',
                          title="Distribuição de Equipamentos por Setor",
                          labels={'SETOR': 'Setor', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='SETOR', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_setor.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}, xaxis_tickangle=45)
        st.plotly_chart(fig_setor)

with l3c1:
    if not transmissores_filtrados.empty and 'FORNECEDOR' in transmissores_filtrados.columns:
        # Gráfico de barras para Setor
        fig_fornecedor = px.bar(fornecedor_count, x='FORNECEDOR', y='Quantidade',
                          title="Distribuição de Equipamentos por Fornecedor",
                          labels={'FORNECEDOR': 'Fornecedor', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='FORNECEDOR', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_fornecedor.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}, xaxis_tickangle=45)
        st.plotly_chart(fig_fornecedor)

with l3c2:
    if not transmissores_filtrados.empty and 'TIPO/MODELO' in transmissores_filtrados.columns:
        # Gráfico de barras para Setor
        fig_modelo = px.bar(modelo_count, x='TIPO/MODELO', y='Quantidade',
                          title="Distribuição de Equipamentos por Modelo",
                          labels={'TIPO/MODELO': 'Modelo', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='TIPO/MODELO', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_modelo.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}, xaxis_tickangle=45)
        st.plotly_chart(fig_modelo)

with l4c1:
    if not transmissores_filtrados.empty and 'ANO FABR.' in transmissores_filtrados.columns:
        # Gráfico de barras para Setor
        fig_anofab = px.bar(anofab_count, x='ANO FABR.', y='Quantidade',
                          title="Distribuição de Equipamentos por Ano de Fabricação",
                          labels={'ANO FABR.': 'Ano de Fabricação', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='ANO FABR.', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_anofab.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}, xaxis_tickangle=45)
        st.plotly_chart(fig_anofab)

with l5c1:
    with st.expander("Mais Detalhes"):
        st.subheader("Detalhes dos Equipamentos Filtrados")
        st.dataframe(transmissores_filtrados, height=400)