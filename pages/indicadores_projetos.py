import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import json
import gspread
import os


# ========================================================================================
# 1. VERIFICAÇÃO DE AUTENTICAÇÃO
# ========================================================================================

if not st.session_state.get("authenticated", False):
    st.warning("Você precisa fazer login para acessar esta página.")
    st.switch_page("index.py")


# ========================================================================================
# 2. IMPORTAÇÃO DOS DADOS (Google Sheets via Service Account)
# ========================================================================================

GOOGLE_REDE_CREDS = os.getenv("GOOGLE_REDE_CREDS")

# Permite que as credenciais venham como string JSON ou já como dicionário
origem_creds = GOOGLE_REDE_CREDS
if isinstance(origem_creds, str):
    info_autenticacao = json.loads(origem_creds)
else:
    info_autenticacao = origem_creds

# Autentica e lê a aba "Documentos_Projetos"
gc = gspread.service_account_from_dict(info_autenticacao)
planilha = gc.open_by_key("1WaXw_Kljcf1CE9SjcewpZyTfT2oSndy8ZDMyTFMy8N8")
aba = planilha.worksheet("Documentos_Projetos")
documentos_projetos = pd.DataFrame(aba.get_all_records())


# ========================================================================================
# 3. TRATAMENTO DOS DADOS
# ========================================================================================

# --- Coluna de responsáveis ---
# gspread retorna strings; garante que não haja NaN
documentos_projetos["Responsável da Atividade"] = (
    documentos_projetos["Responsável da Atividade"]
    .fillna("")
    .astype(str)
)

# Lista única de responsáveis para uso nos filtros (split por vírgula)
lista_responsaveis = sorted({
    nome.strip()
    for responsaveis in documentos_projetos["Responsável da Atividade"]
    if responsaveis.strip() != ""
    for nome in responsaveis.split(",")
    if nome.strip() != ""
})

# --- Conversão de datas ---
# O e-click exporta datas em formato "DD/MM/YYYY"; o parâmetro dayfirst=True garante a leitura correta.
colunas_data = [
    "Data Planejada",
    "Inicio Fluxo",
    "Fim Fluxo",
    "Data da Última Atividade",
    "Data da Última Emissão",
    "Data de Importação",
]
for col in colunas_data:
    if col in documentos_projetos.columns:
        documentos_projetos[col] = pd.to_datetime(
            documentos_projetos[col], errors="coerce", dayfirst=True
        )

hoje = pd.to_datetime(datetime.today().date())

# --- Coluna de Status de Prazo ---
# Documentos encerrados (CERTIFICADO, NÃO SE APLICA, CANCELADO) são excluídos do controle de prazo.
STATUS_ENCERRADO = ["CERTIFICADO", "NÃO SE APLICA", "CANCELADO"]

def status_prazo(data, status_documento):
    if status_documento in STATUS_ENCERRADO:
        return "Encerrado"
    if pd.isna(data):
        return "Sem Data"
    if data > hoje:
        return "Dentro do Prazo"
    if data == hoje:
        return "Vence Hoje"
    return "Atrasado"

documentos_projetos["Status Prazo"] = documentos_projetos.apply(
    lambda row: status_prazo(row["Data Planejada"], row["Status Documento"]),
    axis=1,
)

# --- Coluna de Dias de Atraso ---
documentos_projetos["Dias Diferença"] = (
    hoje - documentos_projetos["Data Planejada"]
).dt.days

def classificar_atraso(dias):
    if pd.isna(dias):
        return "Sem Data"
    elif dias < 0:
        return "No Prazo"
    elif dias == 0:
        return "Vence Hoje"
    elif dias <= 7:
        return "Atraso leve (1-7 dias)"
    elif dias <= 30:
        return "Atraso moderado (8-30 dias)"
    else:
        return "Atraso crítico (>30 dias)"

documentos_projetos["Faixa Atraso"] = documentos_projetos["Dias Diferença"].apply(classificar_atraso)

