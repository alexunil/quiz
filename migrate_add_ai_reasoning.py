"""Migration: AI Reasoning Feld zur responses Tabelle hinzufügen"""
from app import create_app
from app.models import db

def migrate():
    app = create_app()
    with app.app_context():
        try:
            # AI reasoning Spalte hinzufügen
            with db.engine.connect() as conn:
                conn.execute(db.text('''
                    ALTER TABLE responses
                    ADD COLUMN ai_reasoning TEXT;
                '''))
                conn.commit()

            print("✓ Migration erfolgreich: ai_reasoning Feld hinzugefügt")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("✓ Migration bereits durchgeführt: ai_reasoning Feld existiert bereits")
            else:
                print(f"✗ Fehler bei Migration: {e}")
                raise

if __name__ == '__main__':
    migrate()
