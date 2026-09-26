from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.setting import SystemSetting
from app.services.email_service import send_email

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if not current_user.is_admin:
        flash('Acceso restringido: Requiere permisos de Administrador.', 'danger')
        return redirect(url_for('dashboard.index'))

    settings = SystemSetting.get_settings()

    if request.method == 'POST':
        settings.mail_server = request.form.get('mail_server', '').strip()
        settings.mail_port = request.form.get('mail_port', 587, type=int)
        settings.mail_use_tls = True if request.form.get('mail_use_tls') else False
        settings.mail_username = request.form.get('mail_username', '').strip()
        
        # Keep old password if blank
        new_pass = request.form.get('mail_password', '').strip()
        if new_pass:
            settings.mail_password = new_pass
            
        settings.mail_sender_name = request.form.get('mail_sender_name', '').strip()
        settings.mail_sender_email = request.form.get('mail_sender_email', '').strip()
        settings.notifications_enabled = True if request.form.get('notifications_enabled') else False

        db.session.commit()
        flash('Parámetros de configuración del sistema guardados correctamente.', 'success')
        return redirect(url_for('settings.index'))

    return render_template('settings/index.html', settings=settings)

@settings_bp.route('/test-email', methods=['POST'])
@login_required
def test_email():
    if not current_user.is_admin:
        flash('Acceso restringido.', 'danger')
        return redirect(url_for('dashboard.index'))

    recipient = request.form.get('test_recipient', '').strip() or current_user.email
    subject = "[Lego ITlook] Correo de Prueba de Configuración SMTP"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px; border-radius: 10px;">
        <h3 style="color: #0ea5e9;">¡Prueba de Configuración SMTP Exitosa!</h3>
        <p>Hola <strong>{current_user.name}</strong>,</p>
        <p>Este es un correo de prueba enviado desde <strong>Lego ITlook</strong> para verificar que los parámetros del servidor SMTP ingresados están funcionando de forma correcta.</p>
        <p style="font-size: 12px; color: #94a3b8;">LEGO TICS SAS &copy; 2026</p>
    </div>
    """
    
    success, msg = send_email(recipient, subject, html_body)
    if success:
        flash(f'Correo de prueba enviado a {recipient}. Por favor revise su bandeja de entrada.', 'success')
    else:
        flash(f'Error al enviar correo de prueba: {msg}', 'danger')
        
    return redirect(url_for('settings.index'))
