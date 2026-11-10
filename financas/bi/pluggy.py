"""Conexão automática com o Nubank via Open Finance usando a Pluggy (https://pluggy.ai).

O Nubank não oferece API pública para pessoa física. O caminho é o Open
Finance Brasil, acessado por um agregador autorizado como a Pluggy. Para uso
pessoal e gratuito: conecte o Nubank em https://meu.pluggy.ai e, no
dashboard da Pluggy, conecte o conector "MeuPluggy" pelo Demo da sua
aplicação. Configure PLUGGY_CLIENT_ID, PLUGGY_CLIENT_SECRET e PLUGGY_ITEM_ID.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
import requests

from .importador import COLUNAS

API = "https://api.pluggy.ai"

# Categorias da Pluggy (inglês) -> categorias do BI. Casa por trecho do nome.
MAPA_CATEGORIAS = [
    ("credit card payment", "Pagamento da fatura"),
    ("streaming", "Assinaturas"),
    ("digital services", "Assinaturas"),
    ("gym", "Assinaturas"),
    ("fitness", "Assinaturas"),
    ("food delivery", "Alimentação"),
    ("eating out", "Alimentação"),
    ("restaurant", "Alimentação"),
    ("groceries", "Mercado"),
    ("supermarket", "Mercado"),
    ("online shopping", "Compras online"),
    ("electronics", "Compras online"),
    ("clothing", "Vestuário"),
    ("taxi", "Transporte"),
    ("ride", "Transporte"),
    ("gas station", "Transporte"),
    ("parking", "Transporte"),
    ("toll", "Transporte"),
    ("transport", "Transporte"),
    ("pharmac", "Saúde"),
    ("health", "Saúde"),
    ("dentist", "Saúde"),
    ("hospital", "Saúde"),
    ("housing", "Casa e contas"),
    ("utilities", "Casa e contas"),
    ("telecom", "Casa e contas"),
    ("internet", "Casa e contas"),
    ("mobile", "Casa e contas"),
    ("houseware", "Casa e contas"),
    ("travel", "Lazer e viagens"),
    ("airline", "Lazer e viagens"),
    ("accom", "Lazer e viagens"),
    ("leisure", "Lazer e viagens"),
    ("entertainment", "Lazer e viagens"),
    ("gaming", "Lazer e viagens"),
    ("ticket", "Lazer e viagens"),
    ("education", "Educação"),
    ("book", "Educação"),
    ("bank fees", "Pagamentos e ajustes"),
    ("interest", "Pagamentos e ajustes"),
    ("tax", "Pagamentos e ajustes"),
    ("insurance", "Seguros"),
    ("pet", "Pets"),
    ("transfer", "Transferências e Pix"),
    ("shopping", "Compras online"),
]


def traduzir_categoria(categoria: str | None) -> str | None:
    if not categoria:
        return None
    c = categoria.lower()
    for trecho, destino in MAPA_CATEGORIAS:
        if trecho in c:
            return destino
    return None


def configurado() -> bool:
    return all(os.environ.get(k) for k in ("PLUGGY_CLIENT_ID", "PLUGGY_CLIENT_SECRET", "PLUGGY_ITEM_ID"))


def _token() -> str:
    r = requests.post(f"{API}/auth", json={
        "clientId": os.environ["PLUGGY_CLIENT_ID"],
        "clientSecret": os.environ["PLUGGY_CLIENT_SECRET"],
    }, timeout=30)
    if r.status_code in (401, 403):
        raise RuntimeError("Client ID/Secret recusados. Confira se são da MESMA aplicação "
                           "em que você conectou o MeuPluggy.")
    r.raise_for_status()
    return r.json()["apiKey"]


def _get(path: str, token: str, **params) -> dict:
    r = requests.get(f"{API}{path}", headers={"X-API-KEY": token}, params=params, timeout=60)
    if r.status_code == 404 and path == "/accounts":
        raise RuntimeError("Item não encontrado. Confira o PLUGGY_ITEM_ID e se ele pertence "
                           "à mesma aplicação do Client ID.")
    r.raise_for_status()
    return r.json()


def _data_local(valor: str) -> pd.Timestamp:
    ts = pd.to_datetime(valor, utc=True)
    return ts.tz_convert("America/Sao_Paulo").tz_localize(None).normalize()


def sincronizar(dias: int = 365) -> tuple[pd.DataFrame, dict]:
    """Retorna (transações do cartão, info do cartão: limite, disponível, fechamento...)."""
    token = _token()
    contas = _get("/accounts", token, itemId=os.environ["PLUGGY_ITEM_ID"], type="CREDIT")["results"]
    if not contas:
        raise RuntimeError("Nenhum cartão de crédito encontrado nesse item da Pluggy.")

    linhas = []
    info = {"limite": 0.0, "disponivel": 0.0, "fechamento": None, "vencimento": None}
    inicio = (date.today() - timedelta(days=dias)).isoformat()
    for conta in contas:
        cd = conta.get("creditData") or {}
        info["limite"] += cd.get("creditLimit") or 0
        info["disponivel"] += cd.get("availableCreditLimit") or 0
        info["fechamento"] = info["fechamento"] or cd.get("balanceCloseDate")
        info["vencimento"] = info["vencimento"] or cd.get("balanceDueDate")

        pagina, total = 1, 1
        while pagina <= total:
            resp = _get("/transactions", token, accountId=conta["id"], **{"from": inicio},
                        pageSize=500, page=pagina)
            total = resp.get("totalPages", 1)
            for t in resp["results"]:
                meta = t.get("creditCardMetadata") or {}
                total_parc = meta.get("totalInstallments") or 1
                parcela = f"{meta.get('installmentNumber')}/{total_parc}" if total_parc > 1 else None
                # Em contas de cartão da Pluggy: valor positivo = compra, negativo = pagamento/estorno
                linhas.append({
                    "id": f"pluggy-{t['id']}",
                    "data": _data_local(t["date"]),
                    "descricao": t.get("description") or "",
                    "valor": float(t["amount"]),
                    "parcela": parcela,
                    "origem": "pluggy",
                    "categoria_banco": traduzir_categoria(t.get("category")) or t.get("category"),
                })
            pagina += 1
    df = pd.DataFrame(linhas, columns=["id", *COLUNAS, "categoria_banco"])
    return df, info
