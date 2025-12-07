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

#motores = pd.read_csv("data/motores.csv", sep=";", encoding='utf-8')
motores = load_csv("data/motores.csv.enc", sep=";", encoding='utf-8')

# _________________________ Aplicação de Filtros _____________________________

# Seção expansível para filtros
with st.expander("Abrir Filtros"):
    setor_selecionado = st.multiselect("Selecione o Setor", motores["SETOR"].dropna().unique().tolist())
    ccm_selecionado = st.multiselect("Selecione o CCM", motores["CCM"].dropna().unique().tolist())
    acionamento_selecionado = st.multiselect("Selecione o Acionamento", motores["ACIONAMENTO"].dropna().unique().tolist())
    nump_selecionado = st.multiselect("Selecione o Número de Polos", motores["Nº PÓLOS"].dropna().unique().tolist())

# Aplicar os filtros ao DataFrame
motores_filtrados = motores.copy()

if setor_selecionado:
    motores_filtrados = motores_filtrados[motores_filtrados["SETOR"].isin(setor_selecionado)]
if ccm_selecionado:
    motores_filtrados = motores_filtrados[motores_filtrados["CCM"].isin(ccm_selecionado)]
if acionamento_selecionado:
    motores_filtrados = motores_filtrados[motores_filtrados["ACIONAMENTO"].isin(acionamento_selecionado)]
if nump_selecionado:
    motores_filtrados = motores_filtrados[motores_filtrados["Nº PÓLOS"].isin(nump_selecionado)]

# _______________ Geração de Informações ________________________

# Calcular o Total de Motores
total_motores = motores.shape[0]

# Calcular o Total de Motores Filtrados
total_motores_filtrados = motores_filtrados.shape[0]

# Contar a quantidade de equipamentos por setor
motores_filtrados['SETOR'] = motores_filtrados['SETOR'].fillna('Desconhecido')
setor_count = motores_filtrados['SETOR'].value_counts().reset_index()
setor_count.columns = ['SETOR', 'Quantidade']

# Contar a quantidade de equipamentos por CCM
motores_filtrados['CCM'] = motores_filtrados['CCM'].fillna('Desconhecido')
ccm_count = motores_filtrados['CCM'].value_counts().reset_index()
ccm_count.columns = ['CCM', 'Quantidade']

# Contar a quantidade de equipamentos por Acionamento
motores_filtrados['ACIONAMENTO'] = motores_filtrados['ACIONAMENTO'].fillna('Desconhecido')
acionamento_count = motores_filtrados['ACIONAMENTO'].value_counts().reset_index()
acionamento_count.columns = ['ACIONAMENTO', 'Quantidade']


# _________________ Criação da Página ___________________________
st.title("Motores de Baixa Tensão")

# Linha 1
l1c1, l1c2 = st.columns(2)

# Linha 2
l2c1 = st.columns(1)[0]

# Linha 3
l3c1 = st.columns(1)[0]

# Linha 4
l4c1 = st.columns(1)[0]

# Linha 5
l5c1 = st.columns(1)[0]


# __________________ Visualização das Informações ______________

# Início Linha 1
with l1c1:
    st.subheader("Métricas")
    st.metric("Total de Equipamentos", total_motores)

with l1c2:
    # Criar o gráfico de donut
    fig_donut = px.pie(
        names=["Selecionados", "Não Selecionados"],
        values=[total_motores_filtrados, total_motores - total_motores_filtrados],
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
    st.subheader("Visualização")
    if not motores_filtrados.empty and 'SETOR' in motores_filtrados.columns:
        # Gráfico de barras para Setor
        fig_setor = px.bar(setor_count, x='SETOR', y='Quantidade',
                          title="Distribuição de Equipamentos por Setor",
                          labels={'SETOR': 'Setor', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='SETOR', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_setor.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}, xaxis_tickangle=45)
        st.plotly_chart(fig_setor)

# Linha 3
with l3c1:
    if not motores_filtrados.empty and 'CCM' in motores_filtrados.columns:
        # Gráfico de barras para Setor
        fig_setor = px.bar(ccm_count, x='CCM', y='Quantidade',
                          title="Distribuição de Equipamentos por CCM",
                          labels={'CCM': 'CCM', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='CCM', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_setor.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}, xaxis_tickangle=45)
        st.plotly_chart(fig_setor)

# Linha 4
with l4c1:
    if not motores_filtrados.empty and 'ACIONAMENTO' in motores_filtrados.columns:
        # Gráfico de barras para Setor
        fig_setor = px.bar(acionamento_count, x='ACIONAMENTO', y='Quantidade',
                          title="Distribuição de Equipamentos por Acionamento",
                          labels={'ACIONAMENTO': 'Acionamento', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='ACIONAMENTO', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_setor.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}, xaxis_tickangle=45)
        st.plotly_chart(fig_setor)


with l5c1:
    with st.expander("Mais Detalhes"):
        st.subheader("Detalhes dos Equipamentos Filtrados")
        st.dataframe(motores_filtrados, height=400)
