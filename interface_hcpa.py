import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# ======================================================
# CONFIGURAÇÃO
# ======================================================
st.set_page_config(page_title="Logística de Caixas HCPA", layout="wide")

NOME_PLANILHA = "Gestao_Caixas_HCPA"
ABA_ALERTAS = "db_alertas"
ABA_LAVAGEM = "db_lavagem"
COLUNAS = ["ID_Alerta", "Data_Hora", "ID_Setor", "Urgencia", "Qtd_Pretas", "Qtd_Azuis", "Skates", "Carrinhos", "Status", "Responsavel"]
STATUS_ATIVOS = ["Aberto", "Em Coleta", "Coletado"]

MAPA_URGENCIA = {
    "🔴 Está atrapalhando": 3,
    "🟡 Ideal coletar hoje": 2,
    "🟢 Pode esperar": 1
}

# ======================================================
# CONEXÃO GOOGLE SHEETS
# ======================================================
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

aba_alertas = planilha.worksheet(ABA_ALERTAS)
aba_lavagem = planilha.worksheet(ABA_LAVAGEM)

# ======================================================
# FUNÇÕES AUXILIARES
# ======================================================
def novo_id(prefixo):
    return f"{prefixo}{datetime.now().strftime('%Y%m%d%H%M%S')}"

def carregar_alertas():
    dados = aba_alertas.get_all_records()

    df = pd.DataFrame(dados)

    # garante colunas
    for col in COLUNAS:
        if col not in df.columns:
            df[col] = None

    df["Data_Hora"] = pd.to_datetime(df["Data_Hora"], errors="coerce")
    df["Urgencia"] = df["Urgencia"].fillna("🟢 Pode esperar")
    df["Status"] = df["Status"].fillna("Aberto")
    df["Responsavel"] = df["Responsavel"].fillna("")

    return df

