import os
from datetime import timedelta
from dotenv import load_dotenv

# .env Datei laden
load_dotenv()

class Config:
    """Konfigurationseinstellungen für die Quiz-Applikation"""

    # Sicherheitsschlüssel für Flask-Sessions
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Mistral AI API Key
    MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')

    # Datenbank-Konfiguration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'quiz.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Quiz-spezifische Einstellungen
    QUESTIONS_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'questions.json')
    QUESTIONS_PER_QUIZ = 10

    # Katalog-Einstellungen
    CATALOGS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'catalogs')

    # Authentifizierungs-Einstellungen
    PASSWORD_MIN_LENGTH = 8
    REMEMBER_ME_DURATION = timedelta(days=7)

    # Session-Einstellungen
    PERMANENT_SESSION_LIFETIME = timedelta(hours=4)  # Session läuft nach 4 Stunden Inaktivität ab
    SESSION_COOKIE_SECURE = False  # True für HTTPS in Produktion
    SESSION_COOKIE_HTTPONLY = True  # Schutz vor XSS
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF-Schutz

    # Upload-Einstellungen
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file size
    ALLOWED_EXTENSIONS = {'json'}
