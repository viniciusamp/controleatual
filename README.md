# Checklist de Instalação

App single-file (HTML + CSS + JS puro, sem dependências) para acompanhar a
implantação de sistemas em clientes: configuração inicial e treinamento,
organizados por segmento de negócio (Material de Construção, Oficina,
Mercearia, etc.) e por sistema (ex: Integra).

## Como usar

Basta abrir o `index.html` em um navegador — não precisa de servidor nem
build.

## Estrutura de dados

- **Configuração padrão**: itens que valem para qualquer cliente.
- **Segmentos**: tipos de negócio, cada um com itens de configuração
  específicos.
- **Sistemas**: cada sistema tem tópicos de treinamento (telas), que podem
  ser detalhados em subitens.
- **Clientes**: vinculados a um segmento e a um ou mais sistemas, com
  checklist próprio de configuração e treinamento.

## Dados e backup

Os dados são salvos automaticamente (via `window.storage`, oferecido pelo
ambiente onde o app roda). Use os botões **Backup** (exporta um `.json`) e
**Importar** no topo da tela para não perder o progresso ao migrar de
ambiente ou fazer uma cópia de segurança.
