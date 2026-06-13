import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from datetime import timedelta
import plotly.graph_objects as go
import os
import json
import gspread


# _________________________ Checa se login foi feito ______________________________

if not st.session_state.get("authenticated", False):
    st.warning("Você precisa fazer login para acessar esta página.")
    st.switch_page("index.py")  # Redireciona para a tela de login


# _________________________ Importação dos Dados ______________________________

# ordens_servico = pd.read_csv("data/Ordens_Servico_2026.csv", sep=";", encoding='utf-8')

@st.cache_resource
def get_gspread_client():
    GOOGLE_REDE_CREDS = os.getenv("GOOGLE_REDE_CREDS")
    if isinstance(GOOGLE_REDE_CREDS, str):
        info_autenticacao = json.loads(GOOGLE_REDE_CREDS)
    else:
        info_autenticacao = GOOGLE_REDE_CREDS
    return gspread.service_account_from_dict(info_autenticacao)


@st.cache_data(ttl=300)
def carregar_dados():
    gc = get_gspread_client()
    planilha = gc.open("Ordens_Servico")
    aba = planilha.worksheet("Ordens_Servico")
    df = pd.DataFrame(aba.get_all_records())
    df["DATA_CONVERTIDA"] = pd.to_datetime(df["DATA"], format="%d/%m/%Y", errors="coerce")
    df = df.dropna(subset=["DATA_CONVERTIDA"])
    return df
	
ordens_servico = carregar_dados()




# CONVERSÃO DA DATA: Transforma o texto '09/06/2026' em uma data que o Python entende
ordens_servico["DATA_CONVERTIDA"] = pd.to_datetime(
    ordens_servico["DATA"],
    format="%d/%m/%Y",
    errors="coerce"
)
ordens_servico = ordens_servico.dropna(
    subset=["DATA_CONVERTIDA"]
)


# _________________________ Aplicação de Filtros _____________________________

# Ajuste os nomes das equipes ('Equipe A', 'Equipe B', etc.) para os nomes exatos que estão no seu CSV

MAPEAMENTO_OFICINAS = {   
			"Caldeiraria": ["CD00", "CD01", "CD66", "CD99", "CS00", "CD66", "CSEG", "JP01"],
			"Mecânica": ["MM00", "MM66", "TRPM"],
			"Elétrica": ["EL00", "EL66", "EP00", "EPRD", "TRPE"],
			"Instrumentação": ["IN00", "IN66", "SI00", "TRPI"],
			"Automação": ["AT00", "ZAMI"],
            "Jaboticabal": ["T048", "T039"],
            "KSB": ["KSB", "KSB6"]}

MAPEAMENTO_STATUS = {
    0: "Em Andamento",
    1: "Programada",
    2: "Planejada",
    3: "Interrompida",
    4: "Concluída",
    5: "Não Planejada",
    6: "Cancelada",
    9: "Encerrada"
}

# Seção expansível para filtros
with st.expander("Abrir Filtros"):
    #setor_selecionado = st.multiselect("Selecione o Setor", turbinas["SETOR"].dropna().unique().tolist()) # Devera ser feito utilizando a localizacao
    TAG_selecionada = st.multiselect("Selecione a TAG", ordens_servico["EQUIPAMENTO"].dropna().unique().tolist())
    atividade_selecionada = st.multiselect("Selecione o tipo de atividade", ordens_servico["ATIVIDADE"].dropna().unique().tolist())
    equipe_selecionada = st.multiselect("Selecione a Equipe", ordens_servico["DESCRIÇÃO EQUIPE"].dropna().unique().tolist())
    oficina_selecionada = st.multiselect("Selecione a Oficina", list(MAPEAMENTO_OFICINAS.keys()))
    status_selecionado = st.multiselect("Selecione o Status", list(MAPEAMENTO_STATUS.values()))
    periodo = st.date_input(
    "Período",
    value=(
        #ordens_servico["DATA_CONVERTIDA"].min().date(),
        pd.Timestamp("2026-04-01").date(),  # Data inicial fixa
        ordens_servico["DATA_CONVERTIDA"].max().date()
    )
)

if len(periodo) == 2:
    data_inicial, data_final = periodo
else:
    #data_inicial = ordens_servico["DATA_CONVERTIDA"].min()
    data_inicial = pd.Timestamp("2026-04-01").date()
    data_final = ordens_servico["DATA_CONVERTIDA"].max()
  
data_inicial = pd.Timestamp(data_inicial)
data_final = pd.Timestamp(data_final)

