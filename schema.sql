-- 모비딕 테니스 Supabase 스키마
-- Supabase 대시보드 > SQL Editor에서 이 파일 전체를 붙여넣고 실행
-- (기존 테이블이 있다면 drop 후 재생성됩니다)

drop table if exists scoring_config cascade;
drop table if exists extra_scores cascade;
drop table if exists matches cascade;
drop table if exists tournament_players cascade;
drop table if exists players cascade;
drop table if exists tournaments cascade;

-- 대회 테이블
create table tournaments (
  id bigint generated always as identity primary key,
  name text not null,
  date date,
  description text,
  is_finished boolean default false,
  is_legacy boolean default false,     -- 레거시 모드: 대진/경기 없이 순위만 기록
  created_at timestamptz default now()
);

-- 레거시 대회 순위 기록 (1~3위만 저장)
create table legacy_results (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  rank integer not null,               -- 1, 2, 3
  player_name text not null,
  unique(tournament_id, rank)
);

-- 전체 선수 풀 (대회에 종속되지 않음)
create table players (
  id bigint generated always as identity primary key,
  name text not null unique,   -- 이름은 전체에서 유일
  created_at timestamptz default now()
);

-- 대회별 선수 배정 (선수 풀에서 선택 + 대회 내 역할 설정)
create table tournament_players (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  player_id bigint references players(id) on delete cascade,
  title text,                          -- 대회 내 직함 (시드1, 일반2 등)
  is_wildcard boolean default false,   -- 이 대회에서 와일드카드 여부
  unique(tournament_id, player_id)     -- 한 대회에 같은 선수 중복 배정 불가
);

-- 경기 기록 테이블
create table matches (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  round text,
  court text,
  team1_player1 text,
  team1_player2 text,
  team2_player1 text,
  team2_player2 text,
  team1_score integer,
  team2_score integer,
  match_type text,
  created_at timestamptz default now()
);

-- 추가 점수 테이블
create table extra_scores (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  player_name text not null,
  score integer default 0,
  note text,
  created_at timestamptz default now()
);

-- 점수 설정 테이블 (대회별)
create table scoring_config (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  item_key text not null,
  label text not null,
  is_active boolean default true,
  score_value integer default 0,
  unique(tournament_id, item_key)
);
