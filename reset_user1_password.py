#!/usr/bin/env python3
"""Script zum Zurücksetzen des Passworts für user1"""
from app import create_app
from app.models import db, User

def reset_user1_password():
    """Passwort für user1 zurücksetzen"""
    app = create_app()

    with app.app_context():
        user = User.query.filter_by(username='user1').first()

        if not user:
            print("❌ Fehler: Benutzer 'user1' nicht gefunden.")
            return

        # Neues Passwort setzen
        new_password = 'password123'
        user.set_password(new_password)
        db.session.commit()

        print(f"✅ Passwort für Benutzer 'user1' wurde erfolgreich zurückgesetzt!")
        print(f"   Benutzername: user1")
        print(f"   Passwort: {new_password}")
        print()
        print("⚠️  WICHTIG: Bitte ändern Sie dieses Passwort nach dem ersten Login!")

if __name__ == '__main__':
    reset_user1_password()
