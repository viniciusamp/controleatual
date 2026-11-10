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

## Acessar pelo celular, de qualquer lugar, com segurança

O painel só aceita conexões do próprio computador (`localhost`). Ele **não**
fica exposto na rede nem na internet — e não deve ficar: não abra a porta 8501
no roteador. Para acessar de fora, use o [Tailscale](https://tailscale.com),
uma rede privada gratuita e criptografada entre os **seus** aparelhos:

1. Instale o Tailscale no computador (<https://tailscale.com/download>) e entre com uma conta.
2. Instale o app Tailscale no celular e entre com a **mesma conta**.
3. Com o painel rodando, abra outro terminal no computador e rode:
   ```bash
   tailscale serve --bg 8501
   ```
   Na primeira vez ele pede para ativar o HTTPS (mostra um link; é só aceitar).
   O comando devolve um endereço como `https://seu-pc.nome-da-rede.ts.net`.
4. No celular, com o Tailscale ligado, abra esse endereço e entre com a senha do painel.

Só aparelhos logados na sua conta Tailscale alcançam o endereço; para o resto
da internet ele não existe. A conexão é HTTPS e ainda passa pela senha do
painel, que bloqueia por 15 minutos após 5 tentativas erradas.

O computador precisa estar ligado com o painel rodando. Para ficar disponível
24 h, rode o mesmo projeto num servidor (abaixo) com o Tailscale instalado nele.

### Em um servidor (VPS) com Docker

```bash
git clone https://github.com/viniciusamp/controleatual.git
cd controleatual/financas
cp .env.example .env      # edite e defina APP_PASSWORD
docker compose up -d --build
```

O container também só escuta em `localhost`. Publique com `tailscale serve --bg 8501`
(privado) ou, se quiser um endereço público, com um domínio e o
[Caddy](https://caddyserver.com) (`caddy reverse-proxy --from seu.dominio.com --to localhost:8501`),
que cuida do HTTPS. Faça backup da pasta `financas/dados/`.

## Como funciona

- **Categorias**: regras por palavra-chave em `bi/categorias.py` (edite à vontade).
  Na aba *Transações* você corrige qualquer categoria e a correção fica salva.
- **Mês da fatura**: informe o dia de fechamento do seu cartão na barra
  lateral; compras a partir desse dia vão para a fatura seguinte (0 = mês da compra).
- **Uso do limite**: com a Pluggy usa o limite disponível real; com arquivo,
  estima pelo valor da fatura selecionada (parcelas futuras não entram).
- **Explorar**: filtros por período, categoria, tipo (à vista/parcelada), valor e
  texto, com visões por dia, mês, categoria, estabelecimento, dia da semana e mapa de blocos.
- **Meu cartão**: limite, fechamento, vencimento, melhor dia de compra, composição
  da fatura e projeção das parcelas que ainda vão cair nas próximas faturas.
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
