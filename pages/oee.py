import re
import math
import unicodedata

import numpy as np
import pandas as pd


# =============================================================================
# MOTOR DE CÁLCULO DO OEE  (início)
# Funções puras: não dependem de Streamlit nem do Google Sheets.
# =============================================================================

# ---------------------------- Configurações ----------------------------------

META_EFICIENCIA_GLOBAL = 0.92      # meta de referência da Eficiência Global (configurável)
TEMPO_PROGRAMADO_H_DIA = 24.0      # horas programadas por dia presente na base
FIBRA_MIN, FIBRA_MAX, FIBRA_PASSO = 11.00, 16.00, 0.25
REGIMES = {"convencional", "organico"}
KG_POR_SACA = 50.0                 # 12723 está em sacas de 50 kg
TOLERANCIA_REGIME = 0.001          # 12723 >= 99,9% do açúcar do dia => dia 100% convencional
MAX_DIAS_DESVIO_ISOLADO = 2        # até N dias seguidos "convencionais" entre dias orgânicos = desvio
P_MAX_PLAUSIVEL = 2.0              # dia com P acima de 2x a referência é tratado como erro de dado
METODO_TCH_EFETIVO = "tch_efetivo"       # P = 12777 / TCH de referência do regime
METODO_HORAS_MOAGEM = "horas_moagem"     # P = cana / (horas de moagem 10884 x TCH de referência)

CAPACIDADE_TCH_POR_FIBRA = {
    11.00: {"convencional": 712,   "organico": 565.1},
    11.25: {"convencional": 708,   "organico": 562.5},
    11.50: {"convencional": 705,   "organico": 559.9},
    11.75: {"convencional": 702,   "organico": 557.3},
    12.00: {"convencional": 699,   "organico": 554.8},
    12.25: {"convencional": 695,   "organico": 552.2},
    12.50: {"convencional": 692,   "organico": 549.8},
    12.75: {"convencional": 689,   "organico": 547.3},
    13.00: {"convencional": 686,   "organico": 544.8},
    13.25: {"convencional": 683,   "organico": 542.4},
    13.50: {"convencional": 680,   "organico": 540.0},
    13.75: {"convencional": 677,   "organico": 537.6},
    14.00: {"convencional": 674,   "organico": 535.3},
    14.25: {"convencional": 671,   "organico": 532.9},
    14.50: {"convencional": 668,   "organico": 530.6},
    14.75: {"convencional": 665,   "organico": 528.3},
    15.00: {"convencional": 662,   "organico": 526.0},
    15.25: {"convencional": 660,   "organico": 523.7},
    15.50: {"convencional": 657,   "organico": 521.5},
    15.75: {"convencional": 654,   "organico": 519.3},
    16.00: {"convencional": 651,   "organico": 517.1},
}

# Códigos das colunas do CSV/planilha "Desempenho" (o prefixo "2015" do cabeçalho é ignorado)
COLUNAS_POR_CODIGO = {
    "11029": "acucar_total_kg",         # Prod. total de açúcar (kg)
    "13416": "pct_acucar_conv",         # Açúcar ESP/SUP/A400 % (convencional)
    "18019": "pct_acucar_org",          # Açúcar ESP-SUP-ORG % (orgânico)
    "12723": "acucar_conv_sc",          # Prod. açúcar convencional (sc 50 kg)
    "7520":  "etanol_m3",               # Prod. total etanol (m3)
    "2973":  "ef_global_pct",           # Eficiência global (%)
    "10884": "aproveit_moagem_pct",     # Aproveitamento do tempo de moagem (%)
    "12777": "tch_efetivo",             # Cana/hora efetiva (t/h)
    "12513": "cana_t",                  # Cana total moída (t)
    "12726": "ef_etanol_pct",           # Eficiência global - etanol (%)
    "12725": "ef_acucar_pct",           # Eficiência global - açúcar (%)
    "211":   "fibra_pct",               # Fibra % cana
    "19698": "etanol_recuperado_m3",    # Total de etanol recuperado (m3)
    "9452":  "etanol_reclass_l",        # Entrada total de etanol reclassificado (L)
}

_TABELA_TCH_CONV = np.array(
    [CAPACIDADE_TCH_POR_FIBRA[k]["convencional"] for k in sorted(CAPACIDADE_TCH_POR_FIBRA)], dtype=float
)
_TABELA_TCH_ORG = np.array(
    [CAPACIDADE_TCH_POR_FIBRA[k]["organico"] for k in sorted(CAPACIDADE_TCH_POR_FIBRA)], dtype=float
)


# ------------------------- Referência de TCH ---------------------------------

def _normalizar_regime(regime: str) -> str:
    txt = unicodedata.normalize("NFKD", str(regime)).encode("ascii", "ignore").decode().strip().lower()
    if txt not in REGIMES:
        raise ValueError(f"Regime inválido: {regime!r}. Use 'convencional' ou 'organico'.")
    return txt


def _fibra_para_grade(fibra_pct: float) -> float:
    """Arredonda para o múltiplo de 0,25 mais próximo (meio sobe) e limita a [11,00; 16,00]."""
    if fibra_pct is None or (isinstance(fibra_pct, float) and math.isnan(fibra_pct)):
        raise ValueError("fibra_pct não informada (NaN).")
    arredondada = math.floor(float(fibra_pct) / FIBRA_PASSO + 0.5) * FIBRA_PASSO
    return round(min(max(arredondada, FIBRA_MIN), FIBRA_MAX), 2)


