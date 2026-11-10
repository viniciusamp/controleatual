"""Categorização automática de transações por palavras-chave.

Edite REGRAS para ajustar ao seu perfil de gastos. A primeira regra que
casar com a descrição define a categoria.
"""
import re
import unicodedata

REGRAS: dict[str, list[str]] = {
    "Assinaturas": [
        "netflix", "spotify", "amazon prime", "prime video", "disney", "hbo", "max.com",
        "globoplay", "youtube premium", "google one", "icloud", "apple.com", "deezer",
        "paramount", "crunchyroll", "chatgpt", "openai", "anthropic", "claude.ai",
        "microsoft", "adobe", "canva", "dropbox", "linkedin", "smart fit", "smartfit",
        "gympass", "wellhub", "totalpass", "audible", "kindle unlimited",
    ],
    "Alimentação": [
        "ifood", "ifd", "rappi", "restaurante", "lanchonete", "padaria", "pizzaria",
        "burger", "mcdonald", "bk ", "subway", "starbucks", "cafe", "bar ", "churrascaria",
        "sushi", "outback", "habib", "aiqfome", "ze delivery",
    ],
    "Compras online": [
        "amazon", "mercadolivre", "mercado livre", "mercadopago", "shopee", "aliexpress",
        "magalu", "magazine luiza", "americanas", "shein", "casas bahia", "kabum",
    ],
    "Mercado": [
        "mercado", "supermercado", "atacadao", "assai", "carrefour", "pao de acucar",
        "extra", "hortifruti", "sacolao", "acougue", "big ", "sams club", "dia ",
    ],
    "Transporte": [
        "uber", "99app", "99 ", "cabify", "posto", "shell", "ipiranga", "petrobras",
        "br mania", "estacionamento", "estapar", "sem parar", "conectcar", "veloe",
        "pedagio", "metro", "onibus", "bilhete unico",
    ],
    "Saúde": [
        "farmacia", "drogaria", "droga raia", "drogasil", "pague menos", "panvel",
        "clinica", "hospital", "laboratorio", "odonto", "medic", "unimed",
    ],
    "Casa e contas": [
        "enel", "light", "sabesp", "cemig", "copel", "vivo", "claro", "tim ", "oi ",
        "net ", "internet", "gas ", "condominio", "aluguel", "leroy", "tok stok",
    ],
    "Lazer e viagens": [
        "cinema", "cinemark", "ingresso", "sympla", "eventim", "steam", "playstation",
        "xbox", "nintendo", "airbnb", "booking", "hotel", "latam", "gol ", "azul ",
        "decolar", "123milhas",
    ],
    "Vestuário": [
        "renner", "riachuelo", "c&a", "cea ", "zara", "nike", "adidas", "centauro",
        "netshoes", "hering", "marisa",
    ],
    "Educação": [
        "udemy", "alura", "coursera", "escola", "faculdade", "curso", "livraria",
        "duolingo",
    ],
    "Pagamentos e ajustes": [
        "estorno", "credito de", "iof",
        "juros", "multa", "encargos", "anuidade",
    ],
}

OUTROS = "Outros"
PAGAMENTO = "Pagamento da fatura"
PALAVRAS_PAGAMENTO = ["pagamento recebido", "pagamento em ", "pagamento efetuado", "pgto fatura"]


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texto.lower()).strip() + " "


def categorizar(descricao: str, categoria_banco: str | None = None) -> str:
    desc = normalizar(descricao)
    if any(p in desc for p in PALAVRAS_PAGAMENTO):
        return PAGAMENTO
    for categoria, palavras in REGRAS.items():
        if any(p in desc for p in palavras):
            return categoria
    if categoria_banco:
        return str(categoria_banco)
    return OUTROS
