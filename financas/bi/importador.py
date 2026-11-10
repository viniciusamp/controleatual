"""Leitura de arquivos exportados pelo Nubank (CSV de fatura, CSV de conta, OFX)."""
from __future__ import annotations

import io
import re

import pandas as pd

COLUNAS = ["data", "descricao", "valor", "parcela", "origem"]


def _ler_csv(conteudo: bytes) -> pd.DataFrame:
    texto = conteudo.decode("utf-8-sig", errors="replace")
    sep = ";" if texto.count(";") > texto.count(",") else ","
    df = pd.read_csv(io.StringIO(texto), sep=sep)
    df.columns = [c.strip().lower() for c in df.columns]

    # Fatura do cartão: date,title,amount  (compras positivas)
    if {"date", "title", "amount"} <= set(df.columns):
        out = pd.DataFrame({
            "data": pd.to_datetime(df["date"], errors="coerce"),
            "descricao": df["title"].astype(str),
            "valor": pd.to_numeric(df["amount"], errors="coerce"),
        })
    # Extrato da conta: Data,Valor,Identificador,Descrição  (saídas negativas)
    elif {"data", "valor"} <= set(df.columns):
        desc_col = next((c for c in df.columns if c.startswith("descri")), None)
        valor = df["valor"]
        if valor.dtype == object:
            valor = valor.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        out = pd.DataFrame({
            "data": pd.to_datetime(df["data"], dayfirst=True, errors="coerce"),
            "descricao": df[desc_col].astype(str) if desc_col else "",
            "valor": -pd.to_numeric(valor, errors="coerce"),
        })
    else:
        raise ValueError(
            "Formato de CSV não reconhecido. Esperado 'date,title,amount' (fatura) "
            "ou 'Data,Valor,Identificador,Descrição' (conta)."
        )
    return out


def _ler_ofx(conteudo: bytes) -> pd.DataFrame:
    texto = conteudo.decode("latin-1", errors="replace")
    linhas = []
    for bloco in re.findall(r"<STMTTRN>(.*?)</STMTTRN>", texto, flags=re.S | re.I):
        def campo(nome):
            m = re.search(rf"<{nome}>([^<\r\n]+)", bloco, flags=re.I)
            return m.group(1).strip() if m else None
        data = campo("DTPOSTED")
        linhas.append({
            "data": pd.to_datetime(data[:8], format="%Y%m%d", errors="coerce") if data else pd.NaT,
            "descricao": campo("MEMO") or campo("NAME") or "",
            "valor": -float((campo("TRNAMT") or "0").replace(",", ".")),
        })
    if not linhas:
        raise ValueError("Nenhuma transação encontrada no OFX.")
    return pd.DataFrame(linhas)


def extrair_parcela(descricao: str) -> str | None:
    m = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})\s*$", descricao)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def ler_arquivo(nome: str, conteudo: bytes) -> pd.DataFrame:
    df = _ler_ofx(conteudo) if nome.lower().endswith(".ofx") else _ler_csv(conteudo)
    df = df.dropna(subset=["data", "valor"])
    df["descricao"] = df["descricao"].str.strip()
    df["parcela"] = df["descricao"].map(extrair_parcela)
    df["origem"] = "arquivo"
    return df[COLUNAS]
