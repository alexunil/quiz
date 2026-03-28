#!/usr/bin/env python3
"""
Testskript: Überprüft die Gewichtsfunktionalität
"""
from app import create_app
from app.models import db, QuestionWeight, User
from app.quiz_manager import select_random_questions

def test_weights():
    """Testet das Gewichtssystem"""
    app = create_app()

    with app.app_context():
        # User abrufen oder erstellen
        user = User.get_or_create('user1')
        print(f"\nUser: {user.username} (ID: {user.id})")

        # Alle bestehenden Gewichte anzeigen
        weights = QuestionWeight.query.filter_by(user_id=user.id).all()
        print(f"\nAnzahl gespeicherter Gewichte: {len(weights)}")

        if weights:
            print("\nAktuelle Gewichte:")
            for w in weights:
                print(f"  Frage {w.question_id}: Gewicht {w.weight}")

        # Gewichtete Fragenauswahl testen
        print("\n--- Teste gewichtete Fragenauswahl ---")
        questions = select_random_questions(n=3, user_id=user.id)
        print(f"Ausgewählte Fragen (gewichtet): {len(questions)}")
        for q in questions:
            weight_obj = QuestionWeight.query.filter_by(user_id=user.id, question_id=q['id']).first()
            print(f"  - Frage {q['id']}: '{q['question'][:50]}...' (Gewicht: {weight_obj.weight if weight_obj else 'N/A'})")

        # Test: Gewicht aktualisieren
        if questions:
            test_question_id = questions[0]['id']
            weight = QuestionWeight.get_or_create(user.id, test_question_id)
            print(f"\n--- Teste Gewicht-Updates für Frage {test_question_id} ---")
            print(f"Aktuelles Gewicht: {weight.weight}")

            # Simuliere falsche Antwort (Gewicht steigt)
            print("\nSimuliere falsche Antwort...")
            old_weight = weight.weight
            weight.update_weight(is_correct=False)
            print(f"Gewicht nach falscher Antwort: {old_weight} → {weight.weight}")

            # Simuliere richtige Antwort (Gewicht sinkt)
            print("\nSimuliere richtige Antwort...")
            old_weight = weight.weight
            weight.update_weight(is_correct=True)
            print(f"Gewicht nach richtiger Antwort: {old_weight} → {weight.weight}")

        print("\n✓ Test abgeschlossen!")

if __name__ == '__main__':
    test_weights()
