import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema HCPA - Gestão de Caixas", page_icon="📦")

# --- CONEXÃO COM A PLANILHA (Sua chave já configurada) ---
@st.cache_resource
def conectar():
    INFO_DA_CHAVE = st.secrets["gcp_service_account"]
    escopo = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(INFO_DA_CHAVE, escopo)
    return gspread.authorize(creds).open("Gestao_Caixas_HCPA").worksheet("Pendentes")

aba = conectar()

# --- INTERFACE ---
st.title("📦 Gestão de Caixas - HCPA")
st.markdown("---")

aba_notificar, aba_painel = st.tabs(["📢 Notificar Unidade", "🚚 Painel Expedição"])

with aba_notificar:
    st.header("Novo Alerta de Caixas")
    setor = st.selectbox("Selecione o Setor", ["Genética", "Almoxarifado", "Oncologia", "Bloco Cirúrgico", "Outro"])
    volume = st.radio("Volume Estimado", ["1 (Até 5)", "2 (Até 10)", "3 (> 10)"], horizontal=True)
    
    if st.button("Enviar Notificação"):
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        id_fluxo = str(int(datetime.datetime.now().timestamp()))
        aba.append_row([id_fluxo, agora, setor.upper(), volume[0], "PENDENTE"])
        st.success(f"Notificação enviada com sucesso para {setor}!")

with aba_painel:
    st.header("Pendências em Tempo Real")
    if st.button("🔄 Atualizar Dados"):
        st.rerun()
    
    dados = aba.get_all_records()
    pendentes = [d for d in dados if d['Status'] == 'PENDENTE']
    
    if pendentes:
        st.table(pendentes)
    else:

        st.write("✅ Nenhuma pendência no momento.")

