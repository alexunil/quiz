"""Katalog-Verwaltungs-Routes"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, QuestionCatalog, QuestionWeight
from app.ai_service import generate_explanation
import os
import json
import shutil

bp = Blueprint('catalogs', __name__, url_prefix='/catalogs')


def allowed_file(filename):
    """Prüfen ob Datei-Extension erlaubt ist"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@bp.route('/')
@login_required
def manage():
    """Katalog-Übersicht"""
    catalogs = QuestionCatalog.query.filter_by(user_id=current_user.id).order_by(
        QuestionCatalog.is_active.desc(),
        QuestionCatalog.created_at.desc()
    ).all()
    return render_template('catalogs/manage.html', catalogs=catalogs)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Neuen Katalog erstellen"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        copy_sample = request.form.get('copy_sample', 'no')

        # Validierung
        if not name:
            flash('Katalogname ist erforderlich.', 'danger')
            return render_template('catalogs/create.html')

        if len(name) > 200:
            flash('Katalogname ist zu lang (max. 200 Zeichen).', 'danger')
            return render_template('catalogs/create.html')

        # Prüfen ob Name bereits existiert
        existing = QuestionCatalog.query.filter_by(
            user_id=current_user.id,
            name=name
        ).first()
        if existing:
            flash(f'Katalog "{name}" existiert bereits.', 'danger')
            return render_template('catalogs/create.html')

        # Verzeichnis für User erstellen
        user_dir = os.path.join(current_app.config['CATALOGS_DIR'], f'user_{current_user.id}')
        os.makedirs(user_dir, exist_ok=True)

        # Dateiname für JSON (relativ zu CATALOGS_DIR speichern)
        safe_name = secure_filename(name.replace(' ', '_').lower())
        relative_path = os.path.join(f'user_{current_user.id}', f'{safe_name}.json')
        catalog_file = os.path.join(current_app.config['CATALOGS_DIR'], relative_path)

        # Sicherstellen dass Datei nicht bereits existiert
        counter = 1
        while os.path.exists(catalog_file):
            relative_path = os.path.join(f'user_{current_user.id}', f'{safe_name}_{counter}.json')
            catalog_file = os.path.join(current_app.config['CATALOGS_DIR'], relative_path)
            counter += 1

        # Katalog-Inhalt erstellen
        questions = []
        if copy_sample == 'yes':
            # Beispiel-Fragen aus questions.json kopieren
            sample_file = current_app.config.get('QUESTIONS_FILE')
            if os.path.exists(sample_file):
                try:
                    with open(sample_file, 'r', encoding='utf-8') as f:
                        questions = json.load(f)
                except Exception as e:
                    flash(f'Fehler beim Laden der Beispielfragen: {str(e)}', 'warning')
                    questions = []

        # JSON-Datei erstellen
        try:
            with open(catalog_file, 'w', encoding='utf-8') as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            flash(f'Fehler beim Erstellen der Katalogdatei: {str(e)}', 'danger')
            return render_template('catalogs/create.html')

        # Katalog in DB erstellen (relativer Pfad)
        catalog = QuestionCatalog.create_catalog(
            user_id=current_user.id,
            name=name,
            file_path=relative_path,
            description=description if description else None,
            is_active=False
        )

        # Fragen-Anzahl aktualisieren
        catalog.update_question_count(len(questions))

        flash(f'Katalog "{name}" wurde erfolgreich erstellt.', 'success')
        return redirect(url_for('catalogs.manage'))

    return render_template('catalogs/create.html')