# --- Tempo de Ciclo de Aprovação ---
# Calculado como a diferença em dias entre a abertura e o fechamento do fluxo de aprovação.
# Só faz sentido para documentos que já encerraram o fluxo (Fim Fluxo preenchido).
documentos_projetos["Duração Fluxo (dias)"] = (
    documentos_projetos["Fim Fluxo"] - documentos_projetos["Inicio Fluxo"]
).dt.days

# --- Coluna de Fornecedor (derivada de Diretório) ---
# O padrão do diretório é: "CATEGORIA / FORNECEDOR / SUBPROJETO"
# Extraímos apenas o segundo nível como identificador do fornecedor/projetista.
documentos_projetos["Fornecedor"] = (
    documentos_projetos["Diretório"]
    .str.split(" / ")
    .str[1]
    .fillna("Não informado")
    .str.strip()
)

# --- Coluna de Mês de Importação (para tendência temporal) ---
if "Data de Importação" in documentos_projetos.columns:
    documentos_projetos["Mês Importação"] = (
        documentos_projetos["Data de Importação"].dt.to_period("M").astype(str)
    )

# --- Coluna de Classificação de Revisão (indicador de retrabalho) ---
# Revisão >= 3 é considerada sinal de alto retrabalho no documento.
documentos_projetos["Revisão"] = pd.to_numeric(
    documentos_projetos["Revisão"], errors="coerce"
).fillna(0)

def classificar_revisao(rev):
    if rev == 0:
        return "Rev. 0 (Emissão inicial)"
    elif rev == 1:
        return "Rev. 1"
    elif rev == 2:
        return "Rev. 2"
    else:
        return "Rev. 3+ (Alto retrabalho)"

documentos_projetos["Classe Revisão"] = documentos_projetos["Revisão"].apply(classificar_revisao)


# ========================================================================================
# 4. FILTROS
# ========================================================================================

with st.expander("🔍 Abrir Filtros"):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        disciplina_selecionada = st.multiselect(
            "Disciplina",
            documentos_projetos["Disciplina"].dropna().unique().tolist(),
        )
        status_selecionado = st.multiselect(
            "Status do Documento",
            documentos_projetos["Status Documento"].dropna().unique().tolist(),
        )
    with col_f2:
        responsavel_selecionado = st.multiselect(
            "Responsável",
            lista_responsaveis,
        )
        status_prazo_selecionado = st.multiselect(
            "Situação do Prazo",
            ["Dentro do Prazo", "Vence Hoje", "Atrasado", "Sem Data", "Encerrado"],
        )
    fornecedor_selecionado = st.multiselect(
        "Fornecedor / Projetista",
        sorted(documentos_projetos["Fornecedor"].dropna().unique().tolist()),
    )

# Aplica os filtros em cadeia
df = documentos_projetos.copy()

if disciplina_selecionada:
    df = df[df["Disciplina"].isin(disciplina_selecionada)]
if status_selecionado:
    df = df[df["Status Documento"].isin(status_selecionado)]
if responsavel_selecionado:
    df = df[
        df["Responsável da Atividade"].apply(
            lambda x: any(r.strip() in responsavel_selecionado for r in str(x).split(","))
        )
    ]
if status_prazo_selecionado:
    df = df[df["Status Prazo"].isin(status_prazo_selecionado)]
if fornecedor_selecionado:
    df = df[df["Fornecedor"].isin(fornecedor_selecionado)]


# ========================================================================================
# 5. CÁLCULO DOS INDICADORES
# ========================================================================================

total_docs = len(df)

# Documentos encerrados: CERTIFICADO + NÃO SE APLICA (sucesso/encerramento)
total_certificados = df[df["Status Documento"] == "CERTIFICADO"].shape[0]
perc_certificados = (total_certificados / total_docs * 100) if total_docs > 0 else 0

# Documentos ativos = ainda no fluxo de aprovação
df_ativos = df[~df["Status Documento"].isin(STATUS_ENCERRADO)]
total_ativos = len(df_ativos)

# Documentos atrasados (ativos com prazo vencido)
total_atrasados = df[df["Status Prazo"] == "Atrasado"].shape[0]

