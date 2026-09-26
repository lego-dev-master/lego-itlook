from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Credenciales inválidas. Por favor verifique correo y contraseña.', 'danger')
            return render_template('auth/login.html', email=email)

        if not user.is_active:
            flash('Su cuenta se encuentra desactivada. Contacte al administrador.', 'warning')
            return render_template('auth/login.html', email=email)

        login_user(user, remember=remember)
        flash(f'¡Bienvenido de nuevo, {user.name}!', 'success')
        
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('dashboard.index'))

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ha cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/technicians', methods=['GET', 'POST'])
@login_required
def technicians():
    if not current_user.is_admin:
        flash('Acceso denegado: Se requieren permisos de Administrador.', 'danger')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'tech')

        if User.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado.', 'warning')
        else:
            new_user = User(name=name, email=email, role=role)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash(f'Técnico/Usuario {name} registrado con éxito.', 'success')
            return redirect(url_for('auth.technicians'))

    techs = User.query.all()
    return render_template('auth/technicians.html', technicians=techs)
