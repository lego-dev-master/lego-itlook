from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from app.models.client import Client
from app.models.asset import Asset
from app.models.license import MicrosoftLicense
from app.models.ticket import Ticket
from app.services.license_notifier import check_and_notify_license_expirations

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    # Execute proactive license status check
    alerts = check_and_notify_license_expirations()

    total_clients = Client.query.filter_by(is_active=True).count()
    total_assets = Asset.query.count()
    
    # Licenses metrics
    all_licenses = MicrosoftLicense.query.all()
    expiring_30_days = sum(1 for l in all_licenses if 0 <= l.days_until_expiration <= 30)
    expiring_critical = sum(1 for l in all_licenses if 0 <= l.days_until_expiration <= 5)
    expired_licenses = sum(1 for l in all_licenses if l.days_until_expiration < 0)
    
    # Tickets metrics
    open_tickets = Ticket.query.filter(Ticket.status.in_(['Abierto', 'En Proceso', 'Espera Cliente'])).count()
    critical_tickets = Ticket.query.filter(Ticket.status.in_(['Abierto', 'En Proceso']), Ticket.priority == 'Crítica').count()
    
    # SLA breaches
    sla_breached_count = 0
    active_tickets = Ticket.query.filter(Ticket.status.in_(['Abierto', 'En Proceso', 'Espera Cliente'])).all()
    for t in active_tickets:
        if t.is_sla_breached:
            sla_breached_count += 1
            
    # Recent tickets
    if current_user.is_admin:
        recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(8).all()
    else:
        recent_tickets = Ticket.query.filter_by(assigned_to_id=current_user.id).order_by(Ticket.created_at.desc()).limit(8).all()

    # Priority distribution
    priority_counts = {
        'Crítica': Ticket.query.filter_by(priority='Crítica').count(),
        'Alta': Ticket.query.filter_by(priority='Alta').count(),
        'Media': Ticket.query.filter_by(priority='Media').count(),
        'Baja': Ticket.query.filter_by(priority='Baja').count(),
    }

    return render_template('dashboard/index.html',
                           total_clients=total_clients,
                           total_assets=total_assets,
                           expiring_30_days=expiring_30_days,
                           expiring_critical=expiring_critical,
                           expired_licenses=expired_licenses,
                           open_tickets=open_tickets,
                           critical_tickets=critical_tickets,
                           sla_breached_count=sla_breached_count,
                           recent_tickets=recent_tickets,
                           priority_counts=priority_counts,
                           alerts=alerts)
