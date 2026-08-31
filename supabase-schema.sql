-- Checklist de Instalação — esquema Supabase
--
-- Guarda todo o estado do app (segmentos, sistemas, clientes, checklists)
-- em uma única linha JSON. Simples de propósito: o app já trabalha com
-- essa árvore de dados como um documento só, então replicar isso como
-- tabelas relacionais não traria benefício real pra esse caso de uso.
--
-- Como rodar: cole este arquivo inteiro no SQL Editor do seu projeto
-- Supabase (menu lateral -> SQL Editor -> New query) e clique em Run.

create table if not exists checklist_state (
  id text primary key,
  data jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

insert into checklist_state (id, data)
values ('default', '{}'::jsonb)
on conflict (id) do nothing;

alter table checklist_state enable row level security;

-- Acesso aberto: qualquer pessoa com o link do site lê e grava o
-- checklist, sem precisar de login (igual a uma planilha compartilhada).
drop policy if exists "checklist_state_select" on checklist_state;
create policy "checklist_state_select" on checklist_state
  for select using (true);

drop policy if exists "checklist_state_update" on checklist_state;
create policy "checklist_state_update" on checklist_state
  for update using (true) with check (true);

drop policy if exists "checklist_state_insert" on checklist_state;
create policy "checklist_state_insert" on checklist_state
  for insert with check (true);

-- Habilita o realtime, para que a mudança de uma pessoa apareça na tela
-- das outras sem precisar recarregar a página.
alter publication supabase_realtime add table checklist_state;
