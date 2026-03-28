# Scrum Abfragequiz

Eine intelligente Flask-basierte Quiz-Anwendung für Scrum/Agile-Zertifizierungsvorbereitung mit SQLite-Datenbank, Multi-User-Support und KI-gestützter Bewertung.

## Features

### Quiz-Funktionen
- **Intelligente Fragenauswahl**: Fibonacci-gewichtetes System bevorzugt schwierige Fragen
- **Drei Fragetypen**:
  - Single-Choice (eine richtige Antwort)
  - Multiple-Choice (mehrere richtige Antworten)
  - Freitext (KI-bewertet mit Mistral AI)
- **Zwei Quiz-Modi**:
  - **Üben**: Ohne Zeitbegrenzung – zum entspannten Lernen
  - **Prüfen**: Mit Zeitbegrenzung – realistische Prüfungssimulation
- **Zeitmanagement**: Konfigurierbares Zeitlimit pro Katalog (nur im Prüfen-Modus)
  - Nach Zeitablauf: Weiterbeantworten möglich, aber als falsch gewertet
- **Sofortiges Feedback**: Richtig/Falsch mit Erklärungen
- **Detaillierte Statistiken**: Nach Kategorie und Subkategorie

### Katalog-Verwaltung
- **Mehrere Kataloge pro User**: Verschiedene Fragensätze organisieren
- **Katalogwähler im Header**: Schnelles Umschalten ohne Umweg über die Katalogverwaltung
- **Fragen-Editor**: Direkt in der App Fragen erstellen/bearbeiten
- **Import/Export**: JSON-Kataloge hoch-/herunterladen
- **Aktivierung**: Ein Katalog aktiv, andere inaktiv

### User-Management
- **Multi-User-Support**: Registrierung, Login, Passwort-Verwaltung
- **User-spezifische Daten**: Kataloge, Gewichtungen, Sessions getrennt
- **Sichere Authentifizierung**: Flask-Login, bcrypt-Passwort-Hashing

### KI-Integration
- **Mistral AI für Freitextfragen**: Automatische Bewertung mit Begründung
- **Intelligente Analyse**: Versteht semantische Ähnlichkeit, nicht nur exakte Übereinstimmung
- **Transparente Bewertung**: KI-Begründung wird angezeigt
- **Offline-Betrieb**: Bei fehlendem Internet wird die KI-Verfügbarkeit vor dem Start geprüft; Freitextfragen werden automatisch ausgelassen

## Installation

### Voraussetzungen
- Python 3.8+
- pip

### Setup

```bash
# Repository klonen
git clone <repository-url>
cd quiz

# Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt

# .env Datei erstellen (für Mistral AI)
echo "MISTRAL_API_KEY=dein-api-key" > .env
```

### Erste Schritte

```bash
# Anwendung starten
python run.py

# Browser öffnen
# http://127.0.0.1:5009

# Standard-User (erstellt automatisch):
# Username: user1
# Password: password123
```

## Verwendung

### Katalog erstellen
1. Login
2. Navigiere zu "Kataloge verwalten"
3. "Neuen Katalog erstellen"
4. Fragen importieren oder selbst erstellen

### Katalog konfigurieren
- **Name & Beschreibung**
- **Zeit pro Frage**: 10-300 Sekunden (Standard: 30s)

### Fragen erstellen
1. Katalog öffnen → "Fragen verwalten"
2. "Neue Frage"
3. Fragentyp wählen:
   - **Single-Choice**: Radio Buttons
   - **Multiple-Choice**: Checkboxen
   - **Freitext**: Textfeld + KI-Bewertung

### Quiz durchführen
1. Katalog aktivieren (oder über den Katalogwähler im Header wechseln)
2. "Quiz starten" → Modus wählen:
   - **Üben**: Kein Timer, entspanntes Lernen
   - **Prüfen**: Timer aktiv, Prüfungssimulation
3. KI-Verfügbarkeit wird automatisch geprüft (bei Offline: keine Freitextfragen)
4. 10 zufällige Fragen (gewichtet nach Fibonacci)
5. Im Prüfen-Modus: Timer läuft; nach Zeitablauf zählen Antworten als falsch
6. Auswertung mit Statistiken

## Technische Details

### Architektur
```
quiz/
├── app/
│   ├── __init__.py          # Flask App Factory
│   ├── models.py            # SQLAlchemy Models
│   ├── routes.py            # Quiz-Routes
│   ├── auth_routes.py       # Authentication
│   ├── catalog_routes.py    # Katalog-Verwaltung
│   ├── question_editor_routes.py  # Fragen-Editor
│   ├── ai_service.py        # Mistral AI Integration
│   ├── quiz_manager.py      # Quiz-Logik
│   ├── database.py          # DB-Initialisierung
│   ├── templates/           # Jinja2 Templates
│   └── static/              # CSS, JS
├── data/
│   └── catalogs/            # User-Kataloge
├── instance/
│   └── quiz.db              # SQLite Datenbank
├── config.py                # Konfiguration
├── requirements.txt
└── run.py                   # Entry Point
```

### Datenbank-Schema

**users**
- id, username, password_hash, created_at

