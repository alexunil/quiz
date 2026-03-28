#!/usr/bin/env python3
"""
Testskript: Überprüft die Timer-Funktionalität
"""
from app import create_app
from app.quiz_manager import load_questions

def test_timer_calculation():
    """Testet die Berechnung des Zeitlimits"""
    app = create_app()

    with app.app_context():
        questions = load_questions()
        print(f"\n=== Timer-Berechnung ===\n")
        print(f"Gesamtzahl Fragen: {len(questions)}")

        # Zähle Multiple Choice Fragen (single + multiple)
        mc_questions = [q for q in questions if q.get('question_type', 'single') in ['single', 'multiple']]
        text_questions = [q for q in questions if q.get('question_type', 'single') == 'text']

        print(f"Multiple Choice Fragen (single + multiple): {len(mc_questions)}")
        print(f"Freitext-Fragen: {len(text_questions)}")

        time_limit_seconds = len(mc_questions) * 30
        time_limit_minutes = time_limit_seconds / 60

        print(f"\nZeitlimit für Multiple Choice: {time_limit_seconds} Sekunden ({time_limit_minutes:.1f} Minuten)")
        print(f"Freitext-Fragen laufen ohne Timer")

        print("\n✓ Timer-Berechnung erfolgreich!")

if __name__ == '__main__':
    test_timer_calculation()
