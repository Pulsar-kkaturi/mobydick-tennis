# 모비딕 테니스 대회 관리 시스템

테니스 대회 점수 기록, 순위 계산, 시즌 랭킹을 관리하는 웹앱입니다.  
Streamlit + Supabase 기반으로 만들어졌으며, Streamlit Cloud를 통해 무료로 배포할 수 있습니다.

---

## 로그인 & 접근 권한

- **게스트(비로그인):** 대시보드, 순위표, 통계만 열람
- **일반 유저:** 앱에서 **회원가입** 후 로그인 → 선수관리, 대회관리(대회설정/대진표/경기입력)
- **관리자:** **마스터가 일반 유저 중에서 승급** (앱 **운영 → 유저 관리**에서 role을 `관리자`로 변경). 대회 승인 등 운영 탭의 **대회 승인**까지 사용 가능
- **마스터:** 유저 관리(역할 변경·삭제) + 관리자와 동일한 운영 권한. **최초 1명만** 아래처럼 `master`로 지정하면 됨

### 일반 유저 회원가입 (앱)

1. 사이드바 **로그인 / 회원가입** → **회원가입** 탭
2. **이름, 이메일(ID), 비밀번호(영문+숫자 8자 이상), 생년월일** 입력
3. 가입 후 로그인 (이메일 확인을 켜 둔 프로젝트는 메일 링크 확인 후 로그인)

### 관리자 지정 (마스터 전용)

별도로 Supabase에 “관리자 계정”을 만들 필요는 없습니다.  
**앱에서 회원가입한 사람**을 마스터가 **운영 → 유저 관리**에서 role을 **`관리자(admin)`** 로 바꾸면 됩니다.

### 최초 마스터 1명만 만들기

서비스를 처음 켤 때는 **마스터가 0명**이라 앱에서 유저 관리를 열 수 없습니다. 아래 중 하나로 **한 명만** `master`로 올리세요.

**방법 A — 본인이 앱에서 먼저 회원가입**

1. 앱에서 회원가입 후 로그인 (이때는 `user` 권한)
2. Supabase **Authentication → Users**에서 본인 계정의 **UUID** 복사
3. SQL Editor에서 실행:

```sql
insert into profiles (id, role, full_name)
values ('여기에-본인-uuid', 'master', '운영자')
on conflict (id) do update set role = 'master', full_name = coalesce(excluded.full_name, profiles.full_name);
```

4. 앱에서 로그아웃 후 다시 로그인하면 **운영 → 유저 관리**가 보입니다.

**방법 B — Supabase에서 사용자 추가**

1. **Authentication → Users → Add user**로 이메일/비밀번호 생성
2. 위와 동일하게 SQL로 해당 UUID에 `role = 'master'` 지정

### Supabase Auth 권장 설정 (클럽용)

- **Authentication → Providers → Email**  
  - 빠른 운영을 위해 **Confirm email** 을 끄면 가입 직후 바로 로그인됩니다.  
  - 가입 직후 `profiles` 안정화를 위해 `migrations/up_to_date.sql` 실행을 권장합니다 (트리거 포함).

### 기존 DB 마이그레이션

**`migrations/up_to_date.sql` 한 파일만** SQL Editor에서 실행하면 됩니다. (`migrations/README.md` 참고)

---

## 시작하기 전에: Supabase 설정

Supabase는 무료 클라우드 PostgreSQL DB입니다. 앱의 모든 데이터가 여기에 저장됩니다.

### 1단계 — Supabase 프로젝트 만들기

