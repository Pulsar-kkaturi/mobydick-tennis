# README_OPERATIONS

서비스 운영 관점에서 필요한 설정/정책/점검 항목을 정리한 문서입니다.

---

## 권한 체계

- 게스트(비로그인): 대시보드/순위/통계 조회
- 일반 유저: 회원가입 후 로그인, 선수관리/대회관리 사용
- 관리자: 운영 기능 일부 사용(승인 등)
- 마스터: 유저 역할 변경/삭제 포함 전체 운영 권한

---

## 최초 마스터 지정

1. 앱에서 본인 계정 회원가입
2. Supabase Authentication -> Users에서 UUID 확인
3. SQL Editor에서 아래 실행

```sql
insert into profiles (id, role, full_name)
values ('여기에-본인-uuid', 'master', '운영자')
on conflict (id) do update
set role = 'master',
    full_name = coalesce(excluded.full_name, profiles.full_name);
```

4. 앱 재로그인 후 운영 메뉴 확인

---

## 비밀번호 재설정 운영

- 앱의 비밀번호 재설정 탭 사용 가능
- OTP 스타일 코드를 메일에 표시하려면 Supabase Magic Link 템플릿에 `{{ .Token }}` 포함 필요
- 운영자가 직접 처리하려면 Supabase Authentication -> Users에서 사용자 비밀번호 재설정 사용

---

## Supabase Auth 권장 설정

- Confirm email: 클럽 운영에서는 보통 **비활성화 권장**
  - 가입 즉시 로그인 가능
  - 불필요한 메일 발송 감소
- 비밀번호 재설정 기능은 유지

---

## 마이그레이션

- 신규/리셋: `schema.sql`
- 기존 DB 패치: `migrations/up_to_date.sql`

필요 시 Supabase SQL Editor에서 순서대로 적용하세요.

---

## 무료 플랜 keepalive 운영

무료 플랜은 비활성 시 sleep/pause가 발생할 수 있습니다.  
현재 저장소는 GitHub Actions keepalive를 사용합니다.

### Supabase keepalive

- 파일: `.github/workflows/supabase-keepalive.yml`
- Secret: `SUPABASE_URL`
- 응답 코드 처리:
  - `200`: 정상
  - `401`: 인증 요구지만 엔드포인트 도달 성공으로 간주

### Streamlit keepalive

- 파일: `.github/workflows/streamlit-keepalive.yml`
- Secret: `STREAMLIT_APP_URL` (`https://<your-app>.streamlit.app`)
- `2xx~3xx` 응답이면 성공

### 스케줄 확인

- cron은 **UTC 기준**입니다.
- 예: `0 0 * * 1,4` = 월/목 00:00 UTC = 월/목 09:00 KST

---

## 운영 점검 체크리스트

- 배포 앱 접속/로그인 정상 동작
- Supabase 프로젝트 상태(active/paused) 확인
- Actions 최근 실행 성공 여부 확인
- 사용자 role(`user/admin/master`) 의도대로 반영 확인
