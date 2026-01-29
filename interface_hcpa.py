import base64
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime  # Esta linha é essencial para registrar o horário!

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Caixas - HCPA", page_icon="📦")

@st.cache_resource
def conectar():
    # Puxa o dicionário dos Secrets
    info = dict(st.secrets["gcp_service_account"])
    
    # --- LIMPEZA TOTAL DA CHAVE ---
    # Remove aspas duplas, aspas simples, espaços e quebras de linha
    chave_crua = info["private_key"]
    chave_limpa = chave_crua.replace('"', '').replace("'", "").replace("\n", "").replace(" ", "").strip()
    
    try:
        # Decodifica a Base64
        chave_recuperada = base64.b64decode(chave_limpa).decode()
        # Prepara para o Google entender as quebras de linha reais
        info["private_key"] = chave_recuperada.replace("\\n", "\n")
    except Exception as e:
        st.error(f"Erro na decodificação da chave: {e}")
        st.stop()
    
    escopo = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info, escopo)
    return gspread.authorize(creds).open("Gestao_Caixas_HCPA").worksheet("Pendentes")

# Inicializa a conexão
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




