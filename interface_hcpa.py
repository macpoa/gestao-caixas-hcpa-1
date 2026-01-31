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
# cria as abas
tab1, tab2 = st.tabs(["Notificar Coleta", "Painel da Expedição"])


# Captura de Setor via URL (Ex: ?setor=ONCO)
query_params = st.query_params
setor_url = query_params.get("setor", "Geral")
# --- ABA 1: NOTIFICAR ---
with tab1:
    with st.form("form_alerta"):
        st.write("Preencha os dados abaixo para solicitar a coleta:")
        setor_selecionado = st.selectbox("Selecione seu Setor", ["Almoxarifado", "Oncologia", "Bloco Cirúrgico", "Genética"])
        qtd_pretas = st.radio("Quantidade de Caixas Pretas", ["0", "<= 5", "<= 10", "> 10"])
        qtd_azuis = st.radio("Quantidade de Caixas Azuis", ["0", "<= 30", "> 30"])
        
        # O segredo está aqui: o botão deve ser a última coisa do formulário
        submetido = st.form_submit_button("🚀 Enviar Alerta Inteligente")

    # A lógica de gravação deve ficar FORA do bloco 'with st.form'
    if submetido:
        try:
            # Aqui vai o seu código de 'aba.append_row'
            st.success("✅ Alerta enviado com sucesso para a Expedição!")
        except Exception as e:
            st.error(f"Erro ao gravar: {e}")

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

# --- ABA 2: PAINEL DA EXPEDIÇÃO ---
with tab2:
    st.subheader("📊 Painel de Alertas em Aberto")
    
    try:
        # Lê todos os dados da aba da planilha
        dados = aba.get_all_records()
        
        if dados:
            import pandas as pd
            df_visualizacao = pd.DataFrame(dados)
            st.dataframe(df_visualizacao)
        else:
            st.info("Não há alertas registrados no momento.")
            
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")









