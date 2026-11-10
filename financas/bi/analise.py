"""Cálculos do BI: mês de fatura, recorrências e sugestões de economia."""
from __future__ import annotations

import re

import pandas as pd

from .categorias import normalizar


def brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def mes_fatura(datas: pd.Series, dia_fechamento: int) -> pd.Series:
    """Compras a partir do dia de fechamento caem na fatura do mês seguinte.

    dia_fechamento=0 usa o mês calendário da compra.
    """
    d = pd.to_datetime(datas)
    periodo = d.dt.to_period("M")
    if not dia_fechamento:
        return periodo.astype(str)
    return (periodo + (d.dt.day >= dia_fechamento).astype(int)).astype(str)


def chave_estabelecimento(descricao: str) -> str:
    s = normalizar(descricao)
    s = re.sub(r"\d{1,2}\s*/\s*\d{1,2}\s*$", "", s)      # parcela 3/10
    s = re.sub(r"[^a-z ]", " ", s)                          # números, *, -
    s = re.sub(r"\b(br|com|www|pg|pag|ltda|sa)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()[:30]


def recorrentes(df: pd.DataFrame, min_meses: int = 2, tolerancia: float = 0.15) -> pd.DataFrame:
    """Estabelecimentos cobrados em meses diferentes com valor parecido (assinaturas)."""
    gastos = df[(df["valor"] > 0) & (df["parcela"].isna())].copy()
    if gastos.empty:
        return pd.DataFrame()
    gastos["chave"] = gastos["descricao"].map(chave_estabelecimento)
    gastos["mes"] = gastos["data"].dt.to_period("M")
    linhas = []
    for chave, g in gastos.groupby("chave"):
        meses = g["mes"].nunique()
        media = g["valor"].mean()
        variacao = g["valor"].std(ddof=0) / media if media else 1
        eh_assinatura_cat = (g["categoria"] == "Assinaturas").any()
        if (meses >= min_meses and variacao <= tolerancia) or eh_assinatura_cat:
            ultima = g.sort_values("data").iloc[-1]
            linhas.append({
                "Estabelecimento": ultima["descricao"],
                "Categoria": ultima["categoria"],
                "Valor médio": round(media, 2),
                "Meses cobrados": meses,
                "Última cobrança": ultima["data"].date(),
                "Custo anual estimado": round(media * 12, 2),
                "Confiança": "alta" if meses >= 3 and variacao <= tolerancia else
                             "média" if meses >= min_meses else "baixa (só 1 cobrança)",
            })
    if not linhas:
        return pd.DataFrame()
    return pd.DataFrame(linhas).sort_values("Custo anual estimado", ascending=False)


def sugestoes(df_mes: pd.DataFrame, df_hist: pd.DataFrame, rec: pd.DataFrame,
              limite: float, fatura_atual: float) -> list[str]:
    dicas = []
    gastos = df_mes[df_mes["valor"] > 0]
    total = gastos["valor"].sum()
    if total <= 0:
        return dicas

    por_cat = gastos.groupby("categoria")["valor"].sum().sort_values(ascending=False)
    top, top_v = por_cat.index[0], por_cat.iloc[0]
    dicas.append(f"**{top}** é sua maior categoria: {brl(top_v)} ({top_v / total:.0%} da fatura). "
                 f"Cortar 20% dela economizaria ~{brl(top_v * 0.2)}/mês.")

    hist = df_hist[df_hist["valor"] > 0]
    if hist["mes_fatura"].nunique() >= 3:
        media_cat = hist.groupby(["mes_fatura", "categoria"])["valor"].sum().groupby("categoria").mean()
        for cat, v in por_cat.items():
            m = media_cat.get(cat)
            if m and v > m * 1.3 and v - m > 50:
                dicas.append(f"**{cat}** está {v / m - 1:.0%} acima da sua média mensal "
                             f"({brl(v)} vs {brl(m)}).")

    if not rec.empty:
        anual = rec["Custo anual estimado"].sum()
        dicas.append(f"Você tem **{len(rec)} cobranças recorrentes** somando ~{brl(anual / 12)}/mês "
                     f"({brl(anual)}/ano). Revise as que não usa.")

    peq = gastos[gastos["valor"] < 30]
    if len(peq) >= 10:
        dicas.append(f"{len(peq)} compras pequenas (< R$ 30) somam **{brl(peq['valor'].sum())}** — "
                     "o famoso 'efeito cafezinho'.")

    parcelado = gastos[gastos["parcela"].notna()]["valor"].sum()
    if parcelado > total * 0.3:
        dicas.append(f"Parcelas representam {parcelado / total:.0%} da fatura — "
                     "isso compromete o limite dos próximos meses.")

    if limite and fatura_atual > limite * 0.8:
        dicas.append(f"A fatura usa **{fatura_atual / limite:.0%} do limite**. Acima de 30% já pesa "
                     "no score de crédito.")
    return dicas
