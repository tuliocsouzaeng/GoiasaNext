import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

# _________________________ Checa se login foi feito ______________________________

if not st.session_state.get("authenticated", False):
    st.warning("Você precisa fazer login para acessar esta página.")
    st.switch_page("index.py")  # Redireciona para a tela de login


# _________________________ Importação dos Dados ______________________________

valvulas_seg = pd.read_csv("data/valvulas_de_seguranca.csv", sep=";", encoding='utf-8')

# _________________________ Aplicação de Filtros _____________________________

# Seção expansível para filtros

with st.expander("Abrir Filtros"):
    setor_selecionado = st.multiselect("Selecione o Setor", valvulas_seg["SETOR"].dropna().unique().tolist())
    marca_selecionada = st.multiselect("Selecione a Marca", valvulas_seg["MARCA"].dropna().unique().tolist())
    diametro_selecionado = st.multiselect("Selecione o Diâmetro", valvulas_seg["DIÂMETRO"].dropna().unique().tolist())
    pa_selecionada = st.multiselect("Selecione a Pressão de Abertura", valvulas_seg["PRESSÃO DE ABERTURA"].dropna().unique().tolist())
    equipamento_selecionado = st.multiselect("Selecione o Equipamento", valvulas_seg["TAG"].dropna().unique().tolist())
    pmta_selecionada = st.multiselect("Selecione a PMTA", valvulas_seg["PMTA"].dropna().unique().tolist())

# Aplicar os filtros ao DataFrame
valulas_de_seg_filtradas = valvulas_seg.copy()

if setor_selecionado:
    valulas_de_seg_filtradas = valulas_de_seg_filtradas[valulas_de_seg_filtradas["SETOR"].isin(setor_selecionado)]
if diametro_selecionado:
    valulas_de_seg_filtradas = valulas_de_seg_filtradas[valulas_de_seg_filtradas["DIÂMETRO"].isin(diametro_selecionado)]
if pa_selecionada:
    valulas_de_seg_filtradas = valulas_de_seg_filtradas[valulas_de_seg_filtradas["PRESSÃO DE ABERTURA"].isin(pa_selecionada)]
if equipamento_selecionado:
    valulas_de_seg_filtradas = valulas_de_seg_filtradas[valulas_de_seg_filtradas["TAG"].isin(equipamento_selecionado)]
if pmta_selecionada:
    valulas_de_seg_filtradas = valulas_de_seg_filtradas[valulas_de_seg_filtradas["PMTA"].isin(pmta_selecionada)]
if marca_selecionada:
    valulas_de_seg_filtradas = valulas_de_seg_filtradas[valulas_de_seg_filtradas["MARCA"].isin(marca_selecionada)]


# _______________ Geração de Informações ________________________

# Calcular o Total de Válvulas
total_valvulas_seg = valvulas_seg.shape[0]

# Calcular o Total de Válvulas Filtradas
total_valvulas_seg_filtradas = valulas_de_seg_filtradas.shape[0]


# Contar a quantidade de equipamentos por setor
valulas_de_seg_filtradas['SETOR'] = valulas_de_seg_filtradas['SETOR'].fillna('Desconhecido')
setor_count = valulas_de_seg_filtradas['SETOR'].value_counts().reset_index()
setor_count.columns = ['SETOR', 'Quantidade']

# Contar a quantidade de equipamentos por marca
valulas_de_seg_filtradas['MARCA'] = valulas_de_seg_filtradas['MARCA'].fillna('Desconhecido')
marca_count = valulas_de_seg_filtradas['MARCA'].value_counts().reset_index()
marca_count.columns = ['MARCA', 'Quantidade']

# Contar a quantidade de equipamentos por diâmetro
valulas_de_seg_filtradas['DIÂMETRO'] = valulas_de_seg_filtradas['DIÂMETRO'].fillna('Desconhecido')
diametro_count = valulas_de_seg_filtradas['DIÂMETRO'].value_counts().reset_index()
diametro_count.columns = ['DIÂMETRO', 'Quantidade']

# _________________ Criação da Página ___________________________

# Linha 1
l1c1, l1c2 = st.columns(2)

# Linha 2
l2c1 = st.columns(1)[0]

# Linha 3
l3c1 = st.columns(1)[0]

# Linha 4
l4c1 = st.columns(1)[0]


# __________________ Visualização das Informações ______________
# Início Linha 1
with l1c1:
    st.subheader("Métricas")
    st.metric("Total de Equipamentos", total_valvulas_seg)

with l1c2:
    # Criar o gráfico de donut
    fig_donut = px.pie(
        names=["Selecionados", "Não Selecionados"],
        values=[total_valvulas_seg_filtradas, total_valvulas_seg - total_valvulas_seg_filtradas],
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
    if not valulas_de_seg_filtradas.empty and 'SETOR' in valulas_de_seg_filtradas.columns:
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
    if not valulas_de_seg_filtradas.empty and 'MARCA' in valulas_de_seg_filtradas.columns:
        # Gráfico de barras para Criticidade
        fig_criticidade = px.bar(marca_count, x='MARCA', y='Quantidade',
                          title="Distribuição de Equipamentos por Criticidade",
                          labels={'MARCA': 'Marca', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='MARCA', color_discrete_sequence=px.colors.qualitative.Set3)
        fig_criticidade.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 45})
        st.plotly_chart(fig_criticidade)
        
with l4c1:
    if not valulas_de_seg_filtradas.empty and 'DIÂMETRO' in valulas_de_seg_filtradas.columns:
        # Gráfico de barras para Criticidade
        fig_d = px.bar(diametro_count, x='DIÂMETRO', y='Quantidade',
                          title="Distribuição de Equipamentos por Criticidade",
                          labels={'DIÂMETRO': 'Diâmetro', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='DIÂMETRO', color_discrete_sequence=px.colors.qualitative.Set3)
        fig_d.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 45})
        st.plotly_chart(fig_d)

with st.expander("Mais Detalhes"):
    st.subheader("Detalhes dos Equipamentos Filtrados")
    st.dataframe(valulas_de_seg_filtradas, height=400)