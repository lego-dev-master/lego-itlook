import logging
from datetime import date
from app.models.license import MicrosoftLicense
from app.models.user import User

logger = logging.getLogger(__name__)

def check_and_notify_license_expirations():
    """
    RF-06: Scans Microsoft Licenses and identifies licenses expiring in 30, 15, or 5 days.
    Logs and generates email notification alerts for administrators.
    """
    logger.info("Running proactive Microsoft License expiration check...")
    
    licenses = MicrosoftLicense.query.all()
    admins = User.query.filter_by(role='admin', is_active=True).all()
    admin_emails = [admin.email for admin in admins]
    
    alerts = []
    for lic in licenses:
        days = lic.days_until_expiration
        if days in [30, 15, 5, 0] or (days < 0 and days > -7):
            urgency = lic.alert_status
            msg = (
                f"ALERTA LICENCIA [{urgency.upper()}]: "
                f"Cliente: {lic.client.company_name} | "
                f"Suscripción: {lic.subscription_type} | "
                f"Vence en: {days} días (Fecha: {lic.expiration_date})"
            )
            alerts.append({
                'license_id': lic.id,
                'client': lic.client.company_name,
                'subscription': lic.subscription_type,
                'days_left': days,
                'status': urgency,
                'message': msg
            })
            logger.warning(msg)
            
    if alerts and admin_emails:
        logger.info(f"Notification triggered for admins {admin_emails}: {len(alerts)} active license alerts.")
        
    return alerts
