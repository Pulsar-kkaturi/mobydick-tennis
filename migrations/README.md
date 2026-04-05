# DB 마이그레이션

## 이미 테이블을 만들어 둔 경우 (데이터 유지)

**`up_to_date.sql` 파일 전체를 Supabase SQL Editor에서 한 번만 실행**하면 됩니다.

포함 내용:

1. `profiles`에 `full_name`, `birth_date` 컬럼 추가 (없을 때만)
2. `auth.users`에 사용자가 생기면 `profiles` 행을 자동으로 만드는 트리거  
   - 이메일 확인(링크)을 켜도/꺼도 동작에 문제 없음  
   - 앱 `회원가입`에서 넘기는 `full_name`, `birth_date`가 메타데이터로 들어감

별도로 `01` / `02` 나눠 실행할 필요 **없습니다.**

---

## 처음부터 DB를 새로 깔 때

프로젝트 루트의 **`schema.sql`** 전체 실행 (기존 테이블이 있으면 drop 되므로 **데이터 날아감**).

그다음에도 **`up_to_date.sql`은 실행해도 됩니다** (`if not exists` / `or replace` 로 중복 안전).

---

## 이메일 확인이 뭔지 (짧게)

Supabase 기본은 **메일로 온 링크를 클릭**하는 방식입니다. 앱에서 6자리 숫자 입력하는 건 기본이 아닙니다.

**Authentication → Providers → Email → Confirm email** 을 켜면 링크 인증이 켜집니다. 이 경우에도 위 트리거가 있으면 가입 직후 `profiles`가 비는 일을 줄일 수 있습니다.
