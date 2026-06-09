# Update Log v1.02

## Date
- 2026-06-09 (KST)

## Scope
- Added tournament type system (`PREMIER` / `OPEN`)
- Updated season ranking points by tournament type
- Split tournament creation into a dedicated management page
- Expanded dashboard tournament/ranking visibility

## Changes

### 1) Tournament type added to DB
- Updated `tournaments` schema with:
  - `tournament_type text not null default 'OPEN'`
  - check constraint: `PREMIER`, `OPEN`
- Migration updated to:
  - add column for existing DBs
  - backfill existing rows to `OPEN`
  - enforce default/not-null/check safely

### 2) Data layer updates
- `db.create_tournament(...)` now stores `tournament_type`
- Added `db.update_tournament_meta(...)` to update:
  - name
  - date
  - description
  - tournament_type

### 3) New tournament management page
- Added `pages/8_대회생성.py`
- Moved "새 대회 만들기" form from dashboard to this page
- Tournament type selection is required in the form (`Premier` / `Open`)
- Included in app navigation under `대회관리`

### 4) Tournament settings update section
- Added "대회 정보" form to `pages/6_대회설정.py`
- Editable fields:
  - 대회 이름
  - 대회 날짜
  - 메모
  - 대회 등급(Premier/Open)
- Lock policy preserved:
  - if finished or approved, editing is disabled
  - requires 완료 취소 + 승인 취소 for updates

### 5) Season ranking points by type
- Updated `logic/scoring.py`:
  - `PREMIER`: 1위=5, 2위=3, 3위=2
  - `OPEN`: 1위=3, 2위=2, 3위=1
- Ranking detail now stores tournament type for UI aggregation

### 6) Dashboard enhancements
- Added year filter to `대회 목록` section
- Added tournament type badge (`Premier` / `Open`) in each tournament card
- Updated tournament card layout to a single-line summary style
  - `대회명/상태/등급/날짜 | 선수/경기 | 🥇 1위 | 완료처리 | 삭제`
- Removed 2nd/3rd display in cards and keep only 1st-place display for readability
- Expanded season table columns with type-specific medal counts:
  - `Premier🥇`, `Premier🥈`, `Premier🥉`
  - `Open🥇`, `Open🥈`, `Open🥉`
- Removed legacy total medal columns (`🥇`, `🥈`, `🥉`) from season table
- Updated ranking point caption to explain both point systems
- Default year for both season ranking and tournament list now auto-selects current system year

### 7) Page naming cleanup
- Renamed page file for tournament results:
  - `pages/4_순위표.py` -> `pages/4_대회결과.py`
- Renamed page file for tournament creation:
  - `pages/8_대회관리.py` -> `pages/8_대회생성.py`
- Updated references/messages accordingly
- Updated navigation labels:
  - `순위표` -> `대회 결과`
  - `대회관리`(생성 서브메뉴) -> `대회 생성`

## Validation checklist
- [x] Apply `migrations/up_to_date.sql` to existing DB
- [x] Confirm old tournaments are set to `OPEN`
- [x] Create new tournaments with both `Premier` and `Open` types
- [x] Verify lock behavior in `대회설정` (완료/승인 시 수정 불가)
- [x] Verify season point totals by type
- [x] Verify dashboard year filter + podium display