def obter_tch_referencia(fibra_pct: float, regime: str) -> float:
    """TCH máximo teórico para a fibra (% cana) e o regime ('convencional' ou 'organico')."""
    regime = _normalizar_regime(regime)
    return float(CAPACIDADE_TCH_POR_FIBRA[_fibra_para_grade(fibra_pct)][regime])


def obter_tch_referencia_ponderado(fibra_pct: float, horas_convencional: float, horas_organico: float) -> float:
    """TCH de referência ponderado pelas horas de cada regime no dia (operação mista)."""
    if horas_convencional < 0 or horas_organico < 0:
        raise ValueError("As horas por regime não podem ser negativas.")
    total = horas_convencional + horas_organico
    if total <= 0:
        raise ValueError("Informe horas_convencional e/ou horas_organico maiores que zero.")
    tch_c = obter_tch_referencia(fibra_pct, "convencional")
    tch_o = obter_tch_referencia(fibra_pct, "organico")
    return (horas_convencional * tch_c + horas_organico * tch_o) / total


def tch_referencia_vetorizado(fibra_pct: pd.Series, fracao_org: pd.Series) -> pd.Series:
    """Versão em série de obter_tch_referencia_ponderado (fracao_org = parcela orgânica, 0 a 1)."""
    f = pd.to_numeric(fibra_pct, errors="coerce").astype(float)
    grade = np.floor(f / FIBRA_PASSO + 0.5) * FIBRA_PASSO
    grade = grade.clip(FIBRA_MIN, FIBRA_MAX)
    idx = np.rint((grade - FIBRA_MIN) / FIBRA_PASSO)
    idx = idx.where(~idx.isna(), 0).astype(int).to_numpy()
    tch_c = pd.Series(_TABELA_TCH_CONV[idx], index=f.index).where(~f.isna())
    tch_o = pd.Series(_TABELA_TCH_ORG[idx], index=f.index).where(~f.isna())
    frac = pd.to_numeric(fracao_org, errors="coerce").clip(0, 1)
    return (1 - frac) * tch_c + frac * tch_o


# ------------------------- Preparação da base --------------------------------

def padronizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Renomeia '2015 11029 - Prod. total de açúcar (kg)' -> 'acucar_total_kg' (pelo código)."""
    novos = {}
    for col in df.columns:
        if str(col).strip().lower() == "data":
            novos[col] = "Data"
            continue
        m = re.match(r"^\s*\d+\s+(\d+)\s*-", str(col))
        if m and m.group(1) in COLUNAS_POR_CODIGO:
            novos[col] = COLUNAS_POR_CODIGO[m.group(1)]
    out = df.rename(columns=novos)
    faltando = [n for n in ["Data", *COLUNAS_POR_CODIGO.values()] if n not in out.columns
                and n not in ("etanol_recuperado_m3", "ef_etanol_pct", "ef_acucar_pct")]
    if faltando:
        raise ValueError(f"Colunas não encontradas na base de Desempenho: {faltando}")
    return out


def calcular_oee_diario(
    base: pd.DataFrame,
    meta_ef: float = META_EFICIENCIA_GLOBAL,
    zero_como_nao_informado: bool = False,
    max_dias_desvio_isolado: int = MAX_DIAS_DESVIO_ISOLADO,
    metodo_desempenho: str = METODO_TCH_EFETIVO,
    p_max_plausivel: float = P_MAX_PLAUSIVEL,
) -> pd.DataFrame:
    """Calcula D, P, Q e OEE de cada dia (com todas as colunas auxiliares para consolidar).

    zero_como_nao_informado: se True, um % de açúcar especificado igual a 0 em dia COM produção
    do regime é tratado como não informado (usa o outro percentual ou deixa o açúcar fora do Q do dia).
    max_dias_desvio_isolado: até N dias seguidos com 12723 = 100% do açúcar, entre dias orgânicos,
    são tratados como açúcar orgânico desviado (0 desativa).
    metodo_desempenho: "tch_efetivo" (12777 ÷ TCH de referência) ou "horas_moagem" (método anterior).
    p_max_plausivel: dia com P acima desse valor (x a referência) é descartado do P como erro de dado
    (0 desativa). Valores acima de 1,0 abaixo desse limite continuam valendo (dias de pico).
    """
    d = base.copy().sort_values("Data").reset_index(drop=True)
    num = ["acucar_total_kg", "pct_acucar_conv", "pct_acucar_org", "acucar_conv_sc", "etanol_m3",
           "ef_global_pct", "aproveit_moagem_pct", "cana_t", "fibra_pct", "etanol_reclass_l", "tch_efetivo"]
    for c in num:
        d[c] = pd.to_numeric(d[c], errors="coerce")

    # --- Regime: um dia produz um único regime.
    # 12723 = açúcar que saiu como CONVENCIONAL (sc de 50 kg).
    #   * 12723 = 0 com açúcar produzido ................ dia ORGÂNICO
    #   * 12723 = todo o açúcar do dia .................. dia CONVENCIONAL
    #   * 12723 > 0, mas menor que o açúcar do dia ...... dia ORGÂNICO; o 12723 é açúcar orgânico
    #                                                      que sofreu desvio (não pôde ser classificado)
    #   * 1 a N dias com 12723 = 100% entre dias orgânicos: também desvio (dia ORGÂNICO)
    total_kg = d["acucar_total_kg"].fillna(0).clip(lower=0)
    conv_col_kg = np.minimum((d["acucar_conv_sc"].fillna(0) * KG_POR_SACA).clip(lower=0), total_kg)
    prod = total_kg > 0
    conv_integral = prod & (conv_col_kg > 0) & (conv_col_kg >= total_kg * (1 - TOLERANCIA_REGIME))
    reg = pd.Series(index=d.index, dtype=object)
    reg[prod & conv_integral] = "convencional"
    reg[prod & ~conv_integral] = "organico"

    d["desvio_isolado"] = False
    if max_dias_desvio_isolado > 0 and prod.any():
        pr = pd.DataFrame({"Data": d.loc[prod, "Data"], "reg": reg[prod]})
        pr["run"] = (pr["reg"] != pr["reg"].shift()).cumsum()
        n = len(pr)
        for _, g in pr.groupby("run"):
            if g["reg"].iloc[0] != "convencional" or len(g) > max_dias_desvio_isolado:
                continue
            p0, p1 = pr.index.get_loc(g.index[0]), pr.index.get_loc(g.index[-1])
            if p0 == 0 or p1 == n - 1:
                continue
            ant, prox = pr.iloc[p0 - 1], pr.iloc[p1 + 1]
            if (ant["reg"] == "organico" and prox["reg"] == "organico"
                    and (g["Data"].iloc[0] - ant["Data"]).days <= 3
                    and (prox["Data"] - g["Data"].iloc[-1]).days <= 3):
                reg.loc[g.index] = "organico"
                d.loc[g.index, "desvio_isolado"] = True

    # Dias de moagem sem açúcar (só etanol) herdam o último regime conhecido
    d["regime_herdado"] = reg.isna()
    reg = reg.ffill().bfill()
    d["regime_dia"] = reg
    d["fracao_org"] = (reg == "organico").astype(float)
    d["acucar_kg"] = total_kg
    d["conv_kg"] = np.where(reg == "convencional", total_kg, 0.0)
    d["org_kg"] = np.where(reg == "organico", total_kg, 0.0)
    d["desvio_org_kg"] = np.where((reg == "organico") & prod, conv_col_kg, 0.0)

    # --- Fibra: dias sem medição usam o último valor conhecido
    d["fibra_faltante"] = d["fibra_pct"].isna()
    d["fibra_usada"] = d["fibra_pct"].ffill().bfill()
    d["tch_ref"] = tch_referencia_vetorizado(d["fibra_usada"], d["fracao_org"])
    d["fibra_grade"] = (np.floor(d["fibra_usada"] / FIBRA_PASSO + 0.5) * FIBRA_PASSO).clip(FIBRA_MIN, FIBRA_MAX)
    d["fibra_fora_faixa"] = (d["fibra_usada"] < FIBRA_MIN - FIBRA_PASSO / 2) | (d["fibra_usada"] > FIBRA_MAX + FIBRA_PASSO / 2)

    # --- Disponibilidade
    d["tempo_programado_h"] = TEMPO_PROGRAMADO_H_DIA
    d["D"] = (d["aproveit_moagem_pct"] / 100.0).clip(0, 1)
    d["tempo_moagem_h"] = d["D"] * d["tempo_programado_h"]

    # --- Desempenho (pode passar de 1,0 em dias de pico)
    # Método padrão: TCH efetivo (12777) comparado com o TCH de referência do regime do dia.
    # As "horas de desempenho" são as horas implícitas no 12777 (cana ÷ 12777) e servem de peso
    # na consolidação: P_período = Σ cana ÷ Σ (horas × TCH de referência).
    if metodo_desempenho == METODO_HORAS_MOAGEM:
        d["horas_p_h"] = d["tempo_moagem_h"].where(d["tempo_moagem_h"] > 0)
    else:
        d["horas_p_h"] = (d["cana_t"] / d["tch_efetivo"]).where((d["tch_efetivo"] > 0) & (d["cana_t"] > 0))
    cap = d["horas_p_h"] * d["tch_ref"]
    p_dia = d["cana_t"] / cap
    d["P_bruto"] = p_dia
    d["p_descartado"] = (p_dia > p_max_plausivel) if p_max_plausivel and p_max_plausivel > 0 else False
    d["p_valido"] = d["horas_p_h"].notna() & ~d["p_descartado"]
    d["cap_teorica_t"] = cap.where(d["p_valido"])
    d["P"] = p_dia.where(d["p_valido"])

    # --- Qualidade: eficiência global
    d["ef_valida"] = d["ef_global_pct"].notna()
    d["ef_clip"] = d["ef_global_pct"].clip(0, 100)
    d["q_global"] = (d["ef_global_pct"] / 100.0 / meta_ef).clip(0, 1)

    # --- Qualidade: etanol
    d["reclass_m3"] = d["etanol_reclass_l"].fillna(0) / 1000.0
    d["etanol_pos_m3"] = d["etanol_m3"].where(d["etanol_m3"] > 0, 0).fillna(0)
    q_et = (1.0 - d["reclass_m3"] / d["etanol_m3"]).clip(lower=0)
    d["q_etanol"] = np.where(d["etanol_m3"] > 0, q_et, 1.0)

    # --- Qualidade: açúcar (% especificado do regime do dia: 13416 convencional, 18019 orgânico)
    qc = (d["pct_acucar_conv"] / 100.0).clip(0, 1)
    qo = (d["pct_acucar_org"] / 100.0).clip(0, 1)
    if zero_como_nao_informado:
        qc = qc.where(~((qc == 0) & (d["conv_kg"] > 0)))
        qo = qo.where(~((qo == 0) & (d["org_kg"] > 0)))
    q_reg = pd.Series(
        np.where(d["regime_dia"] == "convencional", qc.fillna(qo), qo.fillna(qc)), index=d.index
    )                                                    # se só um % foi informado, usa o disponível
    ok = prod & q_reg.notna()
    d["ac_pct_ok"] = ok
    d["ac_qnum_kg"] = np.where(ok, d["acucar_kg"] * q_reg.fillna(0), 0.0)
    d["q_acucar"] = q_reg.where(ok)

    # --- Conformidade: média ponderada pelos volumes (açúcar em t, etanol em m3)
    w_a = np.where(ok, d["acucar_kg"] / 1000.0, 0.0)
    w_e = d["etanol_pos_m3"].to_numpy()
    soma_w = w_a + w_e
    num_conf = w_a * d["q_acucar"].fillna(0).to_numpy() + w_e * d["q_etanol"].to_numpy()
    d["q_conformidade"] = pd.Series(np.where(soma_w > 0, num_conf / np.where(soma_w > 0, soma_w, 1), np.nan), index=d.index)

    d["Q"] = d["q_global"] * d["q_conformidade"]
    d["OEE"] = d["D"] * d["P"] * d["Q"]
    return d


# ------------------------- Consolidação por período --------------------------

def consolidar(d: pd.DataFrame, meta_ef: float = META_EFICIENCIA_GLOBAL) -> dict:
    """Consolida um período somando os totais (nunca média simples de percentuais diários)."""
    nan = float("nan")
    t_prog = d["tempo_programado_h"].sum()
    t_moagem = d["tempo_moagem_h"].sum()
    D = t_moagem / t_prog if t_prog > 0 else nan

    v = d[d["p_valido"]]
    cap = v["cap_teorica_t"].sum()
    moida_v = v["cana_t"].sum()
    P = moida_v / cap if cap > 0 else nan

    e = d[d["ef_valida"]]
    peso_ef = e["cana_t"].sum()
    ef_pond = (e["ef_clip"] * e["cana_t"]).sum() / peso_ef if peso_ef > 0 else nan
    q_global = min(1.0, max(0.0, ef_pond / 100.0 / meta_ef)) if not math.isnan(ef_pond) else nan

    a = d[d["ac_pct_ok"]]
    kg = a["acucar_kg"].sum()
    q_acucar = a["ac_qnum_kg"].sum() / kg if kg > 0 else nan
    et = d[d["etanol_m3"] > 0]
    vol_et = et["etanol_m3"].sum()
    q_etanol = max(0.0, 1.0 - et["reclass_m3"].sum() / vol_et) if vol_et > 0 else 1.0
    w_a, w_e = kg / 1000.0, vol_et
    if w_a + w_e > 0:
        q_conf = ((w_a * q_acucar if w_a > 0 else 0.0) + w_e * q_etanol) / (w_a + w_e)
    else:
        q_conf = nan
    Q = q_global * q_conf if not (math.isnan(q_global) or math.isnan(q_conf)) else nan
    oee = D * P * Q if not any(math.isnan(x) for x in (D, P, Q)) else nan

    return {
        "D": D, "P": P, "Q": Q, "OEE": oee,
        "q_global": q_global, "q_conformidade": q_conf, "q_acucar": q_acucar, "q_etanol": q_etanol,
        "ef_global_pond_pct": ef_pond,
        "tempo_programado_h": t_prog, "tempo_moagem_h": t_moagem,
        "cana_t": d["cana_t"].sum(), "cana_p_t": moida_v, "capacidade_teorica_t": cap,
        "tch_real": moida_v / v["horas_p_h"].sum() if v["horas_p_h"].sum() > 0 else nan,
        "tch_ref": cap / v["horas_p_h"].sum() if v["horas_p_h"].sum() > 0 else nan,
        "dias_p_descartados": int(d["p_descartado"].sum()),
        "acucar_t": kg / 1000.0, "etanol_m3": vol_et,
        "dias": int(len(d)), "dias_p_maior_1": int((d["P"] > 1.0).sum()),
        "dias_conv": int((d["regime_dia"] == "convencional").sum()),
        "dias_org": int((d["regime_dia"] == "organico").sum()),
        "dias_desvio_isolado": int(d["desvio_isolado"].sum()),
        "desvio_org_t": d["desvio_org_kg"].sum() / 1000.0,
        "acucar_org_t": d["org_kg"].sum() / 1000.0,
    }


def consolidar_por(d: pd.DataFrame, chave: str, meta_ef: float = META_EFICIENCIA_GLOBAL) -> pd.DataFrame:
    linhas = []
    for k, g in d.groupby(chave, sort=True):
        linha = consolidar(g, meta_ef)
        linha[chave] = k
        linhas.append(linha)
    return pd.DataFrame(linhas)


COLUNAS_PERCENTUAIS = ["aproveit_moagem_pct", "ef_global_pct", "pct_acucar_conv", "pct_acucar_org", "fibra_pct"]


def normalizar_escalas(base: pd.DataFrame):
    """Detecta colunas em % que vieram como fração (0 a 1, ex.: célula formatada como porcentagem
    no Google Sheets devolve 0,25 para 25%) e converte para %. Retorna (base, avisos)."""
    b = base.copy()
    avisos = []
    for col in COLUNAS_PERCENTUAIS:
        if col not in b.columns:
            continue
        x = pd.to_numeric(b[col], errors="coerce")
        v = x.dropna()
        # Percentil 95 (e não o máximo): uma coluna em % real tem valores bem acima de 1, e um
        # lançamento absurdo isolado não impede a detecção de uma coluna inteira em fração.
        if len(v) >= 20 and 0 < v.abs().quantile(0.95) <= 1.0 + 1e-9:
            b[col] = x * 100.0
            avisos.append(f"A coluna '{col}' estava em fração (0 a 1) e foi convertida para %. "
                          "Confira o formato das células na planilha.")
    return b, avisos


def validar_escalas(diario: pd.DataFrame) -> list:
    """Avisos de dados fora de escala que distorcem o cálculo."""
    avisos = []
    com_cana = diario[diario["cana_t"] > 0]
    if len(com_cana) >= 20:
        med = com_cana["cana_t"].median()
        if med < 1000 or med > 40000:
            avisos.append(f"Mediana de cana moída por dia = {med:,.0f} t (esperado de 10.000 a 17.000 t). "
                          "Verifique se a coluna 12513 está em toneladas.".replace(",", "."))
    n_fibra = int((diario["fibra_fora_faixa"] & ~diario["fibra_faltante"]).sum())
    if n_fibra > 0:
        avisos.append(f"{n_fibra} dia(s) com fibra fora de 11% a 16% (o TCH de referência é limitado ao extremo da tabela). "
                      "Se a fibra do dia deveria estar dentro da faixa, confira a coluna 211.")
    n_apr = int((diario["aproveit_moagem_pct"] > 100.0001).sum())
    if n_apr > 0:
        avisos.append(f"{n_apr} dia(s) com aproveitamento do tempo de moagem acima de 100% (limitado a 100%).")
    return avisos


def classificar_safra(data) -> str:
    """Safra começa em abril. Ex.: abr/2025 a mar/2026 = Safra 25."""
    ano = data.year if data.month >= 4 else data.year - 1
    return f"Safra {str(ano)[-2:]}"

# =============================================================================
# MOTOR DE CÁLCULO DO OEE  (fim)
# =============================================================================


import streamlit as st
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
# Planilha no Drive (mesmo padrão do MTBF): "Desempenho" -> aba "Desempenho"
# Para atualizar, basta acrescentar linhas (um dia por linha), mantendo os cabeçalhos.

PLANILHA_DESEMPENHO = "Desempenho"
ABA_DESEMPENHO = "Desempenho"


def fmt(valor, casas=1, sufixo=""):
    """Formata no padrão brasileiro: 8.417,1 h"""
    if valor is None or pd.isna(valor):
        return "-"
    txt = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{txt}{sufixo}"


def pct(valor, casas=1):
    return fmt(None if valor is None or pd.isna(valor) else valor * 100, casas, "%")


def mostrar(fig):
    """Gráficos com separadores brasileiros (decimal = vírgula, milhar = ponto)."""
    fig.update_layout(separators=",.")
    st.plotly_chart(fig, use_container_width=True)


def _parse_data(serie):
    """Aceita número de série do Sheets, AAAA-MM-DD e DD/MM/AAAA."""
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_datetime(serie, unit="D", origin="1899-12-30", errors="coerce")
    s = serie.astype(str).str.strip()
    out = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    for f in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S"):
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
def carregar_desempenho():
    gc = get_gspread_client()
    aba = gc.open(PLANILHA_DESEMPENHO).worksheet(ABA_DESEMPENHO)
    # UNFORMATTED_VALUE: números chegam como números, independentemente do idioma da planilha
    registros = aba.get_all_records(value_render_option="UNFORMATTED_VALUE")
    df = padronizar_colunas(pd.DataFrame(registros))
    df["Data"] = _parse_data(df["Data"]).dt.normalize()
    df = df.dropna(subset=["Data"])
    for col in df.columns:
        if col != "Data":
            df[col] = _para_float(df[col])
    # Um registro por dia (se houver repetição, vale o último lançado)
    df = df.drop_duplicates(subset="Data", keep="last").sort_values("Data").reset_index(drop=True)
    return df


base, avisos_escala = normalizar_escalas(carregar_desempenho())


# _________________________ Aplicação de Filtros _____________________________

data_min, data_max = base["Data"].min().date(), base["Data"].max().date()
safras_disponiveis = sorted({classificar_safra(x) for x in base["Data"]})

with st.expander("Abrir Filtros"):
    safra_selecionada = st.multiselect("Selecione a Safra", safras_disponiveis)
    regime_selecionado = st.selectbox(
        "Regime de produção (dia)", ["Todos", "Convencional", "Orgânico"]
    )
    periodo = st.date_input(
        "Período", value=(data_min, data_max), min_value=data_min, max_value=data_max
    )
    meta_ef = st.number_input(
        "Meta de Eficiência Global (referência de Qualidade)",
        min_value=0.50, max_value=1.00, value=META_EFICIENCIA_GLOBAL, step=0.01, format="%.2f",
    )
    p_max = st.number_input(
        "Descartar do Desempenho dias acima de (× a referência; 0 = não descartar)",
        min_value=0.0, max_value=10.0, value=P_MAX_PLAUSIVEL, step=0.1, format="%.1f",
    )
    max_desvio = st.number_input(
        "Máx. de dias convencionais isolados entre dias orgânicos tratados como desvio do orgânico",
        min_value=0, max_value=5, value=MAX_DIAS_DESVIO_ISOLADO, step=1,
    )
    zero_nao_informado = st.checkbox(
        "Tratar % de açúcar igual a 0 (com produção) como não informado", value=False
    )
    agrupamento = st.selectbox("Agrupar evolução por", ["Mês", "Semana", "Safra", "Dia"], index=2)

if len(periodo) == 2:
    data_inicial, data_final = periodo
else:
    data_inicial, data_final = data_min, data_max

# O regime e o TCH são calculados sobre a base completa (herança de regime/fibra entre dias),
# e só depois filtrados.
diario = calcular_oee_diario(base, meta_ef, zero_nao_informado, int(max_desvio), METODO_HORAS_MOAGEM, p_max)
diario["SAFRA"] = diario["Data"].apply(classificar_safra)
diario["MES"] = diario["Data"].dt.to_period("M").dt.to_timestamp()
diario["SEMANA"] = diario["Data"].dt.to_period("W-SUN").dt.start_time

df = diario[(diario["Data"] >= pd.Timestamp(data_inicial)) & (diario["Data"] <= pd.Timestamp(data_final))]
if safra_selecionada:
    df = df[df["SAFRA"].isin(safra_selecionada)]
if regime_selecionado != "Todos":
    alvo = {"Convencional": "convencional", "Orgânico": "organico"}[regime_selecionado]
    df = df[df["regime_dia"] == alvo]


# _______________ Geração de Informações ________________________

if df.empty:
    st.title("OEE - Overall Equipment Effectiveness")
    st.info("Sem dados para os filtros selecionados.")
    st.stop()

res = consolidar(df, meta_ef)

chave = {"Mês": "MES", "Semana": "SEMANA", "Safra": "SAFRA", "Dia": "Data"}[agrupamento]
evolucao = consolidar_por(df, chave, meta_ef)
if chave == "MES":
    evolucao["Período"] = evolucao[chave].dt.strftime("%m/%Y")
elif chave == "SEMANA":
    evolucao["Período"] = evolucao[chave].dt.strftime("%d/%m/%Y")
elif chave == "Data":
    evolucao["Período"] = evolucao[chave].dt.strftime("%d/%m/%Y")
else:
    evolucao["Período"] = evolucao[chave]

por_safra = consolidar_por(df, "SAFRA", meta_ef)
por_regime = consolidar_por(df, "regime_dia", meta_ef)

COR = {"Disponibilidade": "#636EFA", "Desempenho": "#EF553B", "Qualidade": "#00CC96", "OEE": "#AB63FA"}


# _________________ Criação da Página ___________________________
st.title("OEE - Overall Equipment Effectiveness")

for aviso in avisos_escala + validar_escalas(diario):
    st.warning(aviso)

l1c1, l1c2, l1c3, l1c4 = st.columns(4)
l2c1, l2c2, l2c3, l2c4 = st.columns(4)
l2bc1, l2bc2, l2bc3 = st.columns(3)
l3c1 = st.columns(1)[0]
l4c1 = st.columns(1)[0]
l4c2 = st.columns(1)[0]
l5c1 = st.columns(1)[0]
l6c1, l6c2 = st.columns(2)
l7c1 = st.columns(1)[0]


# __________________ Visualização das Informações ______________

with l1c1:
    st.metric("OEE", pct(res["OEE"]))
    with st.popover("Como é calculado?"):
        st.write("""
        OEE = Disponibilidade × Desempenho × Qualidade

        Cada pilar é calculado com os **totais do período** (nunca com a média dos percentuais diários).
        """)

with l1c2:
    st.metric("Disponibilidade (D)", pct(res["D"]))
    st.caption(f"{fmt(res['tempo_moagem_h'], 0)} h de moagem em {fmt(res['tempo_programado_h'], 0)} h programadas")
    with st.popover("Como é calculada?"):
        st.write("""
        D = Σ horas de moagem ÷ Σ horas programadas

        Horas de moagem do dia = Aproveitamento do tempo de moagem (2015 10884) × 24 h.
        Horas programadas = 24 h por dia presente na base.
        """)

with l1c3:
    st.metric("Desempenho (P)", pct(res["P"]))
    cap_txt = f"TCH real {fmt(res['tch_real'], 1)} t/h × referência {fmt(res['tch_ref'], 1)} t/h"
    if res["dias_p_descartados"] > 0:
        cap_txt += f" | {res['dias_p_descartados']} dia(s) descartado(s) como erro de dado"
    st.caption(cap_txt)
    with st.popover("Como é calculado?"):
        st.write("""
        P = Σ cana moída ÷ Σ (horas de moagem × TCH de referência do dia)

        Horas de moagem = Aproveitamento do tempo de moagem (2015 10884) × 24 h.
        Dias com tempo de moagem zero ficam fora do cálculo de P.
        """)
        st.write("""
        O TCH de referência é o máximo teórico por fibra (% cana, arredondada a 0,25 e limitada a 11–16) e por regime.
        Cada dia tem um único regime, definido por 2015 12723 (açúcar convencional, sc 50 kg):
        - 12723 = 0 -> dia orgânico.
        - 12723 igual ao açúcar total do dia -> dia convencional.
        - 12723 menor que o açúcar total, ou 1 a 2 dias isolados entre dias orgânicos -> dia orgânico;
          o valor de 12723 é açúcar orgânico desviado.
        Dias sem açúcar (só etanol) herdam o regime do dia anterior.

        P pode passar de 100% em dias de pico. Só são descartados dias acima do limite configurado nos filtros.
        """)

with l1c4:
    st.metric("Qualidade (Q)", pct(res["Q"]))
    st.caption(f"Q global {pct(res['q_global'])} × Conformidade {pct(res['q_conformidade'])}")
    with st.popover("Como é calculada?"):
        st.write(f"""
        Q = Q global × Q conformidade

        **Q global** = Eficiência global ponderada pela cana moída ÷ meta ({fmt(meta_ef * 100, 0)}%), limitada a 100%.

        **Q conformidade** = média de Q açúcar e Q etanol, ponderada pelos volumes (açúcar em t, etanol em m³).
        - Q açúcar = % de açúcar especificado (2015 13416 no convencional e 2015 18019 no orgânico), ponderado pela produção de cada regime.
        - Q etanol = 1 − etanol reclassificado ÷ etanol produzido.
        """)

with l2c1:
    st.metric("Cana moída", fmt(res["cana_t"], 0, " t"))
    st.caption(f"{res['dias']} dias na seleção")

with l2c2:
    st.metric("Q global", pct(res["q_global"]))
    st.caption(f"Eficiência global ponderada: {fmt(res['ef_global_pond_pct'], 1)}%")

with l2c3:
    st.metric("Q açúcar / Q etanol", f"{pct(res['q_acucar'])} / {pct(res['q_etanol'])}")
    st.caption(f"{fmt(res['acucar_t'], 0)} t de açúcar e {fmt(res['etanol_m3'], 0)} m³ de etanol")

with l2c4:
    st.metric("Dias com P acima de 100%", fmt(res["dias_p_maior_1"], 0))
    st.caption("Dias pontuais de pico; contam normalmente no período.")

with l2bc1:
    st.metric("Dias Convencional / Orgânico", f"{fmt(res['dias_conv'], 0)} / {fmt(res['dias_org'], 0)}")
    st.caption("Um regime por dia; dias só de etanol herdam o regime anterior.")

with l2bc2:
    pct_desvio = res["desvio_org_t"] / res["acucar_org_t"] if res["acucar_org_t"] > 0 else None
    st.metric("Açúcar Orgânico Desviado", fmt(res["desvio_org_t"], 0, " t"))
    st.caption(f"{pct(pct_desvio)} do açúcar dos dias orgânicos ({fmt(res['acucar_org_t'], 0)} t)")
    with st.popover("Como é identificado?"):
        st.write("""
        Em dia orgânico não se produz convencional. Quando 2015 12723 vem diferente de zero
        durante a campanha orgânica, esse valor é açúcar orgânico que sofreu desvio e não pôde
        ser classificado como orgânico. É informado para diagnóstico; a perda de qualidade
        entra em Q pelo % de açúcar especificado (2015 18019 / 13416).
        """)

with l2bc3:
    st.metric("Dias de Desvio Isolado", fmt(res["dias_desvio_isolado"], 0))
    st.caption("Dias 100% 'convencionais' entre dias orgânicos, tratados como orgânico desviado.")

with l3c1:
    ev = evolucao.copy()
    fig = go.Figure()
    fig.add_bar(
        x=ev["Período"], y=ev["OEE"] * 100, name="OEE", marker_color=COR["OEE"],
        text=[fmt(v * 100, 1) for v in ev["OEE"]] if len(ev) <= 31 else None,
        textposition="outside",
    )
    fig.update_layout(title=f"OEE (por {agrupamento.lower()})", yaxis_title="OEE (%)", xaxis_title=agrupamento)
    fig.update_xaxes(type="category")
    mostrar(fig)

with l4c1:
    ps = por_safra.copy()
    fig = go.Figure()
    for nome, col in [("Disponibilidade", "D"), ("Desempenho", "P"), ("Qualidade", "Q"), ("OEE", "OEE")]:
        fig.add_bar(
            x=ps["SAFRA"], y=ps[col] * 100, name=nome, marker_color=COR[nome],
            text=[fmt(v * 100, 1) for v in ps[col]], textposition="outside",
        )
    fig.update_layout(
        title="Pilares do OEE por Safra", barmode="group", yaxis_title="%", legend=dict(orientation="h")
    )
    mostrar(fig)

with l4c2:
    tch = evolucao[["Período", "tch_real", "tch_ref"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tch["Período"], y=tch["tch_ref"], name="TCH de referência (máx. teórico)",
                             mode="lines+markers", line=dict(dash="dash", color="gray")))
    fig.add_trace(go.Scatter(x=tch["Período"], y=tch["tch_real"], name="TCH real",
                             mode="lines+markers", line=dict(color=COR["Desempenho"])))
    fig.update_layout(title=f"TCH Real × Referência (por {agrupamento.lower()})",
                      yaxis_title="t/h", legend=dict(orientation="h"))
    fig.update_xaxes(type="category")
    mostrar(fig)

with l5c1:
    fig = go.Figure()
    for nome, col, cor in [("Q global", "q_global", "#00CC96"), ("Q açúcar", "q_acucar", "#FFA15A"),
                           ("Q etanol", "q_etanol", "#19D3F3"), ("Q conformidade", "q_conformidade", "#AB63FA")]:
        fig.add_bar(
            x=evolucao["Período"], y=evolucao[col] * 100, name=nome, marker_color=cor,
            text=[fmt(v * 100, 1) for v in evolucao[col]] if len(evolucao) <= 14 else None,
            textposition="outside",
        )
    fig.update_layout(title=f"Componentes da Qualidade (por {agrupamento.lower()})", barmode="group",
                      yaxis_title="%", legend=dict(orientation="h"))
    fig.update_xaxes(type="category")
    mostrar(fig)

with l6c1:
    if por_regime.empty:
        st.info("Sem dados de regime na seleção.")
    else:
        pr = por_regime.copy()
        pr["Regime"] = pr["regime_dia"].map({"convencional": "Convencional", "organico": "Orgânico"})
        fig = go.Figure()
        for nome, col in [("Disponibilidade", "D"), ("Desempenho", "P"), ("Qualidade", "Q"), ("OEE", "OEE")]:
            fig.add_bar(x=pr["Regime"], y=pr[col] * 100, name=nome, marker_color=COR[nome],
                        text=[fmt(v * 100, 1) for v in pr[col]], textposition="outside")
        fig.update_layout(title="OEE por Regime", barmode="group",
                          yaxis_title="%", legend=dict(orientation="h"))
        mostrar(fig)

with l6c2:
    validos = df[df["OEE"].notna() & (df["tempo_moagem_h"] >= 12)]
    fig = px.histogram(validos, x=validos["OEE"] * 100, nbins=40,
                       title="Distribuição do OEE Diário (dias com 12 h ou mais de moagem)",
                       labels={"x": "OEE (%)"})
    fig.update_layout(xaxis_title="OEE (%)", yaxis_title="Quantidade de dias")
    mostrar(fig)

with l7c1:
    with st.expander("Mais Detalhes - Dados Brutos"):
        st.subheader("Cálculo Diário do OEE")
        colunas_dia = [
            "Data", "regime_dia", "desvio_org_kg", "fibra_usada", "tch_ref", "tempo_moagem_h", "cana_t",
            "D", "P", "q_global", "q_acucar", "q_etanol", "q_conformidade", "Q", "OEE",
        ]
        st.dataframe(df[colunas_dia], height=400, hide_index=True)

        st.subheader("Auditar o Cálculo de um Dia")
        dia_auditado = st.date_input(
            "Dia", value=df["Data"].max().date(), min_value=data_min, max_value=data_max, key="dia_auditoria"
        )
        linha = diario[diario["Data"] == pd.Timestamp(dia_auditado)]
        if linha.empty:
            st.info("Dia sem registro na base.")
        else:
            x = linha.iloc[0]
            passos = [
                ("Cana moída (t)", fmt(x["cana_t"], 2)),
                ("Aproveitamento do tempo de moagem 10884 (%)", fmt(x["aproveit_moagem_pct"], 2)),
                ("Disponibilidade D do dia", fmt(x["D"], 4)),
                ("Horas de moagem = D × 24 (h)", fmt(x["tempo_moagem_h"], 3)),
                ("Regime do dia", str(x["regime_dia"])),
                ("Fibra informada 211 (%)", fmt(x["fibra_pct"], 4)),
                ("Fibra usada / arredondada a 0,25 e limitada a 11-16 (%)", f"{fmt(x['fibra_usada'], 4)} / {fmt(x['fibra_grade'], 2)}"),
                ("TCH de referência (t/h)", fmt(x["tch_ref"], 1)),
                ("Horas usadas no desempenho (h)", fmt(x["horas_p_h"], 3)),
                ("Capacidade teórica = horas × TCH ref (t)", fmt(x["horas_p_h"] * x["tch_ref"], 1)),
                ("P do dia = cana ÷ capacidade", fmt(x["P_bruto"], 4)),
                ("Descartado como erro de dado?", "Sim" if x["p_descartado"] else "Não"),
            ]
            st.table(pd.DataFrame(passos, columns=["Passo", "Valor"]).set_index("Passo"))

        st.subheader("Maiores Desempenhos Diários (para conferir dados)")
        st.dataframe(
            df.sort_values("P_bruto", ascending=False)[
                ["Data", "regime_dia", "cana_t", "tch_efetivo", "aproveit_moagem_pct", "tch_ref", "P_bruto", "p_descartado"]
            ].head(20),
            hide_index=True,
        )

        st.subheader("Consolidação por Safra")
        st.dataframe(por_safra, height=300, hide_index=True)

        st.subheader("Base de Desempenho (planilha)")
        st.dataframe(base, height=400, hide_index=True)
