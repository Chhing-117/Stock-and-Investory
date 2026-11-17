# StockFlow — Inventory & Stock Management System (Phase 2)

A Flask application extending the **Phase 1 project**. Phase 2 adds working management pages for products, categories, suppliers, customers and admin-controlled staff accounts. It uses Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF and Bootstrap 5. This is **not yet a full POS/inventory ledger**.

## Current functionality

- Authentication: login, POST-only CSRF-protected logout, password hashes, admin/staff roles, create/edit/deactivate staff from Users (admin only); an admin cannot deactivate/demote their own account.
- Catalog: searchable, paginated product/category/supplier/customer tables; create and edit forms; category deletion blocked when products use it; supplier/customer deactivate/reactivate; product archive/restore.
- Products: unique SKU/barcode, category and optional supplier, Decimal money fields, validated nonnegative prices/threshold, default zero stock, DB nonnegative-stock check, description, unit, active state, timestamps. Search by name/SKU/barcode; category and stock filters.
- Dashboard: live totals from the database for users, products, categories, suppliers, customers, and low-stock products.
- Seed command for eight example categories.
- Phase 2 pytest tests under `tests/` (require installation of dependencies to run).

**Scope limits:** Product quantity is intentionally **not editable in Phase 2** because purchases, sales, adjustments, atomic stock updates and movement history arrive in Phase 3. No sample stock should be invented. Image uploads require persistent production storage; Supabase Storage integration is not yet included. Purchase history, sales history, reports, analytics, and comprehensive audit trails will follow in later phases.

## Windows PowerShell + PyCharm

1. Extract `Inventory_Stock_Flask_Phase2.zip` and open the `inventory_stock_system` folder in PyCharm.
2. In the PyCharm terminal:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

3. Edit `.env` and set `SECRET_KEY=` to the generated value. Do not commit `.env` to Git. If upgrading an existing Phase 1 installation, **keep your original `.env`, `instance/inventory.db` and `migrations/` directory** rather than overwriting them. Back up your database first.
4. Set Flask's application entry point:

```powershell
$env:FLASK_APP = "run.py"
```

5. **New installation** (no migrations yet):

```powershell
python -m flask db init
python -m flask db migrate -m "phase2 initial tables"
python -m flask db upgrade
python -m flask seed-categories
python -m flask create-admin
python run.py
```

6. **Upgrading a Phase 1 installation**: copy Phase 2 `app/`, `tests/`, and configuration/code files over your existing project while preserving the old SQLite database and `migrations/`. Then run:

```powershell
python -m flask db migrate -m "add phase2 catalog tables"
python -m flask db upgrade
python -m flask seed-categories
python run.py
```

Do **not** run `db init` again if your Phase 1 project already has a `migrations/` directory. Review the generated migration before `db upgrade`; never substitute `db.create_all()` for production migrations. If a previously generated SQLite DB is outside `instance/`, check the `SQLALCHEMY_DATABASE_URI` setting and ensure you are using the correct database.

7. Open http://127.0.0.1:5000, log in as your admin, choose **Categories** then **Products**, create a supplier and customer, and test user creation in **Users**.
8. Test:

```powershell
python -m pytest -q
```

If activation is blocked by PowerShell execution policy, run `.\.venv\Scripts\python.exe` directly in place of `python` rather than changing a system-wide policy.

## Main routes

| URL | Purpose | Access |
| --- | --- | --- |
| `/` | Welcome | Public |
| `/auth/login` | Login | Public |
| `/dashboard` | Live summary | Logged-in |
| `/products` | Search and list | Logged-in |
| `/products/new` | Add | Admin |
| `/products/<id>/edit` | Edit | Admin |
| `/products/<id>/archive` | POST archive/restore | Admin |
| `/categories` | List | Logged-in |
| `/categories/new` | Add | Admin |
| `/categories/<id>/edit` | Edit | Admin |
| `/categories/<id>/delete` | POST safe delete | Admin |
| `/suppliers` | List | Logged-in |
| `/suppliers/new` | Add | Admin |
| `/suppliers/<id>/edit` | Edit | Admin |
| `/suppliers/<id>/deactivate` | POST toggle | Admin |
| `/customers` | List | Logged-in |
| `/customers/new` | Add | Admin |
| `/customers/<id>/edit` | Edit | Admin |
| `/customers/<id>/deactivate` | POST toggle | Admin |
| `/users/` | Manage users | Admin |
| `/users/new` | Add admin or staff | Admin |
| `/users/<id>/edit` | Edit password, role, active | Admin |

