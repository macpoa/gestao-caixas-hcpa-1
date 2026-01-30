import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Configuração de Acesso (Usando o que já temos nos Secrets)
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

# Nome da sua planilha (Verifique se o nome está exatamente igual ao do Google Sheets)
NOME_PLANILHA = "Logística de Caixas - HCPA" 

try:
    planilha = client.open(NOME_PLANILHA)
    # Tenta abrir a aba db_alertas, se não existir, usa a primeira aba
    try:
        aba = planilha.worksheet("db_alertas")
    except:
        aba = planilha.get_worksheet(0) 
except Exception as e:
    st.error(f"Erro ao abrir planilha: {e}")
# --- INTERFACE ---
st.title("📦 Logística de Caixas HCPA - Versão 2.0")

# Captura de Setor via URL (Ex: ?setor=ONCO)
query_params = st.query_params
setor_url = query_params.get("setor", "Geral")

with st.form("form_notificacao"):
    st.header(f"🔔 Notificar Coleta: {setor_url}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Caixas Pretas")
        qtd_pretas = st.radio("Quantidade (Pretas)", ["0", "Até 05", "Até 10", "+ de 10"], key="pretas")
        skates = st.number_input("Quantidade de Skates", min_value=0, step=1)

    with col2:
        st.subheader("Caixas Azuis")
        qtd_azuis = st.radio("Quantidade (Azuis)", ["0", "Até 10", "Até 30", "+ de 30"], key="azuis")
        carrinhos = st.number_input("Quantidade de Carrinhos", min_value=0, step=1)

    obs = st.text_area("Observações (Ex: Vazamento, Caixa Danificada)")
    
    submetido = st.form_submit_button("🚀 Enviar Alerta Inteligente")

    if submetido:
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        id_alerta = f"ALT{len(df_alertas)+1:03d}"
        
        # Estrutura exatamente igual às colunas que você criou na planilha
        novo_alerta = pd.DataFrame([{
            "ID_Alerta": id_alerta,
            "Data_Hora": agora,
            "ID_Setor": setor_url,
            "Qtd_Pretas": qtd_pretas,
            "Qtd_Azuis": qtd_azuis,
            "Skates": skates,
            "Carrinhos": carrinhos,
            "Status": "Aberto",
            "Responsavel": "Aguardando"
        }])
        
        # Envia para a planilha (aba db_alertas)
        spread.df_to_sheet(novo_alerta, sheet='db_alertas', index=False, append=True)
        
        st.success(f"✅ Alerta {id_alerta} enviado com sucesso!")
        st.balloons()

# --- PAINEL DE DEMANDA (Visão Simplificada para hoje) ---
st.divider()
st.subheader("📊 Painel de Alertas em Aberto")
df_visualizacao = spread.sheet_to_df(sheet='db_alertas', index=0)

if not df_visualizacao.empty:
    # Filtra apenas o que não foi coletado ainda
    pendentes = df_visualizacao[df_visualizacao['Status'] == 'Aberto']
    st.dataframe(pendentes)
else:
    st.info("Nenhum alerta pendente.")




