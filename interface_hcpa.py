import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime

# =============================
# CONFIGURAÇÃO GERAL
# =============================
st.set_page_config(page_title="Logística de Caixas HCPA", layout="wide")

NOME_PLANILHA = "Gestao_Caixas_HCPA"
ABA_ALERTAS = "db_alertas"

COLUNAS_ALERTAS = [
    "ID_Alerta",
    "Data_Hora",
    "ID_Setor",
    "Qtd_Pretas",
    "Qtd_Azuis",
    "Skates",
    "Carrinhos",
    "Status"
]

STATUS_ATIVOS = ["Aberto", "Em Coleta", "Coletado"]

# =============================
# CONEXÃO GOOGLE SHEETS
# =============================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

try:
    planilha = client.open(NOME_PLANILHA)
    aba_alertas = planilha.worksheet(ABA_ALERTAS)
except Exception as e:
    st.error(f"Erro ao abrir planilha: {e}")
    st.stop()

# =============================
# FUNÇÕES UTILITÁRIAS
# =============================
def carregar_alertas():
    dados = aba_alertas.get_all_records()
    return pd.DataFrame(dados) if dados else pd.DataFrame(columns=COLUNAS_ALERTAS)

def gerar_id_alerta():
    return f"ALT{datetime.now().strftime('%Y%m%d%H%M%S')}"

def atualizar_status(id_alerta, novo_status):
    try:
        cell = aba_alertas.find(id_alerta)
        aba_alertas.update_cell(cell.row, COLUNAS_ALERTAS.index("Status") + 1, novo_status)
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar status: {e}")
        return False

def criar_alerta(setor, pretas, azuis, skates, carrinhos):
    nova_linha = [
        gerar_id_alerta(),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        setor,
        pretas,
        azuis,
        skates,
        carrinhos,
        "Aberto"
    ]
    aba_alertas.append_row(nova_linha, value_input_option="USER_ENTERED")

# =============================
# INTERFACE
# =============================
st.title("📦 Logística de Caixas – HCPA | MVP")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🔔 Setor", "🚚 Expedição", "🧼 Lavagem", "🧠 Gestão", "📋 Inventário"]
)

query_params = st.query_params
setor_url = query_params.get("setor", "Geral")

# =============================
# ABA 1 — SETOR (QR CODE)
# =============================
with tab1:
    st.header(f"🔔 Notificar Coleta — Setor: {setor_url}")

    with st.form("form_setor"):
        col1, col2 = st.columns(2)

        with col1:
            qtd_pretas = st.radio("Caixas Pretas", ["0", "≤5", "≤10", ">10"])
            skates = st.number_input("Skates disponíveis", min_value=0, step=1)

        with col2:
            qtd_azuis = st.radio("Caixas Azuis", ["0", "≤30", ">30"])
            carrinhos = st.number_input("Carrinhos disponíveis", min_value=0, step=1)

        enviar = st.form_submit_button("🚀 Enviar Alerta")

    if enviar:
        criar_alerta(setor_url, qtd_pretas, qtd_azuis, skates, carrinhos)
        st.success("✅ Alerta registrado com sucesso!")

# =============================
# ABA 2 — EXPEDIÇÃO
# =============================
with tab2:
    st.subheader("🚚 Gestão de Coletas")

    df = carregar_alertas()
    df_op = df[df["Status"].isin(STATUS_ATIVOS)]

    if df_op.empty:
        st.info("Nenhum alerta ativo.")
    else:
        for _, row in df_op.iterrows():
            with st.expander(f"📍 {row['ID_Setor']} | {row['ID_Alerta']} ({row['Status']})"):
                st.write(f"**Pretas:** {row['Qtd_Pretas']} | **Azuis:** {row['Qtd_Azuis']}")

                col1, col2 = st.columns(2)

                if row["Status"] == "Aberto":
                    if col1.button("🟡 Assumir", key=row["ID_Alerta"]):
                        atualizar_status(row["ID_Alerta"], "Em Coleta")
                        st.rerun()

                if row["Status"] == "Em Coleta":
                    if col2.button("✅ Coletado", key=f"col_{row['ID_Alerta']}"):
                        atualizar_status(row["ID_Alerta"], "Coletado")
                        st.rerun()

# =============================
# ABA 3 — LAVAGEM
# =============================
with tab3:
    st.subheader("🧼 Higienização")

    df = carregar_alertas()
    coletados = df[df["Status"] == "Coletado"]

    st.metric("Caixas aguardando lavagem", len(coletados))

    with st.form("lavagem"):
        qtd = st.number_input("Quantidade no lote", min_value=1)
        finalizar = st.form_submit_button("Finalizar Higienização")

    if finalizar and not coletados.empty:
        for id_alerta in coletados.head(qtd)["ID_Alerta"]:
            atualizar_status(id_alerta, "Higienizado")
        st.success("✅ Lote higienizado!")
        st.rerun()

# =============================
# ABA 4 — GESTÃO
# =============================
with tab4:
    st.subheader("📊 Painel de Gestão")

    df = carregar_alertas()
    df["Data_Hora"] = pd.to_datetime(df["Data_Hora"])

    st.write("**📍 Setores com mais alertas**")
    st.bar_chart(df["ID_Setor"].value_counts())

    st.write("**📦 Distribuição por Status**")
    st.table(df["Status"].value_counts())

# =============================
# ABA 5 — INVENTÁRIO
# =============================
with tab5:
    st.subheader("📋 Inventário Global")

    TOTAL_CAIXAS = 500
    st.info(f"Total cadastrado: {TOTAL_CAIXAS}")

    col1, col2 = st.columns(2)
    with col1:
        prontas = st.number_input("Prontas", min_value=0, value=120)
        separacao = st.number_input("Em separação", min_value=0, value=60)
    with col2:
        entrega = st.number_input("Aguardando entrega", min_value=0, value=40)
        lavagem = st.number_input("Na lavagem", min_value=0, value=50)

    internas = prontas + separacao + entrega + lavagem
    campo = TOTAL_CAIXAS - internas
    perc = (campo / TOTAL_CAIXAS) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Sob controle", internas)
    c2.metric("Em circulação", campo, f"{perc:.1f}%")
    c3.metric("Status", "Crítico" if perc > 30 else "Saudável")

    if perc > 30:
        st.error("⚠️ Risco de desabastecimento detectado.")