**question_catalogs**
- id, user_id, name, description, file_path
- is_active, question_count, time_per_question
- created_at, updated_at

**quiz_sessions**
- id, user_id, catalog_id
- started_at, completed_at
- total_questions, correct_answers

**responses**
- id, session_id, question_id, question_text
- selected_answer, correct_answer, is_correct
- question_type, category, subcategory
- ai_reasoning, answered_after_timeout
- answered_at

**question_weights** (Fibonacci-System)
- id, user_id, catalog_id, question_id
- weight, last_answered, updated_at

### Fibonacci-Gewichtungssystem

```python
# Gewichte: 1, 2, 3, 5, 8 (Fibonacci)
- Richtig beantwortet: Gewicht sinkt
- Falsch beantwortet: Gewicht steigt
- Höheres Gewicht = höhere Wahrscheinlichkeit
→ Schwierige Fragen kommen häufiger
```

## Frageformat (JSON)

Ein Katalog ist eine JSON-Datei mit einem **Array** von Fragen:

```json
[
  { ... },
  { ... }
]
```

### Felder

| Feld | Pflicht | Beschreibung |
|------|---------|--------------|
| `id` | Ja | Eindeutige ID, z.B. `"frage_1"` |
| `question_type` | Ja | `"single"`, `"multiple"` oder `"text"` |
| `question` | Ja | Fragetext |
| `category` | Nein | Oberkategorie, z.B. `"Product Owner"` |
| `subcategory` | Nein | Unterkategorie, z.B. `"MUST"`, `"CAN"`, `"CAN NOT"`, `"SHOULD"` |
| `options` | Bei single/multiple | Antwortobjekt `{"A": "...", "B": "...", ...}` |
| `correct_answer` | Bei single/multiple | `"B"` (single) oder `["A", "C"]` (multiple) |
| `sample_answer` | Bei text | Musterlösung für die KI-Bewertung |
| `explanation` | Nein | Erklärung die nach der Antwort angezeigt wird |

### Single-Choice

```json
{
  "id": "frage_1",
  "question_type": "single",
  "category": "Product Owner",
  "subcategory": "MUST",
  "question": "Wer ist verantwortlich für die Pflege des Product Backlogs?",
  "options": {
    "A": "Scrum Master",
    "B": "Product Owner",
    "C": "Developers",
    "D": "Stakeholder"
  },
  "correct_answer": "B",
  "explanation": "Der Product Owner ist allein verantwortlich für das Product Backlog."
}
```

### Multiple-Choice

```json
{
  "id": "frage_2",
  "question_type": "multiple",
  "category": "Scrum Team",
  "subcategory": "CAN",
  "question": "Welche Aussagen über den Scrum Master sind korrekt?",
  "options": {
    "A": "Der Scrum Master coacht das Team",
    "B": "Der Scrum Master gibt Arbeitsaufträge",
    "C": "Der Scrum Master entfernt Impediments",
    "D": "Der Scrum Master priorisiert das Backlog"
  },
  "correct_answer": ["A", "C"],
  "explanation": "Der Scrum Master dient dem Team, gibt aber keine Aufträge."
}
```

### Freitext (KI-bewertet)

```json
{
  "id": "frage_3",
  "question_type": "text",
  "category": "Sprint",
  "subcategory": "MUST",
  "question": "Was ist das Ziel eines Daily Scrums?",
  "sample_answer": "Das Daily Scrum dient dazu, den Fortschritt in Richtung Sprint-Ziel zu überprüfen und den Plan für den kommenden Tag anzupassen.",
  "explanation": "Das Daily Scrum ist ein 15-minütiges Ereignis für die Developers."
}
```

## Migrationen

Bei Datenbank-Schema-Änderungen:

```bash
python migrate_<name>.py
```

Vorhandene Migrationen:
- `migrate_to_multi_user.py` - Multi-User-Support
- `migrate_add_weights.py` - Fibonacci-Gewichtungen
- `migrate_add_ai_reasoning.py` - AI-Reasoning-Feld
- `migrate_add_timeout_fields.py` - Timeout-Felder

## Entwicklung

### Code-Struktur
- **Models** (models.py): Datenbankmodelle mit Business-Logik
- **Routes**: RESTful Endpunkte, minimale Logik
- **Services**: Wiederverwendbare Business-Logik
- **Templates**: Jinja2, Template-Vererbung

### Wichtige Funktionen

**Quiz starten:**
```python
# routes.py: mode_select() → start_quiz()
1. KI-Verfügbarkeit prüfen (Mistral API, 3s Timeout)
2. Modus wählen: ueben / pruefen
3. Katalog laden, Freitextfragen filtern wenn offline
4. Fibonacci-gewichtete Auswahl
5. Session erstellen
6. Zeitlimit berechnen (0 im Üben-Modus)
```

**Antwort bewerten:**
```python
# routes.py: answer()
1. Timeout prüfen
2. Bei Freitext: AI-Bewertung
3. Response speichern
4. Gewicht aktualisieren
```

## Lizenz

Private Nutzung für Scrum-Zertifizierungsvorbereitung.

## Credits

Entwickelt mit Claude Code für effizientes Lernen von Scrum/Agile-Konzepten.
