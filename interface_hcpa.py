import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime

# -----------------------------
# CONFIGURAÇÃO GOOGLE SHEETS
# -----------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

NOME_PLANILHA = "Gestao_Caixas_HCPA"

try:
    planilha = client.open(NOME_PLANILHA)
    aba_alertas = planilha.worksheet("db_alertas")
except Exception as e:
    st.error(f"Erro ao abrir planilha ou aba db_alertas: {e}")
    st.stop()

# -----------------------------
# LEITURA BASE ATUAL
# -----------------------------
dados_alertas = aba_alertas.get_all_records()
df_alertas = pd.DataFrame(dados_alertas)

# -----------------------------
# INTERFACE
# -----------------------------
st.set_page_config(page_title="Logística de Caixas HCPA", layout="wide")
st.title("📦 Logística de Caixas – HCPA | MVP")

tab1, tab2 = st.tabs(["🔔 Notificar Coleta", "🚚 Painel da Expedição"])

# Captura de Setor via QR (URL)
query_params = st.query_params
setor_url = query_params.get("setor", "Geral")

# =============================
# ABA 1 — SETOR (QR CODE)
# =============================
with tab1:
    with st.form("form_notificacao"):
        st.header(f"🔔 Notificar Coleta — Setor: {setor_url}")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Caixas Pretas")
            qtd_pretas = st.radio(
                "Quantidade estimada",
                ["0", "≤5", "≤10", ">10"]
            )
            skates = st.number_input(
                "Skates disponíveis",
                min_value=0,
                step=1
            )

        with col2:
            st.subheader("Caixas Azuis")
            qtd_azuis = st.radio(
                "Quantidade estimada",
                ["0", "≤30", ">30"]
            )
            carrinhos = st.number_input(
                "Carrinhos disponíveis",
                min_value=0,
                step=1
            )

        obs = st.text_area("Observações operacionais")

        submitted = st.form_submit_button("🚀 Enviar Alerta")

   if submitted:
      agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      novo_id = f"ALT{len(df_alertas) + 1:05d}"

      nova_linha = [
           novo_id,
           agora,
           setor_url,
           qtd_pretas,
           qtd_azuis,
           skates,
           carrinhos,
           "Aberto"
    ]

    aba_alertas.append_row(
        nova_linha,
        value_input_option="USER_ENTERED"
    )

    st.success(f"✅ Alerta {novo_id} registrado com sucesso!")


# =============================
# ABA 2 — EXPEDIÇÃO
# =============================
with tab2:
    st.subheader("🚚 Alertas em Aberto")

    if not df_alertas.empty:
        df_abertos = df_alertas[df_alertas["Status"] == "Aberto"]

        st.metric(
            "Alertas em Aberto",
            len(df_abertos)
        )

        st.dataframe(
            df_abertos.sort_values("Data_Hora_Notificacao", ascending=False),
            use_container_width=True
        )
    else:
        st.info("Nenhum alerta registrado ainda.")













