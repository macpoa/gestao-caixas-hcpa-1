import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# =============================
# CONFIGURAÇÃO
# =============================
st.set_page_config(page_title="Logística de Caixas HCPA", layout="wide")

NOME_PLANILHA = "Gestao_Caixas_HCPA"
ABA_ALERTAS = "db_alertas"

COLUNAS = [
    "ID_Alerta", "Data_Hora", "ID_Setor", "Urgencia",
    "Qtd_Pretas", "Qtd_Azuis", "Skates", "Carrinhos", "Status"
]

STATUS_ATIVOS = ["Aberto", "Em Coleta", "Coletado"]

# =============================
# CONEXÃO GOOGLE SHEETS
# =============================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)
planilha = client.open(NOME_PLANILHA)
aba = planilha.worksheet(ABA_ALERTAS)

# =============================
# FUNÇÕES
# =============================
def carregar():
    dados = aba.get_all_records()
    df = pd.DataFrame(dados) if dados else pd.DataFrame(columns=COLUNAS)
    df["Data_Hora"] = pd.to_datetime(df["Data_Hora"], errors="coerce")
    return df

def novo_id():
    return f"ALT{datetime.now().strftime('%Y%m%d%H%M%S')}"

def atualizar_status(id_alerta, status):
    cell = aba.find(id_alerta)
    aba.update_cell(cell.row, COLUNAS.index("Status") + 1, status)

def criar_alerta(setor, urgencia, pretas, azuis, skates, carrinhos):
    aba.append_row([
        novo_id(),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        setor,
        urgencia,
        pretas,
        azuis,
        skates,
        carrinhos,
        "Aberto"
    ], value_input_option="USER_ENTERED")

# =============================
# INTERFACE
# =============================
st.title("📦 Logística de Caixas – HCPA")

tabs = st.tabs(["🔔 Setor", "🚚 Expedição", "🧼 Lavagem", "🧠 Gestão", "📋 Inventário"])

setor_url = st.query_params.get("setor", "Geral")

# =============================
# ABA 1 — SETOR
# =============================
with tabs[0]:
    st.header(f"🔔 Notificar Coleta — {setor_url}")

    with st.form("setor"):
        urgencia = st.radio(
            "Impacto no trabalho",
            ["🟢 Pode esperar", "🟡 Ideal coletar hoje", "🔴 Está atrapalhando"]
        )

        col1, col2 = st.columns(2)
        with col1:
            pretas = st.radio("Caixas Pretas", ["0", "≤5", "≤10", " >10"])
            skates = st.number_input("Skates disponíveis", min_value=0)
        with col2:
            azuis = st.radio("Caixas Azuis", ["0", "≤30", " >30"])
            carrinhos = st.number_input("Carrinhos disponíveis", min_value=0)

        enviar = st.form_submit_button("🚀 Enviar alerta")

    if enviar:
        criar_alerta(setor_url, urgencia, pretas, azuis, skates, carrinhos)
        st.success("✅ Alerta enviado com sucesso")

# =============================
# ABA 2 — EXPEDIÇÃO (PRIORIZAÇÃO)
# =============================
with tabs[1]:
    st.subheader("🚚 Ordem sugerida de coleta")

    df = carregar()
    ativos = df[df["Status"].isin(["Aberto", "Em Coleta"])].copy()

    if ativos.empty:
        st.info("Nenhum alerta ativo")
    else:
        ativos["Tempo_Aberto"] = (datetime.now() - ativos["Data_Hora"]).dt.total_seconds() / 60
        ativos["Peso_Urgencia"] = ativos["Urgencia"].map({
            "🔴 Está atrapalhando": 3,
            "🟡 Ideal coletar hoje": 2,
            "🟢 Pode esperar": 1
        })

        ativos = ativos.sort_values(
            by=["Peso_Urgencia", "Tempo_Aberto"],
            ascending=False
        )

        for _, row in ativos.iterrows():
            with st.expander(
                f"{row['Urgencia']} | {row['ID_Setor']} | {int(row['Tempo_Aberto'])} min"
            ):
                st.write(f"Pretas: {row['Qtd_Pretas']} | Azuis: {row['Qtd_Azuis']}")

                if row["Status"] == "Aberto":
                    if st.button("🟡 Assumir", key=row["ID_Alerta"]):
                        atualizar_status(row["ID_Alerta"], "Em Coleta")
                        st.rerun()

                if row["Status"] == "Em Coleta":
                    if st.button("✅ Coletado", key=f"col_{row['ID_Alerta']}"):
                        atualizar_status(row["ID_Alerta"], "Coletado")
                        st.rerun()

# =============================
# ABA 3 — LAVAGEM
# =============================
with tabs[2]:
    st.subheader("🧼 Planejamento da Lavagem")

    df = carregar()
    coletados = df[df["Status"] == "Coletado"]

    hoje = datetime.now().date()
    ultimos_7 = df[df["Data_Hora"] >= datetime.now() - timedelta(days=7)]

    media_diaria = round(len(ultimos_7) / 7, 1)
    pico = ultimos_7.groupby(ultimos_7["Data_Hora"].dt.date).size().max()

    c1, c2, c3 = st.columns(3)
    c1.metric("Aguardando lavagem", len(coletados))
    c2.metric("Média diária (7d)", media_diaria)
    c3.metric("Pico recente", pico if pd.notna(pico) else 0)

    if len(coletados) < 20:
        st.warning("🔴 Volume abaixo do ideal para iniciar lote")
    elif len(coletados) < 40:
        st.info("🟡 Lote aceitável")
    else:
        st.success("🟢 Lote eficiente")

    with st.form("lavar"):
        qtd = st.number_input("Quantidade lavada agora", min_value=1)
        finalizar = st.form_submit_button("Finalizar lote")

    if finalizar:
        for id_alerta in coletados.head(qtd)["ID_Alerta"]:
            atualizar_status(id_alerta, "Higienizado")
        st.success("✅ Lote registrado")
        st.rerun()

# =============================
# ABA 4 — GESTÃO
# =============================
with tabs[3]:
    st.subheader("🧠 Gestão Operacional")

    df = carregar()

    st.write("**Setores com mais impacto**")
    st.bar_chart(df["ID_Setor"].value_counts())

    st.write("**Distribuição por status**")
    st.table(df["Status"].value_counts())

# =============================
# ABA 5 — INVENTÁRIO
# =============================
with tabs[4]:
    st.subheader("📋 Inventário por Exclusão")

    TOTAL = 1000
    st.info(f"Patrimônio total: {TOTAL}")

    col1, col2 = st.columns(2)
    with col1:
        prontas = st.number_input("Prontas", min_value=0, value=120)
        separacao = st.number_input("Em separação", min_value=0, value=60)
    with col2:
        entrega = st.number_input("Aguardando entrega", min_value=0, value=40)
        lavagem = st.number_input("Na lavagem", min_value=0, value=50)

    internas = prontas + separacao + entrega + lavagem
    campo = TOTAL - internas
    dispersao = round((campo / TOTAL) * 100, 1)

    c1, c2, c3 = st.columns(3)
    c1.metric("Sob controle", internas)
    c2.metric("Em circulação", campo, f"{dispersao}%")
    c3.metric("Status", "🔴 Crítico" if dispersao > 35 else "🟢 Saudável")

    if dispersao > 35:
        st.error("⚠️ Índice de dispersão acima do limite seguro")