@bp.route('/<int:catalog_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(catalog_id):
    """Katalog bearbeiten"""
    catalog = QuestionCatalog.query.get_or_404(catalog_id)

    # Authorization-Check
    if catalog.user_id != current_user.id:
        flash('Sie haben keine Berechtigung, diesen Katalog zu bearbeiten.', 'danger')
        return redirect(url_for('catalogs.manage'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        time_per_question = request.form.get('time_per_question', '30')

        # Validierung
        if not name:
            flash('Katalogname ist erforderlich.', 'danger')
            return render_template('catalogs/edit.html', catalog=catalog)

        if len(name) > 200:
            flash('Katalogname ist zu lang (max. 200 Zeichen).', 'danger')
            return render_template('catalogs/edit.html', catalog=catalog)

        # Zeit validieren
        try:
            time_per_question = int(time_per_question)
            if time_per_question < 10 or time_per_question > 300:
                flash('Zeit pro Frage muss zwischen 10 und 300 Sekunden liegen.', 'danger')
                return render_template('catalogs/edit.html', catalog=catalog)
        except ValueError:
            flash('Ungültige Zeitangabe.', 'danger')
            return render_template('catalogs/edit.html', catalog=catalog)

        # Prüfen ob Name bereits von anderem Katalog verwendet wird
        existing = QuestionCatalog.query.filter(
            QuestionCatalog.user_id == current_user.id,
            QuestionCatalog.name == name,
            QuestionCatalog.id != catalog_id
        ).first()
        if existing:
            flash(f'Katalog "{name}" existiert bereits.', 'danger')
            return render_template('catalogs/edit.html', catalog=catalog)

        # Aktualisieren
        catalog.name = name
        catalog.description = description if description else None
        catalog.time_per_question = time_per_question
        db.session.commit()

        flash(f'Katalog "{name}" wurde aktualisiert.', 'success')
        return redirect(url_for('catalogs.manage'))

    return render_template('catalogs/edit.html', catalog=catalog)


@bp.route('/<int:catalog_id>/delete', methods=['POST'])
@login_required
def delete(catalog_id):
    """Katalog löschen"""
    catalog = QuestionCatalog.query.get_or_404(catalog_id)

    # Authorization-Check
    if catalog.user_id != current_user.id:
        flash('Sie haben keine Berechtigung, diesen Katalog zu löschen.', 'danger')
        return redirect(url_for('catalogs.manage'))

    # Prüfen ob Katalog aktiv ist
    if catalog.is_active:
        # Prüfen ob es andere Kataloge gibt
        other_catalogs = QuestionCatalog.query.filter(
            QuestionCatalog.user_id == current_user.id,
            QuestionCatalog.id != catalog_id
        ).all()

        if other_catalogs:
            # Anderen Katalog aktivieren
            other_catalogs[0].activate()
        # Wenn keine anderen Kataloge: erlauben zu löschen (User muss dann neuen erstellen)

    catalog_name = catalog.name
    catalog_file = catalog.abs_file_path

    # Katalog aus DB löschen (cascade löscht auch QuestionWeights)
    db.session.delete(catalog)
    db.session.commit()

    # JSON-Datei löschen
    try:
        if os.path.exists(catalog_file):
            os.remove(catalog_file)
    except Exception as e:
        flash(f'Katalog wurde gelöscht, aber Datei konnte nicht entfernt werden: {str(e)}', 'warning')

    flash(f'Katalog "{catalog_name}" wurde gelöscht.', 'success')
    return redirect(url_for('catalogs.manage'))


@bp.route('/<int:catalog_id>/activate', methods=['POST'])
@login_required
def activate(catalog_id):
    """Katalog aktivieren"""
    catalog = QuestionCatalog.query.get_or_404(catalog_id)

    # Authorization-Check
    if catalog.user_id != current_user.id:
        flash('Sie haben keine Berechtigung, diesen Katalog zu aktivieren.', 'danger')
        return redirect(url_for('catalogs.manage'))

    catalog.activate()
    flash(f'Katalog "{catalog.name}" ist jetzt aktiv.', 'success')
    return redirect(url_for('catalogs.manage'))


@bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_catalog():
    """Katalog aus JSON-Datei importieren"""
    if request.method == 'POST':
        # Prüfen ob Datei hochgeladen wurde
        if 'file' not in request.files:
            flash('Keine Datei ausgewählt.', 'danger')
            return render_template('catalogs/import.html')

        file = request.files['file']

        if file.filename == '':
            flash('Keine Datei ausgewählt.', 'danger')
            return render_template('catalogs/import.html')

        if not allowed_file(file.filename):
            flash('Nur JSON-Dateien sind erlaubt.', 'danger')
            return render_template('catalogs/import.html')

        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('Katalogname ist erforderlich.', 'danger')
            return render_template('catalogs/import.html')

        # Prüfen ob Name bereits existiert
        existing = QuestionCatalog.query.filter_by(
            user_id=current_user.id,
            name=name
        ).first()
        if existing:
            flash(f'Katalog "{name}" existiert bereits.', 'danger')
            return render_template('catalogs/import.html')

        # JSON-Inhalt validieren
        try:
            content = file.read().decode('utf-8')
            questions = json.loads(content)

            if not isinstance(questions, list):
                flash('Ungültiges JSON-Format: Erwartet wird ein Array von Fragen.', 'danger')
                return render_template('catalogs/import.html')

            # Basis-Validierung der Fragen
            for idx, q in enumerate(questions):
                if not isinstance(q, dict):
                    flash(f'Frage {idx + 1}: Ungültiges Format.', 'danger')
                    return render_template('catalogs/import.html')
                # Mindestens 'id' und 'question' sollten vorhanden sein
                if 'id' not in q or 'question' not in q:
                    flash(f'Frage {idx + 1}: Fehlende Pflichtfelder (id, question).', 'danger')
                    return render_template('catalogs/import.html')

        except json.JSONDecodeError as e:
            flash(f'Ungültige JSON-Datei: {str(e)}', 'danger')
            return render_template('catalogs/import.html')
        except Exception as e:
            flash(f'Fehler beim Lesen der Datei: {str(e)}', 'danger')
            return render_template('catalogs/import.html')

        # Verzeichnis für User erstellen
        user_dir = os.path.join(current_app.config['CATALOGS_DIR'], f'user_{current_user.id}')
        os.makedirs(user_dir, exist_ok=True)

        # Sicheren Dateinamen erstellen (relativ zu CATALOGS_DIR speichern)
        safe_name = secure_filename(name.replace(' ', '_').lower())
        relative_path = os.path.join(f'user_{current_user.id}', f'{safe_name}.json')
        catalog_file = os.path.join(current_app.config['CATALOGS_DIR'], relative_path)

        # Sicherstellen dass Datei nicht bereits existiert
        counter = 1
        while os.path.exists(catalog_file):
            relative_path = os.path.join(f'user_{current_user.id}', f'{safe_name}_{counter}.json')
            catalog_file = os.path.join(current_app.config['CATALOGS_DIR'], relative_path)
            counter += 1

        # Datei speichern
        try:
            with open(catalog_file, 'w', encoding='utf-8') as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            flash(f'Fehler beim Speichern der Datei: {str(e)}', 'danger')
            return render_template('catalogs/import.html')

        # Katalog in DB erstellen (relativer Pfad)
        catalog = QuestionCatalog.create_catalog(
            user_id=current_user.id,
            name=name,
            file_path=relative_path,
            description=description if description else None,
            is_active=False
        )

        # Fragen-Anzahl aktualisieren
        catalog.update_question_count(len(questions))

        flash(f'Katalog "{name}" wurde mit {len(questions)} Fragen importiert.', 'success')
        return redirect(url_for('catalogs.manage'))

    return render_template('catalogs/import.html')


@bp.route('/<int:catalog_id>/export')
@login_required
def export(catalog_id):
    """Katalog als JSON-Datei exportieren"""
    catalog = QuestionCatalog.query.get_or_404(catalog_id)

    # Authorization-Check
    if catalog.user_id != current_user.id:
        flash('Sie haben keine Berechtigung, diesen Katalog zu exportieren.', 'danger')
        return redirect(url_for('catalogs.manage'))

    # Prüfen ob Datei existiert
    if not os.path.exists(catalog.abs_file_path):
        flash('Katalog-Datei nicht gefunden.', 'danger')
        return redirect(url_for('catalogs.manage'))

    # Dateiname für Download
    download_name = f'{catalog.name.replace(" ", "_")}.json'

    try:
        return send_file(
            catalog.abs_file_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/json'
        )
    except Exception as e:
        flash(f'Fehler beim Exportieren: {str(e)}', 'danger')
        return redirect(url_for('catalogs.manage'))


@bp.route('/<int:catalog_id>/explain_status')
@login_required
def explain_status(catalog_id):
    """Gibt Anzahl Fragen mit/ohne Erklärung zurück (JSON)"""
    catalog = QuestionCatalog.query.filter_by(id=catalog_id, user_id=current_user.id).first_or_404()

    if not os.path.exists(catalog.abs_file_path):
        return jsonify({'error': 'Katalogdatei nicht gefunden'}), 404

    with open(catalog.abs_file_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    total = len(questions)
    missing = sum(1 for q in questions if not q.get('explanation', '').strip())
    return jsonify({'total': total, 'missing': missing, 'done': total - missing})


@bp.route('/<int:catalog_id>/explain_next', methods=['POST'])
@login_required
def explain_next(catalog_id):
    """Generiert KI-Erklärung für die nächste Frage ohne Erklärung (JSON)"""
    catalog = QuestionCatalog.query.filter_by(id=catalog_id, user_id=current_user.id).first_or_404()

    if not os.path.exists(catalog.abs_file_path):
        return jsonify({'error': 'Katalogdatei nicht gefunden'}), 404

    with open(catalog.abs_file_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    # Nächste Frage ohne Erklärung finden
    target_idx = None
    for i, q in enumerate(questions):
        if not q.get('explanation', '').strip():
            target_idx = i
            break

    if target_idx is None:
        total = len(questions)
        return jsonify({'done': total, 'total': total, 'missing': 0, 'finished': True})

    q = questions[target_idx]
    explanation = generate_explanation(q)

    if explanation:
        questions[target_idx]['explanation'] = explanation
        with open(catalog.abs_file_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)

    total = len(questions)
    missing = sum(1 for q in questions if not q.get('explanation', '').strip())
    return jsonify({
        'done': total - missing,
        'total': total,
        'missing': missing,
        'finished': missing == 0,
        'question_id': q.get('id'),
        'error': None if explanation else 'KI-Fehler bei dieser Frage'
    })


@bp.route('/switch/<int:catalog_id>', methods=['POST'])
@login_required
def switch_catalog(catalog_id):
    """Katalog schnell wechseln (aus Header-Dropdown)"""
    catalog = QuestionCatalog.query.filter_by(id=catalog_id, user_id=current_user.id).first_or_404()
    QuestionCatalog.query.filter_by(user_id=current_user.id).update({'is_active': False})
    catalog.is_active = True
    db.session.commit()
    flash(f'Katalog "{catalog.name}" aktiviert.', 'success')
    return redirect(request.referrer or url_for('main.index'))