# Cancelados
total_cancelados = df[df["Status Documento"] == "CANCELADO"].shape[0]

# Avanço físico médio (apenas documentos ativos, pois certificados têm 0% ou 100% fixo)
avanco_medio = df_ativos["Avanço Físico %"].mean() if total_ativos > 0 else 0

# Tempo médio de aprovação (apenas documentos certificados com as duas datas preenchidas)
df_ciclo = df[
    (df["Status Documento"] == "CERTIFICADO")
    & df["Duração Fluxo (dias)"].notna()
    & (df["Duração Fluxo (dias)"] >= 0)
]
tempo_medio_aprovacao = df_ciclo["Duração Fluxo (dias)"].mean() if len(df_ciclo) > 0 else 0

# Documentos com alto retrabalho (revisão >= 3)
total_alto_retrabalho = df[df["Revisão"] >= 3].shape[0]


# ========================================================================================
# 6. LAYOUT DA PÁGINA — INDICADORES E GRÁFICOS
# ========================================================================================

# st.title("📋 Gestão de Documentos de Projetos")
# st.caption(f"Dados exportados do e-click  •  Atualizado em: {datetime.today().strftime('%d/%m/%Y %H:%M')}")

# st.divider()

# ─── SEÇÃO 1: Cards de KPI ────────────────────────────────────────────────────

st.subheader("Visão Geral")

kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

with kpi1:
    st.metric("Total de Documentos", total_docs)

with kpi2:
    st.metric(
        "Certificados",
        f"{total_certificados}",
        delta=f"{perc_certificados:.1f}% do total",
        delta_color="off",
    )

with kpi3:
    st.metric(
        "Em Fluxo de Aprovação",
        total_ativos,
        help="Documentos ainda no fluxo (não encerrados)",
    )

with kpi4:
    # Usa delta vermelho quando há atrasados
    st.metric(
        "Atrasados",
        total_atrasados,
        delta=f"{(total_atrasados/total_ativos*100):.0f}% dos ativos" if total_ativos > 0 else "—",
        delta_color="inverse",
        help="Documentos ativos com Data Planejada anterior a hoje",
    )

with kpi5:
    st.metric(
        "Ciclo Médio de Aprovação",
        f"{tempo_medio_aprovacao:.0f} dias",
        help="Tempo médio entre Início e Fim do Fluxo para documentos certificados",
    )

with kpi6:
    pass
    # st.metric(
    #     "Avanço Físico Médio",
    #     f"{avanco_medio:.1f}%",
    #     help="Média do campo 'Avanço Físico %' dos documentos ativos",
    # )



st.divider()

# ─── SEÇÃO 2: Status e Disciplina ────────────────────────────────────────────

st.subheader("Distribuição por Status e Disciplina")
col_a, col_b = st.columns(2)

