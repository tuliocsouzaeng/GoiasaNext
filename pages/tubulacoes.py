import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
from utils.data_loader import load_csv

# _________________________ Checa se login foi feito ______________________________


if not st.session_state.get("authenticated", False):
    st.warning("Você precisa fazer login para acessar esta página.")
    st.switch_page("index.py")  # Redireciona para a tela de login



# _________________________ Importação dos Dados ______________________________

#tubulacoes = pd.read_csv("data/tubulacoes.csv", sep=";", encoding='utf-8')
tubulacoes = load_csv("data/tubulacoes.csv.enc", sep=";", encoding='utf-8')



# _________________________ Tratamento dos Dados ______________________________

tubulacoes['VIDA RESIDUAL ESTIMADA EM ANOS'] = tubulacoes['VIDA RESIDUAL ESTIMADA EM ANOS'].replace(
    to_replace=['None', '#VALOR!', None, np.nan], 
    value='Desconhecido'
)


# _________________________ Aplicação de Filtros _____________________________

# Seção expansível para filtros
with st.expander("Abrir Filtros"):
    setor_selecionado = st.multiselect("Selecione o Setor", tubulacoes["SETOR"].dropna().unique().tolist())
    criticidade_selecionada = st.multiselect("Selecione a Criticidade", tubulacoes["CRITICIDADE"].dropna().unique().tolist())
    material_selecionado = st.multiselect("Selecione o Material", tubulacoes["MATERIAL"].dropna().unique().tolist())
    equipamento_selecionado = st.multiselect("Selecione o Equipamento", tubulacoes["EQUIPAMENTO PRINCIPAL"].dropna().unique().tolist())
    TAG_selecionada = st.multiselect("Selecione a TAG", tubulacoes["TAG"].dropna().unique().tolist())
    dia_pol = st.multiselect("Selecione o Diâmetro", tubulacoes["DIAMETRO [POL]"].dropna().unique().tolist())

# Aplicar os filtros ao DataFrame
tubulacoes_filtradas = tubulacoes.copy()

if setor_selecionado:
    tubulacoes_filtradas = tubulacoes_filtradas[tubulacoes_filtradas["SETOR"].isin(setor_selecionado)]
if material_selecionado:
    tubulacoes_filtradas = tubulacoes_filtradas[tubulacoes_filtradas["MATERIAL"].isin(material_selecionado)]
if criticidade_selecionada:
    tubulacoes_filtradas = tubulacoes_filtradas[tubulacoes_filtradas["CRITICIDADE"].isin(criticidade_selecionada)]
if equipamento_selecionado:
    tubulacoes_filtradas = tubulacoes_filtradas[tubulacoes_filtradas["EQUIPAMENTO PRINCIPAL"].isin(equipamento_selecionado)]
if TAG_selecionada:
    tubulacoes_filtradas = tubulacoes_filtradas[tubulacoes_filtradas["TAG"].isin(TAG_selecionada)]
if dia_pol:
    tubulacoes_filtradas = tubulacoes_filtradas[tubulacoes_filtradas["DIAMETRO [POL]"].isin(dia_pol)]



# _______________ Geração de Informações ________________________

# Remove duplicatas por TAG (mantém a primeira ocorrência de cada TAG)
tubulacoes_unicas = tubulacoes_filtradas.drop_duplicates(subset='TAG')

# Calcular o Total de Tubulações
total_tubulacoes = tubulacoes["TAG"].nunique()

# Calcular o Total de Tubulações Filtradas
total_tubulacoes_filtradas = tubulacoes_filtradas["TAG"].nunique()

# Calcular o Total de Pontos de Medição
total_pontos_filtrados = tubulacoes_filtradas["PONTO"].shape[0]

# Conta a quantidade de equipamentos por criticidade
criticidade_count = tubulacoes_unicas['CRITICIDADE'].value_counts().reset_index()
criticidade_count.columns = ['CRITICIDADE', 'Quantidade']

