"""Conexão automática com o Nubank via Open Finance usando a Pluggy (https://pluggy.ai).

O Nubank não oferece API pública para pessoa física. O caminho oficial é o
Open Finance Brasil, acessado por um agregador autorizado como a Pluggy.
Configure PLUGGY_CLIENT_ID, PLUGGY_CLIENT_SECRET e PLUGGY_ITEM_ID (o item é
criado quando você conecta sua conta Nubank pelo Pluggy Connect / dashboard).
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
import requests

from .importador import COLUNAS

API = "https://api.pluggy.ai"


def configurado() -> bool:
    return all(os.environ.get(k) for k in ("PLUGGY_CLIENT_ID", "PLUGGY_CLIENT_SECRET", "PLUGGY_ITEM_ID"))


def _token() -> str:
    r = requests.post(f"{API}/auth", json={
        "clientId": os.environ["PLUGGY_CLIENT_ID"],
        "clientSecret": os.environ["PLUGGY_CLIENT_SECRET"],
    }, timeout=30)
    r.raise_for_status()
    return r.json()["apiKey"]


def _get(path: str, token: str, **params) -> dict:
    r = requests.get(f"{API}{path}", headers={"X-API-KEY": token}, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def sincronizar(dias: int = 365) -> tuple[pd.DataFrame, dict]:
    """Retorna (transações do cartão, info do cartão: limite, disponível, vencimento)."""
    token = _token()
    contas = _get("/accounts", token, itemId=os.environ["PLUGGY_ITEM_ID"], type="CREDIT")["results"]
    if not contas:
        raise RuntimeError("Nenhum cartão de crédito encontrado nesse item da Pluggy.")

    linhas, info = [], {}
    inicio = (date.today() - timedelta(days=dias)).isoformat()
    for conta in contas:
        cd = conta.get("creditData") or {}
        info = {
            "limite": cd.get("creditLimit"),
            "disponivel": cd.get("availableCreditLimit"),
            "vencimento": cd.get("balanceDueDate"),
            "fechamento": cd.get("balanceCloseDate"),
            "saldo": conta.get("balance"),
        }
        pagina, total = 1, 1
        while pagina <= total:
            resp = _get("/transactions", token, accountId=conta["id"], **{"from": inicio},
                        pageSize=500, page=pagina)
            total = resp.get("totalPages", 1)
            for t in resp["results"]:
                meta = t.get("creditCardMetadata") or {}
                parcela = (f"{meta['installmentNumber']}/{meta['totalInstallments']}"
                           if meta.get("totalInstallments", 1) and meta.get("totalInstallments", 1) > 1 else None)
                valor = abs(t["amount"]) if t.get("type") == "DEBIT" else -abs(t["amount"])
                linhas.append({
                    "id": f"pluggy-{t['id']}",
                    "data": pd.to_datetime(t["date"]).tz_localize(None) if pd.to_datetime(t["date"]).tzinfo else pd.to_datetime(t["date"]),
                    "descricao": t.get("description", ""),
                    "valor": valor,
                    "parcela": parcela,
                    "origem": "pluggy",
                    "categoria_banco": t.get("category"),
                })
            pagina += 1
    df = pd.DataFrame(linhas, columns=["id", *COLUNAS, "categoria_banco"])
    return df, info
