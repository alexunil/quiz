#!/usr/bin/env python3
"""
Migrations-Script für Multi-User-Authentifizierung und Katalog-Verwaltung

Dieses Script:
1. Erstellt neue Tabellen/Spalten in der Datenbank
2. Setzt Passwort für user1
3. Erstellt Standardkatalog für user1
4. Migriert bestehende QuestionWeights und QuizSessions zum Standardkatalog
"""

import os
import sys
import json
import shutil
import getpass
from pathlib import Path

# Flask-App-Kontext einrichten
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, User, QuestionCatalog, QuestionWeight, QuizSession
from config import Config

def main():
    """Hauptfunktion für Migration"""
    print("=" * 70)
    print("Migration zu Multi-User-Authentifizierung & Katalog-Verwaltung")
    print("=" * 70)
    print()

    app = create_app()

    with app.app_context():
        # Schritt 1: Datenbank-Schema aktualisieren
        print("Schritt 1: Datenbank-Schema aktualisieren...")
        try:
            db.create_all()
            print("✓ Datenbank-Schema aktualisiert")
        except Exception as e:
            print(f"✗ Fehler beim Aktualisieren des Schemas: {e}")
            return False

        # Schritt 2: user1 finden oder erstellen
        print("\nSchritt 2: Benutzer 'user1' vorbereiten...")
        user1 = User.query.filter_by(username='user1').first()

        if not user1:
            print("  Benutzer 'user1' nicht gefunden. Wird erstellt...")
            user1 = User(username='user1')
            db.session.add(user1)
            db.session.commit()
            print("✓ Benutzer 'user1' erstellt")
        else:
            print("✓ Benutzer 'user1' gefunden")

        # Schritt 3: Passwort für user1 setzen (wenn noch nicht gesetzt)
        if not user1.password_hash:
            print("\nSchritt 3: Passwort für 'user1' setzen...")
            while True:
                password = getpass.getpass("  Passwort für user1 (min. 8 Zeichen): ")
                if len(password) < 8:
                    print("  Passwort muss mindestens 8 Zeichen lang sein.")
                    continue

                password_confirm = getpass.getpass("  Passwort bestätigen: ")
                if password != password_confirm:
                    print("  Passwörter stimmen nicht überein.")
                    continue

                user1.set_password(password)
                db.session.commit()
                print("✓ Passwort für 'user1' gesetzt")
                break
        else:
            print("\nSchritt 3: Passwort bereits gesetzt (übersprungen)")

        # Schritt 4: Katalog-Verzeichnis erstellen
        print("\nSchritt 4: Katalog-Verzeichnis erstellen...")
        catalogs_dir = Config.CATALOGS_DIR
        user1_catalog_dir = os.path.join(catalogs_dir, f'user_{user1.id}')

        try:
            os.makedirs(user1_catalog_dir, exist_ok=True)
            print(f"✓ Verzeichnis erstellt: {user1_catalog_dir}")
        except Exception as e:
            print(f"✗ Fehler beim Erstellen des Verzeichnisses: {e}")
            return False

        # Schritt 5: questions.json kopieren
        print("\nSchritt 5: Standardkatalog erstellen...")
        source_file = Config.QUESTIONS_FILE
        catalog_file = os.path.join(user1_catalog_dir, 'standard_katalog.json')

        try:
            if os.path.exists(source_file):
                # Fragen laden
                with open(source_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Unterstützt sowohl {"questions": [...]} als auch [...]
                    if isinstance(data, dict):
                        questions = data.get('questions', [])
                    else:
                        questions = data

                # Als neues Format speichern (direktes Array)
                with open(catalog_file, 'w', encoding='utf-8') as f:
                    json.dump(questions, f, ensure_ascii=False, indent=2)

                print(f"✓ {len(questions)} Fragen nach {catalog_file} kopiert")
                question_count = len(questions)
            else:
                # Leeren Katalog erstellen
                with open(catalog_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                print(f"✓ Leerer Katalog erstellt (Quelldatei nicht gefunden)")
                question_count = 0

        except Exception as e:
            print(f"✗ Fehler beim Kopieren der Fragen: {e}")
            return False

        # Schritt 6: QuestionCatalog-Eintrag erstellen
        print("\nSchritt 6: Katalog-Eintrag in Datenbank erstellen...")
        existing_catalog = QuestionCatalog.query.filter_by(
            user_id=user1.id,
            name=Config.DEFAULT_CATALOG_NAME
        ).first()

        if not existing_catalog:
            catalog = QuestionCatalog.create_catalog(
                user_id=user1.id,
                name=Config.DEFAULT_CATALOG_NAME,
                file_path=catalog_file,
                description='Migrierter Standardkatalog von questions.json',
                is_active=True
            )
            catalog.update_question_count(question_count)
            print(f"✓ Katalog '{catalog.name}' erstellt (ID: {catalog.id})")
        else:
            catalog = existing_catalog
            catalog.file_path = catalog_file
            catalog.is_active = True
            catalog.update_question_count(question_count)
            print(f"✓ Katalog '{catalog.name}' bereits vorhanden, aktualisiert (ID: {catalog.id})")

        # Schritt 7: QuestionWeight-Einträge aktualisieren
        print("\nSchritt 7: QuestionWeight-Einträge migrieren...")
        weights_updated = 0
        try:
            # Alle Gewichte von user1 ohne catalog_id finden
            weights = QuestionWeight.query.filter_by(
                user_id=user1.id,
                catalog_id=None
            ).all()

            for weight in weights:
                weight.catalog_id = catalog.id

            db.session.commit()
            weights_updated = len(weights)
            print(f"✓ {weights_updated} QuestionWeight-Einträge aktualisiert")
        except Exception as e:
            print(f"✗ Fehler beim Aktualisieren der Gewichte: {e}")
            db.session.rollback()

        # Schritt 8: QuizSession-Einträge aktualisieren
        print("\nSchritt 8: QuizSession-Einträge migrieren...")
        sessions_updated = 0
        try:
            # Alle Sessions von user1 ohne catalog_id finden
            sessions = QuizSession.query.filter_by(
                user_id=user1.id,
                catalog_id=None
            ).all()

            for session in sessions:
                session.catalog_id = catalog.id

            db.session.commit()
            sessions_updated = len(sessions)
            print(f"✓ {sessions_updated} QuizSession-Einträge aktualisiert")
        except Exception as e:
            print(f"✗ Fehler beim Aktualisieren der Sessions: {e}")
            db.session.rollback()

        # Zusammenfassung
        print("\n" + "=" * 70)
        print("Migration abgeschlossen!")
        print("=" * 70)
        print(f"""
Zusammenfassung:
  • Benutzer 'user1': ✓
  • Passwort gesetzt: ✓
  • Katalog '{catalog.name}': ✓ ({question_count} Fragen)
  • QuestionWeights migriert: {weights_updated}
  • QuizSessions migriert: {sessions_updated}

Nächste Schritte:
  1. Starten Sie die Anwendung: python run.py
  2. Melden Sie sich als 'user1' an mit dem soeben gesetzten Passwort
  3. Erstellen Sie bei Bedarf weitere Benutzer über /auth/register
  4. Verwalten Sie Kataloge über /catalogs

Hinweis: Sie können sich jetzt mit folgenden Zugangsdaten anmelden:
  Benutzername: user1
  Passwort: [Das soeben gesetzte Passwort]
        """)

        return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
