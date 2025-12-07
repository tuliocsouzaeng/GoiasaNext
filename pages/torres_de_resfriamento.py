import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from utils.data_loader import load_csv

if not st.session_state.get("authenticated", False):
    st.warning("Você precisa fazer login para acessar esta página.")
    st.switch_page("index.py")  # Redireciona para a tela de login

    
# _________________________ Importação dos Dados ______________________________

#torres_de_resfriamento = pd.read_csv("data/torres_de_resfriamento.csv", sep=";", encoding='utf-8')
torres_de_resfriamento = load_csv("data/torres_de_resfriamento.csv.enc", sep=";", encoding='utf-8')

# _________________________ Aplicação de Filtros _____________________________
# Seção expansível para filtros
with st.expander("Abrir Filtros"):
    setor_selecionado = st.multiselect("Selecione o Setor", torres_de_resfriamento["SETOR"].dropna().unique().tolist())
    criticidade_selecionada = st.multiselect("Selecione a Criticidade", torres_de_resfriamento["CRITICIDADE"].dropna().unique().tolist())
    TAG_selecionada = st.multiselect("Selecione a TAG", torres_de_resfriamento["TAG"].dropna().unique().tolist())
    identificacao_selecionada = st.multiselect("Selecione a descrição", torres_de_resfriamento["IDENTIFICAÇÃO"].dropna().unique().tolist())


# Aplicar os filtros ao DataFrame
torres_resf_filtradas = torres_de_resfriamento.copy()

if setor_selecionado:
    torres_resf_filtradas = torres_resf_filtradas[torres_resf_filtradas["SETOR"].isin(setor_selecionado)]
if criticidade_selecionada:
    torres_resf_filtradas = torres_resf_filtradas[torres_resf_filtradas["CRITICIDADE"].isin(criticidade_selecionada)]
if TAG_selecionada:
    torres_resf_filtradas = torres_resf_filtradas[torres_resf_filtradas["TAG"].isin(TAG_selecionada)]
if identificacao_selecionada:
    torres_resf_filtradas = torres_resf_filtradas[torres_resf_filtradas["IDENTIFICAÇÃO"].isin(identificacao_selecionada)]


# _______________ Geração de Informações ________________________

# Calcular o Total de Torres
total_torres = torres_de_resfriamento.shape[0]

# Calcular o Total de Torres Filtradas
total_torres_filtradas = torres_resf_filtradas.shape[0]

# Contar a quantidade de equipamentos por setor
torres_resf_filtradas['SETOR'] = torres_resf_filtradas['SETOR'].fillna('Desconhecido')
setor_count = torres_resf_filtradas['SETOR'].value_counts().reset_index()
setor_count.columns = ['SETOR', 'Quantidade']

# Contar a quantidade de equipamentos por criticidade
torres_resf_filtradas['CRITICIDADE'] = torres_resf_filtradas['CRITICIDADE'].fillna('Desconhecido')
criticidade_count = torres_resf_filtradas['CRITICIDADE'].value_counts().reset_index()
criticidade_count.columns = ['CRITICIDADE', 'Quantidade']

# _________________ Criação da Página ___________________________

# Linha 1
l1c1, l1c2 = st.columns(2)

# Linha 2
l2c1, l2c2 = st.columns(2)



# __________________ Visualização das Informações ______________
# Início Linha 1
with l1c1:
    st.subheader("Métricas")
    st.metric("Total de Equipamentos", total_torres)

with l1c2:
    # Criar o gráfico de donut
    fig_donut = px.pie(
        names=["Selecionados", "Não Selecionados"],
        values=[total_torres_filtradas, total_torres - total_torres_filtradas],
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
    if not torres_resf_filtradas.empty and 'SETOR' in torres_resf_filtradas.columns:
        # Gráfico de barras para Setor
        fig_setor = px.bar(setor_count, x='SETOR', y='Quantidade',
                          title="Distribuição de Equipamentos por Setor",
                          labels={'SETOR': 'Setor', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='SETOR', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_setor.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}, xaxis_tickangle=45)
        st.plotly_chart(fig_setor)

# Linha 3
with l2c2:
    if not torres_resf_filtradas.empty and 'CRITICIDADE' in torres_resf_filtradas.columns:
        # Gráfico de barras para Criticidade
        fig_criticidade = px.bar(criticidade_count, x='CRITICIDADE', y='Quantidade',
                          title="Distribuição de Equipamentos por Criticidade",
                          labels={'CRITICIDADE': 'Criticidade', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='CRITICIDADE', color_discrete_sequence=px.colors.qualitative.Set3)
        fig_criticidade.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0})
        st.plotly_chart(fig_criticidade)


with st.expander("Mais Detalhes"):
    st.subheader("Detalhes dos Equipamentos Filtrados")
    st.dataframe(torres_resf_filtradas, height=400)
