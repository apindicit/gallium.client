-- ============================================================
-- Gallium — база ключей для Supabase
-- Как использовать:
--   1. supabase.com → New project
--   2. SQL Editor → вставить этот файл целиком → Run
--   3. Project URL — кнопка «Connect» в шапке проекта
--      Ключи — «Project Settings (шестерёнка) → API Keys»:
--      publishable (sb_publishable_...) или anon → в src/shared.js / index.html
--      secret (sb_secret_...) или service_role → только в keys.html (НЕ заливать!)
-- ============================================================

create table if not exists public.keys (
  code       text primary key,
  plan       text not null,
  used       boolean not null default false,
  used_by    text,
  used_at    timestamptz,
  created_at timestamptz not null default now()
);

-- RLS включён, политик для anon НЕТ:
-- напрямую читать/писать таблицу анонимный доступ не может.
alter table public.keys enable row level security;

-- Единственная точка входа: точный вызов по коду ключа.
-- security definer: функция сама читает/метит строку,
-- но посторонний код не угадать (6+5 символов, ~8e16 вариантов),
-- и выдать список активных ключей она не может.
create or replace function public.redeem_key(p_code text, p_user text)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  r record;
begin
  select * into r from public.keys where code = p_code for update;
  if not found then
    return jsonb_build_object('status', 'notfound');
  end if;
  if r.used then
    return jsonb_build_object('status', 'used');
  end if;
  update public.keys
     set used = true, used_by = p_user, used_at = now()
   where code = p_code;
  return jsonb_build_object('status', 'ok', 'plan', r.plan);
end;
$$;

revoke all on function public.redeem_key(text, text) from public;
grant execute on function public.redeem_key(text, text) to anon;
grant execute on function public.redeem_key(text, text) to authenticated;