## Project structure

```
inventory_stock_system/
├── app/
│   ├── __init__.py          # Factory, blueprints, CLI commands
│   ├── extensions.py        # db, migrate, login, CSRF
│   ├── models.py            # User, Category, Product, Supplier, Customer
│   ├── routes/
│   │   ├── auth.py          # Login/logout
│   │   ├── common.py        # Admin permission decorator
│   │   ├── main.py          # Landing page/dashboard
│   │   ├── catalog.py       # Catalog CRUD
│   │   └── users.py         # Admin staff management
│   ├── templates/
│   │   ├── catalog/         # List and form templates
│   │   ├── users/           # User list
│   │   ├── auth/            # Login
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── index.html
│   │   └── error.html
│   └── static/css, js/
├── api/index.py              # Serverless entrypoint
├── tests/                    # Pytest
├── app.py                    # Root Vercel Flask app entrypoint
├── run.py                    # Local runner
├── config.py                 # SQLite/PostgreSQL config
├── requirements.txt
├── vercel.json
├── .env.example
└── README.md
```

## Database relationships and migrations

`categories (1) -> (many) products`; `suppliers (1) -> (many) products` (optional relationship). Users and customers are independent until purchases and sales are implemented in Phase 3. Every product must reference an existing category; removing a category with linked products is blocked. Monetary amounts use SQL `NUMERIC(12,2)` and Python `Decimal`, never float columns. `Product.stock_quantity` is initially zero and is never modified by a Phase 2 form.

SQLite is your local database; Supabase PostgreSQL is separate and **does not automatically synchronize**. `DATABASE_URL` switches the app to PostgreSQL, and `DB_TRANSACTION_POOLER=1` enables pooler-friendly configuration for serverless deployment. The UI has not been tested against production Supabase/Vercel; Phase 6 will cover that workflow and storage integration.

## Troubleshooting

- **`No module named flask`**: activate `.venv` and install requirements using the same interpreter as PyCharm.
- **`no such table: categories`**: run Flask-Migrate commands and confirm the SQLite file path.
- **`Target database is not up to date`**: run `python -m flask db upgrade` first, then retry creating a new migration.
- **`Can't locate revision`**: preserve the migrations folder from the database's originating project; do not delete migration history.
- **Duplicate SKU/barcode/category**: choose a unique value.
- **403 Forbidden**: staff users may browse catalog but cannot make Phase 2 changes. Admin can edit their roles in Users.
- **Product stock zero**: intentional. The Phase 3 stock transaction ledger will handle changes.

## Next stage

Phase 3: purchase items, sale items, POS cart, customer/supplier transaction history, transactional stock movements, prevention of overselling and printable receipts.

## Phase 2 UI refresh (login + sidebar)

This package retains StockFlow's original blue `#2563EB`, purple `#7C3AED`, dark navy `#0F172A`, and light gray `#F8FAFC` colors, along with its existing system font. The app now shows a responsive left sidebar on signed-in pages and a redesigned sign-in layout. No database models or Flask routes were changed for this UI refresh.

### Updating an existing Phase 2 installation

1. Back up your current project, especially `.env`, `instance/inventory.db`, and `migrations/`.
2. Replace only these files from the ZIP: `app/templates/base.html`, `app/templates/auth/login.html`, `app/templates/index.html`, `app/static/css/style.css`, `app/static/js/app.js`.
3. Restart with `python run.py`, then hard-refresh the browser with `Ctrl+F5` if old styles are cached.
4. Check `/auth/login`, sign in and check `/dashboard`, then test the sidebar on desktop and phone size.

The existing admin/staff permissions, product/category/supplier/customer routes, CSRF-protected login and logout, and database migration history remain unchanged. **No new migration is needed for these template/CSS/JS changes.**


## Add demo catalog records (20 of each)

After database migrations are applied, run:

```powershell
$env:FLASK_APP = "run.py"
python -m flask db upgrade
python -m flask seed-demo
```

Creates **20 sample products, 20 suppliers, 20 customers** and up to 8 categories. Running the command again skips existing demo records (based on product SKU and demo email). Existing data is not deleted. Sample product stock is **0**, because audited stock-in transactions are part of Phase 3. This command writes to whichever database the app is configured to use; avoid using it on a production database.
