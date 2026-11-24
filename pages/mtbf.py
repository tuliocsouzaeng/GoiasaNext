import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import gspread


# _________________________ Checa se login foi feito ______________________________

if not st.session_state.get("authenticated", False):
    st.warning("Você precisa fazer login para acessar esta página.")
    st.switch_page("index.py")  # Redireciona para a tela de login


# _________________________ Importação dos Dados ______________________________
# Planilhas no Drive (mesmo padrão do indicadores_manutencao):
#   - "Paradas_25_26"   -> aba "Paradas_25_26"   (falhas / paradas)
#   - "Disponibilidade" -> aba "Disponibilidade" (dias efetivos de moagem por dia)
# Para atualizar, basta acrescentar linhas nas planilhas. Cabeçalhos iguais aos arquivos.

PLANILHA_PARADAS = "Paradas_25_26"
ABA_PARADAS = "Paradas_25_26"
PLANILHA_DISP = "Disponibilidade"
ABA_DISP = "Disponibilidade"

TIPO_PROGRAMADA = "PARADA PROGRAMADA"
TIPOS_EXTERNOS = ["CLIMA", "INCENDIO ACIDENTAL"]  # causas fora do controle da manutenção
LOCAIS_EXTERNOS = ["FRENTE DE COLHEITA"]  # equipamentos fora do escopo da indústria
AREAS_EXTERNAS = ["AGRÍCOLA"]  # áreas fora do escopo da indústria (macro-área, antes da barra)


# _________________________ Funções auxiliares ______________________________

def fmt(valor, casas=1, sufixo=""):
    """Formata no padrão brasileiro: 8.417,1 h"""
    if valor is None or pd.isna(valor):
        return "-"
    txt = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{txt}{sufixo}"


def mostrar(fig):
    """Gráficos com separadores brasileiros (decimal = vírgula, milhar = ponto)."""
    fig.update_layout(separators=",.")
    st.plotly_chart(fig, use_container_width=True)


def _parse_datetime(serie):
    """Aceita AAAA-MM-DD[ HH:MM[:SS]] e DD/MM/AAAA[ HH:MM[:SS]] sem trocar dia e mês."""
    s = serie.astype(str).str.strip()
    formatos = [
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
    ]
    out = pd.to_datetime(s, format=formatos[0], errors="coerce")
    for f in formatos[1:]:
        out = out.fillna(pd.to_datetime(s, format=f, errors="coerce"))
    return out


