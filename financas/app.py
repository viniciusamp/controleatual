"""BI de gastos do cartão Nubank — rode com:  streamlit run app.py"""
from __future__ import annotations

import hmac
import os
import time
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from bi import analise, db, login_ui, pluggy
from bi.categorias import OUTROS, PAGAMENTO, REGRAS, categorizar
from bi.importador import ler_arquivo



def carregar_env() -> None:
    """Lê financas/.env (para rodar sem Docker). Variáveis já definidas têm prioridade."""
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(caminho):
        return
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, valor = linha.split("=", 1)
                os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


carregar_env()
st.set_page_config(page_title="Meu BI Financeiro", page_icon="💳", layout="wide")

# Paleta categórica validada (ordem fixa; cor segue a categoria, nunca o ranking)
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
CINZA = "#9a9890"
MAX_FATIAS = 7


# ---------------------------------------------------------------- login
MAX_TENTATIVAS, MINUTOS_BLOQUEIO = 5, 15


def exigir_senha() -> None:
    senha = os.environ.get("APP_PASSWORD")
    if not senha or st.session_state.get("ok"):
        return
    st.markdown(login_ui.css(), unsafe_allow_html=True)
    with st.container(key="login_card"):
        st.markdown(login_ui.TOPO, unsafe_allow_html=True)
        bloqueio = db.get_config("login_bloqueado_ate")
        if bloqueio and datetime.now() < datetime.fromisoformat(bloqueio):
            st.error(f"Muitas tentativas erradas. Tente de novo às {datetime.fromisoformat(bloqueio):%H:%M}.")
            st.stop()
        with st.form("login", border=False):
            digitada = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            entrar = st.form_submit_button("Entrar", width="stretch")
        if entrar:
            if hmac.compare_digest(digitada.encode(), senha.encode()):
                db.set_config("login_falhas", 0)
                st.session_state.ok = True
                st.rerun()
            time.sleep(1)
            falhas = int(db.get_config("login_falhas", 0)) + 1
            if falhas >= MAX_TENTATIVAS:
                db.set_config("login_bloqueado_ate",
                              (datetime.now() + timedelta(minutes=MINUTOS_BLOQUEIO)).isoformat())
                falhas = 0
            db.set_config("login_falhas", falhas)
            restam = MAX_TENTATIVAS - falhas if falhas else 0
            st.error("Senha incorreta." + (f" Restam {restam} tentativas." if restam else
                                           f" Acesso bloqueado por {MINUTOS_BLOQUEIO} minutos."))
        st.markdown(login_ui.RODAPE, unsafe_allow_html=True)
    st.stop()


exigir_senha()


def brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- Pluggy
HORAS_AUTO_SYNC = 6


def sincronizar_pluggy() -> int:
    df_p, info = pluggy.sincronizar()
    df_p["categoria"] = [categorizar(d, c) for d, c in zip(df_p["descricao"], df_p["categoria_banco"])]
    n = db.salvar(df_p)
    if info.get("limite"):
        db.set_config("limite", info["limite"])
        db.set_config("disponivel", info["disponivel"])
    if info.get("fechamento"):
        db.set_config("fechamento", pd.Timestamp(info["fechamento"]).day)
    if info.get("vencimento"):
        db.set_config("vencimento", str(pd.Timestamp(info["vencimento"]).date()))
    db.set_config("ultima_sync", datetime.now().isoformat(timespec="minutes"))
    return n


if pluggy.configurado() and "auto_sync" not in st.session_state:
    st.session_state.auto_sync = True
    ultima = db.get_config("ultima_sync")
    if not ultima or datetime.now() - datetime.fromisoformat(ultima) > timedelta(hours=HORAS_AUTO_SYNC):
        with st.spinner("Atualizando dados do Nubank..."):
            try:
                sincronizar_pluggy()
            except Exception as e:  # noqa: BLE001
                st.warning(f"Não consegui atualizar automaticamente: {e}")

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

    if not os.environ.get("APP_PASSWORD"):
        st.warning("Sem senha: defina APP_PASSWORD no arquivo .env.")

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
                    st.toast(f"{sincronizar_pluggy()} transações novas.")
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(f"Falha na sincronização: {e}")
        ultima = db.get_config("ultima_sync")
        if ultima:
            st.caption(f"Última sincronização: {datetime.fromisoformat(ultima):%d/%m %H:%M}")
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

aba_painel, aba_exp, aba_cartao, aba_rec, aba_tx = st.tabs(
    ["📊 Painel", "🔎 Explorar", "💳 Meu cartão", "🔁 Assinaturas", "🧾 Transações"])


def barras(dados: pd.DataFrame, x: str, y: str, horizontal: bool = False, altura: int = 380):
    """Barras de uma série só: uma cor, valor em R$ no hover e no rótulo."""
    dados = dados.assign(_txt=dados[y if not horizontal else x].map(brl))
    fig = px.bar(dados, x=x, y=y, orientation="h" if horizontal else "v", custom_data=["_txt"],
                 text="_txt" if horizontal else None)
    eixo = "%{y}" if horizontal else "%{x}"
    fig.update_traces(marker_color=PALETA[0], marker_line_width=0, textposition="outside", cliponaxis=False,
                      hovertemplate=eixo + "<br>%{customdata[0]}<extra></extra>")
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=70 if horizontal else 10), height=altura,
                      xaxis_title="", yaxis_title="", bargap=0.3)
    if horizontal:
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(showticklabels=False, showgrid=False)
    return fig


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

