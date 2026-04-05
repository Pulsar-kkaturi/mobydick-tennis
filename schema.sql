-- 모비딕 테니스 Supabase 스키마
-- Supabase 대시보드 > SQL Editor에서 이 파일 전체를 붙여넣고 실행

-- 대회 테이블
create table if not exists tournaments (
  id bigint generated always as identity primary key,
  name text not null,                  -- 대회 이름 (예: 2026 상반기)
  date date,                           -- 대회 날짜
  description text,                    -- 메모
  is_finished boolean default false,   -- 완료 여부
  created_at timestamptz default now()
);

-- 선수 테이블 (대회별 등록)
create table if not exists players (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  title text,                          -- 직함 (시드1, 일반2, WC1 등)
  name text not null,                  -- 이름
  is_wildcard boolean default false,   -- 와일드카드 여부 (보너스 대상)
  created_at timestamptz default now()
);

-- 경기 기록 테이블
create table if not exists matches (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  round text,                          -- 라운드 (R1, R2 ...)
  court text,                          -- 코트 (A, B ...)
  team1_player1 text,                  -- 팀1 선수1 이름
  team1_player2 text,                  -- 팀1 선수2 이름 (단식이면 null)
  team2_player1 text,
  team2_player2 text,
  team1_score integer,                 -- 팀1 게임 수
  team2_score integer,                 -- 팀2 게임 수
  match_type text,                     -- 경기 유형 설명
  created_at timestamptz default now()
);

-- 추가 점수 테이블 (토너먼트 보너스 등 수동 입력)
create table if not exists extra_scores (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  player_name text not null,
  score integer default 0,
  note text,                           -- 점수 사유 메모
  created_at timestamptz default now()
);

-- 점수 설정 테이블 (대회별 커스텀)
create table if not exists scoring_config (
  id bigint generated always as identity primary key,
  tournament_id bigint references tournaments(id) on delete cascade,
  item_key text not null,              -- 설정 항목 키 (예: win_bonus)
  label text not null,                 -- 표시 이름
  is_active boolean default true,      -- 활성화 여부
  score_value integer default 0,       -- 점수값
  unique(tournament_id, item_key)
);