# Aplicar os filtros ao DataFrame
ordens_servico_filtradas = ordens_servico.copy()

#if setor_selecionado:
#    turbinas_filtradas = turbinas_filtradas[turbinas_filtradas["SETOR"].isin(setor_selecionado)]
if TAG_selecionada:
    ordens_servico_filtradas = ordens_servico_filtradas[ordens_servico_filtradas["EQUIPAMENTO"].isin(TAG_selecionada)]
if atividade_selecionada:
    ordens_servico_filtradas = ordens_servico_filtradas[ordens_servico_filtradas["ATIVIDADE"].isin(atividade_selecionada)]
if equipe_selecionada:
    ordens_servico_filtradas = ordens_servico_filtradas[ordens_servico_filtradas["DESCRIÇÃO EQUIPE"].isin(equipe_selecionada)]
if oficina_selecionada:
    equipes_oficinas = []
    for oficina in oficina_selecionada:
        equipes_oficinas.extend(MAPEAMENTO_OFICINAS[oficina])

    ordens_servico_filtradas = ordens_servico_filtradas[
        ordens_servico_filtradas["EQUIPE"].isin(equipes_oficinas)
    ]

if status_selecionado:

    codigos_status = [
        codigo
        for codigo, descricao in MAPEAMENTO_STATUS.items()
        if descricao in status_selecionado
    ]

    ordens_servico_filtradas = ordens_servico_filtradas[
        ordens_servico_filtradas["STATUS OS"].isin(codigos_status)
    ]

if data_inicial and data_final:
    ordens_servico_filtradas = ordens_servico_filtradas[
        (ordens_servico_filtradas["DATA_CONVERTIDA"] >= data_inicial) &
        (ordens_servico_filtradas["DATA_CONVERTIDA"] <= data_final)
    ]


# _______________ Geração de Informações ________________________

# Calcular o Total de Ordens de Serviço
total_ordens = ordens_servico_filtradas.shape[0]

# Cálculo do Status da OS

os_andamento = ordens_servico_filtradas[
    ordens_servico_filtradas["STATUS OS"] == 0
].shape[0]

os_programadas = ordens_servico_filtradas[
    ordens_servico_filtradas["STATUS OS"] == 1
].shape[0]

os_planejada = ordens_servico_filtradas[
    ordens_servico_filtradas["STATUS OS"] == 2
].shape[0]

os_interrompida = ordens_servico_filtradas[
    ordens_servico_filtradas["STATUS OS"] == 3
].shape[0]

os_concluidas = ordens_servico_filtradas[
    ordens_servico_filtradas["STATUS OS"] == 4
].shape[0]

os_naoplanejada = ordens_servico_filtradas[
    ordens_servico_filtradas["STATUS OS"] == 5
].shape[0]

os_canceladas = ordens_servico_filtradas[
    ordens_servico_filtradas["STATUS OS"] == 6
].shape[0]


os_encerradas = ordens_servico_filtradas[
    ordens_servico_filtradas["STATUS OS"] == 9
].shape[0]


# Cálculo da Eficácia

mpc = ordens_servico_filtradas[
    ordens_servico_filtradas["ATIVIDADE"] == "MPC"
].shape[0]

mpd = ordens_servico_filtradas[
    ordens_servico_filtradas["ATIVIDADE"] == "MPD"
].shape[0]

mco = ordens_servico_filtradas[
    ordens_servico_filtradas["ATIVIDADE"] == "MCO"
].shape[0]

eficacia = (
    (mpc + mpd) / (mpc + mpd + mco) * 100
    if (mpc + mpd + mco) > 0
    else 0
)

# Cálculo do percentual de OS corretiva

#percentual_corretiva = mco*100/ordens_servico_filtradas["ATIVIDADE"].shape[0]

# Ativos Vermelhos (Sensitiva - Preventiva)

#ativos_vermelhos_sens_prev = or

# Tempo de Atendimento de OS

dias_periodo = (data_final - data_inicial).days

if dias_periodo < 20:
    backlog_pendentes = None
else:

    data_limite = data_final - timedelta(days=20)

    os_antigas = ordens_servico_filtradas[
        ordens_servico_filtradas["DATA_CONVERTIDA"] <= data_limite
    ]

    backlog_pendentes = os_antigas[
        ~os_antigas["STATUS OS"].isin([4, 6, 9])
    ].shape[0]


# Evolução semanal da eficácia

df_eficacia = ordens_servico_filtradas.copy()