# Conta a quantidade de equipamentos por criticidade
criticidade_count = tubulacoes_unicas['CRITICIDADE'].value_counts().reset_index()
criticidade_count.columns = ['CRITICIDADE', 'Quantidade']

# Conta a quantidade de equipamentos por material
material_count = tubulacoes_unicas['MATERIAL'].value_counts().reset_index()
material_count.columns = ['MATERIAL', 'Quantidade']

# PONTOS MEDIDOS POR ANO -> O RESULTADO É UM DICIONÁRIO 
colunas_ano = [col for col in tubulacoes_filtradas.columns if col.startswith("EM 20")]
dados_medicao = {}
anos_disponiveis = []
anos_exibicao = []           # ← para mostrar no dropdown (só o número)


# Se houver colunas de ano e dados filtrados
if colunas_ano and not tubulacoes_filtradas.empty:
    # Organiza os anos por ordem numérica
    anos_disponiveis = sorted(colunas_ano, key=lambda x: int(x.split()[-1]))

    for ano in anos_disponiveis:
        ano_num = ano.split()[-1]  # "2019"
        anos_exibicao.append(ano_num)       # "2019"
        # Total de valores
        total = tubulacoes_filtradas[ano].shape[0]

        # Contagem de "S / A"
        s_a = tubulacoes_filtradas[ano][tubulacoes_filtradas[ano] == "S / A"].shape[0]

        # Contagem de "None" (valores ausentes ou NaN)
        none = tubulacoes_filtradas[ano][tubulacoes_filtradas[ano].isna()].shape[0]

        # Contagem de valores "medidos" (total menos "S / A" e "None")
        medidos = total - s_a - none

        # Calculando o percentual de medidos
        pct_medidos = (medidos / total * 100) if total > 0 else 0

        # Armazenar os resultados
        dados_medicao[ano] = {
            'total': total,
            'medidos': medidos,
            's_a': s_a,
            'none': none,
            'pct_medidos': pct_medidos
        }

# Histograma da Taxa de Corrosão Máxima
taxa_corrosao_data = {}
taxa_corrosao_stats = {}  # Dicionário para estatísticas gerais, incluindo NaN
if 'TAXA DE CORROSÃO MÁXIMA [mm/ano]' in tubulacoes_filtradas.columns:
    # Converte strings com vírgula para ponto antes de transformar em numérico
    taxa_corrosao = tubulacoes_filtradas['TAXA DE CORROSÃO MÁXIMA [mm/ano]'].astype(str).str.replace(',', '.')
    taxa_corrosao = pd.to_numeric(taxa_corrosao, errors='coerce')  # Converte #VALOR e inválidos para NaN
    
    # Trata 0,00, 0 e #VALOR como inválidos
    taxa_corrosao = taxa_corrosao.replace([0.00, 0], np.nan)

    # Conta o total de valores e os NaN
    total_valores = len(taxa_corrosao)
    nan_count = taxa_corrosao.isna().sum()
    valid_count = total_valores - nan_count
    
    # Remove NaN (incluindo os valores tratados)
    taxa_corrosao = taxa_corrosao.dropna()
    
    if not taxa_corrosao.empty:
        taxa_corrosao_data = {
            'valores': taxa_corrosao,
            'min': taxa_corrosao.min(),
            'max': taxa_corrosao.max(),
            'mean': taxa_corrosao.mean()
        }

        # Adiciona estatísticas gerais, incluindo NaN
        taxa_corrosao_stats = {
            'total': total_valores,
            'nan_count': nan_count,
            'valid_count': valid_count
        }


