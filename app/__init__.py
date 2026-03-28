from flask import Flask
from config import Config
from app.models import db
from app.database import init_db
from app.auth import init_login_manager


def create_app(config_class=Config):
    """Flask Application Factory"""

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Datenbank initialisieren
    db.init_app(app)

    # Flask-Login initialisieren
    init_login_manager(app)

    # Tabellen erstellen und Standard-User anlegen
    with app.app_context():
        init_db(app)

    # Routen registrieren
    from app import routes
    app.register_blueprint(routes.bp)

    # Auth-Routes registrieren
    from app import auth_routes
    app.register_blueprint(auth_routes.bp)

    # Katalog-Routes registrieren
    from app import catalog_routes
    app.register_blueprint(catalog_routes.bp)

    # Frageneditor-Routes registrieren
    from app import question_editor_routes
    app.register_blueprint(question_editor_routes.bp)

    @app.context_processor
    def inject_catalog_info():
        from flask_login import current_user
        from app.models import QuestionCatalog
        if current_user.is_authenticated:
            active = current_user.get_active_catalog()
            all_cats = QuestionCatalog.query.filter_by(user_id=current_user.id).order_by(QuestionCatalog.name).all()
            return dict(active_catalog=active, all_catalogs=all_cats)
        return dict(active_catalog=None, all_catalogs=[])

    return app
