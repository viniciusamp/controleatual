"""Persistência local em SQLite (um arquivo, fácil de fazer backup)."""
from __future__ import annotations

import hashlib
import os
import sqlite3

import pandas as pd

CAMINHO = os.environ.get("BI_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "dados", "financas.db"))


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(CAMINHO)), exist_ok=True)
    con = sqlite3.connect(CAMINHO)
    con.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            parcela TEXT,
            categoria TEXT,
            categoria_manual INTEGER DEFAULT 0,
            origem TEXT
        )""")
    con.execute("CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT)")
    return con


def _id(linha) -> str:
    base = f"{pd.Timestamp(linha['data']).date()}|{linha['descricao']}|{round(float(linha['valor']), 2)}|{linha.get('parcela') or ''}"
    return hashlib.sha1(base.encode()).hexdigest()


def salvar(df: pd.DataFrame) -> int:
    """Insere transações ignorando duplicadas. Retorna quantas eram novas."""
    with _conn() as con:
        antes = con.execute("SELECT COUNT(*) FROM transacoes").fetchone()[0]
        for _, l in df.iterrows():
            con.execute(
                "INSERT OR IGNORE INTO transacoes (id, data, descricao, valor, parcela, categoria, origem) "
                "VALUES (?,?,?,?,?,?,?)",
                (l.get("id") or _id(l), str(pd.Timestamp(l["data"]).date()), l["descricao"],
                 float(l["valor"]), l.get("parcela"), l.get("categoria"), l.get("origem")),
            )
        return con.execute("SELECT COUNT(*) FROM transacoes").fetchone()[0] - antes


def carregar() -> pd.DataFrame:
    with _conn() as con:
        df = pd.read_sql("SELECT * FROM transacoes", con, parse_dates=["data"])
    return df


def definir_categoria(id_: str, categoria: str) -> None:
    with _conn() as con:
        con.execute("UPDATE transacoes SET categoria=?, categoria_manual=1 WHERE id=?", (categoria, id_))


def recategorizar(func) -> None:
    """Reaplica as regras nas transações que não foram editadas à mão."""
    with _conn() as con:
        for id_, desc in con.execute("SELECT id, descricao FROM transacoes WHERE categoria_manual=0").fetchall():
            con.execute("UPDATE transacoes SET categoria=? WHERE id=?", (func(desc), id_))


def apagar_tudo() -> None:
    with _conn() as con:
        con.execute("DELETE FROM transacoes")


def get_config(chave: str, padrao=None):
    with _conn() as con:
        r = con.execute("SELECT valor FROM config WHERE chave=?", (chave,)).fetchone()
    return r[0] if r else padrao


def set_config(chave: str, valor) -> None:
    with _conn() as con:
        con.execute("INSERT OR REPLACE INTO config (chave, valor) VALUES (?,?)", (chave, str(valor)))
