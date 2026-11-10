# 💳 Meu BI Financeiro

Painel pessoal para acompanhar os gastos do cartão Nubank: gastos por
categoria (pizza), uso do limite, valor e histórico das faturas, cobranças
recorrentes/assinaturas e sugestões de onde economizar.

Feito em Python + [Streamlit](https://streamlit.io) + Plotly, com os dados
num arquivo SQLite local (`dados/financas.db`).

## O Nubank tem API?

**Não tem API pública oficial para pessoa física.** As opções são:

| Caminho | Como funciona | Prós | Contras |
|---|---|---|---|
| **1. Importar arquivo** (já funciona) | No app do Nubank, exporte a fatura/extrato (CSV ou OFX) e envie pelo painel | Grátis, sem terceiros, sem risco | Manual (1x por mês) |
| **2. Open Finance via Pluggy** (já implementado, opcional) | Você autoriza o compartilhamento dos seus dados Nubank com a [Pluggy](https://pluggy.ai), um agregador regulado; o painel busca pela API deles | Automático, oficial (Banco Central), traz limite real | Precisa criar conta de desenvolvedor na Pluggy; alguns tipos de lançamento podem não vir |
| 3. Bibliotecas não oficiais (ex.: pynubank) | Simulam o app | — | Quebram com frequência e violam os termos de uso. **Não recomendado.** |

### Exportar a fatura no Nubank
No app: **Cartão de crédito → Faturas → escolha o mês → Exportar / enviar por e-mail**
(o nome exato do menu muda entre versões). O extrato da conta pode ser
exportado em **Conta → Extrato → Exportar**, em CSV ou OFX.

Formatos aceitos:
- Fatura do cartão: CSV `date,title,amount`
- Extrato da conta: CSV `Data,Valor,Identificador,Descrição`
- OFX de qualquer banco

Importar o mesmo arquivo duas vezes não duplica nada.

### Conectar pela Pluggy — grátis com o Meu Pluggy
1. Crie conta em <https://meu.pluggy.ai> e conecte o Nubank (Open Finance).
2. Crie conta de desenvolvedor em <https://dashboard.pluggy.ai>. Em **Aplicações**
   aparece uma aplicação de desenvolvimento com **Client ID** e **Client Secret** (🔑).
3. Clique no **▶** dessa aplicação, busque o conector **MeuPluggy** (não "Nubank" —
   contas de teste só conectam o MeuPluggy ou bancos sandbox) e entre com o login do meu.pluggy.ai.
4. Copie o **Item ID** da conexão: em **Visualizar JSON**, é o campo `itemId` das contas.
5. Crie `financas/.env` (copie de `.env.example`) com `PLUGGY_CLIENT_ID`,
   `PLUGGY_CLIENT_SECRET` e `PLUGGY_ITEM_ID` — **todos da mesma aplicação**.

O painel então sincroniza sozinho ao abrir (no máximo a cada 6 h) e pelo botão
**🔄 Sincronizar com Nubank**. Ele traz 12 meses de transações do cartão, o limite
total/disponível e o dia de fechamento reais. As categorias da Pluggy (em inglês)
são traduzidas para as do BI quando as regras por palavra-chave não reconhecem
a compra. O MeuPluggy atualiza os dados do banco uma vez por dia.

## Rodar no seu computador

```bash
cd financas
pip install -r requirements.txt
streamlit run app.py
```

Abra <http://localhost:8501>. Para ver o painel sem seus dados, use
**Manutenção → Carregar dados de exemplo**.

## Colocar na nuvem (acessar de qualquer lugar)

Qualquer VPS barata serve (Oracle Cloud Free Tier, AWS Lightsail, DigitalOcean,
Hostinger, Magalu Cloud...). Com Docker instalado no servidor:

```bash
git clone https://github.com/viniciusamp/controleatual.git
cd controleatual/financas
cp .env.example .env      # edite e defina APP_PASSWORD
docker compose up -d --build
```

Acesse `http://IP-DO-SERVIDOR:8501` (libere a porta 8501 no firewall do provedor).

**Segurança — são seus dados financeiros:**
- Sempre defina `APP_PASSWORD` no `.env`; sem ele o painel abre sem senha.
- O ideal é usar HTTPS. O jeito mais simples: aponte um domínio para o IP e
  coloque o [Caddy](https://caddyserver.com) na frente
  (`caddy reverse-proxy --from seu.dominio.com --to localhost:8501`), que
  gera o certificado automaticamente. Outra opção sem abrir porta nenhuma:
  [Tailscale](https://tailscale.com) ou Cloudflare Tunnel.
- O banco fica em `financas/dados/` no servidor — faça backup dessa pasta.

## Como funciona

- **Categorias**: regras por palavra-chave em `bi/categorias.py` (edite à vontade).
  Na aba *Transações* você corrige qualquer categoria e a correção fica salva.
- **Mês da fatura**: informe o dia de fechamento do seu cartão na barra
  lateral; compras a partir desse dia vão para a fatura seguinte (0 = mês da compra).
- **Uso do limite**: com a Pluggy usa o limite disponível real; com arquivo,
  estima pelo valor da fatura selecionada (parcelas futuras não entram).
- **Recorrentes**: mesmo estabelecimento cobrado em meses diferentes com valor
  parecido (±15%), ou na categoria *Assinaturas*. Parcelamentos são ignorados.
- **Onde economizar**: maior categoria, categorias acima da média, total de
  assinaturas, compras pequenas acumuladas, peso das parcelas e uso do limite.

## Estrutura

```
financas/
├── app.py               # painel Streamlit
├── bi/
│   ├── categorias.py    # regras de categorização
│   ├── importador.py    # leitura de CSV/OFX do Nubank
│   ├── analise.py       # fatura, recorrentes, sugestões
│   ├── pluggy.py        # conexão Open Finance (opcional)
│   └── db.py            # SQLite
├── dados_exemplo/       # fatura fictícia para testar
├── Dockerfile / docker-compose.yml
└── .env.example
```

## Próximos passos possíveis
- Metas/orçamento por categoria com alerta
- Previsão das próximas faturas com as parcelas futuras
- Múltiplos cartões/contas e múltiplos usuários (virar produto)
- Alertas por e-mail/Telegram
