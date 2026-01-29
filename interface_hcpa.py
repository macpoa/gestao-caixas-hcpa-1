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
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC8T5XwhDaUp8oB\nRx6LHsJjn/5HbwLXYNEx4LLLpYVn8rn1Dak5r5NtYRZJAsspCzy2jmWpn6RO3Dij\nwAlThFroCJBpJksM4rTIFqAAwXPYbV4m5nwhSlP6KB1/TUzLVPVXE7s17FH1+xzB\nftBus0bkBSQl41rClZYJ9hPFh14yCFhKANqSJlI1hq53hsOVfECVrobvR29BLuU2\nakY0S0PCkCjdgUZIbqzkofMCLdw+RJNFAYdveBArZNahc34Zx/zZj04+LJaqoy5B\nKQ5E11Lc7rNHhxXtFplL34nCBl21VlFwLVDrgkIfsBkpc8Vjl2/2uCuw0Gh7O13v\nwXs9TakVAgMBAAECggEAG4xbB44X/ARV4Xz5g2mzD2cDCIk9dau0vuK71V34F75j\nJO3kMUu1uh0naPPvK6h4r85CIh/4Jg9Ce/YmhyDIOcSy96cB+Lcbsl/Y9XNXkrRh\nPzidtTMN+P0wX4S79M0PfTcmPpu9W8pqKQZ30JIKj2YPJTnO98NxaTCmMNH+Xjwo\n9rCgSQdYU1xjWNx+MjrItdiKoB3b9b5aEL1EvA5YkpSzDt7pnI+9egRFYDUgLeDd\nLsmBVVljZiu/GS2v4nvuJkoeSn0IZ4flcfnibfkywgWgKHSrp6lQQx/In0lzX1kS\n1rpIgVwF8w5WxishE17NsMdHNynOvmPBnLy6C9oY4QKBgQDnNBTiO0SMBIvh0DT1\nLwDq0uafGiOk36FfrX1OZKRM/vghRQjK7zVAtn1CRwYLMfhnd2lKE3wJKJZWH1w5\nC5nXcevdw0Lh+P8LRX43Z/KOU8lVMO9tQ65Smex5SgyR5FdEiZDoGMrB67eMIVDB\n3DTCkUEDpDsPednnxnhux7xLEQKBgQDQgdi4EJ0WsM6dyTHQ/22ZRZ/hg3J6RiYZ\nRX7g8jA4HiT/BcYToKQpGXFu4ss0qFpZEkQIkxBJgmHYvrxPQ51hdr6KB9IytapA\nfddkprnyH18QhLa1q3o/jdx7UAPfJ1LOzHC4PiLK0WvrQs1qcxUN/JHYPXkdB1k1\n9TVgIEeVxQKBgC0sguwVEnadKMutR7ukPHSlUoRBsjczrq8oEbSwe13D761odKha\nBrinL2A0ylyDnfpxXXQozHJpqL4ZEIbg2mU7EA/baAUJBqQoJtoiiEUA3/SyRAXA\nVJ41Dvw/2Kbky5xLmLGQroUnTkyl8cZ/BRwDD4Xrn9KNR2M+5ycWBZdRAoGAXarH\nMcD84NGisA1PHMVyddVqQoOrbLSQru+iVOlXsg4QrqPoXK7gsDnm1Fp70PcER1lG\nSNfQDEXPMPBWZgFI9RzD8fwbeH5Vsk0V8vhXNibTrPcBoVEcROq0roy+gIQI1i/P\nP2Viedxkb7Z90yFJxxO8bPkIrHq9n9i9FqbJocUCgYEA1wA2KVzgO1TZhZdkCYwA\nMYbDnJrMPFdmlm8wxhheaFFwvlXVVuTlzXg8sPf/aREtNW4dloJ5i8sZ9VW4K4EN\n7MTFNkDm7XveEqwwT6QcTuEt9zyjAghaz72A+r15dXE3CLDjz2TbHMjq3AVoMEOZ\nD+z4gcWZgMmHIFA46mHpsvM=\n-----END PRIVATE KEY-----\n",
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