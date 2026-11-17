"""Read-only business reports. Money is computed using Decimal (never float)."""
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from calendar import monthrange
from io import BytesIO, StringIO
import csv
from flask import Blueprint, abort, render_template, request, Response, send_file
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from ..extensions import db
from ..models import Product, Category, Purchase, Sale, SaleItem, StockMovement
from .common import admin_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')
ZERO = Decimal('0.00')

def currency(value):
    return (value if isinstance(value, Decimal) else Decimal(str(value or 0))).quantize(Decimal('0.01'))

def date_window(args):
    """Default trailing 30 days; inclusive dates with exclusive end timestamp."""
    today = datetime.now(timezone.utc).date()
    try:
        start = date.fromisoformat(args.get('start', '')) if args.get('start') else today - timedelta(days=29)
        end = date.fromisoformat(args.get('end', '')) if args.get('end') else today
    except ValueError:
        abort(400, 'Dates must use YYYY-MM-DD format.')
    if start > end or (end-start).days > 3660:
        abort(400, 'Choose an ordered date range no longer than 10 years.')
    return start, end, datetime.combine(start, time.min), datetime.combine(end + timedelta(days=1), time.min)

def report_data(start, end, begin, finish):
    # Read-only queries; the sales model records all sales irrespective of payment status.
    sales = db.session.scalars(db.select(Sale).options(selectinload(Sale.items))
        .where(Sale.created_at >= begin, Sale.created_at < finish).order_by(Sale.created_at.desc())).all()
    purchases = db.session.scalars(db.select(Purchase)
        .where(Purchase.created_at >= begin, Purchase.created_at < finish).order_by(Purchase.created_at.desc())).all()
    daily = defaultdict(lambda: {'revenue': ZERO, 'purchases': ZERO, 'cost': ZERO, 'sales': 0})
    products = defaultdict(lambda: {'quantity': 0, 'gross': ZERO, 'cost': ZERO})
    revenue = cost = discounts = tax = purchase_total = ZERO
    for sale in sales:
        d = sale.created_at.date().isoformat()
        gross = currency(sale.subtotal)
        revenue += gross
        discounts += currency(sale.discount)
        tax += currency(sale.tax)
        daily[d]['revenue'] += gross - currency(sale.discount)
        daily[d]['sales'] += 1
        for item in sale.items:
            item_cost = currency(item.unit_cost) * item.quantity
            cost += item_cost
            daily[d]['cost'] += item_cost
            row = products[item.product_id]
            row['quantity'] += item.quantity
            row['gross'] += currency(item.subtotal)
            row['cost'] += item_cost
    for purchase in purchases:
        amount = currency(purchase.total)
        purchase_total += amount
        daily[purchase.created_at.date().isoformat()]['purchases'] += amount
    product_ids = list(products)
    product_names = {p.id: p.name for p in db.session.scalars(db.select(Product).where(Product.id.in_(product_ids)))} if product_ids else {}
    by_product = [{'product':product_names.get(pid, f'Product #{pid}'), 'quantity':row['quantity'],
                   'gross':row['gross'], 'cost':row['cost']}
                  for pid,row in products.items()]
    by_product.sort(key=lambda row: (-row['gross'], row['product']))
    # Discounts are sales-wide. Their effect on profit is applied only to the aggregate,
    # not misleadingly assigned to individual products.
    dates = sorted(daily)
    timeline = [{'date':d, **daily[d], 'profit':daily[d]['revenue'] - daily[d]['cost']} for d in dates]
    stock = db.session.scalars(db.select(Product).where(Product.active.is_(True)).order_by(Product.name)).all()
    stock_rows = [{'sku':p.sku,'name':p.name,'quantity':p.stock_quantity,
                   'min_stock':p.minimum_stock,'cost':currency(p.purchase_price),
                   'value':currency(p.purchase_price)*p.stock_quantity,
                   'status':('Out of stock' if p.stock_quantity == 0 else 'Low stock' if p.stock_quantity <= p.minimum_stock else 'In stock')}
                  for p in stock]
    valuation = sum((p['value'] for p in stock_rows), ZERO)
    net_sales = revenue - discounts  # tax is not revenue or profit
    return dict(start=start, end=end, sales=sales, purchases=purchases, sales_count=len(sales),
                purchase_count=len(purchases), gross_sales=revenue, discounts=discounts, tax=tax,
                net_sales=net_sales, cogs=cost, gross_profit=net_sales-cost,
                purchase_total=purchase_total, timeline=timeline, top_products=by_product[:10],
                all_products=by_product, stock_rows=stock_rows, valuation=valuation,
                low_stock=sum(p['status'] != 'In stock' for p in stock_rows),
                out_of_stock=sum(p['status'] == 'Out of stock' for p in stock_rows))

