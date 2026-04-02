from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import login_required, current_user
from app.models import User, QuizSession, Response
from app.quiz_manager import select_random_questions, get_question_by_id, calculate_statistics, load_questions, load_questions_for_user, get_question_from_catalog
from app.ai_service import evaluate_text_answer
import socket

bp = Blueprint('main', __name__)


def check_ai_availability():
    """Prüft ob Internet/KI verfügbar ist (TCP-Connect, kein HTTP-Request)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect(('api.mistral.ai', 443))
        sock.close()
        return True
    except Exception:
        return False


@bp.route('/')
def index():
    """Startseite"""
    return render_template('index.html')


@bp.route('/mode_select')
@login_required
def mode_select():
    """Modus-Auswahl vor dem Quiz"""
    catalog = current_user.get_active_catalog()
    if not catalog:
        flash('Kein aktiver Katalog gefunden. Bitte aktivieren Sie zuerst einen Katalog.', 'warning')
        return redirect(url_for('catalogs.manage'))

    ai_available = check_ai_availability()

    questions, _ = load_questions_for_user(current_user.id)
    text_question_count = sum(1 for q in questions if q.get('question_type') == 'text') if questions else 0

    return render_template(
        'mode_select.html',
        active_catalog=catalog,
        ai_available=ai_available,
        text_question_count=text_question_count
    )


@bp.route('/start', methods=['POST'])
@login_required
def start_quiz():
    """Neues Quiz starten"""
    # Aktiven Katalog des Benutzers prüfen
    catalog = current_user.get_active_catalog()
    if not catalog:
        flash('Kein aktiver Katalog gefunden. Bitte aktivieren Sie zuerst einen Katalog.', 'warning')
        return redirect(url_for('catalogs.manage'))

    # Fragen aus aktivem Katalog laden
    questions, catalog_id = load_questions_for_user(current_user.id)

    if not questions:
        flash('Es sind keine Fragen im aktiven Katalog verfügbar. Bitte importieren Sie Fragen.', 'warning')
        return redirect(url_for('catalogs.manage'))

    # Fragen auswählen (gewichtet nach Fibonacci-System mit katalog-spezifischen Gewichten)
    selected_questions = select_random_questions(
        user_id=current_user.id,
        catalog_id=catalog_id,
        questions=questions
    )

    if not selected_questions:
        flash('Keine Fragen konnten ausgewählt werden.', 'error')
        return redirect(url_for('main.index'))

    # Modus aus Formular (ueben = ohne Zeit, pruefen = mit Zeit)
    quiz_mode = request.form.get('mode', 'pruefen')

    # KI-Verfügbarkeit prüfen und Freitext-Fragen ggf. filtern
    ai_available = check_ai_availability()
    if not ai_available:
        text_count_before = sum(1 for q in selected_questions if q.get('question_type') == 'text')
        selected_questions = [q for q in selected_questions if q.get('question_type', 'single') != 'text']
        if text_count_before > 0:
            flash(f'Kein Internet: {text_count_before} Freitext-Frage(n) wurden ausgelassen.', 'info')

    if not selected_questions:
        flash('Keine Fragen verfügbar (alle Freitext-Fragen wurden wegen fehlender KI ausgelassen).', 'error')
        return redirect(url_for('main.index'))

    # Neue Quiz-Session erstellen
    quiz_session = QuizSession.create_new(current_user.id, catalog_id=catalog_id)

    # Zeitlimit berechnen: nur im Prüfen-Modus und nur für Single/Multiple-Choice
    from datetime import datetime, timedelta
    mc_questions = [q for q in selected_questions if q.get('question_type', 'single') in ['single', 'multiple']]
    if quiz_mode == 'ueben':
        time_limit_seconds = 0  # kein Zeitlimit
    else:
        time_per_question = catalog.time_per_question
        time_limit_seconds = len(mc_questions) * time_per_question
    start_time = datetime.utcnow()

    # Session als permanent markieren (verhindert vorzeitiges Ablaufen)
    session.permanent = True

    # Session-Daten speichern (nur IDs, keine vollständigen Fragen - Cookie-Limit 4KB)
    session['session_id'] = quiz_session.id
    session['user_id'] = current_user.id
    session['catalog_id'] = catalog_id
    session['question_ids'] = [q['id'] for q in selected_questions]
    session['current_index'] = 0
    session['correct_count'] = 0
    session['deferred_questions'] = []  # Zurückgestellte Fragen
    session['start_time'] = start_time.isoformat()
    session['time_limit_seconds'] = time_limit_seconds
    session['time_expired'] = False  # Flag ob Zeit abgelaufen ist
    session['quiz_mode'] = quiz_mode
    session['ai_available'] = ai_available

    # Zur ersten Frage weiterleiten
    return redirect(url_for('main.question', index=0))


@bp.route('/question/<int:index>')
@login_required
def question(index):
    """Frage anzeigen"""
    # Session-Daten validieren
    if 'question_ids' not in session or 'session_id' not in session:
        flash('Keine aktive Quiz-Session gefunden. Bitte starten Sie ein neues Quiz.', 'warning')
        return redirect(url_for('main.index'))

    question_ids = session['question_ids']

    # Index validieren
    if index < 0 or index >= len(question_ids):
        flash('Ungültiger Fragen-Index.', 'error')
        return redirect(url_for('main.index'))

    # Frage aus Katalog-Datei laden
    question_data = get_question_from_catalog(session['catalog_id'], question_ids[index])
    if not question_data:
        flash('Frage nicht gefunden.', 'error')
        return redirect(url_for('main.index'))

    # Aktuelle Position aktualisieren
    session['current_index'] = index

    # Zeit-Informationen berechnen
    from datetime import datetime
    time_info = None
    quiz_mode = session.get('quiz_mode', 'pruefen')
    if quiz_mode != 'ueben' and session.get('time_limit_seconds', 0) > 0 and question_data.get('question_type', 'single') in ['single', 'multiple']:
        # Nur bei Prüfen-Modus und Single/Multiple-Choice Zeit anzeigen
        start_time = datetime.fromisoformat(session['start_time'])
        elapsed_seconds = (datetime.utcnow() - start_time).total_seconds()
        remaining_seconds = max(0, session['time_limit_seconds'] - elapsed_seconds)
        time_info = {
            'remaining_seconds': int(remaining_seconds),
            'total_seconds': session['time_limit_seconds'],
            'is_expired': remaining_seconds <= 0
        }

    return render_template(
        'question.html',
        question=question_data,
        index=index,
        total=len(question_ids),
        correct_count=session.get('correct_count', 0),
        time_info=time_info,
        quiz_mode=quiz_mode
    )


@bp.route('/answer/<int:index>', methods=['POST'])
@login_required
def answer(index):
    """Antwort verarbeiten und Feedback anzeigen - unterstützt single, multiple, text"""
    # Session-Daten validieren
    if 'question_ids' not in session or 'session_id' not in session:
        flash('Keine aktive Quiz-Session gefunden.', 'warning')
        return redirect(url_for('main.index'))

    question_ids = session['question_ids']

    # Index validieren
    if index < 0 or index >= len(question_ids):
        flash('Ungültiger Fragen-Index.', 'error')
        return redirect(url_for('main.index'))

    # Frage aus Katalog-Datei laden
    question_data = get_question_from_catalog(session['catalog_id'], question_ids[index])
    if not question_data:
        flash('Frage nicht gefunden.', 'error')
        return redirect(url_for('main.index'))

    question_type = question_data.get('question_type', 'single')

    # Zeitüberschreitungsprüfung für Multiple Choice Fragen (nur im Prüfen-Modus)
    answered_after_timeout = False
    from datetime import datetime
    quiz_mode = session.get('quiz_mode', 'pruefen')
    if quiz_mode != 'ueben' and question_type in ['single', 'multiple'] and 'start_time' in session and session.get('time_limit_seconds', 0) > 0:
        start_time = datetime.fromisoformat(session['start_time'])
        elapsed_seconds = (datetime.utcnow() - start_time).total_seconds()
        if elapsed_seconds > session.get('time_limit_seconds', float('inf')):
            answered_after_timeout = True
            # Flag setzen, aber NICHT abbrechen - User kann weitermachen
            if not session.get('time_expired'):
                session['time_expired'] = True
                flash('⏰ Die Zeit ist abgelaufen! Weitere Antworten zählen als falsch.', 'warning')

    # Antwort aus Formular holen - typ-spezifisch
    if question_type == 'text':
        selected_answer = request.form.get('text_answer', '').strip()
        if not selected_answer:
            flash('Bitte geben Sie eine Antwort ein.', 'warning')
            return redirect(url_for('main.question', index=index))
    elif question_type == 'multiple':
        selected_answer = request.form.getlist('answer')  # Liste von Checkboxen
        if not selected_answer:
            flash('Bitte wählen Sie mindestens eine Antwort aus.', 'warning')
            return redirect(url_for('main.question', index=index))
    else:  # single
        selected_answer = request.form.get('answer')
        if not selected_answer:
            flash('Bitte wählen Sie eine Antwort aus.', 'warning')
            return redirect(url_for('main.question', index=index))

    # Bei Textfragen: AI-Bewertung durchführen
    ai_evaluation = None
    if question_type == 'text':
        ai_evaluation = evaluate_text_answer(
            question_text=question_data['question'],
            user_answer=selected_answer,
            correct_answer=question_data.get('sample_answer', '')
        )

    # Antwort in Datenbank speichern
    response = Response.record(
        session_id=session['session_id'],
        question_data=question_data,
        selected_answer=selected_answer,
        ai_evaluation=ai_evaluation,
        answered_after_timeout=answered_after_timeout
    )

    # Gewicht aktualisieren (nur für bewertbare Fragen)
    if response.is_correct is not None:
        from app.models import QuestionWeight
        weight = QuestionWeight.get_or_create(
            session['user_id'],
            session.get('catalog_id'),
            question_data['id']
        )
        weight.update_weight(response.is_correct)

    # Zähler aktualisieren (nur für bewertbare Fragen)
    if response.is_correct is not None and response.is_correct:
        session['correct_count'] = session.get('correct_count', 0) + 1

    return render_template(
        'feedback.html',
        question=question_data,
        selected_answer=selected_answer,
        is_correct=response.is_correct,
        ai_reasoning=response.ai_reasoning,
        answered_after_timeout=answered_after_timeout,
        index=index,
        total=len(question_ids),
        correct_count=session.get('correct_count', 0)
    )


@bp.route('/defer/<int:index>', methods=['POST'])
@login_required
def defer_question(index):
    """Frage zurückstellen und zur nächsten Frage"""
    if 'question_ids' not in session:
        flash('Keine aktive Quiz-Session gefunden.', 'warning')
        return redirect(url_for('main.index'))

    question_ids = session['question_ids']
    deferred = session.get('deferred_questions', [])

    # Frage zur Liste der zurückgestellten hinzufügen (falls noch nicht vorhanden)
    if index not in deferred:
        deferred.append(index)
        session['deferred_questions'] = deferred

    # Zur nächsten Frage
    next_index = index + 1

    # Wenn noch reguläre Fragen übrig sind
    if next_index < len(question_ids):
        return redirect(url_for('main.question', index=next_index))

    # Wenn alle regulären Fragen durch sind, zurückgestellte Fragen abarbeiten
    if deferred:
        # Erste zurückgestellte Frage holen und aus der Liste entfernen
        deferred_index = deferred.pop(0)
        session['deferred_questions'] = deferred
        return redirect(url_for('main.question', index=deferred_index))

    # Sonst Quiz abschließen
    return _complete_quiz()


@bp.route('/next/<int:index>', methods=['POST'])
@login_required
def next_question(index):
    """Zur nächsten Frage oder zur Zusammenfassung"""
    if 'question_ids' not in session:
        flash('Keine aktive Quiz-Session gefunden.', 'warning')
        return redirect(url_for('main.index'))

    question_ids = session['question_ids']
    next_index = index + 1

    # Wenn noch reguläre Fragen übrig sind, zur nächsten Frage
    if next_index < len(question_ids):
        return redirect(url_for('main.question', index=next_index))

    # Wenn alle regulären Fragen durch sind, zurückgestellte Fragen abarbeiten
    deferred = session.get('deferred_questions', [])
    if deferred:
        deferred_index = deferred.pop(0)
        session['deferred_questions'] = deferred
        return redirect(url_for('main.question', index=deferred_index))

    # Sonst Quiz abschließen
    return _complete_quiz()


def _complete_quiz():
    """Hilfsunktion: Quiz abschließen und zur Zusammenfassung"""
    quiz_session = QuizSession.query.get(session['session_id'])
    if quiz_session:
        quiz_session.complete(
            correct_count=session.get('correct_count', 0),
            total_count=len(session.get('question_ids', []))
        )

    return redirect(url_for('main.summary'))


@bp.route('/summary')
@login_required
def summary():
    """Zusammenfassung und Statistiken anzeigen"""
    if 'session_id' not in session:
        flash('Keine Quiz-Session gefunden.', 'warning')
        return redirect(url_for('main.index'))

    # Statistiken berechnen
    stats = calculate_statistics(session['session_id'])

    if not stats:
        flash('Keine Statistiken verfügbar.', 'error')
        return redirect(url_for('main.index'))

    # Session-Daten löschen (Quiz ist abgeschlossen)
    session_id = session['session_id']
    session.clear()

    return render_template('summary.html', stats=stats, session_id=session_id)


@bp.route('/questions')
@login_required
def questions_overview():
    """Fragenübersicht mit Sortierung, Filter und Paginierung"""
    from app.models import QuestionWeight

    # Parameter aus Request
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'asc')
    filter_category = request.args.get('category', '')
    filter_subcategory = request.args.get('subcategory', '')
    filter_type = request.args.get('type', '')
    search = request.args.get('search', '')
    min_weight = request.args.get('min_weight', '', type=str)

    # Fragen aus aktivem Katalog laden
    questions, catalog_id = load_questions_for_user(current_user.id)

    if not questions:
        flash('Kein aktiver Katalog oder keine Fragen verfügbar.', 'warning')
        all_questions = []
    else:
        all_questions = questions

    # Filter anwenden
    filtered_questions = all_questions

    if filter_category:
        filtered_questions = [q for q in filtered_questions if q.get('category', '') == filter_category]

    if filter_subcategory:
        filtered_questions = [q for q in filtered_questions if q.get('subcategory', '') == filter_subcategory]

    if filter_type:
        filtered_questions = [q for q in filtered_questions if q.get('question_type', 'single') == filter_type]

    if search:
        search_lower = search.lower()
        filtered_questions = [q for q in filtered_questions
                            if search_lower in q.get('question', '').lower()
                            or search_lower in q.get('id', '').lower()]

    # Nach Gewicht filtern
    if min_weight and catalog_id:
        try:
            min_weight_int = int(min_weight)
            # Gewichte für alle Fragen laden
            question_ids = [q['id'] for q in filtered_questions]
            weights = QuestionWeight.query.filter(
                QuestionWeight.user_id == current_user.id,
                QuestionWeight.catalog_id == catalog_id,
                QuestionWeight.question_id.in_(question_ids),
                QuestionWeight.weight >= min_weight_int
            ).all()

            # Nur Fragen behalten, die das Mindestgewicht haben
            weight_question_ids = {w.question_id for w in weights}
            filtered_questions = [q for q in filtered_questions if q['id'] in weight_question_ids]
        except ValueError:
            pass  # Ungültige Eingabe ignorieren

    # Sortierung
    reverse = (sort_order == 'desc')
    if sort_by == 'id':
        filtered_questions.sort(key=lambda q: q.get('id', ''), reverse=reverse)
    elif sort_by == 'category':
        filtered_questions.sort(key=lambda q: q.get('category', ''), reverse=reverse)
    elif sort_by == 'subcategory':
        filtered_questions.sort(key=lambda q: q.get('subcategory', ''), reverse=reverse)
    elif sort_by == 'type':
        filtered_questions.sort(key=lambda q: q.get('question_type', 'single'), reverse=reverse)

    # Eindeutige Kategorien und Subkategorien für Filter-Dropdown
    categories = sorted(list(set(q.get('category', '') for q in all_questions if q.get('category'))))
    subcategories = sorted(list(set(q.get('subcategory', '') for q in all_questions if q.get('subcategory'))))
    types = sorted(list(set(q.get('question_type', 'single') for q in all_questions)))

    # Paginierung
    total_questions = len(filtered_questions)
    total_pages = (total_questions + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_questions = filtered_questions[start_idx:end_idx]

    return render_template(
        'questions_overview.html',
        questions=paginated_questions,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_questions=total_questions,
        sort_by=sort_by,
        sort_order=sort_order,
        filter_category=filter_category,
        filter_subcategory=filter_subcategory,
        filter_type=filter_type,
        search=search,
        min_weight=min_weight,
        categories=categories,
        subcategories=subcategories,
        types=types
    )


@bp.route('/questions/<question_id>')
@login_required
def question_detail(question_id):
    """Detail-Ansicht einer einzelnen Frage (JSON für Modal)"""
    from app.models import QuestionWeight, QuestionCatalog

    catalog = current_user.get_active_catalog()
    if not catalog:
        return jsonify({'error': 'Kein aktiver Katalog'}), 404

    question = get_question_from_catalog(catalog.id, question_id)
    if not question:
        return jsonify({'error': 'Frage nicht gefunden'}), 404
    weight_data = []

    weight = QuestionWeight.query.filter_by(
            user_id=current_user.id,
            catalog_id=catalog.id,
            question_id=question_id
        ).first()

    if weight:
        weight_data.append({
            'user_id': current_user.id,
            'username': current_user.username,
            'catalog_id': catalog.id,
            'catalog_name': catalog.name,
            'weight': weight.weight,
            'last_updated': weight.last_updated.isoformat() if weight.last_updated else None
        })

    # Question-Daten mit Gewichten kombinieren
    result = dict(question)
    result['weights'] = weight_data

    return jsonify(result)
