"""
Migration: Absolute Pfade in question_catalogs.file_path auf relative Pfade umstellen.
Konvertiert z.B. '/home/alex/quiz/data/catalogs/user_1/foo.json'
              zu 'user_1/foo.json'
"""
import os
import sys
from app import create_app
from app.models import db, QuestionCatalog

app = create_app()

with app.app_context():
    catalogs_dir = app.config['CATALOGS_DIR']
    catalogs = QuestionCatalog.query.all()
    updated = 0

    for catalog in catalogs:
        path = catalog.file_path
        if os.path.isabs(path) and path.startswith(catalogs_dir):
            relative = os.path.relpath(path, catalogs_dir)
            catalog.file_path = relative
            print(f"  [{catalog.id}] {path} → {relative}")
            updated += 1
        elif os.path.isabs(path):
            print(f"  [{catalog.id}] WARNUNG: Pfad außerhalb CATALOGS_DIR: {path}", file=sys.stderr)

    if updated:
        db.session.commit()
        print(f"\n{updated} Katalog(e) aktualisiert.")
    else:
        print("Keine Änderungen notwendig.")
