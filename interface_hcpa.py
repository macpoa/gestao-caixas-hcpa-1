import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime

# -----------------------------
# CONFIGURAÇÃO GOOGLE SHEETS
# -----------------------------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

NOME_PLANILHA = "Gestao_Caixas_HCPA"

try:
    planilha = client.open(NOME_PLANILHA)
    aba_alertas = planilha.worksheet("db_alertas")
except Exception as e:
    st.error(f"Erro ao abrir planilha ou aba db_alertas: {e}")
    st.stop()

# -----------------------------
# LEITURA BASE ATUAL
# -----------------------------
dados_alertas = aba_alertas.get_all_records()
df_alertas = pd.DataFrame(dados_alertas)

# -----------------------------
# INTERFACE
# -----------------------------
st.set_page_config(page_title="Logística de Caixas HCPA", layout="wide")
st.title("📦 Logística de Caixas – HCPA | MVP")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔔 Setor", "🚚 Expedição", "🧼 Lavagem", "🧠 Gestão", "📋 Inventário"])

# Captura de Setor via QR (URL)
query_params = st.query_params
setor_url = query_params.get("setor", "Geral")

# =============================
# ABA 1 — SETOR (QR CODE)
# =============================
with tab1:
    with st.form("form_notificacao"):
        st.header(f"🔔 Notificar Coleta — Setor: {setor_url}")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Caixas Pretas")
            qtd_pretas = st.radio(
                "Quantidade estimada",
                ["0", "≤5", "≤10", ">10"]
            )
            skates = st.number_input(
                "Skates disponíveis",
                min_value=0,
                step=1
            )

        with col2:
            st.subheader("Caixas Azuis")
            qtd_azuis = st.radio(
                "Quantidade estimada",
                ["0", "≤30", ">30"]
            )
            carrinhos = st.number_input(
                "Carrinhos disponíveis",
                min_value=0,
                step=1
            )

        obs = st.text_area("Observações operacionais")

        submitted = st.form_submit_button("🚀 Enviar Alerta")

    # 👇 ESTE BLOCO TEM QUE FICAR FORA DO with st.form
    if submitted:
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        novo_id = f"ALT{len(df_alertas) + 1:05d}"

        nova_linha = [
            novo_id,
            agora,
            setor_url,
            qtd_pretas,
            qtd_azuis,
            skates,
            carrinhos,
            "Aberto"
        ]

        aba_alertas.append_row(
            nova_linha,
            value_input_option="USER_ENTERED"
        )

        st.success(f"✅ Alerta {novo_id} registrado com sucesso!")

# =============================
# ABA 2 — EXPEDIÇÃO
# =============================
# Dentro de with tab2:
with tab2:
    st.subheader("🚚 Gestão de Coletas")
    
    # Recarregar dados para garantir atualização
    df_atual = pd.DataFrame(aba_alertas.get_all_records())
    st.write("Colunas detectadas:", df_atual.columns.tolist())
    if not df_atual.empty:
        # Filtrar apenas o que não está "Fechado" ou "Lavado"
        df_operacional = df_atual[df_atual["Status"].isin(["Aberto", "Em Coleta", "Coletado"])]
        
        for index, row in df_operacional.iterrows():
            with st.expander(f"📍 {row['ID_Setor']} - {row['ID_Alerta']} ({row['Status']})"):
                col_a, col_b, col_c = st.columns(3)
                col_a.write(f"**Pretas:** {row['Qtd_Pretas_Classe']} | **Azuis:** {row['Qtd_Azuis_Classe']}")
                
                # O gspread usa índice 1-based e tem cabeçalho, então a linha no Sheets é index + 2
                linha_sheets = index + 2 
                
                if row["Status"] == "Aberto":
                    if col_b.button("🟡 Assumir", key=f"assumir_{row['ID_Alerta']}"):
                        aba_alertas.update_cell(linha_sheets, 8, "Em Coleta") # Coluna 8 é Status
                        st.rerun()
                
                if row["Status"] == "Em Coleta":
                    if col_b.button("✅ Coletado", key=f"coletar_{row['ID_Alerta']}"):
                        aba_alertas.update_cell(linha_sheets, 8, "Coletado")
                        # Opcional: registrar horário da coleta em outra coluna se desejar
                        st.rerun()
    else:
        st.info("Sem alertas ativos.")
# =============================
# ABA 3 — CONTROLE DE HIGIENIZAÇÃO
# =============================
with tab3:
    st.subheader("🧼 Controle de Higienização")
    dados = aba_alertas.get_all_records()

    colunas = [
        "ID_Alerta",
        "Data_Hora",
        "ID_Setor",
        "Setor_Nome",
        "Qtd_Pretas",
        "Qtd_Azuis",
        "Skates",
        "Carrinhos",
        "Status",
        "Responsavel"
    ]

if dados:
    df_atual = pd.DataFrame(dados)
