from datetime import datetime, timezone
from decimal import Decimal
from app.extensions import db
from app.models import Product, Supplier, Customer, Sale, SaleItem, Purchase
from app.routes.reports import report_data, date_window
from tests.conftest import sign_in


def test_reports_admin_only(client):
    assert client.get('/reports/').status_code in (302, 401)
    sign_in(client, 'staff')
    assert client.get('/reports/').status_code == 403
    assert client.get('/reports/export/sales.csv').status_code == 403


def test_report_math_and_export(app, client):
    with app.app_context():
        supplier=Supplier(name='Test Supplier'); customer=Customer(name='Test Buyer')
        db.session.add_all([supplier,customer]); db.session.flush()
        product=Product(name='Widget',sku='WIDGET-4',category_id=1,supplier_id=supplier.id,purchase_price=Decimal('4.00'),selling_price=Decimal('10.00'),stock_quantity=10)
        db.session.add(product); db.session.flush()
        sale=Sale(user_id=1,customer_id=customer.id,subtotal=Decimal('20.00'),discount=Decimal('2.00'),tax=Decimal('1.80'),total=Decimal('19.80'),payment_method='cash',payment_status='paid')
        db.session.add(sale); db.session.flush()
        db.session.add(SaleItem(sale_id=sale.id,product_id=product.id,quantity=2,unit_price=Decimal('10.00'),unit_cost=Decimal('4.00'),subtotal=Decimal('20.00')))
        db.session.add(Purchase(supplier_id=supplier.id,user_id=1,total=Decimal('40.00')))
        db.session.commit()
        start,end,begin,finish=date_window({'start':'2021-01-01','end':'2030-12-31'})
        result=report_data(start,end,begin,finish)
        assert result['net_sales']==Decimal('18.00')
        assert result['gross_profit']==Decimal('10.00')
        assert result['purchase_total']==Decimal('40.00')
        assert result['valuation']==Decimal('40.00')
    sign_in(client)
    assert client.get('/reports/').status_code==200
    csv_response=client.get('/reports/export/sales.csv?start=2021-01-01&end=2030-12-31')
    assert csv_response.status_code==200
    assert b'19.80' in csv_response.data
    excel=client.get('/reports/export/inventory.xlsx')
    assert excel.status_code==200
    assert excel.data[:2]==b'PK'


def test_invalid_range(client):
    sign_in(client)
    assert client.get('/reports/?start=2026-12-31&end=2026-01-01').status_code==400
