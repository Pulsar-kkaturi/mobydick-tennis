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

-- 3) legacy_results: 공동 순위 지원 — unique(tournament_id, rank) → unique(tournament_id, rank, player_name)
--    기존 제약 삭제 후 새 제약 추가 (데이터 손실 없음)
alter table legacy_results
  drop constraint if exists legacy_results_tournament_id_rank_key;

alter table legacy_results
  drop constraint if exists legacy_results_tournament_id_rank_player_name_key;

alter table legacy_results
  add constraint legacy_results_tournament_id_rank_player_name_key
  unique (tournament_id, rank, player_name);

-- 4) scoring_config: win_bonus → win_score 키 이름 통일
--    이미 win_score 가 존재하는 대회는 win_bonus 행을 삭제 (중복 방지)
delete from scoring_config
where item_key = 'win_bonus'
  and exists (
    select 1 from scoring_config sc2
    where sc2.tournament_id = scoring_config.tournament_id
      and sc2.item_key = 'win_score'
  );

--    win_score 가 없는 대회의 win_bonus 만 이름 변경
update scoring_config
set item_key = 'win_score', label = '승리'
where item_key = 'win_bonus';

-- 4) scoring_config 에 draw_score / loss_score 항목 추가
--    기존 대회에 항목이 없는 경우에만 삽입 (중복 방지)
insert into scoring_config (tournament_id, item_key, label, is_active, score_value)
select t.id, 'draw_score', '무승부', false, 0
from tournaments t
where not exists (
    select 1 from scoring_config sc
    where sc.tournament_id = t.id and sc.item_key = 'draw_score'
);

insert into scoring_config (tournament_id, item_key, label, is_active, score_value)
select t.id, 'loss_score', '패배', false, 0
from tournaments t
where not exists (
    select 1 from scoring_config sc
    where sc.tournament_id = t.id and sc.item_key = 'loss_score'
);