# Dados para o gráfico de barras: Vida Residual Estimada (prioriza TROCAR/Desconhecido, senão mínimo numérico por TAG)
vida_residual_data = {}
if 'VIDA RESIDUAL ESTIMADA EM ANOS' in tubulacoes_filtradas.columns:
    # Função para determinar o valor por TAG
    def get_min_or_category(group):
        # Converte o numpy.ndarray para pandas.Series
        series = pd.Series(group)
        values = series.values
        # Verifica se há TROCAR ou Desconhecido
        if 'TROCAR' in values or 'Desconhecido' in values:
            return next((v for v in values if v in ['TROCAR', 'Desconhecido']), values[0])
        # Se só houver numéricos, pega o mínimo
        numeric_values = pd.to_numeric(series, errors='coerce').dropna()
        return numeric_values.min() if not numeric_values.empty else values[0]

    # Agrupa por TAG e aplica a lógica
    vida_residual_min = tubulacoes_filtradas.groupby('TAG')['VIDA RESIDUAL ESTIMADA EM ANOS'].agg(get_min_or_category).reset_index()
    
    # Conta a frequência de cada valor
    vida_residual_count = vida_residual_min['VIDA RESIDUAL ESTIMADA EM ANOS'].value_counts().reset_index()
    vida_residual_count.columns = ['Valor', 'Quantidade']
    
    # Ordena por quantidade
    vida_residual_count = vida_residual_count.sort_values(by='Quantidade', ascending=False)
    
    vida_residual_data = {
        'dados': vida_residual_count
    }

# _________________ Criação da Página ___________________________

st.subheader("Métricas")
# Linha 1
l1c1, l1c2, l1c3 = st.columns(3)


# Linha 2
l2c1, l2c2 = st.columns(2)

# Linha 3
l3c1, l3c2 = st.columns(2)

# Linha 4
l4c1 = st.columns(1)[0]

# Linha 5
l5c1 = st.columns(1)[0]

# Linha 6
l6c1, l6c2 = st.columns(2)


# Linha 7
l7c1 = st.columns(1)[0]

# __________________ Visualização das Informações ______________

# Início Linha 1

with l1c1:
    st.metric("Total de Equipamentos", total_tubulacoes)

with l1c2:
    # Criar o gráfico de donut
    fig_donut = px.pie(
        names=["Selecionados", "Não Selecionados"],
        values=[total_tubulacoes_filtradas, total_tubulacoes - total_tubulacoes_filtradas],
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
    st.metric("Total de Pontos de Medição", total_pontos_filtrados)


# Início Linha 2
with l2c1:
    if not tubulacoes_filtradas.empty and 'CRITICIDADE' in tubulacoes_filtradas.columns:
        # Gráfico de barras para Grupo
        fig_criticidade = px.bar(criticidade_count, x='CRITICIDADE', y='Quantidade',
                          title="Distribuição de Equipamentos por Criticidade",
                          labels={'CRITICIDADE': "Criticidade", 'Quantidade': 'Quantidade de Equipamentos'},
                          color='CRITICIDADE', color_discrete_sequence=px.colors.qualitative.Dark2)
        fig_criticidade.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 45}
        )
        st.plotly_chart(fig_criticidade)

with l2c2:
    if not tubulacoes_filtradas.empty and 'MATERIAL' in tubulacoes_filtradas.columns:
        # Gráfico de barras para Material
        fig_material = px.bar(material_count, x='MATERIAL', y='Quantidade',
                          title="Distribuição de Equipamentos por Material",
                          labels={'MATERIAL': "Material", 'Quantidade': 'Quantidade de Equipamentos'},
                          color='MATERIAL', color_discrete_sequence=px.colors.qualitative.Pastel2)
        fig_material.update_layout(
            xaxis={'categoryorder': 'total descending', 'tickangle': 0}
        )
        st.plotly_chart(fig_material)


# Início Linha 3

with l3c1:
    if taxa_corrosao_data:
        fig_corrosao = px.histogram(
            x=taxa_corrosao_data['valores'],
            nbins=20,
            title="Distribuição da Taxa de Corrosão Máxima [mm/ano] das Tubulações com Histórico de Medição",
            labels={'x': 'Taxa de Corrosão [mm/ano]', 'y': 'Quantidade de Equipamentos'},
            color_discrete_sequence=['#2196F3']
        )
        fig_corrosao.update_layout(
            height=500,
            width=500,
            bargap=0.1,
            showlegend=False
        )
        fig_corrosao.add_vline(
            x=taxa_corrosao_data['mean'],
            line_dash="dash",
            line_color="red",
            annotation_text=f"Média: {taxa_corrosao_data['mean']:.2f} mm/ano",
            annotation_position="top right"
        )
        st.plotly_chart(fig_corrosao, use_container_width=True)

        st.caption(
            f"**Mínimo:** {taxa_corrosao_data['min']:.2f} mm/ano | "
            f"**Máximo:** {taxa_corrosao_data['max']:.2f} mm/ano | "
            f"**Média:** {taxa_corrosao_data['mean']:.2f} mm/ano"
        )
    

