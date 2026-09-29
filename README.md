# Checklist de Instalação

App (HTML + CSS + JS puro) para acompanhar a implantação de sistemas em
clientes: configuração inicial e treinamento, organizados por segmento de
negócio (Material de Construção, Oficina, Mercearia, etc.) e por sistema
(ex: Integra).

Site publicado: https://viniciusamp.github.io/controleatual/

## Como usar

O app é servido pelo GitHub Pages a partir do branch `main`. Qualquer
pessoa com o link acessa e edita o checklist, sem login — os dados ficam
salvos num banco Supabase compartilhado e atualizam ao vivo entre quem
estiver com a página aberta.

## Estrutura de dados

- **Configuração padrão**: itens que valem para qualquer cliente.
- **Segmentos**: tipos de negócio, cada um com itens de configuração
  específicos.
- **Sistemas**: cada sistema tem tópicos de treinamento (telas), que podem
  ser detalhados em subitens.
- **Clientes**: vinculados a um segmento e a um ou mais sistemas, com
  checklist próprio de configuração e treinamento.

## Banco de dados (Supabase)

As credenciais do projeto Supabase ficam em `config.js` (a chave é
`publishable`, feita pra ser exposta no navegador). O esquema das tabelas
está em `supabase-schema.sql` — rode esse arquivo no SQL Editor do
Supabase ao configurar um projeto novo.

## Backup

Use o botão **Backup** no topo da tela para exportar um `.json` com todo o
estado atual, e **Importar** para restaurar a partir de um desses
arquivos.

## Ferramentas

- `ferramentas/limpeza-windows.bat`: script para limpar arquivos temporários,
  caches (Windows, navegadores, miniaturas, DNS), lixeira e relatórios de erro
  do Windows. Tem modo rápido e completo (inclui cache do Windows Update,
  DISM, SFC e otimização do disco). Basta dar dois cliques — ele pede
  permissão de Administrador sozinho e salva um log na Área de Trabalho.