# ---------------------------------------------------------------- explorar
with aba_exp:
    gastos = df[df["valor"] > 0].copy()
    gastos["estab"] = gastos["descricao"].map(analise.chave_estabelecimento)
    dmin, dmax = gastos["data"].min().date(), gastos["data"].max().date()

    with st.expander("Filtros", expanded=True):
        f1, f2, f3 = st.columns([2, 3, 2])
        periodo = f1.date_input("Período", (max(dmin, dmax - timedelta(days=90)), dmax),
                                min_value=dmin, max_value=dmax, format="DD/MM/YYYY")
        cats_sel = f2.multiselect("Categorias", sorted(gastos["categoria"].dropna().unique()),
                                  placeholder="Todas")
        tipo = f3.selectbox("Tipo de compra", ["Todas", "À vista", "Parceladas"])
        f4, f5 = st.columns([3, 4])
        busca = f4.text_input("Buscar na descrição", placeholder="ex.: ifood, uber, mercado")
        teto = float(max(gastos["valor"].max(), 1))
        vmin, vmax = f5.slider("Valor da compra (R$)", 0.0, teto, (0.0, teto), step=1.0)

    ini, fim = (periodo if len(periodo) == 2 else (periodo[0], periodo[0])) if isinstance(periodo, tuple) else (periodo, periodo)
    filt = gastos[(gastos["data"].dt.date >= ini) & (gastos["data"].dt.date <= fim)
                  & gastos["valor"].between(vmin, vmax)]
    if cats_sel:
        filt = filt[filt["categoria"].isin(cats_sel)]
    if tipo != "Todas":
        parcelada = filt["parcela"].notna() & (filt["parcela"] != "")
        filt = filt[parcelada if tipo == "Parceladas" else ~parcelada]
    if busca.strip():
        filt = filt[filt["descricao"].str.contains(busca.strip(), case=False, regex=False)]

    if filt.empty:
        st.info("Nenhuma compra com esses filtros.")
    else:
        dias = max((fim - ini).days + 1, 1)
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Total no período", brl(filt["valor"].sum()))
        e2.metric("Compras", len(filt))
        e3.metric("Valor médio por compra", brl(filt["valor"].mean()))
        e4.metric("Média por dia", brl(filt["valor"].sum() / dias))

        visao = st.segmented_control(
            "Ver por", ["Dia a dia", "Mês a mês", "Categoria", "Estabelecimento", "Dia da semana", "Mapa"],
            default="Dia a dia") or "Dia a dia"

        if visao == "Dia a dia":
            d = filt.groupby(filt["data"].dt.date)["valor"].sum().reset_index()
            d.columns = ["Dia", "Valor"]
            st.plotly_chart(barras(d, "Dia", "Valor"), width="stretch")
        elif visao == "Mês a mês":
            d = filt.groupby(filt["data"].dt.to_period("M"))["valor"].sum().reset_index()
            d.columns = ["Mês", "Valor"]
            d["Mês"] = d["Mês"].dt.strftime("%m/%Y")
            fig = barras(d, "Mês", "Valor")
            fig.update_xaxes(type="category")
            st.plotly_chart(fig, width="stretch")
        elif visao == "Categoria":
            d = filt.groupby("categoria")["valor"].sum().sort_values(ascending=False).reset_index()
            st.plotly_chart(barras(d, "valor", "categoria", horizontal=True, altura=60 + 34 * len(d)),
                            width="stretch")
        elif visao == "Estabelecimento":
            d = filt.groupby("estab")["valor"].sum().sort_values(ascending=False).head(15).reset_index()
            st.caption("Os 15 lugares onde você mais gastou no período.")
            st.plotly_chart(barras(d, "valor", "estab", horizontal=True, altura=60 + 34 * len(d)),
                            width="stretch")
        elif visao == "Dia da semana":
            nomes = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            d = filt.groupby(filt["data"].dt.dayofweek)["valor"].sum().reindex(range(7), fill_value=0).reset_index()
            d.columns = ["Dia", "Valor"]
            d["Dia"] = d["Dia"].map(lambda i: nomes[i])
            st.plotly_chart(barras(d, "Dia", "Valor"), width="stretch")
        else:
            st.caption("Cada bloco é um estabelecimento; o tamanho é o quanto você gastou. Clique numa categoria para ampliar.")
            d = filt.groupby(["categoria", "estab"])["valor"].sum().reset_index()
            d["_txt"] = d["valor"].map(brl)
            fig = px.treemap(d, path=["categoria", "estab"], values="valor", color="categoria",
                             color_discrete_map={c: CORES.get(c, CINZA) for c in d["categoria"].unique()})
            fig.update_traces(texttemplate="%{label}<br>R$ %{value:,.0f}", textfont_color="white",
                              hovertemplate="%{label}<br>R$ %{value:,.2f}<extra></extra>",
                              marker=dict(line=dict(width=2, color="white")))
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=520)
            st.plotly_chart(fig, width="stretch")

        with st.expander(f"Ver as {len(filt)} compras filtradas"):
            lista = filt.sort_values("data", ascending=False)[["data", "descricao", "categoria", "parcela", "valor"]]
            st.dataframe(lista, hide_index=True, width="stretch", column_config={
                "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "descricao": "Descrição", "categoria": "Categoria", "parcela": "Parcela",
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")})
            st.download_button("Baixar CSV do filtro", lista.to_csv(index=False).encode(),
                               "compras_filtradas.csv", "text/csv")

# ---------------------------------------------------------------- meu cartão
with aba_cartao:
    hoje = date.today()
    dia_fech = int(fechamento)
    venc = db.get_config("vencimento")
    dia_venc = pd.Timestamp(venc).day if venc else None

    m1, m2, m3 = st.columns(3)
    m1.metric("Limite total", brl(limite))
    m2.metric("Usado", brl(usado), f"{usado / limite:.0%} do limite" if limite else None,
              delta_color="off", delta_arrow="off")
    m3.metric("Disponível", brl(max(limite - usado, 0)))

    m4, m5, m6 = st.columns(3)
    if dia_fech:
        prox = hoje.replace(day=dia_fech)
        if hoje.day >= dia_fech:
            prox = (pd.Timestamp(prox) + pd.DateOffset(months=1)).date()
        m4.metric("Fatura fecha", f"dia {dia_fech}", f"faltam {(prox - hoje).days} dias",
                  delta_color="off", delta_arrow="off")
        m6.metric("Melhor dia para comprar", f"dia {dia_fech}",
                  help="Comprando no dia do fechamento (ou logo depois), a compra só entra na "
                       "fatura seguinte — você ganha cerca de 40 dias para pagar.")
    else:
        m4.metric("Fatura fecha", "—", help="Informe o dia de fechamento na barra lateral.")
        m6.metric("Melhor dia para comprar", "—")
    m5.metric("Vencimento", f"dia {dia_venc}" if dia_venc else "—",
              help=None if dia_venc else "Vem da sincronização com o Nubank.")

    st.subheader(f"Do que é feita a fatura {pd.Period(mes).strftime('%m/%Y')}")
    chaves_rec = set(rec["Estabelecimento"].map(analise.chave_estabelecimento)) if not rec.empty else set()
    eh_parc = gastos_mes["parcela"].notna() & (gastos_mes["parcela"] != "")
    eh_rec = gastos_mes["descricao"].map(analise.chave_estabelecimento).isin(chaves_rec) & ~eh_parc
    comp = pd.DataFrame({
        "Tipo": ["Compras do mês", "Parcelas", "Assinaturas e recorrentes"],
        "Valor": [gastos_mes[~eh_parc & ~eh_rec]["valor"].sum(), gastos_mes[eh_parc]["valor"].sum(),
                  gastos_mes[eh_rec]["valor"].sum()]})
    st.plotly_chart(barras(comp, "Valor", "Tipo", horizontal=True, altura=190), width="stretch")
    fixo = comp["Valor"].iloc[1:].sum()
    if gastos_mes["valor"].sum() > 0:
        st.caption(f"{fixo / gastos_mes['valor'].sum():.0%} desta fatura ({brl(fixo)}) já estava "
                   "comprometido com parcelas e assinaturas antes de você comprar qualquer coisa.")

    st.subheader("Parcelas que ainda vão cair")
    abertas = analise.parcelas_em_aberto(df)
    if abertas.empty:
        st.info("Nenhuma compra parcelada em aberto.")
    else:
        proj = analise.projecao_parcelas(abertas)
        p1, p2 = st.columns(2)
        p1.metric("Total ainda a pagar em parcelas", brl(abertas["Ainda a pagar"].sum()))
        p2.metric("Última parcela termina em", proj["Fatura"].iloc[-1])
        fig = barras(proj, "Fatura", "valor", altura=300)
        fig.update_xaxes(type="category")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(abertas.drop(columns="_mes").style.format({"Parcela": brl, "Ainda a pagar": brl}),
                     hide_index=True, width="stretch")

    with st.expander("Como funciona a fatura do cartão"):
        st.markdown(
            "- **Fechamento**: dia em que o banco soma as compras e fecha a fatura. Compras feitas "
            "a partir desse dia entram na fatura do mês seguinte.\n"
            "- **Vencimento**: dia limite para pagar, normalmente uns 7 dias depois do fechamento.\n"
            "- **Limite**: uma compra parcelada ocupa o valor **inteiro** do limite na hora; ele é "
            "liberado aos poucos, a cada parcela paga.\n"
            "- **Pagar menos que o total** faz o restante entrar no rotativo, com os juros mais "
            "altos do mercado. Sempre que der, pague a fatura inteira.")

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
