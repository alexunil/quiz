"""Frageneditor-Routes"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import db, QuestionCatalog
import os
import json
import uuid

bp = Blueprint('questions', __name__, url_prefix='/questions')


def load_catalog_questions(catalog):
    """Lädt Fragen aus einem Katalog"""
    try:
        if not os.path.exists(catalog.file_path):
            return []

        with open(catalog.file_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
            return questions if isinstance(questions, list) else []
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden des Katalogs: {e}")
        return []


def save_catalog_questions(catalog, questions):
    """Speichert Fragen in einem Katalog"""
    try:
        with open(catalog.file_path, 'w', encoding='utf-8') as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)

        # Question count aktualisieren
        catalog.update_question_count(len(questions))
        return True
    except Exception as e:
        current_app.logger.error(f"Fehler beim Speichern des Katalogs: {e}")
        return False


def generate_question_id():
    """Generiert eine eindeutige Fragen-ID"""
    return f"q_{uuid.uuid4().hex[:8]}"


@bp.route('/catalog/<int:catalog_id>')
@login_required
def catalog_questions(catalog_id):
    """Fragenübersicht für einen Katalog"""
    catalog = QuestionCatalog.query.get_or_404(catalog_id)

    # Authorization-Check
    if catalog.user_id != current_user.id:
        flash('Sie haben keine Berechtigung, diesen Katalog zu bearbeiten.', 'danger')
        return redirect(url_for('catalogs.manage'))

    questions = load_catalog_questions(catalog)

    return render_template(
        'questions/catalog_questions.html',
        catalog=catalog,
        questions=questions
    )


@bp.route('/catalog/<int:catalog_id>/new', methods=['GET', 'POST'])
@login_required
def new_question(catalog_id):
    """Neue Frage erstellen"""
    catalog = QuestionCatalog.query.get_or_404(catalog_id)

    # Authorization-Check
    if catalog.user_id != current_user.id:
        flash('Sie haben keine Berechtigung, diesen Katalog zu bearbeiten.', 'danger')
        return redirect(url_for('catalogs.manage'))

    if request.method == 'POST':
        question_type = request.form.get('question_type', 'single')

        # Basis-Felder
        question_text = request.form.get('question', '').strip()
        category = request.form.get('category', '').strip()
        subcategory = request.form.get('subcategory', '').strip()
        explanation = request.form.get('explanation', '').strip()

        # Validierung
        if not question_text:
            flash('Fragentext ist erforderlich.', 'danger')
            return render_template('questions/edit_question.html', catalog=catalog, question=None)

        # Neue Frage erstellen
        new_question = {
            'id': generate_question_id(),
            'question': question_text,
            'question_type': question_type,
            'category': category if category else None,
            'subcategory': subcategory if subcategory else None,
            'explanation': explanation if explanation else None
        }

        # Typ-spezifische Felder
        if question_type == 'single':
            # Single Choice: 4 Optionen + richtige Antwort (A-D)
            options = {
                'A': request.form.get('option_a', '').strip(),
                'B': request.form.get('option_b', '').strip(),
                'C': request.form.get('option_c', '').strip(),
                'D': request.form.get('option_d', '').strip()
            }
            correct_answer = request.form.get('correct_answer', '').strip()

            if not all(options.values()):
                flash('Alle 4 Antwortoptionen müssen ausgefüllt werden.', 'danger')
                return render_template('questions/edit_question.html', catalog=catalog, question=None)

            if correct_answer not in ['A', 'B', 'C', 'D']:
                flash('Bitte wählen Sie die richtige Antwort aus.', 'danger')
                return render_template('questions/edit_question.html', catalog=catalog, question=None)

            new_question['options'] = options
            new_question['correct_answer'] = correct_answer

        elif question_type == 'multiple':
            # Multiple Choice: 4 Optionen + mehrere richtige Antworten
            options = {
                'A': request.form.get('option_a', '').strip(),
                'B': request.form.get('option_b', '').strip(),
                'C': request.form.get('option_c', '').strip(),
                'D': request.form.get('option_d', '').strip()
            }
            correct_answers = request.form.getlist('correct_answers')

            if not all(options.values()):
                flash('Alle 4 Antwortoptionen müssen ausgefüllt werden.', 'danger')
                return render_template('questions/edit_question.html', catalog=catalog, question=None)

            if not correct_answers:
                flash('Bitte wählen Sie mindestens eine richtige Antwort aus.', 'danger')
                return render_template('questions/edit_question.html', catalog=catalog, question=None)

            new_question['options'] = options
            new_question['correct_answer'] = sorted(correct_answers)

        elif question_type == 'text':
            # Freitext: Beispielantwort
            sample_answer = request.form.get('sample_answer', '').strip()

            if not sample_answer:
                flash('Bitte geben Sie eine Beispielantwort an.', 'danger')
                return render_template('questions/edit_question.html', catalog=catalog, question=None)

            new_question['sample_answer'] = sample_answer

        # Fragen laden, neue Frage hinzufügen, speichern
        questions = load_catalog_questions(catalog)
        questions.append(new_question)

        if save_catalog_questions(catalog, questions):
            flash(f'Frage "{new_question["id"]}" wurde erfolgreich erstellt.', 'success')
            return redirect(url_for('questions.catalog_questions', catalog_id=catalog.id))
        else:
            flash('Fehler beim Speichern der Frage.', 'danger')

    return render_template('questions/edit_question.html', catalog=catalog, question=None)


@bp.route('/catalog/<int:catalog_id>/edit/<question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(catalog_id, question_id):
    """Frage bearbeiten"""
    catalog = QuestionCatalog.query.get_or_404(catalog_id)

    # Authorization-Check
    if catalog.user_id != current_user.id:
        flash('Sie haben keine Berechtigung, diesen Katalog zu bearbeiten.', 'danger')
        return redirect(url_for('catalogs.manage'))

    questions = load_catalog_questions(catalog)
    question = next((q for q in questions if q['id'] == question_id), None)

    if not question:
        flash('Frage nicht gefunden.', 'danger')
        return redirect(url_for('questions.catalog_questions', catalog_id=catalog.id))

    if request.method == 'POST':
        question_type = request.form.get('question_type', question.get('question_type', 'single'))

        # Basis-Felder aktualisieren
        question['question'] = request.form.get('question', '').strip()
        question['question_type'] = question_type
        question['category'] = request.form.get('category', '').strip() or None
        question['subcategory'] = request.form.get('subcategory', '').strip() or None
        question['explanation'] = request.form.get('explanation', '').strip() or None

        # Validierung
        if not question['question']:
            flash('Fragentext ist erforderlich.', 'danger')
            return render_template('questions/edit_question.html', catalog=catalog, question=question)

        # Typ-spezifische Felder aktualisieren
        if question_type == 'single':
            options = {
                'A': request.form.get('option_a', '').strip(),
                'B': request.form.get('option_b', '').strip(),
                'C': request.form.get('option_c', '').strip(),
                'D': request.form.get('option_d', '').strip()
            }
            correct_answer = request.form.get('correct_answer', '').strip()

            if not all(options.values()):
                flash('Alle 4 Antwortoptionen müssen ausgefüllt werden.', 'danger')
                return render_template('questions/edit_question.html', catalog=catalog, question=question)

            if correct_answer not in ['A', 'B', 'C', 'D']:
                flash('Bitte wählen Sie die richtige Antwort aus.', 'danger')
                return render_template('questions/edit_question.html', catalog=catalog, question=question)

            question['options'] = options
            question['correct_answer'] = correct_answer
            # Alte Felder entfernen
            question.pop('sample_answer', None)

        elif question_type == 'multiple':
            options = {
                'A': request.form.get('option_a', '').strip(),
                'B': request.form.get('option_b', '').strip(),
                'C': request.form.get('option_c', '').strip(),
                'D': request.form.get('option_d', '').strip()
            }
            correct_answers = request.form.getlist('correct_answers')

            if not all(options.values()):
                flash('Alle 4 Antwortoptionen müssen ausgefüllt werden.', 'danger')
                return render_template('questions/edit_question.html', catalog=catalog, question=question)

            if not correct_answers:
                flash('Bitte wählen Sie mindestens eine richtige Antwort aus.', 'danger')
                return render_template('questions/edit_question.html', catalog=catalog, question=question)

            question['options'] = options
            question['correct_answer'] = sorted(correct_answers)
            # Alte Felder entfernen
            question.pop('sample_answer', None)

        elif question_type == 'text':
            sample_answer = request.form.get('sample_answer', '').strip()

            if not sample_answer:
                flash('Bitte geben Sie eine Beispielantwort an.', 'danger')
                return render_template('questions/edit_question.html', catalog=catalog, question=question)

            question['sample_answer'] = sample_answer
            # Alte Felder entfernen
            question.pop('options', None)
            question.pop('correct_answer', None)

        # Speichern
        if save_catalog_questions(catalog, questions):
            flash(f'Frage "{question_id}" wurde erfolgreich aktualisiert.', 'success')
            return redirect(url_for('questions.catalog_questions', catalog_id=catalog.id))
        else:
            flash('Fehler beim Speichern der Frage.', 'danger')

    return render_template('questions/edit_question.html', catalog=catalog, question=question)


@bp.route('/catalog/<int:catalog_id>/delete/<question_id>', methods=['POST'])
@login_required
def delete_question(catalog_id, question_id):
    """Frage löschen"""
    catalog = QuestionCatalog.query.get_or_404(catalog_id)

    # Authorization-Check
    if catalog.user_id != current_user.id:
        flash('Sie haben keine Berechtigung, diesen Katalog zu bearbeiten.', 'danger')
        return redirect(url_for('catalogs.manage'))

    questions = load_catalog_questions(catalog)
    original_count = len(questions)

    # Frage entfernen
    questions = [q for q in questions if q['id'] != question_id]

    if len(questions) == original_count:
        flash('Frage nicht gefunden.', 'danger')
    else:
        if save_catalog_questions(catalog, questions):
            flash(f'Frage "{question_id}" wurde gelöscht.', 'success')
        else:
            flash('Fehler beim Löschen der Frage.', 'danger')

    return redirect(url_for('questions.catalog_questions', catalog_id=catalog.id))
