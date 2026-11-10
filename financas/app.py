"""BI de gastos do cartão Nubank — rode com:  streamlit run app.py"""
from __future__ import annotations

import hmac
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from bi import analise, db, pluggy
from bi.categorias import OUTROS, PAGAMENTO, REGRAS, categorizar
from bi.importador import ler_arquivo

st.set_page_config(page_title="Meu BI Financeiro", page_icon="💳", layout="wide")

# Paleta categórica validada (ordem fixa; cor segue a categoria, nunca o ranking)
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
CINZA = "#9a9890"
MAX_FATIAS = 7


# ---------------------------------------------------------------- login
def exigir_senha() -> None:
    senha = os.environ.get("APP_PASSWORD")
    if not senha or st.session_state.get("ok"):
        return
    st.title("🔒 Meu BI Financeiro")
    digitada = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if hmac.compare_digest(digitada.encode(), senha.encode()):
            st.session_state.ok = True
            st.rerun()
        st.error("Senha incorreta.")
    st.stop()


exigir_senha()


def brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Cartão")
    limite = st.number_input("Limite total (R$)", min_value=0.0, step=100.0,
                             value=float(db.get_config("limite", 5000)))
    fechamento = st.number_input("Dia de fechamento da fatura", 0, 28,
                                 int(db.get_config("fechamento", 0)),
                                 help="Veja no app do Nubank. Use 0 para agrupar pelo mês da compra.")
    if st.button("Salvar configurações"):
        db.set_config("limite", limite)
        db.set_config("fechamento", fechamento)
        st.success("Salvo.")

    st.header("📥 Dados")
    arquivos = st.file_uploader("Importar fatura/extrato Nubank (CSV ou OFX)",
                                type=["csv", "ofx"], accept_multiple_files=True)
    if arquivos and st.button("Importar arquivos"):
        total = 0
        for a in arquivos:
            try:
                df_novo = ler_arquivo(a.name, a.getvalue())
                df_novo["categoria"] = df_novo["descricao"].map(categorizar)
                total += db.salvar(df_novo)
            except Exception as e:  # noqa: BLE001
                st.error(f"{a.name}: {e}")
        st.success(f"{total} transações novas importadas.")
        st.rerun()

    if pluggy.configurado():
        if st.button("🔄 Sincronizar com Nubank (Open Finance)"):
            with st.spinner("Buscando dados na Pluggy..."):
                try:
                    df_p, info = pluggy.sincronizar()
                    df_p["categoria"] = [categorizar(d, c) for d, c in
                                         zip(df_p["descricao"], df_p["categoria_banco"])]
                    n = db.salvar(df_p)
                    if info.get("limite"):
                        db.set_config("limite", info["limite"])
                    if info.get("disponivel") is not None:
                        db.set_config("disponivel", info["disponivel"])
                    st.success(f"{n} transações novas.")
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(f"Falha na sincronização: {e}")
    else:
        st.caption("Conexão automática: configure as variáveis PLUGGY_* (veja o README).")

    with st.expander("Manutenção"):
        if st.button("Reaplicar regras de categoria"):
            db.recategorizar(categorizar)
            st.rerun()
        if st.button("Carregar dados de exemplo"):
            caminho = os.path.join(os.path.dirname(__file__), "dados_exemplo", "fatura_exemplo.csv")
            with open(caminho, "rb") as f:
                df_ex = ler_arquivo("exemplo.csv", f.read())
            df_ex["categoria"] = df_ex["descricao"].map(categorizar)
            df_ex["origem"] = "exemplo"
            db.salvar(df_ex)
            st.rerun()
        if st.button("⚠️ Apagar todas as transações"):
            db.apagar_tudo()
            st.rerun()

# ---------------------------------------------------------------- dados
df = db.carregar()
st.title("💳 Meu BI Financeiro")

if df.empty:
    st.info("Nenhuma transação ainda. Importe o CSV da fatura do Nubank na barra lateral "
            "ou use **Manutenção → Carregar dados de exemplo** para ver o painel funcionando.")
    st.stop()

df["mes_fatura"] = analise.mes_fatura(df["data"], int(fechamento))
pagamentos = df["categoria"] == PAGAMENTO
df_tudo, df = df, df[~pagamentos]  # pagamentos da fatura anterior não entram nos gastos
meses = sorted(df["mes_fatura"].unique(), reverse=True)
mes = st.selectbox("Fatura", meses, format_func=lambda m: pd.Period(m).strftime("%m/%Y"))
df_mes = df[df["mes_fatura"] == mes]
gastos_mes = df_mes[df_mes["valor"] > 0]

# cor fixa por categoria: as mais relevantes do histórico ganham slots; resto vira "Outros"
ranking = df[df["valor"] > 0].groupby("categoria")["valor"].sum().sort_values(ascending=False)
principais = [c for c in ranking.index if c != OUTROS][:MAX_FATIAS - 1]
CORES = {c: PALETA[i] for i, c in enumerate(principais)} | {OUTROS: CINZA}


def agrupar(cat: str) -> str:
    return cat if cat in principais else OUTROS


fatura = df_mes["valor"].sum()
disponivel_api = db.get_config("disponivel")
usado = limite - float(disponivel_api) if disponivel_api else max(fatura, 0)
rec = analise.recorrentes(df)
rec_mensal = rec["Valor médio"].sum() if not rec.empty else 0

