# README_DEPLOY

Streamlit Cloud 배포용 절차를 정리한 문서입니다.

---

## 1) GitHub 준비

프로젝트 루트에서:

```bash
git add .
git commit -m "deploy setup"
git push
```

> Streamlit Community Cloud 정책상 저장소 가시성/플랜 조건은 수시로 바뀔 수 있으니, 배포 시점에 Streamlit 안내를 함께 확인하세요.

---

## 2) Streamlit Cloud 앱 생성

1. [share.streamlit.io](https://share.streamlit.io) 접속
2. **New app** 클릭
3. 아래 정보 입력
   - Repository: `본인계정/저장소명`
   - Branch: `main` (또는 배포 브랜치)
   - Main file path: `app.py`
4. **Deploy** 클릭

---

## 3) 배포 시크릿 설정

배포 앱 우측 상단 **Settings -> Secrets** 에 아래 값 입력:

```toml
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_KEY = "<anon-or-publishable-key>"
PASSWORD_RESET_REDIRECT_URL = "https://<your-app>.streamlit.app/"
```

`PASSWORD_RESET_REDIRECT_URL` 사용 시, Supabase의 URL Configuration에도 동일 URL이 등록되어 있어야 합니다.

---

## 4) 업데이트 배포

코드 변경 후 push하면 Streamlit Cloud가 자동 재배포합니다.

```bash
git add .
git commit -m "update app"
git push
```

---

## 5) keepalive (선택)

무료 플랜에서 sleep/pause를 줄이려면 GitHub Actions keepalive를 함께 사용하세요.

- Supabase: `.github/workflows/supabase-keepalive.yml`
- Streamlit: `.github/workflows/streamlit-keepalive.yml`

운영 상세는 [`README_OPERATIONS.md`](README_OPERATIONS.md)를 참고하세요.
