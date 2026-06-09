# Update Log v1.01

## Date
- 2026-06-09 (KST)

## Scope
- Added keepalive automation for Supabase and Streamlit using GitHub Actions cron workflows.

## Changes

### 1) Supabase keepalive workflow added
- File: `.github/workflows/supabase-keepalive.yml`
- Added scheduled job + manual trigger (`workflow_dispatch`)
- Uses `SUPABASE_URL` secret
- Keepalive endpoint: `/auth/v1/health`
- Response handling:
  - `200`: success
  - `401`: treated as reachable/accepted (auth required but endpoint is alive)
  - others: fail

### 2) Streamlit keepalive workflow added
- File: `.github/workflows/streamlit-keepalive.yml`
- Added scheduled job + manual trigger (`workflow_dispatch`)
- Uses `STREAMLIT_APP_URL` secret
- Accepts `2xx~3xx` as success
- Removed redirect-follow (`--location`) due to redirect loop issue (`curl: (47)`)

### 3) Documentation split
- `README.md` shortened to an index + quick start
- Added:
  - `README_DEPLOY.md`
  - `README_OPERATIONS.md`
- Keepalive operational notes moved to operations-focused docs

## Schedules (UTC / KST)
- Supabase: `0 0 * * 1,4` -> Mon/Thu 00:00 UTC (Mon/Thu 09:00 KST)
- Streamlit: `10 0 * * 2,5` -> Tue/Fri 00:10 UTC (Tue/Fri 09:10 KST)

## Secrets required
- `SUPABASE_URL`
- `STREAMLIT_APP_URL`

## Validation results
- Manual runs were executed in GitHub Actions.
- Supabase workflow: success
- Streamlit workflow: success

## Notes
- This log is intended to track each release/update.
- For future updates, create a new file under `docs/` as `update_log_vX.XX.md`.