# ---------------------------------------------------------------- KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Valor da fatura", brl(fatura), f"{len(gastos_mes)} compras", delta_color="off", delta_arrow="off")
k2.metric("Limite usado", f"{usado / limite:.0%}" if limite else "—", brl(usado), delta_color="off", delta_arrow="off")
k3.metric("Limite disponível", brl(max(limite - usado, 0)))
k4.metric("Recorrentes / mês", brl(rec_mensal), f"{len(rec)} cobranças", delta_color="off", delta_arrow="off")

aba_painel, aba_rec, aba_tx = st.tabs(["📊 Painel", "🔁 Assinaturas e recorrentes", "🧾 Transações"])

# ---------------------------------------------------------------- painel
with aba_painel:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Gastos por categoria")
        por_cat = (gastos_mes.assign(categoria=gastos_mes["categoria"].map(agrupar))
                   .groupby("categoria")["valor"].sum().sort_values(ascending=False).reset_index())
        fig = px.pie(por_cat, names="categoria", values="valor", hole=0.55,
                     color="categoria", color_discrete_map=CORES)
        fig.update_traces(textinfo="percent", sort=False,
                          marker=dict(line=dict(color="rgba(0,0,0,0)", width=2)),
                          hovertemplate="%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>")
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title_text="")
        st.plotly_chart(fig, width="stretch")
    with c2:
        st.subheader("Uso do limite")
        fig = go.Figure(go.Pie(labels=["Usado", "Disponível"],
                               values=[max(usado, 0), max(limite - usado, 0)], hole=0.55, sort=False,
                               marker=dict(colors=[PALETA[0], "#d9d7cf"]), textinfo="percent",
                               hovertemplate="%{label}<br>R$ %{value:,.2f}<extra></extra>"))
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10),
                          annotations=[dict(text=brl(limite), showarrow=False, font_size=16)])
        st.plotly_chart(fig, width="stretch")

    st.subheader("Histórico de faturas")
    hist = (df[df["valor"] > 0].assign(categoria=lambda d: d["categoria"].map(agrupar))
            .groupby(["mes_fatura", "categoria"])["valor"].sum().reset_index())
    fig = px.bar(hist, x="mes_fatura", y="valor", color="categoria", color_discrete_map=CORES,
                 category_orders={"categoria": principais + [OUTROS]},
                 labels={"mes_fatura": "", "valor": "R$", "categoria": ""})
    fig.update_traces(marker_line_width=0, hovertemplate="%{fullData.name}<br>R$ %{y:,.2f}<extra></extra>")
    fig.update_layout(bargap=0.35, margin=dict(t=10, b=10), hovermode="x unified")
    st.plotly_chart(fig, width="stretch")

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Onde mais gastei")
        top = (gastos_mes.assign(estab=gastos_mes["descricao"].map(analise.chave_estabelecimento))
               .groupby("estab")["valor"].agg(["sum", "count"]).sort_values("sum", ascending=False).head(10))
        top.columns = ["Total", "Compras"]
        top.index.name = "Estabelecimento"
        st.dataframe(top.style.format({"Total": brl}), width="stretch")
    with c4:
        st.subheader("💡 Onde economizar")
        for dica in analise.sugestoes(df_mes, df, rec, limite, usado):
            st.markdown(f"- {dica}")

# ---------------------------------------------------------------- recorrentes
with aba_rec:
    if rec.empty:
        st.info("Nenhuma cobrança recorrente detectada ainda — importe pelo menos 2 meses de fatura.")
    else:
        st.caption("Detectadas por: mesmo estabelecimento cobrado em meses diferentes com valor "
                   "parecido (±15%), ou categoria 'Assinaturas'. Parcelamentos são ignorados.")
        st.dataframe(rec.style.format({"Valor médio": brl, "Custo anual estimado": brl}),
                     width="stretch", hide_index=True)

# ---------------------------------------------------------------- transações
with aba_tx:
    st.caption("Corrija a categoria direto na tabela — a correção fica salva e não é sobrescrita.")
    categorias = sorted(set(REGRAS) | {OUTROS, PAGAMENTO} | set(df_tudo["categoria"].dropna()))
    tabela = df_tudo[df_tudo["mes_fatura"] == mes].sort_values("data", ascending=False)[["id", "data", "descricao", "valor", "parcela", "categoria"]]
    tabela["parcela"] = tabela["parcela"].fillna("")
    editada = st.data_editor(
        tabela, hide_index=True, width="stretch", disabled=["data", "descricao", "valor", "parcela"],
        column_config={
            "id": None,
            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "descricao": "Descrição",
            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
            "parcela": "Parcela",
            "categoria": st.column_config.SelectboxColumn("Categoria", options=categorias),
        },
    )
    mudou = editada[editada["categoria"] != tabela["categoria"]]
    if not mudou.empty:
        for _, l in mudou.iterrows():
            db.definir_categoria(l["id"], l["categoria"])
        st.rerun()
    st.download_button("Baixar CSV deste mês", tabela.drop(columns="id").to_csv(index=False).encode(),
                       f"fatura_{mes}.csv", "text/csv")
