import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

if not st.session_state.get("authenticated", False):
    st.warning("Você precisa fazer login para acessar esta página.")
    st.switch_page("index.py")  # Redireciona para a tela de login

    
# Dados
vasos_de_pressao = pd.read_csv("data/vasos_de_pressao.csv", sep=";", encoding='utf-8')

vasos_de_pressao['DATA PRÓXIMA INSPEÇÃO (EXTERNA) '] = pd.to_datetime(vasos_de_pressao['DATA PRÓXIMA INSPEÇÃO (EXTERNA) '], errors='coerce')
vasos_de_pressao['DATA PRÓXIMA INSPEÇÃO (INTERNA) '] = pd.to_datetime(vasos_de_pressao['DATA PRÓXIMA INSPEÇÃO (INTERNA) '], errors='coerce')

# Seção expansível para filtros
with st.expander("Abrir Filtros"):
    setor_selecionado = st.multiselect("Selecione o Setor", vasos_de_pressao["SETOR"].dropna().unique().tolist())
    classe_selecionado = st.multiselect("Selecione a Classe", vasos_de_pressao["CLASSE"].dropna().unique().tolist())
    grupo_selecionado = st.multiselect("Selecione o Grupo", vasos_de_pressao["GRUPO"].dropna().unique().tolist())
    categoria_selecionado = st.multiselect("Selecione a Categoria", vasos_de_pressao["CATEGORIA"].dropna().unique().tolist())
    equipamento_selecionado = st.multiselect("Selecione o Equipamento", vasos_de_pressao["TAG"].dropna().unique().tolist())
    data_selecionada = st.date_input("Selecione a Data Máxima de Inspeção", value=None)

data_selecionada = pd.to_datetime(data_selecionada)
# Filtro por SETOR
#setor_opcoes = vasos_de_pressao["SETOR"].dropna().unique().tolist()
#setor_selecionado = st.sidebar.multiselect("Selecione o Setor", setor_opcoes, default=setor_opcoes)
# Aplicar os filtros ao DataFrame
dados_filtrados = vasos_de_pressao.copy()

if setor_selecionado:
    dados_filtrados = dados_filtrados[dados_filtrados["SETOR"].isin(setor_selecionado)]
if classe_selecionado:
    dados_filtrados = dados_filtrados[dados_filtrados["CLASSE"].isin(classe_selecionado)]
if grupo_selecionado:
    dados_filtrados = dados_filtrados[dados_filtrados["GRUPO"].isin(grupo_selecionado)]
if categoria_selecionado:
    dados_filtrados = dados_filtrados[dados_filtrados["CATEGORIA"].isin(categoria_selecionado)]
if equipamento_selecionado:
    dados_filtrados = dados_filtrados[dados_filtrados["TAG"].isin(equipamento_selecionado)]
if data_selecionada:
    dados_filtrados = dados_filtrados[
    (dados_filtrados['DATA PRÓXIMA INSPEÇÃO (EXTERNA) '] <= data_selecionada) |
    (dados_filtrados['DATA PRÓXIMA INSPEÇÃO (INTERNA) '] <= data_selecionada)
]

# Calcular o percentual de equipamentos filtrados em relação ao total
total_equipamentos = vasos_de_pressao.shape[0]
total_filtrados = dados_filtrados.shape[0]


# Calcular a idade dos equipamentos com data atual dinâmica
data_atual = datetime.now()  # Pega a data e hora atuais (22/10/2025 11:22 AM -03)
dados_filtrados.loc[:, 'ANO DE FABRICAÇÃO'] = pd.to_numeric(dados_filtrados['ANO DE FABRICAÇÃO'], errors='coerce')
dados_filtrados.loc[:, 'IDADE'] = data_atual.year - dados_filtrados['ANO DE FABRICAÇÃO']

# Agrupar idades em intervalos de 5 anos, incluindo 'Idade desconhecida' como categoria
bins = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]  # Intervalos até 50 anos
labels = ['0-5', '6-10', '11-15', '16-20', '21-25', '26-30', '31-35', '36-40', '41-45', '46-50']
all_categories = labels + ['Idade desconhecida']  # Incluir 'Idade desconhecida' como categoria válida
dados_filtrados.loc[:, 'FAIXA_IDADE'] = pd.cut(dados_filtrados['IDADE'], bins=bins, labels=labels, right=False, include_lowest=True)

dados_filtrados['FAIXA_IDADE'] = dados_filtrados['FAIXA_IDADE'].cat.add_categories(['Idade desconhecida'])

# Substitui os valores nan por "Idade desconhecida"
dados_filtrados['FAIXA_IDADE'].fillna('Idade desconhecida', inplace=True)

# Conta a quantidade de equipamentos por faixa de idade
faixa_idade_count = dados_filtrados['FAIXA_IDADE'].value_counts().reset_index()
faixa_idade_count.columns = ['FAIXA_IDADE', 'Quantidade']

# Conta a quantidade de equipamentos por fabricante
fabricante_count = dados_filtrados['FABRICANTE RESUMIDO'].value_counts().reset_index()
fabricante_count.columns = ['FABRICANTE RESUMIDO', 'Quantidade']

