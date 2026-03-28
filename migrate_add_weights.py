#!/usr/bin/env python3
"""
Migrationsskript: Fügt die question_weights Tabelle zur Datenbank hinzu.
"""
from app import create_app
from app.models import db

def migrate():
    """Fügt die question_weights Tabelle hinzu"""
    app = create_app()

    with app.app_context():
        # Erstellt nur neue Tabellen, ändert bestehende nicht
        db.create_all()
        print("Migration abgeschlossen: question_weights Tabelle wurde hinzugefügt.")

if __name__ == '__main__':
    migrate()