with col_a:
    status_df = (
        df.groupby("Status Documento")
        .size()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    # Paleta de cores por status para facilitar leitura rápida
    cor_status = {
        "CERTIFICADO": "#2ecc71",
        "APROVAÇÃO 01": "#3498db",
        "REVISÃO FINAL": "#f39c12",
        "REVISÃO": "#e67e22",
        "EMISSÃO FINAL": "#9b59b6",
        "CANCELADO": "#e74c3c",
        "NÃO SE APLICA": "#95a5a6",
    }
    status_df["Cor"] = status_df["Status Documento"].map(cor_status).fillna("#bdc3c7")

    fig_status = px.bar(
        status_df,
        x="Status Documento",
        y="Quantidade",
        text="Quantidade",
        title="Documentos por Status",
        color="Status Documento",
        color_discrete_map=cor_status,
    )
    fig_status.update_traces(textposition="outside")
    fig_status.update_layout(
        xaxis_title="Status",
        yaxis_title="Quantidade",
        height=400,
        showlegend=False,
    )
    st.plotly_chart(fig_status, use_container_width=True)

with col_b:
    disciplina_df = (
        df.groupby("Disciplina")
        .size()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )
    fig_disc = px.bar(
        disciplina_df,
        x="Disciplina",
        y="Quantidade",
        text="Quantidade",
        title="Documentos por Disciplina",
        color="Quantidade",
        color_continuous_scale="Blues",
    )
    fig_disc.update_traces(textposition="outside")
    fig_disc.update_layout(
        xaxis_title="Disciplina",
        yaxis_title="Quantidade",
        height=400,
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_disc, use_container_width=True)

# ─── SEÇÃO 3: Avanço Físico e Ciclo de Aprovação por Disciplina ──────────────

st.subheader("Avanço e Performance por Disciplina")
col_c, col_d = st.columns(2)

with col_c:
    # Avanço físico médio por disciplina (todos os documentos do filtro)
    avanco_disc = (
        df.groupby("Disciplina")["Avanço Físico %"]
        .mean()
        .reset_index(name="Avanço Médio (%)")
        .sort_values("Avanço Médio (%)", ascending=True)
    )
    fig_avanco = px.bar(
        avanco_disc,
        x="Avanço Médio (%)",
        y="Disciplina",
        orientation="h",
        text=avanco_disc["Avanço Médio (%)"].apply(lambda v: f"{v:.1f}%"),
        title="Avanço Físico Médio por Disciplina (%)",
        color="Avanço Médio (%)",
        color_continuous_scale="RdYlGn",
        range_color=[0, 100],
    )
    fig_avanco.update_traces(textposition="outside")
    fig_avanco.update_layout(
        height=400,
        coloraxis_showscale=False,
        xaxis=dict(range=[0, 115]),
    )
    st.plotly_chart(fig_avanco, use_container_width=True)

with col_d:
    # Tempo médio de ciclo de aprovação por disciplina
    # Filtra apenas os que passaram pelo fluxo completo (com datas)
    ciclo_disc = (
        df[df["Duração Fluxo (dias)"].notna() & (df["Duração Fluxo (dias)"] >= 0)]
        .groupby("Disciplina")["Duração Fluxo (dias)"]
        .mean()
        .reset_index(name="Dias Médios")
        .sort_values("Dias Médios", ascending=True)
    )
    fig_ciclo = px.bar(
        ciclo_disc,
        x="Dias Médios",
        y="Disciplina",
        orientation="h",
        text=ciclo_disc["Dias Médios"].apply(lambda v: f"{v:.0f}d"),
        title="Tempo Médio de Aprovação por Disciplina (dias)",
        color="Dias Médios",
        color_continuous_scale="RdYlGn_r",  # verde = rápido, vermelho = lento
    )
    fig_ciclo.update_traces(textposition="outside")
    fig_ciclo.update_layout(
        height=400,
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_ciclo, use_container_width=True)

# ─── SEÇÃO 4: Documentos por Responsável e por Fornecedor ────────────────────

st.subheader("Responsáveis e Fornecedores")
col_e, col_f = st.columns(2)

with col_e:
    # Explode responsáveis múltiplos (campo com vírgula)
    resp_df = (
        df.assign(
            **{"Responsável da Atividade": df["Responsável da Atividade"].str.split(",")}
        )
        .explode("Responsável da Atividade")
    )
    resp_df["Responsável da Atividade"] = resp_df["Responsável da Atividade"].str.strip()
    resp_df = resp_df[resp_df["Responsável da Atividade"] != ""]

    resp_status = (
        resp_df
        .groupby(["Responsável da Atividade", "Status Documento"])
        .size()
        .reset_index(name="Quantidade")
    )
    ordem_resp = (
        resp_status.groupby("Responsável da Atividade")["Quantidade"]
        .sum()
        .sort_values(ascending=False)
        .index
    )
    fig_resp = px.bar(
        resp_status,
        x="Responsável da Atividade",
        y="Quantidade",
        color="Status Documento",
        text="Quantidade",
        title="Documentos por Responsável e Status",
        category_orders={"Responsável da Atividade": list(ordem_resp)},
        color_discrete_map={
            "CERTIFICADO": "#2ecc71",
            "APROVAÇÃO 01": "#3498db",
            "REVISÃO FINAL": "#f39c12",
            "REVISÃO": "#e67e22",
            "EMISSÃO FINAL": "#9b59b6",
            "CANCELADO": "#e74c3c",
            "NÃO SE APLICA": "#95a5a6",
        },
    )
    fig_resp.update_layout(barmode="stack", height=450, legend_title="Status")
    fig_resp.update_traces(textposition="inside")
    st.plotly_chart(fig_resp, use_container_width=True)

with col_f:
    # Top 12 fornecedores por quantidade de documentos
    forn_df = (
        df.groupby("Fornecedor")
        .size()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=True)
        .tail(12)  # Exibe apenas os 12 maiores para não poluir
    )
    fig_forn = px.bar(
        forn_df,
        x="Quantidade",
        y="Fornecedor",
        orientation="h",
        text="Quantidade",
        title="Top 12 Fornecedores / Projetistas por Volume de Documentos",
        color="Quantidade",
        color_continuous_scale="Blues",
    )
    fig_forn.update_traces(textposition="outside")
    fig_forn.update_layout(
        height=450,
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_forn, use_container_width=True)

