# 모비딕 테니스 대회 관리 시스템

**MOAI (Mobydick tennis club Open Arena Information system)**  
테니스 대회 점수 기록, 순위 계산, 시즌 랭킹을 관리하는 웹앱입니다.  
기술 스택: **Streamlit + Supabase**

---

## 문서 안내

- 시작/개요: `README.md` (현재 문서)
- 배포 가이드: [`README_DEPLOY.md`](README_DEPLOY.md)
- 운영 가이드(권한/유저/마이그레이션/keepalive): [`README_OPERATIONS.md`](README_OPERATIONS.md)

---

## 빠른 시작

### 1) Supabase 준비

1. [supabase.com](https://supabase.com)에서 프로젝트 생성
2. SQL Editor에서 `schema.sql` 실행
3. 기존 DB 업데이트가 필요하면 `migrations/up_to_date.sql` 실행
4. `SUPABASE_URL`, `SUPABASE_KEY` 값 확보

### 2) 로컬 시크릿 설정

`.streamlit/secrets.toml` 파일에 아래 값 입력:

```toml
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_KEY = "<anon-or-publishable-key>"

# 선택: 비밀번호 재설정 후 돌아올 주소
PASSWORD_RESET_REDIRECT_URL = "http://localhost:8501/"
```

### 3) 로컬 실행

```bash
uv run streamlit run app.py
```

---

## 배포/운영 핵심

- Streamlit 배포 절차는 [`README_DEPLOY.md`](README_DEPLOY.md) 참고
- 권한 정책(게스트/유저/관리자/마스터), 계정 운영, 비밀번호 재설정은 [`README_OPERATIONS.md`](README_OPERATIONS.md) 참고
- 무료 플랜 sleep/pause 대응용 keepalive 워크플로:
  - `.github/workflows/supabase-keepalive.yml`
  - `.github/workflows/streamlit-keepalive.yml`

---

## 프로젝트 구조

```text
mobydick-tennis/
├── app.py
├── auth.py
├── db.py
├── schema.sql
├── migrations/
├── pages/
├── logic/
├── .github/workflows/
└── .streamlit/
```
