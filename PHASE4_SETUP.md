# Phase 4 — Dashboard, Reports & Analytics

This is the **complete Phase 4 source code**, built on the supplied Phase 3 project. It preserves the StockFlow sidebar, login page, original CSS palette, and all Phase 2/3 modules.

## Existing installation (Windows / PyCharm)

1. Back up `.env`, `instance/inventory.db`, and `migrations/` before replacing code.
2. Extract the ZIP. Copy updated source files into your existing project, **without overwriting your backed-up database, .env, or migrations**.
3. In your activated venv run:

```powershell
python -m pip install -r requirements.txt
$env:FLASK_APP = "run.py"
python -m flask db upgrade
python run.py
```

**No new database models or migrations are required for Phase 4**. Run `flask db upgrade` to confirm prior migrations are applied. Do not rerun `flask db init`.

Login as an admin. Navigate to **Dashboard** and **Reports & Analytics**. Staff can view the operational dashboard; only admins can view financial reports and exports.

## Tests

```powershell
python -m pytest -q
```

## Features

- Dynamic dashboard cards and six-month chart
- Admin-only reports with date filtering (UTC dates)
- Sales, purchase, inventory valuation, and profit calculations
- Top-selling products, low/out-of-stock listing
- Daily chart using Chart.js
- CSV and Excel (.xlsx) export for sales, purchases, daily totals, products, and inventory
- Printable report via browser print

**Accounting note:** Sales reports include pending payments because the underlying Phase 3 Sale table represents recorded sales, not confirmed cash receipts. Gross profit = sales subtotal - discounts - recorded sale-item costs; tax is excluded. Cost snapshots stored on the SaleItem record are used; these are Phase 3 product purchase price snapshots, not FIFO or weighted-average inventory costing. Current inventory valuation uses each product's current purchase price. Product performance reports display gross line sales, not allocated sales-level discounts. Operating expenses and returns are not yet modeled.

## Production note

The reports are read-only. No persistent files are written to Vercel; downloads are created in memory. For very large sales histories, add server-side aggregation, pagination and scheduled exports before production use.
