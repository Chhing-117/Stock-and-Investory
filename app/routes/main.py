from datetime import datetime, timedelta, timezone
from decimal import Decimal
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from ..extensions import db
from ..models import User, Product, Category, Supplier, Customer, Sale, Purchase

main_bp = Blueprint('main', __name__)

@main_bp.get('/')
def index():
    return render_template('index.html')

@main_bp.get('/dashboard')
@login_required
def dashboard():
    stats=dict(users=User.query.count(), products=Product.query.filter_by(active=True).count(),
               categories=Category.query.count(), suppliers=Supplier.query.filter_by(active=True).count(),
               customers=Customer.query.filter_by(active=True).count(),
               low_stock=Product.query.filter(Product.active.is_(True),Product.stock_quantity <= Product.minimum_stock).count(),
               out_of_stock=Product.query.filter(Product.active.is_(True),Product.stock_quantity == 0).count(),
               purchases=Purchase.query.count(),sales=Sale.query.count())
    recent_sales=db.session.scalars(db.select(Sale).order_by(Sale.id.desc()).limit(6)).all()
    chart=[]
    if current_user.role=='admin':
        # Aggregate in Python using Decimal so SQLite and PostgreSQL yield identical money semantics.
        today=datetime.now(timezone.utc).date()
        month_start=today.replace(day=1)
        for offset in range(5,-1,-1):
            year=month_start.year; month=month_start.month-offset
            while month<1: year-=1; month+=12
            dt=datetime(year,month,1)
            end=datetime(year+1,1,1) if month==12 else datetime(year,month+1,1)
            sales=db.session.scalars(db.select(Sale).where(Sale.created_at>=dt,Sale.created_at<end)).all()
            purchases=db.session.scalars(db.select(Purchase).where(Purchase.created_at>=dt,Purchase.created_at<end)).all()
            net_sales=sum((s.subtotal-s.discount for s in sales),Decimal('0.00'))
            purchase_total=sum((p.total for p in purchases),Decimal('0.00'))
            chart.append(dict(month=dt.strftime('%b %Y'),sales=str(net_sales),purchases=str(purchase_total)))
        stats['total_sales']=sum((s.total for s in db.session.scalars(db.select(Sale))),Decimal('0.00'))
    return render_template('dashboard.html',**stats,recent_sales=recent_sales, chart=chart)

@main_bp.get('/health')
def health():
    return {'status':'ok'}