else:
    df_atual = pd.DataFrame(columns=colunas)

    # Cálculo rápido baseado no df_atual
    sujas_pretas = df_atual.get("Status", []).eq("Coletado").sum()
    
    st.metric("Caixas no Pátio (Aguardando Lavagem)", sujas_pretas)
    
    with st.form("fluxo_lavagem"):
        lote_qtd = st.number_input("Quantidade de caixas no lote", min_value=1)
        tipo_caixa = st.selectbox("Tipo", ["Preta", "Azul"])
        botao_lavagem = st.form_submit_button("Finalizar Higienização de Lote")
        
        if botao_lavagem:
            # Aqui você faria o append_row na aba db_lavagem
            # E mudaria o status das caixas em db_alertas para "Higienizada"
            st.success(f"Lote de {lote_qtd} {tipo_caixa} registrado!")

# =============================
# ABA 4 — PAINEL DE GESTAO
# =============================
with tab4:
    st.subheader("📊 Painel de Gestão (Cérebro)")
    
    if not df_atual.empty:
        df_atual['Data_Hora_Notificacao'] = pd.to_datetime(df_atual['Data_Hora_Notificacao'])
        
        # 1. Top 5 Setores (Últimos 7 dias)
        st.write("**📍 Top 5 Setores Críticos (7 dias)**")
        top_setores = df_atual[df_atual['Status'] != "Aberto"]['ID_Setor'].value_counts().head(5)
        st.bar_chart(top_setores)
        
        # 2. Volume por Status
        st.write("**📦 Fluxo de Caixas Atual**")
        fluxo = df_atual['Status'].value_counts()
        st.table(fluxo)
        
        # 3. Alerta de Gargalo (Exemplo de lógica)
        tempo_limite = 30 # minutos
        # Lógica: Se 'Aberto' há mais de X min, avisar.
        agora = pd.Timestamp.now()
        atrasados = df_atual[(df_atual['Status'] == 'Aberto') & 
                             ((agora - df_atual['Data_Hora_Notificacao']).dt.total_seconds() > tempo_limite * 60)]
        
        if not atrasados.empty:
            st.warning(f"⚠️ Existem {len(atrasados)} alertas parados há mais de {tempo_limite} min!")

# =============================
# ABA 5 — INVENTÁRIO DE CAIXAS
# =============================
with tab5:
    st.header("📋 Inventário de Ativos")
    
    # 1. Definição do Patrimônio Total (Ajuste conforme sua realidade)
    TOTAL_CAIXAS_SISTEMA = 500  # Exemplo: total que o hospital possui
    
    st.info(f"Patrimônio Total Cadastrado: **{TOTAL_CAIXAS_SISTEMA} unidades**")

    # 2. Inputs de Contagem Real (O que a expedição enxerga)
    with st.expander("📝 Atualizar Contagem Física (Estoque/Expedição)", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            prontas = st.number_input("Prontas para Uso (Limpas)", min_value=0, value=100)
            em_separacao = st.number_input("Em Separação", min_value=0, value=50)
        with col2:
            aguardando_entrega = st.number_input("Aguardando Entrega", min_value=0, value=30)
            em_lavagem = st.number_input("Na Lavanderia (Em processo)", min_value=0, value=40)

    # 3. Lógica do "Cérebro"
    # Somamos o que está "dentro de casa"
    caixas_internas = prontas + em_separacao + aguardando_entrega + em_lavagem
    
    # O que sobra, por exclusão, está nos setores ou pontos de coleta
    caixas_no_campo = TOTAL_CAIXAS_SISTEMA - caixas_internas
    
    # Cálculo do percentual no campo
    percentual_campo = (caixas_no_campo / TOTAL_CAIXAS_SISTEMA) * 100
    limite_alerta = 30.0  # Seu limite de 30%

    # 4. Exibição dos Indicadores
    st.divider()
    c1, c2, c3 = st.columns(3)
    
    c1.metric("Localizadas (Controle)", caixas_internas)
    
    # Cor do indicador de campo: Vermelho se passar de 30%
    cor_delta = "normal" if percentual_campo <= limite_alerta else "inverse"
    c2.metric(
        "Em Circulação (Setores/Coleta)", 
        caixas_no_campo, 
        f"{percentual_campo:.1f}% do total",
        delta_color=cor_delta
    )
    
    c3.metric("Status do Giro", "Saudável" if percentual_campo <= limite_alerta else "Crítico")

    # 5. Alerta Visual
    if percentual_campo > limite_alerta:
        st.error(f"⚠️ **Atenção:** O volume de caixas espalhadas nos setores ({percentual_campo:.1f}%) ultrapassou o limite de segurança de {limite_alerta}%. Risco de desabastecimento na expedição!")
    else:
        st.success("✅ Fluxo de caixas dentro dos parâmetros operacionais.")

    # Opcional: Gráfico de Pizza para visualização rápida
    df_pizza = pd.DataFrame({
        "Categoria": ["Prontas", "Separação", "Entrega", "Lavagem", "Nos Setores"],
        "Quantidade": [prontas, em_separacao, aguardando_entrega, em_lavagem, caixas_no_campo]
    })
    import plotly.express as px
    fig = px.pie(df_pizza, values='Quantidade', names='Categoria', title="Distribuição do Inventário")
    st.plotly_chart(fig)
















