from flask import Blueprint, flash, redirect, render_template, url_for
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField
from wtforms.validators import DataRequired, Length, Optional
from ..extensions import db
from ..models import User
from .common import admin_required

users_bp = Blueprint('users', __name__, url_prefix='/users')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password (required on creation, optional on edit)', validators=[Optional(), Length(min=10, max=128)])
    role = SelectField('Role', choices=[('staff', 'Staff'), ('admin', 'Admin')])
    active = BooleanField('Active', default=True)

@users_bp.get('/')
@admin_required
def index():
    return render_template('users/list.html', users=User.query.order_by(User.username).all())

@users_bp.route('/new', methods=['GET', 'POST'])
@admin_required
def new():
    form = UserForm()
    if form.validate_on_submit():
        if not form.password.data:
            form.password.errors.append('A password of at least 10 characters is required.')
        elif User.query.filter_by(username=form.username.data.strip()).first():
            form.username.errors.append('Username already exists.')
        else:
            user = User(username=form.username.data.strip(), role=form.role.data, active=form.active.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('User created.', 'success')
            return redirect(url_for('users.index'))
    return render_template('catalog/form.html', form=form, title='Create user')

@users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(user_id):
    from flask_login import current_user
    user = db.get_or_404(User, user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        desired_active = form.active.data
        desired_role = form.role.data
        if user.id == current_user.id and (not desired_active or desired_role != 'admin'):
            flash('You cannot deactivate or demote your own admin account.', 'danger')
        elif user.role == 'admin' and user.active and (not desired_active or desired_role != 'admin') and \
                User.query.filter_by(role='admin', active=True).count() <= 1:
            flash('At least one active administrator must remain.', 'danger')
        elif User.query.filter(User.username == form.username.data.strip(), User.id != user.id).first():
            form.username.errors.append('Username already exists.')
        else:
            user.username = form.username.data.strip()
            user.active = desired_active
            user.role = desired_role
            if form.password.data: user.set_password(form.password.data)
            db.session.commit()
            flash('User updated.', 'success')
            return redirect(url_for('users.index'))
    return render_template('catalog/form.html', form=form, title='Edit user')
