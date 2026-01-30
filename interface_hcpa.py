import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

st.set_page_config(page_title="Gestão de Caixas HCPA", page_icon="📦")

@st.cache_resource
def conectar():
    # Puxa as credenciais dos Secrets do Streamlit
    info = dict(st.secrets["gcp_service_account"])
    # Limpa a chave privada para garantir que o Google aceite a assinatura
    info["private_key"] = info["private_key"].replace("\\n", "\n").strip()
    
    escopo = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info, escopo)
    return gspread.authorize(creds).open("Gestao_Caixas_HCPA").worksheet("Pendentes")

try:
    aba = conectar()
except Exception as e:
    st.error(f"Erro de conexão. Verifique os Secrets no Streamlit. Erro: {e}")
    st.stop()

st.title("📦 Gestão de Caixas - HCPA")
tab1, tab2 = st.tabs(["📢 Notificar Unidade", "🚚 Painel Expedição"])

with tab1:
    st.header("Novo Alerta")
    # 1. Captura o que vem na URL (ex: ?setor=GENETICA)
params = st.query_params

# 2. Define qual setor deve vir marcado por padrão
setor_na_url = params.get("setor", "OUTRO").upper()

# 3. Lista de setores (mantenha exatamente igual à planilha)
lista_setores = ["GENÉTICA", "ALMOXARIFADO", "ONCOLOGIA", "BLOCO CIRÚRGICO", "EMERGÊNCIA", "OUTRO"]

# 4. Descobre a posição do setor da URL na lista (se não achar, usa 'OUTRO')
posicao_padrao = 5
if setor_na_url in lista_setores:
    posicao_padrao = lista_setores.index(setor_na_url)

# 5. O Selectbox agora "mira" no setor do QR Code automaticamente
setor = st.selectbox("Setor/Unidade", lista_setores, index=posicao_padrao)
    volume = st.radio("Volume Estimado", ["1", "2", "3"], horizontal=True)
    
    if st.button("Enviar Notificação"):
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        id_fluxo = str(int(datetime.datetime.now().timestamp()))
        # Ordem: ID_Fluxo, Data_Hora_Notificacao, Setor_Unidade, Volume_Estimado, Status, Responsavel, Data_Coleta, Obs
        aba.append_row([id_fluxo, agora, setor, volume, "PENDENTE", "", "", ""])
        st.success("✅ Notificação enviada para a Expedição!")

with tab2:
    st.header("Pendências em Tempo Real")
    if st.button("🔄 Atualizar"):
        st.rerun()
    
    dados = aba.get_all_records()
    pendentes = [d for d in dados if d.get('Status') == 'PENDENTE']
    
    if pendentes:
        st.table(pendentes)
    else:
        st.info("Nenhuma caixa pendente de coleta no momento. ✅")