# Contar a quantidade de equipamentos por fluido (Casco e Tubo)
dados_filtrados['FLUÍDO (CASCO)'] = dados_filtrados['FLUÍDO (CASCO)'].fillna('Desconhecido')
casco_count = dados_filtrados['FLUÍDO (CASCO)'].value_counts().reset_index()
casco_count.columns = ['FLUÍDO (CASCO)', 'Quantidade']

dados_filtrados['FLUÍDO (TUBO)'] = dados_filtrados['FLUÍDO (TUBO)'].fillna('Desconhecido')
tubo_count = dados_filtrados['FLUÍDO (TUBO)'].value_counts().reset_index()
tubo_count.columns = ['FLUÍDO (TUBO)', 'Quantidade']

# Contar a quantidade de equipamentos por classe
dados_filtrados['CLASSE'] = dados_filtrados['CLASSE'].fillna('Desconhecida')
classe_count = dados_filtrados['CLASSE'].value_counts().reset_index()
classe_count.columns = ['CLASSE', 'Quantidade']

# Contar a quantidade de equipamentos por grupo
dados_filtrados['GRUPO'] = dados_filtrados['GRUPO'].fillna('Desconhecido')
grupo_count = dados_filtrados['GRUPO'].value_counts().reset_index()
grupo_count.columns = ['GRUPO', 'Quantidade']

# Contar a quantidade de equipamentos por categoria
dados_filtrados['CATEGORIA'] = dados_filtrados['CATEGORIA'].fillna('Desconhecida')
categoria_count = dados_filtrados['CATEGORIA'].value_counts().reset_index()
categoria_count.columns = ['CATEGORIA', 'Quantidade']

# Contar a quantidade de equipamentos por setor
dados_filtrados['SETOR'] = dados_filtrados['SETOR'].fillna('Desconhecida')
setor_count = dados_filtrados['SETOR'].value_counts().reset_index()
setor_count.columns = ['SETOR', 'Quantidade']

# Identificar inspeções vencidas
data_atual = pd.to_datetime(datetime.now().date())  # Converter para datetime64[ns] com apenas a data
inspecoes_vencidas = dados_filtrados[
    ((dados_filtrados['DATA PRÓXIMA INSPEÇÃO (EXTERNA) '].notna()) & (dados_filtrados['DATA PRÓXIMA INSPEÇÃO (EXTERNA) '] < data_atual)) |
    ((dados_filtrados['DATA PRÓXIMA INSPEÇÃO (INTERNA) '].notna()) & (dados_filtrados['DATA PRÓXIMA INSPEÇÃO (INTERNA) '] < data_atual))
]
num_inspecoes_vencidas = inspecoes_vencidas.shape[0]


# Layout com colunas para métricas e gráficos

# Linha 1
l1c1, l1c2, l1c3 = st.columns(3)

# Linha 2
l2c1, l2c2 = st.columns(2)

# Linha 3
l3c1 = st.columns(1)[0]

# Linha 4
l4c1, l4c2 = st.columns(2)

# Linha 5
l5c1, l5c2, l5c3 = st.columns(3)

# Linha 6
l6c1 = st.columns(1)[0]

# Graficos
# Início Linha 1
with l1c1:
    st.subheader("Métricas")
    #st.metric("Quantidade de Equipamentos Selecionados", total_filtrados)
    st.metric("Total de Equipamentos", total_equipamentos)

