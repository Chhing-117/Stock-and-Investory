from functools import wraps
from flask import abort
from flask_login import current_user, login_required

def admin_required(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_active or current_user.role != 'admin':
            abort(403)
        return func(*args, **kwargs)
    return wrapper
