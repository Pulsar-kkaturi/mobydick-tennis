-- 모비딕 테니스 Supabase 스키마
-- Supabase 대시보드 > SQL Editor에서 이 파일 전체를 붙여넣고 실행

drop table if exists scoring_config cascade;
drop table if exists extra_scores cascade;
drop table if exists matches cascade;
drop table if exists tournament_players cascade;
drop table if exists players cascade;
drop table if exists tournaments cascade;
drop table if exists profiles cascade;

-- 사용자 프로필 (Supabase Auth와 연결)
-- auth.users 테이블의 id를 참조
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role text not null default 'user',  -- master / admin / user
  full_name text,                       -- 회원가입 시 입력한 이름
  birth_date date,                      -- 생년월일
  email text                            -- 로그인 이메일 (운영 유저관리 표시용, auth.users 와 동기)
);

-- 대회 테이블
create table tournaments (
  id bigint generated always as identity primary key,
  name text not null,
  date date,
  description text,
  is_finished boolean default false,
  is_legacy boolean default false,
  is_approved boolean default false,   -- 관리자 승인 여부 (시즌 랭킹 반영 조건)
  created_at timestamptz default now()
);

-- 레거시 대회 순위 기록 (공동 순위 지원: 같은 rank에 최대 2명)
create table legacy_results (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  rank integer not null,
  player_name text not null,
  unique(tournament_id, rank, player_name)  -- 같은 순위에 같은 선수 중복 방지
);

-- 전체 선수 풀
create table players (
  id bigint generated always as identity primary key,
  name text not null unique,
  gender text,        -- '남' / '여' (빈칸 허용)
  play_style text,    -- 4가지 스타일 중 하나 (빈칸 허용)
  created_at timestamptz default now()
);

-- 대회별 선수 배정
create table tournament_players (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  player_id bigint references players(id) on delete cascade,
  title text,
  is_wildcard boolean default false,
  unique(tournament_id, player_id)
);

-- 경기 기록
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

-- 추가 점수
create table extra_scores (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  player_name text not null,
  score integer default 0,
  note text,
  created_at timestamptz default now()
);

-- 점수 설정 (대회별)
-- 앱이 대회 최초 조회 시 DEFAULT_SCORING_CONFIG(db.py) 기준으로 자동 삽입
-- 표준 item_key 목록:
--   win_score        승리
--   draw_score       무승부
--   loss_score       패배
--   play_bonus       경기 참여
--   score_diff       게임 득실차
--   wc_self_bonus    WC 본인 보너스
--   wc_partner_bonus WC 파트너 보너스 (승리 시)
--   extra_score      추가 점수 (경기입력 페이지에서 입력, 점수설정 UI에서는 숨김)
create table scoring_config (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  item_key text not null,
  label text not null,
  is_active boolean default true,
  score_value integer default 0,
  unique(tournament_id, item_key)
);
