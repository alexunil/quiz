"""Authentifizierungs-Routes"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, QuestionCatalog
from datetime import timedelta
import os

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Benutzer-Registrierung"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        email = request.form.get('email', '').strip()

        # Validierung
        if not username:
            flash('Benutzername ist erforderlich.', 'danger')
            return render_template('auth/register.html')

        if len(username) < 3:
            flash('Benutzername muss mindestens 3 Zeichen lang sein.', 'danger')
            return render_template('auth/register.html')

        if not password:
            flash('Passwort ist erforderlich.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 8:
            flash('Passwort muss mindestens 8 Zeichen lang sein.', 'danger')
            return render_template('auth/register.html')

        if password != password_confirm:
            flash('Passwörter stimmen nicht überein.', 'danger')
            return render_template('auth/register.html')

        # Prüfen ob Benutzername bereits existiert
        if User.query.filter_by(username=username).first():
            flash('Benutzername bereits vergeben.', 'danger')
            return render_template('auth/register.html')

        # Prüfen ob E-Mail bereits existiert (wenn angegeben)
        if email and User.query.filter_by(email=email).first():
            flash('E-Mail-Adresse bereits registriert.', 'danger')
            return render_template('auth/register.html')

        # Benutzer erstellen
        user = User(username=username, email=email if email else None)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(f'Willkommen, {username}! Ihr Konto wurde erfolgreich erstellt. Bitte erstellen Sie zuerst einen Fragenkatalog.', 'success')

        # Automatisch einloggen
        login_user(user, remember=True, duration=timedelta(days=7))
        user.update_last_login()

        return redirect(url_for('catalogs.manage'))

    return render_template('auth/register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Benutzer-Login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False) == 'on'

        if not username or not password:
            flash('Benutzername und Passwort sind erforderlich.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash('Ungültiger Benutzername oder Passwort.', 'danger')
            return render_template('auth/login.html')

        if not user.is_active:
            flash('Ihr Konto wurde deaktiviert.', 'danger')
            return render_template('auth/login.html')

        # Einloggen
        duration = timedelta(days=7) if remember else None
        login_user(user, remember=remember, duration=duration)
        user.update_last_login()

        flash(f'Willkommen zurück, {user.username}!', 'success')

        # Weiterleitung zur ursprünglich angeforderten Seite oder Index
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.index'))

    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    """Benutzer-Logout"""
    logout_user()
    flash('Sie wurden erfolgreich abgemeldet.', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/profile')
@login_required
def profile():
    """Benutzer-Profil"""
    from app.models import QuizSession, Response

    # Statistiken berechnen
    total_sessions = QuizSession.query.filter_by(
        user_id=current_user.id,
        completed_at=db.func.coalesce(QuizSession.completed_at, None) != None
    ).count()

    total_questions = db.session.query(db.func.sum(QuizSession.total_questions)).filter_by(
        user_id=current_user.id
    ).scalar() or 0

    total_correct = db.session.query(db.func.sum(QuizSession.correct_answers)).filter_by(
        user_id=current_user.id
    ).scalar() or 0

    success_rate = round((total_correct / total_questions * 100), 1) if total_questions > 0 else 0

    # Anzahl Kataloge
    catalog_count = QuestionCatalog.query.filter_by(user_id=current_user.id).count()

    stats = {
        'total_sessions': total_sessions,
        'total_questions': total_questions,
        'total_correct': total_correct,
        'success_rate': success_rate,
        'catalog_count': catalog_count
    }

    return render_template('auth/profile.html', stats=stats)