def carregar_lavagem():
    df = pd.DataFrame(aba_lavagem.get_all_records())
    for c in ["Chegada_Lavagem", "Inicio_Lavagem", "Fim_Lavagem"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df

def atualizar_alerta(id_alerta, status, responsavel=None):
    cell = aba_alertas.find(id_alerta)
    row = cell.row
    aba_alertas.update_cell(row, 9, status)
    if responsavel:
        aba_alertas.update_cell(row, 10, responsavel)

# ======================================================
# INTERFACE
# ======================================================
st.title("📦 Logística de Caixas – HCPA")
tabs = st.tabs(["🔔 Setor", "🚚 Expedição", "🧼 Lavagem", "🧠 Gestão", "📋 Inventário"])
setor_url = st.query_params.get("setor", "Geral")

# ======================================================
# ABA 1 — SETOR
# ======================================================
with tabs[0]:
    st.header(f"🔔 Notificar Coleta — {setor_url}")

    with st.form("setor"):
        urgencia = st.radio("Impacto no trabalho", list(MAPA_URGENCIA.keys()))

        c1, c2 = st.columns(2)
        with c1:
            pretas = st.radio("Caixas Pretas", ["0", "≤5", "≤10", "mais que 10"])
            skates = st.number_input("Skates disponíveis", min_value=0)
        with c2:
            azuis = st.radio("Caixas Azuis", ["0", "≤30", "mais que 30"])
            carrinhos = st.number_input("Carrinhos disponíveis", min_value=0)

        enviar = st.form_submit_button("🚀 Enviar alerta")

    if enviar:
        aba_alertas.append_row([
            novo_id("ALT"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            setor_url,
            urgencia,
            pretas,
            azuis,
            skates,
            carrinhos,
            "Aberto",
            ""
        ])
        st.success("✅ Alerta enviado")

# ======================================================
# ABA 2 — EXPEDIÇÃO (POR SETOR)
# ======================================================
with tabs[1]:
    st.subheader("🚚 Ordem sugerida de coleta por setor")

    df = carregar_alertas()
    ativos = df[df["Status"].isin(STATUS_ATIVOS)].copy()

    if ativos.empty:
        st.info("Nenhum alerta ativo")
    else:
        ativos["Tempo_Aberto"] = (
            datetime.now() - ativos["Data_Hora"]
        ).dt.total_seconds().fillna(0) / 60

        ativos["Peso"] = ativos["Urgencia"].map(MAPA_URGENCIA).fillna(1)

        resumo = (
            ativos.groupby("ID_Setor")
            .agg(
                Qtde=("ID_Alerta", "count"),
                Tempo_Max=("Tempo_Aberto", "max"),
                Peso_Max=("Peso", "max")
            )
            .reset_index()
            .sort_values(by=["Peso_Max", "Tempo_Max"], ascending=False)
        )

        for _, s in resumo.iterrows():
            setor = s["ID_Setor"]
            df_setor = ativos[ativos["ID_Setor"] == setor]

            with st.expander(f"📍 {setor} | {int(s['Tempo_Max'])} min | {int(s['Qtde'])} avisos"):
                st.table(df_setor[["Urgencia", "Qtd_Pretas", "Qtd_Azuis", "Status", "Data_Hora"]])

                with st.form(f"coleta_{setor}"):
                    resp = st.text_input("Cartão ponto (até 10 dígitos)", max_chars=10)
                    confirmar = st.form_submit_button("✔️ Confirmar coleta do setor")

                if confirmar:
                    if not resp.isdigit():
                        st.error("Cartão ponto inválido")
                    else:
                        for id_alerta in df_setor["ID_Alerta"]:
                            atualizar_alerta(id_alerta, "Coletado", resp)
                        st.success("✅ Coleta registrada")
                        st.rerun()

# ======================================================
# ABA 3 — LAVAGEM
# ======================================================
with tabs[2]:
    st.subheader("🧼 Lavagem de Caixas")

    # REGISTRAR CHEGADA
    with st.form("chegada_lavagem"):
        c1, c2 = st.columns(2)
        with c1:
            pretas = st.number_input("Pretas que chegaram", min_value=0)
        with c2:
            azuis = st.number_input("Azuis que chegaram", min_value=0)

        turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite"])
        enviar = st.form_submit_button("Registrar chegada")

    if enviar:
        agora = datetime.now()
        aba_lavagem.append_row([
            novo_id("LOT"),
            agora.strftime("%Y-%m-%d %H:%M:%S"),
            pretas,
            azuis,
            "",
            "",
            "",
            "Em Lavagem",
            agora.strftime("%Y-%m-%d %H:%M:%S"),
            "",
            turno
        ])
        st.success("✅ Lote iniciado")
        st.rerun()

    # FECHAR LOTE (Ajustado)
    df_lav = carregar_lavagem()
    ativos = df_lav[df_lav["Status"] == "Em Lavagem"]

    for _, row in ativos.iterrows():
        with st.expander(f"🧺 {row['ID_Lote']} | {row['Turno']}"):
            with st.form(f"fechar_{row['ID_Lote']}"):
                p = st.number_input("Pretas lavadas", min_value=0, key=f"p_{row['ID_Lote']}")
                a = st.number_input("Azuis lavadas", min_value=0, key=f"a_{row['ID_Lote']}")
                fechar = st.form_submit_button("✔️ Fechar lote")

            if fechar:
                # Localiza a linha correta
                cell = aba_lavagem.find(row["ID_Lote"])
                r = cell.row
                
                # Cálculo da diferença
                entrada = (row["Qtd_Pretas_Entrada"] or 0) + (row["Qtd_Azuis_Entrada"] or 0)
                lavadas = p + a
                diferenca = lavadas - entrada
                
                # Atualiza as colunas E até J (Pretas_Lav, Azuis_Lav, Dif, Status, Prev, Fim)
                aba_lavagem.update(f"E{r}:J{r}", [[
                    p, 
                    a, 
                    diferenca, 
                    "Finalizado", 
                    row["Previsao_Termin"], 
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]])

                st.success(f"✅ Lote {row['ID_Lote']} finalizado!")
                st.rerun()

# ======================================================
# ABA 4 — GESTÃO
# ======================================================
with tabs[3]:
    st.subheader("📊 Indicadores")

    df_lav = carregar_lavagem()
    final = df_lav[df_lav["Status"] == "Finalizado"].copy()

    final["Tempo"] = (
        final["Fim_Lavagem"] - final["Inicio_Lavagem"]
    ).dt.total_seconds() / 3600

    backlog = (
        df_lav["Qtd_Pretas_Entrada"].sum() + df_lav["Qtd_Azuis_Entrada"].sum()
    ) - (
        df_lav["Qtd_Pretas_Lavadas"].sum() + df_lav["Qtd_Azuis_Lavadas"].sum()
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Backlog real", backlog)
    c2.metric("Tempo médio (h)", round(final["Tempo"].mean(), 2))
    c3.metric("Eficiência (%)",
              round((final["Qtd_Pretas_Lavadas"].sum() + final["Qtd_Azuis_Lavadas"].sum())
                    / max(1, final["Qtd_Pretas_Entrada"].sum() + final["Qtd_Azuis_Entrada"].sum()) * 100, 1))

    st.bar_chart(final.groupby("Turno")["Qtd_Pretas_Lavadas"].sum() +
                 final.groupby("Turno")["Qtd_Azuis_Lavadas"].sum())

# ======================================================
# ABA 5 — INVENTÁRIO
# ======================================================
with tabs[4]:
    st.subheader("📋 Inventário por Exclusão")

    TOTAL = 1000
    prontas = st.number_input("Prontas", 0)
    separacao = st.number_input("Em separação", 0)
    entrega = st.number_input("Aguardando entrega", 0)
    lavagem = st.number_input("Na lavagem", 0)

    internas = prontas + separacao + entrega + lavagem
    campo = TOTAL - internas
    dispersao = round((campo / TOTAL) * 100, 1)

    st.metric("Em circulação", campo, f"{dispersao}%")




