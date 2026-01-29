import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema HCPA - Gestão de Caixas", page_icon="📦")

# --- CONEXÃO COM A PLANILHA (Sua chave já configurada) ---
@st.cache_resource
def conectar():
    INFO_DA_CHAVE = {
  "type": "service_account",
  "project_id": "gestao-caixas-hcpa",
  "private_key_id": "40294d927c1c149d9c8c9ac84d013715e4d28bb8",
  "private_key": "-----BEGIN PRIVATE KEY-----\n" + "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC8T5XwhDaUp8oB\n" + # ... continue colando as linhas aqui
"-----END PRIVATE KEY-----\n".replace('\\n', '\n'),
  "client_email": "gestao-caixas@gestao-caixas-hcpa.iam.gserviceaccount.com",
  "client_id": "102583460122623263507",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/gestao-caixas%40gestao-caixas-hcpa.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
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
