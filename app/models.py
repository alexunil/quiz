from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Benutzer-Modell"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Beziehungen
    quiz_sessions = db.relationship('QuizSession', backref='user', lazy=True)
    question_weights = db.relationship('QuestionWeight', backref='user', lazy=True)
    catalogs = db.relationship('QuestionCatalog', backref='user', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def get_or_create(username):
        """Benutzer abrufen oder neu erstellen"""
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()
        return user

    def set_password(self, password):
        """Passwort hashen und speichern"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Passwort überprüfen"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_active_catalog(self):
        """Aktiven Katalog des Benutzers abrufen"""
        return QuestionCatalog.query.filter_by(user_id=self.id, is_active=True).first()

    def update_last_login(self):
        """Letzten Login aktualisieren"""
        self.last_login = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f'<User {self.username}>'


class QuestionCatalog(db.Model):
    """Fragenkatalog-Modell"""
    __tablename__ = 'question_catalogs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(500), nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    question_count = db.Column(db.Integer, default=0, nullable=False)
    time_per_question = db.Column(db.Integer, default=30, nullable=False)  # Sekunden pro Frage
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: Ein User kann nicht zwei Kataloge mit gleichem Namen haben
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='_user_catalog_name_uc'),)

    # Beziehungen
    quiz_sessions = db.relationship('QuizSession', backref='catalog', lazy=True)
    question_weights = db.relationship('QuestionWeight', backref='catalog', lazy=True, cascade='all, delete-orphan')

    @property
    def abs_file_path(self):
        """Absoluter Dateipfad – löst relative Pfade zur Laufzeit über CATALOGS_DIR auf."""
        import os
        if os.path.isabs(self.file_path):
            return self.file_path
        from flask import current_app
        return os.path.join(current_app.config['CATALOGS_DIR'], self.file_path)

    @staticmethod
    def create_catalog(user_id, name, file_path, description=None, is_active=False):
        """Neuen Katalog erstellen"""
        catalog = QuestionCatalog(
            user_id=user_id,
            name=name,
            file_path=file_path,
            description=description,
            is_active=is_active
        )
        db.session.add(catalog)
        db.session.commit()
        return catalog

    def activate(self):
        """Diesen Katalog aktivieren und alle anderen des Users deaktivieren"""
        # Alle Kataloge des Users deaktivieren
        QuestionCatalog.query.filter_by(user_id=self.user_id).update({'is_active': False})
        # Diesen Katalog aktivieren
        self.is_active = True
        db.session.commit()

    def update_question_count(self, count):
        """Fragen-Anzahl aktualisieren"""
        self.question_count = count
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f'<QuestionCatalog {self.name} - User {self.user_id}>'


class QuizSession(db.Model):
    """Quiz-Session-Modell"""
    __tablename__ = 'quiz_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    catalog_id = db.Column(db.Integer, db.ForeignKey('question_catalogs.id'), nullable=True)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    total_questions = db.Column(db.Integer)
    correct_answers = db.Column(db.Integer)

    # Beziehungen
    responses = db.relationship('Response', backref='session', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def create_new(user_id, catalog_id=None):
        """Neue Quiz-Session erstellen"""
        session = QuizSession(user_id=user_id, catalog_id=catalog_id)
        db.session.add(session)
        db.session.commit()
        return session

    def complete(self, correct_count, total_count):
        """Session als abgeschlossen markieren"""
        self.completed_at = datetime.utcnow()
        self.correct_answers = correct_count
        self.total_questions = total_count
        db.session.commit()

    def __repr__(self):
        return f'<QuizSession {self.id} - User {self.user_id}>'


class Response(db.Model):
    """Antwort-Modell - unterstützt Single-Choice, Multiple-Choice und Freitext"""
    __tablename__ = 'responses'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('quiz_sessions.id'), nullable=False)
    question_id = db.Column(db.String(50), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    selected_answer = db.Column(db.Text, nullable=False)  # Geändert: String(1) → Text
    correct_answer = db.Column(db.Text, nullable=False)   # Geändert: String(1) → Text
    is_correct = db.Column(db.Boolean, nullable=True)     # Geändert: nullable für Text-Fragen
    question_type = db.Column(db.String(20), default='single')  # Neu: single, multiple, text
    category = db.Column(db.String(100))
    subcategory = db.Column(db.String(100))
    ai_reasoning = db.Column(db.Text, nullable=True)  # AI-Begründung für Freitextfragen
    answered_after_timeout = db.Column(db.Boolean, default=False, nullable=False)  # Nach Zeitablauf beantwortet
    answered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @staticmethod
    def record(session_id, question_data, selected_answer, ai_evaluation=None, answered_after_timeout=False):
        """Antwort speichern - unterstützt single, multiple und text

        Args:
            session_id: ID der Quiz-Session
            question_data: Dict mit Fragendaten
            selected_answer: Ausgewählte/eingegebene Antwort
            ai_evaluation: Optional dict mit {'is_correct': bool, 'reasoning': str} für Textfragen
            answered_after_timeout: Bool - True wenn nach Zeitablauf beantwortet
        """
        question_type = question_data.get('question_type', 'single')

        # Correct answer verarbeiten
        correct_answer_raw = question_data.get('correct_answer')
        if isinstance(correct_answer_raw, list):
            # Multiple-choice: als sortierter comma-separated string
            correct_answer = ','.join(sorted(correct_answer_raw))
        elif correct_answer_raw is None:
            # Text: sample_answer verwenden
            correct_answer = question_data.get('sample_answer', '')
        else:
            # Single-choice: string beibehalten
            correct_answer = correct_answer_raw

        # Selected answer verarbeiten
        if isinstance(selected_answer, list):
            # Multiple-choice: als sortierter comma-separated string
            selected_answer_str = ','.join(sorted(selected_answer))
        else:
            # Single-choice oder Text: string beibehalten
            selected_answer_str = selected_answer

        # Korrektheit prüfen (typ-spezifisch)
        ai_reasoning = None
        if question_type == 'text':
            # Text-Fragen: AI-Bewertung verwenden wenn vorhanden
            if ai_evaluation:
                is_correct = ai_evaluation.get('is_correct')
                ai_reasoning = ai_evaluation.get('reasoning')
            else:
                is_correct = None
        elif question_type == 'multiple':
            # Strikte Bewertung: alle richtig + keine falschen
            is_correct = selected_answer_str == correct_answer
        else:  # single
            is_correct = selected_answer_str == correct_answer

        # Bei Timeout: Antwort als falsch werten (außer bei Textfragen ohne AI-Bewertung)
        if answered_after_timeout and is_correct is not None:
            is_correct = False

        response = Response(
            session_id=session_id,
            question_id=question_data['id'],
            question_text=question_data['question'],
            selected_answer=selected_answer_str,
            correct_answer=correct_answer,
            is_correct=is_correct,
            question_type=question_type,
            category=question_data.get('category'),
            subcategory=question_data.get('subcategory'),
            ai_reasoning=ai_reasoning,
            answered_after_timeout=answered_after_timeout
        )
        db.session.add(response)
        db.session.commit()
        return response

    def __repr__(self):
        return f'<Response {self.id} - Question {self.question_id}>'


class QuestionWeight(db.Model):
    """Fragegewicht-Modell - Speichert Fibonacci-Gewichte für jede Frage pro User und Katalog"""
    __tablename__ = 'question_weights'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    catalog_id = db.Column(db.Integer, db.ForeignKey('question_catalogs.id'), nullable=True)
    question_id = db.Column(db.String(50), nullable=False)
    weight = db.Column(db.Integer, nullable=False, default=3)  # Startwert: 3
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: Ein User kann nur ein Gewicht pro Frage pro Katalog haben
    __table_args__ = (db.UniqueConstraint('user_id', 'catalog_id', 'question_id', name='_user_catalog_question_uc'),)

    @staticmethod
    def get_or_create(user_id, catalog_id, question_id):
        """Gewicht abrufen oder mit Startwert 3 erstellen"""
        weight = QuestionWeight.query.filter_by(
            user_id=user_id,
            catalog_id=catalog_id,
            question_id=question_id
        ).first()
        if not weight:
            weight = QuestionWeight(
                user_id=user_id,
                catalog_id=catalog_id,
                question_id=question_id,
                weight=3
            )
            db.session.add(weight)
            db.session.commit()
        return weight

    def update_weight(self, is_correct):
        """
        Gewicht nach Fibonacci-Logik aktualisieren
        - Richtig: Wert verringern (3→2→1, min=1)
        - Falsch: Wert nach Fibonacci erhöhen (3→5→8→13→21...)
        """
        if is_correct:
            # Fibonacci-Folge: 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144...
            # Bei richtiger Antwort: Wert verringern zum nächst niedrigeren Fibonacci-Wert
            fibonacci_sequence = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
            current_weight = self.weight

            # Finde den nächst niedrigeren Wert in der Fibonacci-Folge
            new_weight = 1  # Minimum
            for i in range(len(fibonacci_sequence) - 1, -1, -1):
                if fibonacci_sequence[i] < current_weight:
                    new_weight = fibonacci_sequence[i]
                    break

            self.weight = new_weight
        else:
            # Bei falscher Antwort: Wert erhöhen zum nächst höheren Fibonacci-Wert
            fibonacci_sequence = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
            current_weight = self.weight

            # Finde den nächst höheren Wert in der Fibonacci-Folge
            new_weight = current_weight
            for fib in fibonacci_sequence:
                if fib > current_weight:
                    new_weight = fib
                    break

            # Falls wir am Ende der Liste sind, weiter in der Fibonacci-Folge berechnen
            if new_weight == current_weight:
                # Berechne die nächsten Fibonacci-Zahlen dynamisch
                a, b = fibonacci_sequence[-2], fibonacci_sequence[-1]
                while b <= current_weight:
                    a, b = b, a + b
                new_weight = b

            self.weight = new_weight

        self.last_updated = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f'<QuestionWeight User:{self.user_id} Q:{self.question_id} W:{self.weight}>'
