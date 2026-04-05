-- =============================================================================
-- 기존 DB를 앱 최신 버전에 맞출 때: 이 파일만 SQL Editor에서 한 번 실행하면 됨
-- =============================================================================
-- 전제: tournaments, players, profiles 등 이미 있음 (데이터 유지)
--
-- 하는 일:
--   1) profiles 에 회원가입용 컬럼 추가 (full_name, birth_date, email)
--   2) (권장) 가입 시 profiles 자동 생성 트리거 — 이메일 확인 ON/OFF 관계없이 무해
-- =============================================================================

-- 1) 프로필 컬럼 (회원가입: 이름, 생년월일, 이메일)
alter table profiles add column if not exists full_name text;
alter table profiles add column if not exists birth_date date;
alter table profiles add column if not exists email text;

-- 기존 행: auth.users 와 id 매칭해 이메일 채움 (SQL Editor 에서 한 번 실행)
update public.profiles p
set email = u.email
from auth.users u
where p.id = u.id;

-- 2) 신규 Auth 사용자 → public.profiles 한 줄 생성 (user_metadata 에 full_name, birth_date)
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, role, full_name, birth_date, email)
  values (
    new.id,
    'user',
    nullif(trim(coalesce(new.raw_user_meta_data->>'full_name', '')), ''),
    nullif(trim(coalesce(new.raw_user_meta_data->>'birth_date', '')), '')::date,
    new.email
  )
  on conflict (id) do update set
    full_name  = coalesce(excluded.full_name, profiles.full_name),
    birth_date = coalesce(excluded.birth_date, profiles.birth_date),
    email      = coalesce(nullif(excluded.email, ''), profiles.email);
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