1. [supabase.com](https://supabase.com) 접속 후 GitHub 계정으로 로그인
2. **New Project** 클릭
3. 프로젝트 이름, 비밀번호, 지역(가까운 곳 선택 권장: `Northeast Asia`) 입력 후 생성
4. 프로젝트 생성까지 1~2분 소요

### 2단계 — 테이블 생성 (schema.sql 실행)

1. Supabase 대시보드 좌측 메뉴에서 **SQL Editor** 클릭
2. `schema.sql` 파일 전체 내용을 복사해서 붙여넣기
3. **Run** 버튼 클릭
4. 하단에 `Success` 메시지 확인

### 3단계 — API 키 복사

1. 좌측 메뉴 **Project Settings → API** 클릭
2. 아래 두 값을 복사

| 항목 | 위치 |
|---|---|
| `SUPABASE_URL` | Project URL 항목 (DATA API 안에 있음) |
| `SUPABASE_KEY` | API KEY > Secret keys (service_role 키 아님!) |

### 4단계 — secrets.toml에 붙여넣기

`.streamlit/secrets.toml` 파일을 열고 복사한 값으로 교체:

```toml
SUPABASE_URL = "https://abcdefghijklmn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

> 이 파일은 `.gitignore`에 등록되어 있어 GitHub에 올라가지 않습니다.
> 따라서 없을 시 파일 생성 필요.

---

## 로컬 실행

프로젝트 폴더에서 아래 명령어 실행:

```bash
uv run streamlit run app.py
```

브라우저가 자동으로 열리며 `http://localhost:8501` 에서 앱이 실행됩니다.

---

## Streamlit Cloud 배포 (무료)

팀원들이 어디서든 접속할 수 있게 배포하려면 아래 단계를 따르세요.

> **주의:** Streamlit Cloud 무료 플랜은 **Public 저장소만** 지원합니다.  
> GitHub 저장소 Settings → Danger Zone → **Change visibility → Public** 으로 변경해 주세요.  
> `.streamlit/secrets.toml`은 `.gitignore`에 등록되어 있어 키가 노출되지 않으니 안심하세요.

### 1단계 — GitHub에 코드 올리기

```bash
# 프로젝트 폴더에서
git init
git add .
git commit -m "초기 커밋"
```

GitHub에서 새 저장소(Public)를 만들고:

```bash
git remote add origin https://github.com/본인계정/저장소이름.git
git push -u origin main
```

### 2단계 — Streamlit Cloud 연결

1. [share.streamlit.io](https://share.streamlit.io) 접속 후 GitHub 계정으로 로그인
2. **New app** 클릭
3. 아래와 같이 입력:

| 항목 | 입력값 |
|---|---|
| Repository | `본인계정/mobydick-tennis` |
| Branch | `main` |
| Main file path | `app.py` |

4. **Deploy** 클릭 → 1~2분 후 배포 완료

### 3단계 — Secrets 설정

배포 환경에도 Supabase 키를 알려줘야 합니다.  
(로컬의 `secrets.toml`은 GitHub에 올라가지 않으므로 별도로 입력해야 합니다)

1. 배포된 앱 우측 상단 **⋮ → Settings → Secrets** 클릭
2. 아래 내용을 그대로 붙여넣기 (본인 값으로 교체):

```toml
SUPABASE_URL = "https://xxxxxxxx.supabase.co"
SUPABASE_KEY = "sb_secret_..."
```

3. **Save** 클릭 → 앱 자동 재시작

### 이후 업데이트 방법

코드를 수정한 뒤 GitHub에 push하면 Streamlit Cloud가 자동으로 감지해서 재배포합니다.  
데이터(Supabase DB)는 재배포와 무관하게 유지됩니다.

```bash
git add .
git commit -m "수정 내용"
git push
# → Streamlit Cloud 자동 재배포 (약 1~2분)
```

---

## 프로젝트 구조

```
mobydick-tennis/
├── app.py                  # 홈: 시즌 랭킹 + 대회 관리
├── db.py                   # Supabase 연결 및 모든 DB 함수
├── schema.sql              # Supabase 테이블 생성 SQL (최초 1회 또는 전체 리셋 시)
├── migrations/             # up_to_date.sql (기존 DB 패치) + README
├── requirements.txt        # Python 패키지 목록
├── pages/
│   ├── 1_선수관리.py        # 선수 등록/수정/삭제 + 엑셀 import
│   ├── 2_대진표.py          # 대진 자동 생성 / 수동 추가
│   ├── 3_경기입력.py        # 경기 결과 입력
│   ├── 4_순위표.py          # 실시간 순위 + 엑셀 내보내기
│   ├── 5_통계.py            # 차트 시각화
│   └── 6_점수설정.py        # 점수 계산 방식 커스텀
├── logic/
│   ├── scoring.py          # 점수 계산 + 시즌 랭킹 로직
│   └── schedule.py         # 라운드 로빈 대진 생성 로직
├── Assets/
│   └── *.xlsx              # 기존 엑셀 파일 (import용)
└── .streamlit/
    ├── config.toml         # 테마 설정
    └── secrets.toml        # Supabase 키 (git 제외)
```

---
