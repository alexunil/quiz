"""Migration: Timeout-Felder hinzufügen"""
from app import create_app
from app.models import db

def migrate():
    app = create_app()
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                # time_per_question zur question_catalogs Tabelle hinzufügen
                conn.execute(db.text('''
                    ALTER TABLE question_catalogs
                    ADD COLUMN time_per_question INTEGER NOT NULL DEFAULT 30;
                '''))

                # answered_after_timeout zur responses Tabelle hinzufügen
                conn.execute(db.text('''
                    ALTER TABLE responses
                    ADD COLUMN answered_after_timeout BOOLEAN NOT NULL DEFAULT 0;
                '''))
                conn.commit()

            print("✓ Migration erfolgreich: time_per_question und answered_after_timeout Felder hinzugefügt")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("✓ Migration bereits durchgeführt: Felder existieren bereits")
            else:
                print(f"✗ Fehler bei Migration: {e}")
                raise

if __name__ == '__main__':
    migrate()