# ─── SEÇÃO 5: Prazo, Retrabalho e Finalidade ─────────────────────────────────

st.subheader("Prazo, Retrabalho e Maturidade dos Documentos")
col_g, col_h, col_i = st.columns(3)

with col_g:
    # Status de prazo (exclui encerrados para focar no que ainda importa)
    df_prazo = (
        df[df["Status Prazo"] != "Encerrado"]
        .groupby("Status Prazo")
        .size()
        .reset_index(name="Quantidade")
    )
    cor_prazo = {
        "Dentro do Prazo": "#2ecc71",
        "Vence Hoje": "#f39c12",
        "Atrasado": "#e74c3c",
        "Sem Data": "#95a5a6",
    }
    fig_prazo = px.pie(
        df_prazo,
        names="Status Prazo",
        values="Quantidade",
        title="Status de Prazo (Documentos Ativos)",
        color="Status Prazo",
        color_discrete_map=cor_prazo,
        hole=0.4,
    )
    fig_prazo.update_traces(textinfo="label+value")
    fig_prazo.update_layout(height=380, showlegend=False)
    st.plotly_chart(fig_prazo, use_container_width=True)

with col_h:
    # Distribuição de revisões — indicador de retrabalho
    rev_df = (
        df.groupby("Classe Revisão")
        .size()
        .reset_index(name="Quantidade")
    )
    # Ordena manualmente para aparecer em sequência lógica
    ordem_rev = [
        "Rev. 0 (Emissão inicial)",
        "Rev. 1",
        "Rev. 2",
        "Rev. 3+ (Alto retrabalho)",
    ]
    rev_df["Classe Revisão"] = pd.Categorical(
        rev_df["Classe Revisão"], categories=ordem_rev, ordered=True
    )
    rev_df = rev_df.sort_values("Classe Revisão")

    cor_rev = {
        "Rev. 0 (Emissão inicial)": "#2ecc71",
        "Rev. 1": "#3498db",
        "Rev. 2": "#f39c12",
        "Rev. 3+ (Alto retrabalho)": "#e74c3c",
    }
    fig_rev = px.bar(
        rev_df,
        x="Classe Revisão",
        y="Quantidade",
        text="Quantidade",
        title=f"Distribuição de Revisões (Retrabalho)<br><sup>{total_alto_retrabalho} docs com Rev. 3+</sup>",
        color="Classe Revisão",
        color_discrete_map=cor_rev,
    )
    fig_rev.update_traces(textposition="outside")
    fig_rev.update_layout(height=380, showlegend=False, xaxis_title="")
    st.plotly_chart(fig_rev, use_container_width=True)

