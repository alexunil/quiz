from app.models import db, User


def init_db(app):
    """Datenbank initialisieren und Standard-User erstellen"""
    with app.app_context():
        # Tabellen erstellen
        db.create_all()

        # Standard-User 'user1' erstellen, falls nicht vorhanden
        seed_default_user()

        print("Datenbank wurde erfolgreich initialisiert!")


def seed_default_user():
    """Standard-User 'user1' erstellen"""
    User.get_or_create('user1')
    print("Standard-User 'user1' wurde erstellt oder existiert bereits.")