with l1c2:
    # Criar o gráfico de donut
    fig_donut = px.pie(
        names=["Selecionados", "Não Selecionados"],
        values=[total_filtrados, total_equipamentos - total_filtrados],
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

with l1c3:
    # Detalhes das inspeções vencidas
    if num_inspecoes_vencidas != 0:
        st.metric("Inspeções Vencidas", num_inspecoes_vencidas, delta=None, delta_color="inverse")
        #st.warning(f"**Atenção:** {num_inspecoes_vencidas} inspeções vencidas detectadas!")
        #st.dataframe(inspecoes_vencidas[['NÚMERO DO EQUIPAMENTO', 'DATA PRÓXIMA INSPEÇÃO (EXTERNA) ', 'DATA PRÓXIMA INSPEÇÃO (INTERNA) ']], height=200)
    else:
        st.metric("Inspeções Vencidas", "0", "Nenhuma inspeção vencida!", delta_color="normal")

# Início Linha 2

# Linha 2
with l2c1:
    st.subheader("Visualização")
    if not dados_filtrados.empty and 'SETOR' in dados_filtrados.columns:
        # Gráfico de barras para Setor
        fig_setor = px.bar(setor_count, x='SETOR', y='Quantidade',
                          title="Distribuição de Equipamentos por Setor",
                          labels={'SETOR': 'Setor', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='SETOR', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_setor.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}, xaxis_tickangle=45)
        st.plotly_chart(fig_setor)

with l2c2:
    if not dados_filtrados.empty and 'FAIXA_IDADE' in dados_filtrados.columns:
        # Gráfico de barras baseado em faixa_idade_count
        fig_idade = px.bar(faixa_idade_count, x='FAIXA_IDADE', y='Quantidade',
                          title="Distribuição da Idade dos Equipamentos (Faixas de 5 Anos)",
                          labels={'FAIXA_IDADE': 'Faixa de Idade (Anos)', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='FAIXA_IDADE', color_discrete_sequence=px.colors.qualitative.Set3)
        fig_idade.update_layout(xaxis={'categoryorder': 'total descending'})  # Ordenar por quantidade descendente
        fig_idade.update_layout(xaxis={'categoryorder': 'total descending'}, xaxis_tickangle=45)
        st.plotly_chart(fig_idade)


# Início Linha 3
with l3c1:
    if not dados_filtrados.empty and 'FABRICANTE RESUMIDO' in dados_filtrados.columns:
        #fabricante_count = fabricante_count.head(10)  # Limitar a 10 fabricantes
        # Gráfico de barras baseado em fabricante_count
        fig_fabricante = px.bar(fabricante_count, x='FABRICANTE RESUMIDO', y='Quantidade',
                            title="Principais Fabricantes",
                            labels={'FABRICANTE RESUMIDO': 'Fabricante', 'Quantidade': 'Quantidade de Equipamentos'},
                            color='FABRICANTE RESUMIDO', color_discrete_sequence=px.colors.qualitative.Set2)
        fig_fabricante.update_layout(xaxis={'categoryorder': 'total descending'}, xaxis_tickangle=30)  # Ordenar e rotacionar rótulos
        fig_fabricante.update_layout(
        #width = 800,  # Ajuste o tamanho conforme necessário
        height = 600,  # Ajuste o tamanho conforme necessário
        )

        st.plotly_chart(fig_fabricante)

# Início Linha 4
with l4c1:
    if not dados_filtrados.empty and 'FLUÍDO (CASCO)' in dados_filtrados.columns:
        # Gráfico de barras para Fluido no Casco
        fig_casco = px.bar(casco_count, x='FLUÍDO (CASCO)', y='Quantidade',
                          title="Distribuição de Equipamentos por Fluido no Casco",
                          labels={'FLUÍDO (CASCO)': 'Fluido no Casco', 'Quantidade': 'Quantidade de Equipamentos'},
                          color='FLUÍDO (CASCO)', color_discrete_sequence=px.colors.qualitative.Set1)
        fig_casco.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 45}
        )
        st.plotly_chart(fig_casco)


with l4c2:
    if not dados_filtrados.empty and 'FLUÍDO (TUBO)' in dados_filtrados.columns:
        # Gráfico de barras para Fluido no Tubo
        fig_tubo = px.bar(tubo_count, x='FLUÍDO (TUBO)', y='Quantidade',
                         title="Distribuição de Equipamentos por Fluido no Tubo",
                         labels={'FLUÍDO (TUBO)': 'Fluido no Tubo', 'Quantidade': 'Quantidade de Equipamentos'},
                         color='FLUÍDO (TUBO)', color_discrete_sequence=px.colors.qualitative.Pastel1)
        fig_tubo.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 45}
        )
        st.plotly_chart(fig_tubo)

# Início l5
with l5c1:
    if not dados_filtrados.empty and 'CLASSE' in dados_filtrados.columns:
        # Gráfico de barras para Classe
        fig_classe = px.bar(classe_count, x='CLASSE', y='Quantidade',
                           title="Distribuição de Equipamentos por Classe",
                           labels={'CLASSE': 'Classe do Fluido', 'Quantidade': 'Quantidade de Equipamentos'},
                           color='CLASSE', color_discrete_sequence=px.colors.qualitative.Pastel2)
        fig_classe.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}
        )
        st.plotly_chart(fig_classe)

with l5c2:
    if not dados_filtrados.empty and 'GRUPO' in dados_filtrados.columns:
        # Gráfico de barras para Grupo
        fig_grupo = px.bar(grupo_count, x='GRUPO', y='Quantidade',
                          title="Distribuição de Equipamentos por Grupo",
                          labels={'GRUPO': "GPR", 'Quantidade': 'Quantidade de Equipamentos'},
                          color='GRUPO', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_grupo.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}
        )
        st.plotly_chart(fig_grupo)

with l5c3:
    if not dados_filtrados.empty and 'CATEGORIA' in dados_filtrados.columns:
        # Gráfico de barras para Categoria
        fig_categoria = px.bar(categoria_count, x='CATEGORIA', y='Quantidade',
                              title="Distribuição de Equipamentos por Categoria",
                              labels={'CATEGORIA': 'Categoria', 'Quantidade': 'Quantidade de Equipamentos'},
                              color='CATEGORIA', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_categoria.update_layout(

            xaxis={'categoryorder': 'total descending', 'tickangle': 0}
        )
        st.plotly_chart(fig_categoria)




with l6c1:
    with st.expander("Mais Detalhes"):
        # Tabela de dados filtrados
        st.subheader("Detalhes dos Equipamentos Filtrados")
        st.dataframe(dados_filtrados, height=400)