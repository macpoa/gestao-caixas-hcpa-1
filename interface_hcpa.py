import streamlit as st
from gspread_pandas import Spread
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Logística HCPA 2.0", page_icon="📦", layout="wide")

# --- CONEXÃO COM GOOGLE SHEETS ---
nome_planilha = "Gestão_Caixas_HCPA" 
try:
    # Conecta à planilha usando suas secrets já configuradas
    spread = Spread(nome_planilha)
    # Tenta ler a aba de alertas para contar as linhas
    df_alertas = spread.sheet_to_df(sheet='db_alertas', index=0)
except Exception as e:
    st.error(f"Erro de conexão: {e}. Verifique se a aba 'db_alertas' existe na planilha.")
    st.stop()

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


