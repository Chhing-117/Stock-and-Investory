# Deploy StockFlow on Vercel + Supabase (November 2026)

This package is based on the **Phase 5 ZIP**, not a new application. It keeps the
Phase 5 routes, templates, sidebar, login, chart assets, and business logic.
**It does not automatically upload your SQLite business data to Supabase.**

## 0. Local verification and backup

In PyCharm PowerShell, from the directory containing `requirements.txt`:

```powershell
Copy-Item .env ..\stockflow-env-backup -ErrorAction SilentlyContinue
Copy-Item instance\inventory.db ..\inventory-phase5-backup.db
Copy-Item migrations ..\migrations-phase5-backup -Recurse
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:FLASK_APP = 'run.py'
python -m pytest -q
python run.py
```

Existing users, products, suppliers and transactions should remain in your existing
local SQLite database. Do **not** replace `.env`, `instance/`, or `migrations/`
when applying the new source over your local project.

## 1. Create a Supabase database

1. Visit https://supabase.com/dashboard and create a project.
2. Store its database password in your password manager.
3. In **Connect**, choose the **Transaction pooler**, port `6543`, for Vercel.
4. Copy the exact database URI from Supabase. Do not fabricate the hostname.
5. The connection URL normally starts with `postgresql://` and is converted
   automatically by `config.py` to `postgresql+psycopg://`.
6. If adding the password to the URI, URL-encode special characters in it.

Typical URI SHAPE ONLY (not a valid hostname or real credential):

`postgresql://postgres.<project-ref>:<url-encoded-password>@<pooler-host>:6543/postgres`

Set `DB_TRANSACTION_POOLER=1` in your production configuration. This configures
SQLAlchemy `NullPool`, TLS, and disables psycopg automatic prepared statements.
For database migrations, the **session pooler** (or direct database endpoint if
reachable) can be preferable. Use a trusted development machine or CI job; do not
run migrations during every web request or Vercel build.

## 2. Create production tables (schema, not data)

IMPORTANT: Production database is not your local SQLite. Make sure you have your
original Phase 1–5 `migrations/` directory, with the earlier migration revisions.
This ZIP intentionally does not invent historical migrations.

In a separate PowerShell terminal/session (do not overwrite your local `.env`):

```powershell
$env:APP_ENV = 'production'
$env:SECRET_KEY = '<your-strong-unique-secret>'
$env:DATABASE_URL = '<supabase-session-pooler-or-direct-URI>'
$env:DB_TRANSACTION_POOLER = '0'
$env:FLASK_APP = 'run.py'
python -m flask db current
python -m flask db upgrade
python -m flask db current
```

If your existing `migrations/` folder is missing, do NOT blindly use
`flask db stamp head` or `db.create_all()` on a database with records. Restore the
migration history, or prepare a carefully reviewed initial migration for an empty DB.
The production DB will initially be empty until you create an admin or import data.

Create a first production admin using an interactive terminal on your trusted
computer, with `DATABASE_URL` set to production and `FLASK_APP=run.py`:

```powershell
python -m flask create-admin
```

Never run `seed-demo` in the production database containing real business data.
Clear transient session environment variables after the migration session.

## 3. Push project to GitHub

Create a private repository for your application. Never commit `.env`, SQLite DB,
migrations backup files, passwords or database dumps. From project root:

```powershell
git init
git add .
git status
git commit -m 'StockFlow Phase 6 production deployment'
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git push -u origin main
```

`git remote ...` uses YOUR OWN repository URL. Keep the checked-in
`migrations/` folder if your existing application already has migrations:
Alembic migration scripts are source code and should normally be versioned.

## 4. Import in Vercel

1. Go to https://vercel.com/new and import your GitHub repository.
2. Select the `inventory_stock_system` directory as **Root Directory** if your
   repository includes its parent folder; otherwise use `.`.
3. Framework detection should find Flask via root `app.py` and `requirements.txt`.
   No custom build command or legacy `@vercel/python` rewrites are required.
4. Set **Production** environment variables:

   - `APP_ENV=production`
   - `SECRET_KEY=<a newly generated secret of at least 32 characters>`
   - `DATABASE_URL=<the transaction pooler URI from Supabase Connect>`
   - `DB_TRANSACTION_POOLER=1`
   - `FLASK_DEBUG=0`

   Vercel sets `VERCEL=1` automatically when running on its platform.
   Use separate database credentials / projects for Preview and Production to
   avoid preview deployments modifying production data. Do not blindly share
   production secrets with Preview environments.

5. Choose a Vercel project region near your Supabase project region if feasible.
6. Deploy. Visit `/health` and expect `{"status":"ok"}` HTTP 200.
7. Open `/auth/login`, sign in as the admin created in the PRODUCTION database,
   and test your dashboard, products, purchases, sales and reports.

Vercel serves your static assets from `public/static/` at `/static/` while Flask
serves the same files from `app/static/` during local development. Keep the two
folders synchronized when changing CSS or JS. The current bundle includes both.

## 5. Verify and troubleshoot

- HTTP 500 on startup: verify DATABASE_URL, pooler hostname, SECRET_KEY and Vercel logs.
- `could not translate host`: check actual Supabase pooler region/host.
- `connection refused` or IPv6 failure: use transaction pooler URI rather than
  direct host on hosts without IPv6.
- `prepared statement` error: set `DB_TRANSACTION_POOLER=1` and confirm the
  psycopg driver is in use.
- Missing tables: use `flask db upgrade` against the production DB (off Vercel).
- No products: local SQLite rows never replicate automatically to PostgreSQL.
- Lost static styles: verify `public/static/css/style.css` was deployed.
- No admin login: create the admin in PRODUCTION, not only SQLite.

## 6. Production checklist before accepting customers

- All tests pass against test DB and staging PostgreSQL.
- Admin accounts have strong, unique passwords and least-privilege roles.
- Login rate limiting and brute-force protection are added and tested.
- Database backups / restore exercises are configured.
- Payment status for KHQR remains a manual record, NOT an actual payment API.
- Product image uploads require persistent object storage, not Vercel files.
- Plan a reviewed migration/import if transferring existing local SQLite data.
- Confirm CSP, HTTPS, cookies, audit trail and pagination in production.

## Authoritative references (checked Nov 2026)

- https://vercel.com/kb/guide/ship-a-flask-app-on-vercel
- https://vercel.com/docs/frameworks/backend/flask
- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/kb/troubleshooting/using-sqlalchemy-with-supabase-FUqebT
- https://supabase.com/kb/troubleshooting/disabling-prepared-statements-qL8lEL
