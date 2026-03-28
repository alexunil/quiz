#!/usr/bin/env python3
"""
Testskript: Erstellt Test-Gewichte für verschiedene Fragen und User
"""
from app import create_app
from app.models import db, User, QuestionWeight
from app.quiz_manager import load_questions

def create_test_weights():
    """Erstellt Test-Gewichte für Debugging"""
    app = create_app()

    with app.app_context():
        # User erstellen/abrufen
        user1 = User.get_or_create('user1')
        user2 = User.get_or_create('test_user_2')

        questions = load_questions()

        print(f"\n=== Erstelle Test-Gewichte ===\n")
        print(f"User: {user1.username} (ID: {user1.id})")
        print(f"User: {user2.username} (ID: {user2.id})")
        print(f"Fragen: {len(questions)}\n")

        # Erstelle verschiedene Gewichte für die ersten 5 Fragen
        test_scenarios = [
            # (question_index, user1_weight, user2_weight)
            (0, 1, 8),   # User1 gut, User2 schlecht
            (1, 3, 5),   # Beide mittel
            (2, 8, 2),   # User1 schlecht, User2 gut
            (3, 5, 13),  # User2 sehr schlecht
            (4, 2, 3),   # Beide relativ gut
        ]

        for idx, w1, w2 in test_scenarios:
            if idx < len(questions):
                q = questions[idx]

                # Gewicht für User 1
                weight1 = QuestionWeight.get_or_create(user1.id, q['id'])
                weight1.weight = w1
                db.session.commit()

                # Gewicht für User 2
                weight2 = QuestionWeight.get_or_create(user2.id, q['id'])
                weight2.weight = w2
                db.session.commit()

                print(f"✓ {q['id']}: {user1.username}={w1}, {user2.username}={w2}")

        print("\n✓ Test-Gewichte erstellt!")
        print("\nJetzt in der Fragenübersicht die Details einer Frage öffnen,")
        print("um die Fibonacci-Gewichte zu sehen!")

if __name__ == '__main__':
    create_test_weights()
