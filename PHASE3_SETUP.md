# Phase 3 — Purchases, Sales/POS, Inventory

## Before upgrading an existing Phase 2 database

1. Back up `.env`, `instance/inventory.db`, and the entire `migrations/` folder. **Do not overwrite them** with files from this ZIP.
2. Copy Phase 3 project source code into your existing PyCharm folder, excluding your `.env`, database, and migrations.
3. Activate `.venv`. Then run the commands below from the directory containing `run.py`.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:FLASK_APP = 'run.py'
python -m flask db migrate -m 'phase 3 purchases sales stock movements'
python -m flask db upgrade
python run.py
```

**Important:** `db migrate` compares your current schema with the model definitions. Review the generated migration carefully before running `db upgrade`. Never run `db init` again on a database with an existing migrations history.

### For a new installation

Read `README.md` and create `.env`. Initialize a *new* migrations folder with `flask db init`, then `flask db migrate`, `flask db upgrade`, and `flask create-admin`. Optionally run `flask seed-demo`.

## How to use

- **Purchases → New purchase:** choose an active supplier, add products, quantities and unit costs. Successful confirmation creates purchase items, stock changes and audit rows together.
- **Sales / POS → New sale:** choose products, quantities, optional customer, discount and tax percentage. The server recalculates prices; it never trusts client totals. Transactions with insufficient stock are rejected.
- **Inventory:** see live quantities, low/out-of-stock labels, and movement history. Admin users can enter audited manual stock adjustments.
- **Receipts:** open a purchase or sale detail and use Print in the browser.
- **KHQR:** **record-only** payment method. No QR creation or payment verification gateway is integrated.
- **Demo data:** sample products start at stock zero; create a purchase or an admin adjustment to add stock before selling.

## Verify

```powershell
python -m pytest -q
```

Manual check: sign in as admin, purchase 10 units, sell 3 units, check stock is 7 and movement history shows +10 and -3. Attempt to sell 8 units and confirm no sale is created.

## Important scope notes

- Existing Phase 2 features and branding/sidebar are retained.
- All financial amounts use Decimal and fixed two-decimal SQL columns.
- Direct modifications to `products.stock_quantity` outside the transaction/adjustment routes are **not** audited. Use provided routes for routine inventory actions.
- Purchase unit cost is preserved in purchase items; sale unit cost is a snapshot of the product's configured purchase price. FIFO/weighted-average inventory costing and financial profit reports remain future work.
- Do not manually delete or edit completed purchase/sale rows as stock reversal workflows are not implemented.
- Database-backed PostgreSQL deployment requires its own validated migration and credentials; local SQLite data is not synchronized.
