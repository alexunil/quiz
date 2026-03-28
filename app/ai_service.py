"""AI Service für die Bewertung von Freitextantworten mit Mistral AI"""
from mistralai import Mistral
from flask import current_app
import json


def evaluate_text_answer(question_text: str, user_answer: str, correct_answer: str) -> dict:
    """
    Bewertet eine Freitextantwort mit Mistral AI.

    Args:
        question_text: Der Text der Frage
        user_answer: Die vom Benutzer gegebene Antwort
        correct_answer: Die Musterantwort/richtige Antwort

    Returns:
        dict mit:
            - is_correct: bool - True wenn richtig, False wenn falsch
            - reasoning: str - Begründung der AI
            - error: str - Fehlermeldung falls API-Call fehlschlägt
    """
    api_key = current_app.config.get('MISTRAL_API_KEY')

    if not api_key:
        return {
            'is_correct': None,
            'reasoning': 'Mistral API Key nicht konfiguriert.',
            'error': 'NO_API_KEY'
        }

    try:
        client = Mistral(api_key=api_key)

        # Prompt für die AI erstellen
        prompt = f"""Du bist ein Prüfer für Scrum-Zertifizierungen. Bewerte die folgende Antwort eines Kandidaten.

FRAGE:
{question_text}

ANTWORT DES KANDIDATEN:
{user_answer}

MUSTERANTWORT:
{correct_answer}

AUFGABE:
Bewerte, ob die Antwort des Kandidaten inhaltlich korrekt ist. Die Antwort muss nicht wörtlich mit der Musterantwort übereinstimmen, sollte aber die wesentlichen Punkte enthalten.

Antworte im folgenden JSON-Format:
{{
    "is_correct": true/false,
    "reasoning": "Deine Begründung in 2-3 Sätzen"
}}

Wichtig:
- is_correct: true = Die Antwort enthält die wesentlichen richtigen Punkte
- is_correct: false = Die Antwort ist falsch, unvollständig oder verfehlt das Thema
- reasoning: Erkläre kurz und präzise, warum die Antwort richtig oder falsch ist"""

        # API Call
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Niedrige Temperatur für konsistente Bewertung
            max_tokens=500
        )

        # Response parsen
        content = response.choices[0].message.content

        # JSON aus der Response extrahieren
        # Manchmal gibt die AI Markdown-Code-Blocks zurück
        if '```json' in content:
            start = content.find('```json') + 7
            end = content.find('```', start)
            content = content[start:end].strip()
        elif '```' in content:
            start = content.find('```') + 3
            end = content.find('```', start)
            content = content[start:end].strip()

        result = json.loads(content)

        return {
            'is_correct': result.get('is_correct', False),
            'reasoning': result.get('reasoning', 'Keine Begründung verfügbar.'),
            'error': None
        }

    except json.JSONDecodeError as e:
        current_app.logger.error(f"JSON parsing error: {e}, Content: {content}")
        return {
            'is_correct': None,
            'reasoning': 'Fehler beim Parsen der AI-Antwort.',
            'error': 'JSON_PARSE_ERROR'
        }
    except Exception as e:
        current_app.logger.error(f"Mistral AI error: {e}")
        return {
            'is_correct': None,
            'reasoning': f'Fehler bei der AI-Bewertung: {str(e)}',
            'error': str(e)
        }
