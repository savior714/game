-- 가입(활성) 구글 계정 목록을 관리자만 조회하기 위한 테이블 및 RLS
-- Supabase SQL Editor에서 한 번 실행하세요. global/auth.js의 ADMIN_EMAILS와 관리자 이메일을 동일하게 맞춥니다.

create table if not exists public.user_directory (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  created_at timestamptz not null default now()
);

alter table public.user_directory enable row level security;

drop policy if exists "user_directory_select_own" on public.user_directory;
drop policy if exists "user_directory_select_admin" on public.user_directory;

-- 본인 행 조회
create policy "user_directory_select_own"
  on public.user_directory for select to authenticated
  using (auth.uid() = id);

-- 관리자만 전체 목록 조회 (아래 이메일을 본인 구글 주소로 교체)
create policy "user_directory_select_admin"
  on public.user_directory for select to authenticated
  using (
    lower(trim(coalesce((select auth.jwt() ->> 'email'), ''))) = lower(trim('savior714@gmail.com'))
  );

create or replace function public.handle_new_user_directory()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.user_directory (id, email, created_at)
  values (new.id, new.email, coalesce(new.created_at, now()))
  on conflict (id) do update
    set email = excluded.email;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created_directory on auth.users;
create trigger on_auth_user_created_directory
  after insert on auth.users
  for each row execute function public.handle_new_user_directory();

-- 기존 가입자 백필(최초 1회)
insert into public.user_directory (id, email, created_at)
select id, email, created_at from auth.users
on conflict (id) do update
  set email = excluded.email;

grant select on public.user_directory to authenticated;