with col_i:
    # Finalidade da última emissão — maturidade do documento no ciclo de aprovação
    final_df = df[
        df["Finalidade Última Emissão"].notna()
        & (df["Finalidade Última Emissão"].astype(str).str.strip() != "")
    ]
    final_count = (
        final_df["Finalidade Última Emissão"]
        .value_counts()
        .reset_index(name="Quantidade")
        .rename(columns={"index": "Finalidade"})
    )
    # Abreviação para legibilidade no gráfico
    abrev = {
        "LIBERADO PARA CONSTRUÇÃO": "Lib. Construção",
        "COMENTÁRIOS/APROVAÇÃO": "Coment./Aprov.",
        "REFERÊNCIA/CONHECIMENTO/ARQUIVO": "Ref./Arquivo",
        "LIBERADO PARA COMPRA": "Lib. Compra",
        "LIBERADO PARA FABRICAÇÃO": "Lib. Fabricação",
    }
    final_count["Finalidade Curta"] = (
        final_count["Finalidade Última Emissão"].map(abrev).fillna(final_count["Finalidade Última Emissão"])
    )
    fig_final = px.bar(
        final_count,
        x="Finalidade Curta",
        y="Quantidade",
        title="Finalidade da Última Emissão",
        color="Finalidade Curta",
        color_discrete_sequence=px.colors.qualitative.Set2,
        text="Quantidade",
    )

    fig_final.update_traces(textposition="outside")
    fig_final.update_layout(
        height=380,
        showlegend=False,
        xaxis_title="Finalidade",
        yaxis_title="Quantidade",
    )

    st.plotly_chart(fig_final, use_container_width=True)

# ─── SEÇÃO 6: Tendência Temporal de Importações ───────────────────────────────

st.subheader("Tendência de Entrada de Documentos")

if "Mês Importação" in df.columns and df["Mês Importação"].notna().any():
    tend_df = (
        df.groupby("Mês Importação")
        .size()
        .reset_index(name="Documentos Importados")
        .sort_values("Mês Importação")
    )
    fig_tend = px.area(
        tend_df,
        x="Mês Importação",
        y="Documentos Importados",
        text="Documentos Importados",
        title="Documentos Importados por Mês (volume de entregáveis recebidos no e-click)",
        markers=True,
        color_discrete_sequence=["#3498db"],
    )
    fig_tend.update_traces(textposition="top center")
    fig_tend.update_layout(
        xaxis_title="Mês",
        yaxis_title="Quantidade",
        height=350,
    )
    st.plotly_chart(fig_tend, use_container_width=True)

# ─── SEÇÃO 7: Alertas — Documentos Críticos em Aprovação ─────────────────────

st.subheader("⚠️ Documentos em Aprovação (Ação Necessária)")

df_aprovacao = df[
    df["Status Documento"].isin(["APROVAÇÃO 01", "REVISÃO FINAL", "REVISÃO", "EMISSÃO FINAL"])
].copy()

if len(df_aprovacao) > 0:
    # Ordena: atrasados primeiro, depois por data planejada mais antiga
    df_aprovacao["_atrasado"] = df_aprovacao["Status Prazo"] == "Atrasado"
    df_aprovacao = df_aprovacao.sort_values(
        ["_atrasado", "Data Planejada"], ascending=[False, True]
    )

    colunas_alerta = [
        "Código",
        "Título",
        "Disciplina",
        "Status Documento",
        "Responsável da Atividade",
        "Data Planejada",
        "Status Prazo",
        "Faixa Atraso",
        "Avanço Físico %",
    ]
    colunas_existentes = [c for c in colunas_alerta if c in df_aprovacao.columns]

    st.dataframe(
        df_aprovacao[colunas_existentes].drop(columns=["_atrasado"], errors="ignore"),
        height=400,
        use_container_width=True,
    )
else:
    st.success("Nenhum documento ativo no momento. Todos estão certificados, cancelados ou classificados como 'Não se aplica'.")

# ─── SEÇÃO 8: Tabela Completa (expansível) ────────────────────────────────────

with st.expander("📄 Ver Tabela Completa de Documentos"):
    st.caption(f"{len(df)} documentos exibidos com os filtros atuais.")
    st.dataframe(df, height=500, use_container_width=True)
