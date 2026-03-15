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


# nomes das abas na planilha
ABA_ALERTAS   = "db_alertas"      # cuidado: na planilha está db_alerta (sem s)
ABA_LAVAGEM   = "db_lavagem"
ABA_SETORES   = "db_setores"
ABA_HISTORICO = "db_historico"   # respeitar maiúsculas/minúsculas

# colunas esperadas em cada aba
COL_ALERTAS = [
    "ID_Alerta", "Data_Hora", "ID_Setor", "Urgencia",
    "Setor_Nome", "Qtd_Pretas", "Qtd_Azuis",
    "Skates", "Carrinhos", "Status", "Responsavel"
]

COL_SETORES = [
    "ID_Setor", "Nome_Setor", "Bloco",
    "Andar", "Distancia_Metros", "Prioridade"
]

COL_LAVAGEM = [
    "ID_Lote", "Chegada_Lavagem",
    "Qtd_Pretas_Entrada", "Qtd_Azuis_Entrada",
    "Qtd_Pretas_Lavadas", "Qtd_Azuis_Lavadas",
    "Diferenca", "Status",
    "Previsao_Termino", "Inicio_Lavagem",
    "Fim_Lavagem", "Turno"
]

COL_HISTORICO = [
    "ID_Alerta", "Data_Hora", "ID_Setor",
    "Setor_Nome", "Qtd_Pretas", "Qtd_Azuis",
    "Skates", "Carrinhos", "Status", "Responsavel"
]

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

def carregar_lavagem():
    df = pd.DataFrame(aba_lavagem.get_all_records())
    for col in COL_LAVAGEM:
        if col not in df.columns:
            df[col] = None
    for c in ["Chegada_Lavagem", "Inicio_Lavagem", "Fim_Lavagem", "Previsao_Termino"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def carregar_alertas():
    df = pd.DataFrame(aba_alertas.get_all_records())
    for col in COL_ALERTAS:
        if col not in df.columns:
            df[col] = None
    df["Data_Hora"] = pd.to_datetime(df["Data_Hora"], errors="coerce")
    df["Urgencia"] = df["Urgencia"].fillna("🟢 Pode esperar")
    df["Status"] = df["Status"].fillna("Aberto")
    df["Responsavel"] = df["Responsavel"].fillna("")
    return df
# ======================================================
# FUNÇÃO PARA CRIAR LOTE NA LAVAGEM
# ======================================================
def criar_lote_lavagem(df_setor, qtd_pretas, qtd_azuis):
    agora = datetime.now()
    id_lote = novo_id("LOT")

    aba_lavagem.append_row([
        id_lote,
        agora.strftime("%Y-%m-%d %H:%M:%S"),  # Chegada_Lavagem
        qtd_pretas,                           # Qtd_Pretas_Entrada
        qtd_azuis,                            # Qtd_Azuis_Entrada
        0,                                    # Qtd_Pretas_Lavadas
        0,                                    # Qtd_Azuis_Lavadas
        0,                                    # Diferenca
        "Em Lavagem",
        "",                                   # Previsao_Termino
        "",                                   # Inicio_Lavagem
        "",                                   # Fim_Lavagem
        ""                                    # Turno
    ])



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
            setor_url,
            pretas,
            azuis,
            skates,
            carrinhos,
            "Aberto",
            ""
        ])
        st.success("✅ Alerta enviado")

