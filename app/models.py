from datetime import datetime, timezone
from decimal import Decimal
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db, login_manager

def utcnow():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    def set_password(self, value):
        self.password_hash = generate_password_hash(value)
    def check_password(self, value):
        return check_password_hash(self.password_hash, value)
    @property
    def is_active(self):
        return self.active

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, default='', nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    products = db.relationship('Product', back_populates='category')

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, index=True)
    contact_person = db.Column(db.String(120), default='', nullable=False)
    phone = db.Column(db.String(40), default='', nullable=False)
    email = db.Column(db.String(255), default='', nullable=False)
    address = db.Column(db.Text, default='', nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    products = db.relationship('Product', back_populates='supplier')

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, index=True)
    phone = db.Column(db.String(40), default='', nullable=False)
    email = db.Column(db.String(255), default='', nullable=False)
    address = db.Column(db.Text, default='', nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    sku = db.Column(db.String(80), unique=True, nullable=False, index=True)
    barcode = db.Column(db.String(100), unique=True, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='RESTRICT'), nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=True, index=True)
    purchase_price = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    selling_price = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal('0.00'))
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    minimum_stock = db.Column(db.Integer, nullable=False, default=5)
    unit = db.Column(db.String(32), nullable=False, default='pcs')
    image_url = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, default='', nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    category = db.relationship('Category', back_populates='products')
    supplier = db.relationship('Supplier', back_populates='products')
    __table_args__ = (
        db.CheckConstraint('stock_quantity >= 0', name='ck_product_stock_nonnegative'),
        db.CheckConstraint('minimum_stock >= 0', name='ck_product_minimum_nonnegative'),
        db.CheckConstraint('purchase_price >= 0', name='ck_product_purchase_price_nonnegative'),
        db.CheckConstraint('selling_price >= 0', name='ck_product_selling_price_nonnegative'),
    )

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


class Purchase(db.Model):
    __tablename__ = 'purchases'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    total = db.Column(db.Numeric(14, 2), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    supplier = db.relationship('Supplier')
    user = db.relationship('User')
    items = db.relationship('PurchaseItem', back_populates='purchase', cascade='all, delete-orphan', order_by='PurchaseItem.id')
    __table_args__ = (db.CheckConstraint('total >= 0', name='ck_purchase_total'),)

class PurchaseItem(db.Model):
    __tablename__ = 'purchase_items'
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False)
    purchase = db.relationship('Purchase', back_populates='items')
    product = db.relationship('Product')
    __table_args__ = (db.CheckConstraint('quantity > 0', name='ck_purchase_item_quantity'),
                      db.CheckConstraint('unit_cost >= 0', name='ck_purchase_item_cost'),)

class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='RESTRICT'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False)
    discount = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal('0.00'))
    tax = db.Column(db.Numeric(14, 2), nullable=False, default=Decimal('0.00'))
    total = db.Column(db.Numeric(14, 2), nullable=False)
    payment_method = db.Column(db.String(30), nullable=False)
    payment_status = db.Column(db.String(20), nullable=False, default='recorded')
    payment_reference = db.Column(db.String(120), nullable=False, default='')
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    customer = db.relationship('Customer')
    user = db.relationship('User')
    items = db.relationship('SaleItem', back_populates='sale', cascade='all, delete-orphan', order_by='SaleItem.id')
    __table_args__ = (db.CheckConstraint('total >= 0', name='ck_sale_total'),)

class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    unit_cost = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(14, 2), nullable=False)
    sale = db.relationship('Sale', back_populates='items')
    product = db.relationship('Product')
    __table_args__ = (db.CheckConstraint('quantity > 0', name='ck_sale_item_quantity'),)

class StockMovement(db.Model):
    __tablename__ = 'stock_movements'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    movement_type = db.Column(db.String(30), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)  # signed quantity
    stock_before = db.Column(db.Integer, nullable=False)
    stock_after = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=False, default='')
    reference_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    product = db.relationship('Product')
    user = db.relationship('User')
    __table_args__ = (db.CheckConstraint('stock_after >= 0', name='ck_movement_nonnegative'),
                      db.CheckConstraint('stock_after = stock_before + quantity', name='ck_movement_balance'),)
