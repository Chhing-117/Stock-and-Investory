from decimal import Decimal
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from flask_wtf import FlaskForm
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from wtforms import (BooleanField, DecimalField, IntegerField, SelectField,
                     StringField, SubmitField, TextAreaField)
from wtforms.validators import DataRequired, Email, InputRequired, Length, NumberRange, Optional
from ..extensions import db
from ..models import Category, Customer, Product, Supplier
from .common import admin_required

catalog_bp = Blueprint('catalog', __name__)

class CategoryForm(FlaskForm):
    name = StringField('Category name', validators=[DataRequired(), Length(max=120)])
    description = TextAreaField('Description', validators=[Length(max=5000)])
    submit = SubmitField('Save category')

class SupplierForm(FlaskForm):
    name = StringField('Supplier name', validators=[DataRequired(), Length(max=160)])
    contact_person = StringField('Contact person', validators=[Length(max=120)])
    phone = StringField('Phone', validators=[Length(max=40)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=255)])
    address = TextAreaField('Address', validators=[Length(max=5000)])
    active = BooleanField('Active', default=True)
    submit = SubmitField('Save supplier')

class CustomerForm(FlaskForm):
    name = StringField('Customer name', validators=[DataRequired(), Length(max=160)])
    phone = StringField('Phone', validators=[Length(max=40)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=255)])
    address = TextAreaField('Address', validators=[Length(max=5000)])
    active = BooleanField('Active', default=True)
    submit = SubmitField('Save customer')

class ProductForm(FlaskForm):
    name = StringField('Product name', validators=[DataRequired(), Length(max=180)])
    sku = StringField('SKU', validators=[DataRequired(), Length(max=80)])
    barcode = StringField('Barcode', validators=[Optional(), Length(max=100)])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    supplier_id = SelectField('Supplier (optional)', coerce=int)
    purchase_price = DecimalField('Purchase price (USD)', places=2, validators=[InputRequired(), NumberRange(min=0)])
    selling_price = DecimalField('Selling price (USD)', places=2, validators=[InputRequired(), NumberRange(min=0)])
    minimum_stock = IntegerField('Minimum stock', validators=[InputRequired(), NumberRange(min=0)])
    unit = StringField('Unit', validators=[DataRequired(), Length(max=32)], default='pcs')
    description = TextAreaField('Description', validators=[Length(max=5000)])
    active = BooleanField('Active', default=True)
    submit = SubmitField('Save product')

def choices(form):
    form.category_id.choices = [(0, 'Choose category')] + [(c.id, c.name) for c in Category.query.order_by(Category.name)]
    form.supplier_id.choices = [(0, 'No supplier')] + [(s.id, s.name) for s in Supplier.query.order_by(Supplier.name)]

def persist():
    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        flash('Could not save. Check that the category name, SKU, or barcode is unique and referenced records exist.', 'danger')
        return False

def page(query):
    number = request.args.get('page', 1, type=int)
    return query.paginate(
        page=number,
        per_page=10,
        error_out=False
    )

@catalog_bp.get('/categories')
@login_required
def categories():
    q = request.args.get('q', '').strip()[:100]
    query = Category.query
    if q:
        query = query.filter(Category.name.ilike(f'%{q}%'))
    return render_template('catalog/list.html', title='Categories', kind='category', rows=page(query.order_by(Category.name)), q=q)

@catalog_bp.route('/categories/new', methods=['GET', 'POST'])
@admin_required
def category_new():
    form = CategoryForm()
    if form.validate_on_submit():
        item = Category(name=form.name.data.strip(), description=form.description.data or '')
        db.session.add(item)
        if persist():
            flash('Category created.', 'success')
            return redirect(url_for('catalog.categories'))
    return render_template('catalog/form.html', title='Add category', form=form)

@catalog_bp.route('/categories/<int:item_id>/edit', methods=['GET', 'POST'])
@admin_required
def category_edit(item_id):
    item = db.get_or_404(Category, item_id)
    form = CategoryForm(obj=item)
    if form.validate_on_submit():
        item.name = form.name.data.strip()
        item.description = form.description.data or ''
        if persist():
            flash('Category updated.', 'success')
            return redirect(url_for('catalog.categories'))
    return render_template('catalog/form.html', title='Edit category', form=form)

@catalog_bp.post('/categories/<int:item_id>/delete')
@admin_required
def category_delete(item_id):
    item = db.get_or_404(Category, item_id)
    if Product.query.filter_by(category_id=item_id).first():
        flash('Cannot delete a category containing products.', 'warning')
    else:
        db.session.delete(item)
        if persist(): flash('Category deleted.', 'success')
    return redirect(url_for('catalog.categories'))

@catalog_bp.get('/suppliers')
@login_required
def suppliers():
    q = request.args.get('q', '').strip()[:100]
    query = Supplier.query
    if q:
        query = query.filter(or_(Supplier.name.ilike(f'%{q}%'), Supplier.phone.ilike(f'%{q}%')))
    return render_template('catalog/list.html', title='Suppliers', kind='supplier', rows=page(query.order_by(Supplier.name)), q=q)

@catalog_bp.route('/suppliers/new', methods=['GET', 'POST'])
@admin_required
def supplier_new():
    form = SupplierForm()
    if form.validate_on_submit():
        item = Supplier()
        update_party(item, form)
        db.session.add(item)
        if persist():
            flash('Supplier created.', 'success')
            return redirect(url_for('catalog.suppliers'))
    return render_template('catalog/form.html', title='Add supplier', form=form)

