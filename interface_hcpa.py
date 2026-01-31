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

MAPA_URGENCIA = {
    "🔴 Está atrapalhando": 3,
    "🟡 Ideal coletar hoje": 2,
    "🟢 Pode esperar": 1
}

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

    # garante todas as colunas
    for col in COLUNAS:
        if col not in df.columns:
            df[col] = None

    df["Data_Hora"] = pd.to_datetime(df["Data_Hora"], errors="coerce")
    df["Urgencia"] = df["Urgencia"].fillna("🟢 Pode esperar")
    df["Status"] = df["Status"].fillna("Aberto")

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
            list(MAPA_URGENCIA.keys())
        )

        col1, col2 = st.columns(2)
        with col1:
            pretas = st.radio("Caixas Pretas", ["0", "≤5", "≤10", "mais que 10"])
            skates = st.number_input("Skates disponíveis", min_value=0)
        with col2:
            azuis = st.radio("Caixas Azuis", ["0", "≤30", "mais que 30"])
            carrinhos = st.number_input("Carrinhos disponíveis", min_value=0)

        enviar = st.form_submit_button("🚀 Enviar alerta")

    if enviar:
        criar_alerta(setor_url, urgencia, pretas, azuis, skates, carrinhos)
        st.success("✅ Alerta enviado com sucesso")

# =============================
# ABA 2 — EXPEDIÇÃO (POR SETOR)
# =============================
with tabs[1]:
    st.subheader("🚚 Ordem sugerida de coleta por setor")

    df = carregar()
    ativos = df[df["Status"].isin(STATUS_ATIVOS)].copy()

    if ativos.empty:
        st.info("Nenhum alerta ativo")
    else:
        agora = datetime.now()

        ativos["Tempo_Aberto"] = (
            agora - ativos["Data_Hora"]
        ).dt.total_seconds().fillna(0) / 60

        ativos["Peso_Urgencia"] = ativos["Urgencia"].map(MAPA_URGENCIA).fillna(1)

        # 🔹 AGREGAÇÃO POR SETOR
        resumo_setor = (
            ativos
            .groupby("ID_Setor")
            .agg(
                Qtde_Alertas=("ID_Alerta", "count"),
                Tempo_Max=("Tempo_Aberto", "max"),
                Peso_Max=("Peso_Urgencia", "max"),
            )
            .reset_index()
        )

        # 🔹 ORDENAÇÃO ESTRATÉGICA
        resumo_setor = resumo_setor.sort_values(
            by=["Peso_Max", "Tempo_Max"],
            ascending=False
        )

        for _, setor in resumo_setor.iterrows():
            setor_nome = setor["ID_Setor"]

            with st.expander(
                f"📍 {setor_nome} | "
                f"{int(setor['Tempo_Max'])} min | "
                f"{int(setor['Qtde_Alertas'])} avisos"
            ):
                df_setor = ativos[ativos["ID_Setor"] == setor_nome]

                st.markdown("**Alertas ativos neste setor:**")
                st.table(
                    df_setor[
                        ["Urgencia", "Qtd_Pretas", "Qtd_Azuis", "Status", "Data_Hora"]
                    ]
                )

                with st.form(f"form_setor_{setor_nome}"):
                    st.markdown("### ✅ Finalizar coleta do setor")

                    responsavel = st.text_input(
                        "Cartão ponto do responsável",
                        max_chars=10,
                        key=f"resp_{setor_nome}"
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        pretas_real = st.number_input(
                            "Pretas coletadas (total setor)",
                            min_value=0,
                            key=f"pr_{setor_nome}"
                        )
                    with col2:
                        azuis_real = st.number_input(
                            "Azuis coletadas (total setor)",
                            min_value=0,
                            key=f"az_{setor_nome}"
                        )

                    confirmar = st.form_submit_button("✔️ Confirmar coleta do setor")

                if confirmar:
                    if not responsavel.isdigit() or len(responsavel) > 10:
                        st.error("⚠️ Informe um cartão ponto válido (até 10 dígitos)")
                    else:
                        # Fecha TODOS os alertas do setor
                        for id_alerta in df_setor["ID_Alerta"]:
                            atualizar_status(id_alerta, "Coletado")
                            atualizar_responsavel(id_alerta, responsavel)

                        st.success(
                            f"✅ Coleta do setor **{setor_nome}** registrada com sucesso"
                        )
                        st.rerun()


# =============================
# ABA 3 — LAVAGEM
# =============================
with tabs[2]:
    st.subheader("🧼 Planejamento da Lavagem")

    df = carregar()
    coletados = df[df["Status"] == "Coletado"]

    ultimos_7 = df[df["Data_Hora"] >= datetime.now() - timedelta(days=7)]
    media_diaria = round(len(ultimos_7) / 7, 1)
    pico = ultimos_7.groupby(ultimos_7["Data_Hora"].dt.date).size().max()

    c1, c2, c3 = st.columns(3)
    c1.metric("Aguardando lavagem", len(coletados))
    c2.metric("Média diária (7d)", media_diaria)
    c3.metric("Pico recente", int(pico) if pd.notna(pico) else 0)

    if len(coletados) < 20:
        st.warning("🔴 Volume abaixo do ideal para iniciar lote")
    elif len(coletados) < 40:
        st.info("🟡 Lote aceitável")
    else:
        st.success("🟢 Lote eficiente")

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




