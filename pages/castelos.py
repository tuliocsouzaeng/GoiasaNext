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

castelos = load_csv("data/castelos.csv.enc", sep=";", encoding="utf-8")
#castelos = pd.read_csv("data/castelos.csv", sep=";", encoding='utf-8')

# _________________________ Aplicação de Filtros _____________________________

# Seção expansível para filtros
with st.expander("Abrir Filtros"):
    setor_selecionado = st.multiselect("Selecione o Setor", castelos["SETOR"].dropna().unique().tolist())
    criticidade_selecionada = st.multiselect("Selecione a Criticidade", castelos["CRITICIDADE"].dropna().unique().tolist())
    modelo_selecionado = st.multiselect("Selecione o Modelo", castelos["TIPO/MODELO"].dropna().unique().tolist())
    equipamento_selecionado = st.multiselect("Selecione o Equipamento", castelos["IDENTIFICAÇÃO"].dropna().unique().tolist())
    TAG_selecionada = st.multiselect("Selecione a TAG", castelos["TAG"].dropna().unique().tolist())
    anofab_selecionado = st.multiselect("Selecione o Ano de Fabricação", castelos["ANO FABR."].dropna().unique().tolist())


# Aplicar os filtros ao DataFrame
castelos_filtradas = castelos.copy()

if setor_selecionado:
    castelos_filtradas = castelos_filtradas[castelos_filtradas["SETOR"].isin(setor_selecionado)]
if criticidade_selecionada:
    castelos_filtradas = castelos_filtradas[castelos_filtradas["CRITICIDADE"].isin(criticidade_selecionada)]
if modelo_selecionado:
    castelos_filtradas = castelos_filtradas[castelos_filtradas["TIPO/MODELO"].isin(modelo_selecionado)]
if equipamento_selecionado:
    castelos_filtradas = castelos_filtradas[castelos_filtradas["IDENTIFICAÇÃO"].isin(equipamento_selecionado)]
if TAG_selecionada:
    castelos_filtradas = castelos_filtradas[castelos_filtradas["TAG"].isin(TAG_selecionada)]
if anofab_selecionado:
    castelos_filtradas = castelos_filtradas[castelos_filtradas["ANO FABR."].isin(anofab_selecionado)]

# _______________ Geração de Informações ________________________

# Calcular o Total de Motores
total_castelos = castelos.shape[0]

# Calcular o Total de Motores Filtrados
total_castelos_filtradas = castelos_filtradas.shape[0]

# Contar a quantidade de equipamentos por setor
castelos_filtradas['SETOR'] = castelos_filtradas['SETOR'].fillna('Desconhecido')
setor_count = castelos_filtradas['SETOR'].value_counts().reset_index()
setor_count.columns = ['SETOR', 'Quantidade']

# Contar a quantidade de equipamentos por criticidade
castelos_filtradas['CRITICIDADE'] = castelos_filtradas['CRITICIDADE'].fillna('Desconhecido')
criticidade_count = castelos_filtradas['CRITICIDADE'].value_counts().reset_index()
criticidade_count.columns = ['CRITICIDADE', 'Quantidade']

# Contar a quantidade de equipamentos por fornecedor
castelos_filtradas['FORNECEDOR'] = castelos_filtradas['FORNECEDOR'].fillna('Desconhecido')
fornecedor_count = castelos_filtradas['FORNECEDOR'].value_counts().reset_index()
fornecedor_count.columns = ['FORNECEDOR', 'Quantidade']

# Contar a quantidade de equipamentos por ANO FABR.
#transmissores_filtrados['ANO FABR.'] = transmissores_filtrados['ANO FABR.'].fillna('Desconhecido')
anofab_count = castelos_filtradas['ANO FABR.'].value_counts(dropna=False).reset_index()
anofab_count.columns = ['ANO FABR.', 'Quantidade']
# Substituir NA por 'Desconhecido' APENAS PARA O GRÁFICO
anofab_count['ANO FABR.'] = anofab_count['ANO FABR.'].astype("string").fillna("Desconhecido")


# _________________ Criação da Página ___________________________
st.title("Castelos")

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

# Linha 6
l6c1 = st.columns(1)[0]

# __________________ Visualização das Informações ______________

# Início Linha 1
with l1c1:
    st.subheader("Métricas")
    st.metric("Total de Equipamentos", total_castelos)

with l1c2:
    # Criar o gráfico de donut
    fig_donut = px.pie(
        names=["Selecionados", "Não Selecionados"],
        values=[total_castelos_filtradas, total_castelos - total_castelos_filtradas],
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

with l2c1:
    if not castelos_filtradas.empty and 'SETOR' in castelos_filtradas.columns:
        # Gráfico de barras para Setor
        fig_setor = px.bar(setor_count, x='SETOR', y='Quantidade',
                          title="Distribuição de Equipamentos por Setor",
                          labels={'SETOR': 'Setor', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='SETOR', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_setor.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}, xaxis_tickangle=45)
        st.plotly_chart(fig_setor)

with l3c1:
    if not castelos_filtradas.empty and 'CRITICIDADE' in castelos_filtradas.columns:
        # Gráfico de barras para Criticidade
        fig_criticidade = px.bar(criticidade_count, x='CRITICIDADE', y='Quantidade',
                          title="Distribuição de Equipamentos por Criticidade",
                          labels={'CRITICIDADE': 'Criticidade', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='CRITICIDADE', color_discrete_sequence=px.colors.qualitative.Set3)
        fig_criticidade.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0})
        st.plotly_chart(fig_criticidade)


with l4c1:
    if not castelos_filtradas.empty and 'FORNECEDOR' in castelos_filtradas.columns:
        # Gráfico de barras para Criticidade
        fig_criticidade = px.bar(fornecedor_count, x='FORNECEDOR', y='Quantidade',
                          title="Distribuição de Equipamentos por Fornecedor",
                          labels={'FORNECEDOR': 'Fornecedor', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='FORNECEDOR', color_discrete_sequence=px.colors.qualitative.Set3)
        fig_criticidade.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 45})
        st.plotly_chart(fig_criticidade)


with l5c1:
    if not castelos_filtradas.empty and 'ANO FABR.' in castelos_filtradas.columns:
        # Gráfico de barras para Setor
        fig_anofab = px.bar(anofab_count, x='ANO FABR.', y='Quantidade',
                          title="Distribuição de Equipamentos por Ano de Fabricação",
                          labels={'ANO FABR.': 'Ano de Fabricação', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='ANO FABR.', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_anofab.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}, xaxis_tickangle=45)
        st.plotly_chart(fig_anofab)

with l6c1:
    with st.expander("Mais Detalhes"):
        st.subheader("Detalhes dos Equipamentos Filtrados")
        st.dataframe(castelos_filtradas, height=400)