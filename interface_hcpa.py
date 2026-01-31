import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# ======================================================
# CONFIGURAÇÃO
# ======================================================
st.set_page_config(page_title="Logística de Caixas HCPA", layout="wide")

NOME_PLANILHA = "Gestao_Caixas_HCPA"
ABA_ALERTAS = "db_alertas"
ABA_LAVAGEM = "db_lavagem"

STATUS_ATIVOS = ["Aberto", "Em Coleta", "Coletado"]

MAPA_URGENCIA = {
    "🔴 Está atrapalhando": 3,
    "🟡 Ideal coletar hoje": 2,
    "🟢 Pode esperar": 1
}

COL_ALERTAS = [
    "ID_Alerta", "Data_Hora", "ID_Setor", "Urgencia",
    "Qtd_Pretas", "Qtd_Azuis", "Skates", "Carrinhos",
    "Status", "Responsavel"
]

COL_LAVAGEM = [
    "ID_Lote", "Chegada_Lavagem", "Qtd_Pretas", "Qtd_Azuis",
    "Qtd_Pretas_Lavadas", "Qtd_Azuis_Lavadas", "Diferenca",
    "Status", "Previsao_Termin", "Fim_Lavagem"
]

# ======================================================
# CONEXÃO GOOGLE SHEETS
# ======================================================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)
planilha = client.open(NOME_PLANILHA)

aba_alertas = planilha.worksheet(ABA_ALERTAS)
aba_lavagem = planilha.worksheet(ABA_LAVAGEM)

# ======================================================
# FUNÇÕES
# ======================================================
def novo_id(prefixo):
    return f"{prefixo}{datetime.now().strftime('%Y%m%d%H%M%S')}"

def carregar_alertas():
    dados = aba_alertas.get_all_records()
    df = pd.DataFrame(dados)

    for c in COL_ALERTAS:
        if c not in df.columns:
            df[c] = None

    df["Data_Hora"] = pd.to_datetime(df["Data_Hora"], errors="coerce")
    df["Urgencia"] = df["Urgencia"].fillna("🟢 Pode esperar")
    df["Status"] = df["Status"].fillna("Aberto")
    df["Responsavel"] = df["Responsavel"].fillna("")

    return df

def carregar_lavagem():
    dados = aba_lavagem.get_all_records()
    df = pd.DataFrame(dados)

    for c in COL_LAVAGEM:
        if c not in df.columns:
            df[c] = None

    df["Chegada_Lavagem"] = pd.to_datetime(df["Chegada_Lavagem"], errors="coerce")
    df["Fim_Lavagem"] = pd.to_datetime(df["Fim_Lavagem"], errors="coerce")

    return df

def atualizar_alerta(id_alerta, status, responsavel):
    cell = aba_alertas.find(id_alerta)
    r = cell.row
    aba_alertas.update_cell(r, 9, status)
    aba_alertas.update_cell(r, 10, responsavel)

# ======================================================
# INTERFACE
# ======================================================
st.title("📦 Logística de Caixas – HCPA")
tabs = st.tabs(["🔔 Setor", "🚚 Expedição", "🧼 Lavagem", "📊 Gestão", "📋 Inventário"])
setor_url = st.query_params.get("setor", "Geral")

