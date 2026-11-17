# Phase 5 — Security and automated testing

This package extends Phase 4 without requiring new tables or migrations.

## Safe upgrade (Windows PowerShell)
1. Stop Flask. Back up `.env`, `instance/inventory.db` and `migrations/` **outside the project folder**.
2. Extract this ZIP and copy source files into your existing project, preserving the three backed-up items.
3. Activate the original environment: `.\.venv\Scripts\Activate.ps1`
4. Install requirements: `python -m pip install -r requirements.txt`
5. Set `FLASK_APP`: `$env:FLASK_APP = "run.py"`
6. Apply existing migrations: `python -m flask db upgrade`
7. Run tests: `python -m pytest -q`
8. Start: `python run.py`

## What changed
- Deactivated users are signed out on their next request; admin-only pages enforce an active admin account.
- Security response headers, no-store on login/report pages, session duration, request-size and form-part limits.
- Server refuses default/weak `SECRET_KEY` in production (`VERCEL=1` or `FLASK_ENV=production`).
- Safer input bounds for search, stock adjustments and stock changes.
- New Phase 5 tests for CSRF, access control, deactivation, size limits and rollback.

## Important
- Do not commit `.env`, SQLite production data, or any password.
- Development demo account credentials must be replaced before production use.
- There is no distributed login rate limiter or login audit table in Phase 5. Add a trusted shared backend before deploying at scale.
- This does not make Vercel/Supabase deployment production-certified; test against a staging PostgreSQL instance.
- CSRF is disabled only in the original test fixture for legacy route tests; a separate Phase 5 test verifies CSRF enforcement when enabled.
- There is **no new database migration in Phase 5**.