@reports_bp.get('/')
@admin_required
def index():
    start, end, begin, finish = date_window(request.args)
    data = report_data(start,end,begin,finish)
    # JSON data uses strings for money; charts can safely coerce for display only.
    chart = [{'label':r['date'],'sales':str(r['revenue']),'purchases':str(r['purchases']),
              'profit':str(r['profit'])} for r in data['timeline']]
    return render_template('reports/index.html', data=data, chart=chart)

def rows_for_export(kind, data):
    if kind == 'sales':
        return ['ID','Date (UTC)','Customer','Subtotal','Discount','Tax','Total','Payment method','Payment status'], [
            [s.id,s.created_at.strftime('%Y-%m-%d %H:%M'),s.customer.name if s.customer else 'Walk-in',
             s.subtotal,s.discount,s.tax,s.total,s.payment_method,s.payment_status] for s in data['sales']]
    if kind == 'purchases':
        return ['ID','Date (UTC)','Supplier','Total'], [
            [p.id,p.created_at.strftime('%Y-%m-%d %H:%M'),p.supplier.name,p.total] for p in data['purchases']]
    if kind == 'inventory':
        return ['SKU','Product','Quantity','Minimum stock','Unit cost','Stock value','Status'], [
            [r['sku'],r['name'],r['quantity'],r['min_stock'],r['cost'],r['value'],r['status']] for r in data['stock_rows']]
    if kind == 'products':
        return ['Product','Units sold','Gross sales','Recorded cost'], [
            [r['product'],r['quantity'],r['gross'],r['cost']] for r in data['all_products']]
    if kind == 'daily':
        return ['Date','Sales ex. tax','Purchases','Recorded cost','Gross profit before overhead','Sale count'], [
            [r['date'],r['revenue'],r['purchases'],r['cost'],r['profit'],r['sales']] for r in data['timeline']]
    abort(404)

@reports_bp.get('/export/<kind>.<fmt>')
@admin_required
def export(kind, fmt):
    if fmt not in ('csv','xlsx') or kind not in ('sales','purchases','inventory','products','daily'):
        abort(404)
    start, end, begin, finish = date_window(request.args)
    data = report_data(start,end,begin,finish)
    headers, rows = rows_for_export(kind,data)
    filename = f'stockflow_{kind}_{start}_{end}.{fmt}'
    if fmt == 'csv':
        io = StringIO(newline='')
        writer = csv.writer(io)
        writer.writerow(headers)
        for row in rows: writer.writerow([str(v) if isinstance(v,Decimal) else v for v in row])
        return Response('\ufeff'+io.getvalue(),mimetype='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{filename}"'})
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb=Workbook(); ws=wb.active; ws.title=kind.capitalize()
    ws.append(headers)
    for cell in ws[1]: cell.fill=PatternFill('solid',fgColor='0F172A'); cell.font=Font(color='FFFFFF',bold=True)
    for row in rows:
        ws.append([float(v) if isinstance(v,Decimal) else v for v in row])
        for cell in ws[ws.max_row]:
            if isinstance(cell.value,float): cell.number_format='#,##0.00'
    ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
    for col in ws.columns:
        values=[len(str(c.value or '')) for c in col[:200]]
        ws.column_dimensions[get_column_letter(col[0].column)].width=min(max(max(values,default=8)+2,12),36)
    stream=BytesIO(); wb.save(stream); stream.seek(0)
    return send_file(stream,as_attachment=True,download_name=filename,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
