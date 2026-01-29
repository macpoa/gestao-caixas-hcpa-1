import base64
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

@st.cache_resource
def conectar():
    info = dict(st.secrets["gcp_service_account"])
    # Remove aspas e limpa a string antes de decodificar
    chave_b64 = info["private_key"].replace('"', '').strip()
    
    # Decodifica e reconstrói os pulos de linha
    chave_final = base64.b64decode(chave_b64).decode().replace("\\n", "\n")
    info["private_key"] = chave_final
    
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
        try:
            # Captura o momento exato
            agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            id_fluxo = str(int(datetime.datetime.now().timestamp()))
            
            # Envia para a planilha
            aba.append_row([id_fluxo, agora, setor.upper(), volume[0], "PENDENTE"])
            st.success(f"✅ Notificação enviada com sucesso para {setor}!")
        except Exception as e:
            st.error(f"Erro ao enviar: {e}")

with aba_painel:
    st.header("Pendências em Tempo Real")
    if st.button("🔄 Atualizar Dados"):
        st.rerun()
    
    try:
        dados = aba.get_all_records()
        pendentes = [d for d in dados if d.get('Status') == 'PENDENTE']
        
        if pendentes:
            st.table(pendentes)
        else:
            st.info("✅ Nenhuma pendência no momento.")
    except Exception as e:
        st.error(f"Erro ao ler dados: {e}")





