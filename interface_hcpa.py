import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime

# ======================================================
# CONFIGURAÇÃO
# ======================================================
st.set_page_config(page_title="Logística de Caixas HCPA", layout="wide")

NOME_PLANILHA = "Gestao_Caixas_HCPA"

# Ajuste aqui se na sua planilha o nome real for diferente.
ABA_ALERTAS = "db_alertas"   # se a aba real for db_alerta, troque aqui
ABA_COLETAS = "db_coletas"
ABA_LAVAGEM = "db_lavagem"
ABA_SETORES = "db_setores"
ABA_HISTORICO = "db_historico"

COL_ALERTAS = [
    "ID_Alerta", "Data_Hora", "ID_Setor", "Urgencia",
    "Setor_Nome", "Qtd_Pretas", "Qtd_Azuis",
    "Skates", "Carrinhos", "Status", "Responsavel"
]

COL_COLETAS = [
    "ID_Coleta", "Data_Hora", "ID_Setor", "Setor_Nome",
    "ID_Alertas", "Transportador", "Qtd_Pretas_Coletadas",
    "Qtd_Azuis_Coletadas", "Tipo_Coleta", "Local_Limpo", "Veiculo"
]

COL_SETORES = [
    "ID_Setor", "Nome_Setor", "Bloco",
    "Andar", "Distancia_Metros", "Prioridade"
]

COL_LAVAGEM = [
    "ID_Lote", "Chegada_Lavagem", "ID_Coleta",
    "Qtd_Pretas_Entrada", "Qtd_Azuis_Entrada",
    "Qtd_Pretas_Lavadas", "Qtd_Azuis_Lavadas",
    "Diferenca", "Status", "Previsao_Termino",
    "Inicio_Lavagem", "Fim_Lavagem", "Turno"
]

COL_HISTORICO = [
    "ID_Alerta", "Data_Hora", "ID_Setor",
    "Setor_Nome", "Qtd_Pretas", "Qtd_Azuis",
    "Skates", "Carrinhos", "Status", "Responsavel"
]

STATUS_ATIVOS = ["Aberto", "Parcial"]

MAPA_URGENCIA = {
    "🔴 Está atrapalhando": 3,
    "🟡 Ideal coletar hoje": 2,
    "🟢 Pode esperar": 1,
}

# ======================================================
# CONEXÃO GOOGLE SHEETS
# ======================================================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope,
)

client = gspread.authorize(creds)
planilha = client.open(NOME_PLANILHA)


# ======================================================
# FUNÇÕES AUXILIARES DE PLANILHA
# ======================================================
def get_or_create_worksheet(nome_aba: str, colunas: list[str]):
    try:
        ws = planilha.worksheet(nome_aba)
    except gspread.WorksheetNotFound:
        ws = planilha.add_worksheet(title=nome_aba, rows=1000, cols=max(20, len(colunas) + 5))
        ws.append_row(colunas)
    else:
        valores = ws.get_all_values()
        if not valores:
            ws.append_row(colunas)
    return ws


aba_alertas = get_or_create_worksheet(ABA_ALERTAS, COL_ALERTAS)
aba_coletas = get_or_create_worksheet(ABA_COLETAS, COL_COLETAS)
aba_lavagem = get_or_create_worksheet(ABA_LAVAGEM, COL_LAVAGEM)


# ======================================================
# FUNÇÕES AUXILIARES
# ======================================================
def novo_id(prefixo):
    return f"{prefixo}{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def garantir_colunas(df: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in colunas:
        if col not in df.columns:
            df[col] = None
    return df[colunas]


def carregar_alertas():
    df = pd.DataFrame(aba_alertas.get_all_records())
    df = garantir_colunas(df, COL_ALERTAS)
    df["Data_Hora"] = pd.to_datetime(df["Data_Hora"], errors="coerce")
    df["Urgencia"] = df["Urgencia"].fillna("🟢 Pode esperar")
    df["Status"] = df["Status"].fillna("Aberto")
    df["Responsavel"] = df["Responsavel"].fillna("")
    return df