df_eficacia["DATA_CONVERTIDA"] = pd.to_datetime(
    df_eficacia["DATA_CONVERTIDA"]
)

dados_semanais = []

for semana, grupo in df_eficacia.groupby(
    pd.Grouper(
        key="DATA_CONVERTIDA",
        freq="7D"
    )
):

    mpc_semana = (
        grupo["ATIVIDADE"] == "MPC"
    ).sum()

    mpd_semana = (
        grupo["ATIVIDADE"] == "MPD"
    ).sum()

    mco_semana = (
        grupo["ATIVIDADE"] == "MCO"
    ).sum()

    total = mpc_semana + mpd_semana + mco_semana

    eficacia_semana = (
        (mpc_semana + mpd_semana)
        / total
        * 100
        if total > 0
        else 0
    )

    dados_semanais.append({
        "Semana": semana,
        "Eficacia": round(eficacia_semana, 2),
        "MPC": mpc_semana,
        "MPD": mpd_semana,
        "MCO": mco_semana,
        "Total": total
    })

eficacia_semanal = pd.DataFrame(
    dados_semanais
)

# Percentual de Corretivas

percentual_corretiva = (
    mco / total_ordens * 100
    if total_ordens > 0
    else 0
)

# Meta de Corretivas
meta_corretiva = 20

# ==========================
# Cálculo do MTTR
# ==========================

# Filtra apenas OS concluídas ou encerradas
os_mttr = ordens_servico_filtradas[
    ordens_servico_filtradas["STATUS OS"].isin([4, 9])
].copy()

# Remove valores vazios
os_mttr = os_mttr[
    os_mttr["HORAS GASTAS"].notna()
]

os_mttr = os_mttr[
    os_mttr["HORAS GASTAS"].astype(str).str.strip() != ""
]

# Converte HH:MM para timedelta
os_mttr["HORAS_GASTAS_TD"] = pd.to_timedelta(
    os_mttr["HORAS GASTAS"] + ":00",
    errors="coerce"
)

# Remove erros de conversão
os_mttr = os_mttr.dropna(subset=["HORAS_GASTAS_TD"])

# Soma total de horas
total_horas = os_mttr["HORAS_GASTAS_TD"].dt.total_seconds().sum() / 3600

# Quantidade de OS válidas
quantidade_os = len(os_mttr)

# MTTR
mttr = total_horas / quantidade_os if quantidade_os > 0 else 0


# OS CONCLUÍDA

os_concluidas_encerradas = ordens_servico_filtradas[
    ordens_servico_filtradas["STATUS OS"].isin([4, 9])
].shape[0]


# _________________ Criação da Página ___________________________
st.title("Ordens de Serviço")

# Linha 1
#l1c1, l1c2, l1c3, l1c4, l1c5, l1c6, l1c7, l1c8, l1c9, l1c10 = st.columns(10)
l1c1, l1c2, l1c3 = st.columns(3)

# Linha 2
l2c1, l2c2, l2c3 = st.columns(3)

# Linha 3
l3c1 = st.columns(1)[0]

# Linha 4
l4c1 = st.columns(1)[0]

# Linha 5
l5c1 = st.columns(1)[0]

# Linha 6
l6c1 = st.columns(1)[0]

# Linha 7
l7c1 = st.columns(1)[0]

# __________________ Visualização das Informações ______________

# Início Linha 1
with l1c1:
    st.metric("Total de OS", total_ordens)


# with l1c2:
#     st.metric("Em Andamento", os_andamento)

# with l1c3:
#     st.metric("Programadas", os_programadas)

# with l1c4:
#     st.metric("Planejadas", os_planejada)

# with l1c5:
#     st.metric("Interrompidas", os_interrompida)

# with l1c6:
#     st.metric("Concluídas", os_concluidas)

# with l1c7:
#     st.metric("Não Planejadas", os_naoplanejada)

# with l1c8:
#     st.metric("Canceladas", os_canceladas)

# with l1c9:
#     st.metric("Encerradas", os_encerradas)

with l1c2:
    st.metric(f"Eficácia", round(eficacia, 2), "%")

    with st.popover("Como é calculada?"):
        st.write("""
        Eficácia = (MPC + MPD) / (MPC + MPD + MCO)

        MPC = Manutenção Preventiva da Sensitiva

        MPD = Manutenção Preventiva Preditiva

        MCO = Manutenção Corretiva
        """)

