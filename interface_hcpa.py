import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# 1. Configuração da Página
st.set_page_config(page_title="Gestão de Caixas HCPA", page_icon="📦")

# 2. Função de Conexão
@st.cache_resource
def conectar():
    info = dict(st.secrets["gcp_service_account"])
    # Ajuste fino da chave para evitar o erro de assinatura
    info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
    
    escopo = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info, escopo)
    return gspread.authorize(creds).open("Gestao_Caixas_HCPA").worksheet("Pendentes")

# 3. Inicialização
try:
    aba = conectar()
except Exception as e:
    st.error(f"Aguardando configuração de credenciais... {e}")
    st.stop()

# 4. Interface
st.title("📦 Gestão de Caixas - HCPA")
tab1, tab2 = st.tabs(["📢 Notificar Unidade", "🚚 Painel Expedição"])

with tab1:
    st.header("Novo Alerta")
    setor = st.selectbox("Setor/Unidade", ["Genética", "Almoxarifado", "Oncologia", "Bloco Cirúrgico", "Outro"])
    volume = st.radio("Volume Estimado", ["1", "2", "3"], horizontal=True)
    
    if st.button("Enviar Notificação"):
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        id_fluxo = str(int(datetime.datetime.now().timestamp()))
        
        # Inserindo os dados respeitando a ordem das suas colunas:
        # ID_Fluxo, Data_Hora_Notificacao, Setor_Unidade, Volume_Estimado, Status, Responsavel_Coleta, Data_Hora_Coleta, Observacoes
        aba.append_row([id_fluxo, agora, setor.upper(), volume, "PENDENTE", "", "", ""])
        st.success("Notificação registrada com sucesso!")

with tab2:
    st.header("Pendências em Tempo Real")
    if st.button("🔄 Atualizar Painel"):
        st.rerun()
    
    dados = aba.get_all_records()
    # Filtra apenas o que está PENDENTE na coluna 'Status'
    pendentes = [d for d in dados if d.get('Status') == 'PENDENTE']
    
    if pendentes:
        st.table(pendentes)
    else:
        st.info("Tudo em dia! ✅")