# ======================================================
# ABA 1 — SETOR
# ======================================================
with tabs[0]:
    st.header(f"🔔 Notificar Coleta — {setor_url}")

    with st.form("setor"):
        urgencia = st.radio("Impacto no trabalho", list(MAPA_URGENCIA.keys()))

        c1, c2 = st.columns(2)
        with c1:
            pretas = st.radio("Caixas Pretas", ["0", "≤5", "≤10", "mais que 10"])
            skates = st.number_input("Skates disponíveis", min_value=0)
        with c2:
            azuis = st.radio("Caixas Azuis", ["0", "≤30", "mais que 30"])
            carrinhos = st.number_input("Carrinhos disponíveis", min_value=0)

        enviar = st.form_submit_button("🚀 Enviar alerta")

    if enviar:
        aba_alertas.append_row([
            novo_id("ALT"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            setor_url,
            urgencia,
            pretas,
            azuis,
            skates,
            carrinhos,
            "Aberto",
            ""
        ])
        st.success("✅ Alerta enviado")

# ======================================================
# ABA 2 — EXPEDIÇÃO
# ======================================================
with tabs[1]:
    st.subheader("🚚 Ordem sugerida de coleta por setor")

    df = carregar_alertas()
    ativos = df[df["Status"].isin(STATUS_ATIVOS)].copy()

    if ativos.empty:
        st.info("Nenhum alerta ativo")
    else:
        ativos["Tempo"] = (datetime.now() - ativos["Data_Hora"]).dt.total_seconds() / 60
        ativos["Peso"] = ativos["Urgencia"].map(MAPA_URGENCIA)

        resumo = (
            ativos.groupby("ID_Setor")
            .agg(Qtde=("ID_Alerta", "count"),
                 Tempo_Max=("Tempo", "max"),
                 Peso_Max=("Peso", "max"))
            .reset_index()
            .sort_values(by=["Peso_Max", "Tempo_Max"], ascending=False)
        )

        for _, s in resumo.iterrows():
            setor = s["ID_Setor"]
            df_setor = ativos[ativos["ID_Setor"] == setor]

            with st.expander(f"📍 {setor} | {int(s['Tempo_Max'])} min | {s['Qtde']} avisos"):
                st.table(df_setor[["Urgencia", "Qtd_Pretas", "Qtd_Azuis", "Data_Hora"]])

                with st.form(f"coleta_{setor}"):
                    resp = st.text_input("Cartão ponto (até 10 dígitos)", max_chars=10)
                    confirmar = st.form_submit_button("✔️ Confirmar coleta")

                if confirmar:
                    if not resp.isdigit():
                        st.error("Cartão ponto inválido")
                    else:
                        for aid in df_setor["ID_Alerta"]:
                            atualizar_alerta(aid, "Coletado", resp)
                        st.success("✅ Coleta registrada")
                        st.rerun()

# ======================================================
# ABA 3 — LAVAGEM
# ======================================================
with tabs[2]:
    st.subheader("🧼 Lavagem")

    with st.form("entrada_lavagem"):
        p = st.number_input("Pretas que chegaram", min_value=0)
        a = st.number_input("Azuis que chegaram", min_value=0)
        enviar = st.form_submit_button("Registrar chegada")

    if enviar:
        aba_lavagem.append_row([
            novo_id("LOT"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            p, a, "", "", "", "Em Lavagem", "", ""
        ])
        st.success("✅ Lote criado")
        st.rerun()

    df_lav = carregar_lavagem()
    ativos = df_lav[df_lav["Status"] == "Em Lavagem"]

    for _, row in ativos.iterrows():
        with st.expander(f"🧺 {row['ID_Lote']}"):
            with st.form(f"fecha_{row['ID_Lote']}"):
                pl = st.number_input("Pretas lavadas", min_value=0)
                al = st.number_input("Azuis lavadas", min_value=0)
                fechar = st.form_submit_button("✔️ Fechar lote")

            if fechar:
                ent = (row["Qtd_Pretas"] or 0) + (row["Qtd_Azuis"] or 0)
                lav = pl + al
                diff = lav - ent

                cell = aba_lavagem.find(row["ID_Lote"])
                r = cell.row

                aba_lavagem.update(f"E{r}:J{r}", [[
                    pl, al, diff, "Finalizado", "",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]])

                st.success("✅ Lote finalizado")
                st.rerun()

# ======================================================
# ABA 4 — GESTÃO
# ======================================================
with tabs[3]:
    st.subheader("📊 Indicadores")

    df_lav = carregar_lavagem()
    fin = df_lav[df_lav["Status"] == "Finalizado"]

    backlog = (
        df_lav["Qtd_Pretas"].fillna(0).sum() +
        df_lav["Qtd_Azuis"].fillna(0).sum()
    ) - (
        df_lav["Qtd_Pretas_Lavadas"].fillna(0).sum() +
        df_lav["Qtd_Azuis_Lavadas"].fillna(0).sum()
    )

    c1, c2 = st.columns(2)
    c1.metric("Backlog real", backlog)
    c2.metric("Lotes finalizados", len(fin))

# ======================================================
# ABA 5 — INVENTÁRIO
# ======================================================
with tabs[4]:
    st.subheader("📋 Inventário por exclusão")

    TOTAL = 1000
    prontas = st.number_input("Prontas", 0)
    separacao = st.number_input("Em separação", 0)
    entrega = st.number_input("Aguardando entrega", 0)
    lavagem = st.number_input("Na lavagem", 0)

    internas = prontas + separacao + entrega + lavagem
    campo = TOTAL - internas
    st.metric("Em circulação", campo)
