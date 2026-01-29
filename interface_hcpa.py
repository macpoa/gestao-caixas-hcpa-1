import base64
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

@st.cache_resource
def conectar():
    # Puxa o dicionário dos Secrets
    info = dict(st.secrets["gcp_service_account"])
    
    # Decodifica a Base64 de volta para a chave original perfeitamente
    # O .replace serve para limpar possíveis aspas extras
    chave_limpa = info["private_key"].replace('"', '')
    chave_recuperada = base64.b64decode(chave_limpa).decode()
    
    # Prepara a chave para o Google entender os pulos de linha
    info["private_key"] = chave_recuperada.replace("\\n", "\n")
    
    escopo = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info, escopo)
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