# ======================================================
# ABA 2 — EXPEDIÇÃO (POR SETOR) - VERSÃO PILOTO 
# ======================================================
with tabs[1]:
    st.subheader("🚚 Gestão de Coletas por Setor")

    df = carregar_alertas()
    # Filtra apenas o que não foi "Coletado" ainda
    ativos = df[df["Status"].isin(STATUS_ATIVOS)].copy()

    if ativos.empty:
        st.info("Nenhum alerta pendente. Bom trabalho!")
    else:
        # Cálculo de tempo e pesos
        ativos["Tempo_Aberto"] = (datetime.now() - ativos["Data_Hora"]).dt.total_seconds().fillna(0) / 60
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

            # Cabeçalho do Card com cor baseada na urgência máxima
            cor_card = "🔴" if s['Peso_Max'] == 3 else "🟡" if s['Peso_Max'] == 2 else "🟢"
            
            with st.expander(f"{cor_card} {setor} | Espera: {int(s['Tempo_Max'])} min | {int(s['Qtde'])} chamados"):
                st.table(df_setor[["Urgencia", "Qtd_Pretas", "Qtd_Azuis", "Status", "Data_Hora"]])

                with st.form(f"coleta_{setor}"):
                    cartao = st.text_input("Cartão ponto do transportador", max_chars=10)
                    
                    # --- LÓGICA DE COLETA PARCIAL VS TOTAL ---
                    tipo_coleta = st.radio(
                        "Situação da coleta no setor:",
                        ["Total (Limpar chamados)", "Parcial (Manter chamados ativos)"],
                        index=0,
                        horizontal=True,
                        help="Total: O setor ficou limpo. Parcial: Ainda ficaram caixas lá para uma próxima viagem."
                    )
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        qtd_pretas = st.number_input("Qtd. Pretas coletadas agora", min_value=0, step=1, key=f"p_{setor}")
                    with c2:
                        qtd_azuis = st.number_input("Qtd. Azuis coletadas agora", min_value=0, step=1, key=f"a_{setor}")

                    confirmar = st.form_submit_button("✔️ Confirmar e Enviar para Lavagem")

                if confirmar:
                    if not cartao.isdigit():
                        st.error("Por favor, informe um cartão ponto válido (apenas números).")
                    elif qtd_pretas == 0 and qtd_azuis == 0:
                        st.warning("Informe a quantidade de caixas que está levando para a lavagem.")
                    else:
                        with st.spinner("Sincronizando com a planilha..."):
                            # 1. Define o novo status
                            novo_status = "Coletado" if "Total" in tipo_coleta else "Em Coleta"
                            
                            # 2. Atualiza os alertas no Google Sheets
                            for id_alerta in df_setor["ID_Alerta"]:
                                atualizar_alerta(id_alerta, novo_status, cartao)

                            # 3. Cria o lote na lavagem (sempre cria, pois a carga saiu do setor)
                            criar_lote_lavagem(df_setor, qtd_pretas, qtd_azuis)

                            st.success(f"✅ Coleta {novo_status} registrada! Lote enviado para lavagem.")
                            st.rerun()
# ======================================================
# ABA 3 — LAVAGEM
# ======================================================
with tabs[2]:
    st.subheader("🧼 Lavagem de Caixas")

    # Carrega todos os lotes da aba db_lavagem
    df_lav = carregar_lavagem()

    # ---------- 1) VISÃO GERAL: TOTAIS PENDENTES ----------
    total_entrada_pretas = df_lav["Qtd_Pretas_Entrada"].fillna(0).astype(int).sum()
    total_entrada_azuis  = df_lav["Qtd_Azuis_Entrada"].fillna(0).astype(int).sum()

    total_lavadas_pretas = df_lav["Qtd_Pretas_Lavadas"].fillna(0).astype(int).sum()
    total_lavadas_azuis  = df_lav["Qtd_Azuis_Lavadas"].fillna(0).astype(int).sum()

    pend_pretas = total_entrada_pretas - total_lavadas_pretas
    pend_azuis  = total_entrada_azuis  - total_lavadas_azuis

    c1, c2 = st.columns(2)
    c1.metric("Caixas pretas pendentes de lavagem", pend_pretas)
    c2.metric("Caixas azuis pendentes de lavagem", pend_azuis)

    st.markdown("---")

    # ---------- 2) LOTES EM LAVAGEM ----------
    em_lavagem = df_lav[df_lav["Status"] == "Em Lavagem"].copy()

    if em_lavagem.empty:
        st.info("Nenhum lote em lavagem no momento.")
    else:
        st.write("Lotes em lavagem:")
        st.table(
            em_lavagem[
                [
                    "ID_Lote",
                    "Chegada_Lavagem",
                    "Qtd_Pretas_Entrada",
                    "Qtd_Azuis_Entrada",
                    "Status",
                    "Turno",
                ]
            ]
        )

    st.markdown("---")
       # ---------- 3) FECHAR LOTES (informar caixas lavadas) ----------
    st.subheader("Finalizar lote de lavagem")

    df_lav = carregar_lavagem()
    em_lavagem = df_lav[df_lav["Status"] == "Em Lavagem"].copy()

    if em_lavagem.empty:
        st.info("Nenhum lote em lavagem para finalizar.")
    else:
        for _, row in em_lavagem.iterrows():
            with st.expander(f"🧺 Lote {row['ID_Lote']} | Turno: {row['Turno']}"):
                ent_pretas = int(row["Qtd_Pretas_Entrada"] or 0)
                ent_azuis  = int(row["Qtd_Azuis_Entrada"] or 0)

                st.write(f"Entrada: {ent_pretas} pretas, {ent_azuis} azuis")

                with st.form(f"fechar_{row['ID_Lote']}"):
                    p = st.number_input(
                        "Quantidade de caixas PRETAS lavadas",
                        min_value=0, step=1, key=f"p_{row['ID_Lote']}"
                    )
                    a = st.number_input(
                        "Quantidade de caixas AZUIS lavadas",
                        min_value=0, step=1, key=f"a_{row['ID_Lote']}"
                    )
                    fechar = st.form_submit_button("✔️ Fechar lote")

                if fechar:
                    cell = aba_lavagem.find(row["ID_Lote"])
                    r = cell.row

                    p_int = int(p)
                    a_int = int(a)
                    entrada_total = ent_pretas + ent_azuis
                    lavadas_total = p_int + a_int
                    diferenca = lavadas_total - entrada_total

                    fim_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    prev_str = "" if pd.isna(row["Previsao_Termino"]) else str(row["Previsao_Termino"])

                    # todos os valores convertidos para tipos simples (int/str)
                    valores = [
                        p_int,
                        a_int,
                        int(diferenca),
                        "Finalizado",
                        prev_str,
                        fim_str,
                    ]

                    aba_lavagem.update(f"E{r}:J{r}", [valores])

                    st.success(f"✅ Lote {row['ID_Lote']} finalizado!")
                    st.rerun()




