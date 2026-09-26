import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
from flask import current_app
from app.models.setting import SystemSetting

logger = logging.getLogger(__name__)

def _send_email_async(app, server_host, port, use_tls, username, password, sender_email, sender_name, recipient_email, subject, html_body):
    with app.app_context():
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{sender_name} <{sender_email}>"
            msg['To'] = recipient_email

            part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(part)

            server = smtplib.SMTP(server_host, port, timeout=10)
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.sendmail(sender_email, [recipient_email], msg.as_string())
            server.quit()
            logger.info(f"Email successfully sent to {recipient_email} - Subject: {subject}")
        except Exception as e:
            logger.error(f"Error sending email to {recipient_email}: {str(e)}")

def send_email(recipient_email, subject, html_body):
    """
    Reads dynamic SystemSetting configuration from DB and sends email in a background thread.
    """
    app = current_app._get_current_object()
    settings = SystemSetting.get_settings()

    if not settings.notifications_enabled:
        logger.info("Global email notifications are currently disabled in System Settings.")
        return False, "Notificaciones desactivadas en la configuración del sistema."

    if not settings.mail_server or not recipient_email:
        logger.warning("Missing mail server or recipient email.")
        return False, "Servidor de correo o destinatario no configurado."

    Thread(
        target=_send_email_async,
        args=(
            app,
            settings.mail_server,
            settings.mail_port,
            settings.mail_use_tls,
            settings.mail_username,
            settings.mail_password,
            settings.mail_sender_email,
            settings.mail_sender_name,
            recipient_email,
            subject,
            html_body
        )
    ).start()

    return True, "Correo enviado a la cola de entrega."

def send_ticket_created_notification(ticket, contact):
    if not contact or not contact.email:
        return
    
    subject = f"[Lego ITlook] Nuevo Ticket Creado #{ticket.ticket_code} - {ticket.title}"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px; border-radius: 10px;">
        <h2 style="color: #0ea5e9;">LEGO TICS SAS - Soporte Técnico</h2>
        <p>Hola <strong>{contact.name}</strong>,</p>
        <p>Se ha registrado exitosamente un nuevo ticket de servicio para su atención:</p>
        <div style="background-color: #1e293b; padding: 15px; border-left: 4px solid #0ea5e9; margin: 15px 0;">
            <p style="margin: 5px 0;"><strong>Código de Ticket:</strong> #{ticket.ticket_code}</p>
            <p style="margin: 5px 0;"><strong>Asunto:</strong> {ticket.title}</p>
            <p style="margin: 5px 0;"><strong>Prioridad:</strong> {ticket.priority}</p>
            <p style="margin: 5px 0;"><strong>Tipo de Servicio:</strong> {ticket.service_type}</p>
            <p style="margin: 5px 0;"><strong>Límite Estimado SLA:</strong> {ticket.sla_due_at.strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        <p><strong>Descripción del Requerimiento:</strong></p>
        <p style="background-color: #1e293b; padding: 10px; border-radius: 5px;">{ticket.description}</p>
        <p style="font-size: 12px; color: #94a3b8; margin-top: 20px;">Este es un mensaje automático de Lego ITlook. Por favor no responda directamente a este correo.</p>
    </div>
    """
    send_email(contact.email, subject, html_body)

def send_ticket_closed_notification(ticket, contact, notes=None):
    if not contact or not contact.email:
        return

    status_str = "Resuelto" if ticket.status == 'Resuelto' else "Cerrado"
    subject = f"[Lego ITlook] Ticket {status_str} #{ticket.ticket_code} - {ticket.title}"
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px; border-radius: 10px;">
        <h2 style="color: #22c55e;">LEGO TICS SAS - Ticket {status_str}</h2>
        <p>Hola <strong>{contact.name}</strong>,</p>
        <p>Le informamos que su ticket de servicio ha sido marcado como <strong>{status_str.upper()}</strong>:</p>
        <div style="background-color: #1e293b; padding: 15px; border-left: 4px solid #22c55e; margin: 15px 0;">
            <p style="margin: 5px 0;"><strong>Código de Ticket:</strong> #{ticket.ticket_code}</p>
            <p style="margin: 5px 0;"><strong>Asunto:</strong> {ticket.title}</p>
            <p style="margin: 5px 0;"><strong>Estado Actual:</strong> {ticket.status}</p>
        </div>
        """
    if notes:
        html_body += f"""
        <p><strong>Detalles de Resolución / Diagnóstico Final:</strong></p>
        <p style="background-color: #1e293b; padding: 10px; border-radius: 5px;">{notes}</p>
        """
        
    html_body += """
        <p>Gracias por confiar en nuestros servicios de infraestructura y soporte TI.</p>
        <p style="font-size: 12px; color: #94a3b8; margin-top: 20px;">Lego ITlook &copy; 2026 - LEGO TICS SAS</p>
    </div>
    """
    send_email(contact.email, subject, html_body)