def salvar_alertas(df: pd.DataFrame):
    df = garantir_colunas(df, COL_ALERTAS).copy()
    df["Data_Hora"] = pd.to_datetime(df["Data_Hora"], errors="coerce")
    df["Data_Hora"] = df["Data_Hora"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df = df.fillna("")
    valores = [COL_ALERTAS] + df.astype(str).values.tolist()
    aba_alertas.clear()
    aba_alertas.update(f"A1:K{len(valores)}", valores)



def carregar_coletas():
    df = pd.DataFrame(aba_coletas.get_all_records())
    df = garantir_colunas(df, COL_COLETAS)
    df["Data_Hora"] = pd.to_datetime(df["Data_Hora"], errors="coerce")
    return df



def carregar_lavagem():
    df = pd.DataFrame(aba_lavagem.get_all_records())
    df = garantir_colunas(df, COL_LAVAGEM)
    for c in ["Chegada_Lavagem", "Inicio_Lavagem", "Fim_Lavagem", "Previsao_Termino"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df



def classificar_veiculo(qtd_pretas: int, qtd_azuis: int) -> str:
    total = int(qtd_pretas) + int(qtd_azuis)
    if total <= 10:
        return "Pequeno"
    if total <= 30:
        return "Médio"
    return "Grande"



def registrar_coleta(id_setor, setor_nome, ids_alerta, cartao, qtd_pretas, qtd_azuis, tipo_coleta):
    tipo_limpo = "Sim" if tipo_coleta == "Total" else "Não"
    veiculo = classificar_veiculo(qtd_pretas, qtd_azuis)

    aba_coletas.append_row([
        novo_id("COL"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        id_setor,
        setor_nome,
        "|".join([str(x) for x in ids_alerta]),
        cartao,
        int(qtd_pretas),
        int(qtd_azuis),
        tipo_coleta,
        tipo_limpo,
        veiculo,
    ])



def criar_lote_lavagem(id_coleta, qtd_pretas, qtd_azuis):
    agora = datetime.now()
    id_lote = novo_id("LOT")

    aba_lavagem.append_row([
        id_lote,
        agora.strftime("%Y-%m-%d %H:%M:%S"),
        id_coleta,
        int(qtd_pretas),
        int(qtd_azuis),
        0,
        0,
        0,
        "Em Lavagem",
        "",
        "",
        "",
        "",
    ])



def atualizar_status_alertas(ids_alerta, novo_status, responsavel):
    df = carregar_alertas()
    ids_alerta = [str(x) for x in ids_alerta]
    mask = df["ID_Alerta"].astype(str).isin(ids_alerta)

    df.loc[mask, "Status"] = novo_status
    df.loc[mask, "Responsavel"] = str(responsavel)

    salvar_alertas(df)



def registrar_coleta_e_lavagem(id_setor, setor_nome, ids_alerta, cartao, qtd_pretas, qtd_azuis, tipo_coleta):
    id_coleta = novo_id("COL")
    tipo_limpo = "Sim" if tipo_coleta == "Total" else "Não"
    veiculo = classificar_veiculo(qtd_pretas, qtd_azuis)

    aba_coletas.append_row([
        id_coleta,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        id_setor,
        setor_nome,
        "|".join([str(x) for x in ids_alerta]),
        cartao,
        int(qtd_pretas),
        int(qtd_azuis),
        tipo_coleta,
        tipo_limpo,
        veiculo,
    ])

    criar_lote_lavagem(id_coleta, qtd_pretas, qtd_azuis)
    novo_status = "Fechado" if tipo_coleta == "Total" else "Parcial"
    atualizar_status_alertas(ids_alerta, novo_status, cartao)
    return id_coleta, veiculo, novo_status


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
    st.caption("O alerta sinaliza demanda logística. A coleta real fica registrada separadamente.")

    with st.form("setor"):
        urgencia = st.radio("Impacto no trabalho", list(MAPA_URGENCIA.keys()))

        c1, c2 = st.columns(2)
        with c1:
            pretas = st.radio("Caixas Pretas", ["0", "≤5", "≤10", "mais que 10"])
            skates = st.number_input("Skates disponíveis", min_value=0, step=1)
        with c2:
            azuis = st.radio("Caixas Azuis", ["0", "≤30", "mais que 30"])
            carrinhos = st.number_input("Carrinhos disponíveis", min_value=0, step=1)

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
            int(skates),
            int(carrinhos),
            "Aberto",
            "",
        ])
        st.success("✅ Alerta enviado")

# ======================================================
# ABA 2 — EXPEDIÇÃO
# ======================================================
with tabs[1]:
    st.subheader("🚚 Gestão de Coletas por Setor")

    df = carregar_alertas()
    ativos = df[df["Status"].isin(STATUS_ATIVOS)].copy()

    if ativos.empty:
        st.info("Nenhum alerta pendente. Bom trabalho!")
    else:
        ativos["Tempo_Aberto"] = (datetime.now() - ativos["Data_Hora"]).dt.total_seconds().fillna(0) / 60
        ativos["Peso"] = ativos["Urgencia"].map(MAPA_URGENCIA).fillna(1)

        resumo = (
            ativos.groupby("ID_Setor")
            .agg(
                Qtde=("ID_Alerta", "count"),
                Tempo_Max=("Tempo_Aberto", "max"),
                Peso_Max=("Peso", "max"),
                Setor_Nome=("Setor_Nome", "last"),
            )
            .reset_index()
            .sort_values(by=["Peso_Max", "Tempo_Max"], ascending=False)
        )

        for _, s in resumo.iterrows():
            setor = s["ID_Setor"]
            df_setor = ativos[ativos["ID_Setor"] == setor].copy()

            cor_card = "🔴" if s["Peso_Max"] == 3 else "🟡" if s["Peso_Max"] == 2 else "🟢"
            with st.expander(f"{cor_card} {setor} | Espera: {int(s['Tempo_Max'])} min | {int(s['Qtde'])} chamados"):
                st.table(df_setor[["Urgencia", "Qtd_Pretas", "Qtd_Azuis", "Status", "Data_Hora"]])

                with st.form(f"coleta_{setor}"):
                    cartao = st.text_input("Cartão ponto do transportador", max_chars=10)
                    tipo_coleta = st.radio(
                        "Situação da coleta no setor:",
                        ["Total", "Parcial"],
                        horizontal=True,
                        help="Total: o setor ficou limpo. Parcial: ainda precisa nova viagem.",
                    )

                    c1, c2 = st.columns(2)
                    with c1:
                        qtd_pretas = st.number_input(
                            "Qtd. Pretas coletadas agora",
                            min_value=0,
                            step=1,
                            key=f"p_{setor}",
                        )
                    with c2:
                        qtd_azuis = st.number_input(
                            "Qtd. Azuis coletadas agora",
                            min_value=0,
                            step=1,
                            key=f"a_{setor}",
                        )

                    confirmar = st.form_submit_button("✔️ Confirmar coleta e enviar para lavagem")

                if confirmar:
                    if not cartao.isdigit():
                        st.error("Informe um cartão ponto válido, somente números.")
                    elif int(qtd_pretas) == 0 and int(qtd_azuis) == 0:
                        st.warning("Informe a quantidade de caixas que está indo para a lavagem.")
                    else:
                        with st.spinner("Sincronizando com a planilha..."):
                            ids_alerta = df_setor["ID_Alerta"].tolist()
                            setor_nome = df_setor["Setor_Nome"].iloc[0] if not df_setor.empty else str(setor)
                            id_coleta, veiculo, novo_status = registrar_coleta_e_lavagem(
                                setor,
                                setor_nome,
                                ids_alerta,
                                cartao,
                                int(qtd_pretas),
                                int(qtd_azuis),
                                tipo_coleta,
                            )
                            st.success(
                                f"✅ Coleta registrada. Status do ponto: {novo_status}. "
                                f"Veículo sugerido: {veiculo}. ID da coleta: {id_coleta}"
                            )
                            st.rerun()

# ======================================================
# ABA 3 — LAVAGEM
# ======================================================
with tabs[2]:
    st.subheader("🧼 Lavagem de Caixas")

    df_lav = carregar_lavagem()

    for c in ["Qtd_Pretas_Entrada", "Qtd_Azuis_Entrada", "Qtd_Pretas_Lavadas", "Qtd_Azuis_Lavadas"]:
        df_lav[c] = pd.to_numeric(df_lav[c], errors="coerce").fillna(0).astype(int)

    total_entrada_pretas = df_lav["Qtd_Pretas_Entrada"].sum()
    total_entrada_azuis = df_lav["Qtd_Azuis_Entrada"].sum()
    total_lavadas_pretas = df_lav["Qtd_Pretas_Lavadas"].sum()
    total_lavadas_azuis = df_lav["Qtd_Azuis_Lavadas"].sum()

    pend_pretas = total_entrada_pretas - total_lavadas_pretas
    pend_azuis = total_entrada_azuis - total_lavadas_azuis

    c1, c2 = st.columns(2)
    c1.metric("Caixas pretas pendentes de lavagem", int(pend_pretas))
    c2.metric("Caixas azuis pendentes de lavagem", int(pend_azuis))

    st.markdown("---")

    em_lavagem = df_lav[df_lav["Status"] == "Em Lavagem"].copy()

    if em_lavagem.empty:
        st.info("Nenhum lote em lavagem no momento.")
    else:
        st.write("Lotes em lavagem:")
        st.table(
            em_lavagem[[
                "ID_Lote", "Chegada_Lavagem", "ID_Coleta",
                "Qtd_Pretas_Entrada", "Qtd_Azuis_Entrada", "Status", "Turno"
            ]]
        )

    st.markdown("---")
    st.subheader("Finalizar lote de lavagem")

    if em_lavagem.empty:
        st.info("Nenhum lote em lavagem para finalizar.")
    else:
        for _, row in em_lavagem.iterrows():
            with st.expander(f"🧺 Lote {row['ID_Lote']} | Turno: {row['Turno']}"):
                ent_pretas = int(row["Qtd_Pretas_Entrada"] or 0)
                ent_azuis = int(row["Qtd_Azuis_Entrada"] or 0)
                st.write(f"Entrada: {ent_pretas} pretas, {ent_azuis} azuis")

                with st.form(f"fechar_{row['ID_Lote']}"):
                    p = st.number_input(
                        "Quantidade de caixas PRETAS lavadas",
                        min_value=0, step=1, key=f"lav_p_{row['ID_Lote']}"
                    )
                    a = st.number_input(
                        "Quantidade de caixas AZUIS lavadas",
                        min_value=0, step=1, key=f"lav_a_{row['ID_Lote']}"
                    )
                    fechar = st.form_submit_button("✔️ Fechar lote")

                if fechar:
                    cell = aba_lavagem.find(str(row["ID_Lote"]))
                    r = cell.row

                    p_int = int(p)
                    a_int = int(a)
                    entrada_total = ent_pretas + ent_azuis
                    lavadas_total = p_int + a_int
                    diferenca = lavadas_total - entrada_total
                    fim_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    prev_str = "" if pd.isna(row["Previsao_Termino"]) else str(row["Previsao_Termino"])

                    valores = [
                        p_int,
                        a_int,
                        int(diferenca),
                        "Finalizado",
                        prev_str,
                        fim_str,
                    ]

                    # E:F:G:H:I:J = lavadas, diferença, status, previsão, início, fim
                    # Mantive o layout o mais próximo possível do seu código original.
                    aba_lavagem.update(f"F{r}:K{r}", [valores])

                    st.success(f"✅ Lote {row['ID_Lote']} finalizado!")
                    st.rerun()

# ======================================================
# ABA 4 — GESTÃO
# ======================================================
with tabs[3]:
    st.subheader("📊 Indicadores")

    df_lav = carregar_lavagem()
    df_col = carregar_coletas()
    df_alert = carregar_alertas()

    for c in ["Qtd_Pretas_Entrada", "Qtd_Azuis_Entrada", "Qtd_Pretas_Lavadas", "Qtd_Azuis_Lavadas"]:
        df_lav[c] = pd.to_numeric(df_lav[c], errors="coerce").fillna(0).astype(int)

    backlog = (
        df_lav["Qtd_Pretas_Entrada"].sum() + df_lav["Qtd_Azuis_Entrada"].sum()
        - df_lav["Qtd_Pretas_Lavadas"].sum() - df_lav["Qtd_Azuis_Lavadas"].sum()
    )

    total_abertos = int(df_alert[df_alert["Status"].isin(STATUS_ATIVOS)].shape[0])
    total_pontos_abertos = int(df_alert[df_alert["Status"].isin(STATUS_ATIVOS)]["ID_Setor"].nunique())

    c1, c2, c3 = st.columns(3)
    c1.metric("Backlog real na lavagem", int(backlog))
    c2.metric("Alertas operacionais abertos", total_abertos)
    c3.metric("Pontos com demanda ativa", total_pontos_abertos)

    st.markdown("---")

    if df_col.empty:
        st.info("Ainda não há coletas registradas.")
    else:
        for c in ["Qtd_Pretas_Coletadas", "Qtd_Azuis_Coletadas"]:
            df_col[c] = pd.to_numeric(df_col[c], errors="coerce").fillna(0).astype(int)

        prod = (
            df_col.groupby("Transportador")[["Qtd_Pretas_Coletadas", "Qtd_Azuis_Coletadas"]]
            .sum()
            .sort_values(by=["Qtd_Pretas_Coletadas", "Qtd_Azuis_Coletadas"], ascending=False)
        )

        st.write("Produção aproximada por colaborador")
        st.dataframe(prod, use_container_width=True)

        por_veiculo = df_col.groupby("Veiculo")[["Qtd_Pretas_Coletadas", "Qtd_Azuis_Coletadas"]].sum()
        st.write("Distribuição por tipo de veículo")
        st.bar_chart(por_veiculo)

# ======================================================
# ABA 5 — INVENTÁRIO
# ======================================================
with tabs[4]:
    st.subheader("📋 Inventário por Exclusão")

    TOTAL = 1000

    df_lav = carregar_lavagem()
    for c in ["Qtd_Pretas_Entrada", "Qtd_Azuis_Entrada", "Qtd_Pretas_Lavadas", "Qtd_Azuis_Lavadas"]:
        df_lav[c] = pd.to_numeric(df_lav[c], errors="coerce").fillna(0).astype(int)

    na_lavagem = (
        df_lav["Qtd_Pretas_Entrada"].sum() + df_lav["Qtd_Azuis_Entrada"].sum()
        - df_lav["Qtd_Pretas_Lavadas"].sum() - df_lav["Qtd_Azuis_Lavadas"].sum()
    )

    df_alert = carregar_alertas()
    pontos_ativos = df_alert[df_alert["Status"].isin(STATUS_ATIVOS)]["ID_Setor"].nunique()

    c1, c2 = st.columns(2)
    with c1:
        prontas = st.number_input("Prontas (em estoque limpo)", min_value=0, step=1)
        separacao = st.number_input("Em separação", min_value=0, step=1)
    with c2:
        entrega = st.number_input("Aguardando entrega", min_value=0, step=1)
        st.number_input("Na lavagem (calculado)", value=int(na_lavagem), disabled=True)

    internas = int(prontas) + int(separacao) + int(entrega) + int(na_lavagem)
    campo = TOTAL - internas
    dispersao = round((campo / TOTAL) * 100, 1) if TOTAL else 0

    st.metric("Em circulação (fora expedição/lavagem/estoque)", int(campo), f"{dispersao}%")
    st.caption(f"Pontos de coleta com demanda ativa agora: {int(pontos_ativos)}")
