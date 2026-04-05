# 모비딕 테니스 점수 관리 시스템

테니스 대회 점수 기록, 순위 계산, 시즌 랭킹을 관리하는 웹앱입니다.  
Streamlit + Supabase 기반으로 만들어졌으며, Streamlit Cloud를 통해 무료로 배포할 수 있습니다.

---

## 기능 요약

- **대회 관리** — 여러 대회를 생성하고 독립적으로 관리
- **선수 관리** — 대회별 선수 등록, 와일드카드 설정, 기존 엑셀 파일에서 import
- **대진표** — 라운드 로빈 자동 생성 또는 수동 추가
- **경기 입력** — 점수 입력 즉시 순위에 반영
- **순위표** — 실시간 순위 계산, 엑셀 내보내기
- **통계** — 총점/승률/득실차/레이더 차트
- **점수 설정** — 프리셋 선택 + 항목별 ON/OFF 및 점수값 커스텀
- **시즌 랭킹** — 원하는 대회만 골라서 1위=3점/2위=2점/3위=1점 합산

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
| `SUPABASE_URL` | Project URL 항목 |
| `SUPABASE_KEY` | `anon` `public` 키 (service_role 키 아님!) |

### 4단계 — secrets.toml에 붙여넣기

`.streamlit/secrets.toml` 파일을 열고 복사한 값으로 교체:

```toml
SUPABASE_URL = "https://abcdefghijklmn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

> 이 파일은 `.gitignore`에 등록되어 있어 GitHub에 올라가지 않습니다.

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

## 처음 사용 순서

```
1. 홈 화면에서 대회 이름/날짜 입력 후 [대회 생성]
2. 선수 관리 페이지에서 선수 등록
   - 엑셀 파일에서 import 가능 (기존 파일 활용)
   - 와일드카드 선수는 체크박스로 설정
3. 대진표 페이지에서 [대진 자동 생성] 또는 수동으로 경기 추가
4. 경기 입력 페이지에서 라운드별 경기 결과 입력
5. 순위표 페이지에서 실시간 순위 확인 및 엑셀 내보내기
6. 여러 대회가 쌓이면 홈 화면 시즌 랭킹에서 통합 순위 확인
```

---

## 점수 계산 방식

점수 설정 페이지에서 언제든지 바꿀 수 있습니다.

### 프리셋 (빠른 전환)

| 프리셋 | 설명 |
|---|---|
| 현재 방식 (엑셀 기준) | 가중치 계산 (승리×100 + 참여×10 + 득실차×1 + WC보너스) |
| 승리수만 | 승리 횟수로만 순위 결정 |
| 득실차 포함 | 승리×100 + 득실차×1 |
| 승점제 (승3/무1/패0) | 축구식 승점 계산 |

### 항목별 세부 설정

| 항목 | 기본값 | 설명 |
|---|---|---|
| 경기 승리 보너스 | 100점 | 경기 이길 때마다 부여 |
| 경기 참여 점수 | 10점 | 경기에 나올 때마다 부여 |
| 게임 득실차 | 1점 | (득점 - 실점) × 1 |
| WC 본인 보너스 | 30점 | 와일드카드 선수에게 경기당 부여 |
| WC 파트너 보너스 | 5점 | WC와 파트너가 되어 이겼을 때, WC 본인과 파트너 모두에게 부여 |
| 추가 점수 | 0점 | 토너먼트 진출 보너스 등 수동 입력 |

### 시즌 랭킹 포인트

| 순위 | 포인트 |
|---|---|
| 1위 | 3점 |
| 2위 | 2점 |
| 3위 | 1점 |
| 4위 이하 | 0점 (랭킹 제외) |

---

## 프로젝트 구조

```
mobydick-tennis/
├── app.py                  # 홈: 시즌 랭킹 + 대회 관리
├── db.py                   # Supabase 연결 및 모든 DB 함수
├── schema.sql              # Supabase 테이블 생성 SQL (최초 1회 실행)
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

## 자주 묻는 것들

**Q. 앱을 재시작하면 데이터가 날아가나요?**  
아니요. 모든 데이터는 Supabase 클라우드 DB에 저장되므로 앱을 껐다 켜도 유지됩니다.

**Q. 여러 명이 동시에 접속해도 되나요?**  
됩니다. Supabase가 동시 접속을 처리하며, 저장 즉시 다른 사용자 화면에도 새로고침 시 반영됩니다.

**Q. 대회를 실수로 만들었는데 삭제하면 경기 기록도 사라지나요?**  
네. 대회 삭제 시 해당 대회의 선수/경기/점수 설정이 모두 함께 삭제됩니다. 홈 화면에서 삭제 버튼을 두 번 눌러야 실행됩니다.

**Q. 기존 엑셀 파일을 계속 써도 되나요?**  
선수 관리 페이지에서 기존 엑셀 파일을 업로드하면 '설정' 시트의 선수 명단을 자동으로 읽어와 등록할 수 있습니다.
