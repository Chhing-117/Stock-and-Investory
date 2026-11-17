import os
import click
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template
from .extensions import db, migrate, login_manager, csrf

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    from config import Config
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    production = os.getenv('VERCEL') == '1' or os.getenv('APP_ENV') == 'production'
    if not app.config.get('TESTING') and production:
        secret = app.config.get('SECRET_KEY', '')
        if not secret or secret in ('local-only-change-me', 'replace-with-a-unique-random-value-at-least-32-characters-long', 'replace-with-a-long-random-secret') or len(secret) < 32:
            raise RuntimeError('Set a unique SECRET_KEY (at least 32 characters) in production.')
        if not app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql+psycopg://'):
            raise RuntimeError('Production requires DATABASE_URL pointing to PostgreSQL (not SQLite).')
        if not app.config.get('SESSION_COOKIE_SECURE'):
            raise RuntimeError('Secure cookies are required in production.')
    # Vercel's runtime filesystem is read-only except /tmp. Local SQLite uses instance/.
    if not production or app.config.get('TESTING'):
        os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    csrf.init_app(app)
    from . import models
    from sqlalchemy import text as sql_text

    @app.get('/health')
    def health():
        try:
            db.session.execute(sql_text('SELECT 1')).scalar()
            return {'status': 'ok'}, 200
        except Exception:
            app.logger.exception('Database health check failed')
            db.session.rollback()
            return {'status': 'unavailable'}, 503
    from flask_login import current_user, logout_user
    from flask import request, redirect, url_for, flash

    @app.before_request
    def enforce_active_accounts():
        # Flask-Login caches the user during the request; recheck the persisted
        # active flag so deactivated users cannot keep using old sessions.
        if current_user.is_authenticated:
            db.session.refresh(current_user, attribute_names=['active', 'role'])
            if not current_user.active:
                logout_user()
                flash('Your account has been deactivated.', 'warning')
                return redirect(url_for('auth.login'))

    @app.after_request
    def security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Content-Security-Policy',
            "frame-ancestors 'none'; object-src 'none'; base-uri 'self'")
        if request.endpoint and (request.endpoint.startswith('auth.') or request.endpoint.startswith('reports.')):
            response.headers['Cache-Control'] = 'no-store'
        if app.config.get('SESSION_COOKIE_SECURE'):
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

    @app.errorhandler(400)
    def bad_request(error):
        return render_template('error.html', code=400, message='Invalid request. Check your input and try again.'), 400

    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', code=404, message='The requested page could not be found.'), 404

    @app.errorhandler(413)
    def oversized(error):
        return render_template('error.html', code=413, message='The submitted form is too large.'), 413
    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.catalog import catalog_bp
    from .routes.users import users_bp
    from .routes.transactions import transactions_bp
    from .routes.reports import reports_bp
    for bp in (main_bp, auth_bp, catalog_bp, users_bp, transactions_bp, reports_bp):
        app.register_blueprint(bp)

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('error.html', code=403, message='You do not have permission to access this page.'), 403

    @app.cli.command('create-admin')
    @click.option('--username', prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin(username, password):
        from .models import User
        if User.query.filter_by(username=username).first():
            raise click.ClickException('Username already exists')
        if len(password) < 10:
            raise click.ClickException('Password must contain at least 10 characters')
        user = User(username=username, role='admin')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo('Admin created successfully.')

    @app.cli.command('seed-categories')
    def seed_categories():
        from .models import Category
        names = ('Electronics', 'Food', 'Clothing', 'Furniture', 'Beverages', 'Office Supplies', 'Accessories', 'Cosmetics')
        for name in names:
            if not Category.query.filter_by(name=name).first():
                db.session.add(Category(name=name))
        db.session.commit()
        click.echo('Categories ready.')
    @app.cli.command('seed-demo')
    def seed_demo():
        """Add 20 sample products, suppliers, and customers without duplicates."""
        from .demo_seed import seed_demo_records
        try:
            result = seed_demo_records()
        except Exception as exc:
            raise click.ClickException(f'Demo seed failed: {exc}') from exc
        click.echo('Demo records added: ' + ', '.join(f'{key}={value}' for key, value in result.items()))

    return app
