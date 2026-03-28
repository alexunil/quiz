#!/usr/bin/env python3
"""
Testskript: Überprüft die Fibonacci-Logik für verschiedene Gewichtswerte
"""
from app import create_app
from app.models import db, QuestionWeight, User

def test_fibonacci_sequence():
    """Testet die Fibonacci-Logik für verschiedene Szenarien"""
    app = create_app()

    with app.app_context():
        user = User.get_or_create('test_fibonacci_user')
        test_question_id = 'test_fib_question'

        print("\n=== Test: Fibonacci-Logik ===\n")

        # Test 1: Mehrere falsche Antworten (Gewicht steigt)
        print("Test 1: Mehrere falsche Antworten")
        weight = QuestionWeight(user_id=user.id, question_id=test_question_id, weight=3)
        db.session.add(weight)
        db.session.commit()

        print(f"Start: {weight.weight}")
        expected_sequence = [3, 5, 8, 13, 21, 34, 55]

        for i, expected in enumerate(expected_sequence[1:], 1):
            weight.update_weight(is_correct=False)
            print(f"Nach falscher Antwort {i}: {weight.weight} (erwartet: {expected})", end="")
            if weight.weight == expected:
                print(" ✓")
            else:
                print(f" ✗ FEHLER!")

        # Test 2: Mehrere richtige Antworten (Gewicht sinkt)
        print("\nTest 2: Mehrere richtige Antworten (von 8 nach unten)")
        weight.weight = 8
        db.session.commit()

        print(f"Start: {weight.weight}")
        expected_down = [8, 5, 3, 2, 1, 1]  # 1 ist Minimum

        for i, expected in enumerate(expected_down[1:], 1):
            weight.update_weight(is_correct=True)
            print(f"Nach richtiger Antwort {i}: {weight.weight} (erwartet: {expected})", end="")
            if weight.weight == expected:
                print(" ✓")
            else:
                print(f" ✗ FEHLER!")

        # Test 3: Mixed - Auf und ab
        print("\nTest 3: Gemischte Antworten")
        weight.weight = 3
        db.session.commit()
        print(f"Start: {weight.weight}")

        # Falsch → 5
        weight.update_weight(is_correct=False)
        print(f"Nach FALSCH: {weight.weight} (erwartet: 5)", "✓" if weight.weight == 5 else "✗")

        # Falsch → 8
        weight.update_weight(is_correct=False)
        print(f"Nach FALSCH: {weight.weight} (erwartet: 8)", "✓" if weight.weight == 8 else "✗")

        # Richtig → 5
        weight.update_weight(is_correct=True)
        print(f"Nach RICHTIG: {weight.weight} (erwartet: 5)", "✓" if weight.weight == 5 else "✗")

        # Richtig → 3
        weight.update_weight(is_correct=True)
        print(f"Nach RICHTIG: {weight.weight} (erwartet: 3)", "✓" if weight.weight == 3 else "✗")

        # Richtig → 2
        weight.update_weight(is_correct=True)
        print(f"Nach RICHTIG: {weight.weight} (erwartet: 2)", "✓" if weight.weight == 2 else "✗")

        # Richtig → 1
        weight.update_weight(is_correct=True)
        print(f"Nach RICHTIG: {weight.weight} (erwartet: 1)", "✓" if weight.weight == 1 else "✗")

        # Richtig → 1 (bleibt bei 1)
        weight.update_weight(is_correct=True)
        print(f"Nach RICHTIG: {weight.weight} (erwartet: 1, Minimum)", "✓" if weight.weight == 1 else "✗")

        # Falsch → 2 (von 1 wieder hoch)
        weight.update_weight(is_correct=False)
        print(f"Nach FALSCH: {weight.weight} (erwartet: 2)", "✓" if weight.weight == 2 else "✗")

        # Cleanup
        db.session.delete(weight)
        db.session.commit()

        print("\n✓ Fibonacci-Test abgeschlossen!")

if __name__ == '__main__':
    test_fibonacci_sequence()
