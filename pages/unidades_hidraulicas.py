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

unidades_hidraulicas = load_csv("data/unidades_hidraulicas.csv.enc", sep=";", encoding="utf-8")
#unidades_hidraulicas = pd.read_csv("data/unidades_hidraulicas.csv", sep=";", encoding='utf-8')

# _________________________ Aplicação de Filtros _____________________________

# Seção expansível para filtros
with st.expander("Abrir Filtros"):
    setor_selecionado = st.multiselect("Selecione o Setor", unidades_hidraulicas["SETOR"].dropna().unique().tolist())
    criticidade_selecionada = st.multiselect("Selecione a Criticidade", unidades_hidraulicas["CRITICIDADE"].dropna().unique().tolist())
    modelo_selecionado = st.multiselect("Selecione o Modelo", unidades_hidraulicas["TIPO/MODELO"].dropna().unique().tolist())
    equipamento_selecionado = st.multiselect("Selecione o Equipamento", unidades_hidraulicas["IDENTIFICAÇÃO"].dropna().unique().tolist())
    TAG_selecionada = st.multiselect("Selecione a TAG", unidades_hidraulicas["TAG"].dropna().unique().tolist())
    anofab_selecionado = st.multiselect("Selecione o Ano de Fabricação", unidades_hidraulicas["ANO FABR."].dropna().unique().tolist())


# Aplicar os filtros ao DataFrame
unidades_hidraulicas_filtradas = unidades_hidraulicas.copy()

if setor_selecionado:
    unidades_hidraulicas_filtradas = unidades_hidraulicas_filtradas[unidades_hidraulicas_filtradas["SETOR"].isin(setor_selecionado)]
if criticidade_selecionada:
    unidades_hidraulicas_filtradas = unidades_hidraulicas_filtradas[unidades_hidraulicas_filtradas["CRITICIDADE"].isin(criticidade_selecionada)]
if modelo_selecionado:
    unidades_hidraulicas_filtradas = unidades_hidraulicas_filtradas[unidades_hidraulicas_filtradas["TIPO/MODELO"].isin(modelo_selecionado)]
if equipamento_selecionado:
    unidades_hidraulicas_filtradas = unidades_hidraulicas_filtradas[unidades_hidraulicas_filtradas["IDENTIFICAÇÃO"].isin(equipamento_selecionado)]
if TAG_selecionada:
    unidades_hidraulicas_filtradas = unidades_hidraulicas_filtradas[unidades_hidraulicas_filtradas["TAG"].isin(TAG_selecionada)]
if anofab_selecionado:
    unidades_hidraulicas_filtradas = unidades_hidraulicas_filtradas[unidades_hidraulicas_filtradas["ANO FABR."].isin(anofab_selecionado)]

# _______________ Geração de Informações ________________________

# Calcular o Total de Motores
total_unidades_hidraulicas = unidades_hidraulicas.shape[0]

# Calcular o Total de Motores Filtrados
total_unidades_hidraulicas_filtradas = unidades_hidraulicas_filtradas.shape[0]

# Contar a quantidade de equipamentos por setor
unidades_hidraulicas_filtradas['SETOR'] = unidades_hidraulicas_filtradas['SETOR'].fillna('Desconhecido')
setor_count = unidades_hidraulicas_filtradas['SETOR'].value_counts().reset_index()
setor_count.columns = ['SETOR', 'Quantidade']

# Contar a quantidade de equipamentos por criticidade
unidades_hidraulicas_filtradas['CRITICIDADE'] = unidades_hidraulicas_filtradas['CRITICIDADE'].fillna('Desconhecido')
criticidade_count = unidades_hidraulicas_filtradas['CRITICIDADE'].value_counts().reset_index()
criticidade_count.columns = ['CRITICIDADE', 'Quantidade']

# Contar a quantidade de equipamentos por fornecedor
unidades_hidraulicas_filtradas['FORNECEDOR'] = unidades_hidraulicas_filtradas['FORNECEDOR'].fillna('Desconhecido')
fornecedor_count = unidades_hidraulicas_filtradas['FORNECEDOR'].value_counts().reset_index()
fornecedor_count.columns = ['FORNECEDOR', 'Quantidade']

# Contar a quantidade de equipamentos por ANO FABR.
#transmissores_filtrados['ANO FABR.'] = transmissores_filtrados['ANO FABR.'].fillna('Desconhecido')
anofab_count = unidades_hidraulicas_filtradas['ANO FABR.'].value_counts(dropna=False).reset_index()
anofab_count.columns = ['ANO FABR.', 'Quantidade']
# Substituir NA por 'Desconhecido' APENAS PARA O GRÁFICO
anofab_count['ANO FABR.'] = anofab_count['ANO FABR.'].astype("string").fillna("Desconhecido")


# _________________ Criação da Página ___________________________
st.title("Unidades Hidráulicas")

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
    st.metric("Total de Equipamentos", total_unidades_hidraulicas)

with l1c2:
    # Criar o gráfico de donut
    fig_donut = px.pie(
        names=["Selecionados", "Não Selecionados"],
        values=[total_unidades_hidraulicas_filtradas, total_unidades_hidraulicas - total_unidades_hidraulicas_filtradas],
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
    if not unidades_hidraulicas_filtradas.empty and 'SETOR' in unidades_hidraulicas_filtradas.columns:
        # Gráfico de barras para Setor
        fig_setor = px.bar(setor_count, x='SETOR', y='Quantidade',
                          title="Distribuição de Equipamentos por Setor",
                          labels={'SETOR': 'Setor', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='SETOR', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_setor.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}, xaxis_tickangle=45)
        st.plotly_chart(fig_setor)

with l3c1:
    if not unidades_hidraulicas_filtradas.empty and 'CRITICIDADE' in unidades_hidraulicas_filtradas.columns:
        # Gráfico de barras para Criticidade
        fig_criticidade = px.bar(criticidade_count, x='CRITICIDADE', y='Quantidade',
                          title="Distribuição de Equipamentos por Criticidade",
                          labels={'CRITICIDADE': 'Criticidade', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='CRITICIDADE', color_discrete_sequence=px.colors.qualitative.Set3)
        fig_criticidade.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0})
        st.plotly_chart(fig_criticidade)


with l4c1:
    if not unidades_hidraulicas_filtradas.empty and 'FORNECEDOR' in unidades_hidraulicas_filtradas.columns:
        # Gráfico de barras para Criticidade
        fig_criticidade = px.bar(fornecedor_count, x='FORNECEDOR', y='Quantidade',
                          title="Distribuição de Equipamentos por Fornecedor",
                          labels={'FORNECEDOR': 'Fornecedor', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='FORNECEDOR', color_discrete_sequence=px.colors.qualitative.Set3)
        fig_criticidade.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 45})
        st.plotly_chart(fig_criticidade)


with l5c1:
    if not unidades_hidraulicas_filtradas.empty and 'ANO FABR.' in unidades_hidraulicas_filtradas.columns:
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
        st.dataframe(unidades_hidraulicas_filtradas, height=400)
