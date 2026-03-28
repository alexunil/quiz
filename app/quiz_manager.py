import json
import random
import os
from flask import current_app


def load_questions():
    """Lädt alle Fragen aus der JSON-Datei (legacy)"""
    try:
        with open(current_app.config['QUESTIONS_FILE'], 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Unterstützt sowohl altes Format {"questions": [...]} als auch neues [...]
            if isinstance(data, dict):
                return data.get('questions', [])
            return data
    except FileNotFoundError:
        current_app.logger.error(f"Fragen-Datei nicht gefunden: {current_app.config['QUESTIONS_FILE']}")
        return []
    except json.JSONDecodeError:
        current_app.logger.error("Fehler beim Parsen der JSON-Datei")
        return []


def load_questions_for_user(user_id):
    """
    Lädt Fragen aus dem aktiven Katalog des Benutzers
    Returns: (questions, catalog_id) oder ([], None) wenn kein aktiver Katalog
    """
    from app.models import User

    user = User.query.get(user_id)
    if not user:
        return [], None

    catalog = user.get_active_catalog()
    if not catalog:
        return [], None

    # Fragen aus Katalog-Datei laden
    try:
        if not os.path.exists(catalog.file_path):
            current_app.logger.error(f"Katalog-Datei nicht gefunden: {catalog.file_path}")
            return [], catalog.id

        with open(catalog.file_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)

            if not isinstance(questions, list):
                current_app.logger.error(f"Ungültiges Katalog-Format: {catalog.file_path}")
                return [], catalog.id

            return questions, catalog.id

    except json.JSONDecodeError:
        current_app.logger.error(f"Fehler beim Parsen der Katalog-Datei: {catalog.file_path}")
        return [], catalog.id
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden des Katalogs: {str(e)}")
        return [], catalog.id


def select_random_questions(n=None, user_id=None, catalog_id=None, questions=None):
    """
    Wählt n Fragen aus - gewichtet nach Fibonacci-System wenn user_id und catalog_id angegeben sind.

    Args:
        n: Anzahl der auszuwählenden Fragen
        user_id: Benutzer-ID für gewichtete Auswahl
        catalog_id: Katalog-ID für katalog-spezifische Gewichtungen
        questions: Fragenliste (optional, sonst wird load_questions() verwendet)

    Wenn user_id und catalog_id angegeben sind:
    - Fragen werden basierend auf ihren katalog-spezifischen Gewichten ausgewählt
    - Neue Fragen starten mit Gewicht 3
    - Richtig beantwortete Fragen werden weniger wahrscheinlich (Gewicht sinkt)
    - Falsch beantwortete Fragen werden häufiger (Gewicht steigt nach Fibonacci)

    Sonst:
    - Rein zufällige Auswahl
    """
    if n is None:
        n = current_app.config['QUESTIONS_PER_QUIZ']

    all_questions = questions if questions is not None else load_questions()

    if not all_questions:
        return []

    # Falls weniger Fragen verfügbar sind als gewünscht, alle nehmen
    if len(all_questions) < n:
        current_app.logger.warning(
            f"Nur {len(all_questions)} Fragen verfügbar, aber {n} angefordert. "
            f"Es werden alle verfügbaren Fragen verwendet."
        )
        selected = all_questions.copy()
    else:
        # Gewichtete Auswahl wenn user_id und catalog_id gegeben sind
        if user_id and catalog_id:
            from app.models import QuestionWeight

            # Gewichte für alle Fragen abrufen oder initialisieren
            weights = []
            for question in all_questions:
                weight_obj = QuestionWeight.get_or_create(user_id, catalog_id, question['id'])
                weights.append(weight_obj.weight)

            # Gewichtete Auswahl ohne Zurücklegen
            # random.choices würde mit Zurücklegen wählen, daher eigene Implementierung
            selected = []
            remaining_questions = all_questions.copy()
            remaining_weights = weights.copy()

            for _ in range(n):
                if not remaining_questions:
                    break

                # Gewichtete Auswahl eines Elements
                chosen = random.choices(remaining_questions, weights=remaining_weights, k=1)[0]
                chosen_index = remaining_questions.index(chosen)

                selected.append(chosen)
                remaining_questions.pop(chosen_index)
                remaining_weights.pop(chosen_index)
        else:
            # Ursprüngliches Verhalten: rein zufällig
            selected = random.sample(all_questions, n)

    return selected


def get_question_by_id(question_id):
    """Findet eine Frage anhand ihrer ID"""
    all_questions = load_questions()

    for question in all_questions:
        if question['id'] == question_id:
            return question

    return None


def check_answer(question_id, selected_answer):
    """
    Überprüft, ob die ausgewählte Antwort korrekt ist
    Gibt (is_correct, question_data) zurück
    Unterstützt: single, multiple, text
    """
    question = get_question_by_id(question_id)

    if not question:
        return False, None

    question_type = question.get('question_type', 'single')

    if question_type == 'text':
        # Text-Fragen werden nicht automatisch bewertet
        return None, question
    elif question_type == 'multiple':
        # Multiple-Choice: Strikte Bewertung
        correct = question['correct_answer']
        if isinstance(selected_answer, list) and isinstance(correct, list):
            is_correct = sorted(selected_answer) == sorted(correct)
        else:
            is_correct = False
        return is_correct, question
    else:  # single
        is_correct = selected_answer == question['correct_answer']
        return is_correct, question


def calculate_statistics(session_id):
    """
    Berechnet Statistiken für eine Quiz-Session
    Nur bewertbare Fragen (single, multiple) werden in Prozentberechnung einbezogen
    Text-Fragen werden separat aufgelistet
    """
    from app.models import Response, QuizSession

    session = QuizSession.query.get(session_id)
    if not session:
        return None

    responses = Response.query.filter_by(session_id=session_id).all()

    # Bewertbare Fragen (single, multiple) - is_correct ist nicht NULL
    evaluable_responses = [r for r in responses if r.is_correct is not None]
    # Text-Fragen (nicht bewertet) - is_correct ist NULL
    text_responses = [r for r in responses if r.is_correct is None]

    total_evaluable = len(evaluable_responses)
    correct = sum(1 for r in evaluable_responses if r.is_correct)
    incorrect = total_evaluable - correct

    # Statistiken nach Kategorie (nur bewertbare)
    category_stats = {}
    for response in evaluable_responses:
        cat = response.category or 'Unbekannt'
        if cat not in category_stats:
            category_stats[cat] = {'total': 0, 'correct': 0}

        category_stats[cat]['total'] += 1
        if response.is_correct:
            category_stats[cat]['correct'] += 1

    # Statistiken nach Subkategorie (nur bewertbare)
    subcategory_stats = {}
    for response in evaluable_responses:
        subcat = response.subcategory or 'Unbekannt'
        if subcat not in subcategory_stats:
            subcategory_stats[subcat] = {'total': 0, 'correct': 0}

        subcategory_stats[subcat]['total'] += 1
        if response.is_correct:
            subcategory_stats[subcat]['correct'] += 1

    percentage = (correct / total_evaluable * 100) if total_evaluable > 0 else 0

    return {
        'total': total_evaluable,  # Nur bewertbare Fragen
        'correct': correct,
        'incorrect': incorrect,
        'percentage': round(percentage, 1),
        'category_stats': category_stats,
        'subcategory_stats': subcategory_stats,
        'responses': evaluable_responses,  # Für Summary-Anzeige
        'text_responses': text_responses,  # Separate Liste für Text-Fragen
        'total_questions': len(responses)  # Alle Fragen inkl. Text
    }