with l1c3:

    if backlog_pendentes is None:
        st.metric(
            "Tempo de Atend. OS (Backlog > 20 dias)",
            "-"
        )
        st.caption(
            "Selecione um período mínimo de 20 dias."
        )

    else:
        st.metric(
            "Tempo de Atend. OS (Backlog > 20 dias)",
            backlog_pendentes
        )

        st.caption(
            "OS com mais de 20 dias sem conclusão."
        )

    with st.popover("Como é calculada?"):
        st.write("""
        No Diário de Ocorrência, seleciona-se todas as Ordens de Serviço. 
        
        Retire as que foram abertas nos últimos 20 dias. 
        
        Dentro dessas Ordens de Serviço filtradas, quantas não possuem Status Concluída, Encerrada, Cancelada?
        """)
with l2c1:
    st.metric(
        "Percentual de Corretivas",
        f"{percentual_corretiva:.1f}%",
        delta=f"{percentual_corretiva-meta_corretiva:.1f}%",
        delta_color="inverse"
    )


    with st.popover("Como é calculado?"):
        st.write("""
            Percentual de Corretivas = (MCO) / (Total de OS exceto Sensitiva)
        """)
with l2c2:
    st.metric(
        "MTTR",
        f"{mttr:.2f} h"
    )

    # Espaço para alinhar com os outros indicadores
    st.write("")


    with st.popover("Como é calculado?"):
        st.write("""
        Considera apenas OS:

        • Concluídas (Status 4)

        • Encerradas (Status 9)

         Exclui OS sem o campo HORAS GASTAS.

        MTTR = Soma das Horas Gastas ÷ Quantidade de OS
        """)

with l2c3:
    st.metric(
        "OS Concluídas",
        os_concluidas_encerradas
    )
    # Espaço para alinhar com os outros indicadores
    st.write("")
    
    with st.popover("Como é calculado?"):
        st.write("""
        Total de OS com Status Concluído ou Encerrado.
        """)

with l3c1:
    status_count = (
        ordens_servico_filtradas["STATUS OS"]
        .map(MAPEAMENTO_STATUS)
        .value_counts()
        .reset_index()
    )

    status_count.columns = ["Status", "Quantidade"]

    fig = px.bar(
        status_count,
        x="Status",
        y="Quantidade",
        title="Ordens por Status"
    )

    st.plotly_chart(fig, use_container_width=True)

with l4c1:
    mapa_invertido = {}

    for oficina, equipes in MAPEAMENTO_OFICINAS.items():
        for equipe in equipes:
            mapa_invertido[equipe] = oficina

    ordens_servico_filtradas["OFICINA"] = (
        ordens_servico_filtradas["EQUIPE"]
        .map(mapa_invertido)
    )
    
    oficina_count = (
        ordens_servico_filtradas["OFICINA"]
        .value_counts()
        .reset_index()
    )

    oficina_count.columns = ["Oficina", "Quantidade"]

    fig = px.bar(
        oficina_count,
        x="Oficina",
        y="Quantidade",
        title="Ordens por Oficina"
    )

    st.plotly_chart(fig, use_container_width=True)

with l5c1:
    atividade_count = (
        ordens_servico_filtradas["ATIVIDADE"]
        .value_counts()
        .reset_index()
    )

    atividade_count.columns = [
    "Atividade",
    "Quantidade"]

    st.subheader("Ordens de Serviço por Atividade")

    fig_atividade = px.bar(
        atividade_count,
        x="Atividade",
        y="Quantidade",
        text="Quantidade",
        title="Quantidade de O.S. por Atividade"
    )

    fig_atividade.update_traces(
        textposition="outside"
    )

    fig_atividade.update_layout(
        xaxis_title="Atividade",
        yaxis_title="Quantidade de O.S."
    )

    st.plotly_chart(
        fig_atividade,
        use_container_width=True
    )

atividade_count.columns = ["Atividade", "Quantidade"]

with l6c1:
    with st.container():

        fig = px.line(
            eficacia_semanal,
            x="Semana",
            y="Eficacia",
            markers=True,
            title="Evolução da Eficácia (7 dias)",
            hover_data=[
                "MPC",
                "MPD",
                "MCO",
                "Total"
            ]
        )

        fig.update_layout(
            yaxis_title="Eficácia (%)",
            xaxis_title="Período"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

with l7c1:
    with st.expander("Mais Detalhes"):
        st.subheader("Detalhes dos Equipamentos Filtrados")
        st.dataframe(ordens_servico_filtradas, height=400)
