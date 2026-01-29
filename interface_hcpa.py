import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# Configuração da página
st.set_page_config(page_title="Gestão de Caixas - HCPA", page_icon="📦")

@st.cache_resource
def conectar():
    # Puxa o dicionário diretamente dos Secrets
    info = dict(st.secrets["gcp_service_account"])
    
    # Limpeza: Garante que a chave privada trate corretamente as quebras de linha
    # e remove possíveis aspas duplas acidentais nas extremidades
    pk = info["private_key"].replace("\\n", "\n").strip()
    if pk.startswith('"') and pk.endswith('"'):
        pk = pk[1:-1]
    info["private_key"] = pk
    
    escopo = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info, escopo)
    return gspread.authorize(creds).open("Gestao_Caixas_HCPA").worksheet("Pendentes")

# Inicialização segura
try:
    aba = conectar()
except Exception as e:
    st.error(f"Erro ao conectar com a base de dados: {e}")
    st.stop()

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
            agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            id_fluxo = str(int(datetime.datetime.now().timestamp()))
            aba.append_row([id_fluxo, agora, setor.upper(), volume[0], "PENDENTE"])
            st.success(f"Notificação enviada para {setor}!")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

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
        st.error(f"Erro ao ler tabela: {e}")