# ======================================================
# ABA 4 — GESTÃO
# ======================================================
with tabs[3]:
    st.subheader("📊 Indicadores")

    df_lav = carregar_lavagem()

    # garante tipos numéricos
    for c in ["Qtd_Pretas_Entrada", "Qtd_Azuis_Entrada",
              "Qtd_Pretas_Lavadas", "Qtd_Azuis_Lavadas"]:
        df_lav[c] = df_lav[c].fillna(0).astype(int)

    final = df_lav[df_lav["Status"] == "Finalizado"].copy()

    # evita erro se ainda não houver lotes finalizados
    if final.empty:
        st.info("Ainda não há lotes finalizados para cálculo de indicadores.")
    else:
        final["Tempo"] = (
            final["Fim_Lavagem"] - final["Inicio_Lavagem"]
        ).dt.total_seconds() / 3600

        backlog = (
            df_lav["Qtd_Pretas_Entrada"].sum() + df_lav["Qtd_Azuis_Entrada"].sum()
        ) - (
            df_lav["Qtd_Pretas_Lavadas"].sum() + df_lav["Qtd_Azuis_Lavadas"].sum()
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Backlog real (caixas sujas)", int(backlog))
        c2.metric("Tempo médio de lavagem (h)", round(final["Tempo"].mean(), 2))

        total_ent = final["Qtd_Pretas_Entrada"].sum() + final["Qtd_Azuis_Entrada"].sum()
        total_lav = final["Qtd_Pretas_Lavadas"].sum() + final["Qtd_Azuis_Lavadas"].sum()
        eficiencia = (total_lav / max(1, total_ent)) * 100

        c3.metric("Eficiência (%)", round(eficiencia, 1))

        # gráfico por turno
        por_turno = final.groupby("Turno")[["Qtd_Pretas_Lavadas", "Qtd_Azuis_Lavadas"]].sum()
        st.bar_chart(por_turno)

# ======================================================
# ABA 5 — INVENTÁRIO
# ======================================================
with tabs[4]:
    st.subheader("📋 Inventário por Exclusão")

    TOTAL = 1000  # total de caixas existentes (ajuste se necessário)

    # calcula automaticamente o que está na lavagem
    df_lav = carregar_lavagem()
    df_lav[["Qtd_Pretas_Entrada", "Qtd_Azuis_Entrada",
            "Qtd_Pretas_Lavadas", "Qtd_Azuis_Lavadas"]] = \
        df_lav[["Qtd_Pretas_Entrada", "Qtd_Azuis_Entrada",
                "Qtd_Pretas_Lavadas", "Qtd_Azuis_Lavadas"]].fillna(0).astype(int)

    na_lavagem = (
        df_lav["Qtd_Pretas_Entrada"].sum() + df_lav["Qtd_Azuis_Entrada"].sum()
        - df_lav["Qtd_Pretas_Lavadas"].sum() - df_lav["Qtd_Azuis_Lavadas"].sum()
    )

    c1, c2 = st.columns(2)
    with c1:
        prontas = st.number_input("Prontas (em estoque limpo)", min_value=0, step=1)
        separacao = st.number_input("Em separação", min_value=0, step=1)
    with c2:
        entrega = st.number_input("Aguardando entrega", min_value=0, step=1)
        st.number_input("Na lavagem (calculado)", value=int(na_lavagem), disabled=True)

    internas = prontas + separacao + entrega + int(na_lavagem)
    campo = TOTAL - internas
    dispersao = round((campo / TOTAL) * 100, 1)

    st.metric("Em circulação (fora expedição/lavagem/estoque)", campo, f"{dispersao}%")





























