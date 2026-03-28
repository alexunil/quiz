"""Flask-Login Konfiguration"""
from flask_login import LoginManager
from app.models import User

login_manager = LoginManager()


def init_login_manager(app):
    """Login Manager initialisieren"""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bitte melden Sie sich an, um auf diese Seite zuzugreifen.'
    login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    """Benutzer anhand der ID laden"""
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    """Handler für unautorisierten Zugriff"""
    from flask import redirect, url_for, flash
    flash('Bitte melden Sie sich an, um auf diese Seite zuzugreifen.', 'warning')
    return redirect(url_for('auth.login'))