def _para_float(serie):
    """Aceita 0,42 / 0.42 / 1.234,5 e números já numéricos."""
    if pd.api.types.is_numeric_dtype(serie):
        return serie.astype(float)
    s = serie.astype(str).str.strip()
    tem_virgula = s.str.contains(",", regex=False)
    s = s.where(~tem_virgula, s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    return pd.to_numeric(s, errors="coerce")


@st.cache_resource
def get_gspread_client():
    GOOGLE_REDE_CREDS = os.getenv("GOOGLE_REDE_CREDS")
    if isinstance(GOOGLE_REDE_CREDS, str):
        info_autenticacao = json.loads(GOOGLE_REDE_CREDS)
    else:
        info_autenticacao = GOOGLE_REDE_CREDS
    return gspread.service_account_from_dict(info_autenticacao)


@st.cache_data(ttl=300)
def carregar_paradas():
    gc = get_gspread_client()
    aba = gc.open(PLANILHA_PARADAS).worksheet(ABA_PARADAS)
    df = pd.DataFrame(aba.get_all_records())

    df["INICIO"] = _parse_datetime(df["Início (Data/Hora)"])
    df["FIM"] = _parse_datetime(df["Fim (Data/Hora)"])
    df = df.dropna(subset=["INICIO", "FIM"])

    for col in ["Localização", "Área / Setor", "Tipo de Parada"]:
        df[col] = df[col].astype(str).str.strip()
    df["Tipo de Parada"] = df["Tipo de Parada"].str.upper()

    # A duração é recalculada a partir de início/fim (a coluna "Duração (Horas)"
    # pode vir arredondada ou com formatos mistos).
    df["DURACAO_H"] = (df["FIM"] - df["INICIO"]).dt.total_seconds() / 3600
    df = df[df["DURACAO_H"] > 0]
    df["DATA_CONVERTIDA"] = df["INICIO"].dt.normalize()
    df["ANO"] = df["INICIO"].dt.year
    df["MES"] = df["INICIO"].dt.to_period("M").dt.to_timestamp()
    return df.sort_values("INICIO").reset_index(drop=True)


@st.cache_data(ttl=300)
def carregar_disponibilidade():
    gc = get_gspread_client()
    aba = gc.open(PLANILHA_DISP).worksheet(ABA_DISP)
    df = pd.DataFrame(aba.get_all_records())
    df.columns = ["Data", "DIAS_MOAGEM"]
    df["Data"] = _parse_datetime(df["Data"]).dt.normalize()
    df["DIAS_MOAGEM"] = _para_float(df["DIAS_MOAGEM"])
    df = df.dropna(subset=["Data", "DIAS_MOAGEM"])
    # O histórico pode ter blocos repetidos: mantém 1 registro por dia
    df = df.drop_duplicates(subset="Data", keep="last").sort_values("Data")
    df["HORAS_OPERADAS"] = df["DIAS_MOAGEM"] * 24
    df["ANO"] = df["Data"].dt.year
    df["MES"] = df["Data"].dt.to_period("M").dt.to_timestamp()
    return df.reset_index(drop=True)


paradas = carregar_paradas()
disp = carregar_disponibilidade()


# _________________________ Classificações ______________________________

def classificar_safra(data):
    # Safra inicia em abril. Ex.: abr/2025 a mar/2026 = Safra 25
    ano = data.year if data.month >= 4 else data.year - 1
    return f"Safra {str(ano)[-2:]}"


paradas["SAFRA"] = paradas["INICIO"].apply(classificar_safra)
disp["SAFRA"] = disp["Data"].apply(classificar_safra)

# "Área / Setor" -> macro-área (antes da barra) para um gráfico mais limpo
paradas["AREA"] = paradas["Área / Setor"].str.split("/").str[0].str.strip()
paradas.loc[paradas["AREA"].str.startswith("UTIL"), "AREA"] = "UTILIDADES"
paradas.loc[paradas["AREA"].str.startswith("PRODU"), "AREA"] = "PRODUÇÃO"


# _________________________ Aplicação de Filtros _____________________________

data_min = min(disp["Data"].min(), paradas["DATA_CONVERTIDA"].min()).date()
data_max = max(disp["Data"].max(), paradas["DATA_CONVERTIDA"].max()).date()

with st.expander("Abrir Filtros"):
    safra_selecionada = st.multiselect(
        "Selecione a Safra",
        sorted(set(disp["SAFRA"]) | set(paradas["SAFRA"])),
    )
    area_selecionada = st.multiselect(
        "Selecione a Área / Setor",
        sorted(paradas["Área / Setor"].dropna().unique().tolist()),
    )
    tipo_selecionado = st.multiselect(
        "Selecione o Tipo de Parada",
        sorted(paradas["Tipo de Parada"].dropna().unique().tolist()),
    )
    equipamento_selecionado = st.multiselect(
        "Selecione o Equipamento (Localização)",
        sorted(paradas["Localização"].dropna().unique().tolist()),
    )
    incluir_programadas = st.checkbox(
        "Incluir paradas programadas como falha", value=False
    )
    excluir_externas = st.checkbox(
        "Excluir paradas externas (clima, incêndio acidental, Frente de Colheita e área Agrícola)", value=False
    )
    periodo = st.date_input(
        "Período",
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max,
    )

if len(periodo) == 2:
    data_inicial, data_final = periodo
else:
    data_inicial, data_final = data_min, data_max

data_inicial = pd.Timestamp(data_inicial)
data_final = pd.Timestamp(data_final)

# Tempo operado: depende apenas de período e safra (é a moagem da indústria inteira)
disp_f = disp[(disp["Data"] >= data_inicial) & (disp["Data"] <= data_final)]
if safra_selecionada:
    disp_f = disp_f[disp_f["SAFRA"].isin(safra_selecionada)]

# Falhas: período, safra e demais filtros
paradas_f = paradas[
    (paradas["DATA_CONVERTIDA"] >= data_inicial) & (paradas["DATA_CONVERTIDA"] <= data_final)
]
if safra_selecionada:
    paradas_f = paradas_f[paradas_f["SAFRA"].isin(safra_selecionada)]
if area_selecionada:
    paradas_f = paradas_f[paradas_f["Área / Setor"].isin(area_selecionada)]
if equipamento_selecionado:
    paradas_f = paradas_f[paradas_f["Localização"].isin(equipamento_selecionado)]

# Paradas programadas: respeitam período, safra, área e equipamento (não o filtro de tipo)
paradas_programadas = paradas_f[paradas_f["Tipo de Parada"] == TIPO_PROGRAMADA]

if tipo_selecionado:
    paradas_f = paradas_f[paradas_f["Tipo de Parada"].isin(tipo_selecionado)]
if excluir_externas:
    paradas_f = paradas_f[
        ~paradas_f["Tipo de Parada"].isin(TIPOS_EXTERNOS)
        & ~paradas_f["Localização"].str.upper().isin(LOCAIS_EXTERNOS)
        & ~paradas_f["AREA"].str.upper().isin(AREAS_EXTERNAS)
    ]

falhas = paradas_f if incluir_programadas else paradas_f[paradas_f["Tipo de Parada"] != TIPO_PROGRAMADA]


# _______________ Geração de Informações ________________________

horas_operadas = disp_f["HORAS_OPERADAS"].sum()
dias_moagem = disp_f["DIAS_MOAGEM"].sum()
dias_calendario = disp_f["Data"].nunique()
total_falhas = len(falhas)
horas_parada = falhas["DURACAO_H"].sum()
horas_programadas = paradas_programadas["DURACAO_H"].sum()

mtbf = horas_operadas / total_falhas if total_falhas > 0 else None
mttr = horas_parada / total_falhas if total_falhas > 0 else None
taxa_falhas = 1 / mtbf if mtbf else None  # lambda (falhas por hora)
disponibilidade_moagem = dias_moagem / dias_calendario * 100 if dias_calendario > 0 else 0
disponibilidade_inerente = (
    mtbf / (mtbf + mttr) * 100 if (mtbf is not None and (mtbf + mttr) > 0) else None
)

# Evolução mensal
op_mes = disp_f.groupby("MES")["HORAS_OPERADAS"].sum().reset_index()
falhas_mes = (
    falhas.groupby("MES")
    .agg(Falhas=("DURACAO_H", "size"), Horas_Parada=("DURACAO_H", "sum"))
    .reset_index()
)
mensal = op_mes.merge(falhas_mes, on="MES", how="left").fillna({"Falhas": 0, "Horas_Parada": 0})
mensal["MTBF"] = mensal.apply(
    lambda r: r["HORAS_OPERADAS"] / r["Falhas"] if r["Falhas"] > 0 else None, axis=1
)
mensal["MTTR"] = mensal.apply(
    lambda r: r["Horas_Parada"] / r["Falhas"] if r["Falhas"] > 0 else None, axis=1
)
mensal["Mês"] = mensal["MES"].dt.strftime("%m/%Y")


def tabela_mtbf(df_falhas, coluna, nome):
    """MTBF por grupo = horas operadas da indústria / falhas do grupo."""
    t = (
        df_falhas.groupby(coluna)
        .agg(Falhas=("DURACAO_H", "size"), Horas_Parada=("DURACAO_H", "sum"))
        .reset_index()
        .rename(columns={coluna: nome})
    )
    t["MTBF (h)"] = horas_operadas / t["Falhas"]
    t["MTTR (h)"] = t["Horas_Parada"] / t["Falhas"]
    t["λ (falhas/h)"] = 1 / t["MTBF (h)"]
    return t.sort_values("Falhas", ascending=False)


# _________________ Criação da Página ___________________________
st.title("MTBF - Mean Time Between Failures")

# Linha 1
l1c1, l1c2, l1c3, l1c4 = st.columns(4)

# Linha 2
l2c1, l2c2, l2c3, l2c4 = st.columns(4)

# Linha 3 em diante
l3c1 = st.columns(1)[0]
l3bc1 = st.columns(1)[0]
l4c1, l4c2 = st.columns(2)
l5c1 = st.columns(1)[0]
l6c1 = st.columns(1)[0]
l7c1, l7c2 = st.columns(2)
l8c1 = st.columns(1)[0]
l9c1 = st.columns(1)[0]

# __________________ Visualização das Informações ______________

with l1c1:
    st.metric("MTBF", fmt(mtbf, 2, " h"))

    with st.popover("Como é calculado?"):
        st.write("""
        MTBF = Horas Operadas ÷ Número de Falhas

        Horas Operadas = Σ (Dias efetivos de moagem × 24) no período.
        Fonte: Disponibilidade (indústria inteira).

        Número de Falhas = paradas registradas no período, de acordo com os filtros.
        Fonte: Paradas. Por padrão, paradas programadas não contam como falha.

        Quando se filtra por área, tipo ou equipamento, o tempo operado continua sendo o da indústria inteira.
        """)

with l1c2:
    st.metric("MTTR", fmt(mttr, 2, " h"))

    with st.popover("Como é calculado?"):
        st.write("""
        MTTR = Soma das Durações das Paradas ÷ Número de Falhas

        A duração é calculada por Fim − Início de cada parada.
        """)

with l1c3:
    st.metric("Taxa de Falhas (λ)", fmt(taxa_falhas, 4, " falhas/h"))
    if taxa_falhas is not None:
        st.caption(f"≈ {fmt(taxa_falhas * 1000, 1)} falhas a cada 1.000 h operadas")

    with st.popover("Como é calculada?"):
        st.write("""
        λ = 1 ÷ MTBF

        Equivale a Número de Falhas ÷ Horas Operadas.
        Representa a taxa média de falhas por hora de operação.
        """)

with l1c4:
    st.metric("Total de Falhas", fmt(total_falhas, 0))

    with st.popover("Como é calculado?"):
        st.write("""
        Quantidade de paradas no período, sem as paradas programadas (a menos que o filtro seja marcado).
        """)

with l2c1:
    st.metric("Horas Operadas", fmt(horas_operadas, 0, " h"))
    st.caption(f"{fmt(dias_moagem, 1)} dias efetivos de moagem")

with l2c2:
    st.metric("Horas de Parada (falhas)", fmt(horas_parada, 1, " h"))
    if incluir_programadas:
        st.caption("Inclui as paradas programadas.")
    if excluir_externas:
        st.caption("Exclui clima, incêndio acidental, Frente de Colheita e área Agrícola.")

with l2c3:
    st.metric("Horas de Parada (programada)", fmt(horas_programadas, 1, " h"))
    st.caption(f"{len(paradas_programadas)} parada(s) programada(s) - detalhes na seção abaixo.")

with l2c4:
    st.metric(
        "Disponibilidade Inerente",
        fmt(disponibilidade_inerente, 2, "%"),
    )
    st.caption(f"Efetividade de moagem no período: {fmt(disponibilidade_moagem, 1)}%")

    with st.popover("Como é calculada?"):
        st.write("""
        Disponibilidade Inerente = MTBF ÷ (MTBF + MTTR)

        Efetividade de moagem = Σ dias efetivos de moagem ÷ dias do período
        """)

with l3c1:
    fig = go.Figure()
    fig.add_bar(x=mensal["Mês"], y=mensal["Falhas"], name="Falhas", yaxis="y2", opacity=0.35)
    fig.add_trace(
        go.Scatter(x=mensal["Mês"], y=mensal["MTBF"], name="MTBF (h)", mode="lines+markers")
    )
    if mtbf is not None:
        fig.add_hline(y=mtbf, line_dash="dash", annotation_text=f"MTBF do período: {fmt(mtbf, 1)} h")
    fig.update_layout(
        title="Evolução Mensal do MTBF",
        xaxis_title="Mês",
        yaxis=dict(title="MTBF (h)"),
        yaxis2=dict(title="Nº de Falhas", overlaying="y", side="right"),
        legend=dict(orientation="h"),
    )
    mostrar(fig)

with l3bc1:
    if falhas.empty:
        st.info("Sem paradas para os filtros selecionados.")
    else:
        total_ano = falhas.groupby("ANO")["DURACAO_H"].sum().reset_index()

        # Detalhamento por tipo de parada, mostrado ao passar o mouse sobre a barra
        def detalhe_ano(ano):
            g = (
                falhas[falhas["ANO"] == ano]
                .groupby("Tipo de Parada")["DURACAO_H"]
                .sum()
                .sort_values(ascending=False)
            )
            return "<br>".join(f"{tipo}: {fmt(h, 1)} h" for tipo, h in g.items())

        total_ano["Detalhe"] = total_ano["ANO"].apply(detalhe_ano)
        fig = px.bar(
            total_ano,
            x="ANO",
            y="DURACAO_H",
            text=[fmt(v, 0) for v in total_ano["DURACAO_H"]],
            custom_data=["Detalhe"],
            title="Horas de Parada por Ano",
            labels={"ANO": "Ano", "DURACAO_H": "Horas de parada (h)"},
        )
        fig.update_traces(
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Total: %{y:,.1f} h<br><br>%{customdata[0]}<extra></extra>",
        )
        fig.update_xaxes(type="category")
        fig.update_layout(yaxis_title="Horas de parada (h)")
        mostrar(fig)

with l4c1:
    fig = px.bar(
        mensal,
        x="Mês",
        y="MTTR",
        text=mensal["MTTR"].round(2),
        title="Evolução Mensal do MTTR (h)",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis_title="MTTR (h)")
    mostrar(fig)

with l4c2:
    # Comparativo entre safras (respeita período e demais filtros)
    linhas = []
    for safra, g in disp_f.groupby("SAFRA"):
        n = len(falhas[falhas["SAFRA"] == safra])
        h = g["HORAS_OPERADAS"].sum()
        linhas.append({"Safra": safra, "MTBF (h)": h / n if n > 0 else None, "Falhas": n})
    comp_safra = pd.DataFrame(linhas)
    if not comp_safra.empty:
        fig = px.bar(
            comp_safra,
            x="Safra",
            y="MTBF (h)",
            text=comp_safra["MTBF (h)"].round(1),
            hover_data=["Falhas"],
            title="MTBF por Safra",
        )
        fig.update_traces(textposition="outside")
        mostrar(fig)

with l5c1:
    t_area = tabela_mtbf(falhas, "AREA", "Área")
    fig = px.bar(
        t_area,
        x="Área",
        y="Falhas",
        text="Falhas",
        hover_data=["MTBF (h)", "MTTR (h)", "Horas_Parada"],
        title="Falhas por Área",
    )
    fig.update_traces(textposition="outside")
    mostrar(fig)

with l6c1:
    # Pareto por equipamento (horas de parada)
    pareto = (
        falhas.groupby("Localização")
        .agg(Falhas=("DURACAO_H", "size"), Horas_Parada=("DURACAO_H", "sum"))
        .reset_index()
        .sort_values("Horas_Parada", ascending=False)
        .head(15)
    )
    pareto["MTBF (h)"] = horas_operadas / pareto["Falhas"]
    total_h = falhas["DURACAO_H"].sum()
    pareto["Acumulado (%)"] = pareto["Horas_Parada"].cumsum() / total_h * 100 if total_h > 0 else 0

    fig = go.Figure()
    fig.add_bar(
        x=pareto["Localização"],
        y=pareto["Horas_Parada"],
        name="Horas de parada",
        customdata=pareto[["Falhas", "MTBF (h)"]],
        hovertemplate="%{x}<br>Horas: %{y:.1f}<br>Falhas: %{customdata[0]}<br>MTBF: %{customdata[1]:.1f} h<extra></extra>",
    )
    fig.add_trace(
        go.Scatter(
            x=pareto["Localização"],
            y=pareto["Acumulado (%)"],
            name="Acumulado (%)",
            yaxis="y2",
            mode="lines+markers",
        )
    )
    fig.update_layout(
        title="Pareto - 15 Equipamentos com Mais Horas de Parada",
        yaxis=dict(title="Horas de parada"),
        yaxis2=dict(title="Acumulado (%)", overlaying="y", side="right", range=[0, 105]),
        legend=dict(orientation="h"),
    )
    mostrar(fig)

with l7c1:
    t_tipo = tabela_mtbf(falhas, "Tipo de Parada", "Tipo de Parada")
    fig = px.bar(
        t_tipo,
        x="Tipo de Parada",
        y="MTBF (h)",
        text=t_tipo["MTBF (h)"].round(1),
        hover_data=["Falhas", "MTTR (h)"],
        title="MTBF por Tipo de Parada (h)",
    )
    fig.update_traces(textposition="outside")
    mostrar(fig)

with l7c2:
    fig = px.histogram(
        falhas,
        x="DURACAO_H",
        nbins=30,
        title="Distribuição da Duração das Paradas",
        labels={"DURACAO_H": "Duração (h)"},
    )
    fig.update_layout(yaxis_title="Quantidade de paradas")
    mostrar(fig)

with l8c1:
    st.subheader("Paradas Programadas")
    if paradas_programadas.empty:
        st.info("Nenhuma parada programada no período e filtros selecionados.")
    else:
        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("Quantidade", len(paradas_programadas))
        pc2.metric("Horas paradas", fmt(horas_programadas, 1, " h"))
        pc3.metric("Duração média", fmt(paradas_programadas["DURACAO_H"].mean(), 1, " h"))

        tabela_prog = paradas_programadas[
            ["INICIO", "FIM", "Localização", "Área / Setor", "DURACAO_H", "Descrição da Ocorrência"]
        ].rename(
            columns={
                "INICIO": "Início",
                "FIM": "Fim",
                "Localização": "Equipamento",
                "DURACAO_H": "Duração (h)",
                "Descrição da Ocorrência": "Descrição",
            }
        )
        tabela_prog["Duração (h)"] = tabela_prog["Duração (h)"].round(2)
        st.dataframe(tabela_prog, hide_index=True, use_container_width=True)
        st.caption(
            "Estas paradas são planejadas e não entram no MTBF, a menos que o filtro "
            "'Incluir paradas programadas como falha' esteja marcado."
        )

with l9c1:
    with st.expander("Mais Detalhes - Dados Brutos"):
        st.subheader("Paradas (Falhas) Filtradas")
        st.dataframe(paradas_f, height=400)

        st.subheader("Disponibilidade (Dias Efetivos de Moagem) no Período")
        st.dataframe(disp_f, height=400)

        st.subheader("MTBF por Equipamento")
        st.dataframe(tabela_mtbf(falhas, "Localização", "Equipamento"), height=400)