with l3c2:
# corrosão definida vs. não definida
    if taxa_corrosao_stats:
        fig_donut_corrosao = px.pie(
            names=["Definidos", "Não Definidos"],
            values=[taxa_corrosao_stats['valid_count'], taxa_corrosao_stats['nan_count']],
            title="Proporção de Pontos com Taxa de Corrosão Máxima Definida",
            hole=0.7,
            color_discrete_sequence=["#4CAF50", "#FF9800"]
        )
        fig_donut_corrosao.update_layout(
            height=500,
            width=500
        )
        st.plotly_chart(fig_donut_corrosao, use_container_width=True)

        st.caption(f"Total de pontos: {taxa_corrosao_stats['total']} | Definidos: {taxa_corrosao_stats['valid_count']} | Não Definidos: {taxa_corrosao_stats['nan_count']}")

with l4c1:
    if vida_residual_data:
        fig_vida_residual = px.bar(
            vida_residual_data['dados'],
            x='Valor',
            y='Quantidade',
            title="Distribuição da Vida Residual por Tubulação [Anos]",
            labels={'Valor': 'Vida Residual [Anos]', 'Quantidade': 'Quantidade de Tubulações'},
            color='Valor',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_vida_residual.update_layout(
            height=500,
            width=500,
            xaxis={'tickangle': 45},
            bargap=0.2,
            showlegend=False
        )
        st.plotly_chart(fig_vida_residual, use_container_width=True)

        st.caption("Valores: 'TROCAR' ou 'Desconhecido' se presentes na tubulação (TAG), senão o mínimo numérico.")

with l5c1:
    st.subheader("Histórico de Medição")
    if True:
        ano_selecionado_num = st.selectbox(
            "Selecione o ano da medição",
            options=anos_exibicao,
            index=6, #define a opção que irá aparecer como default
            key="select_ano_medicao_3cat"
        )

        ano_selecionado = f"EM {ano_selecionado_num}" # Converte "2019" → "EM 2019"

with l6c1:
        d = dados_medicao[ano_selecionado]
        # Dados para o gráfico
        df_grafico = pd.DataFrame({
            'Categoria': ['Medidos', 'Sem Acesso', 'Sem Informação'],
            'Quantidade': [d['medidos'], d['s_a'], d['none']]
        })

        # Cores personalizadas
        cores = {'Medidos': '#4CAF50', 'S / A': '#FF9800', 'None': '#9E9E9E'}
        
        #st.metric(
        #label=f"Medidos em {ano_selecionado.split()[-1]}",
        #value=d['medidos'])
        # Gráfico de pizza (donut)
        fig = px.pie(
            df_grafico,
            values='Quantidade',
            names='Categoria',
            hole=0.6,
            color='Categoria',
            color_discrete_map=cores,
            #title=f"{ano_selecionado}: {d['pct_medidos']:.1f}% medidos",
        )

        fig.update_traces(textinfo='percent+label', textposition='inside')
        fig.update_layout(height=400, width=400, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)



with l6c2:
    colunas_selecionadas = ["TAG", "PONTO", ano_selecionado, "SETOR", "EQUIPAMENTO PRINCIPAL",]
    df_medicao = tubulacoes_filtradas[colunas_selecionadas]
    df_medicao = df_medicao.rename(columns={ano_selecionado: ano_selecionado.split()[-1]})
    st.dataframe(df_medicao, height=400)

with l7c1:
    with st.expander("Mais Detalhes"):
        st.subheader("Detalhes dos Equipamentos Filtrados")
        st.dataframe(tubulacoes_filtradas, height=400)
