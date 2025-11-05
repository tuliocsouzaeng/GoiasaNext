import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

# _________________________ Checa se login foi feito ______________________________

if not st.session_state.get("authenticated", False):
    st.warning("Você precisa fazer login para acessar esta página.")
    st.switch_page("index.py")  # Redireciona para a tela de login



# _________________________ Importação dos Dados ______________________________

tanques = pd.read_csv("data/tanques.csv", sep=";", encoding='utf-8')

# _________________________ Aplicação de Filtros _____________________________

# Seção expansível para filtros
with st.expander("Abrir Filtros"):
    setor_selecionado = st.multiselect("Selecione o Setor", tanques["SETOR"].dropna().unique().tolist())
    material_selecionado = st.multiselect("Selecione o Material", tanques["MATERIAL"].dropna().unique().tolist())
    criticidade_selecionada = st.multiselect("Selecione a Criticidade", tanques["CRITICIDADE"].dropna().unique().tolist())
    equipamento_selecionado = st.multiselect("Selecione o Equipamento", tanques["TAG"].dropna().unique().tolist())
    nr13_selecionada = st.multiselect("Equipamento enquadra na NR-13?", tanques["NR-13"].dropna().unique().tolist())

# Aplicar os filtros ao DataFrame
tanques_filtrados = tanques.copy()

if setor_selecionado:
    tanques_filtrados = tanques_filtrados[tanques_filtrados["SETOR"].isin(setor_selecionado)]
if material_selecionado:
    tanques_filtrados = tanques_filtrados[tanques_filtrados["MATERIAL"].isin(material_selecionado)]
if criticidade_selecionada:
    tanques_filtrados = tanques_filtrados[tanques_filtrados["CRITICIDADE"].isin(criticidade_selecionada)]
if equipamento_selecionado:
    tanques_filtrados = tanques_filtrados[tanques_filtrados["TAG"].isin(equipamento_selecionado)]
if nr13_selecionada:
    tanques_filtrados = tanques_filtrados[tanques_filtrados["NR-13"].isin(nr13_selecionada)]


# _______________ Geração de Informações ________________________

# Calcular o Total de Tanques
total_tanques = tanques.shape[0]

# Calcular o Total de Tanques Filtrados
total_tanques_filtrados = tanques_filtrados.shape[0]

# Contar a quantidade de equipamentos por setor
tanques_filtrados['SETOR'] = tanques_filtrados['SETOR'].fillna('Desconhecido')
setor_count = tanques_filtrados['SETOR'].value_counts().reset_index()
setor_count.columns = ['SETOR', 'Quantidade']

# Contar a quantidade de equipamentos por criticidade
tanques_filtrados['CRITICIDADE'] = tanques_filtrados['CRITICIDADE'].fillna('Desconhecido')
criticidade_count = tanques_filtrados['CRITICIDADE'].value_counts().reset_index()
criticidade_count.columns = ['CRITICIDADE', 'Quantidade']

# Contar a quantidade de equipamentos por material
tanques_filtrados['MATERIAL'] = tanques_filtrados['MATERIAL'].fillna('Desconhecido')
material_count = tanques_filtrados['MATERIAL'].value_counts().reset_index()
material_count.columns = ['MATERIAL', 'Quantidade']

# _________________ Criação da Página ___________________________
st.title("Tanques")

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
    st.metric("Total de Equipamentos", total_tanques)

with l1c2:
    # Criar o gráfico de donut
    fig_donut = px.pie(
        names=["Selecionados", "Não Selecionados"],
        values=[total_tanques_filtrados, total_tanques - total_tanques_filtrados],
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
    if not tanques_filtrados.empty and 'SETOR' in tanques_filtrados.columns:
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
    if not tanques_filtrados.empty and 'CRITICIDADE' in tanques_filtrados.columns:
        # Gráfico de barras para Criticidade
        fig_criticidade = px.bar(criticidade_count, x='CRITICIDADE', y='Quantidade',
                          title="Distribuição de Equipamentos por Criticidade",
                          labels={'CRITICIDADE': 'Criticidade', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='CRITICIDADE', color_discrete_sequence=px.colors.qualitative.Set3)
        fig_criticidade.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0})
        st.plotly_chart(fig_criticidade)

# Linha 4
with l4c1:
    if not tanques_filtrados.empty and 'MATERIAL' in tanques_filtrados.columns:
        # Gráfico de barras para Criticidade
        fig_material = px.bar(material_count, x='MATERIAL', y='Quantidade',
                          title="Distribuição de Equipamentos por Criticidade",
                          labels={'MATERIAL': 'Material', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='MATERIAL', color_discrete_sequence=px.colors.qualitative.Set2)
        fig_material.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0})
        st.plotly_chart(fig_material)


# Linha 5
with l5c1:
    with st.expander("Mais Detalhes"):
        st.subheader("Detalhes dos Equipamentos Filtrados")
        st.dataframe(tanques_filtrados, height=400)