@catalog_bp.route('/suppliers/<int:item_id>/edit', methods=['GET', 'POST'])
@admin_required
def supplier_edit(item_id):
    item = db.get_or_404(Supplier, item_id)
    form = SupplierForm(obj=item)
    if form.validate_on_submit():
        update_party(item, form)
        if persist():
            flash('Supplier updated.', 'success')
            return redirect(url_for('catalog.suppliers'))
    return render_template('catalog/form.html', title='Edit supplier', form=form)

@catalog_bp.post('/suppliers/<int:item_id>/deactivate')
@admin_required
def supplier_deactivate(item_id):
    item = db.get_or_404(Supplier, item_id)
    item.active = not item.active
    if persist(): flash('Supplier status updated.', 'success')
    return redirect(url_for('catalog.suppliers'))

@catalog_bp.get('/customers')
@login_required
def customers():
    q = request.args.get('q', '').strip()[:100]
    query = Customer.query
    if q:
        query = query.filter(or_(Customer.name.ilike(f'%{q}%'), Customer.phone.ilike(f'%{q}%')))
    return render_template('catalog/list.html', title='Customers', kind='customer', rows=page(query.order_by(Customer.name)), q=q)

@catalog_bp.route('/customers/new', methods=['GET', 'POST'])
@admin_required
def customer_new():
    form = CustomerForm()
    if form.validate_on_submit():
        item = Customer()
        update_party(item, form)
        db.session.add(item)
        if persist():
            flash('Customer created.', 'success')
            return redirect(url_for('catalog.customers'))
    return render_template('catalog/form.html', title='Add customer', form=form)

@catalog_bp.route('/customers/<int:item_id>/edit', methods=['GET', 'POST'])
@admin_required
def customer_edit(item_id):
    item = db.get_or_404(Customer, item_id)
    form = CustomerForm(obj=item)
    if form.validate_on_submit():
        update_party(item, form)
        if persist():
            flash('Customer updated.', 'success')
            return redirect(url_for('catalog.customers'))
    return render_template('catalog/form.html', title='Edit customer', form=form)

@catalog_bp.post('/customers/<int:item_id>/deactivate')
@admin_required
def customer_deactivate(item_id):
    item = db.get_or_404(Customer, item_id)
    item.active = not item.active
    if persist(): flash('Customer status updated.', 'success')
    return redirect(url_for('catalog.customers'))

def update_party(item, form):
    for field in ('name', 'phone', 'email', 'address'):
        if hasattr(form, field):
            value = getattr(form, field).data
            setattr(item, field, value.strip() if value else '')
    if hasattr(form, 'contact_person'):
        item.contact_person = (form.contact_person.data or '').strip()
    item.active = form.active.data

@catalog_bp.get('/products')
@login_required
def products():
    q = request.args.get('q', '').strip()[:100]
    category = request.args.get('category', type=int)
    stock = request.args.get('stock', '')
    query = Product.query
    if q:
        query = query.filter(or_(Product.name.ilike(f'%{q}%'), Product.sku.ilike(f'%{q}%'), Product.barcode.ilike(f'%{q}%')))
    if category:
        query = query.filter(Product.category_id == category)
    if stock == 'out': query = query.filter(Product.stock_quantity == 0)
    if stock == 'low': query = query.filter(Product.stock_quantity > 0, Product.stock_quantity <= Product.minimum_stock)
    return render_template('catalog/list.html', title='Products', kind='product', rows=page(query.order_by(Product.name)), q=q,
                           categories=Category.query.order_by(Category.name).all(), selected_category=category, stock=stock)

@catalog_bp.route('/products/new', methods=['GET', 'POST'])
@admin_required
def product_new():
    form = ProductForm()
    choices(form)
    if not Category.query.first():
        flash('Create a category before adding products.', 'warning')
        return redirect(url_for('catalog.category_new'))
    if form.validate_on_submit():
        if form.category_id.data == 0:
            form.category_id.errors.append('Choose a category.')
        else:
            item = Product(stock_quantity=0)
            update_product(item, form)
            db.session.add(item)
            if persist():
                flash('Product created with zero stock. Record a purchase or adjustment to add stock.', 'success')
                return redirect(url_for('catalog.products'))
    return render_template('catalog/form.html', title='Add product', form=form)

@catalog_bp.route('/products/<int:item_id>/edit', methods=['GET', 'POST'])
@admin_required
def product_edit(item_id):
    item = db.get_or_404(Product, item_id)
    form = ProductForm(obj=item)
    choices(form)
    if request.method == 'GET':
        form.supplier_id.data = item.supplier_id or 0
    if form.validate_on_submit():
        if form.category_id.data == 0:
            form.category_id.errors.append('Choose a category.')
        else:
            update_product(item, form)
            if persist():
                flash('Product updated.', 'success')
                return redirect(url_for('catalog.products'))
    return render_template('catalog/form.html', title='Edit product', form=form, item=item)

@catalog_bp.post('/products/<int:item_id>/archive')
@admin_required
def product_archive(item_id):
    item = db.get_or_404(Product, item_id)
    item.active = not item.active
    if persist(): flash('Product availability updated.', 'success')
    return redirect(url_for('catalog.products'))

def update_product(item, form):
    for field in ('name', 'sku', 'unit', 'description'):
        setattr(item, field, (getattr(form, field).data or '').strip())
    item.barcode = (form.barcode.data or '').strip() or None
    item.category_id = form.category_id.data
    item.supplier_id = form.supplier_id.data or None
    item.purchase_price = form.purchase_price.data
    item.selling_price = form.selling_price.data
    item.minimum_stock = form.minimum_stock.data
    item.active = form.active.data
