import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.ticket import Ticket, TicketIntervention
from app.models.client import Client, Location, ClientContact
from app.models.asset import Asset
from app.models.user import User
from app.services.email_service import send_ticket_created_notification, send_ticket_closed_notification

tickets_bp = Blueprint('tickets', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_ticket_code():
    year = datetime.utcnow().year
    last_ticket = Ticket.query.order_by(Ticket.id.desc()).first()
    next_id = (last_ticket.id + 1) if last_ticket else 1
    return f"TCK-{year}-{next_id:04d}"

@tickets_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '').strip()
    priority_filter = request.args.get('priority', '').strip()
    client_id = request.args.get('client_id', type=int)
    assigned_to_me = request.args.get('my_tickets', type=int)
    sla_filter = request.args.get('sla', '').strip()

    query = Ticket.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    if client_id:
        query = query.filter_by(client_id=client_id)
    if assigned_to_me or not current_user.is_admin:
        query = query.filter_by(assigned_to_id=current_user.id)

    tickets_list = query.order_by(Ticket.created_at.desc()).all()

    if sla_filter == 'breached':
        tickets_list = [t for t in tickets_list if t.is_sla_breached]
    elif sla_filter == 'ontime':
        tickets_list = [t for t in tickets_list if not t.is_sla_breached]

    clients = Client.query.filter_by(is_active=True).order_by(Client.company_name.asc()).all()
    technicians = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()

    return render_template('tickets/index.html',
                           tickets=tickets_list,
                           clients=clients,
                           technicians=technicians,
                           status_filter=status_filter,
                           priority_filter=priority_filter,
                           client_id=client_id,
                           assigned_to_me=assigned_to_me,
                           sla_filter=sla_filter)

@tickets_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    clients = Client.query.filter_by(is_active=True).order_by(Client.company_name.asc()).all()
    technicians = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()

    if request.method == 'POST':
        client_id = request.form.get('client_id', type=int)
        location_id = request.form.get('location_id', type=int)
        contact_id = request.form.get('contact_id', type=int)
        asset_id = request.form.get('asset_id', type=int)
        assigned_to_id = request.form.get('assigned_to_id', type=int)
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'Media').strip()
        service_type = request.form.get('service_type', 'Soporte').strip()

        if not title or not description or not client_id:
            flash('Por favor complete los campos obligatorios.', 'warning')
            return render_template('tickets/form.html', ticket=None, clients=clients, technicians=technicians)

        ticket_code = generate_ticket_code()
        created_now = datetime.utcnow()
        sla_due = Ticket.calculate_sla_due(priority, created_now)

        new_ticket = Ticket(
            ticket_code=ticket_code,
            client_id=client_id,
            location_id=location_id if location_id else None,
            contact_id=contact_id if contact_id else None,
            asset_id=asset_id if asset_id else None,
            assigned_to_id=assigned_to_id if assigned_to_id else current_user.id,
            title=title,
            description=description,
            priority=priority,
            service_type=service_type,
            status='Abierto',
            created_at=created_now,
            sla_due_at=sla_due
        )
        db.session.add(new_ticket)
        db.session.commit()

        # Trigger automatic creation email to client contact
        if new_ticket.contact:
            send_ticket_created_notification(new_ticket, new_ticket.contact)

        flash(f'Ticket {ticket_code} creado exitosamente. SLA debido: {sla_due.strftime("%Y-%m-%d %H:%M")}', 'success')
        return redirect(url_for('tickets.detail', ticket_id=new_ticket.id))

    preselected_client_id = request.args.get('client_id', type=int)
    contacts = []
    locations = []
    assets = []
    if preselected_client_id:
        contacts = ClientContact.query.filter_by(client_id=preselected_client_id).order_by(ClientContact.name.asc()).all()
        locations = Location.query.filter_by(client_id=preselected_client_id).all()
        assets = Asset.query.filter_by(client_id=preselected_client_id).all()

    return render_template('tickets/form.html',
                           ticket=None,
                           clients=clients,
                           technicians=technicians,
                           preselected_client_id=preselected_client_id,
                           contacts=contacts,
                           locations=locations,
                           assets=assets)


@tickets_bp.route('/<int:ticket_id>')
@login_required
def detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    technicians = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()
    return render_template('tickets/detail.html', ticket=ticket, technicians=technicians)

@tickets_bp.route('/<int:ticket_id>/add-intervention', methods=['POST'])
@login_required
def add_intervention(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    notes = request.form.get('notes', '').strip()
    hours_spent = request.form.get('hours_spent', 0.5, type=float)
    new_status = request.form.get('status')
    reassign_to_id = request.form.get('reassign_to_id', type=int)

    if not notes:
        flash('Las notas de la intervención son obligatorias.', 'warning')
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    previous_status = ticket.status
    filename = None

    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename != '' and allowed_file(file.filename):
            sec_filename = secure_filename(file.filename)
            filename = f"tck_{ticket_id}_{sec_filename}"
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)

    # Status update logic
    status_changed_to_closed = False
    if new_status and new_status != ticket.status:
        ticket.status = new_status
        if new_status in ['Resuelto', 'Cerrado']:
            status_changed_to_closed = True
            if not ticket.resolved_at:
                ticket.resolved_at = datetime.utcnow()
        if new_status == 'Cerrado' and not ticket.closed_at:
            ticket.closed_at = datetime.utcnow()

    # Reassignment logic
    if reassign_to_id and reassign_to_id != ticket.assigned_to_id:
        ticket.assigned_to_id = reassign_to_id

    intervention = TicketIntervention(
        ticket_id=ticket_id,
        user_id=current_user.id,
        notes=notes,
        hours_spent=hours_spent,
        previous_status=previous_status,
        new_status=ticket.status,
        attachment_filename=filename
    )

    db.session.add(intervention)
    db.session.commit()

    # Trigger automatic resolution email to contact if ticket was resolved/closed
    if status_changed_to_closed and ticket.contact:
        send_ticket_closed_notification(ticket, ticket.contact, notes)

    flash('Intervención registrada en el historial del ticket.', 'success')
    return redirect(url_for('tickets.detail', ticket_id=ticket_id))

